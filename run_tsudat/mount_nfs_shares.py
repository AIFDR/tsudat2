#!/usr/bin/env python

"""
A program to mount an NFS share from a *static* IP.

Will not terminate until successful.

This program is run as root from /etc/rc.local.
"""

import os
import sys
import time


# time to sleep upon failure (seconds)
SleepTime = 30


def mount_share():
    # now try to create /data and mount the /data share
    while True:
        cmd = 'mkdir /data'
        print(cmd); sys.stdout.flush()
        fd = os.popen(cmd)
        line = fd.readline()
        status = fd.close()
        print(line); sys.stdout.flush()

# ignore as error could be 'already exists'
#        if status:	# some sort of error
#            print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
#            time.sleep(SleepTime)
#            continue

        # this is why we must run as root
        cmd = 'mount /data'
        print(cmd); sys.stdout.flush()
        fd = os.popen(cmd)
        line = fd.readline()
        status = fd.close()
        print(line); sys.stdout.flush()

        if status:	# some sort of error
            print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
            time.sleep(SleepTime)
            continue

        # Success!
        return
        

if __name__ == '__main__':
    mount_share()
