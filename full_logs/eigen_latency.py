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
def prep_df(fname):
	loc_rdtsc = 'linux_mcd_rdtsc_0_0x1d00_135_200k'
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
	
	return lat


# parse single log file (1 core)
def parse_log_file(fname):
	loc_out = 'linux_mcd_out_0_0x1d00_135_200k/'
	tag = fname.split('.')[-1].split('_')
	print(tag)
	desc = '_'.join(np.delete(tag, [1]))
	print(desc)
	expno = tag[0]
	out_fname = f'{loc_out}/linux.mcd.out.{desc}'
	lat = get_latencies(out_fname)
	df = prep_df(fname)
	eig_vals = get_eigenvalues(df)
	return desc, lat['read'], eig_vals

def parse_all_logs(dirname):
	latencies = {}
	eigenvals = {}
	descriptors = {'desc': []}
	for file in os.listdir(dirname):
		print(dirname + file)
		desc, lat, eig_vals = parse_log_file(dirname + file)
		descriptors['desc'].append(desc)
		if (len(latencies.keys()) == 0) or (len(eigenvals.keys()) == 0):
			latencies = {key: [] for key in lat.keys()}
			eigenvals = {key: [] for key in eig_vals.keys()}
		for key in latencies.keys():
			latencies[key].append(lat[key])
		for key in eigenvals.keys():
			eigenvals[key].append(eig_vals[key])
	lat_eig = {**descriptors, **latencies, **eigenvals}
	df = pd.DataFrame.from_dict(lat_eig).set_index('desc')
	print(df)
	df.to_csv(dirname + "lat_eig.csv")




