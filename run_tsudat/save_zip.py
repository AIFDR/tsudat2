#!/usr/bin/env python2.6

"""
Little helper program to zip up the working directory
and push it into S3.

Use this when making cahnges inside the working directory
and you don't wan't to reboot the instance.
"""

import os

import boto


ACCESS_KEY = 'AKIAIV6EGXIX4D7MIV3A'
SECRET_KEY = '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'

S3_FILE = 'input-data/user-project-VictorHarbour-trial.zip'

ZIP_FILE = 'tsudat-user-project-VictorHarbour-trial.zip'

BUCKET = 'tsudat.aifdr.org'

WORK_DIR = '/tmp/tsudat'


if os.path.isfile(ZIP_FILE):
    print('ZIP file exists, delete it first.')
else:
    print("Creating ZIP file %s" % ZIP_FILE)
    os.system('zip -r %s %s' % (ZIP_FILE, WORK_DIR))
    print("Saving ZIP file to '%s/%s'" % (BUCKET, S3_FILE))
    s3 = boto.connect_s3(ACCESS_KEY, SECRET_KEY)
    bucket = s3.create_bucket(BUCKET)
    key = bucket.new_key(S3_FILE)
    key.set_contents_from_filename(ZIP_FILE)
    key.set_acl('public-read')
