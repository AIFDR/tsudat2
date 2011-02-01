#!/usr/bin/env python

"""
Create a file containing subfault ID to zonename information.

usage: make_subfaultid_2_zonename.py [<path to data>]

Creates a CSV file: <subfaultID>,<zone name>

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path


# default path to data - overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

OutputFile = './subfaultid_2_zonename.csv'

def main():
    # override path to T-00000 file is sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # make path to subfaults file
    input_file = os.path.join(DataPath, 'subfaults.txt')

    # get data from file
    fd = open(input_file, 'r')
    lines = fd.readlines()
    fd.close()

    out_fd = open(OutputFile, 'wb')

    # read data lines, writing to stdout
    for line in lines:
        line = line.strip()
        if not line or line[0] == '#':
            continue

        (lon, lat, subfaultid, zonename) = line.split(' ', 3)
        lon = float(lon)
        lat = float(lat)
        subfaultid = int(subfaultid)

        out_fd.write('%d,%s\n' % (subfaultid, zonename))

    out_fd.close()


if __name__ == '__main__':
    main()
