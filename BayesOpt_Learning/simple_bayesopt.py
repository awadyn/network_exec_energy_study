import sys
import numpy as np

from sklearn.linear_model import LinearRegression
from ax.service.managed_loop import optimize

import helpers

logs_file = sys.argv[1]
N_trials = int(sys.argv[2])

df = helpers.init_df_simple(logs_file, None)
itr_vals = list(set(list(df['itr'])))
dvfs_vals = list(set(list(df['dvfs'])))
itr_dict = {'is_ordered': True, 'log_scale': False, 'name': 'itr', 'type': 'choice', 'value_type': 'int', 'values': itr_vals}
dvfs_dict = {'is_ordered': True, 'log_scale': False, 'name': 'dvfs', 'type': 'choice', 'value_type': 'int', 'values': dvfs_vals}
search_space = [itr_dict, dvfs_dict]
lat_target = 500.0

####################################
# BAD: temporary missing keys hack
predictors = ['itr', 'dvfs']
X = df[predictors]
y = df['joules_sum']
z = df['read_99th']
lm = LinearRegression()
lm2 = LinearRegression()
model = lm.fit(X, y)
model2 = lm2.fit(X, z)
####################################

def get_joules_latency(itr, dvfs):
	global df
	global model
	runs = df.loc[df['itr']==itr].loc[df['dvfs']==dvfs]
	if runs.empty:
		print(f'KEY ERROR : ITR = {itr}    DVFS = {dvfs}')
		joules = model.predict([[itr, dvfs]]).item()
		rth = model2.predict([[itr, dvfs]]).item()
		print(f'Running regression model... predicting joules = {joules}')
	else:
		joules = np.median(np.sort(list(runs['joules_sum'])))
		rth = np.median(np.sort(list(runs['read_99th'])))
		if rth > lat_target:
			joules = joules * (rth - lat_target + 1)
	return joules, rth


def mcd_eval(params):
	itr = params['itr']
	dvfs = params['dvfs']
	joules, rth = get_joules_latency(itr, dvfs)
	print(f'itr = {itr},  dvfs = {dvfs},  joules = {joules}, rth = {rth}')
	print()
	res = {'mcd': (joules, 0.0)}
	return res

best_params, values, exp, model = optimize(parameters=search_space, evaluation_function = lambda params: mcd_eval(params), experiment_name=f'mcd_discrete', objective_name='mcd', minimize=True, total_trials = N_trials)

min_joules = min(list(df['joules_sum'].values))
target_best_params = df.loc[df['joules_sum'] == min_joules][['itr', 'dvfs', 'joules_sum']]
print('target best params:')
print(target_best_params)
print()
print(f'best params: {best_params}')
print(f'values: {values}')
print(f'exp: {exp}')
print(f'model: {model}')


