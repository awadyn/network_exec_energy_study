def missing_keys(df):
    d = df[2]
    df = df[0]
    
    missing = []
    
    for i in d['itr']:
        for j in d['dvfs']:
            try:
                df.loc[i,j]['joules_mean']
            except:
                missing.append([i,j])
                               
    return missing

def list_missing_keys(df_dict):
    for k in df_dict:

        missing = missing_keys(df_dict[k])
        print(k)
        print(missing, '\n')
