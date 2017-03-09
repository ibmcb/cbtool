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
This scenario tries to fill up a white-box Cloud with as many VMs as possible.
The question we are trying to answer here is whether the Cloud can actually 
support the number of VMs it is supposed to, based on the product of the number 
of hypervisors and the number of VMs that can be hosted on a hypervisor.
The experiment starts by trying to establish a baseline for the VM deployment
time, randomly selecting specific hosts to deploy VMs.
After the baseline is established, it tries to populate the cloud with VMs up
until the imminence of an overflow. The overflow is determined by multiple 
conditions: failure ratio, decrease in  performance and experiment time. 
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
from random import sample

from common import *

def parse_cli() :
    '''
    Command line parsing
    '''
    usage = '''usage: %prog [options] [command]
    '''

    _parser = OptionParser(usage)


    _parser.add_option("-c","--cloud", \
                       dest="cloud_name", \
                       default=None, \
                       help="Cloud name")

    _parser.add_option("--profile", \
                       dest="profile", \
                       default=2, \
                       help="Number of nodes to use during profile")

    _parser.add_option("--duration", \
                       dest="duration", \
                       default=259200, \
                       help="Total experiment duration")

    _parser.add_option("--completion", \
                       dest="completion", \
                       default=100, \
                       help="Wait for the batch to be partially or completely \
                       deployed before continuing (number converted to percentage)")

    _parser.add_option("--deployment", \
                       dest="deployment", \
                       default=None, \
                       help="Baseline deployment time")

    _parser.add_option("--role", \
                       dest="role", \
                       default="tinyvm", \
                       help="VM role used in the profiling phase")

    _parser.add_option("--instance_size", \
                       dest="instance_size", \
                       default="default", \
                       help="Instance size (default is \"default\", which means don't change what was specified in the role)")

    _parser.add_option("--samples", \
                       dest="num_samples", \
                       default=2, \
                       help="Number of samples during the profiling phase, and also the number of Application Performance Samples")

    _parser.add_option("--sample_every", \
                       dest="sample_every", \
                       default=100, \
                       help="Take a \"single VM\" every \"N\" VMs")

    _parser.add_option("--batches", \
                       dest="batches", \
                       default=100000, \
                       help="Maximum number of batches during the capacity phase")

    _parser.add_option("--pctif", \
                       dest="pctif", \
                       default=None, \
                       help="Percentage of induced failure rate. Only applicable to SIMULATED clouds.")

    _parser.add_option("--failure", \
                       dest="failure", \
                       default=20, \
                       help="Maximum failure rate (number converted to percentage)")

    _parser.add_option("-s", "--batch_size", \
                       dest="batch_size", \
                       default="auto", \
                       help="Initial batch size (auto=number of compute nodes)")

    _parser.add_option("-w", "--batch_width", \
                       dest="batch_width", \
                       default="1", \
                       help="Number of VMs per Virtual Application Instance")

    _parser.add_option("--batch_scaling_factor", \
                       dest="batch_scaling_factor", \
                       default=2, \
                       help="Batch scaling up/down factor in case of failures")

    _parser.add_option("--batch_scaling_hysteresis", \
                       dest="batch_scaling_hysteresis", \
                       default=2, \
                       help="Number of failed/sucessful batchs before deciding to scale up/down")

    _parser.add_option("--increase", \
                       dest="increase", \
                       default=200, \
                       help="Maximum deployment time increase (number converted to percentage)")

    _parser.add_option("-e", "--experiment_id", \
                       dest="experiment_id", \
                       default="capacity_" + makeTimestamp().replace(' ','_').replace('/','_').replace(':','_'), \
                       help="Experiment identifier")

    _parser.add_option("--fip", \
                       dest="fip", \
                       default=None, \
                       help="Floating IP Pool to be used")

    _parser.add_option("--hypervisor", \
                       dest="hypervisor", \
                       default="QEMU", \
                       help="Hypervisor type")

    _parser.add_option("--network", \
                       dest="network", \
                       default=None, \
                       help="Private network to be used. Possible values are None (just use default), a network name and \"random\" (use any private network)")

    _parser.add_option("--multitenant", "-m",
                       action="store_true", \
                       dest="multitenant", \
                       default=False, \
                       help="Create instances on its own tenant and network")

    _parser.add_option("--lb",\
                       action="store_true", \
                       dest="lb", \
                       default=False, \
                       help="Create a load balancer associated with each instance")

    _parser.add_option("--abstraction",\
                       dest="abstraction", \
                       default="pod", \
                       help="Resource type to be deployed (\"pod\", \"replicaset\" or \"deployment\"). Only applicable to KUBERNETE clouds.")

    _parser.add_option("--noidle",\
                       action="store_true", \
                       dest="noidle", \
                       default=False, \
                       help="Deploy active (instead of \"idle\" workloads)")

    _parser.add_option("--waitafter", \
                       dest="waitafter", \
                       default=0, \
                       help="How long to wait after the experiment finishes (to collect additional performance samples")

    _parser.add_option("--resume", "-r",\
                       action="store_true", \
                       dest="resume", \
                       default=False, \
                       help="Resume from a previous execution")

    _parser.add_option("--create_only",\
                       action="store_true", \
                       dest="create_only", \
                       default=False, \
                       help="Do not attempt to contact the deployed VMs")

    _parser.add_option("--cleanup", \
                       action="store_true", \
                       dest="cleanup", \
                       default=False, \
                       help="Remove VMs at the end of the experiment.")

    _parser.add_option("--bgwks", \
                       dest="bgwks", \
                       default=None, \
                       help="Will deploy user-controlled \"background noise\" workloads. Format: workload1:N,workload2:M")

    _parser.add_option("--fgwk", \
                       dest="fgwk", \
                       default="nullworkload", \
                       help="Workload used to populate the cloud")

    _parser.add_option("--update_frequency", \
                       dest="update_frequency", \
                       default=5, \
                       help="Seconds between status requests from the cloud")

    _parser.add_option("--phone", \
                       dest="phone", \
                       default=None, \
                       help="Telephone number to receive messages when important experiment events happen")

    _parser.add_option("--update_attempts", \
                       dest="update_attempts", \
                       default=60, \
                       help="Number of times status requests are made before declaring that instance started")

    _parser.set_defaults()
    (options, _args) = _parser.parse_args()

    return options

