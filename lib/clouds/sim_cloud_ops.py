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
    Created on Aug 27, 2011

    SimCloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint, choice, shuffle
from uuid import uuid5, NAMESPACE_DNS
from subprocess import Popen, PIPE
from os import chmod

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException, create_restart_script
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.network_functions import Nethashget
from shared_functions import CldOpsException, CommonCloudFunctions 

class SimCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci, expid = None) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.ft_supported = False
        self.expid = expid
        self.last_round_robin_host_index = 0

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench SimCloud."
    
    @trace
    def test_vmc_connection(self, vmc_hn, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        return True

    def generate_random_ip_address(self) :
        '''
        TBD
        '''
        _ip = ".".join(str(randint(1, 255)) for _octect in range(4))
        return _ip
        
    def generate_random_mac_address(self) :
        '''
        TBD
        '''
        _mac_template = [ 0x00, 0x16, 0x3e, randint(0x00, 0x7f), randint(0x00, 0xff), randint(0x00, 0xff) ]
        _mac = ':'.join(map(lambda x: "%02x" % x, _mac_template))
        return _mac

    def generate_random_uuid(self) :
        _uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,1000000000000000000)))).upper()
        return _uuid

    @trace
    def get_virtual_hardware_config(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _vhw_config = {}
            _vhw_config["pico32"] = "vcpus:1,vmemory:192,vstorage:2048,vnics:1"
            _vhw_config["nano32"] = "vcpus:1,vmemory:512,vstorage:61440,vnics:1"
            _vhw_config["micro32"] = "vcpus:1,vmemory:1024,vstorage:61440,vnics:1"
            _vhw_config["copper32"] = "vcpus:1,vmemory:2048,vstorage:61440,vnics:1"
            _vhw_config["bronze32"] = "vcpus:1,vmemory:2048,vstorage:179200,vnics:1"
            _vhw_config["iron32"] = "vcpus:2,vmemory:2048,vstorage:179200,vnics:1"
            _vhw_config["silver32"] = "vcpus:4,vmemory:2048,vstorage:358400,vnics:1"
            _vhw_config["gold32"] = "vcpus:8,vmemory:4096,vstorage:358400,vnics:1"
            _vhw_config["copper64"] = "vcpus:2,vmemory:4096,vstorage:61440,vnics:1"
            _vhw_config["bronze64"]  = "vcpus:2,vmemory:4096,vstorage:870400,vnics:1"
            _vhw_config["silver64"] = "vcpus:4,vmemory:8192,vstorage:1048576,vnics:1"
            _vhw_config["gold64"] = "vcpus:8,vmemory:16384,vstorage:1048576,vnics:1"
            _vhw_config["rhodium64"] = "vcpus:16,vmemory:16384,vstorage:2097152,vnics:1"
            _vhw_config["platinum64"] = "vcpus:24,vmemory:32768,vstorage:2097152,vnics:1"
                
            _vhw_config["premium"] = "cpu_upper:1000,cpu_lower:1000,memory_upper:100,memory_lower:100"
            _vhw_config["standard"] = "cpu_upper:1000,cpu_lower:500,memory_upper:100,memory_lower:50"
            _vhw_config["value"] = "cpu_upper:-1,cpu_lower:0,memory_upper:100,memory_lower:0"
            
            if "size" not in obj_attr_list :
                obj_attr_list["size"] = "micro32"
            else :
                obj_attr_list["size"] = choice(obj_attr_list["size"].strip().split(','))

            if "class" not in obj_attr_list :
                obj_attr_list["class"] = "standard"
            
            _curr_vhw_config = _vhw_config[obj_attr_list["size"]] + ',' + _vhw_config[obj_attr_list["class"]]
            _curr_vhw_config = str2dic(_curr_vhw_config)
            obj_attr_list.update(_curr_vhw_config)
            _status = 0
        
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "virtual hardware configuration parameters could not be "
                _msg += "determined:" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "virtual hardware configuration parameters were "
                _msg += "successfully determined."
                cbdebug(_msg)
                return True

    def create_simulated_hosts(self, obj_attr_list, host_uuid) :
        '''
        TBD
        '''
        _cpus = choice(obj_attr_list["hosts_cpu"])
        obj_attr_list["host_list"][host_uuid]["cores"] = _cpus        
        obj_attr_list["host_list"][host_uuid]["available_cores"] = _cpus

        _mem_per_core = choice(obj_attr_list["hosts_mem_per_core"])         

        _memory = int(_cpus) * int(_mem_per_core) * 1024
        
        obj_attr_list["host_list"][host_uuid]["memory"] = _memory
        obj_attr_list["host_list"][host_uuid]["available_memory"] = _memory
        
        _gpus = choice(obj_attr_list["hosts_gpu"].strip().split(','))

        obj_attr_list["host_list"][host_uuid]["gpus"] = _gpus
        obj_attr_list["host_list"][host_uuid]["available_gpus"] = _gpus
        
        return True

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["hosts_cpu"] = obj_attr_list["hosts_cpu"].strip().split(',')
        obj_attr_list["hosts_mem_per_core"] = obj_attr_list["hosts_mem_per_core"].strip().split(',')
            
        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''
        _auto_name = False
        if len(obj_attr_list["initial_hosts"]) < 2 :
            _auto_name = True
            obj_attr_list["host_count"] = int(obj_attr_list["hosts_per_vmc"])
        else :
            obj_attr_list["initial_hosts"] = obj_attr_list["initial_hosts"].split(',')
            obj_attr_list["host_count"] = len(obj_attr_list["initial_hosts"])
    
        for _host_n in range(0, obj_attr_list["host_count"]) :
            _host_uuid = self.generate_random_uuid()
            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                                
            if obj_attr_list["host_user_root"].lower() == "true" :
                obj_attr_list["host_list"][_host_uuid]["login"] = "root"                        
            else :
                obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["host_list"][_host_uuid]["username"]
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = self.generate_random_ip_address()
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            if _auto_name :
                obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = "simhost" + obj_attr_list["name"][-1] + str(_host_n)
            else :
                obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = obj_attr_list["initial_hosts"][_host_n]

            obj_attr_list["host_list"][_host_uuid]["name"] = "host_"  + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["cloud_vm_uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
                        
            if _host_n == 0 :
                obj_attr_list["host_list"][_host_uuid]["function"] = "controller"
            else :
                obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"

            self.create_simulated_hosts(obj_attr_list, _host_uuid)
            obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
            obj_attr_list["host_list"][_host_uuid]["simulated"] = "True"
            obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]
            
            if "login" in obj_attr_list :
                obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["login"]
            else :
                obj_attr_list["host_list"][_host_uuid]["login"] = "root"

            obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
            obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
            obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
            _time_mark_prc = int(time())
            obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start

        obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

        self.additional_host_discovery (obj_attr_list)
        self.populate_interface(obj_attr_list)

        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _msg = "Ok"
            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])            

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = self.generate_random_ip_address()

            _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
            _fmsg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()

            obj_attr_list["arrival"] = int(time())
            
            if obj_attr_list["discover_hosts"].lower() == "true" :
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            for _net_n in range(1, int(obj_attr_list["networks_per_vmc"]) + 1) :
                obj_attr_list["network_private" + str(_net_n)] = obj_attr_list["network_type"]
            
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def vmcunregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            
            _time_mark_drs = int(time())

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])    
        
            if "cleanup_on_detach" in obj_attr_list and obj_attr_list["cleanup_on_detach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            _time_mark_prc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_prc - _time_mark_drs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list):
        '''
        TBD
        '''
        obj_attr_list["last_known_state"] = "running with ip assigned"
        if obj_attr_list["role"] != "predictablevm" :
            obj_attr_list["run_cloud_ip"] = self.generate_random_ip_address()
            obj_attr_list["prov_cloud_ip"] = self.generate_random_ip_address()            
        else :
            obj_attr_list["run_cloud_ip"] = "1.2.3.4"
            obj_attr_list["prov_cloud_ip"] = "1.2.3.4"
            
        # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
        obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"] 
            
        obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_uuid"] + ".simcloud.com"
        return True        

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return self.osci.count_object(obj_attr_list["cloud_name"], "VM", "ARRIVED")

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        return True
    
    def is_vm_ready(self, obj_attr_list) :

        if self.is_vm_running(obj_attr_list) :

            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")

            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"

    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''
        if "host_name" not in obj_attr_list :

            if obj_attr_list["placement"] == "first-fit" or obj_attr_list["placement"] == "random" :

                _vmc_list = list(self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC"))
    
                if obj_attr_list["placement"] == "random" :
                    shuffle(_vmc_list)
    
                for _vmc_uuid in _vmc_list :

                    _vmc_host_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, _vmc_uuid, False)["hosts"]
                    
                    _host_list = _vmc_host_list.split(',')
                    
                    if obj_attr_list["placement"] == "random" :
                        shuffle(_host_list)                    
                    
                    for _host_uuid in _host_list :
                        _lock = self.lock(obj_attr_list["cloud_name"], "HOST", _host_uuid, "hostlock")
                        _host_core_found, _host_mem_found = self.check_host_capacity(obj_attr_list, _host_uuid)

                        if _host_core_found and _host_mem_found :
                            self.host_resource_update(obj_attr_list, "create")
                            self.unlock(obj_attr_list["cloud_name"], "HOST", _host_uuid, _lock)
                            break
                        else :
                            self.unlock(obj_attr_list["cloud_name"], "HOST", _host_uuid, _lock)

                    if _host_core_found and _host_mem_found :
                        break
                        
            else :
                _status = 7776
                obj_attr_list["host"] = "NA"
                _msg = "Unknown placement algorithm (" + obj_attr_list["placement"] + ")"
                raise CldOpsException(_msg, _status)
        else :
            _host_core_found = True
            _host_mem_found = True
            obj_attr_list["host"] = self.osci.object_exists(obj_attr_list["cloud_name"], "HOST", obj_attr_list["host_name"], True, False)
            self.host_resource_update(obj_attr_list, "create")

        if not _host_core_found :
            _status = 7777
            _msg = "Failed to create VM image: no available cores left on ANY host"
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                      "VMC", obj_attr_list["vmc"], False, \
                                                      "cpu_drop", 1, True)
            raise CldOpsException(_msg, _status)

        if not _host_mem_found :
            _status = 7777
            _msg = "Failed to create VM image: no available memory left on ANY host"
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                      "VMC", obj_attr_list["vmc"], False, \
                                                      "memory_drop", 1, True)                
            raise CldOpsException(_msg, _status)            

        return True

    def check_host_capacity(self, obj_attr_list, host_uuid) :
        '''
        TBD
        '''
        _host_core_found = False
        _host_mem_found = False        
        
        _host = self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, host_uuid, False)
        
        if int(_host["available_cores"]) >= int(obj_attr_list["vcpus"]) :
            _host_core_found = True
            
            if int(_host["available_memory"]) >= int(obj_attr_list["vmemory"]) :
                _host_mem_found = True
                obj_attr_list["host_name"] = _host["name"][5:]
                obj_attr_list["host"] = host_uuid

        return _host_core_found, _host_mem_found

    def host_resource_update(self, obj_attr_list, operation) :
        '''
        TBD
        '''

        if operation == "create" :
            _cores = -int(obj_attr_list["vcpus"])
            _memory = -int(obj_attr_list["vmemory"])
            _host_uuid = obj_attr_list["host"]

            if self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "HOST", _host_uuid, False, \
                                              "available_cores", _cores, True) >= 0 :
                True
            
            else :
                _status = 7778
                _msg = "Failed to create VM image: no available cores left"
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                          "VMC", obj_attr_list["vmc"], False, \
                                                          "cpu_drop", 1, True)
                raise CldOpsException(_msg, _status)
            

            if self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "HOST", _host_uuid, False, \
                                              "available_memory", _memory, True) >= 0 :
                True
                
            else :
                _status = 7778
                _msg = "Failed to create VM image: no available memory left"
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                          "VMC", obj_attr_list["vmc"], False, \
                                                          "memory_drop", 1, True)                
                raise CldOpsException(_msg, _status)

        elif operation == "destroy" :
            _cores = int(obj_attr_list["vcpus"])
            _memory = int(obj_attr_list["vmemory"])
            _host_uuid = obj_attr_list["host"]


            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                          "HOST", _host_uuid, False, \
                                          "available_cores", _cores, True)
            
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                      "HOST", _host_uuid, False, \
                                                      "available_memory", _memory, True)
        
        elif operation == "migrate" :
            _cores = -_cores
            _memory = -_memory
            _host_uuid = obj_attr_list["destination_uuid"]    

            if self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "HOST", _host_uuid, False, \
                                              "available_cores", _cores, True) >= 0 :
                True
            
            else :
                _status = 7778
                _msg = "Failed to create VM image: no available cores left"
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                          "VMC", obj_attr_list["vmc"], False, \
                                                          "cpu_drop", 1, True)
                raise CldOpsException(_msg, _status)
            

            if self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "HOST", _host_uuid, False, \
                                              "available_memory", _memory, True) >= 0 :
                True
                
            else :
                _status = 7778
                _msg = "Failed to create VM image: no available memory left"
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                          "VMC", obj_attr_list["vmc"], False, \
                                                          "memory_drop", 1, True)                
                raise CldOpsException(_msg, _status)

            _cores = int(obj_attr_list["vcpus"])
            _memory = int(obj_attr_list["vmemory"])
            _host_uuid = obj_attr_list["host"]

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                          "HOST", _host_uuid, False, \
                                          "available_cores", _cores, True)
            
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                      "HOST", _host_uuid, False, \
                                                      "available_memory", _memory, True)

        else :
            _cores = False
            _memory = False
            _host_uuid = False

        return True

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["role"] != "predictablevm" :
                obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()
            else :
                obj_attr_list["cloud_vm_uuid"] = "11111111-1111-1111-1111-111111111111"

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] 
            obj_attr_list["cloud_vm_name"] += '-' + "vm_" + obj_attr_list["name"].split("_")[1] 
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")            

            obj_attr_list["cloud_mac"] = self.generate_random_mac_address()
            self.get_virtual_hardware_config(obj_attr_list)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            if obj_attr_list["role"] != "willfail" :
                True
            else :
                _status = 7778
                _msg = "Failed to create VM image"
                raise CldOpsException(_msg, _status)

            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            self.vm_placement(obj_attr_list)

            if "meta_tags" in obj_attr_list :
                if obj_attr_list["meta_tags"] != "empty" and \
                obj_attr_list["meta_tags"].count(':') and \
                obj_attr_list["meta_tags"].count(',') :
                    obj_attr_list["meta_tags"] = str2dic(obj_attr_list["meta_tags"])
                else :
                    obj_attr_list["meta_tags"] = "empty"
            else :
                obj_attr_list["meta_tags"] = "empty"
  
            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                         obj_attr_list["uuid"], "utc_offset_on_vm", "3600") 
            
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                         obj_attr_list["uuid"], "mgt_006_instance_preparation", "1")

            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                         obj_attr_list["uuid"], "status", "Application starting up...") 

            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                
                _status = 916

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if "lvt_cnt" in obj_attr_list :
                del obj_attr_list["lvt_cnt"]
                
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation was rolled back)"
                cberr(_msg, True)
                
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                self.vmdestroy(obj_attr_list)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())
            
            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                
            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            if obj_attr_list["host"] != "NA" :
                self.host_resource_update(obj_attr_list, "destroy")

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
            
            _status = 0
            
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmcapture(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_crs = int(time())
            obj_attr_list["captured_image_name"] = obj_attr_list["name"] + "_at_" + str(_time_mark_crs)
            
            obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]
                      
            _msg = "Waiting for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
            _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
            _msg += "\"..."
            cbdebug(_msg, True)
            
            sleep(1.0)
            
            _time_mark_crc = int(time())
            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs

            _msg = "VM " + obj_attr_list["name"] + " capture request completed."
            cbdebug(_msg)

            _msg = "VM capture is not implemented for \"SimClouds\""
            cbdebug(_msg)
            
            _status = 0
            
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]

            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = \
                _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate completed."
            cbdebug(_msg)
            sleep(5)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not have its runstate changed "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "had its runstate successfully "
                _msg += "changed on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''
        _time_mark_crs = int(time())            
        operation = obj_attr_list["mtype"]
        obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]

        _msg = "Sending a " + operation + " request for "  + obj_attr_list["name"]
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)

        if obj_attr_list["placement"] != "random" :
            self.host_resource_update(obj_attr_list, "migrate")
        
        _time_mark_crc = int(time())
        obj_attr_list["mgt_503_" + operation + "_request_completed"] = _time_mark_crc - _time_mark_crs

        cbdebug("VM " + obj_attr_list["name"] + " " + operation + " request completed.")

        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
        _msg += "was successfully "
        _msg += operation + "ed on SimCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
            
        return 0, _msg

    @trace        
    def aidefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"

            _vg = ValueGeneration("NA")
            
            for _vm in obj_attr_list["vms"].split(',') :
                _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                # default distribution is 10-500.  If the user set distribution, use it.
                _distribution = 'uniformIXIXI10I500'
                if 'deployment_time_value' in obj_attr_list:
                    _distribution = obj_attr_list['deployment_time_value']

                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                             _vm_uuid, "mgt_007_application_start", \
                                             int(_vg.get_value(_distribution, 0)))

                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                             obj_attr_list["uuid"], "status", "Application starting up...") 

                if _vm.count("faildb2") :
                    _fmsg = "Forced failure during AI definition"

            self.take_action_if_requested("AI", obj_attr_list, "all_vms_booted")

            if obj_attr_list["create_performance_emitter"].lower() == "true" :
                
                _msg = "Starting a new \"performance emitter\" for " + obj_attr_list["name"]
                cbdebug(_msg, True)

                _cmd = obj_attr_list["base_dir"] + "/cbact"
                _cmd += " --procid=" + self.pid
                _cmd += " --osp=" + obj_attr_list["osp"]
                _cmd += " --msp=" + obj_attr_list["msp"]
                _cmd += " --operation=performance-emit"
                _cmd += " --cn=" + obj_attr_list["cloud_name"]
                _cmd += " --uuid=" + obj_attr_list["uuid"]
                _cmd += " --daemon"
                cbdebug(_cmd)

                _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)

                if _proc_h.pid :
                    _msg = "Performance emitter command \"" + _cmd + "\" "
                    _msg += " successfully started a new daemon."
                    _msg += "The process id is " + str(_proc_h.pid) + "."
                    cbdebug(_msg)

                    _obj_id = obj_attr_list["uuid"] + '-' + "performance-emit"
                    
                    _process_identifier = "AI-" + _obj_id

                    self.osci.add_to_list(obj_attr_list["cloud_name"], \
                                          "GLOBAL", \
                                          "running_processes", \
                                          _process_identifier)

                    create_restart_script("restart_cb_perf-emitter", \
                                          _cmd, \
                                          obj_attr_list["username"], \
                                          "performance-emit", \
                                          obj_attr_list["name"], \
                                          obj_attr_list["uuid"])


            if _fmsg == "Forced failure during AI definition" :
                _status = 181
            else :
                _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg
