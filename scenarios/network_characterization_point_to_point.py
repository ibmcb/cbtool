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
In this first example, we establish the network baseline by running "network
synthetic" benchmarks on all hosts on the cloud, in point to point pairwise manner. 
This means that at any given time, only two hosts will house VMs transmitting/receiving.

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

def pt2pt_configure_vapp(options, api, cloud_model, workload, load_level, load_duration, target_udp_bw, mtu_size) :
    '''
    TBD
    '''
    
    _msg = '#' * 10 + " Setting Virtual Application \"" + workload + "\" parameters "
    _msg += "\"load_level\" to " + load_level + " and \"load_duration\""
    _msg += " to " + load_duration + "..."      

    api.typealter(options.cloud_name, workload, "load_level", load_level)
    api.typealter(options.cloud_name, workload, "load_duration", load_duration)    

    api.typealter(options.cloud_name, workload, "if_mtu", mtu_size)  

    if options.experiment_type == "bw" :
        
        if options.protocol_type == "tcp" :

            if workload == "netperf" :
                api.typealter(options.cloud_name, workload, "load_profile", "tcp_stream")        
    
            if workload == "iperf" :
                api.typealter(options.cloud_name, workload, "load_profile", "tcp")
    
            if workload == "nuttcp" :
                api.typealter(options.cloud_name, workload, "load_profile", "tcp")            
        else :

            if workload == "netperf" :
                api.typealter(options.cloud_name, workload, "load_profile", "udp_stream")        
    
            if workload == "iperf" :
                api.typealter(options.cloud_name, workload, "load_profile", "udp")
    
            if workload == "nuttcp" :
                api.typealter(options.cloud_name, workload, "load_profile", "udp")                        

    if options.experiment_type == "tput" :
        
        if options.protocol_type == "tcp" :

            api.typealter(options.cloud_name, workload, "load_profile", "tcp_rr")        
        else :
            api.typealter(options.cloud_name, workload, "load_profile", "udp_rr")        

    workload_attrs = api.typeshow(options.cloud_name, workload)
    _lp = workload_attrs["load_profile"]
    
    if _lp == "udp" :
        _msg = "Virtual Application \"" + workload + "\"load_profile\" is \"udp\"."
        _msg += "Setting target bandwidth to \"" + target_udp_bw + "\"."
        print _msg
        
        if workload == "iperf" :
            api.typealter(options.cloud_name, workload, "udp_bw", target_udp_bw)

        if workload == "nuttcp" :
            api.typealter(options.cloud_name, workload, "rate_limit", target_udp_bw)
            
    _msg = '#' * 10 + " Virtual Application \"" + workload + "\" configured."
    print _msg

    return True

def cli_postional_argument_parser() :
    '''
    TBD
    '''
    
    _usage = "./" + argv[0] + " <cloud_name> <experiment_id> bw|lat|tput tcp|udp|icmp [hypervisor type]"

    options, args = cli_named_option_parser()

    if len(argv) < 5 :
        print _usage
        exit(1)

    options.cloud_name = argv[1]
    options.experiment_name = argv[2]

    options.experiment_type = argv[3]
    if options.experiment_type != "bw" and options.experiment_type != "lat" and options.experiment_type != "tput":
        print _usage
        exit(1)

    if options.experiment_type == "lat" :
        _msg = "EXPERIMENT TYPE is set to \"" + options.experiment_type + "\". Setting protocol"
        _msg += " type to \"icmp\"."
        print _msg
        options.protocol_type = "icmp"
    else :
        options.protocol_type = argv[4]

    if options.protocol_type != "tcp" and options.protocol_type != "udp" and options.protocol_type != "icmp":
        print _usage
        exit(1)

    if len(argv) > 5 :
        options.hypervisor = argv[5]
    else :
        options.hypervisor = "QEMU"

    options.networks = [ "private1", "private1" ]
    options.num_samples = "3"

    return options

