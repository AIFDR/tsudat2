#!/usr/bin/env python

"""
Start an AMI.

usage: start_ami_test <ami>
"""

import os
import time
import tempfile
import boto
from boto.ec2.regioninfo import RegionInfo


# keypair used to start instance
DefaultKeypair = 'testkey'

# default instance type
DefaultType = 'c1.large'


def start_ami(ami, key_name=DefaultKeypair, instance_type=DefaultType,
              user_data=None):
    """Start the configured AMI, wait until it's running.

    ami            the ami ID ('ami-????????')
    key_name       the keypair name
    instance_type  type of instance to run
    user_data      the user data string to pass to instance
    """

    if user_data is None:
        user_data = ''

    # create file with user data
    (fd, tfile) = tempfile.mkstemp(prefix='start_ami_')
    os.write(fd, user_data)
    os.close(fd)

    cmd = ('. /home/tsudat/.nova/novarc; euca-run-instances -f %s -k %s -t %s %s'
           % (tfile, key_name, instance_type, ami))
    print('Doing: %s' % cmd) 
    os.system(cmd)

    time.sleep(1)
    os.remove(tfile)


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print __doc__
        sys.exit(10)

    ami = sys.argv[1]

    user_data="""{"Project":"project","UserDir":"/data/tsudat_runs/user_20110610T023627","Debug":"debug","User":"user","Scenario":"VictorHarbour","ScriptPath":"/data/tsudat_runs/user_20110610T023627/project/VictorHarbour/trial/scripts","Setup":"trial","BaseDir":"/data/tsudat_runs/user_20110610T023627/project/VictorHarbour/trial","JSONData":"/data/tsudat_runs/user_20110610T023627/project/VictorHarbour/trial/scripts/data.json","getsww":true}"""

    start_ami(ami, user_data=user_data)
