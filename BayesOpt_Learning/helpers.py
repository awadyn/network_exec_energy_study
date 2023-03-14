import os, sys
import numpy as np
import re
import pandas as pd
import torch


def init_df_simple(logs_file, non_norm_cols):
	df = pd.read_csv(logs_file, sep = ',')
	itrs = []
	dvfss = []
	qpss = []
	runs = []
	cores = []	
	# adding itr, dvfs, and qps columns to df
	for i, v in df.iterrows():
		f = v['fname']
		run = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(1))
		core = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(2))
		itr = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(3))
		dvfs = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(4), base=16)
		qps = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(6))
		itrs.append(itr)
		dvfss.append(dvfs)
		qpss.append(qps)
		runs.append(run)
		cores.append(core)
	df['itr'] = itrs
	df['dvfs'] = dvfss
	df['qps'] = qpss
	df['run'] = runs
	df['core'] = cores

	if non_norm_cols != None:	
		for col in df.drop(non_norm_cols, axis = 1).columns:
			# normalizing relative to train set:
			train_max = df[col].max()
			train_min = df[col].min()
			# sanity check
			if (train_max - train_min == 0):
				continue
			df[col] = (df[col] - train_min) / (train_max - train_min)
			test_df[col] = (test_df[col] - train_min) / (train_max - train_min)

	return df



def init_df(logs_dir, non_norm_cols):
	df = pd.DataFrame()
	test_df = pd.DataFrame()
#	qps_df_dict = {}

	# create per-QPS dataframes
	for qps_file in os.listdir(logs_dir):
		filename = logs_dir + qps_file
		qps_df = pd.read_csv(filename, sep = ',')
		itrs = []
		dvfss = []
		qpss = []
		runs = []
		cores = []	
		# adding itr, dvfs, and qps columns to df
		for i, v in qps_df.iterrows():
			f = v['fname']
			run = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(1))
			core = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(2))
			itr = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(3))
			dvfs = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(4), base=16)
			qps = int(re.search(r'linux\.mcd\.dmesg\.(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)\.csv', f).group(6))
			itrs.append(itr)
			dvfss.append(dvfs)
			qpss.append(qps)
			runs.append(run)
			cores.append(core)
		qps_df['itr'] = itrs
		qps_df['dvfs'] = dvfss
		qps_df['qps'] = qpss
		qps_df['run'] = runs
		qps_df['core'] = cores
	
		# testing correlation between train and test data
		df1 = pd.DataFrame()	# train set runs
		df2 = pd.DataFrame()	# test set runs

		# splitting df into dfs of independent runs
		for i,r in qps_df.iterrows():
			df_row = pd.DataFrame([r])
			if (r['run'] in [0, 2, 4]):
				df1 = pd.concat([df1, df_row], axis=0, ignore_index=True)
			else:

				df2 = pd.concat([df2, df_row], axis=0, ignore_index=True)
		# splitting df into dfs of independent qpses
		df = pd.concat([df, df1.loc[df1['qps'] == 200000]], ignore_index=True)
		df = pd.concat([df, df1.loc[df1['qps'] == 600000]], ignore_index=True)
		test_df = pd.concat([test_df, df2.loc[df2['qps'] == 400000]], ignore_index=True)
		test_df = pd.concat([test_df, df2.loc[df2['qps'] == 750000]], ignore_index=True)
	
		#qps_df_dict[str(qps)] = qps_df
	
	for col in df.drop(non_norm_cols, axis = 1).columns:
		# normalizing relative to train set:
		train_max = df[col].max()
		train_min = df[col].min()
		# sanity check
		if (train_max - train_min == 0):
			continue
		df[col] = (df[col] - train_min) / (train_max - train_min)
		test_df[col] = (test_df[col] - train_min) / (train_max - train_min)

	return df, test_df


def init_dataset(df, test_df, state_cols, verify_qps_rmses):
	state_df = df[state_cols]
	label_df = df['qps']
	test_state_df = test_df[state_cols]
	test_label_df = test_df['qps']
	
	features = state_df.values
	features = torch.from_numpy(features).float()

	labels = label_df.values
	labels = torch.from_numpy(labels).float()

	test_features = test_state_df.values
	test_features = torch.from_numpy(test_features).float()

	test_labels = test_label_df.values
	test_labels = torch.from_numpy(test_labels).float()
	
	if verify_qps_rmses:
		train_qpses = set(label_df.values)
		test_qpses = set(test_label_df.values)
		per_qps_features = {}
		per_qps_labels = {}
		per_qps_test_features = {}
		per_qps_test_labels = {}
		for qps in train_qpses:
			per_qps_features[qps] = state_df.loc[label_df == qps].values
			per_qps_features[qps] = torch.from_numpy(per_qps_features[qps]).float()	
			per_qps_labels[qps] = label_df.loc[label_df == qps].values
			per_qps_labels[qps] = torch.from_numpy(per_qps_labels[qps]).float()
		for qps in test_qpses:
			per_qps_test_features[qps] = test_state_df.loc[test_label_df == qps].values
			per_qps_test_features[qps] = torch.from_numpy(per_qps_test_features[qps]).float()	
			per_qps_test_labels[qps] = test_label_df.loc[test_label_df == qps].values
			per_qps_test_labels[qps] = torch.from_numpy(per_qps_test_labels[qps]).float()
	
	if verify_qps_rmses:
		return features, labels, test_features, test_labels, per_qps_features, per_qps_labels, per_qps_test_features, per_qps_test_labels
	else:
		return features, labels, test_features, test_labels	






