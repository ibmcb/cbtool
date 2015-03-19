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

_cloud_name = argv[1]
_workload = argv[2]

import yaml
_retrun_msg = ""

def _check_sla(_yaml, _api,uuid, _current_ai, _all_ai) :
    _check_data = 0 
    print _yaml
    print uuid
    while True :
        _check_data+=1
        print "Waiting for Application Data from AI: %s, attempt %s" % (_current_ai['uuid'], _check_data)
        try : 
            if _check_data > 50 : 
                _return_msg = "Failed to retrieve Application Metrics"
                return False
            _data = _api.get_latest_app_data(_cloud_name,uuid)
            print _data 
            break
        except APINoSuchMetricException, obj :
            sleep(10)
            continue

    return False 

_launched_ais = []
_sla = open('./SPEC_SLA.yaml')
_yaml = yaml.safe_load(_sla)
_sla.close()

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

    ai_return_state=True

    print "Launching AI %s" % _workload
    print "Guest, Provison complete, Network accessible, Last Known state"
    while ai_return_state :
#----------------------- Create Apps over time ----------------------------------
        app = api.appattach(_cloud_name, _workload)
        vms = [ val.split("|")[0] for val in app["vms"].split(",")]
        _data_uuid = ""
        for vm in vms :
            _guest_data = api.get_latest_management_data(_cloud_name,vm)
            if _guest_data["cloud_hostname"].find("ycsb") != -1 :
                _data_uuid = _guest_data["uuid"]
                print "%s ,%s, %s, %s" % (_guest_data["cloud_hostname"], \
                                          _guest_data["mgt_003_provisioning_request_completed"], \
                                          _guest_data["mgt_004_network_acessible"], \
                                          _guest_data["last_known_state"])
        _launched_ais.append(app)
        ai_return_state=_check_sla(_yaml,api,_data_uuid,app,_launched_ais)

    print "Removing all AIs"
    api.appdetach(_cloud_name, app["uuid"])

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
    if app is not None :
        try :
            if error :
                print "Destroying VM..."
                api.appdetach(_cloud_name, app["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg