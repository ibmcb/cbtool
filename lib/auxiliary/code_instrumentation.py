#!/usr/bin/env python3

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

'''
    Created on Nov 15, 2011

    Tracing and Debugging

    @author: Marcio A. Silva, Michael R. Galaxy
'''

from logging.handlers import logging, SysLogHandler
from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO
from sys import getsizeof, stderr, _getframe
from itertools import chain
from collections import deque
import sys
import socket
import builtins

try:
    from reprlib import repr
except ImportError:
    pass

bins = dir(builtins)

DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARN
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
STATUS = " status: "

def trace_nothing(aFunc):
    return aFunc

def trace_actual(aFunc):
    
    '''
    Trace entry, exit and exceptions.
    '''
    def loggedFunc(*args, **kwargs ):
        _log_suffix = ""
        try :
            _log_prefix = aFunc.__module__ + ".py/"  + aFunc.__class__.__name__
            _log_prefix += '.' + aFunc.__name__
        except AttributeError :
            _log_prefix = aFunc.__module__ + ".py/" + aFunc.__name__
        _msg = _log_prefix + " - Entry point " + _log_suffix
        logging.debug( _msg)
        
        try:
            result = aFunc(*args, **kwargs )
        except Exception as e:
            _msg = _log_prefix + " - Exit point (Exception \"" + str(e) + "\") "
            _msg += _log_suffix
            logging.debug(_msg)
            raise
        _msg = _log_prefix + " - Exit point " + _log_suffix
        logging.debug(_msg)
        return result
    loggedFunc.__name__= aFunc.__name__
    loggedFunc.__doc__= aFunc.__doc__
    
        
    return loggedFunc

#trace = trace_actual
trace = trace_nothing

def _cblog(*args):
    '''
    TBD
    '''
    try :
        # Need to improve this selection later
        _log_severity={}
        _log_severity[DEBUG] = logging.debug
        _log_severity[INFO] = logging.info
        _log_severity[WARN] = logging.warning
        _log_severity[ERROR] = logging.error
        _log_severity[CRITICAL] = logging.critical
        
        _print_on_console = False
        _in_the_same_line = False
        _log_suffix = ""
        _procid = ''
        
        if len(args) == 1 :
            _severity = DEBUG 
            _msg = args[0]
        elif len(args) == 2 :
            _severity = args[0]
            _msg = args[1]
        else :
            _severity = args[0]
            _msg = args[1]
            if len(args) == 3 :
                _print_on_console = args[2]
            if len(args) == 4 :
                _print_on_console = args[2]
                _in_the_same_line = args[3]
    
        f = _getframe(2)
    
        if 'processid' in f.f_locals :
            _procid = str(f.f_locals['processid'])

        try:
            # Local variable 'processid' takes precendence first
            # Only if this does not exist should we use the object-level 'self.pid'
            # during printing
            if _procid == '' and 'self' in f.f_locals :
                _procid = str(f.f_locals['self'].pid)
            _log_prefix = f.f_code.co_filename.split('/')[-1] + '/' 
            _log_prefix += f.f_locals['self'].__class__.__name__ + '.'
            _log_prefix += f.f_code.co_name

        except KeyError:
            _log_prefix = f.f_code.co_filename.split('/')[-1] + '/'
            _log_prefix += f.f_code.co_name
    
        if _print_on_console :
            _log_severity[_severity](STATUS + _msg,)
            
        _msg = _log_prefix + ' ' + _procid + " - " + _msg + _log_suffix
        _log_severity[_severity](_msg)
    
    except Exception as msg :
        print ("exception: " + str(msg) + " : " + _msg)

    return True

def cblog(*args) :
    '''
    TBD
    '''
    return _cblog(*args) 

def cbdebug(*args) :
    '''
    TBD
    '''
    return _cblog(DEBUG, *args)

def cberr(*args) :
    '''
    TBD
    '''
    return _cblog(ERROR, *args)

def cbinfo(*args) :
    '''
    TBD
    '''
    return _cblog(INFO, *args)

def cbwarn(*args) :
    '''
    TBD
    '''
    return _cblog(WARN, *args)

