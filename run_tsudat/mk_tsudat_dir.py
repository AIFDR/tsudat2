#!/usr/bin/env python

"""A small program to create a TsuDAT2 working directory.

usage: mk_tsudat_dir.py <base_dir> <user> <project> <scenario> <setup> <event>

eg: mk_tsudat_dir.py /tmp/xyzzy fred project scenario trial 12345
"""


import os
import shutil
import time


MajorSubDirs = ['topographies', 'polygons', 'boundaries', 'outputs',
                'gauges', 'meshes']


def touch(path):
    """Do a 'touch' for a file.

    This is NOT a good solution, it's just to show where files will go."""

    with file(path, 'a'):
        os.utime(path, None)


def mk_tsudat_dir(base, user, proj, scen, setup, event):
    """Create a TsuDAT2 run directory.

    base   path to base of new directory structure
    user   user name
    proj   project name
    scen   scenario name
    setup  type of run ('trial', etc)
    event  event number

    Creates a TSUDAT directory structure under the 'base' path.

    Returns a tuple of paths to places under 'base' required by the UI.
    """

    # delete any dir that might be there
    shutil.rmtree(base, ignore_errors=True)

    # create the 'raw_elevation' directory for a project
    path = os.path.join(base, user, proj, 'raw_elevation')
    raw_elev = path
    os.makedirs(path)
    touch(os.path.join(path, 'raw_elevation1.asc'))	# NOT IN FINAL
    touch(os.path.join(path, 'raw_elevation2.asc'))	# NOT IN FINAL

    # create base directory after deleting any dir that might be there
    run_dir = os.path.join(base, user, proj, scen, setup)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)

    # now create major sub-dirs under $setup
    for sd in MajorSubDirs:
        os.makedirs(os.path.join(run_dir, sd))

    # now create lower directories & files (NOT IN FINAL)
    path = os.path.join(run_dir, 'topographies')
    touch(os.path.join(path, 'combined_elevation.pts'))
    touch(os.path.join(path, 'combined_elevation.txt'))

    # NOT IN FINAL
    path = os.path.join(run_dir, 'boundaries')
    touch(os.path.join(path, 'event_%d.lst' % event))
    touch(os.path.join(path, 'landward_boundary.csv'))
    touch(os.path.join(path, 'urs_order.csv'))

    # NOT IN FINAL
    path = os.path.join(run_dir, 'outputs')
    touch(os.path.join(path, 'generated_files'))

    # NOT IN FINAL
    path = os.path.join(run_dir, 'gauges')
    touch(os.path.join(path, 'gauges_final.csv'))

    # NOT IN FINAL
    path = os.path.join(run_dir, 'meshes')
    touch(os.path.join(path, 'meshes.msh'))

    # return paths to various placesunder 'base'
    return (raw_elev,)


if __name__ == '__main__':
    import sys

    def usage(msg=None):
        if msg:
            print(msg)
        print(__doc__)
        sys.exit(10)

    if len(sys.argv) != 7:
        usage()

    index = 1
    base = sys.argv[index]; index += 1
    user = sys.argv[index]; index += 1
    proj = sys.argv[index]; index += 1
    scen = sys.argv[index]; index += 1
    setup = sys.argv[index]; index += 1
    event = int(sys.argv[index]); index += 1

    mk_tsudat_dir(base, user, proj, scen, setup, event)
