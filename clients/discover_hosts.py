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

from sys import path

import fnmatch
import os

_home = os.environ["HOME"]

_path_set = False

for _path, _dirs, _files in os.walk(os.path.abspath(path[0] + "/../")):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        if _path.count("/lib/auxiliary") :
            path.append(_path.replace("/lib/auxiliary",''))
            _path_set = True
            break
    if _path_set :
        break

from lib.api.api_service_client import *

'''
This is a Python example of how to discover Hosts through CloudBench

This assumes you have already attached to a cloud through the GUI or CLI.
'''

api = APIClient("http://172.16.1.250:7070")

try :
    error = False
    hosts = None

    print "Getting hostlist....."
    _hosts = api.hostlist("TESTOPENSTACK")

    for _host in _hosts :
        _host_data = api.hostshow("TESTOPENSTACK", _host["name"])
        print _host_data

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except APINoSuchMetricException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    if hosts is not None :
        try :
            if error :
                print "Unable to get host list"
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
