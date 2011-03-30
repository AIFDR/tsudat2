#!/usr/bin/env python

"""A test run_tsudat script."""

import json


def run_tsudat(json_file):
    """Run a TsuDAT simulation.

    json_file  path to the JSON settings file
    """

    print('json_file=%s' % json_file)
    log.debug('json_file=%s' % json_file)

    with open(json_file) as fd:
        lines = fd.readlines()

    log('JSON:\n%s' % (''.join(lines)))
