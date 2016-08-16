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
In this scenario, we establish the full network capacity baseline by running
 "network synthetic" benchmarks on all hosts on the cloud simultaneously, in a 
"ring" configuration (i.e., node1 -> node2 ..... node N-1 -> node N, node N -> node 1

This assumes you have already attached to a cloud through the GUI or CLI.
'''
#--------------------------------- START CB API --------------------------------

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

def cli_postional_argument_parser() :
    '''
    TBD
    '''
    
    _usage = "./" + argv[0] + " <cloud_name> options.experiment_id "
    _usage += "[hypervisor type] [vms per host] [flows per vm] [samples] [networks] [workloads] "
    _usage += "[profile] [load duration] [external address]"

    options, args = cli_named_option_parser()
        
    if len(argv) < 3 :
        print _usage
        exit(1)

    options.cloud_name = argv[1]

    options.experiment_name = argv[2]
    
    if len(argv) > 3 :
        options.hypervisor = argv[3]
    else :
        options.hypervisor = "QEMU"
    
    if len(argv) > 4 :
        options.vm_per_host = argv[4]    
    else :
        options.vm_per_host = "1"
    
    if len(argv) > 5 :
        options.flows_per_vm = argv[5]    
    else :
        options.flows_per_vm = "1"
    
    if len(argv) > 6 :
        options.num_samples = argv[6]  
    else :
        options.num_samples = "10"
    
    if len(argv) > 7 :
        options.networks = argv[7].split(',')   
    else :
        options.networks = ["private1", "private1"]
    
    if len(argv) > 8 :
        options.workloads = argv[8].split(',')   
    else :
    #    options.workloads = [ "netperf", "iperf", "nuttcp" ]
        options.workloads = [ "iperf" ]
    
    if len(argv) > 9 :
        options.load_profile = argv[9] 
    else :
        options.load_profile = "tcp"

    if len(argv) > 10 :
        options.load_duration = argv[10]
    else :
        options.load_duration = "60"
    
    if len(argv) > 11:
        options.external_target = argv[11] 
    else :
        options.external_target = False

    return options

def run_ring_pattern_scenario(options, api) :
    '''
    TBD
    '''
    #try :

    error = True

    cloud_attrs = api.cldlist()[0]
    cloud_model = cloud_attrs["model"]

    _hyper_type = get_compute_parms(options, api)

    options.experiment_id = options.cloud_name + "_ring_" + options.hypervisor 
    options.experiment_id += '_' + options.experiment_name

    print '#' * 5 + " cloud name: " + str(options.cloud_name)
    print '#' * 5 + " hypervisor: " + str(options.hypervisor)
    print '#' * 5 + " experiment id: " + str(options.experiment_id)
    print '#' * 5 + " vms per host: " + str(options.vm_per_host)
    print '#' * 5 + " flows per vm: " + str(options.flows_per_vm)
    print '#' * 5 + " samples: " + str(options.num_samples)
    print '#' * 5 + " networks: " + str(options.networks)
    print '#' * 5 + " workloads: " + str(options.workloads)
    print '#' * 5 + " load_profile: " + str(options.load_profile)
    print '#' * 5 + " load_duration : " + str(options.load_duration)
    print '#' * 5 + " external_target: " + str(options.external_target)

    _net_n = "NA"
    if len(options.networks) == 2 :
        if options.networks[0] == options.networks[1] :
            _net_n = "sn"
        else :
            _net_n = "dn"
                            
    ################## START - USER-DEFINED PARAMATERS" ################## 
    _check_interval = "20"
    
    # Assumes a 10 Gbps link
    _rate_limit = "10000"

    # Change according to your cloud network parameters
    _buffer_length = "1450"

    _inter_vm_wait = "0"
    _inter_host_wait = "0"
    ################## END - USER-DEFINED PARAMATERS" ################## 

    api.cldalter(options.cloud_name, "vm_defaults", "detach_parallelism", "5")
    api.cldalter(options.cloud_name, "ai_defaults", "detach_parallelism", "5")

    if cloud_model == "sim" :    
        options.num_samples = "3"

    _per_vapp_run_time = int(options.num_samples) * int(options.load_duration) * 1.10

    _max_check = int(max(120, _per_vapp_run_time/2))

    if cloud_model == "sim" :    
        _check_interval = int(_check_interval)/10
        options.load_duration = str(int(options.load_duration)/20)
        _per_vapp_run_time = _per_vapp_run_time/1

    _cb_dirs = api.cldshow(options.cloud_name, "space")
    
    _cb_base_dir = os.path.abspath(_cb_dirs["base_dir"])
    _cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])

    _type, _mechanism = get_network_parms(options, api)

    _channel = "EXPERIMENT"

    _start = int(time())

    _msg = "Experiment ID will have the format <CLOUD_NAME>_ring_"
    _msg += "<USER-SUPPLIED ID>_<NET MECHANISM>_<NET MODEL>_<WORKLOAD>_<PROFILE>_"
    _msg += "<VMS PER HOST>_<FLOWS PER VM>_<NETWORKS>"
    print _msg

    _host_ring_pair_list = prepare_host_ring_list(options, api)

    _executed_experiment_list = []

    _nr_ais = str(int(options.vm_per_host))

    _total_ais = int(options.vm_per_host) * len(_host_ring_pair_list)

    for _workload in options.workloads :

        _curr_experiment_id = options.experiment_id + '_' + _type + '_' + _mechanism 
        _curr_experiment_id += '_' + _workload + '_' + options.load_profile + '_'
        _curr_experiment_id += options.vm_per_host + '_' + options.flows_per_vm + '_' + _net_n
        
        _msg = '#' * 5 + " Setting expid to \"" + _curr_experiment_id  + "\" " + '#' * 5 
        print _msg
        
        _executed_experiment_list.append(_curr_experiment_id)

        api.expid(options.cloud_name, _curr_experiment_id)

        _load_generator_vm_list = []

        configure_vapp(options, api, _workload, _rate_limit, _buffer_length)                        

        _curr_stats_ai = api.stats(options.cloud_name)["experiment_counters"]["AI"]
                
        for _host_pair in _host_ring_pair_list :

            deploy_vapp(options, api, _workload, _host_pair, _nr_ais, _inter_vm_wait)
            if int(_inter_host_wait) :
                sleep(float(_inter_host_wait))

        if wait_until_vapp_deployed(options, api, _curr_stats_ai, _total_ais, \
                                    _max_check, _check_interval, pct_failure = 0) :
    
            _msg = '#' * 5 + " Done, will wait for " + str(_per_vapp_run_time) + " seconds for"
            _msg += " the experiment to run."
            print _msg
    
            _start_time = int(time())
            
            while check_samples(options, api, _start_time, _per_vapp_run_time) :
                sleep(float(_check_interval))
                print ' '

            _h2h = False
            if options.vm_per_host == "1" :
                _msg = "Performing a quick \"host-to-host\" analysis (" + _workload + ")" 
                print _msg
                _h2h = host_to_host(options, api, _curr_experiment_id, True)                
                print ' '

            print ' '
            _msg = '#' * 3 + " Experiment \"" + _curr_experiment_id + "\" ended. Performance metrics will"
            _msg += " be collected in .csv files." 
            print _msg
            _tm = time()            
            _url = api.monextract(options.cloud_name, "all", "all")
            _h2h = host_to_host(options, api, _curr_experiment_id, False)
            _tm = int(time() - _tm)
            _msg = "\n"
            _msg = '#' * 3 + " After " + str(_tm )+ " seconds, all metrics were collected "
            _msg +=  " in .csv files.\n"
            print _msg

            remove_all_vapps(options, api, _total_ais)
                
            if _h2h :
                _fn = _cb_data_dir + '/' + _curr_experiment_id + "/host_to_host.txt"
                _fh = open(_fn, "w")
                _fh.write(str(_h2h))
                _fh.close()
        
            _msg = "Data is available at url \"" + _url + "\". \nTo automatically generate"
            _msg += " plots, just run \"" + _cb_base_dir + "/util/plot/cbplotgen.R "
            _msg += "-d " + _cb_data_dir + " -e " + ','.join(_executed_experiment_list)
            _msg += " -c -p -r -l\""
            print _msg
        
            error = False
        
    #except APIException, obj :
    #    print "API Problem (" + str(obj.status) + "): " + obj.msg
    
    #except APINoSuchMetricException, obj :
    #    print "API Problem (" + str(obj.status) + "): " + obj.msg
    
    #except KeyboardInterrupt :
    #    print "Aborting this APP."
    
    #except Exception, msg :
    #    print "Problem during experiment: " + str(msg)
    
    #finally :
    return not(error)
    
def main() :
    '''
    TBD
    '''
    _options = cli_postional_argument_parser()    
    _api = connect_to_cb(_options.cloud_name)

    if run_ring_pattern_scenario(_options, _api) :
        exit(0)
    else :
        exit(1)

if __name__ == '__main__':
    main()
