#!/usr/bin/env python

"""
Function to read TsuDAT simulation messages.

It's a generator returning messages as python dictionaries
as described in the wiki.
"""

import sys
import json
import pprint
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

    routing_key = config.ServerRouting
    chan.queue_bind(queue=config.Queue, exchange=config.Exchange, routing_key=routing_key)

    # now get messages, convert from JSON and yield each one
    msg = True
    while msg:
        msg = chan.basic_get(queue=config.Queue, no_ack=True)
        if msg:
            message = json.loads(msg.body)
            yield message
    # no more messages, tear down messaging
    chan.close()
    conn.close()


if __name__ == '__main__':
    for msg in queue_messages():
        instance = msg.get('instance', '<none>')
        status = msg.get('status', '<none>')
        timestamp = msg['timestamp']
        payload = msg.get('payload', '')
        if payload:
            pp = pprint.PrettyPrinter(indent=4)
            pp_payload = pp.pformat(payload)
        else:
            pp_payload = None
        if pp_payload:
            m = ('%s: %-8s at %s%s%s%s%s%s'
                 % (instance, status, timestamp,
                    '\n\t      User: %s' % msg['user'],
                    '\n\t   Project: %s' % msg['project'],
                    '\n\t  Scenario: %s' % msg['scenario'],
                    '\n\t     Setup: %s' % msg['setup'],
                    '\n\t   Payload:\n%s' % pp_payload))
        else:
            m = ('%s: %-8s at %s%s%s%s%s'
                 % (instance, status, timestamp,
                    '\n\t      User: %s' % msg['user'],
                    '\n\t   Project: %s' % msg['project'],
                    '\n\t  Scenario: %s' % msg['scenario'],
                    '\n\t     Setup: %s' % msg['setup']))

        print(m)

