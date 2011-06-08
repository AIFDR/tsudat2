#!/usr/bin/env python

"""
Module containing rabbit/amqp messaging stuff.
Also contains amqp configuration stuff.
"""

import sys
import json
import time
from amqplib import client_0_8 as amqp


# messaging configuration
#MsgHost='localhost:5672'
MsgHost = '124.168.213.210:5672'
MsgUserid = 'tsudat2'
MsgPassword = 'tsudat12'
MsgVirtualHost = '/'
Exchange = 'tsudat'
Queue = 'messages'

##MsgHost='localhost:5672'
#MsgHost = '124.168.213.210:5672'
#MsgUserid = 'guest'
#MsgPassword = 'guest'
#MsgVirtualHost = '/'
#Exchange = 'sorting_room'
#Queue = 'po_box'

WorkerRouting = 'worker'
ServerRouting = 'server'


# timeout if no message, in seconds
Timeout = 5.0


def post_server_message(user, project, scenario, setup, instance, **kwargs):
    """Send a message to the server.

    kwargs   a dict of keyword arguments

    Send a JSON representation of the kwargs dict.
    Add the User, Project, Scenario, Setup & Ip values.
    """

    # add the global values
    kwargs['user'] = user
    kwargs['project'] = project
    kwargs['scenario'] = scenario
    kwargs['setup'] = setup
    kwargs['instance'] = instance

    # add time as float and string (UTC, ISO 8601 format)
    kwargs['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())

    # get JSON string
    msg = json.dumps(kwargs)

    # send the JSON
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    msg_obj = amqp.Message(msg)
    msg_obj.properties["delivery_mode"] = 2
    routing_key = ServerRouting
    chan.basic_publish(msg_obj, exchange=Exchange, routing_key=routing_key)

    chan.close()
    conn.close()


def post_worker_message(user, project, scenario, setup, **kwargs):
    """Send a message to the worker(s).

    kwargs   a dict of keyword arguments

    Send a JSON representation of the kwargs dict.
    Add the User, Project, Scenario, Setup & Ip values.
    """

    # add the global values
    kwargs['user'] = user
    kwargs['project'] = project
    kwargs['scenario'] = scenario
    kwargs['setup'] = setup

    # add time as float and string (UTC, ISO 8601 format)
    kwargs['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())

    # get JSON string
    msg = json.dumps(kwargs)

    # send the JSON
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    msg_obj = amqp.Message(msg)
    msg_obj.properties["delivery_mode"] = 2
    routing_key = WorkerRouting
    chan.basic_publish(msg_obj, exchange=Exchange, routing_key=routing_key)

    chan.close()
    conn.close()


def get_server_message():
    """Get a message from the server.

    Returns message dictionary.  Blocks if no message available.
    """

    # create exchange+queue, bound
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    chan.queue_declare(queue=Queue, durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(exchange=Exchange, type="direct", durable=True, auto_delete=False,)

    routing_key = ServerRouting
    chan.queue_bind(queue=Queue, exchange=Exchange, routing_key=routing_key)

    # now get messages, convert from JSON and return
    while True:
        msg = chan.basic_get(queue=Queue, no_ack=True)
        if msg:
            msg_dict = json.loads(msg.body)
            break
        else:
            time.sleep(Timeout)

    # tear down messaging connection
    chan.close()
    conn.close()

    # return message dict
    return msg_dict


def get_worker_message():
    """Get a message from a worker.

    Returns message dictionary.  Returns None if no message available
    """

    # create exchange+queue, bound
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    chan.queue_declare(queue=Queue, durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(exchange=Exchange, type="direct", durable=True, auto_delete=False,)

    routing_key = WorkerRouting
    chan.queue_bind(queue=Queue, exchange=Exchange, routing_key=routing_key)

    # now get messages, convert from JSON and yield each one
    msg = chan.basic_get(queue=Queue, no_ack=True)
    if msg:
        msg_dict = json.loads(msg.body)
    else:
        msg_dict = None

    # tear down messaging connection
    chan.close()
    conn.close()

    # return message dict
    return msg_dict


if __name__ == '__main__':
    """Test a little."""

    User = 'user'
    Project = 'project'
    Scenario = 'scenario'
    Setup = 'setup'
    NumMessages = 3

    # send X messages to the worker(s)
    for i in range(NumMessages):
        print('Sending message to worker(s): instance=%d' % i)
        post_worker_message(User, Project, Scenario, Setup, instance=i, state='RUN')

    # pretend to be a worker, read each messages, respond with 2 (Start & STOP)
    for i in range(NumMessages):
        msg = get_server_message()
        instance = msg['instance']
        print('Worker got %s message, instance=%d, timestamp=%s'
              % (msg['state'], instance, msg['timestamp']))
        post_server_message(User, Project, Scenario, Setup, instance, state='START')
        post_server_message(User, Project, Scenario, Setup, instance, state='STOP')

    # now server reads worker messages
    while True:
        msg = get_worker_message()
        if msg is None:
            break
        print('From worker: state=%s, instance=%d, timestamp=%s'
              % (msg['state'], msg['instance'], msg['timestamp']))
