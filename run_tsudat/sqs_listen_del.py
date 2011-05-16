#!/usr/bin/env python2.6

"""
Little helper program to monitor the tsudat.aifdr.org SQS queue.

Prints what is on the SQS queue as it comes in and deletes the message.
"""

import os
import sys
import time
import json

import boto


# default SQS queue name
SQSQueueName = 'tsudat_aifdr_org'

# idle sleep time in seconds
SleepTime = 1.0


def NextWhirly():
    phase = 0
    chars = ['|', '/', '-', '\\']
    while True:
        yield chars[phase]
        phase += 1
        if phase >= len(chars):
            phase = 0


def main(qname, delay):
    """Listen to SQS queue 'qname'."""

    print('Reading queue %s and deleting messages' % qname)

    sqs = boto.connect_sqs(os.environ['EC2_ACCESS_KEY'],
                           os.environ['EC2_SECRET_ACCESS_KEY'])
    queue = sqs.create_queue(SQSQueueName)

    char = NextWhirly()

    while True:
        m = queue.read()
        if m:
            msg = m.get_body()
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
                print('\r'+msg)
        else:
            print '\r' + char.next(),
            sys.stdout.flush()
            time.sleep(delay)


if __name__ == '__main__':
    import sys
    import optparse

    qname = SQSQueueName
    delay = SleepTime

# no time to fart around getting optparse working
#    parser = optparse.OptionParser()
#    parser.add_option('-q', '--queue', type='str', action='store', default=SQSQueueName,
#                      help='SQS queue to read, default is %s' % SQSQueueName)
#    parser.add_option('-d', '--delay', type='float', action='store', default=SleepTime,
#                      help='delay before reading again if queue empty')
#    (options, args) = parser.parse_args()
#    if args:
#        parser.error("unexpected arguments: " + " ".join(args))
#    else:

    try:
        main(qname, delay)
    except KeyboardInterrupt:
        pass

