import os
import pandas as pd
import numpy as np
from numpy.linalg import eig
import scipy
import matplotlib.pyplot as plt

# input: logs directory for const OS/APP/QPS
# for each log, find corr matrix eigenvalues + latency percentiles + total joules count
# output: dataframe indexed by log ID with latency, total joules count, and correlation matrix eigenvalues

EBBRT_COLS = ['i',
	'rx_desc',
	'rx_bytes',
	'tx_desc',
	'tx_bytes',
	'instructions',
	'cycles',
	'ref_cycles',
	'llc_miss',
	'c3',
	'c6',
	'c7',
	'joules',
	'timestamp']

LINUX_COLS = ['i',
              'rx_desc',
              'rx_bytes',
              'tx_desc',
              'tx_bytes',
              'instructions',
              'cycles',
              'ref_cycles',
              'llc_miss',
              'c1',
              'c1e',
              'c3',
              'c6',
              'c7',
              'joules',
              'timestamp']

def get_rdtsc(rdtsc_fname):
	df = pd.read_csv(rdtsc_fname, header=None, sep=' ')
	df[2] = df[2].astype(int)
	df[3] = df[3].astype(int)
	START_RDTSC = df[2].max()
	END_RDTSC = df[3].min()
	return START_RDTSC, END_RDTSC


# for every log file, log must be cleaned
def prep_df(fname, qps):
	loc_rdtsc = 'linux_mcd_rdtsc_0_0x1d00_135_' + qps
	tag = fname.split('.')[-1].split('_')
	print(tag)
	desc = '_'.join(np.delete(tag, [1]))
	print(desc)
	rdtsc_fname = f'{loc_rdtsc}/linux.mcd.rdtsc.{desc}'
	print(rdtsc_fname)
	START_RDTSC, END_RDTSC = get_rdtsc(rdtsc_fname)

	TIME_CONVERSION_khz = 1./(2899999*1000)
	JOULE_CONVERSION = 0.00001526
	df = pd.read_csv(fname, sep=" ", skiprows=1, index_col=0, names=LINUX_COLS)
	df = df[(df['timestamp'] >= START_RDTSC) & (df['timestamp'] <= END_RDTSC)]
	df = df[(df['joules']>0) & (df['instructions'] > 0) & (df['cycles'] > 0) & (df['ref_cycles'] > 0) & (df['llc_miss'] > 0)].copy()
	df['timestamp'] = df['timestamp'] - df['timestamp'].min()
	df['timestamp'] = df['timestamp'] * TIME_CONVERSION_khz
	df['joules'] = df['joules'] * JOULE_CONVERSION
	return df


# per log file
def get_eigenvalues(df):
	df_corr = df.drop('c6', axis=1).corr()	
	vals, vecs = eig(df_corr)
	eigenvals = {}
	i = 0
	for val in vals:
		eigenvals['eig_'+str(i)] = val
		i += 1
	return eigenvals

# per log file
def get_latencies(out_fname):
	with open(out_fname, 'r') as f:
		lines = f.readlines()
	header = lines[0].rstrip('\n').split()
	read_lat = lines[1].rstrip('\n').split()
	lat = {'read': dict(zip(header[1:], [float(y) for y in read_lat[1:]]))}
	
	return lat['read']

def get_energy(df):
	energy = df['joules']
	energy_sum = sum(energy)
	energy_avg = np.average(energy)
	energy_std = np.std(energy)
	eng = {'joules_sum': energy_sum, 'joules_avg': energy_avg, 'joules_std': energy_std}
	return eng

# parse single log file (1 core)
def parse_log_file(fname, qps, target):
	loc_out = 'linux_mcd_out_0_0x1d00_135_' + qps
	tag = fname.split('.')[-1].split('_')
	desc = '_'.join(np.delete(tag, [1]))
	expno = tag[0]
	df = prep_df(fname, qps)
	if target == "latency":
		out_fname = f'{loc_out}/linux.mcd.out.{desc}'
		ret = get_latencies(out_fname)
	else:
		if target == "energy":
			ret = get_energy(df)
			#df.drop('joules', axis=1)
	eig_vals = get_eigenvalues(df)
	return desc, ret, eig_vals

def parse_all_logs(dirname):
	print(dirname)
	qps = dirname.split('_')[len(dirname.split('_')) - 1]
	targets = {}
	eigenvals = {}
	descriptors = {'desc': []}
	for file in os.listdir(dirname):
		print(dirname + file)
		desc, target, eig_vals = parse_log_file(dirname + file, qps, target="energy")
		print(target)
		print(desc)
		descriptors['desc'].append(desc)
		if (len(targets.keys()) == 0) or (len(eigenvals.keys()) == 0):
			targets = {key: [] for key in target.keys()}
			eigenvals = {key: [] for key in eig_vals.keys()}
		for key in targets.keys():
			targets[key].append(target[key])
		for key in eigenvals.keys():
			eigenvals[key].append(eig_vals[key])
	target_eig = {**descriptors, **targets, **eigenvals}
	df = pd.DataFrame.from_dict(target_eig).set_index('desc')
	return df





