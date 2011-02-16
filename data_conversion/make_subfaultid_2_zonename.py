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


def get_max_subfaultid(datapath):
    """Get the maximum subfault ID in the data.

    Get value from number of lines in multimux/i_invall minus 4 because:
        . 3 header lines in i_invall
        . subfault IDs start at 0
    """

    fname = os.path.join(datapath, 'multimux', 'i_invall')
    fd = open(fname, 'r')
    lines = fd.readlines()
    fd.close()

    return len(lines) - 4

def get_zone_subfault_dict(datapath):
    """Get a dictionary mapping {subfaultID: <zonename>, ...}.

    datapath  base path of earthquake data

    Returns a dictionary holding all subfaultIDs mapped to a zone name.
    """

    # read zone_subfault.txt and get dict {0: 'Alaska', ...}
    # containing the start subfault OD: zone data.
    start_subfault_2_zone = {}
    fname = os.path.join(datapath, 'hazmap_files', 'zone_subfault.txt')
    fd = open(fname, 'r')
    lines = fd.readlines()
    fd.close()

    for line in lines:
        line = line.strip()
        (zone, id) = line.split(' ')
        id = int(id)
        start_subfault_2_zone[id] = zone

    return start_subfault_2_zone


def main():
    # override path to T-00000 file is sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]
    DataPath = os.path.join(DataPath, 'earthquake_data')

    # get the max sun\bfault ID from the data
    max_subfault = get_max_subfaultid(DataPath)

    # get start subfault -> zone dictionary
    start_subfault_2_zone = get_zone_subfault_dict(DataPath)

    # open the output file
    out_fd = open(OutputFile, 'wb')

    # now step through all subfault IDs, getting name change
    #  from start_subfault_2_zone
    zone_name = None
    for id in xrange(max_subfault + 1):
        if id in start_subfault_2_zone:
            zone_name = start_subfault_2_zone[id]
        out_fd.write('%d,%s\n' % (id, zone_name))

    out_fd.close()


if __name__ == '__main__':
    main()
