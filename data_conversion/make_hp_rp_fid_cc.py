#!/usr/bin/env python

"""
Create a file containing a mapping of hpID+rpID+subfID to subfault colour-code.

usage:  make_hp_rp_fid_cc.py [<path to data>]

Creates a CSV file: <hpID>,<rpID>,<subfID>,<colour_code>.

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path
import re
import glob


# default mount path - can be overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

# derived paths to file(s)
OutputFile = './hp_rp_fid_cc.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


def main():
    # override data path if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # prepare output file
    out_fd = open(OutputFile, 'wb')

    # make mask for a points file      
    input_mask = os.path.join(DataPath, 'deag_points', 'points_*_*.txt')

    # get all files matching mask in the directory
    count = 0
    for fname in glob.glob(input_mask):
        count += 1

        # get hpID and rpID from filename
        basename = os.path.basename(fname)
        (_, hpID, rpID) = basename.split('_')
        (rpID, _) = rpID.split('.')

        # get data from this file
        fd = open(fname, 'r')
        lines = fd.readlines()
        fd.close()

        # step thtough data, get sfID and colour_code, write data
        for line in lines:
            (_, _, cc, sfID) = SpacesPattern.split(line)
            out_fd.write('%s,%s,%s,%s\n' % (hpID, rpID, sfID.strip(), cc))

        print '%d' % count,
        sys.stdout.flush()
            
    out_fd.close()


if __name__ == '__main__':
    main()
