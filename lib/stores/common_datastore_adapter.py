#!/usr/bin/env python

'''
    Created on June 30th, 2020

    Mysql data management operations library

    @author: Michael Galaxy 
'''

import os
import threading

from lib.auxiliary.config import get_my_parameters, set_my_parameters 
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from pwd import getpwuid

@trace
class MetricStoreMgdConnException(BaseException):
    def __init__(self, msg, status):
        BaseException.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg

'''
FIXME: There are many other details that need to be moved here,
in particular the table naming scheme.
'''

class MetricStoreMgdConn :
    @trace
    def __init__(self, parameters) :
        set_my_parameters(self, parameters)
        if isinstance(self.password, str) and self.password.lower() == "false" :
            self.password = False
        self.pid = "TEST_" + getpwuid(os.getuid())[0]

    @trace
    def mscp(self) :
        return get_my_parameters(self)
        
