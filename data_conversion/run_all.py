#!/usr/bin/env python

"""
Run all conversion programs.

usage:   run_all.py [<data mount path>]

Will run all python programs starting "make_".

This generates all the files used to load data into TsuDAT2.
"""


import os
import sys
import glob


# default mount path - can be overridden by sys.argv[1]
DataPath = '/media/Tsu-DAT 1.0/Tsu-DAT_Data'


def main():
    # override path to T-00000 file is sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]
     
    # get list of make_*.py files, sort
    files = []
    for name in glob.glob('make_*.py'):   
        files.append(name)
    files.sort()

    # step through all 'make_*.py" files
    for name in files:
        cmd = './%s "%s"' % (name, DataPath)
        print(cmd)
        os.system(cmd)

if __name__ == '__main__':
    main()