def manipulate_perf_dict(api, options, perf_dict, directory, operation) :
    if operation == "write" :
        _fn = directory + "/perf_dict.txt"

        with open(_fn, 'w') as fp :
            json.dump(perf_dict, fp)

    else :
        _fn = directory + "/perf_dict.txt"

        with open(_fn, 'r') as fp:
            perf_dict.update(json.load(fp))

    return True

def additional_vm_attributes(options) :
    '''
    TBD
    '''
    _temp_attr_list_str = ''
    if options.network == "random" :
        _chosen_networkname = sample(options.network_list,1)[0]
        _msg = "### The private network \"" + _chosen_networkname + "\" was "
        _msg += "selected for deployment."
        print _msg
        _temp_attr_list_str = "netname=" + _chosen_networkname
    else :
        if options.network :
            _chosen_networkname = options.network
            _msg = "### The network \"" + _chosen_networkname + "\" was "
            _msg += "selected for deployment."
            print _msg
            _temp_attr_list_str = "netname=" + _chosen_networkname

    return _temp_attr_list_str

def get_experiment_parameters(api, options) :

    _setup = api.cldshow(options.cloud_name, "setup")

    if "exp_opt.role" in _setup :
        options.role = _setup["exp_opt.role"]

    if "exp_opt.instance_size" in _setup :
        options.instance_size = _setup["exp_opt.instance_size"]
  
    if "exp_opt.pause_step" in _setup :
        options.pause_step = _setup["exp_opt.pause_step"]

    if "exp_opt.batch_size" in _setup :
        options.batch_size = _setup["exp_opt.batch_size"]

    if "exp_opt.override_batch_size" in _setup :
        options.override_batch_size = _setup["exp_opt.override_batch_size"]

    if "exp_opt.batch_scaling_factor" in _setup :
        options.batch_scaling_factor = int(_setup["exp_opt.batch_scaling_factor"])

    if "exp_opt.batch_scaling_hysteresis" in _setup :
        options.batch_scaling_hysteresis = int(_setup["exp_opt.batch_scaling_hysteresis"])
    
    if "exp_opt.pctif" in _setup :
        options.pctif = _setup["exp_opt.pctif"].lower()

    if "exp_ctrl.bgwks_state" in _setup :
        options.bgwks_state = _setup["exp_ctrl.bgwks_state"].lower()

    _batch_nr = 0
    if "exp_ctrl.batch_nr" in _setup :
        _batch_nr = _setup["exp_ctrl.batch_nr"]

    _sample_nr = 1
    if "exp_ctrl.sample_nr" in _setup :
        _sample_nr = _setup["exp_ctrl.sample_nr"]

    _total_average_time = 0
    if "exp_ctrl.total_average_time" in _setup :
        _total_average_time = _setup["exp_ctrl.total_average_time"]

    return _batch_nr, _sample_nr, _total_average_time

def asynchronously_end_experiment(api, options) :

    _setup = api.cldshow(options.cloud_name, "setup")
    
    if "exp_ctrl.end_now" in _setup :
        if _setup["exp_ctrl.end_now"].lower() == "true" :
            _msg = "# Attribute \"exp_ctrl.end_now\" set to \"true\" in CBTOOL's"
            _msg += "[SETUP] global object. Ending the experiment now..."
            api.cldalter(options.cloud_name, "setup", "exp_ctrl.end_now", "false")
            print _msg
            send_text(options, _msg)            
            return True

    _current_bgwks_state = options.bgwks_state

    if "exp_ctrl.bgwks_state" in _setup :
        if _setup["exp_ctrl.bgwks_state"].lower() == "attached" :
            options.bgwks_state = "attached"
        else :
            options.bgwks_state = "stopped"
    else :
        if options.bgwks :
            options.bgwks_state = "stopped"
            stop_start_all_vapps(options, api, options.bgwks_state)
        
    api.cldalter(options.cloud_name, "setup", "exp_ctrl.bgwks_state", "stopped")
        
    if _current_bgwks_state == options.bgwks_state :
        True
    else :
        stop_start_all_vapps(options, api, options.bgwks_state, options.total_ais)

    try :
        _fn = "/tmp/end_" + options.experiment_id
        _fh = open(_fn, "r")
        _fh.close()
        _msg = "# File \"" + _fn + "\" found, ending the experiment now..."
        os.remove(_fn)
        print _msg
        send_text(options, _msg)
        return True
    except :
        pass

    return False

