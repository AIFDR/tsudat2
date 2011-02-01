#!/usr/bin/env python

"""
Create a file containing subfault positions for each zone.

usage:  make_zonename_2_subfault_posn.py [<path to data>]

Writes a CSV file: <zone name>,<posn>,<posn>,...
where a <posn> is:  <lon>:<lat>.

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path


# default data path - ovridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

OutputFile = './zonename_2_subfault_posn.csv'

def main():
    # override path to data directory if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # generate path to subfaults.txt
    input_file = os.path.join(DataPath, 'subfaults.txt')

    # get data from file
    fd = open(input_file, 'r')
    lines = fd.readlines()
    fd.close()

    out_fd = open(OutputFile, 'wb')

    # read data lines, writing to stdout
    prev_zone = None
    
    for line in lines:
        line = line.strip()
        if not line or line[0] == '#':
            continue

        (lon, lat, subfaultid, zonename) = line.split(' ', 3)
        lon = float(lon)
        lat = float(lat)
        subfaultid = int(subfaultid)

        if zonename != prev_zone:
            if prev_zone:
                out_fd.write('\n')
            out_fd.write('%s' % zonename)
            prev_zone = zonename

        out_fd.write(',%.5f:%.5f' % (lon, lat))

    out_fd.close()


if __name__ == '__main__':
    main()
