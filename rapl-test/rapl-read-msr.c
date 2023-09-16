/* Read the RAPL registers on recent (>sandybridge) Intel processors	*/
/*									*/
/* There are currently three ways to do this:				*/
/*	1. Read the MSRs directly with /dev/cpu/??/msr			*/
/*	2. Use the perf_event_open() interface				*/
/*	3. Read the values from the sysfs powercap interface		*/
/*									*/
/* MSR Code originally based on a (never made it upstream) linux-kernel	*/
/*	RAPL driver by Zhang Rui <rui.zhang@intel.com>			*/
/*	https://lkml.org/lkml/2011/5/26/93				*/
/* Additional contributions by:						*/
/*	Romain Dolbeau -- romain @ dolbeau.org				*/
/*									*/
/* For raw MSR access the /dev/cpu/??/msr driver must be enabled and	*/
/*	permissions set to allow read access.				*/
/*	You might need to "modprobe msr" before it will work.		*/
/*									*/
/* perf_event_open() support requires at least Linux 3.14 and to have	*/
/*	/proc/sys/kernel/perf_event_paranoid < 1			*/
/*									*/
/* the sysfs powercap interface got into the kernel in 			*/
/*	2d281d8196e38dd (3.13)						*/
/*									*/
/* Compile with:   gcc -O2 -Wall -o rapl-read rapl-read.c -lm		*/
/*									*/
/* Vince Weaver -- vincent.weaver @ maine.edu -- 11 September 2015	*/
/*									*/

#include "rapl-read.h"


static int open_msr(int core) {

	char msr_filename[BUFSIZ];
	int fd;

	sprintf(msr_filename, "/dev/cpu/%d/msr", core);
	fd = open(msr_filename, O_RDONLY);
	if ( fd < 0 ) {
		if ( errno == ENXIO ) {
			fprintf(stderr, "rdmsr: No CPU %d\n", core);
			exit(2);
		} else if ( errno == EIO ) {
			fprintf(stderr, "rdmsr: CPU %d doesn't support MSRs\n",
					core);
			exit(3);
		} else {
			perror("rdmsr:open");
			fprintf(stderr,"Trying to open %s\n",msr_filename);
			exit(127);
		}
	}

	return fd;
}

static long long read_msr(int fd, int which) {

	uint64_t data;

	if ( pread(fd, &data, sizeof data, which) != sizeof data ) {
		perror("rdmsr:pread");
		exit(127);
	}

	printf("read_msr = %lld\n", (long long)data);
	return (long long)data;
}


