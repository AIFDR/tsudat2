#!/usr/bin/env python

"""
A small program to find the maximum contribution value in the deag/DP-grn-rp-* files.

usage: nax_cc.py <path to data>
"""


import sys
import os.path
import re
import glob


# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


def main(DataPath):
    max_contrib = -1.0

    # make mask for a points file      
    input_mask = os.path.join(DataPath, 'earthquake_data', 'hazmap_files',
                              'deag', 'DP-grn-rp-*')

    # get all files matching mask in the directory
    for fname in glob.glob(input_mask):
        # get data from this file
        fd = open(fname, 'r')
        lines = fd.readlines()
        fd.close()

        # get header line, split out return periods
        header = lines[0].strip()
        lines = lines[1:]

        # step through data, get contribution for each RP
        for (sfid, line) in enumerate(lines):
            # get just the return_periods
            (_, _, contribs) = SpacesPattern.split(line.strip(), maxsplit=2)
            contribs = SpacesPattern.split(contribs.strip())
            for contrib in contribs:
                contrib = float(contrib)
                if contrib > max_contrib:
                    max_contrib = contrib
                    print('new max: %.2f, file=%s' % (max_contrib, fname))


if __name__ == '__main__':
    main(sys.argv[1])
