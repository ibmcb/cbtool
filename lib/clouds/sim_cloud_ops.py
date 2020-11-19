#!/usr/bin/env python3
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
from random import choice, shuffle
from subprocess import Popen, PIPE

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, dic2str, DataOpsException, create_restart_script, weighted_choice
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.network_functions import Nethashget
from .shared_functions import CldOpsException, CommonCloudFunctions 

import traceback

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
        self.additional_rc_contents = ''
        self.last_round_robin_host_index = 0
        self.map_name_to_id = {}
        self.map_uuid_to_name = {}

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench SimCloud"

    @trace
    def connect(self, access_url, authentication_data, region, extra_parms = {}, diag = False) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _region = "everything"            
            _status = 0
            
        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)                    
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, _region            
    
    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)

            _security_group_found = self.check_security_group(vmc_name, security_group_name)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)

            _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_defaults, vm_defaults)
            
            if not (_run_netname_found and _prov_netname_found and \
                    _key_pair_found and _security_group_found) :
                _msg = "Check the previous errors, fix it (using CBTOOL's web"
                _msg += " GUI or CLI"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            if len(_detected_imageids) :
                _status = 0               
            else :
                _status = 1

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            
            _status, _msg = self.common_messages("VMC", {"name" : vmc_name }, "connected", _status, _fmsg)
            return _status, _msg

    @trace
    def check_networks(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        if "prov_netname" not in vm_defaults :
            _prov_netname = vm_defaults["netname"]
        else :
            _prov_netname = "public"

        if "run_netname" not in vm_defaults :
            _run_netname = vm_defaults["netname"]
        else :
            _run_netname = vm_defaults["run_netname"]

        if _run_netname == _prov_netname :                        
            _net_str = "network \"" + _prov_netname + "\""
        else :
            _net_str = "networks \"" + _prov_netname + "\" and \"" + _run_netname + "\""
                        
        _msg = "Checking if the " + _net_str + " can be found on VMC " + vmc_name + "..."
        cbdebug(_msg, True)
                        
        _prov_netname_found = True
        _run_netname_found = True

        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, vmc_defaults, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _registered_imageid_list = []
        if True :
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid != "to_replace" :
                    if not self.is_cloud_image_uuid(_imageid) :
                        if _imageid in self.map_name_to_id :
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, self.map_name_to_id[_imageid])
                        else :
                            self.map_name_to_id[_imageid] = self.generate_random_uuid(_imageid)
                            self.map_uuid_to_name[self.map_name_to_id[_imageid]] = _imageid                                              
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, self.map_name_to_id[_imageid])
    
                        if self.map_name_to_id[_imageid] not in _registered_imageid_list :
                            _registered_imageid_list.append(self.map_name_to_id[_imageid])
                    else :
                        if _imageid not in _registered_imageid_list :
                            _registered_imageid_list.append(_imageid)

        self.map_name_to_id["baseimg"] = self.generate_random_uuid("baseimg")
        self.map_uuid_to_name[self.map_name_to_id["baseimg"]] = "baseimg"

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, self.map_uuid_to_name, vm_defaults)

        if "images_uuid2name" not in vmc_defaults :
            vmc_defaults["images_uuid2name"] = dic2str(self.map_uuid_to_name)

        if "images_name2uuid" not in vmc_defaults :            
            vmc_defaults["images_name2uuid"] = dic2str(self.map_name_to_id)
                
        return _detected_imageids

    @trace
    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["hosts_cpu"] = obj_attr_list["hosts_cpu"].strip()
        obj_attr_list["hosts_mem_per_core"] = obj_attr_list["hosts_mem_per_core"].strip()
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
            obj_attr_list["host_list"][_host_uuid]["hypervisor_type"] = obj_attr_list["hosts_hypervisor_type"]
                                    
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

        _status = 0
        _status, _msg = self.common_messages("HOST", obj_attr_list, "discovered", _status, _fmsg)

        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')

            _msg = "Ok"
            _status = 0
            
        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "cleaned up", _status, _fmsg)
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

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "registered", _status, _fmsg)
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

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "unregistered", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _status = 100
            _nr_instances = "NA"
            _fmsg = "An error has occurred, but no error message was captured"                        
            _nr_instances = self.osci.count_object(obj_attr_list["cloud_name"], "VM", "RESERVATIONS")

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            return _nr_instances                    

    @trace
    def get_ssh_keys(self, vmc_name, key_name, key_contents, key_fingerprint, registered_key_pairs, internal, connection) :
        '''
        TBD
        '''

        registered_key_pairs[key_name] = key_fingerprint + "-NA"

        return True

    @trace
    def get_security_groups(self, vmc_name, security_group_name, registered_security_groups) :
        '''
        TBD
        '''

        registered_security_groups.append(security_group_name)              

        return True
        
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
        return True

    @trace
    def get_instances(self, obj_attr_list) :
        '''
        TBD
        '''
        return True

    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])

            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :

                obj_attr_list["boot_volume_imageid1"] = obj_attr_list["imageid1"]                
                if obj_attr_list["imageid1"] in _map_uuid_to_name :
                    obj_attr_list["imageid1"] = _map_uuid_to_name[obj_attr_list["imageid1"]]
                    _status = 0                    
                else :
                    _fmsg = "image does not exist"
                    _status = 1817                    
            else :
                if obj_attr_list["imageid1"] in _map_name_to_uuid :
                    obj_attr_list["boot_volume_imageid1"] = _map_name_to_uuid[obj_attr_list["imageid1"]]
                    _status = 0                    
                else :
                    _fmsg = "image does not exist"
                    _status = 1817
