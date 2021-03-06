#!/usr/bin/env python

"""
Create a file containing a mapping of event ID to subfault IDs.

usage:  make_event_subfaults.py [<path to data>]

Creates a CSV file: <eventID>,<list of subfaultIDs>.

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path
import re


# default mount path - can be overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

# output filename
OutputFile = './event_subfaults.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


def main():
    # override path to T-00000 file is sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # make path to single Tfile        
    input_file = os.path.join(DataPath, 'earthquake_data', 'Tfiles', 'T-0000')

    # get data from file, skip header line
    fd = open(input_file, 'r')
    lines = fd.readlines()[1:]
    fd.close()

    out_fd = open(OutputFile, 'wb')

    # read data lines, writing to output file
    for (id, line) in enumerate(lines):
        line = line.strip()
        #(_, _, _, _, subfaults) = SpacesPattern.split(line, 4)
	a = SpacesPattern.split(line, 4)
        subfaults = a[4]	

        subfault_list = SpacesPattern.split(subfaults)

        out_fd.write('%d,%s\n' % (id+1, ','.join(subfault_list)))

    out_fd.close()


if __name__ == '__main__':
    main()
