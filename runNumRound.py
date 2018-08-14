import sys
from XGBoostTest import XGBoostTest

'''sys.argv[1] - RESULT.CSV'''
'''sys.argv[2] - JSON LIST (seperated by ',')'''
t = XGBoostTest(sys.argv[1], sys.argv[2], num_round=20)

for n in [i*5 for i in range(1,10)]:
	params = {'n_estimators': n}
	t.train_predict(params)

t.tearDownClass()