#                    obj_attr_list["boot_volume_imageid1"] = self.generate_random_uuid(obj_attr_list["imageid1"])

            if str(obj_attr_list["build"]).lower() == "true" :
                obj_attr_list["boot_volume_imageid1"] = self.generate_random_uuid(obj_attr_list["imageid1"])
                _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ") not found: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace
    def get_networks(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Network (" +  obj_attr_list["prov_netname"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace            
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''        
        if len(imageid) == 36 and imageid.count('-') == 4 :
            return True
        
        return False

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        return self.get_instances(obj_attr_list)

    @trace    
    def is_vm_ready(self, obj_attr_list) :

        if self.is_vm_running(obj_attr_list) :

            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"

    @trace
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

    @trace        
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "cloud_vv_type" not in obj_attr_list :
                obj_attr_list["cloud_vv_type"] = "local"

            if "cloud_vv" in obj_attr_list :

                obj_attr_list["last_known_state"] = "about to send volume create request"

                obj_attr_list["cloud_vv_uuid"] = self.generate_random_uuid()

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

                obj_attr_list["volume_list"] += ",/dev/sdb"

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace        
    def vvdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :    
                self.common_messages("VV", obj_attr_list, "destroying", 0, '')
                                
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("VV", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
                         
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["host"] = "NA"
                
            if obj_attr_list["role"] != "predictablevm" :
                obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()
            else :
                obj_attr_list["cloud_vm_uuid"] = "11111111-1111-1111-1111-111111111111"

            self.determine_instance_name(obj_attr_list)
            self.determine_key_name(obj_attr_list)
            
            obj_attr_list["cloud_mac"] = self.generate_random_mac_address()
            self.get_virtual_hardware_config(obj_attr_list)

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            sleep(float(obj_attr_list["pre_creation_delay"]))

            if str(obj_attr_list["userdata"]).lower() == "false" :
                obj_attr_list["config_drive"] = None
            else :
                obj_attr_list["config_drive"] = True                
                  
            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _mark_a = time()
            self.get_images(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_imageid_time", _mark_a)
                                    
            self.get_networks(obj_attr_list) 
            
            if obj_attr_list["role"] != "willfail" :
                True
            else :
                _status = 7778
                _msg = "Deterministic VM failure (\"willfail\")"
                raise CldOpsException(_msg, _status)

            if obj_attr_list["pct_failure"] != " " :
                _pct_failure = int(obj_attr_list["pct_failure"])
                if not weighted_choice([_pct_failure, (100 - _pct_failure)]) :
                    _status = 7779
                    _msg = "Probabilistic VM failure (" + obj_attr_list["pct_failure"] + "%)"
                    raise CldOpsException(_msg, _status)
                else :
                    True
                
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _mark_a = time()
            self.vm_placement(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "vm_placement_time", _mark_a)

            obj_attr_list["volume_list"] = "/dev/sda,/dev/hda"

            self.vvcreate(obj_attr_list)

            self.pre_vmcreate_process(obj_attr_list)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            if str(obj_attr_list["check_ssh"]).lower() != "false" :
                obj_attr_list["check_ssh"] = "pseudotrue" 
                                
            if str(obj_attr_list["transfer_files"]).lower() != "false" :
                obj_attr_list["transfer_files"] = "pseudotrue"
                
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

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            self.post_vmboot_process(obj_attr_list)
            _status, _msg = self.common_messages("VM", obj_attr_list, "created", _status, _fmsg)
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

            self.common_messages("VM", obj_attr_list, "destroying", 0, '')

            if obj_attr_list["host"] != "NA" :
                self.host_resource_update(obj_attr_list, "destroy")

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            cbdebug(str(obj_attr_list["mgt_901_deprovisioning_request_originated"]), True)
            self.vvdestroy(obj_attr_list)
                    
            _status = 0
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "destroyed", _status, _fmsg)
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
            
            if obj_attr_list["captured_image_name"] == "auto" :
                obj_attr_list["captured_image_name"] = obj_attr_list["name"] + "_at_" + str(_time_mark_crs)
            
            obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]
                      
            self.common_messages("VM", obj_attr_list, "capturing", 0, '')

            _img_uuid = self.generate_random_uuid(obj_attr_list["captured_image_name"])
            _img_name = obj_attr_list["captured_image_name"]
            
            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])

            _map_uuid_to_name[_img_uuid] = _img_name
            _map_name_to_uuid[_img_name] = _img_uuid
            
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              obj_attr_list["vmc"], \
                                              False, \
                                              "images_uuid2name", \
                                              dic2str(_map_uuid_to_name), \
                                              False)

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              obj_attr_list["vmc"], \
                                              False, \
                                              "images_name2uuid", \
                                              dic2str(_map_name_to_uuid), \
                                              False)
            
            sleep(1.0)
            
            _time_mark_crc = int(time())
            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
            
            _status = 0
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
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

            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = \
                _time_mark_rrc - _time_mark_rrs

            sleep(5)

            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "runstate altered", _status, _fmsg)
            return _status, _msg

    @trace
    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''
        _time_mark_crs = int(time())            
        operation = obj_attr_list["mtype"]
        obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]

        self.common_messages("VM", obj_attr_list, "migrating", 0, '')

        if obj_attr_list["placement"] != "random" :
            self.host_resource_update(obj_attr_list, "migrate")
        
        _time_mark_crc = int(time())
        obj_attr_list["mgt_503_" + operation + "_request_completed"] = _time_mark_crc - _time_mark_crs

        _status, _msg = self.common_messages("VM", obj_attr_list, operation + "d", 0, '')
        return _status, _msg

    @trace
    def vmresize(self, obj_attr_list) :
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"

    @trace        
    def imgdelete(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')
            _img_name = obj_attr_list["name"]

            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", True, obj_attr_list["vmc_name"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])                

            if _img_name in _map_name_to_uuid :
                _img_uuid = _map_name_to_uuid[_img_name]
                obj_attr_list["boot_volume_imageid1"] = _img_uuid
                del _map_name_to_uuid[_img_name]
                del _map_uuid_to_name[_img_uuid]
                
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              _vmc_attr_list["uuid"], \
                                              False, \
                                              "images_uuid2name", \
                                              dic2str(_map_uuid_to_name), \
                                              False)

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              _vmc_attr_list["uuid"], \
                                              False, \
                                              "images_name2uuid", \
                                              dic2str(_map_name_to_uuid), \
                                              False)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.take_action_if_requested("AI", obj_attr_list, current_step)

            _status = 0

            for _vm in obj_attr_list["vms"].split(',') :
                if _vm.count('|') :
                    _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                if _vm.count("faildb2") :
                    _fmsg = "Forced failure during AI definition"

            if current_step == "all_vms_booted" :

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
                        
                sleep(float(obj_attr_list["pre_creation_delay"]))
    
                if obj_attr_list["create_performance_emitter"].lower() == "true" :
                    
                    _msg = "Starting a new \"performance emitter\" for " + obj_attr_list["log_string"]
                    cbdebug(_msg, True)
    
                    _cmd = "\"" + obj_attr_list["base_dir"] + "/cbact\""
                    _cmd += " --procid=" + self.pid
                    _cmd += " --osp=" + obj_attr_list["osp"]
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
                
        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("AI", obj_attr_list, "defined", _status, _fmsg)
            return _status, _msg

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
        
        except Exception as e :
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

    @trace
    def create_simulated_hosts(self, obj_attr_list, host_uuid) :
        '''
        TBD
        '''
        _cpus = choice(obj_attr_list["hosts_cpu"].split(','))
        obj_attr_list["host_list"][host_uuid]["cores"] = _cpus        
        obj_attr_list["host_list"][host_uuid]["available_cores"] = _cpus

        _mem_per_core = choice(obj_attr_list["hosts_mem_per_core"].split(','))
        _memory = int(_cpus) * int(_mem_per_core) * 1024
        
        obj_attr_list["host_list"][host_uuid]["memory"] = _memory
        obj_attr_list["host_list"][host_uuid]["available_memory"] = _memory
        
        _gpus = choice(obj_attr_list["hosts_gpu"].strip().split(','))

        obj_attr_list["host_list"][host_uuid]["gpus"] = _gpus
        obj_attr_list["host_list"][host_uuid]["available_gpus"] = _gpus
        
        return True
    
    @trace
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

    @trace
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
                _msg = "Failed to create instance: no available cores left"
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
                _msg = "Failed to create instance: no available memory left"
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
                _msg = "Failed to create instance: no available cores left"
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
                _msg = "Failed to create instance: no available memory left"
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
