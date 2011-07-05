#!/usr/bin/env python

"""
Function to read TsuDAT simulation messages.

It's a generator returning messages as python dictionaries
as described in the wiki.
"""

import sys
import json
from amqplib import client_0_8 as amqp

import config


def queue_messages(user, project, scenario):
    """Return messages for user+project+scenario queue.

    user      user name
    project   project name
    scenario  scenario name

    Yields messages as a dictionary.
    """

    # create exchange+queue, bound
    conn = amqp.Connection(host=config.host, userid=config.userid,
                           password=config.password, virtual_host=config.virtual_host,
                           insist=False)
    chan = conn.channel()

    chan.queue_declare(queue=config.queue, durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(exchange=config.exchange, type="direct", durable=True, auto_delete=False,)

    routing_key = '%s_%s_%s' % (user, project, scenario)
    chan.queue_bind(queue=config.queue, exchange=config.exchange, routing_key=routing_key)

    # now get messages, convert from JSON and yield each one
    msg = True
    while msg:
        msg = chan.basic_get(queue=config.queue, no_ack=False)
        if msg:
            d = json.loads(msg.body)
            yield d
    # no more messages, tear down messaging
    chan.close()
    conn.close()


if __name__ == '__main__':
    user = 'user'
    project = 'project'
    scenario = 'scenario'

    for msg in queue_messages(user, project, scenario):
        instance = msg['instance']
        #status = msg['status']
        status = msg.get('status', 'STATUS')
        timestamp = msg['timestamp']
        gen_file = msg.get('generated_datafile', '')
        message = msg.get('message', '')
        message = message.replace('\n', '\n\t')
        payload = str(msg.get('payload', ''))
        m = ('%s: %-8s at %s%s%s%s'
             % (instance, status, timestamp,
                '\n\tgen_file: %s' % gen_file if gen_file else '',
                '\n\t message: %s' % message if message else '',
                '\n\t payload: %s' % payload if payload else ''))
        print(m)

