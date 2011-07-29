#!/usr/bin/env python

"""
A program to associate a public IP with this instance and
mount the /data share.

Will not terminate until successful.

This program is run as root from /etc/rc.local.

NOTE: THIS CODE IS NOW OBSOLETE.  THE INSTANCES CAN NOW MOUNT
      NFS SHARES WITHOUT A PUBLIC IP.
"""

import os
import sys
import re
import time
import random


# time to sleep upon failure (seconds)
SleepTime = 30

# patternmatch for any number of spaces/tabs
SpacesPattern = re.compile('[ \t]+')

# Instance information URL
InstanceInfoURL = 'http://169.254.169.254'

# URL to get instance ID
InstanceURL = '%s/latest/meta-data/instance-id' % InstanceInfoURL


def mount_share():
    while True:
        # get the instance string
        with os.popen('wget -O - -q %s' % InstanceURL) as fd:
            instance = fd.readline()
        print('instance=%s' % str(instance)); sys.stdout.flush()
        instance = str(instance)
        if not instance.startswith('i-'):
            # we didn't get an instance string
            print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
            time.sleep(SleepTime)
            continue

        # get an unused allocated IP
        cmd = '. /home/ubuntu/.nova/novarc; euca-describe-addresses'
        print(cmd); sys.stdout.flush()
        fd = os.popen(cmd)
        # expect: ADDRESS	192.43.239.145	i-00000173
        # expect: ADDRESS	192.43.239.146	
        lines = fd.readlines()
        status = fd.close()
        print(''.join(lines)); sys.stdout.flush()

        if status:
            # some sort of error
            print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
            time.sleep(SleepTime)
            continue

        IP_list = []
        for line in lines:
            l = SpacesPattern.split(line.strip())
            if len(l) == 2:
                # got an unused allocated IP
                IP_list.append(l[1])
        print('free IPs: %s' % str(IP_list)); sys.stdout.flush()

        if not IP_list:
            # no unused allocated IPs, try to allocate another
            cmd = '. /home/ubuntu/.nova/novarc; euca-allocate-address'
            print(cmd); sys.stdout.flush()
            fd = os.popen(cmd)
            # expect: ADDRESS	192.43.239.146
            line = fd.readline()
            status = fd.close()
            print(line); sys.stdout.flush()

            if status:
                # some sort of error
                print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
                time.sleep(SleepTime)
                continue

            l = SpacesPattern.split(line.strip())
            IP_list = [l[1]]
            print('newly allocated IP=%s' % l[1]); sys.stdout.flush()

        #####
        # pick a random IP from the list
        #####

        print('free IPs: %s' % str(IP_list)); sys.stdout.flush()
        random.seed()
        index = random.randrange(len(IP_list))
        IP = IP_list[index]
        print('free IP: %s' % str(IP)); sys.stdout.flush()

        #####
        # At this point we have an unused IP
        # If we get an error associating, throw away the IP, start again
        # because someone else my have used our IP
        #####

        # associate IP with ourselves
        cmd = '. /home/ubuntu/.nova/novarc; euca-associate-address -i %s %s' % (instance, IP)
        print(cmd); sys.stdout.flush()
        fd = os.popen(cmd)
        # expect: ADDRESS	192.43.239.142	i-00000171
        line = fd.readline()
        status = fd.close()
        print(line); sys.stdout.flush()

        if status:
            # some sort of error, possibly someone else grabbed our IP
            print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
            time.sleep(SleepTime)
            continue

        #####
        # At this point we have a good association
        # Don't ever go to the top of the outer loop again
        #####

        # now try to create /data and mount the /data share
        while True:
            cmd = 'mkdir /data'
            print(cmd); sys.stdout.flush()
            fd = os.popen(cmd)
            line = fd.readline()
            status = fd.close()
            print(line); sys.stdout.flush()

# ignore as error could be 'already exists'
#            if status:	# some sort of error
#                print('sleeping %d seconds' % SleepTime); sys.stdout.flush()
#                time.sleep(SleepTime)
#                continue

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
