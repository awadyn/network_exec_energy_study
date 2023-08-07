import sys
import numpy as np
import itertools

from sklearn.linear_model import LinearRegression

from ax.service.managed_loop import optimize
from ax.plot.trace import optimization_trace_single_method
from ax.utils.notebook.plotting import render, init_notebook_plotting
init_notebook_plotting()

import plotly.graph_objects as go

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


####################################
# BAD: temporary missing keys hack
predictors = ['itr', 'dvfs']
X = df[predictors]
y = df['joules_sum_mean']
z = df['read_99th_mean']
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
		joules = np.median(np.sort(list(runs['joules_sum_mean'])))
		rth = np.median(np.sort(list(runs['read_99th_mean'])))
		if rth > lat_target:
			joules = joules * (rth - lat_target + 1)
	return joules, rth


def mcd_eval(params):
	itr = params['itr']
	dvfs = params['dvfs']
	joules, rth = get_joules_latency(itr, dvfs)
	print(f'itr = {itr},  dvfs = {dvfs},  joules = {joules}, rth = {rth}')
	print()
	itrs_visited.append(itr)
	dvfss_visited.append(dvfs)
	res = {'mcd': (joules, 0.0)}
	return res

best_params, values, exp, model = optimize(parameters=search_space, evaluation_function = lambda params: mcd_eval(params), experiment_name=f'mcd_discrete', objective_name='mcd', minimize=True, total_trials = N_trials)

min_joules = min(list(df['joules_sum_mean'].values))
target_best_params = df.loc[df['joules_sum_mean'] == min_joules][['itr', 'dvfs', 'joules_sum_mean']]
print('target best params:')
print(target_best_params)
print()
print(f'best params: {best_params}')
print(f'values (mean + covariance): {values}')
print(f'exp: {exp}')
print(f'model: {model}')

best_objectives = np.array([[trial.objective_mean for trial in exp.trials.values()]])
best_objective_plot = optimization_trace_single_method(
	y = np.minimum.accumulate(best_objectives, axis=1),
	optimum = min_joules,
	title = "Model Performance vs. # Iterations",
	ylabel = "Energy",
)
print(best_objective_plot)


# fig = go.Figure()

# plot_dvfss = []
# plot_itrs = []
# #plot_rewards = []
# for (i, d) in itertools.product(itr_vals, dvfs_vals):
# 	plot_dvfss.append(d)
# 	plot_itrs.append(i)
# #	plot_rewards.append(env.reward_space[(i,d)])
# fig.add_trace(go.Scatter(x=plot_itrs, y=plot_dvfss, mode='markers'))
# fig.add_trace(go.Scatter(x=[list(target_best_params['itr'])[0]], y=[list(target_best_params['dvfs'])[0]], marker_size=20, marker_color = "yellow"))	

# fig.add_trace(go.Scatter(x=itrs_visited, y=dvfss_visited, marker= dict(size=10,symbol= "arrow-bar-up", angleref="previous")))
# fig.show()



