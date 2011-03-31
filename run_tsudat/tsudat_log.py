#!/usr/bin/env python

"""
A simple logger.

Allows a single logfile for an entire system as well as individual logfiles
for selected modules.  Each logfile can have separate logging levels, etc.

TODO: Use python logging, etc.
"""

import os
import sys
import datetime
import traceback


# the predefined logging levels
CRITICAL = 50
ERROR = 40
WARN = 30
INFO = 20
DEBUG = 10
NOTSET = 0

# a dictionary mapping the log level value to a display string
LevelNumToName = {NOTSET: 'NOTSET',
                  DEBUG: 'DEBUG',
                  INFO: 'INFO',
                  WARN: 'WARN',
                  ERROR: 'ERROR',
                  CRITICAL: 'CRITICAL'}

# some default settings
DefaultLevel = NOTSET
MaxModuleNameLen = 12


################################################################################
# A simple logger.
# 
# Simple usage:
#     import log
#     log = log.Log()
#     log('A line in the log at the default level (DEBUG)')
#     log('A log line at WARN level', Log.WARN)
#     log.debug('log line issued at DEBUG level')
# 
# Inspired by the 'borg' recipe from:
#     [http://code.activestate.com/recipes/66531/]
# 
# Log levels styled on the Python 'logging' module.
################################################################################

class Log(object):

    def __init__(self, logfile=None, level=DefaultLevel, append=False,
                 max_name_len=MaxModuleNameLen):
        """Initialise the logging object.
        
        logfile       the path to the log file
        level         logging level - don't log below this level
        append        True if log file is appended to
        max_name_len  the maximum allowed module name to display in log
        """

        # if no logfile given and there is a default logger, use it
        if logfile is None and 'DefaultObj' in globals():
            self.__dict__ = DefaultObj.__dict__
            # ignore level and max_name_len params
            return

        # no default logger, make up log filename if user didn't supply
        if logfile is None:
            # get caller module name, use it
            (caller_name, _) = self.caller_info()
            logfile = '%s.log' % caller_name

        # if no global logger yet, make this one global
        if not 'DefaultObj' in globals():
            globals()['DefaultObj'] = self

        # try to open log - a check for READONLY filesystem (ie, CD)
        try:
            if append:
                fd = open(logfile, 'a')
            else:
                fd = open(logfile, 'w')
        except IOError:
            # assume we have readonly filesystem
            basefile = os.path.basename(logfile)
            if sys.platform == 'win32':
                logfile = os.path.join('C:\\', basefile)
            else:
                logfile = os.path.join('~', basefile)
        else:
            fd.close()

        # try to open logfile again for real
        if append:
            self.logfd = open(logfile, 'a')
        else:
            self.logfd = open(logfile, 'w')

        # set attributes for this instance
        self.logfile = logfile
        self.level = level
        self.max_name_len = max_name_len

        # start the log with some information - date/time, level, etc.
        self.critical('='*55)
        self.critical('Log started on %s, log level=%s'
             % (datetime.datetime.now().ctime(),
                LevelNumToName[level]))
        self.critical('-'*55)

    def caller_info(self):
        """Get caller information - a helper routine.

        Find first traceback frame with name != this module's name.

        Return a tuple of (modulename, linenumber) of calling code.
        """

        frames = traceback.extract_stack()
        frames.reverse()
        try:
            (_, mod_name) = __name__.rsplit('.', 1)
        except ValueError:
            mod_name = __name__
        for (fpath, lnum, _, _) in frames:
            (fname, _) = os.path.basename(fpath).rsplit('.', 1)
            if fname != mod_name:
                break

        return (fname, lnum)

    def __call__(self, msg=None, level=None):
        """Call on the logging object.

        msg    message string to log
        level  level to log 'msg' at (if not given, assume self.level)
        """

        # get level to log at
        if level is None:
            level = self.level

        # are we going to log?
        if level < self.level:
            return

        if msg is None:
            msg = ''

        # get time
        to = datetime.datetime.now()
        hr = to.hour
        min = to.minute
        sec = to.second
        msec = to.microsecond

        # caller module and line number
        (fname, lnum) = self.caller_info()

        # get display string for log level
        loglevel = LevelNumToName[level]

        # write log message, then flush write to disk (maybe)
        fname = fname[:self.max_name_len]
        self.logfd.write('%02d:%02d:%02d.%06d|%8s|%*s:%-4d|%s\n'
                         % (hr, min, sec, msec, loglevel,
                            self.max_name_len, fname, lnum, msg))
        self.logfd.flush()

    def __del__(self):
        """When deleted, close log file."""

        self.logfd.close()

    ######
    # helper routines to log at particular levels
    ######

    def critical(self, msg):
        """Log a message at CRITICAL level."""

        self(msg, CRITICAL)

    def error(self, msg):
        """Log a message at ERROR level."""

        self(msg, ERROR)

    def warn(self, msg):
        """Log a message at WARN level."""

        self(msg, WARN)

    def info(self, msg):
        """Log a message at INFO level."""

        self(msg, INFO)

    def debug(self, msg):
        """Log a message at DEBUG level."""

        self(msg, DEBUG)

