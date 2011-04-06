#!/usr/bin/env python

"""
The TsuDAT2 bootstrap.

The minimum code required to run ..../scripts/run_tsudat.py.
"""


import os
import sys
import shutil
import zipfile
import glob
import tempfile
import traceback

import boto

import tsudat_log as log


# the bucket to use
S3Bucket = 'tsudat.aifdr.org'

# S3 directories under S3Bucket
InputS3DataDir = 'input-data'
OutputS3DataDir = 'output-data'

# form of the data ZIP filename
DataFileFormat = '%s-%s-%s-%s.zip'

# where we write generated data directory
GenSaveDir = 'tmp'

# the file to log to
LogFile = 'tsudat.log'

# the authentication stuff
AccessKey = 'AKIAIKGYJFXGT5TFJJOA'
SecretKey = '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'

# URL to get user-data from
UserDataURL = 'http://169.254.169.254/2007-01-19/user-data'

# path to input data zip file
InputZipFile = './input_data.zip'
OutputZipFile = './output_data.zip'
GeneratedZipFile = './gen_data.zip'

# sub-directory holding run_tsudat.py and other scripts/data
ScriptsDirectory = 'scripts'

# name of the JSON file in the S3 input data
JSONFile = 'data.json'


def make_dir_zip(dirname, zipname):
    """Make a ZIP file from a directory.

    dirname  path to directory to zip up
    zipname  path to ZIP file to create
    """

    os.system('zip -q -r %s %s' % (zipname, dirname))

def make_dir_zip2(dirname, zipname):
    """Make a ZIP file from a directory.

    dirname  path to directory to zip up
    zipname  path to ZIP file to create
    """

    def recursive_zip(zipf, directory):
        ls = os.listdir(directory)

        for f in ls:
            f_path = os.path.join(directory, f)
            if os.path.isdir(f_path):
                recursive_zip(zipf, f_path)
            else:
                zipf.write(f_path, f_path, zipfile.ZIP_DEFLATED)

    zf = zipfile.ZipFile(zipname, mode='w')
    recursive_zip(zf, dirname)
    zf.close()


def abort(msg):
    """Abort a run with an error message."""

    log.critical('ABORT: %s' % msg)

    # try to save the log file to S3 first
    try:
        s3 = s3_connect()
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
    else:
        os.system('sudo halt')

def s3_connect():
    """Connect to S3 storage.

    Returns a connection object.

    Tries to remove sensitive data from memory as soon as possible.
    """

    access_key = os.environ['EC2_ACCESS_KEY']
    secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
    s3 = boto.connect_s3(access_key, secret_key)
    access_key = 'DEADBEEF'
    secret_key = 'DEADBEEF'
    del access_key, secret_key

    return s3

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
    log.info('   Project=%s' % Project)
    log.info('   Scenario=%s' % Scenario)
    log.info('   Setup=%s' % Setup)
    log.info('   BaseDir=%s' % BaseDir)
    log.info('   Debug=%s' % Debug)

    # get name of ZIP working file
    zip_name = DataFileFormat % (User, Project, Scenario, Setup)

    # get an S3 connection
    s3 = s3_connect()

    # load the input data files from S3
    key_str = ('%s/%s' % (InputS3DataDir, zip_name))
    log.info('Loading %s from S3 ...' % key_str)
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
    log.info('Done')

    # unzip the input data ZIP file into the local directory
    log.debug('Unzipping %s ...' % InputZipFile)
    z = zipfile.ZipFile(InputZipFile)
    z.extractall(path='/')
    if not Debug:
        os.remove(InputZipFile)
    log.debug('Done')

    # now load any generated data from a previous run
    key_str = ('%s/%s' % (OutputS3DataDir, zip_name))
    log.info('Trying to load %s from S3 ...' % key_str)
    try:
        bucket = s3.get_bucket(S3Bucket)
        key = bucket.get_key(key_str)
        if key:
            key.get_contents_to_filename(OutputZipFile)
            log.info('Done')

            # unpack generated data into working directory
            log.debug('Unzipping %s ...' % OutputZipFile)
            z = zipfile.ZipFile(OutputZipFile)
            z.extractall(path='/')
            if not Debug:
                os.remove(OutputZipFile)
            log.debug('Done')
        else:
            log.info('Previously generated data not found')
    except S3ResponseError:
        log.info('Previously generated data not found')

    # jigger the PYTHONPATH so we can import 'run_tsudat' from the S3 data
    new_pythonpath = os.path.join(BaseDir, User, Project, Scenario, Setup,
                                  ScriptsDirectory)
    sys.path.append(new_pythonpath)
    log.debug('Added additional import path=%s' % new_pythonpath)

    # get the code for the rest of the simulation
    import run_tsudat

    # get path to the JSON file in scripts dir, pass to run_tsudat()
    json_path = os.path.join(new_pythonpath, JSONFile)
    log.info('Running run_tsudat.run_tsudat()')
    gen_files = run_tsudat.run_tsudat(json_path)

    # add local log files to the 'log' entry
    gen_files['log'] = glob.glob('*.log')

    # optionally dump returned file data
    if Debug:
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        gen_str = pprint.pformat(gen_files)
        log.debug('Returned files:\n%s' % gen_str)

    # save generated data to a staging directory
    # want same pathname for each file as in input ZIP archive
    save_zip_base = os.path.dirname(gen_files['sww'][0])[1:]
    log.debug('save_zip_base=%s' % save_zip_base)
    os.makedirs(save_zip_base)
    for key in gen_files:
        for f in gen_files[key]:
            log.debug('Copying %s -> %s' % (f, save_zip_base))
            shutil.copy2(f, save_zip_base)

    # ZIP the generated directory
    log.debug('zipping dir: %s' % save_zip_base)
    make_dir_zip(save_zip_base, OutputZipFile)

    # save generated directory back to S3
    s3_name = '%s/%s' % (OutputS3DataDir, zip_name)
    log.info('Saving generated directory to S3 storage as %s.' % s3_name)
    try:
        bucket = s3.create_bucket(S3Bucket)
        key = bucket.new_key(s3_name)
        log.debug('Creating S3 file: %s/%s' % (S3Bucket, s3_name))
        key.set_contents_from_filename(OutputZipFile)
        log.debug('Done!')
        key.set_acl('public-read')
    except boto.exception.S3ResponseError, e:
        log.critical('S3 error: %s' % str(e))
        sys.exit(10)

    # stop this AMI (in case run_tsudat() doesn't)
    log.info('run_tsudat() finished, shutting down')
    shutdown()

if __name__ == '__main__':
    import re

    global User, Project, Scenario, Setup, BaseDir, Debug

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
        log.critical("Expected 5 or 6 args in setup string. Got '%s'." % args)
        sys.exit(10)

    level = log.INFO
    if Debug == 'debug':
        Debug = True
        level = log.DEBUG

    log = log.Log(LogFile, level=level)

    bootstrap()
