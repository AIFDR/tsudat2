#/usr/bin/env python

"""
Program designed to run from cron every whenever and recycle public
IPs from instances that don't properly release them.

The basic idea is to:
1. get a list of unassociated IPs
2. wait for period (get away from possible timing window)
3. release any IPs that are *still* unassociated

That means that anyone allocating IPs 'by hand' has the wait period
to associate the IP before it's released.

Note: This program must be compatible with python 2.4 because that's
      the standard on this old CentOS.  Can't use 'with'!
"""

import os
import re
import time


# wait period, seconds
WaitPeriod = 180

# log file
LogFile = '/home/tsudat/recycle_public_ips.log'

# patternmatch for any number of spaces/tabs
SpacesPattern = re.compile('[ \t]+')


def log(msg=None):
    """Log a message to the logfile.

    msg  the message to log

    Append \n if the message doesn't end in one.
    """

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
    fd = os.popen('. /home/tsudat/.nova/novarc; euca-describe-addresses')
    lines = fd.readlines()
    fd.close()

    # step through the output, releasing IPs not associated with an instance
    unassociated_ips = []
    for line in lines:
        line = line.strip()
        split_line = SpacesPattern.split(line)        
        if len(split_line) == 2:
            # unassociated IP, release it
            (_, ip) = split_line
            unassociated_ips.append(ip)

    # if no unassociated IPs, quit
    if not unassociated_ips:
        return

    # wait a bit
    log(('waiting %d seconds ' % WaitPeriod) + '-' * 60)
    time.sleep(WaitPeriod)

    # get unassociated IPs again, release only if in unassociated_ips list
    fd = os.popen('. /home/tsudat/.nova/novarc; euca-describe-addresses')
    lines = fd.readlines()
    fd.close()
    for line in lines:
        line = line.strip()
        split_line = SpacesPattern.split(line)
        if len(split_line) == 2:
            # unassociated IP, possibly release it
            (_, ip) = split_line
            if ip in unassociated_ips:
                # OK, we've seen this before, release it
                cmd = '. /home/tsudat/.nova/novarc; euca-release-address %s' % ip
                log(cmd)
                fd = os.popen(cmd)
                lines = fd.readlines()
                ret = fd.close()
                if ret:
                    # some sort of error, show output text
                    log(''.join(lines))

    # close log
    log_fd.close()


if __name__ == '__main__':
    main()
