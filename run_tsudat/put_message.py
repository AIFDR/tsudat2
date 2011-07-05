#!/usr/bin/env python

"""
Function to send a TsuDAT simulation message.
"""

import sys
import json
import time
from amqplib import client_0_8 as amqp

import config


def send_message(User, Project, Scenario, Setup, Instance, **kwargs):
    """Send a message.

    kwargs   a dict of keyword arguments

    Send a JSON representation of the kwargs dict.
    Add the User, Project, Scenario, Setup & Instance global values.
    """

    # add the global values
    kwargs['user'] = User
    kwargs['project'] = Project
    kwargs['scenario'] = Scenario
    kwargs['setup'] = Setup
    kwargs['instance'] = Instance

    # add time as float and string (UTC, ISO 8601 format)
    #kwargs['time'] = time.gmtime()
    kwargs['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())

    # get JSON string
    msg = json.dumps(kwargs)

    # send the JSON
    conn = amqp.Connection(host=config.host, userid=config.userid,
                           password=config.password, virtual_host=config.virtual_host,
                           insist=False)
    chan = conn.channel()

    msg_obj = amqp.Message(msg)
    msg_obj.properties["delivery_mode"] = 2
    routing_key = '%s_%s_%s' % (User, Project, Scenario)
    chan.basic_publish(msg_obj, exchange=config.exchange, routing_key=routing_key)

    chan.close()
    conn.close()


if __name__ == '__main__':
    user = 'user'
    project = 'project'
    scenario = 'scenario'
    setup = 'setup'
    instance = 'i-12345'

    if len(sys.argv) > 1:
        number = int(sys.argv[1])
    else:
        number = 10

    for i in range(1, number+1):
        send_message(user, project, scenario, setup, instance, status='LOG', message='Message %d' % i)
        print('Sent message %d' % i)
        time.sleep(1.0)