def run_pt2pt_pattern_scenario(options, api) :
    '''
    TBD
    '''
    #try :
    error = True

    cloud_attrs = api.cldlist()[0]
    cloud_model = cloud_attrs["model"]

    _hyper_type = get_compute_parms(options, api)
    _net_type, _net_mechanism = get_network_parms(options, api)

    options.experiment_id = options.cloud_name + "_pt2pt_" + options.hypervisor 
    options.experiment_id += '_' + _net_type + '_' + _net_mechanism + '_' 
    options.experiment_id += options.experiment_type + '_' 
    options.experiment_id += options.protocol_type + '_' + options.experiment_name

    print '#' * 5 + " cloud name: " + str(options.cloud_name)
    print '#' * 5 + " hypervisor: " + str(options.hypervisor)
    print '#' * 5 + " net type: " + str(_net_type)
    print '#' * 5 + " net mechanism: " + str(_net_mechanism)    
    print '#' * 5 + " experiment id: " + str(options.experiment_id)
    print '#' * 5 + " experiment name: " + str(options.experiment_name)    
    print '#' * 5 + " experiment_type: " + str(options.experiment_type)
    print '#' * 5 + " protocol type: " + str(options.protocol_type)

    ################## START - USER-DEFINED PARAMATERS" ################## 
    _load_level = "1"
    _load_duration = "30"
    _check_interval = "10"
    _max_check = "60"
    _mtu_size = "auto"
    _target_udp_bw = "2000M"
    
    if options.experiment_type == "bw" :    
        _workloads = [ "netperf", "iperf", "nuttcp" ]
        
    elif options.experiment_type == "lat" :
        _workloads = [ "xping"]
        
    elif options.experiment_type == "tput" :
        _workloads = [ "netperf"]
    
    ################## END - USER-DEFINED PARAMATERS" ################## 

    if cloud_model == "sim" :    
        options.num_samples = "1"
    
    per_vapp_run_time = int(options.num_samples) * int(_load_duration) + 3

    if cloud_model == "sim" :    
        _check_interval = int(_check_interval)/10
        _load_duration = str(int(_load_duration)/10)
        per_vapp_run_time = per_vapp_run_time/1

    _cb_dirs = api.cldshow(options.cloud_name, "space")
    
    _cb_base_dir = os.path.abspath(_cb_dirs["base_dir"])
    _cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])
    
    _channel = "EXPERIMENT"    
    _start = int(time())

    _host_pair_list = prepare_hostpair_list(options, api)

    _executed_experiment_list = []

    for _workload in _workloads :

        _curr_experiment_id = options.experiment_id + "_" + _workload

        _msg = '#' * 5 + "Setting expid to \"" + _curr_experiment_id  + "\"" + '#' * 15 
        print _msg
        
        api.expid(options.cloud_name, _curr_experiment_id)
        _executed_experiment_list.append(_curr_experiment_id)

        pt2pt_configure_vapp(options, api, cloud_model, _workload, _load_level, _load_duration, _target_udp_bw, _mtu_size)

        for _host_pair in _host_pair_list :

            _vapp_attrs = deploy_vapp(options, api, _workload, _host_pair, 1, 0, _max_check)

            if _vapp_attrs :

                _msg = "Done, will wait for " + str(per_vapp_run_time) + " seconds for"
                _msg += " the experiment to run."
                print _msg

                _start_time = int(time())

                while check_samples(options, api, _start_time, per_vapp_run_time) :
                    sleep(float(_check_interval))
                    print ' '

                _msg = "\nRemoving all Virtual Applications\n"
                print _msg
                api.appdetach(options.cloud_name, "all")

            _msg = "Performing a quick \"host-to-host\" analysis (" + _workload + ")" 
            print _msg
            _h2h = host_to_host(options, api, _curr_experiment_id, True)
            print ' '

        _msg = "Experiment \"" + options.experiment_id + "\" ended. Performance metrics will"
        _msg += " be collected in .csv files." 
        print _msg
        _url = api.monextract(options.cloud_name, "all", "all")
        _h2h = host_to_host(options, api, _curr_experiment_id, False)
                
    _msg = "Data is available at url \"" + _url + "\". \nTo automatically generate"
    _msg += " plots, just run \"" + _cb_base_dir + "/util/plot/cbplotgen.R "
    _msg += "-d " + _cb_data_dir + " -e " + ','.join(_executed_experiment_list)
    _msg += " -c -p -r -l -a\""
    print _msg

    error = False
        
#    except APIException, obj :
#        print "API Problem (" + str(obj.status) + "): " + obj.msg
    
#    except APINoSuchMetricException, obj :
#        print "API Problem (" + str(obj.status) + "): " + obj.msg
    
#    except KeyboardInterrupt :
#        print "Aborting this APP."
    
#    except Exception, msg :        
#        print "Problem during experiment: " + str(msg)
    
#    finally :
#        return not(error)
    
def main() :
    '''
    TBD
    '''
    _options = cli_postional_argument_parser()    
    _api = connect_to_cb(_options.cloud_name)
    
    if run_pt2pt_pattern_scenario(_options, _api) :
        exit(0)
    else :
        exit(1)
        
if __name__ == '__main__':
    main()       
    