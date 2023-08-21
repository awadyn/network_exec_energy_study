import os
import sys
import pandas as pd
import numpy as np
from numpy.linalg import eig, eigvalsh
import scipy
import matplotlib.pyplot as plt

# input: logs directory for const OS/APP/QPS
# for each log, find corr matrix eigenvalues + latency percentiles + total joules count
# output: dataframe indexed by log ID with latency or total joules count, and correlation matrix eigenvalues

TIME_CONVERSION_khz = 1./(2899999*1000)
JOULE_CONVERSION = 0.00001526

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
	frdtsc = open(rdtsc_fname)
	START_RDTSC = 0
	END_RDTSC = 0
	for line in frdtsc:
		tmp = line.strip().split(' ')
		if int(tmp[2]) > START_RDTSC:
			START_RDTSC = int(tmp[2])
		if END_RDTSC == 0:
			END_RDTSC = int(tmp[3])
		elif END_RDTSC < int(tmp[3]):
			END_RDTSC = int(tmp[3])
	frdtsc.close()
	tdiff = round(float((END_RDTSC - START_RDTSC) * TIME_CONVERSION_khz), 2)
	return START_RDTSC, END_RDTSC

def get_eigenvalues(df, eigenval_counter = 0):
	df_corr = df.corr()	
	eigenvals = {}
	vals, vecs = eig(df_corr)
#	vals = eigvalsh(df_corr)
	for val in vals:
		if val <= 0:
			print('NEGATIVE EIGENVALUE ', 'eig_' + str(eigenval_counter), val)
		eigenvals['eig_'+str(eigenval_counter)] = val
		eigenval_counter += 1
	return eigenvals, eigenval_counter

def get_latencies(out_fname):
	with open(out_fname, 'r') as f:
		lines = f.readlines()
	header = lines[0].rstrip('\n').split()
	read_lat = lines[1].rstrip('\n').split()
	lat = {'read': dict(zip(header[1:], [float(y) for y in read_lat[1:]]))}
	
	return lat['read']

def get_energy(df):
	energy_sum = df['joules_diff'].sum()
	eng = {'joules_sum': energy_sum}
	return eng


def plot_histogram(df_diffs):
	return


# for every log file, log must be cleaned
def prep_df(fname, qps, dvfs):
#	fname = 'linux_mcd_dmesg_0_0xd00_135_200k/linux.mcd.dmesg.0_6_10_0xd00_135_200000'
	print(fname)

	# rdtsc files not tagged by core number
	tag = fname.split('.')[-1].split('_')
	desc = '_'.join(np.delete(tag, [1]))
	loc_rdtsc = 'linux_mcd_rdtsc_0_' + dvfs + '_135_' + qps
	rdtsc_fname = f'{loc_rdtsc}/linux.mcd.rdtsc.{desc}'
	START_RDTSC, END_RDTSC = get_rdtsc(rdtsc_fname)
 
	df = pd.read_csv(fname, sep=" ", skiprows=1, index_col=0, names=LINUX_COLS)
	df = df[(df['timestamp'] >= START_RDTSC) & (df['timestamp'] <= END_RDTSC)]
	df['timestamp'] = df['timestamp'] - df['timestamp'].min()
	df['timestamp'] = df['timestamp'] * TIME_CONVERSION_khz
	df['joules'] = df['joules'] * JOULE_CONVERSION

	df = df.drop(['c6', 'c1', 'c1e', 'c3', 'c7'], axis=1)
	# TODO remove, should not passively delete weird rows
	df.dropna(inplace=True)

	# NOTE this should never be the case
	df_neg = df[(df['joules'] < 0) | (df['instructions'] < 0) | (df['cycles'] < 0) | (df['ref_cycles'] < 0) | (df['llc_miss'] < 0)].copy()
	if df_neg.shape[0] > 0:
		print("UNEXPECTED NEGATIVE VAL IN ", fname)

	# non-continuous counter metrics: rx-bytes/desc, tx-bytes/desc
	df_no_diffs = df[['rx_bytes' , 'rx_desc', 'tx_bytes', 'tx_desc']]

	# continuous counter metrics: joules, inst, cycles, etc.
	df_diffs = df[['instructions', 'cycles', 'ref_cycles', 'llc_miss', 'joules', 'timestamp']].copy()
	df_diffs.columns = [f'{c}_diff' for c in df_diffs.columns]
	df_diffs = df_diffs[(df_diffs['joules_diff']>0) & (df_diffs['instructions_diff'] > 0) & (df_diffs['cycles_diff'] > 0) & (df_diffs['ref_cycles_diff'] > 0) & (df_diffs['llc_miss_diff'] > 0)].copy()

	# computing diffs
