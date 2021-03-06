import os, sys, csv, psutil, functools, math, time, json, threading, smtplib
import unittest
from sys import stdout, argv
from palLib import Name, Ignore, MemoryMeasure, Timing
import xgboost as xgb
from sklearn.model_selection import KFold
from sklearn import preprocessing
import numpy as np
np.set_printoptions(threshold=np.inf)
import pandas as pd
from collections import OrderedDict
from scipy.sparse import csr_matrix, isspmatrix
from PythonMemoryMeasure import PythonMemoryMeasure
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from CSVHelper import readFromParamFile, writeResultCSV
from PythonPerformanceTest import PythonPerformanceTest

PARAM_CNT = -1

'''self variables: should store all the best parameters'''
class XGBoostTest(PythonPerformanceTest):
    def __init__(self, outputfile, jsonfile, num_round=None):
        super(XGBoostTest, self).__init__(outputfile, jsonfile)
        num_round = 100 if num_round is None else num_round
        self.default_params = {'silent':1, 'objective':'binary:logistic', 'booster':'gbtree', 'eval_metric':['auc','error','logloss'], 
              'n_estimators': num_round, 'max_depth': 6, 'min_child_weight': 1.0, 'gamma': 0.0, 'subsample': 1.0,
              'colsample_bytree': 1.0, 'reg_alpha': 0.0, 'eta': 0.3}
        self.best_params = self.default_params
        self.setUp() # Load Data
        writeResultCSV(self.RESULT_CSV, [], ['Mode','MemUse','TrainTime','PredictTime',
                                             'SaveModelTime','TestErr','TestAUC','TestObj'])

    def setUp(self):
        super(XGBoostTest, self).setUp(dataType='DMatrix') # Load data 
        eval_set = xgb.cv(self.default_params, self.dtrain, 
                num_boost_round=self.default_params['n_estimators'], nfold=5,
                metrics={'error', 'auc', 'logloss'}, seed=0)
        self.bestErr = eval_set['test-error-mean'].iloc[-1] # bestErr: default params

    def train_predict(self, params=None, predict=False, 
                            savemodel=False, getscore=False):
        if params == None: #params: None then train using best param
            params = self.best_params
            tpparams = {"self.best_params": "..."}
        else:
            tpparams = params.copy()
            for param, value in self.default_params.items():
                if param not in params:
                    params[param] = value
        # Specially deal with num of booster
        num_round = params['n_estimators'] if 'n_estimators' in params else self.default_params['n_estimators']

        mem = PythonMemoryMeasure()
        memThread = threading.Thread(target = mem)
        try:
            memThread.start()
            evals = {}
            watchlist = [(self.dtest, 'eval'), (self.dtrain, 'train')]
            stTrain = time.time()
            bst = xgb.train(params, self.dtrain, num_round, watchlist, evals_result=evals, verbose_eval = 0) # train and predict
            etTrain = time.time()
        finally:
            mem.stop = True
            memThread.join()
        trainingTime = str(etTrain - stTrain)
        totalMem = self.dataSetMem + mem.usedMem

        # Do Prediction
        predictTime = -1
        if predict:
            stPredict = time.time()
            preds = bst.predict(self.dtest)
            etPredict = time.time()
            predictTime = str(etPredict - stPredict)

        # Model Saving
        saveModelTime = -1
        if savemodel:
            modelName = "/XGBoost/model/xgb"
            for key, value in tpparams.items():
                modelName += "_%s_%s" % (key, value)
            modelName += ".model"
            stModel = time.time()
            bst.save_model(modelName)
            etModel = time.time()
            saveModelTime = str(etModel - stModel)

        # Get Importance (Score)
        if getscore:
            rows = [['IMPORTANCE WEIGHT']]
            imp_weight = bst.get_score(importance_type='weight') # 'gain', 'cover' or 'weight'
            imp_weight = sorted(imp_weight.items(), key=lambda kv: kv[1], reverse=True)
            print type(imp_weight)
            print imp_weight
            for key, value in imp_weight[:10]:
                rows.append([key, value])
            writeResultCSV(self.RESULT_CSV, rows)

        # Write CSV
        rows = [['Train+Test', totalMem, trainingTime, predictTime, saveModelTime, evals['eval']['error'][-1],
                 evals['eval']['auc'][-1], evals['eval']['logloss'][-1]]]
        for param, value in tpparams.items():
            rows[0].append("%s=%s" % (param, value))
        writeResultCSV(self.RESULT_CSV, rows)

    def cross_validation(self, params):
        print " "
        print str(params)
        cvparams = params.copy() # used for CSV writing
        for param, value in self.default_params.items():
            if param not in params:
                params[param] = value
        # Specially deal with num of booster
        num_round = params['n_estimators'] if 'n_estimators' in params else self.default_params['n_estimators']

        stTime = time.time()
        mem = PythonMemoryMeasure()
        memThread = threading.Thread(target = mem)
        try:
            memThread.start()
            eval_set = xgb.cv(params, self.dtrain,num_boost_round=num_round, nfold=5,
                              metrics={'error', 'auc', 'logloss'}, seed=0)
        finally:
            mem.stop = True
            memThread.join()
        edTime = time.time()
        trainingTime = str(edTime - stTime)
        totalMem = self.dataSetMem + mem.usedMem
        print "totalMem : ", totalMem
        print "trainingTime : ", trainingTime
        
        # Evaluation Result
        testObj = eval_set['test-logloss-mean'].iloc[-1]
        testErr = eval_set['test-error-mean'].iloc[-1]
        testAUC = eval_set['test-auc-mean'].iloc[-1]

        print "testErr", testErr
        print "self.bestErr", self.bestErr
        # Compare with self.bestErr
        if testErr < self.bestErr:
            print "Enter"
            self.bestErr = testErr
            for param, value in params.items():
                self.best_params[param] = value # TODO: Bug?

        # Write CSV
        rows = [["CV", totalMem, trainingTime, -1, testErr,
                 testAUC, testObj]]
        for param, value in cvparams.items():
            rows[0].append("%s=%s" % (param, value))
        writeResultCSV(self.RESULT_CSV, rows)
    
    def tearDown(self):
        super(XGBoostTest, self).tearDown()

    def tearDownClass(self):
        super(XGBoostTest, self).tearDownClass()

    def writeBestParams(self):
        print self.best_params
        writeResultCSV(self.RESULT_CSV, [["Best Params"], [str(self.best_params)]])