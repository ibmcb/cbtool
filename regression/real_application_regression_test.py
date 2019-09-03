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
from time import sleep, time, strftime
from optparse import OptionParser
from datetime import datetime

import fnmatch
import os
import pwd

home = os.environ["HOME"]
username = pwd.getpwuid(os.getuid())[0]

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

#---------------------------------- END CB API ---------------------------------

import prettytable

def print_msg(message, newline = True) :
    '''
    TBD
    '''
    if newline :
        print datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S') + ' ' + message
    else :
        print datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S') + ' ' + message,        

def get_type_list(options) :
    '''
    TBD
    '''
    _path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0)
    _fn = _path + "/../util/workloads_alias_mapping.txt"
    _fd = open(_fn, 'r')
    _fc = _fd.read()
    _cb_workload_alias = {}
    for _line in _fc.split('\n') :
        if _line[0] != "#" :
            _key, _contents = _line.split(' ')
            _cb_workload_alias[_key] = _contents
    _fd.close()
        
    if not options.typelist.count(',') :
        options.file_identifier = '_' + options.typelist
    else :
        options.file_identifier = ''
        
    if options.typelist == "all" :
        options.typelist="fake,synthetic,application-stress,scientific,transactional,data-centric"
        
    for _wks in options.typelist.split(',') :
        if _wks in _cb_workload_alias :
            options.typelist = options.typelist.replace(_wks, _cb_workload_alias[_wks])

    if options.headeronly :
        options.file_identifier = '_a0'
        options.typelist = ''

    return True
            
def cli_postional_argument_parser() :
    '''
    TBD
    '''

    if len(argv) < 2 :
        print_msg("./" + argv[0] + " <AI type1>,...,<AI typeN>")
        exit(1)

    _options, args = cli_named_option_parser()
            
    return _options

def retriable_cloud_connection(options, cloud_model, command) :
    '''
    TBD
    '''
    
    _api = False
    _attempts = 3
    _attempt = 0
    
    while not _api and _attempt < _attempts :

        try : 
    
            if cloud_model != "auto" :
                api_file_name = "/tmp/cb_api_" + username + '_' + cloud_model            
            else :
                api_file_name = "/tmp/cb_api_" + username

            if os.access(api_file_name, os.F_OK) :    
                try :
                    _fd = open(api_file_name, 'r')
                    _api_conn_info = _fd.read()
                    _fd.close()
                except :
                    _msg = "Unable to open file containing API connection information "
                    _msg += "(" + api_file_name + ")."
                    print_msg(_msg)
                    exit(4)
            else :
                _msg = "Unable to locate file containing API connection information "
                _msg += "(" + api_file_name + ")."
                print_msg(_msg)
                exit(4)
        
            _msg = "Connecting to API daemon (" + _api_conn_info + ")..."
            print_msg(_msg)
            _api = APIClient(_api_conn_info)
            return _api

        except :
            _api = False
            _attempt += 1
            sleep(10)



def cli_named_option_parser() :
    '''
    Reserved for future use
    '''
    usage = '''usage: %prog [options] [command]
    '''
    
    parser = OptionParser(usage)

    parser.add_option("-t", "--types", dest="typelist", default = "nullworklaod", help="Virtual Application Types to test")
    parser.add_option("-b", "--build", dest="build", default = "none", help="Base image to build from")
    parser.add_option("-w", "--wait", dest="wait", default = 900, help="How long to wait before declaring the test a failure (seconds)")
    parser.add_option("-i", "--interval", dest="interval", default = 30, help="Interval between attempts to obtain application performance samples (seconds)")
    parser.add_option("-s", "--samples", dest="samples", default = 2, help="How many application performance samples are required?")
    parser.add_option("-c", "--cloud_model", dest="cloud_model", default = "auto", help="Which cloud model should be used")        
    parser.add_option("--noheader", dest = "noheader", action = "store_true", help = "Do not print header")
    parser.add_option("--headeronly", dest = "headeronly", action = "store_true", help = "Print only header")
    (options, args) = parser.parse_args()

    return options, args

