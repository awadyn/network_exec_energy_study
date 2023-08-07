from config import *
from utils import *
import pandas as pd
import numpy as np
import os

def prepare_scan_all_data(df):
    if 'msg' in df.columns: #netpipe
        COLS = ['sys', 'msg', 'itr', 'dvfs', 'rapl']
    elif 'target_QPS' in df.columns:
        COLS = ['sys', 'target_QPS', 'itr', 'dvfs', 'rapl']
    else: #nodejs
        COLS = ['sys', 'itr', 'dvfs', 'rapl']    

    df_mean = df.groupby(COLS).mean()
    df_std = df.groupby(COLS).std()
    
    df_mean.columns = [f'{c}_mean' for c in df_mean.columns]
    df_std.columns = [f'{c}_std' for c in df_std.columns]

    df_comb = pd.concat([df_mean, df_std], axis=1)

    return df_comb


def identify_outliers(df, dfr, RATIO_THRESH=0.03):
    '''df -> grouped by data 
    dfr -> data for individual runs
    '''

    df = df.copy()

    df.fillna(0, inplace=True) #configs with 1 run have std dev = 0

    df_highstd = df[df.joules_std / df.joules_mean > RATIO_THRESH] #step 1

    outlier_list = []

    for idx, row in df_highstd.iterrows():
        sys = row['sys']
        itr = row['itr']
        dvfs = row['dvfs']
        rapl = row['rapl']

        if 'msg' in row: #netpipe
            msg = row['msg']

            df_bad = dfr[(dfr.sys==sys) & (dfr.itr==itr) & (dfr.dvfs==dvfs) & (dfr.rapl==rapl) & (dfr.msg==msg)]

            bad_row = df_bad[df_bad.joules==df_bad.joules.min()].iloc[0] #the outlier doesn't have to be the minimum joule one

            outlier_list.append((sys, bad_row['i'], itr, dvfs, rapl, msg)) #can ignore "i" to focus on bad config

        elif 'QPS' in row: #memcached
            qps = row['QPS']

            df_bad = dfr[(dfr.sys==sys) & (dfr.itr==itr) & (dfr.dvfs==dvfs) & (dfr.rapl==rapl) & (dfr.QPS==qps)]

            bad_row = df_bad[df_bad.joules==df_bad.joules.min()].iloc[0] #the outlier doesn't have to be the minimum joule one

            outlier_list.append((sys, bad_row['i'], itr, dvfs, rapl, qps)) #can ignore "i" to focus on bad config

        else:
            df_bad = dfr[(dfr.sys==sys) & (dfr.itr==itr) & (dfr.dvfs==dvfs) & (dfr.rapl==rapl)]

            bad_row = df_bad[df_bad.joules==df_bad.joules.min()].iloc[0] #the outlier doesn't have to be the minimum joule one

            outlier_list.append((sys, bad_row['i'], itr, dvfs, rapl)) #can ignore "i" to focus on bad config

    return outlier_list



def start_analysis(workload='mcd', drop_outliers=False, **kwargs):

    if 'scale_requests' not in kwargs:
        kwargs['scale_requests'] = True
    df_comb, df, outlier_list = start_mcd_analysis(drop_outliers=drop_outliers, scale_requests=kwargs['scale_requests'])

    return df_comb, df, outlier_list


def start_mcd_analysis(drop_outliers=False, scale_requests=True):
    df = pd.read_csv(os.path.join(Locations.aggregate_files_loc, 'mcd_combined.csv'), sep=' ')


    #drop time < 30s
    print('Dropping rows with time <= 29')
    print(f'Before: {df.shape[0]}')
    df = df[df['time']>19].copy()
    print(f'After: {df.shape[0]}\n')

    #drop 99th percentile > 500 latencies
    print('Dropping rows with read_99th latency > 500')
    print(f'Before: {df.shape[0]}')
    df = df[df['read_99th'] <= 500].copy()
    print(f'After: {df.shape[0]}\n')

    def scale_to_requests(d):
        print("Scaling to 5 million requests")
        COLS_TO_SCALE = ['rx_desc',
                         'rx_bytes',
                         'tx_desc',
                         'tx_bytes',
                         'time',
                         'joules',
                         'instructions',
                         'cycles',
                         'ref_cycles',
                         'llc_miss',
                         'c1',
                         'c1e',
                         'c3',
                         'c6',
                         'c7',
                         'num_interrupts'
                         ]

        SCALE_FACTOR = 5000000. / (d['measure_QPS']*d['time'])

        for c in COLS_TO_SCALE:
            # d[c] = pd.to_numeric(d[c], errors='coerce') * SCALE_FACTOR
            d[c] = d[c] * SCALE_FACTOR

        return d

    if scale_requests:
        df = scale_to_requests(df)


    df['edp'] = 0.5 * (df['joules'] * df['time'])
    #df['eput'] = df['QPS'] * df['time'] / df['joules']

    dfr = df.copy() #raw data
    df = prepare_scan_all_data(dfr) #grouped by data
    df.reset_index(inplace=True)

    outlier_list = identify_outliers(df, dfr)
    if drop_outliers:    
        print(f'Dropping {len(outlier_list)} outlier rows')

        print(f'Before: {dfr.shape[0]}')
        dfr = filter_outliers(outlier_list, dfr)
        print(f'After: {dfr.shape[0]}')

        df = prepare_scan_all_data(dfr) #grouped by data    
        df.reset_index(inplace=True)

    return df, dfr, outlier_list

