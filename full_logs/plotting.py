#energy_list = []
#sort energy list
#log -> df corr plot -> filename is labeled by energy tag and latency tag -> energy0 (min energy), energy1 (next min), ...
#lat0 (min 99th lat), lat1 (next min 99th lat), ...



import pandas as pd
import numpy as np
import scipy
import matplotlib.pyplot as plt

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


def prep_df(fname):
	loc_rdtsc = '../linux_mcd_rdtsc_0_0xd00_135_200k'
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


def plot_pdf(df):
	df_tmp = df.sort_values()
	mean = np.mean(df_tmp)
	std = np.std(df_tmp)
	pdf = stats.norm.pdf(df_tmp, mean, std)
	plt.plot(df_tmp, pdf)
	plt.show()

def plot_timeseries(df, col):
	fig, ax = plt.subplots()
	diff_df = df[col].diff()
	time = df['timestamp']
	ax.plot(time[1000:], diff_df[1000:])
	fig.show()

