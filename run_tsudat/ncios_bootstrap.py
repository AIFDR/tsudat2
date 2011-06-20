#!/usr/bin/env python

"""
The TsuDAT2 bootstrap.

The minimum code required to run a TsuDAT simulation.

Expects the user/project/scenario/setup values in user data.
Gets the S3 package, unzips it and runs run_tsudat.py in the
scripts directory.
"""


import os
import sys
import gc
import shutil
import zipfile
import glob
import json
import time
import tempfile
import traceback

import boto
import messaging_amqp as amqp

import tsudat_log as log


# the file to log to
LogFile = 'tsudat.log'

# Instance information URL
InstanceInfoURL = 'http://169.254.169.254'

# URL to get user-data from
UserDataURL = '%s/2007-01-19/user-data' % InstanceInfoURL

# URL to get instance ID
InstanceURL = '%s/latest/meta-data/instance-id' % InstanceInfoURL

# URL to get public IP
PublicIpUrl = '%s/latest/meta-data/public-ipv4' % InstanceInfoURL

# path to check for good /data mount & sleep time
CheckMountPath = '/data/run_tsudat'
CheckMountSleep = 5

# sub-directory holding run_tsudat.py and other scripts/data
ScriptsDirectory = 'scripts'
OutputsDirectory = 'outputs'

# name of the JSON file in the S3 input data
JSONFile = 'data.json'

# number of minutes to keep idle machine alive -  the idea is to keep instance
# alive for debugging.  for nice message order, IdleTime should not be an
# integer multiple of ReminderTime.
IdleTime = 10 - 1	# 10 mins (almost)
ReminderTime = 1

# message status strings
StatusStart = 'START'
StatusStop = 'STOP'
StatusAbort = 'ABORT'
StatusIdle = 'IDLE'
StatusLog = 'LOG'


def get_public_ip():
    """Get the public address of this instance."""

    # get public IP
    with os.popen('wget -O - -q %s' % InstanceURL) as fd:
        public_ip = fd.readline()
    return public_ip 


def abort(msg):
    """Abort a run with an error message.

    We assume logging has been set up.
    """

    log.critical('ABORT: %s' % msg)

    send_message(status=StatusAbort, message=msg)

    # then stop the AMI
    shutdown()

def error(msg):
    """Send an ERROR message.

    We assume logging has NOT been set up.
    Stop the process right here.  Can't use shutdown().
    """

    log.critical('ERROR: %s' % msg)

    send_message_lite(status=StatusERROR, message=msg)

    # then stop the AMI
    terminate_instance()


def terminate_instance():
    """Terminate the instance, release public IP."""

    # get public IP
    public_ip = get_public_ip()

    # disassociate IP with this instance and terminate the instance
    cmd = '/usr/bin/euca-disassociate-address %s' % public_ip
    log.debug('Doing: %s' % cmd)
    with os.popen(cmd) as fd:
        result = fd.readline()
    log.debug('result: %s' % str(result))

    cmd = '/usr/bin/euca-terminate-instances %s' % Instance
    log.debug('Doing: %s' % cmd)
    with os.popen(cmd) as fd:
        result = fd.readline()
    log.debug('result: %s' % str(result))

    sys.exit(0)


def wait_a_while():
    """Wait for a specified number of seconds (global).

    Send reminder message every few (global) minutes.
    """

    elapsed_time = 0
    while elapsed_time < IdleTime:
        send_message(status=StatusIdle)
        time.sleep(ReminderTime*60)
        elapsed_time += ReminderTime


def shutdown():
    """Shutdown this AMI."""

    log.debug('Debug is %s, instance is %sterminating immediately'
              % (str(Debug), 'not ' if Debug else ''))

    if Debug:
        wait_a_while()

    terminate_instance()