def profiling_phase(api, options, performance_data, directory) :
    '''
    In the profiling phase, an attempt to determine the average deployment
    time for a given VM role is made. To this end, a number of randomly selected
    hosts is used. VMs are deployed *serially* on each host, and the numbers are
    then computed.
    '''

    _msg = "\n# Starting PROFILING phase...."
    print _msg
    send_text(options, _msg)
        
    print "### Getting compute node list on cloud \"" + options.cloud_name + "\"....."
    _hosts = get_compute_nodes(options, api)
    
    performance_data["total_nodes"] = len(_hosts)

    _msg = "### The following computes nodes are reported as part of the cloud "
    _msg += "\"" + options.cloud_name + "\" " + ','.join(_hosts) + '\n'    
    print _msg

    if options.profile == "1" :
        _chosen_nodenames = []
        _chosen_nodenames.append(choice(_hosts))
    else :
        _chosen_nodenames = sample(_hosts, options.profile)

    _msg = "### The following computes nodes were selected for the profiling"
    _msg += " phase: " + ','.join(_chosen_nodenames) + '\n'    
    print _msg

    _temp_attr_list_str = additional_vm_attributes(options)

    _temp_attr_list_str += "batch=-1,comments=baseline"
    
    get_experiment_parameters(api, options)
        
    for _node in _chosen_nodenames :

        _msg = "##### Selected compute node is \"" + _node + "\""
        print _msg

        for _j in range(0, int(options.num_samples) + 1) :
            
            if options.obj == "VM" :

                _msg = "####### Deploying VM with role \"" + options.role 
                _msg += "\" size \"" + options.instance_size + "\", on "
                _msg += "node \"" + _node  + "\" (Sample " + str(_j) + ")..."

                print _msg
                
                _vm_attrs = api.vmattach(options.cloud_name, \
                                         options.role, \
                                         size = options.instance_size, \
                                         vm_location = _node, \
                                         temp_attr_list = _temp_attr_list_str, \
                                         pause_step = options.pause_step)
                
                _vm_name = _vm_attrs["name"]
                _vm_uuid = _vm_attrs["uuid"]

                _vm_list = [ _vm_uuid + "|X|" + _vm_name]
            else :
                
                _msg = "####### Deploying VMs forming AI type \"" + options.fgwk
                _msg += ", on node \"" + _node  + "\" (Sample " + str(_j) + ")..."
                print _msg
                                
                _ai_attrs = deploy_vapp(options, api, options.fgwk, None, "1", \
                                        0, False, True, options.pause_step, _temp_attr_list_str)

                _vm_list = _ai_attrs["vms"].split(',')
                for _vm_attrs in _vm_list:
                    _vm_uuid, _p_role, _vm_name = _vm_attrs.split('|')
                        
                    _msg = "####### \"" + _vm_name + "\" (" + _vm_uuid 
                    _msg += ") successfully deployed." 
                    print _msg
        
                    _msg = "####### \"" + _vm_name + "\" (" + _vm_uuid 
                    _msg += ") will now be deleted." 
                    print _msg

            if options.obj == "VM" :
                api.vmdetach(options.cloud_name, _vm_name)
            else :
                api.appdetach(options.cloud_name, _ai_attrs["uuid"])

            for _vm_attrs in _vm_list :
                _vm_uuid, _p_role, _vm_name = _vm_attrs.split('|')
                
                print "####### Obtaining management performance metrics for VM \"" + _vm_name + "\"...."
                _mgt_metric = {}
    
                for _metric in api.get_management_data(options.cloud_name, _vm_uuid):
                    _mgt_metric = _metric
                
                if not _j :
                    _msg = "####### Since this is the first deployment on this node,"
                    _msg += " will ignore this result (VM image might not be pre-"
                    _msg += "cached on the compute node)."             
                    print _msg
                else :
                    if _node not in performance_data :
                        performance_data[_node] = {}
                    
                    performance_data[_node][_j] = total_deployment_time(_mgt_metric)

    print "\n### Determining baseline deployment time ...."    
        
    _min = 100000
    _max = 0
    _acc = 0
    
    for _node in _chosen_nodenames :
        for _sample in performance_data[_node] :
            _perf = performance_data[_node][_sample]
            if _perf < _min :
                _min = _perf
            
            if _perf > _max :
                _max = _perf
            
            _acc += _perf

    performance_data["selected_nodes"] = int(options.profile)
    performance_data["samples"] = int(options.num_samples)    
    performance_data["total_samples"] = performance_data["selected_nodes"] * performance_data["samples"]
    performance_data["average"] = _acc/performance_data["total_samples"]
    performance_data["min"] = int(_min)
    performance_data["max"] = int(_max)

    _profiling_table = prettytable.PrettyTable(["Nodes", "Samples (per Node)", \
                                                "Avg Deployment Time (s)", \
                                                "Min Deployment Time (s)", \
                                                "Max Deployment Time (s)"])

    _profiling_row = []
    _profiling_row.append(performance_data["selected_nodes"])
    _profiling_row.append(performance_data["samples"])
    _profiling_row.append(performance_data["average"])
    _profiling_row.append(performance_data["min"])
    _profiling_row.append(performance_data["max"])        

    _profiling_table.add_row(_profiling_row)

    print "### Baseline deployment time for cloud \"" + options.cloud_name + "\" determined."    
    print _profiling_table

    if not os.path.exists(directory) :  
        os.makedirs(directory)

    _fn = directory + "/profiling.txt"
    _fh = open(_fn, "w")
    _fh.write(str(_profiling_table))
    _fh.close()

    manipulate_perf_dict(api, options, performance_data, directory, "write")

    _msg = "# Ended PROFILING phase.\n"
    print _msg
    send_text(options, _msg)
           
    return True

def total_deployment_time(management_metrics) :
    '''
    TBD
    '''
    total_time = 0

    for _key in management_metrics.keys() :
        if _key.count("mgt") :
            if _key.count("provisioning") :                    
                if not _key.count("originated") and not _key.count("sla") :
                    total_time += int(management_metrics[_key])
            if _key.count("network_acessible") or _key.count("instance_preparation") :
                total_time += int(management_metrics[_key])

    return total_time

