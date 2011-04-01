#!/usr/bin/env python2.6

"""
Little helper program to zip up the working directory
and push it into S3.

Use this when making cahnges inside the working directory
and you don't wan't to reboot the instance.
"""

import os

import boto


ACCESS_KEY = 'AKIAIKGYJFXGT5TFJJOA'
SECRET_KEY = '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'

S3_FILE = 'input-data/user-project-VictorHarbour-trial.zip'

ZIP_FILE = 'tsudat_user_project_VictorHarbour_trial.zip'

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
