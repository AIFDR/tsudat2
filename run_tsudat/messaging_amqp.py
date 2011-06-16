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


class ServerMessages(object):
    """Class to read from the server queue.

    If reading an processing with ACK:
        c = ServerMessages()
        while True:
            msg = c.recv_message()
            if msg is None:
                break
            # prolonged processing here
            c.ack_message()

    """

    def __init__(self):
        """Initialise the system.

        Uses default configuration, allow override later.
        """

        # create exchange+queue, bound
        self.conn = amqp.Connection(host=MsgHost, userid=MsgUserid,
                                    password=MsgPassword, virtual_host=MsgVirtualHost,
                                    insist=False)
        self.chan = self.conn.channel()

        self.chan.queue_declare(queue=Queue, durable=True, exclusive=False, auto_delete=False)
        self.chan.exchange_declare(exchange=Exchange, type="direct", durable=True, auto_delete=False,)

        routing_key = WorkerRouting
        self.chan.queue_bind(queue=Queue, exchange=Exchange, routing_key=routing_key)

    def recv_message(self, no_ack=False):
        """Receive a message from the queue.

        no_ack  if True, don't need to ACK messages

        Returns a message if there is one, else None.
        """

        # now get a messages
        msg = self.chan.basic_get(queue=Queue, no_ack=False)
        if msg:
            message = msg.body
            if no_ack:
                self.delivery_tag = None
            else:
                self.delivery_tag = msg.delivery_tag
        else:
            message = None
            self.delivery_tag = None

        return message

    def ack_message(self):
        """ACK the message we just read."""

        if self.delivery_tag is None:
            # error, can't ACK
            msg = "Can't ACK as no message read?"
            raise Exception(msg)

        self.chan.basic_ack(self.delivery_tag)

    def __del__(self):
        """Destroy the messaging infrastructure."""

        # tear down messaging connection
        self.chan.close()
        self.conn.close()
        
        
    
if __name__ == '__main__':
    """Test class ServerMessages() a little."""

    User = 'user'
    Project = 'project'
    Scenario = 'scenario'
    Setup = 'setup'
    NumMessages = 3

    """
    # send X messages to the server queue
    for i in range(NumMessages):
        message = 'Instance %s, state=RUN' % i
        print('Sending message to worker(s): %s' % message)
        post_server_message(message)

    """

    # pretend to be the server, read each message
    c = ServerMessages()
    while True:
        msg = c.recv_message()
        if msg is None:
            break
        print('Server got message: %s' % msg)
        c.ack_message()
    del c
