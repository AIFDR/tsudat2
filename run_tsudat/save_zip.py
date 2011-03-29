import boto

ACCESS_KEY = 'AKIAIKGYJFXGT5TFJJOA'
SECRET_KEY = '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'

FILE = 'input-data/user-project-VictorHarbour-trial.zip'

s3 = boto.connect_s3(ACCESS_KEY, SECRET_KEY)
bucket = s3.create_bucket('tsudat.aifdr.org')  # bucket names must be unique
key = bucket.new_key(FILE)
key.set_contents_from_filename('tsudat_user_project_VictorHarbour_trial.zip')
key.set_acl('public-read')





