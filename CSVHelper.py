import csv
import json
import os

def readFromParamFile(paramFile):
    file_exists = os.path.isfile(paramFile)
    with open(paramFile) as f:
        params = json.load(f)
    return params

def writeResultCSV(filename, rows, header=None):
    file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0
    with open(filename,"a+") as f:
        writer = csv.writer(f, delimiter=',', lineterminator='\n')
        #if not file_exists and header:
        if header:
            writer.writerow(header)
        if len(rows) > 0:
            writer.writerows(rows) # add a comment