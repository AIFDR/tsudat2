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
    input_mask = os.path.join(DataPath, 'earthquake_data', 'hazmap_files',
                              'deag', 'DP-grn-rp-*')

    # get all files matching mask in the directory
    count = 0
    for fname in glob.glob(input_mask):
        count += 1

        # get hpID from filename
        basename = os.path.basename(fname)
        (_, _, _, hpID) = basename.split('-')
        hpID = int(hpID)

        # get data from this file
        fd = open(fname, 'r')
        lines = fd.readlines()
        fd.close()

        # get header line, split out return periods
        header = lines[0].strip()
        lines = lines[1:]

        return_periods = SpacesPattern.split(header)[3:]
        return_periods = [int(float(rp)) for rp in return_periods]

        # step through data, get subfaultID and contribution for each RP
        for (sfid, line) in enumerate(lines):
            # get just the return_periods
            (_, _, contribs) = SpacesPattern.split(line.strip(), maxsplit=2)
            contribs = SpacesPattern.split(contribs.strip())
            for (rp, contrib) in zip(return_periods, contribs):
                contrib = float(contrib)
                if contrib > 0.0:
                    out_fd.write('%s,%d,%d,%s\n' % (hpID, rp, sfid, contrib))

        print '%d' % count,
        sys.stdout.flush()
            
    out_fd.close()


if __name__ == '__main__':
    main()
