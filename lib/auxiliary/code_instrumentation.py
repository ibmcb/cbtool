#!/usr/bin/env python

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

    @author: Marcio A. Silva
'''

from logging.handlers import logging
from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO
from sys import _getframe

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
    def loggedFunc(self, *args, **kwargs ):
        _log_suffix = ""
        try :
            _log_prefix = self.__module__ + ".py/"  + self.__class__.__name__
            _log_prefix += '.' + aFunc.__name__
        except AttributeError :
            _log_prefix = aFunc.__module__ + ".py/" + aFunc.__name__
        _msg = _log_prefix + " - Entry point " + _log_suffix
        logging.debug( _msg)
        try:
            result= aFunc(self, *args, **kwargs )
        except Exception, e:
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
    except Exception, msg :
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
        return not record.msg.count(self.expr)
    
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
