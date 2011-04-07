#!/usr/bin/env python2.6

"""
Little helper program to monitor the tsudat.aifdr.org SQS queue.
"""

import os
import json

import boto


SQSQueueName = 'tsudat_aifdr_org'

SleepTime = 5


def get_sqs_message():
    """Get an SQS message.

    Returns a message string, or None if no messages.
    """

    sqs = boto.connect_sqs(os.environ['EC2_ACCESS_KEY'],
                           os.environ['EC2_SECRET_ACCESS_KEY'])
    queue = sqs.create_queue(SQSQueueName)
    m = queue.read()
    if m:
        msg = m.get_body()
        queue.delete_message(m)
        return msg

    return None


if __name__ == '__main__':
    import sys
    import time

    while True:
        msg = get_sqs_message()
        if msg:
            msg_obj = json.loads(msg)
            now = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                time.gmtime())
            instance = msg_obj['instance']
            status = msg_obj['status']
            timestamp = msg_obj['timestamp']
            try:
                gen_file = msg_obj['generated_datafile']
            except KeyError:
                gen_file = ''
            print('%s|%s: %s at %s%s'
                  % (now, instance, status, timestamp,
                     ', gen_file=%s' % gen_file if gen_file else ''))
            continue
        time.sleep(SleepTime)

