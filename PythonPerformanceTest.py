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
from scipy.sparse import csr_matrix, isspmatrix
from PythonMemoryMeasure import PythonMemoryMeasure
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from CSVHelper import readFromParamFile, writeResultCSV

class PythonPerformanceTest(object):
	def __init__(self, RESULT_CSV, JSON_LIST):
		self.RESULT_CSV = RESULT_CSV
		self.JSON_LIST = JSON_LIST

	# Param dataType should be 'Pandas', 'Numpy' or 'DMatrix'
	# If dataType = 'DMatrix', store self.dtrain and self.dtest
	# If dataType = 'Pandas' or 'Numpy', store self.data, self.label, 
	# self.testData and self.testLabel
	def setUp(self, dataType):
		assert(dataType in ('Pandas', 'Numpy', 'DMatrix')), \
			"DataType should be either 'Pandas', 'Numpy' or 'DMatrix'"
		# Read parameters from file
		print self.JSON_LIST
		params = readFromParamFile(self.JSON_LIST)

		# Read CSV and calculate time
		stTime = time.time()
		ds = pd.read_csv(params['dataset_file'], 
			nrows=params['nrows'] if 'nrows' in params else None)
		print ds.head()
		edTime = time.time()
		self.dataSetName = params['dataset_file']
		target_column = params['target_column'][0]
		label_ds = ds[[target_column]]
		ds = ds.drop(columns=[target_column])	# Fix: use "target_column" in json
		print('takes %f sec to load data' % (edTime - stTime))

		# Has ID
		if len(params['id_column']) > 0:
			ds = ds.drop(columns=params['id_column'])

		# Drop Columns
		if len(params['drop_col']) > 0: 
			ds = ds.drop(columns=params['drop_col'])
				
		# One-hot Encoding - ORIGIN,DEST
		st = time.time()
		dummiesCol_l = []
		for col in params['onehot_col']:
			dummiesCol = pd.get_dummies(ds[col], prefix = col)
			dummiesCol_l.append(dummiesCol)
			ds = ds.drop(columns=col) # FixBug
		mt = time.time()
		print('takes %f sec to do one hot encoding' % (mt - st))

		# Normalize Data
		if len(params['norm_col']) > 0:
			nor_col = ds[params['norm_col']]
			print "nor shape : ", nor_col.shape 
			scaler = preprocessing.StandardScaler()
			# scaler = preprocessing.MinMaxScaler()
			nor_col = scaler.fit_transform(nor_col)
			ds = pd.DataFrame(nor_col)
		nor_col = None # Fix

		# Concat the One-hot DF with Norm DF
		print "len(dummiesCol_l) : ", len(dummiesCol_l)
		for dummiesCol in dummiesCol_l: # TODO: this would cost a long time
			print "size of dummy : ", dummiesCol.shape
			st1 = time.time()
			ds = ds.join(dummiesCol)
			#ds[list(dummiesCol.dtypes.index)] = dummiesCol
			et1 = time.time()
			print('takes %f sec to join one dummy' % (et1 - st1))
		ds[target_column] = label_ds
		dummiesCol_l = None # Fix
		et = time.time()
		print('takes %f sec to do one hot encoding' % (et - mt))
		
		n_train = int(math.ceil(ds.shape[0]*params['train_percent']))

		# Decide dataType to use
		self.data = ds.drop(columns=[target_column]).iloc[0:n_train]
		self.label = ds[[target_column]].iloc[0:n_train]
		self.testData = ds.drop(self.data.index).drop(columns=[target_column])
		self.testLabel = ds.drop(self.label.index)[[target_column]]
		ds = None
		if dataType == 'Pandas':
			pass
		elif dataType == 'Numpy':
			self.data = self.data.values
			self.label = self.label.values[:,0]
			self.testData = self.testData.values
			self.testLabel = self.testLabel.values[:,0]
		else: # DMatrix
			self.dtrain = xgb.DMatrix(self.data, self.label)
			self.dtest = xgb.DMatrix(self.testData, self.testLabel)
	   	
		# Convert to sparse matrix
		if params['sparse']:
			assert(dataType == 'Numpy'), "Only Numpy could use sparse matrix"
			self.data = csr_matrix(self.data) #TODO: sparse matrix: only numpy could handle this?
		
		self.dataSetMem = PythonMemoryMeasure().initMem
		print "dataSet Memory : ", self.dataSetMem

	def tearDownClass(self):
		message = MIMEMultipart()
		message['From'] = os.uname()[1]
		message['To'] = 'jackie.lin@sap.com'
		message['Subject'] = 'XGBoost Performance Test'
		
		# Attach the CSV
		f = file(self.RESULT_CSV)
		filebody = f.read()
		attachment = MIMEText(filebody)
		attachment.add_header("Content-Disposition", "attachment", filename=self.RESULT_CSV)
		message.attach(attachment)

		# Text
		msgText = MIMEText(filebody, 'plain', 'utf-8')
		message.attach(msgText)
		f.close()

		try:
			smtpObj = smtplib.SMTP('mail.sap.corp')
			smtpObj.sendmail('jackie.lin@sap.com', 'jackie.lin@sap.com', message.as_string())
			smtpObj.quit()
			print("Mail sent successfully")
		except smtplib.SMTPException:
			print("Err: could not send mail")