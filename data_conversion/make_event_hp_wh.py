#!/usr/bin/env python

"""
Create a CSV file containing distilled Tfile data.

usage:  make_tfile_data.py [<path to data>]

Writes a CSV file:  "event ID, hazard point ID, wave height".
Events which have probability or wave height of 0.0 are not
written out.

This is for loading TsuDATA data into the TsuDAT2 database.
"""


import sys
import os.path
import re


# default data path - overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

OutputFile = './event_hp_wh.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')

MAX_HP_ID = 100000   # event IDs are expected to be in [1, 76170]


def main():
    # override path to Tfle directory if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    # make path to single Tfile        
    input_path = os.path.join(DataPath, 'earthquake_data', 'Tfiles')

    out_fd = open(OutputFile, 'wb')

    for hp_id in xrange(MAX_HP_ID):
        tfile = 'T-%04d' % hp_id
        tfile_path = os.path.join(input_path, tfile)
#        print('Tfile is %s' % tfile_path)
        print '%d' % hp_id,
        sys.stdout.flush()

        try:
            in_fd = open(tfile_path, 'r')
        except IOError:
            print('Max eventID=%d' % (hp_id-1))
            break

        lines = in_fd.readlines()[1:]	# skip header line
        in_fd.close()

        for (event_id, line) in enumerate(lines):
            (wh, prob, _) = SpacesPattern.split(line.strip(), 2)
            wh = float(wh)
            prob = float(prob)
            if wh > 0.0 and prob > 0.0:
                # event_id+1 because events start index is 1
                out_fd.write('%d,%d,%f\n' % (event_id+1, hp_id, wh))

    out_fd.close()


if __name__ == '__main__':
     main()