def send_message(**kwargs):
    """Send a message to server.

    kwargs   a dict of keyword arguments

    Send a JSON representation of the kwargs dict.
    Add the User, Project, Scenario, Setup global values.
    """

    # add the global values
    kwargs['user'] = User
    kwargs['project'] = Project
    kwargs['scenario'] = Scenario
    kwargs['setup'] = Setup
    kwargs['instance'] = Instance
    kwargs['project_id'] = ProjectID
    kwargs['scenario_id'] = ScenarioID

    # add time as float and string (UTC, ISO 8601 format)
    kwargs['time'] = time.time()
    kwargs['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())

    # get JSON string
    msg = json.dumps(kwargs)
    log.debug('message JSON: %s' % msg)

    amqp.post_server_message(msg)
    

def send_message_lite(**kwargs):
    """Send a message.  Can't assume any environment.

    kwargs   a dict of keyword arguments

    Send a JSON representation of the kwargs dict ONLY.
    Can't assume logging is set up
    """

    # add time as float and string (UTC, ISO 8601 format)
    kwargs['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())

    # get JSON string
    msg = json.dumps(kwargs)

    amqp.post_server_message(msg)
    

def run_tsudat_log(msg=None):
    """Callback routine for ANUGA periodic logging.

    msg  the message to send to SQS with status of 'LOG'
    """

    if msg is None:
        msg = 'Progress message'

    send_message(message=msg, status=StatusLog)


def bootstrap():
    """Bootstrap the TsuDAT run into existence.

    The following globals are used (all are strings):
    User      user name
    Project   the TsuDAT project
    Scenario  the scenario
    Setup     the run setup ('trial', etc)
    BaseDir   base of the tsudat working directory
    """

    log.info('bootstrap start, user_data globals:')
    log.info('   User=%s' % User)
    log.info('   UserDir=%s' % UserDir)
    log.info('   Project=%s' % Project)
    log.info('   Scenario=%s' % Scenario)
    log.info('   Setup=%s' % Setup)
    log.info('   BaseDir=%s' % BaseDir)
    log.info('   Debug=%s' % Debug)
    log.info('   Instance=%s' % Instance)

    send_message(status=StatusStart)

    # jigger the PYTHONPATH so we can import 'run_tsudat' from the common filesystem
    new_pythonpath = os.path.join(UserDir, Project, Scenario, Setup,
                                  ScriptsDirectory)
    sys.path.append(new_pythonpath)
    log.debug('Added additional import path=%s' % new_pythonpath)

    # get the code for the rest of the simulation
    import run_tsudat

    # get path to the JSON file in scripts dir, pass to run_tsudat()
    json_path = os.path.join(new_pythonpath, JSONFile)
    log.info('Running run_tsudat.run_tsudat(%s)' % json_path)
    gen_files = run_tsudat.run_tsudat(json_path)

    # add local log files to the 'log' entry
    output_path = os.path.join(UserDir, Project, Scenario, Setup,
                               OutputsDirectory)
    local_logs = glob.glob('*.log')
    log_gen_files = []
    for l_l in local_logs:
        dst = os.path.join(output_path, l_l)
        shutil.copyfile(l_l, dst)
        log_gen_files.append(dst)
    gen_files['log'] = log_gen_files

#    # before we possibly delete the gen_files['sww'], get output path
#    save_zip_base = os.path.dirname(gen_files['sww'][0])[1:]
#    log.debug('save_zip_base=%s' % save_zip_base)

    # if user data shows 'getsww' as False, remove 'sww' key from dictionary
    if not UserData.get('GETSWW', True):
        msg = 'Userdata says not to save SWW files, deleting...'
        log.info(msg)
        del gen_files['sww']

    # optionally dump returned file data
    if Debug:
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        gen_str = pprint.pformat(gen_files)
        log.debug('Returned files:\n%s' % gen_str)

    # convert gen_files to JSON and add to stopping message
    send_message(status=StatusStop, payload=gen_files)

    # stop this AMI
    log.info('run_tsudat() finished, shutting down')
    shutdown()


if __name__ == '__main__':
    import re

    global UserData, User, Project, Scenario, Setup, BaseDir, Debug, Instance
    global UserDir
    global ProjectID, ScenarioID

    def excepthook(type, value, tb):
        """Exception hook routine."""

        msg = '\n' + '='*80 + '\n'
        msg += 'Uncaught exception:\n'
        msg += ''.join(traceback.format_exception(type, value, tb))
        msg += '='*80 + '\n'
        print(msg)		# we can't assume logging is set up
        abort(msg)

    # plug our handler into the python system
    sys.excepthook = excepthook

    # wait here until /data mounted
    while not os.path.isdir(CheckMountPath):
        print('Waiting for /data mount (checking %s, sleep %ds)'
              % (CheckMountPath, CheckMountSleep))
        time.sleep(CheckMountSleep)
        
    # get instance ID
    with os.popen('wget -O - -q %s' % InstanceURL) as fd:
        Instance = fd.readline()

    # get user-data into a string & convert JSON to python dictionary
    with os.popen('wget -O - -q %s' % UserDataURL) as fd:
        json_userdata = fd.readlines()

    json_userdata = '\n'.join(json_userdata)
    UserData = json.loads(json_userdata)

    # uppercase all dictionary keys
    for (key, value) in UserData.items():
        del UserData[key]
        UserData[key.upper()] = value

    # check userdata payload
    error_flag = False
    error_msg = []

    if not UserData.get('USER', ''):
        error_flag = True
        error_msg.append("USER field doesn't exist or is empty")
    if not UserData.get('USERDIR', ''):
        error_flag = True
        error_msg.append("USERDIR field doesn't exist or is empty")
    if not UserData.get('PROJECT', ''):
        error_flag = True
        error_msg.append("PROJECT field doesn't exist or is empty")
    if not UserData.get('SCENARIO', ''):
        error_flag = True
        error_msg.append("SCENARIO field doesn't exist or is empty")
    if not UserData.get('SETUP', ''):
        error_flag = True
        error_msg.append("SETUP field doesn't exist or is empty")
    if not UserData.get('BASEDIR', ''):
        error_flag = True
        error_msg.append("BASEDIR field doesn't exist or is empty")

    ProjectID = UserData.get('PROJECT_ID', '')
    ScenarioID = UserData.get('SCENARIO_ID', '')

    if error_flag:
        msg = '\n'.join(error_msg)
        print(msg)
        error(msg)

    # set userdata defaults, etc
    if not UserData.get('DEBUG', ''):
        UserData['DEBUG'] = 'production'

    # set globals: common use variables, debug and logging, etc
    User = UserData['USER']
    UserDir = UserData['USERDIR']
    Project = UserData['PROJECT']
    Scenario = UserData['SCENARIO']
    Setup = UserData['SETUP']
    BaseDir = UserData['BASEDIR']

    if UserData['DEBUG'].lower() == 'debug':
        Debug = True
        level = log.DEBUG
    else:
        Debug = False
        level = log.INFO

    log = log.Log(LogFile, level=level)

    log.debug('UserData=%s' % str(UserData))

    # do it!
    bootstrap()

