def prepare_data(workload='mcd', fix_rapl=135):
    df_comb, _, _ = read_agg_data.start_analysis(workload) #DATA                                                  
    df_comb['dvfs'] = df_comb['dvfs'].apply(lambda x: int(x, base=16))
    df_comb = df_comb[(df_comb['itr']!=1) | (df_comb['dvfs']!=65535)] #filter out linux dynamic    
    
    df_dict = {}
    for sys in ['linux_tuned', 'ebbrt_tuned']:
        df = df_comb[(df_comb['sys']==sys)].copy()
        
        for conf in config[workload]:
            if conf is not None:
                df_lookup = df[df[conf[0]]==conf[1]]
            else:
                df_lookup = df.copy()
                                
            INDEX_COLS = [] #what variables to search over                                                            
            uniq_val_dict = {} #range for each variable                                                               

            for colname in ['itr', 'dvfs', 'rapl']:
                uniq_vals = np.sort(df_lookup[colname].unique())

                if fix_rapl and colname=='rapl':
                    df_lookup = df_lookup[df_lookup['rapl']==fix_rapl].copy()
                    continue
    
                if len(uniq_vals) > 1:
                    INDEX_COLS.append(colname)
                    uniq_val_dict[colname] = uniq_vals #all unique values                                 
                
            df_lookup.set_index(INDEX_COLS, inplace=True) #df for fixed workload, for fixed OS                               
            
            df_dict[(sys, conf[1])] = (df_lookup, INDEX_COLS, uniq_val_dict)
            
    return df_dict

