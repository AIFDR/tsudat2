#!/usr/bin/env python

"""The TsuDAT2 bootstrap.  Run the RsuDAT simulation."""


import os
import sys
import zipfile
import traceback

import boto

import tsudat_log as log
LOGFILE = 'tsudat.log'
log = log.Log(LOGFILE)


# the authentication stuff
ACCESS_KEY = 'AKIAIKGYJFXGT5TFJJOA'
SECRET_KEY = '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'

# URL to get user-data from
USER_DATA_URL = 'http://169.254.169.254/2007-01-19/user-data'

# the bucket to use
#BUCKET = 'tsudat.aifdr.org'
BUCKET = 'tsudat.aifdr.org'

# path to input data zip file
IN_ZIP = './input_data.zip'
GEN_ZIP = './gen_data.zip'

# root of the working directory
WORK_DIR = './tsudat'

# sub-directory holding run_tsudat.py and other scripts
TSUDAT_SCRIPTS = 'scripts'


def abort(msg):
    """Abort a run with an error message."""

    log.critical('ABORT: %s' % msg)

    # try to save the log file to S3 first
    try:
        s3 = boto.connect_s3(ACCESS_KEY, SECRET_KEY)
        bucket = s3.create_bucket(BUCKET)
        key_str = ('abort/%s-%s-%s-%s.log'
                   % (user, project, scenario, setup))
        key = bucket.new_key(key_str)
        key.set_contents_from_filename(LOGFILE)
        key.set_acl('public-read')
    except:
        # if we get here, we can't save the log file
        pass

    # then stop the AMI
    shutdown()

def shutdown():
    """Shutdown this AMI."""

    #os.system('sudo halt')
    sys.exit(0)

def bootstrap():
    """Bootstrap the TsuDAT run into existence.

    The following globals are used (all are strings):
    user      user name
    project   the TsuDAT project
    scenario  the scenario
    setup     the run setup ('trial', etc)
    """

    # load the input data files from S3
    s3 = boto.connect_s3(ACCESS_KEY, SECRET_KEY)
    key_str = ('input-data/%s-%s-%s-%s.zip'
               % (user, project, scenario, setup))
    log('Loading %s from S3' % key_str)
    bucket = s3.get_bucket(BUCKET)
    if bucket is None:
        abort("Can't find bucket '%s'" % BUCKET)
    try:
        key = bucket.get_key(key_str)
    except S3ResponseError:
        abort("Can't find key '%s' in bucket '%s'" % (key_str, BUCKET))
    if key is None:
        abort("Can't find key '%s' in bucket '%s'" % (key_str, BUCKET))
    key.get_contents_to_filename(IN_ZIP)

    log('Unzipping %s ...' % IN_ZIP)
    z = zipfile.PyZipFile(IN_ZIP)
    z.extractall()
    log('... done.')
    os.remove(IN_ZIP)

    # load any previous generated data
    key_str = ('gen-data/%s-%s-%s-%s.zip'
               % (user, project, scenario, setup))
    try:
        key = bucket.get_key(key_str)
    except S3ResponseError:
        key = None
    if key:
        log('Getting previously generated data %s' % GEN_ZIP)
        key.get_contents_to_filename(GEN_ZIP)

        log('Unzipping %s ...' % GEN_ZIP)
        z = zipfile.PyZipFile(GEN_ZIP)
        z.extractall()
        log('... done.')

    # run the run_tsudat.py from input dir
    # first jigger the PYTHONPATH so we can import it
    new_path = os.path.join(os.getcwd(), WORK_DIR,
                            user, project, scenario, setup,
                            TSUDAT_SCRIPTS)
    sys.path.append(new_path)
    log('New search path=%s' % new_path)

    import run_tsudat

    log('Running run_tsudat.run_tsudat()')
    run_tsudat.run_tsudat(user, project, scenario, setup)

    # stop this AMI
    log('run_tsudat() finished, shutting down')
    shutdown()

if __name__ == '__main__':
    global user, project, scenario, setup

    import sys
    import re

    def excepthook(type, value, tb):
        """Exception hook routine."""

        msg = '\n' + '='*80 + '\n'
        msg += 'Uncaught exception:\n'
        msg += ''.join(traceback.format_exception(type, value, tb))
        msg += '='*80 + '\n'
        log.critical(msg)
        abort('')

    # plug our handler into the python system
    sys.excepthook = excepthook
        
    # wget user-data into a string & split into params
    with os.popen('wget -O - -q %s' % USER_DATA_URL) as fd:
        args = fd.readline()

    log('args=%s' % str(args))

    expr = re.compile(' *')
    try:
        (user, project, scenario, setup) = expr.split(args)
    except ValueError:
        abort("Expected 4 args in setup string. Got '%s'" % args)
        sys.exit(10)

    bootstrap()
