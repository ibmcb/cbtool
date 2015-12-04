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
Library with common functions used by all experiments
'''

import itertools
import fnmatch
import json
import os
import pwd
import redis
import prettytable

from sys import path, argv, stdout
from time import sleep, time, strftime, strptime, localtime
from random import sample
from optparse import OptionParser
from datetime import datetime

def connect_to_cb(cloud_name) :
    '''
    TBD
    '''    
    home = os.environ["HOME"]
    username = pwd.getpwuid(os.getuid())[0]
    
    api_file_name = "/tmp/cb_api_" + username
    if os.access(api_file_name, os.F_OK) :    
        try :
            _fd = open(api_file_name, 'r')
            _api_conn_info = _fd.read()
            _fd.close()
            print 
            _msg = "#" * 75
            _msg += "\nFound CB API connection information in \"" + api_file_name + "\"\n"
            _msg += "#" * 75                
            print _msg
            sleep(3)

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
    
    for _location in [ os.path.abspath(path[0] + "/../"), home ]:
        for _path, _dirs, _files in os.walk(_location):
            for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
                if _path.count("/lib/auxiliary") :
                    _path_set = _path.replace("/lib/auxiliary",'')
                    path.append(_path_set)
                    break
                
            if _path_set :
                break
    
    if not _path_set :
        _msg = "Unable to find CB's client API library"
        print _msg
        exit(4)
    else :
        _msg = "#" * 75
        _msg += "\nCB API client library found in \"" + _path + "\".\n"
        _msg += "#" * 75                
        print _msg
        sleep(3)
        
    #from lib.api.api_service_client import *
    from lib.api.api_service_client import APIException,APINoSuchMetricException,APINoDataException,makeTimestamp,APIVM, APIClient

    _msg = "\nConnecting to API daemon (" + _api_conn_info + ")...\n"
    print _msg
    api = APIClient(_api_conn_info)

    _msg = "#" * 75
    _msg += "\nChecking connection to cloud \"" + cloud_name + "\"..."
    print _msg,
    api.hostlist(cloud_name)
    print "OK"
    print "#" * 75
    return api

def cloud_attach(options, api) :
    '''
    TBD
    '''
    attached=False
    for cloud in api.cldlist():
        if cloud['name'] == options.cloud_name : 
            attached=True
            
    if not attached:
        print '# Attaching to cloud %s'%(options.cloud_name)
        try:
            api.cldattach(options.cloud_model, options.cloud_name)
        except Exception, e:
            print 'Attachment failed: %s'%(str(e))
            exit(1)
            
    print '#' * 10 + " Attached to cloud %s" %(options.cloud_name)

    attached=False

    _vmcs = len(api.vmclist(options.cloud_name))
    if _vmcs > 1 :
        attached=True
        print '#' * 10 + " All VMCs (" + str(_vmcs) + ") attached to the cloud." 

    return True

def cloud_detach(options, api) :
    '''
    TBD
    '''
    
    print '# Detaching from VMC %s'%(options.vmc_name)
    try:
        api.vmcdetach(options.cloud_name, options.vmc_name)
        
    except Exception, e:
        print 'Detaching from VMC %s failed:\n %s'%(options.vmc_name, str(e))

    print '# Detaching from cloud %s'%(options.cloud_name)
    
    try:
        options.api.clddetach(options.cloud_name)
        
    except Exception, e:
        print 'Detaching from cloud %s failed:\n %s'%(options.cloud_name, str(e))

def cloud_cleanup(options, api) :
    '''
    TBD
    '''
    print '#' * 10 + "Cleaning up all AIs in cloud \"" + options.cloud_name + "\"...."        
    try:
        api.appdetach(options.cloud_name, 'all')        
    except Exception, e:
        print str(e)
        return False
    
    try:
        ailist = api.applist(options.cloud_name)
        for ai in ailist:
            print '#' * 10 + "Detaching AI %s" %(ai['uuid'])
            try:
                api.appdetach(options.cloud_name, ai['uuid'])
            except Exception, e:
                print str(e)
                return False
                            
    except Exception, e:
        print str(e)
        return False
    
    try:
        vmlist = api.vmlist(options.cloud_name)
        for vm in vmlist:
            print '#' * 10 + "Detaching VM %s" %(vm['uuid'])
            try:
                api.vmdetach(options.cloud_name, vm['uuid'])
            except Exception, e:
                print str(e)
                return False
                    
    except Exception, e:
        print str(e)
        return False
    
    return True

def get_network_parms(options, api) :
    '''
    TBD
    '''
    _net_mechanism = "NA"    
    if "networks" in dir(options) :
        _net_type = "NA"
        _netname = options.networks[0]

        for _vmc in api.vmclist(options.cloud_name) :
            _vmc_attr = api.vmcshow(options.cloud_name, _vmc["uuid"])
            
            if "network_" + _netname in _vmc_attr :
                _net_type = _vmc_attr["network_" + _netname]
                break
    else :
        _net_type = []

        for _vmc in api.vmclist(options.cloud_name) :
            _vmc_attr = api.vmcshow(options.cloud_name, _vmc["uuid"])

            for _attr in _vmc_attr.keys() :
                if _attr.count("network_") and not _attr.count("overcommit") :
                    _x_net_type = _vmc_attr[_attr]
                
                    if _x_net_type not in _net_type :
                        _net_type.append(_x_net_type)
                    
        if len(_net_type) :
            _net_type = '\\'.join(_net_type).upper()
        else :
            _net_type = "NA"

    for _host in api.hostlist(options.cloud_name) :
        if _host["function"] == "controller" :
            _host_attr = api.hostshow(options.cloud_name, _host["uuid"])    
            if "services" in _host_attr :
                if "neutron-openvswitch-agent" in _host_attr["services"] :
                    _net_mechanism = "OVS"
                    
                if "neutron-linuxbridge-agent" in _host_attr["services"] :
                    _net_mechanism = "LB"

    return _net_type, _net_mechanism

def get_compute_parms(options, api) :
    '''
    TBD
    '''
    _hypervisor_type = []

    for _host in api.hostlist(options.cloud_name) :
        if _host["function"] == "hypervisor" or _host["function"] == "compute" :
            if "hypervisor_type" in _host :
                if _host["hypervisor_type"] not in _hypervisor_type :
                    _hypervisor_type.append(_host["hypervisor_type"])

    if len(_hypervisor_type) :
        _hypervisor_type = '\\'.join(_hypervisor_type).upper()
    else :
        _hypervisor_type = "NA"
        
    return _hypervisor_type

def get_compute_nodes(options, api) :
    '''
    TBD
    '''
    _host_list = []

    for _host in api.hostlist(options.cloud_name) :
        if _host["function"] == "hypervisor" or _host["function"] == "compute" :
            if _host["hypervisor_type"].lower() == options.hypervisor.lower() :   
                _host_list.append(_host["name"].replace("host_",''))

    return _host_list

def get_controller_nodes(options, api) :
    '''
    TBD
    '''
    _host_list = []

    for _host in api.hostlist(options.cloud_name) :
        if _host["function"] != "hypervisor" and _host["function"] != "compute" :        
            _host_list.append(_host["name"].replace("host_",''))

    return _host_list

def list_private_networks(options, api) :
    '''
    TBD
    '''
    _network_list = [] 

    for _vmc in api.vmclist(options.cloud_name) :
        _vmc_attr = api.vmcshow(options.cloud_name, _vmc["uuid"])

        for _attr in _vmc_attr.keys() :
            if _attr.count("network_") and not _attr.count("overcommit") :
                _x_net_type = _vmc_attr[_attr]
                if _x_net_type == "gre" or _x_net_type == "vxlan" or _x_net_type == "vlan" :
                
                    if _x_net_type not in _network_list :
                        _network_list.append(_attr.replace("network_",''))                

    return _network_list

def selective_fault_injection(options, api, fault_clock) :
    '''
    TBD
    '''
    if not int(options.fault_duration) :

        return True
    else :
        
        _controller_list = get_controller_nodes(options, api)

        if fault_clock["time_to_next_repair"] > 0 :
            _elapsed_time = time() - fault_clock["loop_start_time"] 
            fault_clock["time_to_next_repair"] = fault_clock["time_to_next_repair"] - _elapsed_time
        elif fault_clock["time_to_next_repair"] == 0 :
            True
        else :
            for _element in api.stateshow(options.cloud_name) :
                if _element["type"] == "HOST" :
                    if _element["state"] == "fail" :
                        _msg = '#' * 15 + " Repairing host \"" + _element["name"].replace("host_", '') + "\""
                        print _msg                
                        api.hostrepair(options.cloud_name, _element["name"])
                        fault_clock["time_to_next_repair"] = 0
                                                      
    #    api.viewshow(options.cloud_name, "VM", "batch", str(_batch_id))        

        _elapsed_time = time() - fault_clock["loop_start_time"]
        fault_clock["time_to_next_fault"] = fault_clock["time_to_next_fault"] - _elapsed_time       

        if fault_clock["time_to_next_fault"] <= 0 :        
            _host = sample(_controller_list,1)[0]
            _msg = '#' * 15 + " Injecting fault \"" + options.fault_situation + "\" on host \"" + _host + "\""
            print _msg
            
            api.hostfail(options.cloud_name, _host, options.fault_situation)
            fault_clock["fault_base_time"] = time()
            fault_clock["time_to_next_fault"] = int(options.ift)              
            fault_clock["time_to_next_repair"] = int(options.fault_duration)

    return True

def prepare_host_ring_list(options, api) :
    '''
    TBD
    '''

    _msg = '#' * 10 + " Obtaining Host Ring pair list......"
    print _msg
    
    _host_list = get_compute_nodes(options, api)
    
    _host_ring_pair_list = []
    
    for _index in range(0, len(_host_list)) :

        if _index < len(_host_list) - 1 :
            _host_pair = [ _host_list[_index], _host_list[_index + 1] ]
        else :
            _host_pair = [ _host_list[_index], _host_list[0] ]

        _host_ring_pair_list.append(_host_pair)

    _msg = '#' * 10 + " Host Ring pair list is " + str(_host_ring_pair_list)
    print _msg
    
    return _host_ring_pair_list

def prepare_hostpair_list(options, api) :
    '''
    TBD
    '''

    _msg = '#' * 10 + " Obtaining Host pair list......"
    print _msg
    
    _host_list = get_compute_nodes(options, api)

    _host_pair_list = list(itertools.combinations(_host_list,2))

    _msg = '#' * 10 + " Host pair list is " + str(_host_pair_list)
    print _msg

    return _host_pair_list

def configure_vapp(options, api, workload, rate_limit, buffer_length) :
    '''
    TBD
    '''
    _msg = '#' * 10 + " Setting Virtual Application \"" + workload + "\" parameters "
    _msg += "\"load_level\" to " + options.flows_per_vm + ", \"load_duration\""
    _msg += " to " + options.load_duration + ", and \"load_profile\" to " 
    _msg += options.load_profile + "..."      
    print _msg
    
    api.typealter(options.cloud_name, workload, "load_level", options.flows_per_vm)
    api.typealter(options.cloud_name, workload, "load_duration", options.load_duration)
    api.typealter(options.cloud_name, workload, "load_level", options.flows_per_vm)
    api.typealter(options.cloud_name, workload, "load_profile", options.load_profile)

    if options.load_profile.count("udp") :
        api.typealter(options.cloud_name, workload, "rate_limit", str(int(rate_limit)/int(options.flows_per_vm))+'M')
        api.typealter(options.cloud_name, workload, "buffer_length", buffer_length)

    if options.external_target :
        api.typealter(options.cloud_name, workload, "external_target", options.external_target)        

    _msg = '#' * 10 + " Virtual Application \"" + workload + "\" configured."
    print _msg

    return True

def deploy_vapp(options, api, workload, hostpair, nr_ais = "1", \
                inter_vm_wait = 0, max_check = False):
    '''
    TBD
    '''

    _msg = '#' * 10 + " Deploying " + str(nr_ais) + " Virtual Application(s) of type \"" + workload + "\""
    _msg += " on the Host pair \"" + str(hostpair) + "\" (network"
    _msg += " pair " + str(options.networks) + ")..."
    print _msg    

    workload_attrs = api.typeshow(options.cloud_name, workload)

    _role_list = workload_attrs["role_list"].split(',')     

    _temp_attr_list_str = ''    
    for _role in _role_list :
        _temp_attr_list_str += _role + "_pref_host=" + hostpair[_role_list.index(_role)] + ','
        _temp_attr_list_str += _role + "_netname=" + options.networks[_role_list.index(_role)] + ',' 
    _temp_attr_list_str = _temp_attr_list_str[0:-1]

    if int(inter_vm_wait) :
        _async = nr_ais + ':' + inter_vm_wait
    else :
        _async = nr_ais

    _app_attr = api.appattach(options.cloud_name, workload, temp_attr_list = _temp_attr_list_str, async = nr_ais)

    if max_check :

        _stats = api.waituntil(options.cloud_name, "AI", "ARRIVING", 0, "decreasing", \
                               int(max_check)/10, int(max_check))

        _counters = _stats["experiment_counters"]
            
        if int(_counters["AI"]["failed"]) > 0 :
            _msg = '#' * 10 + " Error while deploying Virtual Application!"
            print _msg
            return False
        else :
            return _app_attr

        _msg = '#' * 10 + " Virtual Application \"" + workload + "\" has now ARRIVED."
        print _msg
    else :
        _msg = '#' * 10 + " Virtual Application \"" + workload + "\" is now ARRIVING."
        print _msg

    return _app_attr

def wait_until_vapp_deployed(options, api, curr_stats, nr_vapps, max_check, \
                             check_interval, pct_failure = 0) :
    '''
    TBD
    '''
    
    _target_reservations = int(curr_stats["reservations"]) + int(nr_vapps)
    
    _msg = '#' * 5 + " Waiting until all Virtual Applications (" + str(nr_vapps) 
    _msg += ") have RESERVATIONS in CB (i.e., they are in ARRIVING state)."
    print _msg

    _tm = time()
    _stats = api.waituntil(options.cloud_name, "AI", "RESERVATIONS", \
                           _target_reservations, "increasing", check_interval, \
                           max_check)

    _tm = int(time() - _tm)
    _msg = '#' * 5 + " After " + str(_tm )+ " seconds, all VApps started deployment. "
    _msg += "Waiting until all Virtual Applications (" + str(nr_vapps) 
    _msg += ") are fully deployed (i.e., they are in ARRIVED state)."
    print _msg
    _tm = time()
    
#    _stats = api.waituntil(options.cloud_name, "AI", "ARRIVING", 0, "decreasing", \
#                                      check_interval, max_check)

    _target_arrived = int(curr_stats["arrived"]) + int(nr_vapps)
    _stats = api.waituntil(options.cloud_name, "AI", "ARRIVED", _target_arrived,\
                           "increasing", check_interval, int(max_check))

    _counters = _stats["experiment_counters"]

    _failed_ais = int(_counters["AI"]["failed"]) - int(curr_stats["failed"])

    _pct_failed = 0    
    if int(_failed_ais) > 0 :
        _pct_failed = float(nr_vapps)/float(_failed_ais)
    
    if _pct_failed > pct_failure :
        
        _msg = "Error while deploying Virtual Applications! While attaching "
        _msg += str(nr_vapps) + " VApps, " + str(_failed_ais) + " have failed"
        print _msg
        
        _msg = "\nRemoving all " + str(nr_vapps) + " Virtual Applications\n"
        print _msg
        _tm = int(time() - _tm)
        api.appdetach(options.cloud_name, "all")

        _msg = "\nAfter " + str(_tm )+ " seconds, all Virtual Applications (" + str(nr_vapps) 
        _msg += ") are were removed."
        print _msg
        
        return False
    
    else :
        _tm = int(time() - _tm)        
        _msg = '#' * 5 + " After " + str(_tm )+ " seconds, all Virtual Applications (" + str(nr_vapps) 
        _msg += ") are fully deployed (i.e., they are in ARRIVED state)."
        print _msg
        return True
        
def remove_all_vapps(options, api, total_ais) :
    '''
    TBD
    '''
    _msg = "\n"
    _msg = '#' * 5 + " Removing all " + str(total_ais) + " Virtual Applications\n"
    print _msg
    _tm = time()
    api.appdetach(options.cloud_name, "all")
    _tm = int(time() - _tm)
    _msg = "\n"
    _msg = '#' * 5 + " After " + str(_tm )+ " seconds, all Virtual Applications "
    _msg += "(" + str(total_ais) + ") are were removed."
    print _msg
    
    return True

def makeTimestamp(supplied_epoch_time = False) :
    '''
    TBD
    '''
    if not supplied_epoch_time :
        _now = datetime.now()
    else :
        _now = datetime.fromtimestamp(supplied_epoch_time)

    _date = _now.date()

    result = ("%02d" % _date.month) + "/" + ("%02d" % _date.day) + "/" + ("%04d" % _date.year)

    result += strftime(" %I:%M:%S %p",
                        strptime(str(_now.hour) + ":" + str(_now.minute) + ":" + \
                                 str(_now.second), "%H:%M:%S"))

    result += strftime(" %Z", localtime(time()))
    return result

def check_samples(options, api, start_time, max_time) :
    '''
    TBD
    '''

    _ai_table_header = [ "AI", "LOAD_ID", "BANDWIDTH", "THROUGHPUT", "JITTER", "LOSS" ]
    _ai_table = prettytable.PrettyTable(_ai_table_header)

    _min_samples = 100000000000

    for _ai in api.applist(options.cloud_name) :
        _vm_uuid = _ai["load_generator_vm"]        

        _ai_table_line = []

        _vapp_metrics_list = api.get_performance_data(options.cloud_name, _vm_uuid, \
                                                      metric_class = "runtime", \
                                                      object_type = "VM", \
                                                      metric_type = "app", \
                                                      latest = True)

        if _vapp_metrics_list :
            for _vapp_metrics in _vapp_metrics_list :
    
                if "uuid" in _vapp_metrics :
                    _ai_table_line.append(_vapp_metrics["uuid"])
                else :
                    _ai_table_line.append("NA")
    
                for _value in _ai_table_header[1:] :
                    _value = "app_" + _value.lower()
                    
                    if _value in _vapp_metrics :
                        
                        if _value == "app_load_id" :
                            if _min_samples > int(_vapp_metrics[_value]["val"]) :
                                _min_samples = int(_vapp_metrics[_value]["val"])
                        _ai_table_line.append(_vapp_metrics[_value]["val"])                        
                    else :
                        _ai_table_line.append("NA")
    
            if len(_ai_table_line) == len(_ai_table_header) :
                _ai_table.add_row(_ai_table_line) 

    if _min_samples == 100000000000 :
        _min_samples = 0
    
    _elapsed_time = int(time()) - start_time

    if int(_min_samples) >= int(options.num_samples) :
        _msg = "All Virtual Applications (AIs) reported at least " + str(_min_samples)
        _msg += " application performance metrics samples."
        _msg += "Finishing the experiment after " + str(_elapsed_time) + " seconds."
        print _msg
        print _ai_table        
        return False
    else :
        if float(_elapsed_time) > float(max_time) :
            _msg = "At least one Virtual Application (AI) reported fewer application "
            _msg += "performance metrics samples (" + str(_min_samples) + ") than the"
            _msg += " minimum required (" + str(options.num_samples) + "), but the experiment"
            _msg += " will be finished due to the specified time limit (" + str(max_time) + ")."
            _msg += "Finishing the experiment after " + str(_elapsed_time) + " seconds."
            print _msg
            print _ai_table        
            return False
    
        else :
            _msg = "At least one Virtual Application (AI) reported fewer application "
            _msg += "performance metrics samples (" + str(_min_samples) + ") than the"
            _msg += " minimum required (" + str(options.num_samples) + "), and the experiment"
            _msg += " has not yet reached the specified time limit (" + str(max_time)
            _msg += "). Remaining time until end: " + str(max_time - _elapsed_time)
            _msg += " seconds."
            print _msg
            print _ai_table        
            return True

def host_to_host(options, api, experiment_id):
    '''
    TBD
    '''
    _ai2host = {}
    _vm2host = {}

    _host_list = []    
    _ai_list = []
    _mgt_reported_vm_uuids = []

    _cb_dirs = api.cldshow(options.cloud_name, "space")

    _cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])

    for _mgt_metrics in api.get_performance_data(options.cloud_name, \
                                                 None, \
                                                 metric_class = "management", \
                                                 object_type = "VM", \
                                                 latest = False, \
                                                 expid = experiment_id) :

        _vm_uuid = _mgt_metrics["uuid"]
        _ai_uuid = _mgt_metrics["ai"]
        
        if _vm_uuid not in _mgt_reported_vm_uuids :
            _mgt_reported_vm_uuids.append(_vm_uuid)
            
        _vm_role = _mgt_metrics["role"]
        _host_name = _mgt_metrics["host_name"]

        if _mgt_metrics["type"] == "xping" :
            _metric = "app_latency"            
        else :
            _metric = "app_bandwidth"

        if _vm_uuid not in _vm2host :
            _vm2host[_vm_uuid] = {}
            
        _vm2host[_vm_uuid]["host"] = _host_name
        _vm2host[_vm_uuid]["ai"] = _ai_uuid

        if _host_name not in _host_list :
            _host_list.append(str(_host_name))
                    
        if _ai_uuid not in _ai2host :
            _ai2host[_ai_uuid] = {}
            
        if _vm_role.count("client") or _vm_role.count("sender") :                
            _ai2host[_ai_uuid]["sender"] = _host_name            
        else :
            _ai2host[_ai_uuid]["receiver"] = _host_name               

    for _vm in _vm2host.keys() :
        _ai = _vm2host[_vm]["ai"]

        _vm2host[_vm].update(_ai2host[_ai])

    sorted(_host_list)
    _host_table = prettytable.PrettyTable([ "s->r" ] + _host_list)

    if _metric == "app_bandwidth" :  
        _best = 0
    else :
        _best = 100000
        
    _app_reported_vm_uuids = []
    
    for _vm_uuid in _mgt_reported_vm_uuids :

        _vm_app_metrics = api.get_performance_data(options.cloud_name, \
                                                    _vm_uuid, \
                                                    metric_class = "runtime", \
                                                    object_type = "VM", \
                                                    metric_type = "app", \
                                                    latest = False, \
                                                    samples = 1, \
                                                    expid = experiment_id)
    
        if _vm_app_metrics :
            _vm_uuid = _vm_app_metrics["uuid"]
            _val = _vm_app_metrics[_metric]["avg"]

            if _metric == "app_bandwidth" :            
                if _val > _best :
                    _best = _val
            else :
                if _val < _best :
                    _best = _val
                                    
            _app_reported_vm_uuids.append(_vm_uuid)
            _vm2host[_vm_uuid]["val"] = _vm_app_metrics[_metric]["avg"]

    _host_pairs = {}
    
    for _vm_uuid in _app_reported_vm_uuids :
        
        _sender = _vm2host[_vm_uuid]["sender"]
        _receiver = _vm2host[_vm_uuid]["receiver"]
        
        if "val" in _vm2host[_vm_uuid] :
            _val = _vm2host[_vm_uuid]["val"]
        else :
            _val = "NR"
            
        _host_pairs[_sender + "->" + _receiver] = _val

    for _sender in _host_list :
        _line = [ _sender ]
        
        for _receiver in _host_list :
            _key = _sender + "->" + _receiver
            
            if _key in _host_pairs :
                _line.append(round(_host_pairs[_key]/_best,5))
            else :
                _line.append("NA")
            
        _host_table.add_row(_line)

    print _host_table

    _fn = _cb_data_dir + '/' + experiment_id + "/host_to_host.txt"
    _fh = open(_fn, "w")
    _fh.write(str(_host_table))
    _fh.close()
    
    return _host_table
    
#---------------------------------- MAIN LOOP ----------------------------------

def cli_named_option_parser() :
    '''
    Reserved for future use
    '''
    usage = '''usage: %prog [options] [command]
    '''
    
    parser = OptionParser(usage)

    (options, args) = parser.parse_args()

    return options, args