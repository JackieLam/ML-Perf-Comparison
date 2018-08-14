import time
import functools
import psutil
import os

class PythonMemoryMeasure :
    def __init__(self) :
        self.stop = False
        self.initMem = self._getMemory()
        print "initMem", self.initMem
        self.usedMem = 0

    def __call__(self) :
        while not self.stop :
            memSize = self._getMemory()
            gap = memSize - self.initMem
            if gap > self.usedMem :
                self.usedMem = gap
            time.sleep(0.1)

    def _getMemory(self) :
        process = psutil.Process(os.getpid())
        memSize = process.memory_info().rss / (1024.0 * 1024.0)
        return memSize
