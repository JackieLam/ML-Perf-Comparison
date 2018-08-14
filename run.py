import sys
from XGBoostTest import XGBoostTest

'''sys.argv[1] - RESULT.CSV'''
'''sys.argv[2] - JSON LIST (seperated by ',')'''
t = XGBoostTest(sys.argv[1], sys.argv[2], num_round=20)

t.writeBestParams()
t.train_predict()

'''round 2: max_depth / min_child_weight'''
gridsearch_params1 = [
    (max_depth, min_child_weight)
    for max_depth in range(7,9)
    for min_child_weight in [i/10.0 for i in range(6,15)]
]
for max_depth, min_child_weight in gridsearch_params1:
	params = {'max_depth': max_depth, 'min_child_weight': min_child_weight}
	t.cross_validation(params)

t.writeBestParams()
t.train_predict()
