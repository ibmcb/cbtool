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

from time import sleep
from api_service_client import *

'''
This is a Python example of how to provision a virtual machine through CloudBench

This assumes you have already attached to a cloud through the GUI or CLI.
'''

api = APIClient("http://172.16.1.222:7070")

try :
    error = False
    vm = None

    print "creating new VM..."
    vm = api.vmattach("SIM1", "tinyvm")

    print vm["name"]

    # Get some data from the monitoring system
    for data in api.get_latest_data("SIM1", vm["uuid"], "runtime_os_VM") :
        print data

    # 'vm' is a dicitionary containing all the details of the VM

    print "CTRL-C to unpause..."
    while True :
       sleep(10)

    print "destroying VM..."

    api.vmdetach("SIM1", vm["uuid"])

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
                api.vmdetach("SIM1", vm["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
