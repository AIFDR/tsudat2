#!/usr/bin/env python

"""
Function to read TsuDAT simulation messages.

It's a generator returning messages as python dictionaries
as described in the wiki.
"""

import sys
import json
from amqplib import client_0_8 as amqp

import messaging_amqp as config


def queue_messages():
    """Return messages from server queue.

    Yields messages as a dictionary.
    """

    # create exchange+queue, bound
    conn = amqp.Connection(host=config.MsgHost, userid=config.MsgUserid,
                           password=config.MsgPassword, virtual_host=config.MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    chan.queue_declare(queue=config.Queue, durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(exchange=config.Exchange, type="direct", durable=True, auto_delete=False,)

    routing_key = config.WorkerRouting
    chan.queue_bind(queue=config.Queue, exchange=config.Exchange, routing_key=routing_key)

    # now get messages, convert from JSON and yield each one
    msg = True
    while msg:
        msg = chan.basic_get(queue=config.Queue, no_ack=True)
        if msg:
            d = json.loads(msg.body)
            yield d
    # no more messages, tear down messaging
    chan.close()
    conn.close()


if __name__ == '__main__':
    for msg in queue_messages():
        instance = msg.get('instance', '<none>')
        #status = msg['status']
        status = msg.get('status', 'STATUS')
        timestamp = msg['timestamp']
        gen_file = msg.get('generated_datafile', '')
        message = msg.get('message', '')
        if message == 'POLL':
            m = ('%s: %-8s at %s POLL'
             % (instance, status, timestamp))
        else:
            m = ('%s: %-8s at %s%s%s%s%s%s%s'
                 % (instance, status, timestamp,
                    '\n\t      User: %s' % message['User'],
                    '\n\t   Project: %s' % message['Project'],
                    '\n\t  Scenario: %s' % message['Scenario'],
                    '\n\t   BaseDir: %s' % message['BaseDir'],
                    '\n\tScriptPath: %s' % message['ScriptPath'],
                    '\n\t     Setup: %s' % message['Setup']))
        print(m)
        print('message=%s' % str(message))

