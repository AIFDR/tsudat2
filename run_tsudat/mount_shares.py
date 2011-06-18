#!/usr/bin/env python

"""
A program to associate a public IP with this instance and
mount the /data share.

Will not terminate until successful.

This program is run as root from /etc/rc.local.
"""

import os
import re
import time


# time to sleep upon failure (seconds)
SleepTime = 5

# get this instance string (i-00000???)
HostName = os.getenv('HOSTNAME')

# patternmatch for any number of spaces/tabs
SpacesPattern = re.compile('[ \t]+')


def mount_share():
    while True:
        # get an available allocated IP
        cmd = '. /home/tsudat/.nova/novarc; euca-describe-addresses'
        print(cmd)
        with os.popen(cmd) as fd:
            # expect: ADDRESS	192.43.239.145	i-00000173
            # expect: ADDRESS	192.43.239.146	
            lines = fd.readlines()
        print(''.join(lines))
        IP = None
        for line in lines:
            if 'error' in line:
                print('sleeping %d seconds' % SleepTime)
                time.sleep(SleepTime)
                continue

            l = SpacesPattern.split(line.strip())
            if len(l) == 2:
                # got an unused allocated IP
                IP = l[1]
                print('unused allocated IP=%s' % IP)
                break

        if IP is None:
            # no free allocated IPs, try to allocate another
            cmd = '. /home/tsudat/.nova/novarc; euca-allocate-address'
            print(cmd)
            with os.popen(cmd) as fd:
                # expect: ADDRESS	192.43.239.146
                line = fd.readline()
            print(line)
            if 'error' in line:
                print('sleeping %d seconds' % SleepTime)
                time.sleep(SleepTime)
                continue
            l = SpacesPattern.split(line.strip())
            IP = l[1]
            print('newly allocated IP=%s' % IP)

        # associate IP with ourselves
        cmd = '. /home/tsudat/.nova/novarc; euca-associate-address -i %s %s' (HostName, IP)
        print(cmd)
        with os.popen(cmd) as fd:
            # expect: ADDRESS	192.43.239.142	i-00000171
            line = fd.readline()
        print(line)
        if 'error' in line:
            print('sleeping %d seconds' % SleepTime)
            time.sleep(SleepTime)
            continue

        # now try to mount the /data share
        cmd = 'mount -t nfs dcnfs.nci.org.au:/short/w85 /data'
        print(cmd)
        with os.popen(cmd) as fd:
            line = fd.readline()
        print(line)
        if 'error' in line.lower():
            print('sleeping %d seconds' % SleepTime)
            time.sleep(SleepTime)
            continue
        if 'permission' in line.lower():
            print('sleeping %d seconds' % SleepTime)
            time.sleep(SleepTime)
            continue
        

if __name__ == '__main__':
    mount_share()