/*******************************/
/* MSR code                    */
/*******************************/
static int rapl_msr(int core, int cpu_model) {

	int fd;
	long long result;
	double power_units,time_units;
	double cpu_energy_units[MAX_PACKAGES],dram_energy_units[MAX_PACKAGES];
	double package_before[MAX_PACKAGES],package_after[MAX_PACKAGES];
	double pp0_before[MAX_PACKAGES],pp0_after[MAX_PACKAGES];
	double pp1_before[MAX_PACKAGES],pp1_after[MAX_PACKAGES];
	double dram_before[MAX_PACKAGES],dram_after[MAX_PACKAGES];
	double psys_before[MAX_PACKAGES],psys_after[MAX_PACKAGES];
	double thermal_spec_power,minimum_power,maximum_power,time_window;
	int j;

	int dram_avail=0,pp0_avail=0,pp1_avail=0,psys_avail=0;
	int different_units=0;

	printf("\nTrying /dev/msr interface to gather results\n\n");

	if (cpu_model<0) {
		printf("\tUnsupported CPU model %d\n",cpu_model);
		return -1;
	}

	setup_cpu_model(cpu_model, &pp0_avail, &pp1_avail, &dram_avail, &psys_avail, &different_units);

	for(j=0;j<total_packages;j++) {
		printf("\tListing paramaters for package #%d\n",j);

		fd=open_msr(package_map[j]);

		/* Calculate the units used */
		result=read_msr(fd,MSR_RAPL_POWER_UNIT);

		power_units=pow(0.5,(double)(result&0xf));
		cpu_energy_units[j]=pow(0.5,(double)((result>>8)&0x1f));
		time_units=pow(0.5,(double)((result>>16)&0xf));

		/* On Haswell EP and Knights Landing */
		/* The DRAM units differ from the CPU ones */
		if (different_units) {
			dram_energy_units[j]=pow(0.5,(double)16);
			printf("DRAM: Using %lf instead of %lf\n",
				dram_energy_units[j],cpu_energy_units[j]);
		}
		else {
			dram_energy_units[j]=cpu_energy_units[j];
		}

		printf("\t\tPower units = %.3fW\n",power_units);
		printf("\t\tCPU Energy units = %.8fJ\n",cpu_energy_units[j]);
		printf("\t\tDRAM Energy units = %.8fJ\n",dram_energy_units[j]);
		printf("\t\tTime units = %.8fs\n",time_units);
		printf("\n");

		/* Show package power info */
		result=read_msr(fd,MSR_PKG_POWER_INFO);
		thermal_spec_power=power_units*(double)(result&0x7fff);
		printf("\t\tPackage thermal spec: %.3fW\n",thermal_spec_power);
		minimum_power=power_units*(double)((result>>16)&0x7fff);
		printf("\t\tPackage minimum power: %.3fW\n",minimum_power);
		maximum_power=power_units*(double)((result>>32)&0x7fff);
		printf("\t\tPackage maximum power: %.3fW\n",maximum_power);
		time_window=time_units*(double)((result>>48)&0x7fff);
		printf("\t\tPackage maximum time window: %.6fs\n",time_window);

		/* Show package power limit */
		result=read_msr(fd,MSR_PKG_RAPL_POWER_LIMIT);
		printf("\t\tPackage power limits are %s\n", (result >> 63) ? "locked" : "unlocked");
		double pkg_power_limit_1 = power_units*(double)((result>>0)&0x7FFF);
		double pkg_time_window_1 = time_units*(double)((result>>17)&0x007F);
		printf("\t\tPackage power limit #1: %.3fW for %.6fs (%s, %s)\n",
			pkg_power_limit_1, pkg_time_window_1,
			(result & (1LL<<15)) ? "enabled" : "disabled",
			(result & (1LL<<16)) ? "clamped" : "not_clamped");
		double pkg_power_limit_2 = power_units*(double)((result>>32)&0x7FFF);
		double pkg_time_window_2 = time_units*(double)((result>>49)&0x007F);
		printf("\t\tPackage power limit #2: %.3fW for %.6fs (%s, %s)\n", 
			pkg_power_limit_2, pkg_time_window_2,
			(result & (1LL<<47)) ? "enabled" : "disabled",
			(result & (1LL<<48)) ? "clamped" : "not_clamped");

		/* only available on *Bridge-EP */
		if ((cpu_model==CPU_SANDYBRIDGE_EP) || (cpu_model==CPU_IVYBRIDGE_EP)) {
			result=read_msr(fd,MSR_PKG_PERF_STATUS);
			double acc_pkg_throttled_time=(double)result*time_units;
			printf("\tAccumulated Package Throttled Time : %.6fs\n",
				acc_pkg_throttled_time);
		}

		/* only available on *Bridge-EP */
		if ((cpu_model==CPU_SANDYBRIDGE_EP) || (cpu_model==CPU_IVYBRIDGE_EP)) {
			result=read_msr(fd,MSR_PP0_PERF_STATUS);
			double acc_pp0_throttled_time=(double)result*time_units;
			printf("\tPowerPlane0 (core) Accumulated Throttled Time "
				": %.6fs\n",acc_pp0_throttled_time);

			result=read_msr(fd,MSR_PP0_POLICY);
			int pp0_policy=(int)result&0x001f;
			printf("\tPowerPlane0 (core) for core %d policy: %d\n",core,pp0_policy);

		}


		if (pp1_avail) {
			result=read_msr(fd,MSR_PP1_POLICY);
			int pp1_policy=(int)result&0x001f;
			printf("\tPowerPlane1 (on-core GPU if avail) %d policy: %d\n",
				core,pp1_policy);
		}
		close(fd);

	}
	printf("\n");

	for(j=0;j<total_packages;j++) {

		fd=open_msr(package_map[j]);

		/* Package Energy */
		//result=read_msr(fd,MSR_PKG_ENERGY_STATUS);
		//package_before[j]=(double)result*cpu_energy_units[j];

		/* PP0 energy */
		/* Not available on Knights* */
		/* Always returns zero on Haswell-EP? */
		if (pp0_avail) {
			result=read_msr(fd,MSR_PP0_ENERGY_STATUS);
			pp0_before[j]=(double)result*cpu_energy_units[j];
		}

		/* PP1 energy */
		/* not available on *Bridge-EP */
		//if (pp1_avail) {
	 	//	result=read_msr(fd,MSR_PP1_ENERGY_STATUS);
		//	pp1_before[j]=(double)result*cpu_energy_units[j];
		//}


		/* Updated documentation (but not the Vol3B) says Haswell and	*/
		/* Broadwell have DRAM support too				*/
		//if (dram_avail) {
		//	result=read_msr(fd,MSR_DRAM_ENERGY_STATUS);
		//	dram_before[j]=(double)result*dram_energy_units[j];
		//}


		/* Skylake and newer for Psys				*/
		//if ((cpu_model==CPU_SKYLAKE) ||
		//	(cpu_model==CPU_SKYLAKE_HS) ||
		//	(cpu_model==CPU_KABYLAKE) ||
		//	(cpu_model==CPU_KABYLAKE_MOBILE)) {
		//
		//	result=read_msr(fd,MSR_PLATFORM_ENERGY_STATUS);
		//	psys_before[j]=(double)result*cpu_energy_units[j];
		//}

		close(fd);
	}

  	printf("\n\tSleeping 1 second\n\n");
	sleep(1);

	for(j=0;j<total_packages;j++) {

		fd=open_msr(package_map[j]);

		printf("\tPackage %d:\n",j);

		//result=read_msr(fd,MSR_PKG_ENERGY_STATUS);
		//printf("package energy after: %lld\n", result);
		//package_after[j]=(double)result*cpu_energy_units[j];
		//printf("\t\tPackage energy: %.6fJ\n",
		//	package_after[j]-package_before[j]);

		result=read_msr(fd,MSR_PP0_ENERGY_STATUS);
		pp0_after[j]=(double)result*cpu_energy_units[j];
		printf("\t\tPowerPlane0 (cores): %.6fJ\n",
			pp0_after[j]-pp0_before[j]);

		/* not available on SandyBridge-EP */
		//if (pp1_avail) {
		//	result=read_msr(fd,MSR_PP1_ENERGY_STATUS);
		//	pp1_after[j]=(double)result*cpu_energy_units[j];
		//	printf("\t\tPowerPlane1 (on-core GPU if avail): %.6f J\n",
		//		pp1_after[j]-pp1_before[j]);
		//}

		//if (dram_avail) {
		//	result=read_msr(fd,MSR_DRAM_ENERGY_STATUS);
		//	dram_after[j]=(double)result*dram_energy_units[j];
		//	printf("\t\tDRAM: %.6fJ\n",
		//		dram_after[j]-dram_before[j]);
		//}

		//if (psys_avail) {
		//	result=read_msr(fd,MSR_PLATFORM_ENERGY_STATUS);
		//	psys_after[j]=(double)result*cpu_energy_units[j];
		//	printf("\t\tPSYS: %.6fJ\n",
		//		psys_after[j]-psys_before[j]);
		//}

		close(fd);
	}
	printf("\n");
	printf("Note: the energy measurements can overflow in 60s or so\n");
	printf("      so try to sample the counters more often than that.\n\n");

	return 0;
}