def deploy_background_workloads(api, options, performance_data) :
    '''
    TBD
    '''
    _msg = "\n# Starting BACKGROUND WORKLOADS (PRE-CAPACITY) phase...."
    print _msg
    send_text(options, _msg)
        
    _msg = "### Before starting the capacity phase, deploying workloads to"
    _msg += " generate background \"noise\".\n" 
    _msg += "    Each application will produce one application performance sample "
    _msg += "and will then have its execution suspended.\n"
    _msg += "    During the experiment, workload execution can be resumed at any "
    _msg += "time by executing the command \"cldalter " 
    _msg += options.cloud_name + " setup exp_ctrl.bgwks_state attached\" on the CLI."
    print _msg            

    _max_average_deployment_time = performance_data["average"] * (1 + float(options.increase/100))
    _max_wait_time = 40 * _max_average_deployment_time
        
    for _item in options.bgwks.split(',') :
        _workload, _nr_ais = _item.split(':')
        _workload_sut = api.typeshow(options.cloud_name, _workload)["sut"]
        
        _width, _roles = enumerate_vms_in_vapp(_workload_sut)

        if _nr_ais == "auto" :
            _nr_ais = int(performance_data["total_nodes"])/_width
            _inter_vm_wait = "5"
        else :
            if _nr_ais.count('-') :
                _nr_ais, _inter_vm_wait = _nr_ais.split('-')
            else :
                _inter_vm_wait = "0"

        _temp_attr_list_str = additional_vm_attributes(options)
    
        _temp_attr_list_str += "batch=0,comments=background"

        _load_duration = "60"
        api.typealter(options.cloud_name, _workload, "load_duration", _load_duration)    
            
        _msg = "####### Deploying " + _nr_ais + " Application Instances of type \""
        _msg += _workload + "\" (" + _inter_vm_wait + ")...."
        print _msg
        deploy_vapp(options, api, _workload, None, _nr_ais, _inter_vm_wait, \
                    False, True, options.pause_step, _temp_attr_list_str)

    _msg = "##### Waiting until all Application Instances (Workloads) are fully deployed....."
    print _msg

    _counters = api.waituntil(options.cloud_name, "AI", "ARRIVING", "0", \
                              "decreasing", 5, time_limit = _max_wait_time)


    _failed_ais = int(_counters['experiment_counters']["AI"]["failed"])
    _arrived_ais = int(_counters['experiment_counters']["AI"]["arrived"])
    _issued_ais = int(_counters['experiment_counters']["AI"]["issued"])

    if _issued_ais :
        _failure_ratio = float(_failed_ais)/float(_arrived_ais)
    else :
        _failure_ratio = 1.0

    _max_failure_ratio = float(int(options.failure)/100.0)

    if _failure_ratio > _max_failure_ratio :
        _msg = "##### The failure ratio (" + str(_failure_ratio) + ") for Application Instances is "
        _msg += " higher than the maximum (" + str(_max_failure_ratio)
        _msg += "). Ending the experiment...."            
        print _msg
        send_text(options, _msg)            
        _experiment_end = True
        exit(1)
        
    options.total_ais = str(_arrived_ais)
                            
    _per_vapp_run_time = 2 * int(_load_duration) * int (options.num_samples)
    _check_interval = 5
    _msg = "##### Done, will wait for " + str(_per_vapp_run_time) + " seconds for"
    _msg += " at least one application performance sample from each Application Instance..."
    print _msg

    _start_time = int(time())

    while check_samples(options, api, _start_time, _per_vapp_run_time) :
        sleep(float(_check_interval))
        print ' '

    if check_samples(options, api, _start_time, _per_vapp_run_time, True) :
        options.bgwks_state = "stopped"        
        stop_start_all_vapps(options, api, options.bgwks_state, options.total_ais)
        
        _msg = "# Ended BACKGROUND WORKLOADS (PRE-CAPACITY) phase."
        print _msg
        send_text(options, _msg)
        return True
    else :        
        _msg = "# Failed to get application performance samples from all Application"
        _msg += " Instances. Ending the experiment....\n\n"            
        print _msg
        send_text(options, _msg)            
        _experiment_end = True
        exit(1)

def capacity_phase(api, options, performance_data, directory) :
    '''
    TBD
    '''
    _msg = "\n# Starting CAPACITY phase...."
    print _msg
    send_text(options, _msg)
    
    _msg = "### The experiment can be ended at any time by either executing the"
    _msg += " command \"cldalter " + options.cloud_name + " setup exp_ctrl.end_now True"
    _msg += "\" on the CLI or by running \"touch /tmp/end_" + options.experiment_id
    _msg += "\" on the bash prompt."
    print _msg

    _msg = "### IMPORTANT! It is assumed that this is the only process deploying"
    _msg += " VMs on the cloud \"" + options.cloud_name + "\".\n"
    print _msg

    if options.batch_size == "auto" :    
        _batch_size = int(performance_data["total_nodes"])/int(performance_data["batch_width"])
    else :
        _batch_size = int(options.batch_size)

    _inter_batch_success_counter = 0
    _inter_batch_failure_counter = 0

    _original_batch_size = _batch_size
        
    _msg = "### Initial batch size (deployment parallelism) is " + str(_batch_size) + ").\n"
    print _msg

    _max_average_deployment_time = performance_data["average"] * (1 + float(options.increase/100))
    _msg = "### Maximum average deployment time (per-batch) is "
    _msg += str(_max_average_deployment_time) + " seconds.\n"
    print _msg

    _max_failure_ratio = float(int(options.failure)/100.0)
    _msg = "### Maximum failure ratio is " + str(options.failure) + "%.\n"
    print _msg

    _batch_nr, _sample_nr, _total_average_time = get_experiment_parameters(api, options)
    _batch_nr = int(_batch_nr) + 1
    _total_average_time = int(_total_average_time)
    
    if options.resume : 

        _msg = "### Resuming from batch " + str(_batch_nr) + "\n"
        print _msg
        
        _msg = "### Resuming with accumulated average time " + str(_total_average_time) + " s\n"
        print _msg

    _duration = time() - performance_data["experiment_start"] 

    _header = ["Timestamp", "Batch", "Batch Size/Width", "Total Time Spent (s)", \
               "VM/AI Reservations", "VMs/AIs ISSUED", "VMs/AIs ARRIVED", \
               "VMs/AIs ARRIVING", "VMs/AIs DEPARTED", "VMs/AIs DEPARTING", \
               "VMs/AIs FAILED", \
               #"VMs REPORTED (Cloud)", \
               "Exp Avg Deployment Time (s)", \
               "Batch Avg Deployment Time(s)", "Shortest Deployment Time (s)", \
               "Longest Deployment Time (s)", "Failure Ratio (%)", "Background Workload"]

    #_capacity_table = prettytable.PrettyTable(_header)

    _stats = api.stats(options.cloud_name, "VM")
    _vm_stats = _stats["experiment_counters"]["VM"]

    _failed_vms = int(_vm_stats["failed"])
    _arrived_vms = int(_vm_stats["arrived"])
    _issued_vms = int(_vm_stats["issued"])
    
    _max_wait_time = 10 * _max_average_deployment_time
    _single_vm_failure_counter = 1
    _experiment_end = False

    while _duration < options.duration and not _experiment_end :

        get_experiment_parameters(api, options)

        if options.pctif != "none" :
            _msg = "##### Settting the percentage of induced failures (" + str(options.pctif) + "%)."
            print _msg
            api.cldalter(options.cloud_name, "vm_defaults", "pct_failure", options.pctif)

        if _batch_nr not in performance_data :
            performance_data["batch" + str(_batch_nr)] = {}

        #_batch_id = str(uuid5(NAMESPACE_DNS, str(randint(0, 1000000000000000000)))).upper()        
        _batch_id = _batch_nr

        performance_data["batch" + str(_batch_nr)]["id"] = _batch_id

        if _arrived_vms >= int(_sample_nr) * int(options.sample_every) :
            _selected_batch_size = 1
            _comments = "sample"
            _sample_nr += 1
        else :
            _comments = "foreground"
            if options.override_batch_size == "false" :
                _selected_batch_size = _batch_size
            else :
                _selected_batch_size = int(options.override_batch_size)

        _msg = "\n\n##### Deploying batch " + str(_batch_nr) + " (id " + str(_batch_id)
        _msg += ") with size/width (parallelism = size * width) " + str(_selected_batch_size)
        _msg += '/' + str(performance_data["batch_width"])
