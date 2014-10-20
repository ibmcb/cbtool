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
This is a Python example of how to provision an Application through CloudBench

This assumes you have already attached to a cloud through the GUI or CLI.
'''
#--------------------------------- START CB API --------------------------------

from sys import path, argv
from time import sleep

import fnmatch
import os
import pwd

home = os.environ["HOME"]
username = pwd.getpwuid(os.getuid())[0]

api_file_name = "/tmp/cb_api_" + username
if os.access(api_file_name, os.F_OK) :    
    try :
        _fd = open(api_file_name, 'r')
        _api_conn_info = _fd.read()
        _fd.close()
    except :
        _msg = "Unable to open file containing API connection information "
        _msg += "(" + api_file_name + ")."
        print _msg
        exit(4)
else :
    _msg = "Unable to locate file containing API connection information "
    _msg += "(" + api_file_name + ")."
    print _msg
    exit(4)

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

_msg = "Connecting to API daemon (" + _api_conn_info + ")..."
print _msg
api = APIClient(_api_conn_info)

#---------------------------------- END CB API ---------------------------------

if len(argv) < 3 :
        print "./" + argv[0] + " <cloud_name> <vapp type>"
        exit(1)

cloud_name = argv[1]
workload = argv[2]

try :
    error = False
    app = None

    print "Setting new expid" 
    api.expid(cloud_name, "NEWEXPID")

    print "creating new application..."
    app = api.appattach(cloud_name, workload)

    print app["name"]

    for vm in app["vms"].split(",") :
        uuid, role, name = vm.split("|")
        print "Management performance metrics for VM \"" + name + "...."
        _mgt_metric = api.get_latest_management_data(cloud_name, uuid)
        print _mgt_metric

    # 'app' is a dicitionary containing all the details of the VMs and
    # applications the were created in the cloud

    print "CTRL-C to unpause..."
    while True :
        # Get some data from the monitoring system
        for vm in app["vms"].split(",") :
            uuid, role, name = vm.split("|")
            print "Application performance metrics for VM \"" + name + "...."
            _app_metric = api.get_latest_app_data(cloud_name, uuid)
            print _app_metric        
        sleep(10)

    print "destroying application..."

    api.appdetach(cloud_name, app["uuid"])

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except APINoSuchMetricException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except KeyboardInterrupt :
    print "Aborting this APP."

except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    if app is not None :
        try :
            if error :
                print "Destroying application..."
                api.appdetach(cloud_name, app["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
