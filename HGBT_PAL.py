import os
import smtplib
from email.mime.text import MIMEText
import time
import unittest
from sys import stdin, stdout
from palLib import Name, Ignore, Timing
from PalTestCase import PalTestCase, PalMemoryMeasure
import threading
import csv
from CSVHelper import writeResultCSV

multiParam = [("'THREAD_RATIO'", "NULL", "1.0", "NULL"),]
singleParam = [("'THREAD_RATIO'", "NULL", "0.0", "NULL"),]
testParams = [("'THREAD_RATIO'", "NULL", "1.0", "NULL"),]

RESULT_CSV = '/tmp/work/script/result_h37_amazon.csv'

class HGBTTest_PAL(PalTestCase) :
    @Name("unittest")
    def test_main0(self):
        proc = "PAL_HGBT"
        dataSet = "AMAZON" # prepared manually
        params = [
            ("'LEARNING_RATE'", "NULL", "0.3", "NULL"),
            ("'FOLD_NUM'", "5","NULL", "NULL"),
            ("'ITER_NUM'","100","NULL", "NULL"),
            ("'RANGE_MAX_TREE_DEPTH'", "NULL", "NULL", "'[3,7,10]'"),
            ("'RANGE_MIN_SPLIT_LOSS'", "NULL", "NULL", "'[0.1,10,1.0]'"),
            ("'CV_METRIC'","NULL","NULL","'ERROR_RATE'"), # not related to tunning
            ("'REF_METRIC'","NULL","NULL","'AUC'"),
            ("'REF_METRIC'","NULL","NULL","'NLL'"),
            ("'THREAD_RATIO'", "NULL", "1.0", "NULL"),
            ("'HAS_ID'", "0", "NULL", "NULL"),
            ("'CATEGORICAL_VARIABLE'", "NULL", "NULL", "'ACTION'"),
	        ("'DEPENDENT_VARIABLE'", "NULL", "NULL", "'ACTION'"),
	        #("'CALCULATE_IMPORTANCE'", "0", "NULL", "NULL"),
	        #("'CALCULATE_CONFUSION'", "0", "NULL", "NULL")
        ]
        self.single_execution(proc, dataSet, params, testParams)
    
    @Timing()
    def single_execution(self, proc, dataSet, params, testParams) :
        # train
        self.truncate('PAL_PARAMETER_TBL')
        self.insert('PAL_PARAMETER_TBL', params)
        trainTbl = dataSet + '_TRAIN_TBL' # train table name
        sql = 'CALL _SYS_AFL.%s(%s, PAL_PARAMETER_TBL, ?, ?, ?, ?, ?) WITH OVERVIEW' % (proc, trainTbl)
        mem = PalMemoryMeasure()
        memThread = threading.Thread(target = mem)
        try :
            memThread.start()
            stTime = time.time()
            print "SQL : ", sql	   
            self.cur.execute(sql)
            edTime = time.time()
            trainingTime = str(edTime - stTime)
            print trainingTime
        finally :
            mem.stop = True
            memThread.join()
        totalMem = mem.usedMem / (1024.0 * 1024)
        stdout.write('used memory is: %fM' % (mem.usedMem / (1024.0 * 1024)))
        rtnTbls = self.cur.fetchall()
        # rtnTbls :  [(u'P3', u'"DM_PAL"."MODEL"'), (u'P4', u'"DM_PAL"."IMP"'), 
        # (u'P5', u'"DM_PAL"."CONFUSION"'), (u'P6', u'"DM_PAL"."STATS"'), (u'P7', u'"DM_PAL"."CV"')]
        
        # query statistical result
        sql = "SELECT * FROM %s" % rtnTbls[3][1] # P6: stat table
        self.cur.execute(sql)
        statTbl = self.cur.fetchall()
        # statTbls : [(u'ERROR_RATE_MEAN', u'0.420666'), (u'ERROR_RATE_VAR', u'0.000108444'), 
        # (u'AUC_MEAN', u'0.60504'), (u'NLL_MEAN', u'0.60504')]
        stdout.write('\n%sSTAT TBL%s\n' % ('-'*14, '-'*14))
        for tu in statTbl:
            stdout.write('|%-15s|%-18s|\n' % (tu[0], tu[1]))
        stdout.write("%s\n" % ('-' * 36))
        error_rate = statTbl[0][1]
        auc = statTbl[2][1]
        nll = statTbl[3][1]

        # cross validation result
        sql = "SELECT * FROM %s" % rtnTbls[4][1] # P7: cv result
        self.cur.execute(sql)
        cvTbl = self.cur.fetchall()
        if len(cvTbl) > 0: # only print result while CV is enabled
            stdout.write('\n%sCVCV TBL%s\n' % ('-'*14, '-'*14))
            for tu in cvTbl:
                tu = filter(None, tu)
                stdout.write('|%-15s|%-18s|\n' % (tu[0], tu[1]))
            stdout.write("%s\n" % ('-' * 36))

        # Write CSV
        rows = [['DataSet', dataSet], ['Parameter']] # write parameters
        for tu in params:
            tu = [x for x in tu if x != "NULL"]
            if tu[0].endswith("METRIC'") or tu[0].endswith("VARIABLE'") or tu[0] == "'THREAD_RATIO'" or tu[0] == "'HAS_ID'":
                continue
            rows.append(tu)
        writeResultCSV(RESULT_CSV, rows)
        header = ['MemUsage','TrainingTime','ErrTest','AUCTest','ObjTest'] # write Result
        rows = [[totalMem, trainingTime, error_rate, auc, nll]]
        writeResultCSV(RESULT_CSV, rows, header)
        if len(cvTbl) > 0: # cross validation result
            rows = [['CV']]
            for tu in cvTbl:
                tu = filter(None, tu)
                rows.append(list(tu))
            writeResultCSV(RESULT_CSV, rows)
           
    @classmethod
    def tearDownClass(self):
        f = file(RESULT_CSV) 
        message = MIMEText(f.read(), 'plain', 'utf-8')
        message['From'] = os.uname()[1]
        message['To'] = 'jackie.lin@sap.com'
        message['Subject'] = 'PAL Performance Test'
        try:
            smtpObj = smtplib.SMTP('mail.sap.corp')
            smtpObj.sendmail('jackie.lin@sap.com', 'jackie.lin@sap.com', message.as_string())
            smtpObj.quit()
            print("Mail sent successfully")
        except smtplib.SMTPException:
            print("Err: could not send mail")

if __name__ == "__main__" :
    unittest.main()