#        _msg += " over " + str(performance_data["total_nodes"]) + " nodes"

        if options.obj == "VM" :
            _msg += " (instance size is \"" + options.instance_size + "\") ..."
        print _msg

        _temp_attr_list_str = additional_vm_attributes(options)

        if len(_temp_attr_list_str) :
            _temp_attr_list_str += ','
            
        _temp_attr_list_str += "batch=" + str(_batch_id) + ",comments=" + _comments
        _temp_attr_list_str += ",leave_instance_on_failure=true"

        _batch_start = int(time())        
        
        if options.obj == "VM" :

            _deployed = int(_selected_batch_size * options.completion/100)

            _target = _selected_batch_size * - _deployed

            api.vmattach(options.cloud_name, options.role, \
                         size = options.instance_size, \
                         temp_attr_list = _temp_attr_list_str, \
                         async = _selected_batch_size, \
                         pause_step = options.pause_step)
                        
        else :

            _deployed = int(_selected_batch_size * int(performance_data["batch_width"]) * options.completion/100)

            _target = _selected_batch_size * int(performance_data["batch_width"]) - _deployed            
            
            deploy_vapp(options, api, options.fgwk, None, _selected_batch_size, \
                        0, False, True, options.pause_step, _temp_attr_list_str)

            sleep(10)
        
        _msg = "####### Waiting until " + str(options.completion) + "% of the " + options.obj + "s"
        _msg += " forming the batch " + str(_batch_nr) + " (" + str(_deployed)
        _msg += " VMs) are deployed (" + options.obj + " ARRIVING=" + str(_target) + ")....."
        print _msg

        _counters = api.waituntil(options.cloud_name, options.obj, "ARRIVING", \
                             _target, "decreasing", \
                             5, time_limit = _max_wait_time)
                
        if _counters['experiment_counters'][options.obj]["arriving"] != str(_target) :
            _msg = "####### WARNING: " + options.obj + " ARRIVING counter still not \""
            _msg += str(_target) + " even after " + str(_max_wait_time) + " seconds!"
            print _msg
            send_text(options, _msg)
            
        _batch_total = int(time()) - _batch_start
        
        _msg = "####### Determining average deployment time for batch " + str(_batch_nr) + "...."
        print _msg
        _batch_vms = api.viewshow(options.cloud_name, "VM", "batch", str(_batch_id))

        _batch_tdt = 0
        _batch_actual_size = len(_batch_vms)
        performance_data["batch" + str(_batch_nr)]["size"] = _batch_actual_size

        performance_data["batch" + str(_batch_nr)]["total_deployment_time"] = _batch_total

        _slowest_vm = 0
        _fastest_vm = 10000000

        for _vm in _batch_vms :
            for _mgt_metric in api.get_latest_management_data(options.cloud_name, _vm["uuid"]) :
                _tdt = total_deployment_time(_mgt_metric)
            
            if _tdt < _fastest_vm :
                _fastest_vm = _tdt

            if _tdt > _slowest_vm :
                _slowest_vm = _tdt

            _batch_tdt += _tdt

        if _batch_actual_size :
            _batch_adt = _batch_tdt/_batch_actual_size
        else :
            _batch_adt = 0
            
        performance_data["batch" + str(_batch_nr)]["average_deployment_time"] = _batch_adt

        _msg = "####### Average deployment time for batch " + str(_batch_nr)
        _msg += " is " + str(_batch_adt) + " seconds."
        print _msg

        _total_average_time += _batch_adt 
        api.cldalter(options.cloud_name, "setup", "exp_ctrl.total_average_time", _total_average_time)

        _average_deployment_time = _total_average_time/_batch_nr
        
        _msg = "####### Obtaining the values of all CB counters"
        print _msg
        _stats = api.stats(options.cloud_name)

        _msg = "##### Inter-batch statistics"
        print _msg
        
        _vm_stats = _stats["experiment_counters"]["VM"]

        _failed_vms = int(_vm_stats["failed"])
        _arrived_vms = int(_vm_stats["arrived"])
        _issued_vms = int(_vm_stats["issued"])

        _ai_stats = _stats["experiment_counters"]["AI"]

        _failed_ais = int(_ai_stats["failed"])
        _arrived_ais = int(_ai_stats["arrived"])
        _issued_ais = int(_ai_stats["issued"])

        _x_mark = ''
        if _issued_vms < _issued_ais * int(performance_data["batch_width"]) :
            _diff = (_issued_ais * int(performance_data["batch_width"])) - _issued_vms
            _msg = "####### WARNING: the number of issued VMs (" + str(_failed_vms)
            _msg += ") is smaller of the number of number of issued AIs ("
            _msg += str(_issued_ais) + ") time the AI size (" + str(performance_data["batch_width"])
            _msg += "). This means that AIs failed during initialization phase,"
            _msg += " even before the VMs were actually issued. In order to "
            _msg += "properly account for it will add " + str(_diff) + " VMs as \"failed\""            
            print _msg

            _issued_vms += _diff
            _failed_vms += _diff

            _x_mark = "*"
            
        if _issued_vms :
            _failure_ratio = float(_failed_vms)/float(_issued_vms)
        else : 
            _failure_ratio = 1.0

        performance_data["batch" + str(_batch_nr)]["failure_ratio"] = _failure_ratio
        performance_data["batch" + str(_batch_nr)]["failed_vms"] = _failed_vms
        
        _temp_capacity_table = prettytable.PrettyTable(_header)
        
        _capacity_row = []
        _capacity_row.append(makeTimestamp())
        _capacity_row.append(_batch_nr)
        _capacity_row.append(str(_selected_batch_size) + '/' + str(performance_data["batch_width"]))
        _capacity_row.append(_batch_total)        
        _capacity_row.append(_vm_stats["reservations"] + '/' + _ai_stats["reservations"])
        _capacity_row.append(str(_issued_vms) + _x_mark + '/' + str(_issued_ais))        
        _capacity_row.append(str(_arrived_vms) + '/' + str(_arrived_ais))
        _capacity_row.append(_vm_stats["arriving"] + '/' + _ai_stats["arriving"])
        _capacity_row.append(_vm_stats["departed"] + '/' + _ai_stats["departed"])
        _capacity_row.append(_vm_stats["departing"] + '/' + _ai_stats["departing"])
        _capacity_row.append(str(_failed_vms) + _x_mark + '/' + str(_failed_ais))
