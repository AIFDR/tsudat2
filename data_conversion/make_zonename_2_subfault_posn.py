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
import re


# default data path - ovridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

OutputFile = './zonename_2_subfault_posn.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


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


def get_subfaultid_2_posn(datapath):
    """Get a dictionary containing {<subfaultID>: <posn>, ...}

    datapath  path to base of data doirectory
    """

    fname = os.path.join(datapath, 'multimux', 'i_invall')
    fd = open(fname, 'r')
    lines = fd.readlines()
    fd.close()

    # skip 3 heder lines
    lines = lines[3:]

    d = {}
    for (id, line) in enumerate(lines):
        line = line.strip()
        (lon, lat, _) = SpacesPattern.split(line, 2)
        d[id] = '%s:%s' % (lon, lat)

    return d

    
def main():
    # override path to data files if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]
    DataPath = os.path.join(DataPath, 'earthquake_data')

    # get the max subfault ID from the data
    max_subfault = get_max_subfaultid(DataPath)

    # get start subfault -> zone dictionary
    start_subfault_2_zone = get_zone_subfault_dict(DataPath)

    # get dict of subfaultID: <posn>,
    # where <posn> is string "<lon>:<lat>"
    subfaultID_2_posn = get_subfaultid_2_posn(DataPath)

    # open the output file
    out_fd = open(OutputFile, 'wb')

    # step through all subfault IDs
    zone_name = None
    positions = ''
    for id in xrange(max_subfault + 1):
        if id in start_subfault_2_zone:
            # dump any accumulated positions
            if positions:
                out_fd.write('%s%s\n' % (zone_name, positions))
            zone_name = start_subfault_2_zone[id]
            positions = ''	# happens for id==0
        positions += ',%s' % subfaultID_2_posn[id]
        
    out_fd.write('%s%s\n' % (zone_name, positions))

    out_fd.close()


if __name__ == '__main__':
    main()
