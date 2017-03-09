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
from time import sleep, time

import fnmatch
import os
import pwd

home = os.environ["HOME"]
username = pwd.getpwuid(os.getuid())[0]

api_file_name = "/tmp/cb_api_" + username
if os.access(api_file_name, os.F_OK) :    
    try :
        _fd = open(api_file_name, 'r')
        api_conn_info = _fd.read()
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

_msg = "Connecting to API daemon (" + api_conn_info + ")..."
print _msg
api = APIClient(api_conn_info)

#---------------------------------- END CB API ---------------------------------

import prettytable

    
#_usage = "./" + argv[0] + " <cloud_name>"

#if len(argv) < 2 :
#    print _usage
#    exit(1)

#cloud_name = argv[1]

def main(apiconn) :
    '''
    TBD
    '''
    _timeout = 900
    _check_interval = 30
    _runtime_samples = 3

    if len(argv) < 2 :
        print "./" + argv[0] + " <AI type1>,...,<AI typeN>"
        exit(1)
    
    _type_list = argv[1].split(',')
    
    try :
        cloud_name = apiconn.cldlist()[0]["name"]
    except :
        _msg = "ERROR: Unable to connect to API and get a list of attached clouds"
        exit(1)

    _test_results_table = prettytable.PrettyTable(["Virtual Application", \
                                                   "Hypervisor Type", \
                                                   "Management Report Pass?", \
                                                   "Runtime Report Pass?"])

    for _type in _type_list :

        if _type.count('|') :
            _type, _hypervisor_list = _type.split('|')
            _hypervisor_list = _hypervisor_list.split(',')            
        else :
            _hypervisor_list = [ None ]
            
        for _hypervisor_type in _hypervisor_list :
            _mgt_pass, _rt_pass = deploy_virtual_application(api, _type, _hypervisor_type, _runtime_samples, _timeout, _check_interval)

            _results_row = []
            _results_row.append(_type)
            _results_row.append(_hypervisor_type)
            _results_row.append(str(_mgt_pass))
            _results_row.append(str(_rt_pass))
    
            _test_results_table.add_row(_results_row)

            _fn = "/tmp/real_application_regression_test.txt"
            _fh = open(_fn, "w")
            _fh.write(str(_test_results_table))
            _fh.close()

            print _test_results_table
    
    return True
    