#        if "reported" in _vm_stats :
#            _capacity_row.append(_vm_stats["reported"])
#        else :
#            _capacity_row.append("NA")

        _capacity_row.append(_average_deployment_time)            
        _capacity_row.append(_batch_adt)                    
        
        if _fastest_vm != 10000000 :            
            _capacity_row.append(_fastest_vm)
        else :
            _capacity_row.append("NA")
            
        if _slowest_vm != 0 :                                    
            _capacity_row.append(_slowest_vm)
        else :
            _capacity_row.append("NA")
            
        _capacity_row.append(_failure_ratio * 100)
        _capacity_row.append(options.bgwks_state)
                    
        #_capacity_table.add_row(_capacity_row)

        _temp_capacity_table.add_row(_capacity_row)

        print _temp_capacity_table
        print '\n'

        if not os.path.exists(directory) :  
            os.makedirs(directory)
    
        _fn = directory + "/capacity.txt"
        if _batch_nr == 1 :
            _fh = open(_fn, 'w')
            _fh.write(str('\n'.join(_temp_capacity_table.get_string().split('\n')[0:-1])) + '\n')
        else :
            _fh = open(_fn, "a")
            _fh.write(str('\n'.join(_temp_capacity_table.get_string().split('\n')[2:4])) + '\n')
        _fh.close()

        if _average_deployment_time > _max_average_deployment_time :
            _msg = "##### The average deployment time (" + str(_average_deployment_time)
            _msg += " seconds) is higher than the maximum (" + str(_max_average_deployment_time)
            _msg += " seconds). Ending the experiment...."            
            print _msg
            send_text(options, _msg)            
            _experiment_end = True

        if _failure_ratio > _max_failure_ratio :
            _msg = "##### The failure ratio (" + str(_failure_ratio) + ") for VMs/Containers is "
            _msg += " higher than the maximum (" + str(_max_failure_ratio)
            _msg += "). Ending the experiment...."            
            print _msg
            send_text(options, _msg)            
            _experiment_end = True
        
        if _batch_nr >= int(options.batches) :
            _msg = "##### The Number of batches (" + str(_batch_nr) + ") is larger"
            _msg += " than the total number of batches. Ending the experiment..."
            print _msg
            send_text(options, _msg)                    
            _experiment_end = True

        if _batch_nr >= 2 :
            _delta_failure_ratio = performance_data["batch" + str(_batch_nr)]["failure_ratio"] - \
            performance_data["batch" + str(_batch_nr - 1)]["failure_ratio"]

            _delta_failed_vms = performance_data["batch" + str(_batch_nr)]["failed_vms"] - \
            performance_data["batch" + str(_batch_nr - 1)]["failed_vms"]

            if _delta_failed_vms :
                _msg = "##### The number of failures increased between batches \""
                _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\""
                _msg += " by " + str(_delta_failed_vms) + "." 
                print _msg
                if _delta_failure_ratio < 0 :
                    _delta_failure_ratio *= -1
            
            if _delta_failure_ratio > 0 :
                _inter_batch_success_counter = 0
                _inter_batch_failure_counter += 1

                if _batch_size > 1 :
                    _msg = "##### The failure ratio increased between batches \""
                    _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\""
                    _msg += " by " + str(_delta_failure_ratio) + " (" 
                    _msg += str(_inter_batch_failure_counter) + ")." 
                    print _msg

                    if _inter_batch_failure_counter >= options.batch_scaling_hysteresis :
                        _msg = "##### The failure ratio increased "
                        _msg += "for " + str(_inter_batch_failure_counter)
                        _msg += " consecutive batches. Dividing the batch size by "
                        _msg += str(options.batch_scaling_factor) + '.' 
                        print _msg            
                        _batch_size = int(_batch_size/int(options.batch_scaling_factor))
                    else :
                        _msg = "###### The failure ratio increased "
                        _msg += "for " + str(_inter_batch_failure_counter)
                        _msg += " consecutive batches, waiting for failure "
                        _msg += "counter to reach " 
                        _msg += str(options.batch_scaling_hysteresis) + ". "
                        print _msg

                else :
                    _svcf = 5                   
                    _msg = "##### The failure ratio increased between batches \""
                    _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\""
                    _msg += " by " + str(_delta_failure_ratio) + "(" 
                    _msg += str(_inter_batch_failure_counter) + "), but batch "
                    _msg += "size is already 1 (" + str(_single_vm_failure_counter)
                    _msg += '/' + str(_svcf) + "). "            
                    print _msg
                    send_text(options, _msg)
                    _single_vm_failure_counter += float(1.0)

                    if _single_vm_failure_counter > _svcf :
                        _msg = "##### The batch size is already 1 and " + str(_svcf)
                        _msg += " consecutive failures were detected. Ending the experimen..."
                        print _msg
                        _experiment_end = True

                if not _batch_size :
                    _msg = "##### Batch size equal zero (too many failures). Ending the experiment..."
                    print _msg
                    _experiment_end = True

            else :
                _inter_batch_failure_counter = 0
                _inter_batch_success_counter += 1
                
                _msg = "##### The failure ratio between batches \""
                _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\""
                _msg += " did not increase (" + str(_inter_batch_success_counter) + ")."
                print _msg           

                if _batch_size == 1 :
                    _single_vm_failure_counter = 0
               
                if _batch_size < _original_batch_size : 
                            
                    if _inter_batch_success_counter >= options.batch_scaling_hysteresis :
                        _msg = "###### The failure ratio did not increase "
                        _msg += "for " + str(_inter_batch_success_counter)
                        _msg += " consecutive batches. Multiplying the batch size"
                        _msg += " by " + str(options.batch_scaling_factor) + " (up to "
                        _msg += str(_original_batch_size) + ")."                
                        print _msg                                        

                        _batch_size = _batch_size * int(options.batch_scaling_factor)
                        if _batch_size > _original_batch_size :
                            _batch_size = _original_batch_size
                    else :
                        _msg = "###### The failure ratio did not increase "
                        _msg += "for " + str(_inter_batch_success_counter)
                        _msg += " consecutive batches, waiting for success "
                        _msg += "counter to reach " 
                        _msg += str(options.batch_scaling_hysteresis) + ". "
                        print _msg
                else :
                    if _inter_batch_success_counter >= options.batch_scaling_hysteresis :                    
                        _msg = "\n###### The failure ratio did not increase "
                        _msg += "for " + str(_inter_batch_success_counter)
                        _msg += " consecutive batches, but current batch size ("
                        _msg += str(_batch_size) + ") is already maximum." 
                        print _msg                                        
                    else :
                        _msg = "\n " 
                        print _msg
                                            
        api.cldalter(options.cloud_name, "setup", "exp_ctrl.batch_nr", _batch_nr)
        api.cldalter(options.cloud_name, "setup", "exp_ctrl.sample_nr", _sample_nr)        

        manipulate_perf_dict(api, options, performance_data, directory, "write")

        if not _experiment_end :
            _experiment_end = asynchronously_end_experiment(api, options) 
        
        _batch_nr +=1

    return True    
        
