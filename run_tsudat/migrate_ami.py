#!/usr/bin/env python

"""
Program to migrate an AMI from one region to another.

Expects all authentication to be set up.

Prompted by the great Amazon melt-down of 22 April 2011.
"""


import os
import gc
import optparse
import tempfile

import boto
from boto.s3.key import Key


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


def move_bucket_contents(from_bucket_name, to_bucket_name, verbose=False):
    connection = s3_connect()
    all_buckets = [bucket.name for bucket in connection.get_all_buckets()]
    if verbose:
        print('Existing buckets:')
        for b in all_buckets:
            print('\t%s' % b)

    error = False
    if not from_bucket_name in all_buckets:
        error = True
        print("Bucket doesn't exist: %s" % from_bucket_name)

    if  not to_bucket_name in all_buckets:
#        error = True
        print("Bucket doesn't exist: %s" % to_bucket_name)

    if error:
        return

    from_bucket = connection.get_bucket(from_bucket_name)
    if verbose:
        print('From files:')
        for x in from_bucket.list():
            print('\t%s' % str(x))

    to_bucket = connection.get_bucket(to_bucket_name)

    # for every FROM file, read and copy to TO bucket
    from_key = Key(from_bucket)
    to_key = Key(to_bucket)
    for key in from_bucket.list():
        if verbose:
            print('Copying: %s' % str(key))
        tmp_file = tempfile.NamedTemporaryFile()
        (fd, tmp_file) = tempfile.mkstemp()
        os.close(fd)
        from_key.key = key
        to_key.key = key
        from_key.get_contents_to_filename(tmp_file)
        to_key.set_contents_from_filename(tmp_file)




#from_bucket = connection.create_bucket('ami.aifdr.org')
#from_key = Key(from_bucket)
#from_key.key = 'myfile'
#from_key.get_contents_to_filename('bar.jpg')
#to_key.set_contents_from_filename('foo.jpg')

parser = optparse.OptionParser('usage: %prog [-v] from_bucket to_bucket')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                  default=False, help='verbose output')

(options, args) = parser.parse_args()
if len(args) != 2:
    parser.error('incorrect number of arguments')

move_bucket_contents(args[0], args[1], options.verbose)
