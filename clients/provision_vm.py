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
This is a Python example of how to provision a virtual machine through CloudBench

This assumes you have already attached to a cloud through the GUI or CLI.
'''

from time import sleep
from sys import path

import os
import fnmatch

_home = os.environ["HOME"]
_api_endpoint = "10.10.0.3"
_cloud_name = "TESTOPENSTACK"
_vm_role = "tinyvm"

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from lib.api.api_service_client import *

api = APIClient("http://" + _api_endpoint + ":7070")

try :
    error = False
    vm = None

    _cloud_attached = False
    for _cloud in api.cldlist() :
        if _cloud["name"] == _cloud_name :
            _cloud_attached = True
            _cloud_model = _cloud["model"]
            break

    if not _cloud_attached :
        print "Cloud " + _cloud_name + " not attached"
        exit(1)

    print "creating new VM..."
    vm = api.vmattach(_cloud_name, _vm_role)

    print vm["name"]

    if _cloud_model != "sim" :
        # Get some data from the monitoring system
        for data in api.get_latest_data(_cloud_name, vm["uuid"], "runtime_os_VM") :
            print data

    # 'vm' is a dicitionary containing all the details of the VM

    print "CTRL-C to unpause..."
    while True :
        sleep(10)

    print "destroying VM..."

    api.vmdetach(_cloud_name, vm["uuid"])

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except APINoSuchMetricException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except KeyboardInterrupt :
    print "Aborting this VM."

except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    if vm is not None :
        try :
            if error :
                print "Destroying VM..."
                api.vmdetach(_cloud_name, vm["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