def deploy_virtual_application(apiconn, application_type, hypervisor_type, runtime_samples, timeout, check_interval) :
    '''
    TBD
    '''
    try :
        _vapp = None
        _management_metrics_pass = False
        _runtime_metrics_pass = False

        cloud_name = apiconn.cldlist()[0]["name"]
        _crt_m = apiconn.cldshow(cloud_name,"mon_defaults")["crt_m"].split(',')
        _dst_m = apiconn.cldshow(cloud_name,"mon_defaults")["dst_m"].split(',')

        if hypervisor_type :
            _msg = "Set hypervisor type to \"" + hypervisor_type + "\" on cloud \""
            _msg += cloud_name + "\"..."
            print _msg
            _vapp = apiconn.cldalter(cloud_name, "vm_defaults", "hypervisor_type", hypervisor_type)

        _msg = "Creating a new Virtual Application Instance with type \"" 
        _msg += application_type + "\" on cloud \"" + cloud_name + "\"..."
        print _msg
        _vapp = apiconn.appattach(cloud_name, application_type)

        _msg = "    Virtual Application \"" + _vapp["name"] + "\" deployed successfully"    
        print _msg

        _msg = "    Checking reported provisioning metrics..." 
        print _msg
        # Get some data from the monitoring system
        for _vm in _vapp["vms"].split(",") :
            _vm_uuid, _vm_role, _vm_name = _vm.split("|") 
            for _management_metrics in apiconn.get_latest_management_data(cloud_name, _vm_uuid) :
                for _metric in _crt_m :
                    _msg = "        Checking metric \"" + _metric + "\"..."
                    print _msg,
                    if _metric not in _management_metrics :
                        print "NOK"
                    else :
                        _value = int(_management_metrics[_metric])
                        print str(_value) + " OK"

        _msg = "    Reported provisioning metrics OK" 
        print _msg
        _management_metrics_pass = True

        if _management_metrics_pass :
            _msg = "    Checking for at least " + str(runtime_samples) + " application"
            _msg += " performance metric samples..."
            print _msg
            _initial_time = int(time())
            _curr_time = 0
            _collected_samples = 0

            _app_m = apiconn.typeshow(cloud_name, application_type)["reported_metrics"].split(',')
            _app_m += [ "app_load_profile", "app_load_id", "app_load_level"]

            _load_manager_vm_uuid = _vapp["load_manager_vm"]
            while _curr_time < timeout and _collected_samples < runtime_samples :
                try :
                    for _runtime_metrics in apiconn.get_latest_app_data(cloud_name, _load_manager_vm_uuid) :
                        for _metric in _app_m :
                            
                            if not _metric.count("app_") :
                                _metric = "app_" + _metric
    
                            _msg = "        Checking metric \"" + _metric + "\"..."
                            print _msg,                
                            if _metric not in _runtime_metrics :
                                print "NOK"
                            else :
                                if not _metric.count("load_profile") :
                                    _value = float(_runtime_metrics[_metric]["val"])
                                print str(_value) + " OK"
                                if _metric == "app_load_id" :
                                    _collected_samples = _value
                    print "----------------------------------------"                                    
                except :
                    _curr_time = int(time()) - _initial_time                    
                    _msg = "        No application performance metrics reported after "
                    _msg += str(_curr_time) + " seconds"
                    print _msg

                _curr_time = int(time()) - _initial_time
                sleep(check_interval)

            if _collected_samples >= runtime_samples :
                _runtime_metrics_pass = True
                _msg = "    Reported application performance metrics OK"
                print _msg

        if "uuid" in _vapp :
            _msg = "    Destroying Virtual Application \"" + _vapp["name"] + "\"..."
            print _msg
            apiconn.appdetach(cloud_name, _vapp["uuid"])

        _msg = "    Checking reported deprovisioning metrics..." 
        print _msg
        # Get some data from the monitoring system
        for _vm in _vapp["vms"].split(",") :
            _vm_uuid, _vm_role, _vm_name = _vm.split("|") 
            for _management_metrics in apiconn.get_management_data(cloud_name, _vm_uuid) :
                for _metric in _dst_m :
                    _msg = "        Checking metric \"" + _metric + "\"..."
                    print _msg,
                    if _metric not in _management_metrics :
                        _management_metrics_pass = False
                        print "NOK"
                    else :
                        _value = int(_management_metrics[_metric])                        
                        print str(_value) + " OK"

        if _management_metrics_pass :
            _msg = "    Reported deprovisioning metrics OK" 
            print _msg

        _vapp = None

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
        if _vapp is not None :
            try :
                if "name" not in _vapp :
                    _vapp["name"] = "NA"
                    
                if "uuid" in _vapp :
                    _msg = "Attempting to destroy Virtual Application \"" + _vapp["name"] + "\" again..."
                    print _msg,             
                    apiconn.appdetach(cloud_name, _vapp["uuid"])
                    print "DONE"
                    
            except APIException, obj :
                print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
        else :
            try :            
                for _vapp in apiconn.applist(cloud_name) :
                    if _vapp["type"] == application_type :
                        _msg = "Attempting to destroy Virtual Application \"" + _vapp["name"] + "\" again..."
                        print _msg,             
                        apiconn.appdetach(cloud_name, _vapp["uuid"])                    
                        print "DONE"
                        
            except APIException, obj :
                print "Error finishing up: (" + str(obj.status) + "): " + obj.msg

        return _management_metrics_pass, _runtime_metrics_pass
    
main(api)
