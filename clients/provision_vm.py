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
        print(_msg)
        exit(4)
else :
    _msg = "Unable to locate file containing API connection information "
    _msg += "(" + api_file_name + ")."
    print(_msg)
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
print(_msg)
api = APIClient(_api_conn_info)

#---------------------------------- END CB API ---------------------------------

if len(argv) < 3 :
        print("./" + argv[0] + " <cloud_name> <vm role>")
        exit(1)

_cloud_name = argv[1]
_vm_role = argv[2]

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
        print("Cloud " + _cloud_name + " not attached")
        exit(1)

    print("Setting new expid") 
    api.expid(_cloud_name, "NEWEXPID")
    
    print("creating new VM...")
    vm = api.vmattach(_cloud_name, _vm_role)

    print(vm["name"])

    print("Management performance metrics for VM \"" + vm["name"] + "....")
    _mgt_metric = api.get_latest_management_data(_cloud_name, vm["uuid"])
    print(_mgt_metric)

    # 'app' is a dicitionary containing all the details of the VMs and
    # applications the were created in the cloud

    print("CTRL-C to unpause...")
    while True :
        # Get some data from the monitoring system
        print("System (OS resource usage) performance metrics for VM \"" + vm["name"] + "....")
        _system_metric = api.get_latest_system_data(_cloud_name, vm["uuid"])
        print(_system_metric)     
        sleep(10)

    print("destroying VM...")

    api.vmdetach(_cloud_name, vm["uuid"])

except APIException as obj :
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)

except APINoSuchMetricException as obj :
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)

except KeyboardInterrupt :
    print("Aborting this VM.")

except Exception as msg :
    error = True
    print("Problem during experiment: " + str(msg))

finally :
    if vm is not None :
        try :
            if error :
                print("Destroying VM...")
                api.vmdetach(_cloud_name, vm["uuid"])
        except APIException as obj :
            print("Error finishing up: (" + str(obj.status) + "): " + obj.msg)