def main() :
    '''
    TBD
    '''

    _error = False
    _perf_dict = {}
    _perf_dict["experiment_start"] = time()
    
    _phase = "connection"
    _options = parse_cli()

    if not _options.cloud_name :
        print "A cloud name (\"-c\") is mandatory"
        exit(1)

    _options.obj = "AI"
        
    api = connect_to_cb(_options.cloud_name)

    _cloud_model = api.cldlist()[0]["model"]

    _hyper_type = get_compute_parms(_options, api)
    _net_type, _net_mechanism = get_network_parms(_options, api)
    
    if not _hyper_type.lower().count(_options.hypervisor.lower()) :
        _msg = "ERROR: There are no hypervisors with type \"" + _options.hypervisor
        _msg += "\" on the cloud \"" + _options.cloud_name + "\". The hypervisor"
        _msg += "types detected on the cloud are: " + _hyper_type
        print _msg
        exit(2)
         
    _experiment_id = _options.hypervisor + '_' + _net_type + '_' + _net_mechanism + '_'
    _experiment_id += _options.experiment_id

    _experiment_id = _experiment_id.replace("\\","_and_" )
    _msg = "# Setting expid to \"" + _experiment_id  + "\""
    print _msg
    api.expid(_options.cloud_name, _experiment_id)

    _options.network_list = list_private_networks(_options, api)
    _msg = "# The following networks were reported as created on the cloud "
    _msg += "\"" + _options.cloud_name + "\" " + ','.join(_options.network_list) + '\n'    
    print _msg

    _cb_dirs = api.cldshow(_options.cloud_name, "space")
    
    _cb_base_dir = os.path.abspath(_cb_dirs["base_dir"])
    _cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])

    if _options.fip :
        _msg = "# Instances will use floating IPs from pool \"" + _options.fip + "\""
        print _msg
        api.cldalter(_options.cloud_name, "vm_defaults", "floating_pool", _options.fip)     
        api.cldalter(_options.cloud_name, "vm_defaults", "use_floating_ip", "True")
        api.cldalter(_options.cloud_name, "vm_defaults", "always_create_floating_ip", "True")
        api.cldalter(_options.cloud_name, "ai_defaults", "floating_pool", _options.fip)     
    else :
        api.cldalter(_options.cloud_name, "vm_defaults", "use_floating_ip", "False")

    if _options.lb :
        _msg = "# Instances will have load balancers associated to it"
        print _msg
        api.cldalter(_options.cloud_name, "vm_defaults", "create_lb", "True")     
        api.cldalter(_options.cloud_name, "ai_defaults", "create_lb", "True")             
    else :
        api.cldalter(_options.cloud_name, "vm_defaults", "create_lb", "False")     
        api.cldalter(_options.cloud_name, "ai_defaults", "create_lb", "False")             

    api.cldalter(_options.cloud_name, "vm_defaults", "update_attempts", _options.update_attempts)
    api.cldalter(_options.cloud_name, "vm_defaults", "update_frequency", _options.update_frequency)
    api.cldalter(_options.cloud_name, "vm_defaults", "leave_instance_on_failure", "true")    

    api.cldalter(_options.cloud_name, "ai_defaults", "update_attempts", _options.update_attempts)
    api.cldalter(_options.cloud_name, "ai_defaults", "update_frequency", _options.update_frequency)
        
    api.cldalter(_options.cloud_name, "admission_control", "vm_max_reservations", 75000)

    if _cloud_model == "kub" :
        _msg = "# This is a Kubernetes cloud, setting the parameter ABSTRACTION on [VM_DEFAULTS : KUB_CLOUDCONFIG]"
        _msg += " to \"" + _options.abstraction + "\""
        print _msg
        api.cldalter(_options.cloud_name, "vm_defaults", "abstraction", _options.abstraction)        

    if _options.hypervisor.lower() == "fake" or _options.create_only :
        api.cldalter(_options.cloud_name, "vm_defaults", "check_boot_complete", "wait_for_0")
        api.cldalter(_options.cloud_name, "vm_defaults", "transfer_files", "false")
        api.cldalter(_options.cloud_name, "vm_defaults", "run_generic_scripts", "false")
        api.cldalter(_options.cloud_name, "vm_defaults", "check_ssh", "false")        
        api.cldalter(_options.cloud_name, "vm_defaults", "update_frequency", "1")
        api.cldalter(_options.cloud_name, "ai_defaults", "run_application_scripts", "false")
        api.cldalter(_options.cloud_name, "ai_defaults", "dont_start_load_manager", "true")
                
    if _options.noidle :
        _msg = "# Option \"noidle\" detected, will deploy active workloads"
        print _msg
        api.cldalter(_options.cloud_name, "ai_defaults", "run_application_scripts", "True")
        api.cldalter(_options.cloud_name, 'ai_defaults', "dont_start_load_manager", "False")        
    else :
        api.cldalter(_options.cloud_name, "ai_defaults", "run_application_scripts", "False")
        api.cldalter(_options.cloud_name, 'ai_defaults', "dont_start_load_manager", "True")

    _type_sut = api.typeshow(_options.cloud_name, _options.fgwk)["sut"]
    _instances_per_tenant, _roles = enumerate_vms_in_vapp(_type_sut)

    _mt_script = None
    if _options.multitenant :
        _mt_script = _cb_base_dir + "/scenarios/scripts/" + _cloud_model + "_multitenant.sh"

        if _cloud_model == "osk" :

            _mgt_info = api.cldshow(_options.cloud_name, "mon_defaults")
            _host_runtime_metrics_header = _mgt_info["host_runtime_os_metrics_header"]
                
            if not _host_runtime_metrics_header.count("procstat") :
                _host_runtime_metrics_header += ',' + _mgt_info["cloud_base_m"]
                _host_runtime_metrics_header += ',' + _mgt_info["openstack_m"]
    
                api.cldalter(_options.cloud_name, \
                             "mon_defaults", \
                             "host_runtime_os_metrics_header", \
                             _host_runtime_metrics_header)           

        _msg = "# Instances will run the script \"" + _mt_script + "\" in order to "
        _msg += "create a new tenant/user/network/subnet/router before attachment"
        print _msg

        api.cldalter(_options.cloud_name, "vm_defaults", "execute_script_name", _mt_script)
        api.cldalter(_options.cloud_name, "ai_defaults", "execute_script_name", _mt_script)                
        _options.pause_step = "execute_provision_originated"

#        _mgt_info = api.cldshow(_options.cloud_name, "mon_defaults")
#        _mgt_metrics_header = _mgt_info["vm_management_metrics_header"]
        
#        _msg = "# The attribute \"vm_management_metrics_header\" was updated to"
#        _msg += ' ' + _mgt_metrics_header

#        print _msg

        if _instances_per_tenant > int(_options.batch_width) :
            _msg = "ERROR: the workload \"" + _options.fgwk + "\" already has "
            _msg += "more VMs (" + str(_instances_per_tenant) + ") than the amount "
            _msg += "required (" + str(_options.batch_width)
            exit(2)
        elif _instances_per_tenant < int(_options.batch_width) :
            _type_sut = _type_sut + "->" + str(int(_options.batch_width) - _instances_per_tenant) + "_x_yatinyvm"
            api.typealter(_options.cloud_name, _options.fgwk, "sut", _type_sut)
            _roles.append("yatinyvm")
                        
        _msg = "# The number of instances per tenant is \"" + _options.batch_width
        _msg += "\". The SUT for the workload \"" + _options.fgwk + "\" will be \""
        _msg += _type_sut + "\""
        print _msg

    else :
        _options.pause_step = "none"

    if _options.instance_size != "default" :
        _msg = "# Setting the instace size of all instances on workload \""
        _msg += _options.fgwk + "\" to be \"" + _options.instance_size + "\"."
        print _msg
                
        for _role in _roles :
            api.typealter(_options.cloud_name, _options.fgwk, _role + "_size", _options.instance_size)

    if not _options.deployment and not _options.resume :
        _phase = "profiling"
        profiling_phase(api, _options, _perf_dict, _cb_data_dir + '/' + _experiment_id)
    
    if not _options.resume :
        _perf_dict["selected_nodes"] = 0
        _perf_dict["samples"] = 0
        _perf_dict["total_samples"] = 0
        _perf_dict["total_nodes"] = len(get_compute_nodes(_options, api) )
        _perf_dict["batch_width"] = _options.batch_width

        if _options.deployment :
            _perf_dict["average"] = int(_options.deployment)
            _perf_dict["min"] = int(_options.deployment)
            _perf_dict["max"] = int(_options.deployment)

        api.cldalter(_options.cloud_name, "setup", "exp_opt.role", _options.role)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.instance_size", _options.instance_size)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.batch_size", _options.batch_size)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.pause_step", _options.pause_step)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.override_batch_size", "false")
        api.cldalter(_options.cloud_name, "setup", "exp_opt.batch_scaling_factor", _options.batch_scaling_factor)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.batch_scaling_hysteresis", _options.batch_scaling_hysteresis)
        api.cldalter(_options.cloud_name, "setup", "exp_opt.pctif", str(_options.pctif).lower())

        if _options.bgwks :
            deploy_background_workloads(api, _options, _perf_dict)
        else :
            _options.bgwks_state = "stopped"
    else :
        manipulate_perf_dict(api, _options, _perf_dict, _cb_data_dir + '/' + _experiment_id, "read")

    _phase = "capacity"
    capacity_phase(api, _options, _perf_dict, _cb_data_dir + '/' + _experiment_id)

    _msg = "# Experiment \"" + _options.experiment_id + "\" ended."
    print _msg

    if _options.waitafter :
        _msg = "# Waiting additional " + str(_options.waitafter) + " seconds "
        _msg += "after the end of the experiment, in order to collect additional"
        _msg += " samples."
        print _msg
        sleep(float(_options.waitafter))
        
    _msg = "# Performance metrics will be collected in .csv files." 
    print _msg
    _url = api.monextract(_options.cloud_name, "all", "all")

    create_plots(_options, api, _cb_base_dir, _cb_data_dir, _experiment_id, _url)

    if _options.cleanup :
        _start = int(time())
        _msg = "\nCleaning up all VMs (might take a long time, if the number of VMs is large)."
        print _msg        
        if _options.obj == "VM" :
            api.vmdetach(_options.cloud_name, "all")
        else :
            api.appdetach(_options.cloud_name, "all")

        _counters = api.waituntil(_options.cloud_name, "VM", "RESERVATIONS", "0", \
                                  "decreasing", 5, time_limit = 86400)

        _duration = int(time()) - _start
        _msg = "\nCleaned after " + str(_duration) + " seconds."
        print _msg        

if __name__ == '__main__':
    main()
