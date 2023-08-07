import pandas as pd
import numpy as np
import torch

from ax import *
from ax.core.metric import Metric
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.service.utils.report_utils import exp_to_df
from ax.runners.synthetic import SyntheticRunner

from ax.modelbridge.factory import get_MOO_EHVI, get_MOO_PAREGO

from ax.modelbridge.modelbridge_utils import observed_hypervolume


# sample 2 objective problem
from botorch.test_functions.multi_objective import BraninCurrin
branin_currin = BraninCurrin(negate=True).to(
	dtype=torch.double,
)


# search space initialization
x1 = RangeParameter(name="x1", lower=0, upper=1, parameter_type=ParameterType.FLOAT)
x2 = RangeParameter(name="x2", lower=0, upper=1, parameter_type=ParameterType.FLOAT)
search_space = SearchSpace(
	parameters=[x1, x2]
)
print(x1, x2)
print(search_space)


# multi-objective optimization initialization
class MetricA(NoisyFunctionMetric):
	def f(self, x:np.ndarray) -> float:
		return float(branin_currin(torch.tensor(x))[0])

class MetricB(NoisyFunctionMetric):
	def f(self, x:np.ndarray) -> float:
		return float(branin_currin(torch.tensor(x))[1])

metric_a = MetricA("a", ["x1","x2"], noise_sd=0.0, lower_is_better=False)
metric_b = MetricB("b", ["x1","x2"], noise_sd=0.0, lower_is_better=False)

mo = MultiObjective(
	objectives=[Objective(metric=metric_a), Objective(metric=metric_b)]
)

objective_thresholds = [
	ObjectiveThreshold(metric=metric, bound=val, relative=False) for metric,val in zip(mo.metrics, branin_currin.ref_point)
]

optimization_config = MultiObjectiveOptimizationConfig(
	objective = mo,
	objective_thresholds = objective_thresholds,
)