def main() :
    '''
    TBD
    '''
    if len(argv) < 2 :
        print_msg("./" + argv[0] + "--types <AI type1>,...,<AI typeN> --build [IMAGENAME or IMAGEID] --wait [S] --interval [S] --samples [N]")
        exit(1)

    _options = cli_postional_argument_parser()

    apiconn = retriable_cloud_connection(_options, str(_options.cloud_model).lower(), "/bin/true")
    
    try :
        cloud_attrs = apiconn.cldlist()[0]
        cloud_name = cloud_attrs["name"]
        cloud_model = cloud_attrs["model"]
    except :
        _msg = "ERROR: Unable to connect to API and get a list of attached clouds"
        print_msg(_msg)
        exit(1)

    _exit_code = 0
    
    _test_results_table = prettytable.PrettyTable(["Virtual".center(37, ' '), \
                                                   "SUT".center(72, ' '), \
                                                   "Management", \
                                                   " Management ".center(30, ' '), \
                                                   "Runtime", \
                                                   " Runtime ".center(64, ' '), \
                                                   "  Runtime  ".center(51, ' ')])

    _second_header = ["Application", '', "Report", "Metrics", "Report", "Metrics", "Missing" ]
    _test_results_table.add_row(_second_header)
    _third_header = [strftime("%Y-%m-%d"), strftime("%H:%M:%S"), "", "mgt_001-mgt_007", "", "id, prof, dur, compl, gen, tput, bw, lat", "Metrics" ]
    _test_results_table.add_row(_third_header)

    get_type_list(_options)

    for _type in _options.typelist.split(',') :

        if _type.count('|') :
            _type, _hypervisor_list = _type.split('|')
            _hypervisor_list = _hypervisor_list.split(',')
        else :
            _hypervisor_list = [ None ]

        _model_to_imguuid = {}
        _model_to_imguuid["sim"] = "baseimg"
        _model_to_imguuid["pcm"] = "xenial"
        _model_to_imguuid["plm"] = "xenial"        
        _model_to_imguuid["pdm"] = "ibmcb/cbtoolbt-ubuntu"
        _model_to_imguuid["nop"] = "baseimg"
        _model_to_imguuid["osk"] = "xenial3"
        _model_to_imguuid["os"] = "xenial3"        
        _model_to_imguuid["ec2"] = "ami-a9d276c9"
        _model_to_imguuid["gce"] = "ubuntu-1604-xenial-v20161221"
        _model_to_imguuid["do"] = "21669205"        
        _model_to_imguuid["slr"] = "1836627"        
        _model_to_imguuid["kub"] = "ibmcb/cbtoolbt-ubuntu"
        _model_to_imguuid["as"] = "b39f27a8b8c64d52b05eac6a62ebad85__Ubuntu-16_04-LTS-amd64-server-20180112-en-us-30GB"

        if str(_options.build).lower() == "auto" :
            _options.build = _model_to_imguuid[cloud_model]

        if _options.build :
            _actual_type = "build:" + _options.build + ':' + _type
        else :
            _actual_type = _type
            
        for _hypervisor_type in _hypervisor_list :
            
            _start = int(time())

            if _actual_type != "build:none:" :
                _mgt_pass, _rt_pass, _rt_missing, _sut = deploy_virtual_application(apiconn, \
                                                                                    _actual_type, \
                                                                                    _hypervisor_type, \
                                                                                    _options.samples, \
                                                                                    _options.wait, \
                                                                                    _options.interval)
    
#                _actual_type = _actual_type.replace("_lb",'')
                
                _duration = int(time()) - _start
                
                _results_row = []
                _results_row.append((_actual_type + " (" + str(_duration) + "s)").center(37, ' '))
                _results_row.append(_sut.center(72, ' '))            
    #            _results_row.append(_hypervisor_type)
                
                if _mgt_pass :
                    _results_row.append("PASS")
                    _results_row.append(_mgt_pass.center(30, ' '))
                else :
                    _results_row.append("FAIL")
                    _results_row.append(str(_mgt_pass).center(30, ' '))
                    _exit_code = 1
    
                if _rt_pass :
                    _results_row.append("PASS")                
                    _results_row.append(str(_rt_pass).center(64, ' '))
                else :
                    _results_row.append("FAIL")                
                    _results_row.append(str(_rt_pass).center(64, ' '))
                    _exit_code = 1
    
                if len(_rt_missing) < 5 :
                    _results_row.append(','.join(_rt_missing).replace("app_",''))
                else :
                    _results_row.append(','.join(_rt_missing[0:4]).replace("app_",'') + ",...")
    
                _test_results_table.add_row(_results_row)

            _x_test_results_table = _test_results_table.get_string().split('\n')

            _aux = _x_test_results_table[2]
            _x_test_results_table[2] = _x_test_results_table[3]
            _x_test_results_table[3] = _x_test_results_table[4]            
            _x_test_results_table[4] = _aux

            if not _options.headeronly :
                print '\n'.join(_x_test_results_table)

            if _options.noheader :
                _x_test_results_table = '\n'.join(_x_test_results_table[4:-1])
            else :
                if _options.headeronly :
                    _x_test_results_table = '\n'.join(_x_test_results_table[0:5])
                else :
                    _x_test_results_table = '\n'.join(_x_test_results_table)
        
        _fn = "/tmp/" + cloud_model + _options.file_identifier + "_real_application_regression_test.txt"
        _fh = open(_fn, "w")
        _fh.write(str(_x_test_results_table)+'\n')
        _fh.close()

        if not _options.noheader :
            print _x_test_results_table
                
    return True

    exit(_exit_code)
    
