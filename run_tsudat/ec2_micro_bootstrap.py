#!/usr/bin/env python

"""
The TsuDAT2 micro bootstrap.

The minimum code required to:
1. Read userdata (bucket, s3filepath, scriptpath)
2. Download S3 file, unzip it (relative) into a temporary directory
3. Execute 'scriptpath' script

Note step 3 says 'execute'.  This is a separate process execute,
not a python import and call methods.

Expects the following environment variables to be set:
    EC2_ACCESS_KEY
    EC2_SECRET_ACCESS_KEY
"""


import os
import sys
import gc
import zipfile
import json
import traceback
import tempfile
import boto


# Amazon information URL
AmazonInfoURL = 'http://169.254.169.254'

# URL to get user-data from
UserDataURL = '%s/2007-01-19/user-data' % AmazonInfoURL

# file to download S3 payload as
S3ZipFile = './input_data.zip'

# required keys in userdata JSON dictionary
RequiredValues = ['bucket', 's3_file_path', 'script_path']


def abort(msg):
    """Abort after printing message."""

    print(msg)
    sys.exit(10)


def s3_connect():
    """Connect to S3 storage.

    Returns an S3 connection object.

    Tries to remove sensitive data from memory as soon as possible.
    """

    access_key = os.environ['EC2_ACCESS_KEY']
    secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
    s3 = boto.connect_s3(access_key, secret_key)
    access_key = 'DEADBEEF'
    secret_key = 'DEADBEEF'
    del access_key, secret_key
    gc.collect()

    return s3


def micro_bootstrap(bucket, s3_file_path, script_path):
    """Bootstrap the run into existence."""

    print('micro bootstrap start, globals from user_data are:')
    print('   bucket=%s' % bucket)
    print('   s3_file_path=%s' % s3_file_path)
    print('   script_path=%s' % script_path)

    # get an S3 connection
    s3 = s3_connect()

    # load the input data files from S3
    print('Loading S3 file %s/%s into %s' % (bucket, s3_file_path, S3ZipFile))
    bucket = s3.get_bucket(bucket)
    if bucket is None:
        abort("Can't find bucket '%s'" % S3bucket)
    try:
        key = bucket.get_key(s3_file_path)
    except S3ResponseError:
        abort("Can't find key '%s' in bucket '%s'" % (s3_file_path, S3bucket))
    if key is None:
        abort("Can't find key '%s' in bucket '%s'" % (s3_file_path, S3bucket))
    key.get_contents_to_filename(S3ZipFile)

    # unzip the input data ZIP file into a temporary directory
    tmp_path = tempfile.mkdtemp(prefix='tsudat_')
    print('Unzipping %s to %s' % (S3ZipFile, tmp_path))
    z = zipfile.ZipFile(S3ZipFile)
    z.extractall(path=tmp_path)
    os.remove(S3ZipFile)

    # replace this process with the one in the S3 file
    os.execv(script_path, [])


if __name__ == '__main__':
    """The task here is to get the userdata string, put values into globals.
    and call micro_bootstrap()."""

    def excepthook(type, value, tb):
        """Exception hook routine."""

        msg = '\n' + '='*80 + '\n'
        msg += 'Uncaught exception:\n'
        msg += ''.join(traceback.format_exception(type, value, tb))
        msg += '='*80 + '\n'
        print(msg)

    # plug our handler into the python system
    sys.excepthook = excepthook
        
    # get user-data into a string & convert JSON to python dictionary
    with os.popen('wget -O - -q %s' % UserDataURL) as fd:
        json_userdata = fd.readlines()

    json_userdata = '\n'.join(json_userdata)
    userdata = json.loads(json_userdata)

    print('userdata=%s' % str(userdata))

    # check userdata dictionary for required parameters
    error = False
    error_msg = []

    for name in RequiredValues:
        if not userdata.get(name, None):
            error = True
            error_msg.append("%s field doesn't exist or is empty" % name)

    if error:
        abort('\n'.join(error_msg))

    # set values: common use variables, debug and logging, etc
    for name in RequiredValues:
        exec "%s = userdata['%s']" % (name, name)

    # do it!
    micro_bootstrap(bucket, s3_file_path, script_path)

