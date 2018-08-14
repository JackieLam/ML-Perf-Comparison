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
from CSVHelper import readFromParamFiles, writeResultCSV

PARAM_CNT = -1

class PythonPerformanceTest(object):
	def __init__(self, RESULT_CSV, JSON_LIST):
		self.RESULT_CSV = RESULT_CSV
		json_string = JSON_LIST
		self.JSON_LIST = json_string.split(',')

	def setUp(self):
		global PARAM_CNT
		PARAM_CNT += 1 # JSON file counter
		# Read parameters from file
		print self.JSON_LIST
		params_l = readFromParamFiles(self.JSON_LIST)
		params = params_l[PARAM_CNT]

		# Read CSV and calculate time
		stTime = time.time()
		ds = pd.read_csv(params['dataset_file'])
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
			print col
			dummiesCol = pd.get_dummies(ds[col], prefix = col)
			dummiesCol_l.append(dummiesCol)
			ds = ds.drop(columns=col) # FixBug
		et = time.time()
		print('takes %f sec to do one hot encoding' % (et - st))

		# Normalize Data
		if len(params['norm_col']) > 0:
			nor_col = ds[params['norm_col']]
			print "nor shape : ", nor_col.shape 
			scaler = preprocessing.StandardScaler()
			# scaler = preprocessing.MinMaxScaler()
			nor_col = scaler.fit_transform(nor_col)
			ds = pd.DataFrame(nor_col)
		
		# Concat the One-hot DF with Norm DF
		for dummiesCol in dummiesCol_l:
			ds[list(dummiesCol.dtypes.index)] = dummiesCol
		ds['y'] = label_ds
		
		n_train = int(math.ceil(ds.shape[0]*params['train_percent']))

		label_ds = ds[['y']].iloc[0:n_train]
		data_ds = ds.drop(columns=['y']).iloc[0:n_train]
	   
		self.testData = ds.drop(data_ds.index).drop(columns=['y']).values
		self.testLabel = ds.drop(label_ds.index)[['y']].values[:,0]
		self.label = label_ds.values[:,0]
		self.data = data_ds.values

		self.testLabel[self.testLabel < 0] = 0 # Deal with special case -1/1
		self.label[self.label < 0] = 0

		# Convert to sparse matrix
		if params['sparse']:
			self.data = csr_matrix(self.data)
		
		ds = None
		data_ds = None
		label_ds = None
		nor_col = None
		dummiesCol_l = None

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