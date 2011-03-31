#!/usr/bin/env python

"""
The TsuDAT2 bootstrap.

The minimum code required to run ..../scripts/run_tsudat.py.
"""


import os
import sys
import zipfile
import traceback

import boto

import tsudat_log as log


LogFile = 'tsudat.log'

# the authentication stuff
AccessKey = 'AKIAIKGYJFXGT5TFJJOA'
SecretKey = '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'

# URL to get user-data from
UserDataURL = 'http://169.254.169.254/2007-01-19/user-data'

# the bucket to use
#S3Bucket = 'tsudat.aifdr.org'
S3Bucket = 'tsudat.aifdr.org'

# path to input data zip file
InputZipFile = './input_data.zip'
GeneratedZipFile = './gen_data.zip'

# root of the working directory
WorkingDirectory = './tsudat'

# sub-directory holding run_tsudat.py and other scripts/data
ScriptsDirectory = 'scripts'

# name of the JSON file in the S3 input data
JSONFile = 'data.json'


def abort(msg):
    """Abort a run with an error message."""

    log.critical('ABORT: %s' % msg)

    # try to save the log file to S3 first
    try:
        s3 = boto.connect_s3(AccessKey, SecretKey)
        bucket = s3.create_bucket(S3Bucket)
        key_str = ('abort/%s-%s-%s-%s.log'
                   % (User, Project, Scenario, Setup))
        key = bucket.new_key(key_str)
        key.set_contents_from_filename(LogFile)
        key.set_acl('public-read')
    except:
        # if we get here, we can't save the log file
        pass

    # then stop the AMI
    shutdown()

def shutdown():
    """Shutdown this AMI."""

    log.debug('Debug is %s, instance is %sterminating'
              % (str(Debug), 'not ' if Debug else ''))

    if Debug:
        sys.exit(0)
#    else:
#        os.system('sudo halt')

def bootstrap():
    """Bootstrap the TsuDAT run into existence.

    The following globals are used (all are strings):
    User      user name
    Project   the TsuDAT project
    Scenario  the scenario
    Setup     the run setup ('trial', etc)
    """

    log.critical('bootstrap start')

    # load the input data files from S3
    s3 = boto.connect_s3(AccessKey, SecretKey)
    key_str = ('input-data/%s-%s-%s-%s.zip'
               % (User, Project, Scenario, Setup))
    log.info('Loading %s from S3' % key_str)
    bucket = s3.get_bucket(S3Bucket)
    if bucket is None:
        abort("Can't find bucket '%s'" % S3Bucket)
    try:
        key = bucket.get_key(key_str)
    except S3ResponseError:
        abort("Can't find key '%s' in bucket '%s'" % (key_str, S3Bucket))
    if key is None:
        abort("Can't find key '%s' in bucket '%s'" % (key_str, S3Bucket))
    key.get_contents_to_filename(InputZipFile)

    # unzip the input data ZIP file into the local directory
    log.debug('Unzipping %s ...' % InputZipFile)
    z = zipfile.ZipFile(InputZipFile)
    z.extractall()
    if not Debug:
        os.remove(InputZipFile)
    log.debug('... done.')

    # load any previous generated data
    key_str = ('gen-data/%s-%s-%s-%s.zip'
               % (User, Project, Scenario, Setup))
    try:
        key = bucket.get_key(key_str)
    except S3ResponseError:
        key = None
    if key:
        log.info('Getting previously generated data %s' % GeneratedZipFile)
        key.get_contents_to_filename(GeneratedZipFile)

        log.debug('Unzipping %s ...' % GeneratedZipFile)
        z = zipfile.PyZipFile(GeneratedZipFile)
        z.extractall()
        log.debug('... done.')

    # run the run_tsudat.py from input dir
    # first jigger the PYTHONPATH so we can import it
    scripts_path = os.path.join(WorkingDirectory, User, Project, Scenario,
                                Setup, ScriptsDirectory)
    new_pythonpath = os.path.join(os.getcwd(), scripts_path)
    sys.path.append(new_pythonpath)
    log.debug('Added additional import path=%s' % new_pythonpath)
    log.debug('sys.path=%s' % str(sys.path))

    import run_tsudat

    # get path to the JSON file in scripts dir, pass to run_tsudat()
    json_path = os.path.join(new_pythonpath, JSONFile)
    log.info('Running run_tsudat.run_tsudat()')
    run_tsudat.run_tsudat(json_path)

    # stop this AMI ( in case run_tsudat() doesn't
    log.info('run_tsudat() finished, shutting down')
    shutdown()

if __name__ == '__main__':
    global User, Project, Scenario, Setup, BaseDir, Debug

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
    with os.popen('wget -O - -q %s' % UserDataURL) as fd:
        args = fd.readline()    # ignore all but first line

    expr = re.compile(' *')
    fields = expr.split(args)
    if len(fields) == 5:
        (User, Project, Scenario, Setup, BaseDir) = expr.split(args)
        Debug = 'production'
    elif len(fields) == 6:
        (User, Project, Scenario, Setup, BaseDir, Debug) = expr.split(args)
    else:
        abort("Expected 5 or 6 args in setup string. Got '%s'" % args)
        sys.exit(10)

    level = log.INFO
    if Debug == 'debug':
        Debug = True
        level = log.DEBUG

    log = log.Log(LogFile, level=level)

    bootstrap()