def deploy_virtual_application(apiconn, application_type, hypervisor_type, runtime_samples, timeout, check_interval) :
    '''
    TBD
    '''
    try :
        _vapp = None
        _sut = ''
        _management_metrics_pass = False
        _runtime_metrics_pass = False
        _runtime_metrics_problem = ''
        _runtime_missing_metrics = []
            
        _rt_m_list = "load_id,load_profile,load_duration,completion_time,datagen_time,throughput,bandwidth,latency"
        _aux_run_time_metrics = ''
                        
        cloud_name = apiconn.cldlist()[0]["name"]
        _crt_m = apiconn.cldshow(cloud_name,"mon_defaults")["crt_m"].split(',')
        _dst_m = apiconn.cldshow(cloud_name,"mon_defaults")["dst_m"].split(',')

        if application_type.count(':') :
            _x, _y, _actual_application_type = application_type.split(':')
        else :
            _actual_application_type = application_type

        _temp_attr_list_str = ''
        if _actual_application_type.count("_lb") :
            _actual_application_type = _actual_application_type.replace("_lb",'')
            _temp_attr_list_str = "load_balancer=true"

        if hypervisor_type :
            _msg = "Set hypervisor type to \"" + hypervisor_type + "\" on cloud \""
            _msg += cloud_name + "\"..."
            print_msg(_msg)
            _vapp = apiconn.cldalter(cloud_name, "vm_defaults", "hypervisor_type", hypervisor_type)

        _msg = "Creating a new Virtual Application Instance with type \"" 
        _msg += _actual_application_type + "\" on cloud \"" + cloud_name + "\"..."
        print_msg(_msg)
        _vapp = apiconn.appattach(cloud_name, _actual_application_type, temp_attr_list = _temp_attr_list_str)

        _sut = _vapp["sut"]
        
        _msg = "    Virtual Application \"" + _vapp["name"] + "\" deployed successfully"    
        print_msg(_msg)

        _vm_name_list = []
        _vm_uuid_list = []
        
        for _vm in _vapp["vms"].split(",") :
            _vm_uuid, _vm_role, _vm_name = _vm.split("|") 
            _vm_name_list.append(_vm_name)
            _vm_uuid_list.append(_vm_uuid)
            
        _msg = "    Checking reported provisioning metrics on instances " + ','.join(_vm_name_list) + "..." 
        print_msg(_msg)
        
        # Get some data from the monitoring system
        for _vm_uuid in _vm_uuid_list :
            for _management_metrics in apiconn.get_latest_management_data(cloud_name, _vm_uuid) :
                for _metric in _crt_m :
                    _msg = "        Checking metric \"" + _metric + "\"..."
                    print_msg(_msg, False)
                    if _metric not in _management_metrics :
                        print "NOK"
                    else :
                        _value = int(_management_metrics[_metric])
                        print str(_value) + " OK"

                        if _vm_uuid == _vapp["load_manager_vm"] :
                            if not _management_metrics_pass :
                                _management_metrics_pass = _management_metrics[_metric]
                            else :
                                _management_metrics_pass += ' ' + _management_metrics[_metric]

        _msg = "    Reported provisioning metrics OK" 
        print_msg(_msg)

        if _management_metrics_pass :
            _msg = "    Checking for at least " + str(runtime_samples) + " application"
            _msg += " performance metric samples..."
            print_msg(_msg)
            _initial_time = int(time())
            _curr_time = 0
            _collected_samples = 0
            _must_have_metrics_found = 0
            
            _app_m = apiconn.typeshow(cloud_name, _actual_application_type)["reported_metrics"].replace(", ",',').split(',')
            _app_m += [ "app_load_profile", "app_load_id", "app_load_level" ]
            
            _load_manager_vm_uuid = _vapp["load_manager_vm"]
            while _curr_time < timeout and _collected_samples < runtime_samples :
                try :
                    for _runtime_metrics in apiconn.get_latest_app_data(cloud_name, _load_manager_vm_uuid) :

                        for _metric in _app_m :
                            
                            if not _metric.count("app_") :
                                _metric = "app_" + _metric
    
                            _msg = "        Checking metric \"" + _metric + "\"..."
                            print_msg(_msg, False)                
                            if _metric not in _runtime_metrics :
                                if _metric not in _runtime_missing_metrics :
                                    _runtime_missing_metrics.append(_metric)
                                print "NOK"
                            elif _metric.count("completion_time") and \
                            (_runtime_metrics[_metric]["val"] == "0" or _runtime_metrics[_metric]["val"] == "0.0" or _runtime_metrics[_metric]["val"] == "NA" ) :
                                _runtime_metrics_problem = "|compl is zero or NA|"
                                _runtime_missing_metrics.append(_metric)
                                print "NOK"      
                            else :
                                if not _metric.count("load_profile") :
                                    try:
                                        _value = float(_runtime_metrics[_metric]["val"])
                                    except: 
                                        _value = str(_value)
                                else :
                                    _value = _runtime_metrics[_metric]["val"]                                    
                                print str(_value) + " OK"
                                if _metric == "app_load_id" :
                                    _collected_samples = _value

                        _aux_run_time_metrics = ''
                        
                        if _collected_samples >= runtime_samples :

                            for _m in _rt_m_list.split(',') :
                                _value = "NA"
    
                                _m = "app_" + _m
                                
                                if _m in _runtime_metrics :
                                    
                                    if not _m == "app_load_profile" :
                                        _value = str(round(float(_runtime_metrics[_m]["val"]),2))
                                        if _m == "app_throughput" or _m == "app_bandwidth" or _m == "app_latency" :
                                            if str(_runtime_metrics[_m]["val"]) != "NA" and str(_runtime_metrics[_m]["val"]) != "0" and str(_runtime_metrics[_m]["val"]) != "0.0" :
                                                _must_have_metrics_found +=1                                  
                                    else :
                                        _value = _runtime_metrics[_m]["val"]
                                
                                _aux_run_time_metrics += _value + ', '

                            _aux_run_time_metrics = _aux_run_time_metrics[0:-1]
                                    
                    print_msg("---------------------------------------- Sample " + str(_collected_samples))
                except :
                    _curr_time = int(time()) - _initial_time                    
                    _msg = "        No application performance metrics reported after "
                    _msg += str(_curr_time) + " seconds"
                    print_msg(_msg)

                _curr_time = int(time()) - _initial_time
                sleep(check_interval)

            if _collected_samples >= runtime_samples :
                if not _must_have_metrics_found :
                    _runtime_metrics_problem += " |tput, bw and lat are all zero or NA|"

                if not len(_aux_run_time_metrics[0:-1]) :
                    _runtime_metrics_problem += " |no metrics found on the sample|"                    

                if not _runtime_metrics_problem :
                    _runtime_metrics_pass = _aux_run_time_metrics[0:-1]                     
                    _msg = "    Reported application performance metrics OK"
                    print_msg(_msg)
                else :
                    _msg = "    Reported application performance metrics NOK: " + _runtime_metrics_problem
                    print_msg(_msg)
                                        
        if "uuid" in _vapp :
            _msg = "    Destroying Virtual Application \"" + _vapp["name"] + "\"..."
            print_msg(_msg)
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
            print_msg(_msg)

        _vapp = None

    except APIException, obj :
        error = True
        print_msg("API Problem (" + str(obj.status) + "): " + obj.msg)
    
    except APINoSuchMetricException, obj :
        error = True
        print_msg("API Problem (" + str(obj.status) + "): " + obj.msg)
    
    except KeyboardInterrupt :
        print_msg("Aborting this APP.")
    
    except Exception, msg :
        error = True
        print_msg("Problem during experiment: " + str(msg))
    
    finally :
        if _vapp is not None :
            try :
                if "name" not in _vapp :
                    _vapp["name"] = "NA"
                    
                if "uuid" in _vapp :
                    _msg = "Attempting to destroy Virtual Application \"" + _vapp["name"] + "\" again..."
                    print_msg(_msg, False)             
                    apiconn.appdetach(cloud_name, _vapp["uuid"])
                    print "DONE"
                    
            except APIException, obj :
                print_msg("Error finishing up: (\" + str(obj.status) + \"): " + obj.msg)
        else :
            try :            
                for _vapp in apiconn.applist(cloud_name) :
                    if _vapp["type"] == _actual_application_type :
                        _msg = "Attempting to destroy Virtual Application \"" + _vapp["name"] + "\" again..."
                        print_msg(_msg, False) 
                        apiconn.appdetach(cloud_name, _vapp["uuid"])                    
                        print "DONE"
                        
            except APIException, obj :
                print_msg("Error finishing up: (" + str(obj.status) + "): " + obj.msg)

        return _management_metrics_pass, _runtime_metrics_pass, _runtime_missing_metrics, _sut

main()