# Dataset: CAT & Num
# Task 1.1: train time/mem use/predict time/model time for 
#         'n_estimators' 20, 40, ..., 100, 200, ..., 500 (100K)
# Task 1.2: train time for 'max_depth' 10, 20, 30, 40, 50
# Task 1.3: train time for 'min_child_weight'
# Task 1.4: multi-threading (100K) train time: 1, 28, 56, 112 CPU
# Task 1.5: importance of 100 and 200 trees (100K)
# Task 1.6: train time/mem use/predict time for 100K, 200K and 500K (100 trees)
# Task 1.7: model loading time for 20, 40, 60, 80, 100 trees

# Dataset: Numerical
import sys
from XGBoostTest import XGBoostTest
# sys.argv[1] - RESULT.CSV
# sys.argv[2] - JSON LIST (seperated by ',')
output_cat = "result_airline_cat.csv"
jsonfile_cat = "airline_cat_100K.json"
output_num = "result_airline_num.csv"
jsonfile_num = "airline_num.json"

out_json_pair = {output_num: jsonfile_num, \
				 output_cat: jsonfile_cat}

for outputfile, jsonfile in out_json_pair.items():
	print "%s -- %s" % (outputfile, jsonfile)
	t100 = XGBoostTest(outputfile=outputfile, 
					   jsonfile=jsonfile, num_round=100)
	# Task 1.1
	for n in [i*20 for i in range(1,6)]:
		params = {'n_estimators': n}
		t100.train_predict(params, predict=True, savemodel=True)
	for n in [i*100 for i in range(2,6)]:
		params = {'n_estimators': n}
		t100.train_predict(params, predict=True, savemodel=True)

	# Task 1.2
	for n in [i*10 for i in range(1,11)]:
		params = {'max_depth': n} # max_depth: (100K) set to 100 still fast (9 seconds)
		t100.train_predict(params, predict=True, savemodel=True)
	# question: what's the actual max_depth of a tree?

	# Task 1.3
	for n in range(1,8):
		params = {'min_child_weight': n} # do not have much difference on (100K)
		t100.train_predict(params, predict=True, savemodel=True)

	# Task 1.4
	for n in [1, 28, 56, 112]:
		params = {'n_jobs': n}
		t100.train_predict(params, predict=True, savemodel=True)

	# Task 1.5
	for n in [100, 200]:
		params = {'n_estimators': n}
		t100.train_predict(params, predict=True, savemodel=True, getscore=True)

	t100 = None

# Task 1.6
t200 = XGBoostTest(outputfile=output_cat, 
				   jsonfile="airline_cat_200K.json", num_round=100)
params = {'dataset': '200K'}
t200.train_predict(params, predict=True, savemodel=True)
t200 = None 
t500 = XGBoostTest(outputfile=output_cat, 
				   jsonfile="airline_cat_500K.json", num_round=100)
params = {'dataset': '500K'}
t500.train_predict(params, predict=True, savemodel=True)


# Email Alert
t500.tearDownClass()