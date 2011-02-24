#!/usr/bin/env python

"""A small program to create a TsuDAT2 working directory.

usage: mk_tsudat_dir <user> <setup> <base_dir> <project> <scenario> <event>

eg: mk_tsudat_dir fred trial /tmp/xyzzy project scenario 12345
"""


import os
import shutil
import time


MajorSubDirs = ['topographies', 'polygons', 'boundaries', 'outputs',
                'gauges', 'meshes']


def touch(path):
    """Do a 'touch' for a file.  This is NOT  good solution."""

    with file(path, 'a'):
        os.utime(path, None)


def mk_tsudat_dir(user, setup, base, proj, scen, event):
    """Create a TsuDAT2 directory."""

    # delete any directory that might be there

    # create base directory
    proj_dir = os.path.join(base, user, proj)
    shutil.rmtree(proj_dir, ignore_errors=True)
    os.makedirs(proj_dir)

    # now create major sub-dirs
    for sd in MajorSubDirs:
        os.makedirs(os.path.join(proj_dir, sd))

    # get time string, 'comment', etc
    time_str = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    comment = '%s_%d' % (setup, event)

    # now create lower directories & files
    path = os.path.join(proj_dir, 'topographies')
    touch(os.path.join(path, scen+'_combined_elevation.pts'))
    touch(os.path.join(path, scen+'_combined_elevation.txt'))

    path = os.path.join(proj_dir, 'boundaries')
    touch(os.path.join(path, 'landward_boundary.csv'))
    touch(os.path.join(path, 'urs_order.csv'))

    path = os.path.join(path, '%s' % event)
    os.makedirs(path)
    touch(os.path.join(path, 'event.lst'))

    path = os.path.join(path, scen)
    os.makedirs(path)

    path = os.path.join(proj_dir, 'outputs')
    sub_dir = os.path.join(path, time_str+'_build_'+user)
    os.makedirs(sub_dir)
    sub_dir = os.path.join(path, time_str+'_run_'+comment)
    os.makedirs(sub_dir)
    os.makedirs(os.path.join(sub_dir, scen))

    path = os.path.join(proj_dir, 'gauges')
    touch(os.path.join(path, 'gauges_final.csv'))

    path = os.path.join(proj_dir, 'meshes')
    touch(os.path.join(path, scen+'.msh'))


if __name__ == '__main__':
    import sys

    def usage(msg=None):
        if msg:
            print(msg)
        print(__doc__)
        sys.exit(10)

    if len(sys.argv) != 7:
        usage()

    user = sys.argv[1]
    setup = sys.argv[2]
    base = sys.argv[3]
    proj = sys.argv[4]
    scen = sys.argv[5]
    event = int(sys.argv[6])

    mk_tsudat_dir(user, setup, base, proj, scen, event)
