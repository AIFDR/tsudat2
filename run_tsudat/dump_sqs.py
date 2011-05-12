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


Delete = False
if len(sys.argv) == 2 and sys.argv[1] == '-d':
    Delete = True

print('Reading queue %s %s'
      % (SQSQueueName, '- deleting messages' if Delete else ''))

sqs = boto.connect_sqs(os.environ['EC2_ACCESS_KEY'],
                       os.environ['EC2_SECRET_ACCESS_KEY'])
queue = sqs.create_queue(SQSQueueName)


msgs = []
while True:
    # queue.read() seems to hang if given a visibility timeout value??
    #m = queue.read(Timeout)
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
            try:
                message = msg_obj['message'].replace('\n', '\n\t')
            except KeyError:
                message = ''
            try:
                payload = str(msg_obj['payload'])
            except KeyError:
                payload = ''
            msg = ('%s: %-8s at %s%s%s%s'
                   % (instance, status, timestamp,
                      '\n\tgen_file: %s' % gen_file if gen_file else '',
                      '\n\t message: %s' % message if message else '',
                      '\n\t payload: %s' % payload if payload else ''))
            msgs.append((instance, msg_obj['timestamp'], msg))
    else:
        break

msgs.sort()
last_instance = None
for (instance, _, msg) in msgs:
    if last_instance != instance:
        last_instance = instance
        print('-' * 50)
    print(msg)

