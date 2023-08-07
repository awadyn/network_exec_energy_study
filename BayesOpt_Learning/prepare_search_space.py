def prepare_search_space(df, var_type='discrete'):
    if var_type != 'discrete' and var_type != 'range':
        raise ValueError('var_type should be "discrete" or "range"')

    idx = df.index
    search_space = []
    
    for i, name in enumerate(idx.names):
        if var_type=='range':
            s = {'name': name,
                 'type': 'range',
                 'bounds': [np.min([val[i] for val in idx]), np.max([val[i] for val in idx])],
                 'value_type': 'int',
                 'log_scale': False
                }
            search_space.append(s)
        
        elif var_type=='discrete':
            s = {'name': name,
                 'type': 'choice',
                 'values': list(np.unique([val[i] for val in idx])),
                 'value_type': 'float',
                 'log_scale': False,
                 'is_ordered': True,
                 #'sort_values': True
                }
            search_space.append(s)
                        
    return search_space