static int rapl_perf(int core) {
	return 0;
}

static int rapl_sysfs(int core) {
	return 0;
}

int main(int argc, char **argv) {

	int c;
	int force_msr=0,force_perf_event=0,force_sysfs=0;
	int core=0;
	int result=-1;
	int cpu_model;

	printf("\n");
	printf("RAPL read -- use -s for sysfs, -p for perf_event, -m for msr\n\n");

	opterr=0;

	while ((c = getopt (argc, argv, "c:hmps")) != -1) {
		switch (c) {
		case 'c':
			core = atoi(optarg);
			printf("core: %d\n", core);
			break;
		case 'h':
			printf("Usage: %s [-c core] [-h] [-m]\n\n",argv[0]);
			printf("\t-c core : specifies which core to measure\n");
			printf("\t-h      : displays this help\n");
			printf("\t-m      : forces use of MSR mode\n");
			printf("\t-p      : forces use of perf_event mode\n");
			printf("\t-s      : forces use of sysfs mode\n");
			exit(0);
		case 'm':
			force_msr = 1;
			break;
		case 'p':
			force_perf_event = 1;
			break;
		case 's':
			force_sysfs = 1;
			break;
		default:
			fprintf(stderr,"Unknown option %c\n",c);
			exit(-1);
		}
	}

	(void)force_sysfs;

	cpu_model=detect_cpu();
	detect_packages();

	if ((!force_msr) && (!force_perf_event)) {
		result=rapl_sysfs(core);
	}

	if (result<0) {
		if ((force_perf_event) && (!force_msr)) {
			result=rapl_perf(core);
		}
	}

	if (result<0) {
		result=rapl_msr(core,cpu_model);
	}

	if (result<0) {

		printf("Unable to read RAPL counters.\n");
		printf("* Verify you have an Intel Sandybridge or newer processor\n");
		printf("* You may need to run as root or have /proc/sys/kernel/perf_event_paranoid set properly\n");
		printf("* If using raw msr access, make sure msr module is installed\n");
		printf("\n");

		return -1;

	}

	return 0;
}
