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
    Created on Nov 28, 2011

    Background Object Operations Library

    @author: Marcio A. Silva
'''

from uuid import uuid5, NAMESPACE_DNS
from random import randint
from subprocess import Popen, PIPE
from time import sleep

from ..auxiliary.code_instrumentation import trace, cblog, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from ..auxiliary.data_ops import dic2str, DataOpsException
from base_operations import BaseObjectOperations
from lib.auxiliary.data_ops import str2dic, dic2str

class BackgroundObjectOperations(BaseObjectOperations) :
    '''
        This file only had one function 'background_execute' which
        I needed to use inside ActiveOperations, so, since there was only
        one function, I just moved it to the base class.
        
        I don't see any reason to keep the Background class, but it's here
        just in case I forgot something.......
    '''
    
    pass

