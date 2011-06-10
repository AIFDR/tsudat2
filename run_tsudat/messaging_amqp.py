#!/usr/bin/env python

"""
Module containing rabbit/amqp messaging stuff.
Also contains amqp configuration stuff.
"""

import sys
import json
import time
from amqplib import client_0_8 as amqp

# AMQP configuration
MsgHost = '192.43.239.232:5672'
MsgUserid = 'guest'
MsgPassword = 'guest'
MsgVirtualHost = '/'
Exchange = 'sorting_room'
Queue = 'po_box'

WorkerRouting = 'worker'
ServerRouting = 'server'


# timeout if no message, in seconds
Timeout = 5.0


def post_server_message(message):
    """Send a message to the server.

    message   the message string
    """

    # create connection
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    # declare the exchange
    chan.exchange_declare(exchange=Exchange, type='direct',
                          durable=True, auto_delete=False)

    # send the message
    msg_obj = amqp.Message(message)
    msg_obj.properties["delivery_mode"] = 2
    routing_key = ServerRouting
    chan.basic_publish(msg_obj, exchange=Exchange, routing_key=routing_key)

    chan.close()
    conn.close()


def post_worker_message(message):
    """Send a message to the worker(s).

    message   the message string
    """

    # send the JSON
    conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                           password=MsgPassword, virtual_host=MsgVirtualHost,
                           insist=False)
    chan = conn.channel()

    # declare the exchange
    chan.exchange_declare(exchange=Exchange, type='direct',
                          durable=True, auto_delete=False)

    # send the message
    msg_obj = amqp.Message(message)
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
            message = msg.body
            break
        else:
            time.sleep(Timeout)

    # tear down messaging connection
    chan.close()
    conn.close()

    # return message dict
    return message


def get_worker_message():
    """Get a message from a worker.

    Returns message string.  Returns None if no message available
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
        message = msg.body
    else:
        message = None

    # tear down messaging connection
    chan.close()
    conn.close()

    # return message dict
    return message


if __name__ == '__main__':
    """Test a little."""

    User = 'user'
    Project = 'project'
    Scenario = 'scenario'
    Setup = 'setup'
    NumMessages = 3

    # send X messages to the worker(s)
    for i in range(NumMessages):
        message = 'Instance %s, state=RUN' % i
        print('Sending message to worker(s): %s' % message)
        post_worker_message(message)

    # pretend to be a worker, read each messages, respond with 2 (START & STOP)
    for i in range(NumMessages):
        msg = get_server_message()
        print('msg=%s' % str(msg))
        print('Worker got message: %s' % msg)
        post_server_message('START')
        post_server_message('STOP')

    # now server reads worker messages
    while True:
        msg = get_worker_message()
        if msg is None:
            break
        print('From worker: %s' % msg)
