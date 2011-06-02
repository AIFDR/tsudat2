#!/usr/bin/env python


"""A program to print event information for a specified scenario.

Usage: get_hp_events [<hp_id> [<min_height> [<max_height> [<zone_name>]]]]]

where <hp_id>      is the ID number of the hazard point
      <min_height> is the minimum wave height at the hazard point
      <max_height> is the minimum wave height at the hazard point
      <zone_name>  is the name of the zone

Defaults for the above parameters are:
      <hp_id>       3020
      <min_height>  2.0
      <max_height>  3.0
      <zone_name>   Kermadec
"""


import os
import re

#import log
#log = log.Log()

# pattern that will split fields in a string delimited by one or more spaces
DelimPattern = re.compile(' +')

# small tolerance for float compares (wave heights)
Epsilon = 1.0e-6

EventID2ZoneFile = '../data/fault_list_extra.txt'
TFilesDirectory = '/Volumes/Tsu-DAT 1.0/Tsu-DAT_Data/earthquake_data/Tfiles'

def get_zone_fault_limits(zone_name):
    """Get the fault ID limits for a zone.

    zone_name  the name of the zone

    Return a tuple (min, max) of fault IDs, inclusive in zone.
    """

    fd = open(EventID2ZoneFile, 'r')
    lines = fd.readlines()
    fd.close()

    for l in lines:
        l = l.strip()
        (name, start, stop) = l.split()
        if name == zone_name:
            return (int(start), int(stop))

    msg = "Didn't find zone %s in file %s!?" % (zone_name, EventID2ZoneFile)
    raise RuntimeError(msg)


def get_hp_events(hp_id, min_height, max_height, zone_name):
    """Get event information given a hazard point and wave height range.

    hp_id               hazard point index number
    min_height          minimum wave height
    max_height          maximum wave height
    zone_name           name of the zone of interest

    Returns a list of tuples (Quake_ID,Ann_Prob,z_max(m),Mag,Slip(m),subfaults).
    The values are STRINGS!
    The subfaults list is a list of integers (subfault IDs).
    """

    # get pathnames to files of interest
    Tfilename = os.path.join(TFilesDirectory, 'T-%05d' % hp_id)

    # get fault ID limits for the zone
    (f_start, f_stop) = get_zone_fault_limits(zone_name)

    # now read T-**** file
    try:
        fd = open(Tfilename, "r")
        lines = fd.readlines()
        fd.close()
    except IOError, e:
        msg = "Error reading file: %s" % str(e)
        raise RuntimeError(msg)

    # trash the first line of T-**** data
    lines = lines[1:]

    # get the data from the fault lines
    result = []
    min_wave = min_height - Epsilon
    max_wave = max_height + Epsilon
    
    for (i, line) in enumerate(lines[f_start:f_stop+1]):
        event_id = i + f_start
        l = line.strip()
        (zquake, zprob, mag, slip, _, _) = DelimPattern.split(l, maxsplit=5)
        zquake = float(zquake)
        zprob = float(zprob)
        mag = float(mag)
        slip = float(slip)

        if zprob > 0.0 and (min_wave <= zquake <= max_wave):
            id = '%05d' % event_id
            zprob = '%.2g' % zprob
            zquake = '%.2f' % zquake
            mag = '%.1f' % mag
            slip = '%.3f' % slip

            result.append((id, zprob, zquake, mag, slip))

    return result

################################################################################

if __name__ == '__main__':
    import sys
    import getopt

    def usage(msg=None):
        if msg:
            print(msg+'\n')
        print(__doc__)        # module docstring used


    def main():
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
        except getopt.error, msg:
            usage()
            return 1

        for (opt, param) in opts:
            if opt in ['-h', '--help']:
                usage()
                return 0

        if len(args) > 4:
            usage()
            return 1

        # set defaults
        hp_id = 3020
        min_height = 2.0
        max_height = 3.0
        zone_name = 'Kermadec'

        # override defaults with params (if any)
        index = 0
        if index < len(args): hp_id = args[index]; index += 1
        if index < len(args): min_height = args[index]; index += 1
        if index < len(args): max_height = args[index]; index += 1
        if index < len(args): zone_name = args[index]; index += 1

        # make sure args are correct type
        try:
            hp_id = int(hp_id)
            min_height = float(min_height)
            max_height = float(max_height)
        except ValueError:
            usage()
            return 1

        faults = get_hp_events(hp_id, min_height, max_height, zone_name)

        print('HP ID=%d, min_height=%.2f, max_height=%.2f, zone=%s'
              % (hp_id, min_height, max_height, zone_name))
        print('Q_ID\tProb\tz_max\tMag\tSlip')
        print('----\t----\t-----\t---\t----')
        for data in faults:
            print('%s\t%s\t%s\t%s\t%s' % data)

    sys.exit(main())
