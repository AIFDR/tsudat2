#/usr/bin/env python

"""
Program designed to run from cron every whenever and recycle public
IPs from instances that don't properly release them.

Note: This program must be compatible with python 2.4 because that's
      the standard on this old CentOS.  Can't use 'with'!
"""

import os
import re
import time


# log file
LogFile = '/home/tsudat/recycle_public_ips.log'

# patternmatch for any number of spaces/tabs
SpacesPattern = re.compile('[ \t]+')


def log(msg=None):
    # get timestamp
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # write the message
    if msg is None:
        msg = ''
    if msg[-1] != '\n':
        msg += '\n'
    log_fd.write('%s|%s' % (timestamp, msg))


def main():
    global log_fd

    # establish the logfile
    log_fd = open(LogFile, 'a')

    # establish the environment and get allocated addresses
# can't do this in python 2.4
#    with os.popen('. /home/tsudat/.nova/novarc; euca-describe-addresses') as fd:
#        lines = fd.readlines()

    fd = os.popen('. /home/tsudat/.nova/novarc; euca-describe-addresses')
    lines = fd.readlines()
    fd.close()

    # step through the output, releasing IPs not associated with an instance
    for line in lines:
        line = line.strip()
        split_line = SpacesPattern.split(line)        
        if len(split_line) == 2:
            # unassociated IP, release it
            (_, ip) = split_line
            cmd = '. /home/tsudat/.nova/novarc; euca-release-address %s' % ip

# can't do this in python 2.4
#            with os.popen(cmd) as fd:
#                lines = fd.readlines()

            log(cmd)
            fd = os.popen(cmd)
            lines = fd.readlines()
            fd.close()
            log(''.join(lines))

    # close log
    log_fd.close()


if __name__ == '__main__':
    main()
