#!/usr/bin/env python

"""
Restart an Amazon instance, using /tmp/tsudat/_restart_ data.

usage: restart_amazon <user> <project> <scenario> <setup>

"""

import os
import time
import boto


# the AMI we are going to run
DefaultAmi = 'ami-54a55b3d'  # Ubuntu_10.04_TsuDAT_2.0.28

# keypair used to start instance
DefaultKeypair = 'tsudat2'

# base directory for restart data
RestartDir = '/tmp/tsudat/_restart_'


def start_ami(ami, key_name=DefaultKeypair, instance_type='m1.large',
              user_data=None):
    """Start the configured AMI, wait until it's running.

    ami            the ami ID ('ami-????????')
    key_name       the keypair name
    instance_type  type of instance to run
    user_data      the user data string to pass to instance
    """

    access_key = os.environ['EC2_ACCESS_KEY']
    secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
    ec2 = boto.connect_ec2(access_key, secret_key)
    access_key = 'DEADBEEF'
    secret_key = 'DEADBEEF'
    del access_key, secret_key

    if user_data is None:
        user_data = ''

    reservation = ec2.run_instances(image_id=ami, key_name=key_name,
                                    instance_type=instance_type,
                                    user_data=user_data)
    # got some sort of race - "instance not found"? - try waiting a bit
    time.sleep(1)

    # Wait a minute or two while it boots
    instance = reservation.instances[0]
    while True:
        instance.update()
        if instance.state == 'running':
            break
        time.sleep(1)

    return instance


def restart(user, project, scenario, setup):
    """Restart instance for supplied data."""
#    user_project_VictorHarbour_trial.restart

    # check for existance of restart data
    restart_file = os.path.join(RestartDir,
                                '%s_%s_%s_%s.restart'
                                % (user, project, scenario, setup))
    if not os.path.isfile(restart_file):
        print('Sorry, no restart for user/project/scenario/setup')
        print('restart_file=%s' % restart_file)
        sys.exit(0)

    with open(restart_file, 'r') as fp:
        user_data = fp.read()

    instance = start_ami(DefaultAmi, user_data=user_data)

    print('Started: %s' % instance.dns_name)


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 5:
        print __doc__
        sys.exit(10)

    user = sys.argv[1]
    project = sys.argv[2]
    scenario = sys.argv[3]
    setup = sys.argv[4]

    restart(user, project, scenario, setup)
