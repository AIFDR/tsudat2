#!/usr/bin/env python2.6

"""
Little helper program to monitor the tsudat.aifdr.org SQS queue.

Prints what is on the SQS queue - doesn't delete messages by default.

To delete messages, do:
    dump_sqs -d
"""

import os
import sys
import time
import json

import boto


SQSQueueName = 'tsudat_aifdr_org'
Timeout = 5


Delete = False
if len(sys.argv) == 2 and sys.argv[1] == '-d':
    Delete = True

print('Reading queue %s %s'
      % (SQSQueueName, '- deleting messages' if Delete else ''))

sqs = boto.connect_sqs(os.environ['EC2_ACCESS_KEY'],
                       os.environ['EC2_SECRET_ACCESS_KEY'])
queue = sqs.create_queue(SQSQueueName)

last_read = time.time()

while True:
    #m = queue.read(Timeout*2)
    m = queue.read()
    if m:
        msg = m.get_body()
        if Delete:
            queue.delete_message(m)
        if msg:
            msg_obj = json.loads(msg)

            instance = msg_obj['instance']
            status = msg_obj['status']
            timestamp = msg_obj['timestamp']
            try:
                gen_file = msg_obj['generated_datafile']
            except KeyError:
                gen_file = ''
            print('%s: %s at %s%s'
                  % (instance, status, timestamp,
                     ', gen_file=%s' % gen_file if gen_file else ''))
            last_read = time.time()
    else:
       idle_time = time.time() - last_read
       if idle_time > Timeout:
           break
       time.sleep(0.5)

print('No more messages.')

