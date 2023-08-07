import sys
import numpy as np
import itertools
import plotly.graph_objects as go

# TODO remove after finalizing missing keys solution
from sklearn.linear_model import LinearRegression

# single objective (energy) optimizer
from ax.service.managed_loop import optimize
# multi objective (energy, latency) optimizer
from ax.service.ax_client import AxClient 
from ax.service.utils.instantiation import ObjectiveProperties
# plot tools for multi-objective optimization
# TODO

import helpers

logs_file = sys.argv[1]
N_trials = int(sys.argv[2])

# preparing dataframe
# 1. grouping per-core logs of individual cores and
#    filtering out the outlier runs
df, df_raw, outlier_list = helpers.init_df_simple(logs_file)
# 2. filtering out itr and dvfs extremes
df = df[(df['itr']!=1) | (df['dvfs']!=65535)]

# preparing search space
itr_vals = list(set(list(df['itr'])))
dvfs_vals = list(set(list(df['dvfs'])))
itr_dict = {'is_ordered': True, 'log_scale': False, 'name': 'itr', 'type': 'choice', 'value_type': 'float', 'values': itr_vals}
dvfs_dict = {'is_ordered': True, 'log_scale': False, 'name': 'dvfs', 'type': 'choice', 'value_type': 'float', 'values': dvfs_vals}
search_space = [itr_dict, dvfs_dict]

print(df)
print(search_space)

lat_target = 500.0
itrs_visited = []
dvfss_visited = []


# multi objective bayesian optimization
ax_client = AxClient()
ax_client.create_experiment(
	name = "mcd_multi_obj_bayesopt"
)


