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
testParams = [("'THREAD_RATIO'", "NULL", "0.5", "NULL"),
              ("'VERBOSE'", "0", "NULL", "NULL"),]
sharedParams = [("'CV_METRIC'","NULL","NULL","'ERROR_RATE'"), # not related to tunning
                ("'FOLD_NUM'","0","NULL","NULL"),
                ("'REF_METRIC'","NULL","NULL","'AUC'"),
                ("'REF_METRIC'","NULL","NULL","'NLL'"),
                ("'THREAD_RATIO'", "NULL", "1.0", "NULL"),
                ("'HAS_ID'", "1", "NULL", "NULL"),
                ("'CATEGORICAL_VARIABLE'", "NULL", "NULL", "'ISDELAYED'"),
                ("'DEPENDENT_VARIABLE'", "NULL", "NULL", "'ISDELAYED'"),]

RESULT_CSV = '/tmp/work/script/pal_result_tmp.csv'

class HGBTTest_PAL(PalTestCase) :
    @Name("unittest")
    def test_main0(self):
        proc = "PAL_HGBT"
        dataSet = "AIRLINE2008_CAT_UNITTEST" # CAT ["UniqueCarrier","TailNum","Origin","Dest"]
        # Task 1.1
        params = [
            ("'ITER_NUM'","20","NULL", "NULL")
        ]
        params += sharedParams
        print
        self.single_execution(proc, dataSet, params, testParams)
    
    @Timing()
    def single_execution(self, proc, dataSet, params, testParams) :
        # train
        self.truncate('PAL_PARAMETER_TBL')
        self.truncate('PAL_HGBT_MODEL_TBL') # Fix: use this to store model for prediction
        self.insert('PAL_PARAMETER_TBL', params)
        trainTbl = dataSet + '_TRAIN_TBL' # train table name
        testTbl = dataSet + '_TEST_TBL' # Add
        sql = 'CALL _SYS_AFL.%s(%s, PAL_PARAMETER_TBL, PAL_HGBT_MODEL_TBL, ?, ?, ?, ?) WITH OVERVIEW' % (proc, trainTbl)
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

        # do prediction
        self.truncate('PAL_PARAMETER_TBL')
        self.insert('PAL_PARAMETER_TBL', testParams)
        sql = 'CALL _SYS_AFL.%s_PREDICT(%s, PAL_HGBT_MODEL_TBL, PAL_PARAMETER_TBL, ?) WITH OVERVIEW' % (proc, testTbl)
        self.cur.execute(sql)
        rtnPred = self.cur.fetchall() # rtnPred [(u'P4', u'"DM_PAL"."PRED_RESULT"')]
        sql = "SELECT * FROM %s" % rtnPred[0][1]
        self.cur.execute(sql)
        predTbl = self.cur.fetchall()

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
        rows = [[totalMem, trainingTime, error_rate, auc, nll]]
        for tu in params:
            tu = [x for x in tu if x != "NULL"] # Delete NULL and turn into list
            if tu[0].endswith("METRIC'") or tu[0].endswith("VARIABLE'") \
                or tu[0] == "'THREAD_RATIO'" or tu[0] == "'HAS_ID'":
                continue
            rows[0].append("%s=%s" % (tu[0], tu[1])) # param=value
        writeResultCSV(RESULT_CSV, rows)
        # cross validation result
        if len(cvTbl) > 0: 
            rows = [['CV']]
            for tu in cvTbl:
                tu = filter(None, tu)
                rows.append(list(tu))
            writeResultCSV(RESULT_CSV, rows)
    
    def setUp(self):
        header = ['MemUsage','TrainingTime','ErrTest','AUCTest','ObjTest'] # write header
        writeResultCSV(RESULT_CSV, [], header)

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
