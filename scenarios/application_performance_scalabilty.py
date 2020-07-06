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
This is scenario exemplifies how to use CloudBench to ascertain application scalability.
At the moment, this is heavily tailored for a simulated cloud (the main goal of
this code is exemplify the use of APIs in long range (several hours to days) and
large scale (thousands of VMs) experiments.

This assumes you have already attached to a cloud through the GUI or CLI.
'''
import itertools
import fnmatch
import json
import os
import pwd
import redis
import prettytable

from sys import path, argv
from time import sleep, time
from optparse import OptionParser

from common import *

def set_provisioning_sla(options, api, workload_attrs, slaprov) :
    '''
    TBD
    '''
    for _role in workload_attrs["role_list"].split(',') :
        api.typealter(options.cloud_name, options.workload, _role + "_sla_provisioning_target", str(slaprov))

    return True

def set_runtime_sla(options, api, workload_attrs, metric, value) :
    '''
    TBD
    '''
    if metric.count("latency") or metric.count("_time") :
        _limit = "lt"
    elif metric.count("bandwidth") or metric.count("throughput") :
        _limit = "gt"
    else :
        _limit = "gt"
    
    api.typealter(options.cloud_name, options.workload, "sla_runtime_target_" + metric, str(value) + '-' + _limit)

    return True

def subscribe(options, api, channel) :
    '''
    TBD
    '''
    _obj_stor_attr = api.waiton(options.cloud_name,"VM",channel,"getsubscription",1)

    redis_conn = redis.Redis(host = _obj_stor_attr["host"], port = 6379, db = _obj_stor_attr["dbid"], decode_responses=True)
        
    redis_conn_pubsub = redis_conn.pubsub()
    redis_conn_pubsub.subscribe(_obj_stor_attr["subscription"])

    _msg = "Will wait for messages published by VMs..."
    print _msg
    
    for message in redis_conn_pubsub.listen() :
        if isinstance(message["data"], str) :
            _msg = "Message detected, getting statistics from CB"
            print _msg            
            _stats = api.stats(options.cloud_name)
            
            return _stats    

def check_stopping_conditions(options, \
                              api, \
                              stats, \
                              minimum_ais, 
                              failed_vms_pct, \
                              sla_provisioning_violated_vms_pct, \
                              sla_runtime_violated_vms_pct, \
                              app_errors_vms_pct, \
                              cumulative_run_errors_pct) :
    '''
    TBD
    '''

    _stopping_condition = False
    
    print "Checking stopping conditions"    
    _exp_counters = stats["experiment_counters"]

    print "TOTAL AIs: " + _exp_counters["AI"]["arrived"]     
    
    if int(_exp_counters["AI"]["arrived"]) < minimum_ais:
        print "Do not check stopping conditions with less than " + str(minimum_ais) + " AIs."
        return _stopping_condition
        
    print "TOTAL VMs: " + _exp_counters["VM"]["arrived"]
    print "FAILED VMs: " + _exp_counters["VM"]["failed"]
    print "FAILED VMs stopping condition: ",
        
    _failed_vms_pct = float(_exp_counters["VM"]["failed"])/float(_exp_counters["VM"]["arrived"])

    if _failed_vms_pct >= failed_vms_pct :
        print " YES ",
        _stopping_condition = True
    else :
        print " NO ",

    print " (target " + str(failed_vms_pct*100) + "%, actual " + str(_failed_vms_pct * 100) + "%)"

    print "SLA Provisioning violated VMs stopping condition: ",
    
    _sla_provisioning_violated_vms_pct = float(_exp_counters["VM"]["sla_provisioning_violated"]) / float(_exp_counters["VM"]["arrived"])

    if _sla_provisioning_violated_vms_pct >= sla_provisioning_violated_vms_pct :
        print " YES ",
        _stopping_condition = True        
    else :
        print " NO ",

    print " (target " + str(sla_provisioning_violated_vms_pct*100) + "%, actual " + str(_sla_provisioning_violated_vms_pct * 100) + "%)"

    print "SLA Runtime violated VMs stopping condition: ",            
    # EXTREMELY IMPORTANT. Here we are relying heavily on the fact that (typically)
    # only one VM (the load generator VM) computes SLA RUNTIME violations
    
    _sla_runtime_violated_vms_pct = float(_exp_counters["VM"]["sla_runtime_violated"]) / float(_exp_counters["AI"]["arrived"])

    if _sla_runtime_violated_vms_pct >= sla_runtime_violated_vms_pct :
        print " YES ",
        _stopping_condition = True        
    else :
        print " NO ",

    print " (target " + str(sla_runtime_violated_vms_pct*100) + "%, actual " + str(_sla_runtime_violated_vms_pct * 100) + "%)"        

    print "App Errors VMs stopping condition: ",                
    # EXTREMELY IMPORTANT. Here we are relying heavily on the fact that (typically)
    # only one VM (the load generator VM) computes (APP)ERRORS violations

    _app_errors_vms_pct = float(_exp_counters["VM"]["app_errors"]) / float(_exp_counters["AI"]["arrived"])

    if _app_errors_vms_pct >= app_errors_vms_pct :
        print " YES ",
        _stopping_condition = True        
    else :
        print " NO ",

    print " (target " + str(app_errors_vms_pct * 100) + "%, actual " + str(_app_errors_vms_pct * 100) + "%)"        

    print "Cumulative App Errors stopping condition: ",                
    
    _total_runs = 0
    _total_run_errors = 0
    
    # Get data for ALL AIs currently running with a single API call.
    
    for _ai_metrics in api.get_performance_data(options.cloud_name, None, metric_class = "runtime", object_type = "VM", metric_type = "app", latest = True) :
        if "app_load_id" in _ai_metrics :
            if "val" in _ai_metrics["app_load_id"] :
                _total_runs += int(_ai_metrics["app_load_id"]["val"])

        if "app_errors" in _ai_metrics :
            if "acc" in _ai_metrics["app_errors"] :
                _total_run_errors += int(_ai_metrics["app_errors"]["acc"])

    if float(_total_runs):    
        _cumulative_run_errors_pct = float(_total_run_errors) / float(_total_runs)
    else :
        _cumulative_run_errors_pct = 0        

    if _cumulative_run_errors_pct >= cumulative_run_errors_pct :
        print " YES ",
        _stopping_condition = True        
    else :
        print " NO ",

    print " (target " + str(cumulative_run_errors_pct*100) + "%, actual " + str(_cumulative_run_errors_pct * 100) + "%)"        
        
    return _stopping_condition

def cli_postional_argument_parser() :
    '''
    TBD
    '''
    _usage = "./" + argv[0] + "  <cloud_name> <experiment id> <vapp type> <vapps pattern>"

    options, args = cli_named_option_parser()    
        
    if len(argv) < 4 :
        print _usage
        exit(1)
    
    options.cloud_name = argv[1]
    options.experiment_id = argv[2]
    options.workload = argv[3]
    options.pattern = argv[4]

    print '#' * 5 + " cloud name: " + str(options.cloud_name)
    print '#' * 5 + " experiment id: " + str(options.experiment_id)    
    print '#' * 5 + " workload: " + str(options.workload)
    print '#' * 5 + " pattern: " + str(options.pattern)
    return options

def main() :
    '''
    TDB
    '''    

    error = False

    _channel = "EXPERIMENT"
    
    _start = int(time())

    options = cli_postional_argument_parser()    
    api = connect_to_cb(options.cloud_name)

    _msg = "Setting expid \"" + options.experiment_id + "\"" 
    print _msg
    api.expid(options.cloud_name, options.experiment_id)

    _msg = "Obtaining Virtual Application attributes"
    print _msg
    workload_attrs = api.typeshow(options.cloud_name, options.workload)

    _msg = "Setting SLA (provisioning and runtime) targets"
    print _msg
    # Lets assume that these target SLAs were already obtained by any other mean
    set_provisioning_sla(options, api, workload_attrs, 5)
    set_runtime_sla(options, api, workload_attrs, "bandwidth", 1000) 
    set_runtime_sla(options, api, workload_attrs, "throughput", 150) 
    set_runtime_sla(options, api, workload_attrs, "latency", 210) 

    _msg = "Setting application status stickyness (i.e., once an AI reports an "
    _msg += "error, permanently add this AI to the \"AI in Error\" list)"
    print _msg
    api.cldalter(options.cloud_name, "vm_defaults", "sticky_app_status", "true")

    _msg = "Instructing VMs to publish messages whenever they arrive, update app"
    _msg += " metrics or depart)"
    print _msg
    api.cldalter(options.cloud_name, "vm_defaults", "notification", "true")
    api.cldalter(options.cloud_name, "vm_defaults", "notification_channel", _channel)

    _iait = "unformIxIxI300I600"
    # ------------------ START SIMULATED CLOUD ONLY ----------------------------                
    # Since we are focusing on a simulated cloud, lets make sure the each new
    # simulated AI will create its own performance emitter.    
    api.cldalter(options.cloud_name, "ai_defaults", "create_performance_emitter", "true")
    # ------------------- END SIMULATED CLOUD ONLY -----------------------------
    
    # We will now attach a new Virtual Application Submitter (VAppS).
    # Important, the "pattern name" must refer to an EXISTING VAppS. If needed,
    # please add on to your private configuration file befor executing the
    # cloud attachment through the CLI. See below an illustrative example,
    # which assumes that Virtual Applications of the type "nullworkload" will
    # be created.
    # [AIDRS_TEMPLATES : SIMPLENW]
    # TYPE = nullworkload
    # MAX_AIS = 8000
    # IAIT = uniformIXIXI60I180
    # LOAD_LEVEL = uniformIXIXI1I3
    # LOAD_DURATION = uniformIXIXI40I60
    # LIFETIME = uniformIXIXI200I300

    # ------------------ START SIMULATED CLOUD ONLY ----------------------------
    # Again, given our focus on simulated clouds, lets "accelerate" both the 
    # VApp (by producing more performance samples per unit of time) and the 
    # VApp Submmiter (by dispatching a new VApp every 20 seconds)
    api.typealter(options.cloud_name, options.workload, "load_duration", "5")
    _iait="20"
    # ------------------- END SIMULATED CLOUD ONLY -----------------------------

    _msg = "Setting Virtual Application Submmiter inter-arrival time to " + str(_iait)
    _msg += " seconds."
    print _msg
    api.patternalter(options.cloud_name, options.pattern, "iait", _iait)

    _msg = "Setting Virtual Application Submmiter (AI) lifetime time to 10000000000000"
    _msg += " seconds."
    print _msg        
    api.patternalter(options.cloud_name, options.pattern, "lifetime", "10000000000000")

    # ------------------ START SIMULATED CLOUD ONLY ----------------------------
    # In the case of simulated clouds (and ONLY for simulated clouds) the time
    # to boot is controlled by the parameter "CHECK_BOOT_COMPLETE". Lets make
    # sure that the deployment time for these VMs stay well within the defined
    # SLA for provisioning (defined in the function set_provisioning_sla).    
    api.cldalter(options.cloud_name, "vm_defaults", "check_boot_complete", "wait_for_0")
    # Lets also set "good" (i.e., well within SLA, as defined in the "set_runtime_sla"
    # functions. Again, keep in mind that these are needed for "Simulated" clouds
    # only.    
    api.typealter(options.cloud_name, options.workload, "bandwidth_value", "uniformIXIXI1200I1500")
    api.typealter(options.cloud_name, options.workload, "throughput_value", "uniformIXIXI200I330")
    api.typealter(options.cloud_name, options.workload, "latency_value", "uniformIXIXI100I150")
    api.typealter(options.cloud_name, options.workload, "errors_value", "0")
    
    _change_ai_template = True
    # ------------------- END SIMULATED CLOUD ONLY -----------------------------
        
    _msg = "\nAttaching Virtual Application submmiter\n"
    print _msg
    api.appdrsattach(options.cloud_name, options.pattern)

    _stop = False

    while not _stop:    
        # Now we wait, and check whenever the number of AIs in "ARRIVING" state 
        # is equal zero. The counter state is updated every 10 seconds, waiting
        # at the most 1 minute.
        _check_interval = 10
        _max_check = 60


        '''
        _msg = "Waiting until the counter \"AI ARRIVING\" is equal zero, waiting "
        _msg += str(_check_interval) + " seconds between updates, up to " 
        _msg += str(_max_check) + " seconds."
        print _msg        
        _counters = api.waituntil(options.cloud_name, \
                                  "AI", \
                                  "ARRIVING", \
                                  0, \
                                  "decreasing", \
                                  _check_interval, \
                                  _max_check)
        '''
        
        _counters = subscribe(options, api, _channel)

        _min_ais = 3

    # ------------------ START SIMULATED CLOUD ONLY ----------------------------
    # We want the cloud to misbehave after a certain number of AIs are present.
    # There are multiple possibilities for errors.

        if int(_counters["experiment_counters"]["AI"]["arrived"]) > _min_ais + 2 and _change_ai_template :
            
            _msg = "\nChanging Virtual Application defaults in order to force the"
            _msg += " the reaching of an stopping condition\n"
            print _msg

            # SLA provisioning violation
            #api.cldalter(options.cloud_name, "vm_defaults", "check_boot_complete", "wait_for_7")
            # SLA runtime violation
            api.typealter(options.cloud_name, options.workload, "bandwidth_value", "uniformIXIXI500I600")
            # App Errors VMs
            #api.typealter(options.cloud_name, workload, "errors_value", "1")    
        
            _change_ai_template = False
    # ------------------- END SIMULATED CLOUD ONLY -----------------------------
    
        _stop = check_stopping_conditions(options, \
                                          api, \
                                         _counters, \
                                         _min_ais, 
                                         0.05, \
                                         0.06, \
                                         0.02, \
                                         0.04, \
                                         0.1)

        _msg = "Total experiment time is " + str(int(time()) - _start) + " seconds... \n\n"
        print _msg    

    _msg = "\nDetaching Virtual Application submmiter\n"
    print _msg
    api.appdrsdetach(options.cloud_name, "all")

    _msg = "\nDetaching all Virtual Applications\n"
    print _msg
    api.appdetach(options.cloud_name, "all")
    
if __name__ == '__main__':
    main()
