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
This experiment tries to fill up a white-box Cloud with as many VMs as possible.
The question we are trying to answer here is whether the Cloud can actually 
support the number of VMs it is supposed to, based on the product of the number 
of hypervisors and the number of VMs that can be hosted on a hypervisor.
The experiment starts by trying to establish a baseline for the VM deployment
time, randomly selecting specific hosts to deploy VMs.
After the baseline is established, it tries to populate the cloud with VMs up
until the imminence of an overflow. The overflow is determined by multiple 
conditions: failure ratio, decrease in  performance and experiment time. 
'''

#--------------------------------- START CB API --------------------------------

import sys
import pwd
import fnmatch
import prettytable

from os import environ, getuid, access, F_OK, walk, path
from optparse import OptionParser
from random import choice,sample
from time import sleep
from json import dumps

from uuid import uuid5, NAMESPACE_DNS
from random import randint
    
_path_set = False

for _path, _dirs, _files in walk(path.abspath(sys.path[0] + "/../")):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        if _path.count("/lib/auxiliary") :
            sys.path.append(_path.replace("/lib/auxiliary",''))
            _path_set = True
            break
    if _path_set :
        break

from lib.api.api_service_client import *

#---------------------------------- END CB API ---------------------------------

def parse_cli() :
    '''
    Command line parsing
    '''
    usage = '''usage: %prog [options] [command]
    '''

    _parser = OptionParser(usage)


    _parser.add_option("-c","--cloud", \
                       dest="cloud", \
                       default=None, \
                       help="Cloud name")

    _parser.add_option("-p","--port", \
                       dest="port", \
                       default=None, \
                       help="API port")

    _parser.add_option("-a","--address", \
                       dest="host", \
                       default=None, \
                       help="API host")

    _parser.add_option("--profile", \
                       dest="profile", \
                       default=2, \
                       help="Number of nodes to use during profile")

    _parser.add_option("--duration", \
                       dest="duration", \
                       default=86400, \
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

    _parser.add_option("--samples", \
                       dest="samples", \
                       default=2, \
                       help="Number of samples during the profiling phase")

    _parser.add_option("--failure", \
                       dest="failure", \
                       default=20, \
                       help="Maximum failure rate (number converted to percentage)")

    _parser.add_option("--increase", \
                       dest="increase", \
                       default=20, \
                       help="Maximum deployment time increase (number converted to percentage)")

    _parser.set_defaults()
    (options, _args) = _parser.parse_args()

    _username = pwd.getpwuid(getuid())[0]
    
    _api_conn_info = False
    # When CB is started and the API daemons are brought on-line, a fine containing
    # the API connection string will be generated in /tmp (cb_api_<username>).
    # If this executable is run co-located with the API daemon, then the connection
    # information can be automatically determined.    
    _api_file_name = "/tmp/cb_api_" + _username
    if access(_api_file_name, F_OK) :    
        try :
            _fd = open(_api_file_name, 'r')
            _api_conn_info = _fd.read()
            _fd.close()
        except :
            _msg = "Unable to open file containing API connection information "
            _msg += "(" + _api_file_name + ")."
            print "WARNING: " + _msg
    else :
        _msg = "Unable to locate file containing API connection information "
        _msg += "(" + _api_file_name + ")."
        print "WARNING: " + _msg

    if not _api_conn_info :
        if not (options.host and options.port) :
            _msg = "API connection information (host and port) could not be"
            _msg += " automatically determined. Options \"-a\",\"--address\" and "
            _msg += "\"-p\",\"--port\" will have to be specified. "
            print "ERROR: " + _msg
            exit()
        else :
            _api_conn_info = "http://" + options.address + ':' + options.port

    if not options.cloud :
        _msg = "A cloud name (option \"-c\",\"--cloud\") needs to specified"
        print "ERROR: " + _msg

    return _api_conn_info, options

def profiling_phase(api, options, performance_data) :
    '''
    In the profiling phase, an attempt to determine the average deployment
    time for a given VM role is made. To this end, a number of randomly selected
    hosts is used. VMs are deployed *serially* on each host, and the numbers are
    then computed.
    '''

    print "\n# Starting PROFILING phase...."    
    print "### Getting compute node list on cloud \"" + options.cloud + "\"....."
    _hosts = api.hostlist(options.cloud)
    
    performance_data["total_nodes"] = len(_hosts)
    
    _hostnames = []
    for _host in _hosts :
        _hostnames.append(_host["cloud_hostname"])

    _msg = "### The following computes nodes are reported as part of the cloud "
    _msg += "\"" + options.cloud + "\" " + ','.join(_hostnames) + '\n'    
    print _msg
    
    _chose_nodes = sample(_hosts, options.profile)

    _chosen_nodenames = []
    for _node in _chose_nodes :
        _chosen_nodenames.append(_node["cloud_hostname"])

    _msg = "### The following computes nodes were selected for the profiling"
    _msg += " phase: " + ','.join(_chosen_nodenames) + '\n'    
    print _msg

    for _node in _chosen_nodenames :

        _msg = "##### Selected compute node is \"" + _node + "\""
        print _msg

        for _j in range(0, options.samples + 1) :
            _msg = "####### Deploying VM with role \"" + options.role + "\" on "
            _msg += "node \"" + _node  + "\" (Sample " + str(_j) + ")..."
            print _msg
            
            _vm_attrs = api.vmattach(options.cloud, options.role, vm_location = _node)

            _msg = "####### \"" + _vm_attrs["name"] + "\" (" + _vm_attrs["uuid"] 
            _msg += ") successfully deployed" 
            print _msg

            print "####### Obtaining management performance metrics for VM \"" + _vm_attrs["name"] + "\"...."
            _mgt_metric = api.get_latest_management_data(options.cloud, _vm_attrs["uuid"])
            #print _mgt_metric

            if not _j :
                _msg = "####### Since this is the first deployment on this node,"
                _msg += " will ignore this result (VM image might not be pre-"
                _msg += "cached on the compute node."             
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
    performance_data["samples"] = int(options.samples)    
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

    print "### Baseline deployment time for cloud \"" + options.cloud + "\" determined."    
    print _profiling_table

    print "# Ended PROFILING phase.\n"        
    return True

def total_deployment_time(management_metrics) :
    '''
    '''
    total_time = 0

    for _key in management_metrics.keys() :
        if _key.count("mgt") :
            if _key.count("provisioning") :
                if not _key.count("originated") and not _key.count("sla") :
                    total_time += int(management_metrics[_key])
    return total_time

def capacity_phase(api, options, performance_data) :
    '''
    TBD
    '''
    print "\n# Starting CAPACITY phase...."

    _msg = "### IMPORTANT! It is assumed that this is the only process deploying"
    _msg += "VMs on the cloud \"" + options.cloud + "\".\n"
    print _msg
    
    _batch_size = int(performance_data["total_nodes"])    
    _msg = "### Initial batch size (deployment parallelism) is equal the number of compute "
    _msg += "nodes (" + str(_batch_size) + ").\n"
    print _msg

    _max_average_deployment_time = performance_data["average"] * (1 + float(options.increase/100))
    _msg = "### Maximum average deployment time (per-batch) is "
    _msg += str(_max_average_deployment_time) + " seconds.\n"
    print _msg

    _max_failure_ratio = float(int(options.failure)/100.0)
    _msg = "### Maximum failure ratio is " + str(options.failure) + "%.\n"
    print _msg
     
    _batch_nr = 1

    _duration = time() - performance_data["experiment_start"] 

    _total_average_time = 0
    while _duration < options.duration :

        if _batch_nr not in performance_data :
            performance_data["batch" + str(_batch_nr)] = {}

        #_batch_id = str(uuid5(NAMESPACE_DNS, str(randint(0, 1000000000000000000)))).upper()        
        _batch_id = _batch_nr
        
        performance_data["batch" + str(_batch_nr)]["id"] = _batch_id
        
        _msg = "##### Deploying batch " + str(_batch_nr) + " (id " + str(_batch_id)
        _msg += ") with size (parallelism) " + str(_batch_size) + "...."
        print _msg

        api.vmattach(options.cloud, options.role, temp_attr_list="batch=" + str(_batch_id), async=_batch_size)

        _vms_deployed = int(_batch_size * options.completion/100)
        
        _msg = "####### Waiting until " + str(options.completion) + "% of the VMs"
        _msg += " forming the batch " + str(_batch_nr) + " (" + str(_vms_deployed)
        _msg += " VMs) are deployed....."
        print _msg
        api.waituntil(options.cloud, "VM", "ARRIVING", \
                      _batch_size - _vms_deployed, "decreasing", \
                      5)

        _msg = "####### Determining average deployment time for batch " + str(_batch_nr) + "...."
        print _msg
        _batch_vms = api.viewshow(options.cloud, "VM", "batch", str(_batch_id))
        
        _batch_tdt = 0
        _batch_actual_size = len(_batch_vms)
        performance_data["batch" + str(_batch_nr)]["size"] = _batch_actual_size
                
        for _vm in _batch_vms :            
            _mgt_metric = api.get_latest_management_data(options.cloud, _vm["uuid"])
            _batch_tdt += total_deployment_time(_mgt_metric)

        _batch_adt = _batch_tdt/_batch_actual_size
        performance_data["batch" + str(_batch_nr)]["average_deployment_time"] = _batch_adt

        _msg = "####### Average deployment time for batch " + str(_batch_nr)
        _msg += " is " + str(_batch_adt) + " seconds."
        print _msg

        _total_average_time += _batch_adt 

        _average_deployment_time = _total_average_time/_batch_nr
        
        _msg = "####### Obtaining the values of all CB counters"
        print _msg
        _stats = api.stats(options.cloud, "VM")
        
        _msg = "##### Inter-batch statistics"
        print _msg
        
        _vm_stats = _stats["experiment_counters"]["VM"]

        _failure_ratio = float(int(_vm_stats["failed"])/int(_vm_stats["arrived"]))
        performance_data["batch" + str(_batch_nr)]["failure_ratio"] = _failure_ratio        
        _capacity_table = prettytable.PrettyTable(["Batches", "VM Reservations", "VMs ARRIVED", \
                                                "VMs ARRIVING", "VMs DEPARTED", \
                                                "VMs DEPARTING", "VMs FAILED", \
                                                "VMs REPORTED (Cloud)", \
                                                "Avg Deployment Time (s)", \
                                                "Failure Ratio (%)"])

        _capacity_row = []
        _capacity_row.append(_batch_nr)
        _capacity_row.append(_vm_stats["reservations"])
        _capacity_row.append(_vm_stats["arrived"])
        _capacity_row.append(_vm_stats["arriving"])
        _capacity_row.append(_vm_stats["departed"])
        _capacity_row.append(_vm_stats["departing"])
        _capacity_row.append(_vm_stats["failed"])
        _capacity_row.append(_vm_stats["reported"])
        _capacity_row.append(_average_deployment_time)        
        _capacity_row.append(_failure_ratio * 100)
            
        _capacity_table.add_row(_capacity_row)

        print _capacity_table
        print '\n'

        if _average_deployment_time > _max_average_deployment_time :
            _msg = "##### The average deployment time (" + str(_average_deployment_time)
            _msg += " seconds) is higher than the maximum (" + str(_max_average_deployment_time)
            _msg += " seconds). Ending the experiment...."            
            print _msg            
            break

        if _failure_ratio > _max_failure_ratio :
            _msg = "##### The failure ratio (" + str(_failure_ratio) + ") is "
            _msg += " higher than the maximum (" + str(_max_failure_ratio)
            _msg += "). Ending the experiment...."            
            print _msg            
            break

        if _batch_nr >= 2 :
            _delta_failure_ratio = performance_data["batch" + str(_batch_nr)]["failure_ratio"] - \
            performance_data["batch" + str(_batch_nr - 1)]["failure_ratio"]
            if _delta_failure_ratio :
                _msg = "##### The failure ratio increased between batches \""
                _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\""
                _msg += " (" + str(_delta_failure_ratio) + "). Dividing the batch size in half."            
                print _msg            
                _batch_size = int(_batch_size/2)

                if not _batch_size :
                    _msg = "##### Batch size equal zero (too many failures). Ending the experiment..."
                    print _msg
                    return True
            else :
                _msg = "##### The failure ratio between batches \""
                _msg += str(_batch_nr) + "\" and \"" + str(_batch_nr-1) + "\" remained constant."
                print _msg                        
        
        _batch_nr +=1
        
    return True    
        
def main() :
    '''
    '''
    try :
        _error = False
        _perf_dict = {}
        _perf_dict["experiment_start"] = time()
        
        _phase = "connection"
        _api_conn_info, _options = parse_cli()
        _msg = "# Connecting to API daemon (" + _api_conn_info + ")..."
        print _msg
        
        api = APIClient(_api_conn_info)

        if not _options.deployment :
            _phase = "profiling"
            profiling_phase(api, _options, _perf_dict)
        else :
            _perf_dict["selected_nodes"] = 0
            _perf_dict["samples"] = 0    
            _perf_dict["total_samples"] = 0
            _perf_dict["average"] = int(_options.deployment)
            _perf_dict["min"] = int(_options.deployment)
            _perf_dict["max"] = int(_options.deployment)
                       
        _phase = "capacity"
        capacity_phase(api, _options, _perf_dict)

    
    except APIException, obj :
        _error = True
        print "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except APINoSuchMetricException, obj :
        _error = True
        print "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except KeyboardInterrupt :
        print "Aborting this VM."
    
    except Exception, msg :
        _error = True
        print "Problem during the \"" + _phase + "\" phase of the experiment: " + str(msg)
    
    finally :
        if _error :
            exit(0)
        else :
            exit(1)

main()