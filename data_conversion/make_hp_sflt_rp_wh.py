#!/usr/bin/env python

"""
Create a file containing a subfault wave height data.

usage:  make_hp_sflt_rp_wh.py [<path to data>]

Creates a CSV file: <hpID>,<sfltID>,<rp>,<wave_height_value>

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path
import re
import glob


# default mount path - can be overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

# derived paths to file(s)
OutputFile = './hp_sflt_rp_wh.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


def main():
    # override path to data if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # make path to DP-* directory      
    input_mask = os.path.join(DataPath, 'earthquake_data', 'hazmap_files', 'deag', 'D-*')

    out_fd = open(OutputFile, 'wb')

    for fname in glob.glob(input_mask):
        # get hpID from filename
        basename = os.path.basename(fname)
        print('DP file: %s' % basename)
        (_, hpID) = basename.split('-')
        hpID = int(hpID)

        # get data from file
        fd = open(fname, 'r')
        lines = fd.readlines()
        fd.close()

        # split header and data lines
        header = lines[0].strip()
        lines = lines[1:]

        # get return periods list from header
        header = SpacesPattern.split(header)[3:]
        header = map(float, header)
        header = map(int, header)

        # read data lines, writing to output file
        for (sfID, line) in enumerate(lines):
            # get waveheights for this subfault ID
            line = line.strip()
            data = SpacesPattern.split(line)[2:]

            for (rp, wh) in zip(header, data):
                wh = float(wh)
                out_fd.write('%d,%d,%d,%f\n' % (hpID, sfID, rp, wh))

    out_fd.close()


if __name__ == '__main__':
    main()