#	df_diffs = df_diffs.diff()
	tmp = df_diffs.diff().copy()
	df_diffs_neg = tmp[(tmp['joules_diff'] < 0) | (tmp['instructions_diff'] < 0) | (tmp['cycles_diff'] < 0) | (tmp['ref_cycles_diff'] < 0) | (tmp['llc_miss_diff'] < 0)]
	if df_diffs_neg.shape[0] > 0:
		print('NEGATIVE DIFFS IN FILE ', fname)
		print(df_diffs_neg)
		for i,j in df_diffs_neg.iterrows():
			prev = df_diffs.shift(1).loc[i]
			cur = df_diffs.loc[i]
			print('previous row: ', list(prev))
			print('current row: ', list(cur))
			if (tmp.loc[i]['joules_diff'] < 0) & (tmp.loc[i]['timestamp_diff'] >= 0.001):
				print('NEGATIVE JOULES DIFFS AT ', i)
				tmp.loc[i, ['joules_diff']] = (2**32 - 1) * JOULE_CONVERSION - prev + cur 
			print('new joules diff: ', tmp.loc[i]['joules_diff'])
	df_diffs = tmp.copy()	

	df_diffs = df_diffs[(df_diffs['joules_diff'] >= 0) & (df_diffs['instructions_diff'] >= 0) & (df_diffs['cycles_diff'] >= 0) & (df_diffs['ref_cycles_diff'] >= 0) & (df_diffs['llc_miss_diff'] >= 0)]

	# slow for loop for diffs
#	tmp = df_diffs.copy()
#	first_row = True
#	for i,j in tmp.iterrows():
#		if first_row:
#			first_row = False
#			continue
#		for col in df_diffs.columns:
#			cur = int(df_diffs.loc[i][col])
#			prev = int(df_diffs.shift(1).loc[i][col])
#			if cur >= prev:
#				tmp.loc[i, [col]] = cur - prev
#			else:
#				tmp.loc[i, [col]] = sys.maxsize - prev + cur
#				if col == 'joules_diff':
#					print(prev)
#					print(cur)
#					print(tmp.loc[i, [col]])
#	for i, j in df_diffs.iterrows():
#		for col in df_diffs.columns:
#			tmp.loc[i, [col]] = 0
#		break
#	df_diffs = tmp.copy()

	# SCHEME 1
	return df_no_diffs, df_diffs
	# SCHEME 2
	#df_full = pd.concat([df, df_diffs], axis=1)
	#df_full.dropna(inplace=True)
	#return df_full


# parse single log file (1 core)
def parse_log_file(fname, qps, dvfs, target):
	tag = fname.split('.')[-1].split('_')
	# maintaining core number in desc
	desc = '_'.join(tag)
	expno = tag[0]

	# SCHEME 1
	df_no_diffs, df_diffs = prep_df(fname, qps, dvfs)

	plot_histogram(df_diffs)

	# SCHEME 2
#	df = prep_df(fname, qps, dvfs)

	# GET TARGET
	if target == "latency":
		desc = '_'.join(np.delete(tag, [1]))
		loc_out = 'linux_mcd_out_0_' + dvfs + '_135_' + qps
		out_fname = f'{loc_out}/linux.mcd.out.{desc}'
		ret = get_latencies(out_fname)
	else:
		if target == "energy":
			ret = get_energy(df_diffs)
			# ensure energy values do not leak into correlation matrices
			df_diffs.drop('joules_diff', axis=1)

	# GET EIGENVALS
	# SCHEME 1
	eigenval_counter = 0
	eigenvals, eigenval_counter = get_eigenvalues(df_no_diffs, eigenval_counter)
	eigenvals_diffs, eigenval_counter = get_eigenvalues(df_diffs, eigenval_counter)
	all_eigenvals = {**eigenvals, **eigenvals_diffs}
	# SCHEME 2
#	df = prep_df(fname, qps, dvfs)
#	eigenvals = get_eigenvalues(df)
#	return desc, ret, all_eigenvals, df

	return desc, ret, all_eigenvals, df_no_diffs, df_diffs


# each directory represents logs with const qps, dvfs, rapl, and run number
# itr-delay values and core numbers vary within a directory
def parse_all_logs(dirname, target_reward):
	qps = dirname.split('_')[len(dirname.split('_')) - 1][:-1]
	dvfs = dirname.split('_')[4]
	targets = {}
	eigenvals = {}
	descriptors = {'desc': []}
	for file in os.listdir(dirname):
		desc, target, eig_vals, df_no_diffs, df_diffs = parse_log_file(dirname + file, qps, dvfs, target_reward)
		print(target)
		descriptors['desc'].append(desc)
		if (len(targets.keys()) == 0) or (len(eigenvals.keys()) == 0):
			targets = {key: [] for key in target.keys()}
			eigenvals = {key: [] for key in eig_vals.keys()}
		for key in targets.keys():
			targets[key].append(target[key])
		for key in eigenvals.keys():
			eigenvals[key].append(eig_vals[key])
#		break
	target_eig = {**descriptors, **targets, **eigenvals}
	df = pd.DataFrame.from_dict(target_eig).set_index('desc')
	outfile = '../new_eigenval_dfs/' + target_reward + '_eig_' + dvfs + '_' + qps + '.csv'
	df.to_csv(outfile)
	return df, df_no_diffs, df_diffs




