import unittest
import time
import sys
import gc
import resource

class Name :
    def __init__(self, name) :
        self.name = name

    def __call__(self, func) :
        def wrapper(*args) :
            print('%s start running...' % self.name)
            rtn = func(*args)
            print('... %s end\n' % self.name)
            return rtn
        return wrapper

class Ignore :
    def __call__(self, func) :
        def wrapper(*args) :
            print('ignored')
        return wrapper

class MemoryMeasure :
    def __call__(self, func) :
        def wrapper(*args) :
            gc.collect()
            rtn = func(*args)
            print('memory used: %f Mb' % self.memory_usage_resource())
            return rtn
        return wrapper

    def memory_usage_resource(self):
        rusage_denom = 1024.
        if sys.platform == 'darwin':
            # ... it seems that in OSX the output is different units ...
            rusage_denom = rusage_denom * rusage_denom
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / rusage_denom
        return mem

class Timing :
    def __call__(self, func) :
        def wrapper(*args) :
            stTime = time.time()
            rtn = func(*args)
            edTime = time.time()
            print('takes %f sec\n' % (edTime - stTime))
            return rtn
        return wrapper