def cbcrit(*args) :
    '''
    TBD
    '''
    return _cblog(CRITICAL, *args)

class VerbosityFilter(Filter) :
    '''
    Allows the filtering out of messages from lower layer 
    modules/functions (e.g., ssh_ops, redis_dstore), implementing
    multi-level verbosity.
    '''
    def __init__(self, expr) :
        '''
        TBD
        '''
        self.expr = expr
        
    def filter(self, record) :
        '''
        TBD
        '''
        if isinstance(record.msg, str) :
            return not record.msg.count(self.expr)
        else :
            return False
    
class AntiMsgFilter(Filter) :
    '''
    Negative behavior of the MsgFilter
    '''
    def __init__(self, expr):
        self.expr = expr
    def filter(self, record) :
        return record.getMessage().count(self.expr)
    
class MsgFilter(Filter) :
    '''
    Allows the filtering out of messages from lower layer 
    modules/functions (e.g., ssh_ops, redis_dstore), implementing
    multi-level verbosity.
    '''
    def __init__(self, expr):
        self.expr = expr
    def filter(self, record) :
        return not record.getMessage().count(self.expr)

# Taken from https://code.activestate.com/recipes/577504/

def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(list(d.items()))
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file = stderr)

        for typ, handler in list(all_handlers.items()):
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


    print(total_size(d, verbose=True))

# Extend the class so that we emit a newline instead of the #000 character
# when running over TCP
# This bug was fixed in python v3, but not v2: https://bugs.python.org/issue12168
#
# Also further extend the class to handle TCP socket failure.
class ReconnectingNewlineSysLogHandler(logging.handlers.SysLogHandler):
    """Syslog handler that reconnects if the socket closes

    If we're writing to syslog with TCP and syslog restarts, the old TCP socket
    will no longer be writeable and we'll get a socket.error of type 32.  When
    than happens, use the default error handling, but also try to reconnect to
    the same host/port used before.  Also make 1 attempt to re-send the
    message.
    """
    def __init__(self, *args, **kwargs):
        super(ReconnectingNewlineSysLogHandler, self).__init__(*args, **kwargs)
        self._is_retry = False

    def _reconnect(self):
        """Make a new socket that is the same as the old one"""
        # close the existing socket before getting a new one to the same host/port
        if self.socket:
            self.socket.close()

        # cut/pasted from logging.handlers.SysLogHandler
        if self.unixsocket:
            self._connect_unixsocket(self.address)
        else:
            self.socket = socket.socket(socket.AF_INET, self.socktype)
            if self.socktype == socket.SOCK_STREAM:
                self.socket.connect(self.address)

    def handleError(self, record):
        # use the default error handling (writes an error message to stderr)
        #super(ReconnectingNewlineSysLogHandler, self).handleError(record)

        # If we get an error within a retry, just return.  We don't want an
        # infinite, recursive loop telling us something is broken.
        # This leaves the socket broken.
        if self._is_retry:
            return

        # Set the retry flag and begin deciding if this is a closed socket, and
        # trying to reconnect.
        self._is_retry = True
        try:
            __, exception, __ = sys.exc_info()
            # If the error is a broken pipe exception (32), get a new socket.
            if isinstance(exception, socket.error) and exception.errno == 32:
                try:
                    self._reconnect()
                except:
                    # If reconnecting fails, give up.
                    pass
                else:
                    # Make an effort to rescue the recod.
                    self.emit(record)
        finally:
            self._is_retry = False

    def emit(self, record):
        try:
            msg = self.format(record) + '\n'
            """
            We need to convert record level to lowercase, maybe this will
            change in the future.
            """
            prio = '<%d>' % self.encodePriority(self.facility,
                                                self.mapPriority(record.levelname))
            # Message is a string. Convert to bytes as required by RFC 5424
            if type(msg) is str:
                msg = msg.encode('utf-8')
            msg = prio.encode('utf-8') + msg
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except socket.error:
                    self.socket.close() # See issue 17981
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            elif self.socktype == socket.SOCK_DGRAM:
                self.socket.sendto(msg, self.address)
            else:
                self.socket.sendall(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
