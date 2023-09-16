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

//	printf("read_msr : %lld\n", (long long)(data));
	return (long long)data;
}


int main() {
	int cpu_model, rc, old_result, new_result;
	cpu_model=detect_cpu();
	detect_packages();

	int fd;
	fd=open_msr(0);
	rc=read_msr(fd, MSR_RAPL_POWER_UNIT);
	printf("MSR_RAPL_POWER_UNIT: %d\n", rc);

	old_result=read_msr(fd, MSR_PP0_ENERGY_STATUS);
	while(1) {
		new_result=read_msr(fd, MSR_PP0_ENERGY_STATUS);
		if (new_result < old_result) {
			printf("REACHED OVERFLOW!\n");
			printf("old_msr = %d, new_msr = %d\n", old_result, new_result);
			break;
		}
		old_result = new_result;
		sleep(1);
	}
	close(fd);
	
	return 0;
}

