import unittest
from hdbcli import dbapi
import time

class PalTestCase(unittest.TestCase) :
    @classmethod
    def setUpClass(self) :
        super(PalTestCase, self).setUpClass()
        self.con = dbapi.connect('127.0.0.1', 33715, 'DM_PAL', 'Manager1')
        self.cur = self.con.cursor()
        self.cur.execute('SET SCHEMA DM_PAL')

    def insert(self, tableName, values) :
        for value in values :
            self.cur.execute('INSERT INTO %s VALUES (%s)' % (tableName, ",".join(value)))

    def truncate(self, tableName) :
        self.cur.execute('TRUNCATE TABLE %s' % tableName)

class PalMemoryMeasure :
    def __init__(self) :
        self.stop = False
        self.con = dbapi.connect('localhost', 33715, 'DM_PAL', 'Manager1')
        self.cur = self.con.cursor()
        self.initMem = self._getMemory()
        self.usedMem = 0

    def __call__(self) :
        while not self.stop :
            memSize = self._getMemory()
            gap = memSize - self.initMem
            if gap > self.usedMem :
                self.usedMem = gap
            time.sleep(0.1)

    def _getMemory(self) :
        self.cur.execute("SELECT CURRENT_TIMESTAMP, TOTAL_MEMORY_USED_SIZE FROM DUMMY, SYS.M_SERVICE_MEMORY WHERE SERVICE_NAME = 'scriptserver'")
        timestamp, memSize = self.cur.fetchone()
        return memSize

