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
    Created on Feb 22, 2017

    PLM Cloud Object Operations Library

    @author: Marcio A. Silva
'''
import libxml2
import os
from time import time, sleep
from random import choice, randint
from hashlib import sha256

from libvirt import *

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, dic2str, is_number, DataOpsException
from lib.remote.process_management import ProcessManagement
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

class PlmCmds(CommonCloudFunctions) :
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
        self.lvirtconn = {}
        self.expid = expid
        self.api_error_counter = {}
        self.max_api_errors = 10
        self.additional_rc_contents = ''

        self.vhw_config = {}
        self.vhw_config["pico32"] = { "vcpus" : "1", "vmem" : "256", "vstorage" : "2048", "vnics" : "1" }
        self.vhw_config["nano32"] = { "vcpus" : "1", "vmem" : "512", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["micro32"] = { "vcpus" : "1", "vmem" : "1024", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["copper32"] = { "vcpus" : "1", "vmem" : "2048", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze32"] = { "vcpus" : "1", "vmem" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["iron32"] = { "vcpus" : "2", "vmem" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["silver32"] = { "vcpus" : "4", "vmem" : "2048", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["gold32"] = { "vcpus" : "8", "vmem" : "4096", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["copper64"] = { "vcpus" : "2", "vmem" : "4096", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze64"]  = { "vcpus" : "2", "vmem" : "4096", "vstorage" : "870400", "vnics" : "1" }
        self.vhw_config["silver64"] = { "vcpus" : "4", "vmem" : "8192", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["gold64"] = { "vcpus" : "8", "vmem" : "16384", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["platinum64"] = { "vcpus" : "16", "vmem" : "16384", "vstorage" : "2097152", "vnics" : "1" }
                
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Parallel Libvirt Manager Cloud"

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}, diag = False, generate_rc = False) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _endpoint_ip = "NA"            
            _fmsg = "An error has occurred, but no error message was captured"
                        

            for _endpoint in access.split(',') :
                _endpoint, _endpoint_name, _endpoint_ip= self.parse_endpoint(_endpoint, "qemu+tcp", False)
                
                if _endpoint_ip not in self.lvirtconn :
                    self.lvirtconn[_endpoint_ip] = open(_endpoint + "/system")
                    self.lvirtconn[_endpoint_ip].getSysinfo()

            _status -= 100
            
        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)
            
        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " connection to endpoint \"" + _endpoint_ip + "\" failed: " + _fmsg
                cberr(_msg)                    
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, ''
    
    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True, True)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_defaults['poolname'], vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it (using lxc CLI)"
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
        _prov_netname = vm_defaults["netname"]
        _run_netname = vm_defaults["netname"]

        _net_str = "network \"" + _prov_netname + "\""

        _prov_netname_found = False
        _run_netname_found = False

        for _endpoint in list(self.lvirtconn.keys()) :

            _msg = "Checking if the " + _net_str + " can be "
            _msg += "found on VMC " + vmc_name + " (endpoint " + _endpoint + ")..."
            cbdebug(_msg, True)

            for _network in self.lvirtconn[_endpoint].listNetworks() :
                if _network == _prov_netname :
                    _prov_netname_found = True
                    
                if _network == _run_netname :
                    _run_netname_found = True                    

        if not _prov_netname_found : 
            _msg = "ERROR! Please make sure that the provisioning network " + _prov_netname + " can be found"
            _msg += " VMC " + vmc_name  + " (endpoint " + _endpoint + ")..."
            _fmsg = _msg 
            cberr(_msg, True)

        if not _prov_netname_found : 
            _msg = "ERROR! Please make sure that the running network " + _run_netname + " can be found"
            _msg += " VMC " + vmc_name  + " (endpoint " + _endpoint + ")..."
            _fmsg = _msg 
            cberr(_msg, True)
            
        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, poolname, vm_defaults) :
        '''
        TBD
        '''

        for _endpoint in list(self.lvirtconn.keys()) :

            self.common_messages("IMG", { "name": vmc_name, "endpoint" : _endpoint }, "checking", 0, '')

            _map_name_to_id = {}
            _map_id_to_name = {}

            _storage_pool_handle = self.lvirtconn[_endpoint].storagePoolLookupByName(poolname)          
            _registered_image_list = _storage_pool_handle.listVolumes()

            _registered_imageid_list = []

            for _registered_image in _registered_image_list :
                _image_uuid = self.generate_random_uuid(_registered_image)
                _registered_imageid_list.append(_image_uuid)

                _map_name_to_id[_registered_image] = _image_uuid
                
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]

                if _imageid != "to_replace" :
                    if _imageid in _map_name_to_id and _map_name_to_id[_imageid] != _imageid :
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    else :
                        _map_name_to_id[_imageid] = _imageid
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])                        

                    _map_id_to_name[_map_name_to_id[_imageid]] = _imageid
                
            _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_id_to_name, vm_defaults)

            if not _detected_imageids :
                return _detected_imageids

        return _detected_imageids

    @trace
    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        for _endpoint in self.lvirtconn :
            _host_info = self.lvirtconn[_endpoint].getInfo()
            _host_extended_info = self.lvirtconn[_endpoint].getSysinfo()

            for _line in _host_extended_info.split('\n') :
                if _line.count("uuid") :                    
                    _host_uuid = _line.split('>')[1].split('<')[0]

            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"

            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], \
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_endpoint, True)

            obj_attr_list["host_list"][_host_uuid]["name"] = "host_"  + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["cloud_vm_uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
            obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"
            obj_attr_list["host_list"][_host_uuid]["cores"] = _host_info[2]
            obj_attr_list["host_list"][_host_uuid]["memory"] = _host_info[1]
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = _endpoint             
            obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
            obj_attr_list["host_list"][_host_uuid]["simulated"] = False
            obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]

            obj_attr_list["host_list"][_host_uuid]["hypervisor_type"] = "kvm"
                                                
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

        self.additional_host_discovery(obj_attr_list)

        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _running_instances = True

            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False

                for _endpoint in self.lvirtconn :

                    _proc_man = ProcessManagement(username = "root", \
                                                  hostname = _endpoint, \
                                                  cloud_name = obj_attr_list["cloud_name"])

                    _cmd = "sudo pkill -9 -f 'rinetd -c /tmp/cb'; sudo rm -rf /tmp/cb-*.rinetd.conf"
                    _status, _result_stdout, _fmsg = _proc_man.run_os_command(_cmd, raise_exception=False) 
                    
                    _domain_list = self.lvirtconn[_endpoint].listAllDomains()
                    
                    for _domain in _domain_list :
                        if _domain.name().count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :

                            _running_instances = True
                            
                            _msg = "Terminating instance: " 
                            _msg += _domain.UUIDString() + " (" + str(_domain.name()) + ")"
                            cbdebug(_msg, True)
                            
                            if _domain.state()[0] == VIR_DOMAIN_RUNNING :
                                _domain.destroy()
                                
                            _domain.undefine()

                sleep(_wait)

                _curr_tries += 1

            self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')
            
            _curr_tries = 0    
            _created_volumes = True
            while _created_volumes and _curr_tries < _max_tries :

                _created_volumes = False

                _storage_pool_list = [ obj_attr_list["poolname"] ]
                for _storage_pool in _storage_pool_list :
                    _storage_pool_handle = self.lvirtconn[_endpoint].storagePoolLookupByName(_storage_pool)                
                    _volume_list = _storage_pool_handle.listVolumes()

                    for _volume in _volume_list :
                        if _volume.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                            _created_volumes = True
                            _msg = "Removing volume : " 
                            _msg += self.generate_random_uuid(_volume) + " (" + str(_volume) + ")"
                            cbdebug(_msg, True)                                
                            
                            _storage_pool_handle.storageVolLookupByName(_volume).delete(0)
                            
                sleep(_wait)

                _curr_tries += 1

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "Some instances on VMC \"" + obj_attr_list["name"] + "\""
                _fmsg += " could not be removed because they never became active"
                _fmsg += ". They will have to be removed manually."
                cberr(_msg, True)
            else :
                _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)
                        
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
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])            

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"], obj_attr_list)

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["name"], False)

            _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
            _fmsg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid(obj_attr_list["name"])

            obj_attr_list["arrival"] = int(time())
            
            if obj_attr_list["discover_hosts"].lower() == "true" :
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
            
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = \
            _time_mark_prc - _time_mark_prs
            
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
    def vmcount(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"                        
            _nr_instances = 0

            sleep(15)
            for _vmc_uuid in self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC") :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                      "VMC", False, _vmc_uuid, \
                                                      False)
                
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             _vmc_attr_list["name"], obj_attr_list)

                for _endpoint in self.lvirtconn :
                    _domain_list = self.lvirtconn[_endpoint].listAllDomains()
                    for _domain in _domain_list :
                        if _domain.name().count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                            _nr_instances += 1

        except Exception as e :
            _status = 23
            _nr_instances = "NA"
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
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        
        _network_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].networkLookupByName(obj_attr_list["run_netname"])
            
        for _item in _network_handle.DHCPLeases() :
            if _item["mac"] == obj_attr_list["cloud_vm_mac"] :                
                obj_attr_list["run_cloud_ip"] = _item["ipaddr"]
                
                if str(obj_attr_list["ports_base"]).lower() != "false" :
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["host_cloud_ip"]                    
                else :
                    obj_attr_list["prov_cloud_ip"] = _item["ipaddr"]
                obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]                    
                return True
        return False
        
    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", endpoints = "all", identifier = "all") :
        '''
        TBD
        '''

        _instances = []
        _fmsg = "Error while getting instances"
        _call = "NA"
        
        if endpoints == "all" :
            _endpoints = list(self.lvirtconn.keys())
        else :
            _endpoints = [endpoints]
                      
        try :
            for _endpoint in _endpoints :            
                if identifier == "all" :
                    _call = "listAllDomains()"                    
                    _instances = self.lvirtconn[_endpoint].listAllDomains()
                                                                   
                else :
                    _call = "lookupByName()"
                    _instances = self.lvirtconn[_endpoint].lookupByName(identifier)

            _status = 0
        
        except CldOpsException as obj :
            _status = obj.status
            _xfmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _xfmsg = str(msg)

        except Exception as e :
            _status = 23
            _xfmsg = str(e)
            
        finally :
            if _status :
                _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + _xfmsg
                if identifier not in self.api_error_counter :
                    self.api_error_counter[identifier] = 0
                
                self.api_error_counter[identifier] += 1
                                
                if self.api_error_counter[identifier] > self.max_api_errors :
                    raise CldOpsException(_fmsg, _status)
                else :
                    cbwarn(_fmsg)
                    return []
            else :
                return _instances

    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _storage_pool_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].storagePoolLookupByName(obj_attr_list["poolname"])

            _xml_contents = _storage_pool_handle.XMLDesc(0)
            _xml_doc = libxml2.parseDoc(_xml_contents)
            _xml_ctx = _xml_doc.xpathNewContext()
            
            _path_list = _xml_ctx.xpathEval("/pool/target/path")
            if _path_list :
                obj_attr_list["pool_path"] = _path_list[0].content

            _image_list = _storage_pool_handle.listVolumes()

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += self.get_description()

            _candidate_images = []

            for _image in _image_list :
                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :

                    if self.generate_random_uuid(_image) == obj_attr_list["imageid1"] :
                        _candidate_images.append(_image) 
                else :
                    if _image == obj_attr_list["imageid1"] :
                        _candidate_images.append(_image)

            if len(_candidate_images) :
                obj_attr_list["imageid1"] = _candidate_images[0]
                obj_attr_list["boot_volume_imageid1"] = self.generate_random_uuid(_candidate_images[0])
                _volume_data = _storage_pool_handle.storageVolLookupByName(_candidate_images[0])
                obj_attr_list["boot_volume_snapshot_path"] = _volume_data.path()
                obj_attr_list["boot_volume_snapshot_size"] = int(_storage_pool_handle.storageVolLookupByName(obj_attr_list["imageid1"]).info()[1])/(1024*1024)
                _xml_contents = _volume_data.XMLDesc(0)
                _xml_doc = libxml2.parseDoc(_xml_contents)
                _xml_ctx = _xml_doc.xpathNewContext()
            
                _volume_format = _xml_ctx.xpathEval("/volume/target/format/@type")
                if _volume_format :
                    obj_attr_list["boot_volume_format"] = _volume_format[0].content

                _status = 0
            else :
                _fmsg = "Unable to locate image \"" + obj_attr_list["imageid1"] + "\""
                _fmsg += " on " + self.get_description()
                _status = 1927

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

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

            _network_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].networkLookupByName(obj_attr_list["netname"])

            obj_attr_list["network_bridge_name"] = _network_handle.bridgeName()

            obj_attr_list["extra_vnics"] = []
            if str(obj_attr_list["extra_netnames"]).lower() != "false" :
                for _exn in obj_attr_list["extra_netnames"].split(',') :
                    _network_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].networkLookupByName(_exn)
        
                    _exbn = _network_handle.bridgeName()
                    obj_attr_list["extra_vnics"].append([_exn, _exbn])

            _status = 0

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

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
        try :
            if "host_cloud_ip" in obj_attr_list :
                _host_ip = obj_attr_list["host_cloud_ip"]
            else :
                _host_ip = "all"
            
            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _instance_state = _instance.state()[0]
                
            else :
                _instance_state = "non-existent"

            if _instance_state == VIR_DOMAIN_RUNNING :
                return True
            else :
                return False
        
        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)
    
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''        
        if self.is_vm_running(obj_attr_list) :

            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
            return False
        
    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''        
        obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(choice(list(self.lvirtconn.keys())), True)
        
        return True

    def vvcreate(self, obj_attr_list, boot = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            if not boot and "cloud_vv" not in obj_attr_list :
                obj_attr_list["cloud_vv_uuid"] = "none"

            else :
                
                _xml_file = self.generate_libvirt_vv_template(obj_attr_list, boot)
                
                obj_attr_list["last_known_state"] = "about to send volume create request"

                if not boot :        
                    obj_attr_list["cloud_vv_uuid"] = self.generate_random_uuid(obj_attr_list["cloud_vm_name"])
                else :
                    obj_attr_list["boot_from_volume"] = "true"

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

                _storage_pool_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].storagePoolLookupByName(obj_attr_list["poolname"])

                _storage_pool_handle.createXML(_xml_file, 0)
                                                  
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace        
    def vvdestroy(self, obj_attr_list, boot = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _storage_pool_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].storagePoolLookupByName(obj_attr_list["poolname"])

            for _volume in obj_attr_list["volume_list"].split(',') :
                if _volume.count(":") == 4 :
                    _vol_name, _vol_path, _vol_format, _backing_path, _backing_format = _volume.strip().split(':')
                    _storage_pool_handle.storageVolLookupByName(_vol_name).delete(0)
                
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

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
            
            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list)

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            if str(obj_attr_list["ports_base"]).lower() != "false" :
                obj_attr_list["prov_cloud_port"] = str(int(obj_attr_list["ports_base"]) + int(obj_attr_list["name"].replace("vm_",'')))

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            _mark_a = time()
            self.get_images(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_image_time", _mark_a)

            _mark_a = time()
            self.get_networks(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_network_time", _mark_a)

            _mark_a = time()
            self.vvcreate(obj_attr_list, True)
            self.annotate_time_breakdown(obj_attr_list, "get_create_boot_volume_time", _mark_a)

            _mark_a = time()
            self.vvcreate(obj_attr_list, False)
            self.annotate_time_breakdown(obj_attr_list, "get_create_boot_volume_time", _mark_a)
                        
            obj_attr_list["config_drive"] = True

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            self.pre_vmcreate_process(obj_attr_list)

            _mark_a = time()
            self.generate_mac_addr(obj_attr_list)

            self.ship_cloud_init_iso(obj_attr_list)  
            _xml_file = self.generate_libvirt_vm_template(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "ship_cloudinit_iso_time", _mark_a)
            
            _mark_a = time()            
            _domain = self.lvirtconn[obj_attr_list["host_cloud_ip"]].defineXML(_xml_file)
            _domain.create()
            self.annotate_time_breakdown(obj_attr_list, "domain_creation_time", _mark_a)
                                    
            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid(obj_attr_list["cloud_vm_name"])

            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            obj_attr_list["pcm_005_instance_creation_time"] = obj_attr_list["mgt_003_provisioning_request_completed"]

            _mark_a = time()
            if str(obj_attr_list["ports_base"]).lower() != "false" :
                self.configure_port_mapping(obj_attr_list, "setup")
                self.annotate_time_breakdown(obj_attr_list, "domain_port_mapping_time", _mark_a)

            if str(obj_attr_list["ports_base"]).lower() != "false" :
                if obj_attr_list["check_boot_complete"].lower() == "tcp_on_22" :
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
            
            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                _status = 916

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list)
            
            _wait = int(obj_attr_list["update_frequency"])
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0

            if "host_cloud_ip" in obj_attr_list :
                _host_ip = obj_attr_list["host_cloud_ip"]
    
                _instance = self.get_instances(obj_attr_list, "vm", _host_ip, \
                                               obj_attr_list["cloud_vm_name"])
                                        
                if _instance :
                    self.common_messages("VM", obj_attr_list, "destroying", 0, '')
    
                    while _instance and _curr_tries < _max_tries :
                        
                        _instance = self.get_instances(obj_attr_list, "vm", _host_ip, \
                                                       obj_attr_list["cloud_vm_name"])


                        if _instance :

                            if _instance.state()[0] == VIR_DOMAIN_RUNNING :
                                _instance.destroy()
                                    
                            _instance.undefine()
                                                    
                        sleep(_wait)
                        _curr_tries += 1
    
                    if str(obj_attr_list["ports_base"]).lower() != "false" :
                        self.configure_port_mapping(obj_attr_list, "teardown")    

                _time_mark_drc = int(time())
                obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                    _time_mark_drc - _time_mark_drs
    
                self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

                self.vvdestroy(obj_attr_list)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list)
            
            _wait = int(obj_attr_list["update_frequency"])

            _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                _instance.destroy()
                
                _vol_path = obj_attr_list["volume_list"].split(',')[0].split(':')[1]

                _storage_pool_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].storagePoolLookupByName(obj_attr_list["poolname"])                
                _volume_handle = self.lvirtconn[obj_attr_list["host_cloud_ip"]].storageVolLookupByPath(_vol_path)

                _xml_file = ""
                _xml_file += "\t<volume>\n"
                _xml_file += "\t<capacity unit=\"M\">" + str(int(self.vhw_config[obj_attr_list["size"]]["vstorage"])) + "</capacity>\n"                    
                _xml_file += "\t<name>" + obj_attr_list["captured_image_name"] + "</name>\n"                    
                _xml_file += "\t<target>\n"
                _xml_file += "\t\t<permissions>\n"
                _xml_file += "\t\t\t<mode>0777</mode>\n"
                _xml_file += "\t\t</permissions>\n"
                _xml_file += "\t\t<path>" + obj_attr_list["pool_path"] + "</path>\n"        
                _xml_file += "\t\t<format type='" + "qcow2"  + "'/>\n"                
                _xml_file += "\t</target>\n"
                _xml_file += "\t</volume>\n"

                _storage_pool_handle.createXMLFrom(_xml_file, _volume_handle, 0)                
                                
                obj_attr_list["cloud_image_uuid"] = self.generate_random_uuid(obj_attr_list["captured_image_name"])
                
                obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs

                if "mgt_103_capture_request_completed" not in obj_attr_list :
                    obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs
                        
                _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
            return _status, _msg
        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list)

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    _instance.stop()
                elif _ts == "save" :
                    _instance.save()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.start()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.restore()
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

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
        return 0, "NOT SUPPORTED"

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
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list)            
            
            for _endpoint in self.lvirtconn :

                _storage_pool_handle = self.lvirtconn[_endpoint].storagePoolLookupByName(obj_attr_list["poolname"])

                _image_list = _storage_pool_handle.listVolumes()

                for _image in _image_list :
                    if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
    
                        if self.generate_random_uuid(_image) == self.generate_random_uuid(obj_attr_list["imageid1"]) :
                            _storage_pool_handle.storageVolLookupByName(_image).delete(0)
                            break
                    else :
                        if _image == obj_attr_list["imageid1"] :
                            _storage_pool_handle.storageVolLookupByName(_image).delete(0)
                            break

            _status = 0

        except libvirtError as msg :
            _status = 18127
            _fmsg = str(msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg
        
    def configure_port_mapping(self, obj_attr_list, operation) :
        '''
        TBD
        '''

        _status = 189
        _fmsg = "About to configure port mapping"

        # LXD does not provide an automated method to expose specific ports 
        # directly through the host's IP, like Docker does. For now, will
        # resort to ssh into the host and start a new "rinetd" instance each
        # time a new vmattach is issued.
        
        try :        
            _proc_man = ProcessManagement(username = "root", \
                                          hostname = obj_attr_list["host_cloud_ip"], \
                                          cloud_name = obj_attr_list["cloud_name"])

            if operation == "setup" :
                _cmd = "echo \"0.0.0.0 " + obj_attr_list["prov_cloud_port"] + ' '
                _cmd += obj_attr_list["cloud_ip"] + " 22\" > /tmp/" 
                _cmd += obj_attr_list["cloud_vm_name"] + ".rinetd.conf; rinetd -c "
                _cmd += "/tmp/" + obj_attr_list["cloud_vm_name"] + ".rinetd.conf"
                _rexcpt = True
            else:
                _cmd = "sudo pkill -9 -f 'rinetd -c /tmp/" + obj_attr_list["cloud_vm_name"] 
                _cmd += ".rinetd.conf" + "'; sudo rm -rf /tmp/" 
                _cmd += obj_attr_list["cloud_vm_name"] + ".rinetd.conf"
                _rexcpt = False
            
            _msg = operation.capitalize() + " port mapping (" + obj_attr_list["prov_cloud_port"] 
            _msg += " -> 22) for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
            _msg += "running on libvirt host \"" + obj_attr_list["host_name"] + "\""
            cbdebug(_msg, True)

            _status, _result_stdout, _fmsg = _proc_man.run_os_command(_cmd, raise_exception = _rexcpt)

            _status = 0

        except ProcessManagement.ProcessManagementException as obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while attempting to " + operation + " port mapping for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on LXD host \"" + obj_attr_list["host_name"] + "\""
                _msg += " in " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            
            else :
                _msg = "Successfully " + operation + " port mapping for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on LXD host \"" + obj_attr_list["host_name"] + "\""
                _msg += " in " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)

            return _status, _msg

    def generate_libvirt_vv_template(self, obj_attr_list, boot = False) :
        '''
        TBD
        '''
        
        _xml_file = ""
        _xml_file += "\t<volume>\n"
        
        if boot :
            obj_attr_list["cloud_vv_data_name"] = obj_attr_list["cloud_vv_name"]
            obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].replace("-vv","-vbv")
            if int(obj_attr_list["boot_volume_snapshot_size"]) > int(self.vhw_config[obj_attr_list["size"]]["vstorage"]) :
                _xml_file += "\t<capacity unit=\"M\">" + str(int(obj_attr_list["boot_volume_snapshot_size"])) + "</capacity>\n"
            else :
                _xml_file += "\t<capacity unit=\"M\">" + str(int(self.vhw_config[obj_attr_list["size"]]["vstorage"])) + "</capacity>\n"                
        else :
            obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_data_name"]
            _xml_file += "\t<capacity unit=\"G\">" + obj_attr_list["cloud_vv"] + "</capacity>\n"

        _vol_name = obj_attr_list["cloud_vv_name"]
            
        _xml_file += "\t<name>" + obj_attr_list["cloud_vv_name"] + "</name>\n"                    
        _xml_file += "\t<target>\n"
        _xml_file += "\t\t<permissions>\n"
        _xml_file += "\t\t\t<mode>0777</mode>\n"
        _xml_file += "\t\t</permissions>\n"
        _xml_file += "\t\t<path>" + obj_attr_list["pool_path"] + "</path>\n"

        if boot :
            _vol_format = "qcow2"
        else :
            _vol_format = "raw"

        obj_attr_list["cloud_vv_type"] = _vol_format

        _xml_file += "\t\t<format type='" + _vol_format  + "'/>\n"                
        _xml_file += "\t</target>\n"
        
        if boot :
            _backing_path = obj_attr_list["boot_volume_snapshot_path"]
            _backing_format = obj_attr_list["boot_volume_format"]
        else :
            _backing_path = "none"
            _backing_format = "none"
            
        if _backing_path != "none" :
            _xml_file += "\t<backingStore>\n"
            _xml_file += "\t\t<path>" + _backing_path + "</path>\n"
            _xml_file += "\t\t<format type='" + _backing_format + "'/>\n"
            _xml_file += "\t</backingStore>\n"
        _xml_file += "\t</volume>\n"

        _vol_path = obj_attr_list["pool_path"] + '/' + _vol_name

        obj_attr_list["volume_list"] += _vol_name + ':' + _vol_path + ':' + _vol_format + ':' + _backing_path + ':' + _backing_format + ','         

        return _xml_file

    @trace
    def generate_mac_addr(self, obj_attr_list) :
        '''
        This function is designed to pseudo-determinstically generate MAC addresses.
        
        The standard 6-byte MAC address is splitup as follows:
        
        | prefix (X bytes long) | selector byte | suffix (Y bytes long) |
        
        For example:
        1. The user sets an X-byte long 'mac_prefix' == '12:34'. This is used to 
           represent all experiments in a shared cluster controlled by PLMloud.
           For each shared cluster, this prefix should never need to change.
           This prefix is also used in the DHCP server configuration to ensure
           that requests from outside VMs are not answered to VMs that do not
           belong to this cluster. If there is more than one private DHCP server
           in the cluster, then, this mac_prefix should be changed, otherwise not.
        
        2. The selector byte is generated automatically to provide additional
           uniqueness and predictability in the MAC address to prevent
           collisions among users of the same shared cluster. It is a hash of 
           the username of the benchmark combined with the hostname of the VM 
           running the benchmark.
           
        3. The remaining Y-byte suffix is generated at provisioning time. This is done
           by having the datastore maintain a counter that represents the last used
           MAC address. An increasing counter ensures that collisions never happen
           but only requires a small amount of memory even when the number of Y
           bytes in the suffix is very large.
        '''

        # Form the 1st two parts of the MAC address 
        _mac_prefix = "52:54:00"
        bytes_needed = (17 - len(_mac_prefix)) / 3 - 1
        unique_mac_selector_key = obj_attr_list["cloud_vm_name"] + obj_attr_list["experiment_id"]
        selector_hd = sha256(unique_mac_selector_key.encode('utf-8')).hexdigest()
        selector_pos = randint(0,len(selector_hd)-2)
        selector_byte = selector_hd[selector_pos:selector_pos+2]
        mac = _mac_prefix  + ":" + selector_byte

        for x in range(0, int(bytes_needed)) :
            byte = ((int(obj_attr_list["counter"]) >> (8 * ((int(bytes_needed) - 1) - x))) & 0xff)
            mac += (":%02x" % (byte)) 

        obj_attr_list["cloud_vm_mac"] =  mac.replace('-', ':')       
        return True

    def generate_libvirt_vm_template(self, obj_attr_list) :
        '''
        TBD
        '''
        if obj_attr_list["hypervisor"] == "xen" :
            _xml_template = "<domain type='xen' "
        else :
            _xml_template = "<domain type='kvm' "

        _xml_template += ">\n"
        _xml_template += "\t<name>" + str(obj_attr_list["cloud_vm_name"]) + "</name>\n"
#        _xml_template += "\t<uuid>" + str(instance_attr_list["cloud_uuid"]) + "</uuid>\n"
        _xml_template += "\t<memory>" + str(int(self.vhw_config[obj_attr_list["size"]]["vmem"]) * 1024) + "</memory>\n"
        _xml_template += "\t<currentMemory>" + str(int(self.vhw_config[obj_attr_list["size"]]["vmem"]) * 1024) + "</currentMemory>\n"

        if obj_attr_list["arch"] == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
            _xml_template += "\t<vcpu placement='static'>" + str(int(self.vhw_config[obj_attr_list["size"]]["vcpus"])) + "</vcpu>\n"
            _xml_template += "\t<resource>\n"
            _xml_template += "\t\t<partition>/machine</partition>\n"
            _xml_template += "\t</resource>\n"
        else :
            _xml_template += "\t<vcpu>" + str(int(self.vhw_config[obj_attr_list["size"]]["vcpus"])) + "</vcpu>\n"

        _xml_template += "\t<os>\n"
        
        if obj_attr_list["hypervisor"] == "xen" :
            _xml_template += "\t\t<type arch='x86_64' machine='xenfv'>hvm</type>\n"
        else :
            if obj_attr_list["arch"] == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
                _xml_template += "\t\t<type arch='ppc64' machine='pseries'>hvm</type>\n"
            else :
                _xml_template += "\t\t<type arch='x86_64' machine='pc'>hvm</type>\n"

        if obj_attr_list["hypervisor"] == "xen" :
            _xml_template += "\t\t<loader>/usr/lib/xen/boot/hvmloader</loader>\n"
        
        _xml_template += "\t\t<boot dev='hd'/>\n"
        _xml_template += "\t</os>\n"
        _xml_template += "\t<features>\n"
        _xml_template += "\t\t<acpi/>\n"
        _xml_template += "\t\t<apic/>\n"
#        _xml_template += "\t\t<pae/>\n"
        _xml_template += "\t</features>\n"
        _xml_template += "\t<cpu mode='host-model'>\n"
        _xml_template += "\t<model fallback='allow'/>\n"
        _xml_template += "\t</cpu>\n"
        
        _xml_template += "\t<clock offset='utc'>\n"
        _xml_template += "\t\t<timer name='rtc' tickpolicy='catchup'/>\n"
        _xml_template += "\t\t<timer name='pit' tickpolicy='delay'/>\n"
        _xml_template += "\t\t<timer name='hpet' present='no'/>\n"
        _xml_template += "\t</clock>\n"        
        _xml_template += "\t<devices>\n"
        _xml_template += "\t\t<emulator>" + obj_attr_list["emulator"] + "</emulator>\n"

        _disk_number = 0
        for _volume in obj_attr_list["volume_list"].split(',') + [ "cloud-init" + ':' + obj_attr_list["host_remote_dir"] + obj_attr_list["cloud_vm_name"] + ".iso:" + "raw" + ':' + "none" + ':' + "none" ] :
            if _volume.count(':') == 4 :
                _vol_name, _vol_path, _vol_format, _backing_path, _backing_format = _volume.split(':')

                _xml_template += "\t\t<disk type='file' device='disk'>\n"
                _xml_template += "\t\t\t<driver name='qemu' type='" + _vol_format + "'/>\n"
                _xml_template += "\t\t\t<source file='" + _vol_path + "'/>\n"
                if _backing_path != "none" :
                    _xml_template += "\t\t\t<backingStore type='file'>\n"
                    _xml_template += "\t\t\t\t<source file='" + _backing_path + "'/>\n"
                    _xml_template += "\t\t\t\t<format type='" + _backing_format + "'/>\n"
                    _xml_template += "\t\t\t</backingStore>\n"
                    
                _xml_template += "\t\t\t<target dev='"
    
                if obj_attr_list["diskmode"] == "virtio" :
                    _xml_template += "v"
                elif obj_attr_list["diskmode"] == "ide" :
                    _xml_template += "h" 
                elif obj_attr_list["diskmode"] == "scsi" :
                    _xml_template += "s"
    
                _xml_template += "d" + chr(ord('a') + _disk_number) + "' bus='" + obj_attr_list["diskmode"] + "'/>\n"                 
                _xml_template += "\t\t</disk>\n"
                _disk_number += 1

        if obj_attr_list["arch"] == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
            _xml_template += "\t\t<controller type='usb' index='0'>\n"
            _xml_template += "\t\t\t<alias name='usb0'/>\n"
            _xml_template += "\t\t</controller>\n"
            _xml_template += "\t\t<controller type='pci' index='0' model='pci-root'>\n"
            _xml_template += "\t\t\t<alias name='pci.0'/>\n"
            _xml_template += "\t\t</controller>\n"
            _xml_template += "\t\t<controller type='scsi' index='0'>\n"
            _xml_template += "\t\t\t<alias name='scsi0'/>\n"
            _xml_template += "\t\t\t<address type='spapr-vio' reg='0x2000'/>\n"
            _xml_template += "\t\t</controller>\n"

        _xml_template += "\t\t<interface type='bridge'>\n"
        _xml_template += "\t\t\t<source bridge='" + obj_attr_list["network_bridge_name"] + "'/>\n"
        _xml_template += "\t\t\t<mac address='" + str(obj_attr_list["cloud_vm_mac"]) + "'/>\n"
        
        if obj_attr_list["netmode"] == "virtio" :
            _xml_template += "\t\t\t<model type='virtio'/>\n"

        _xml_template += "\t\t</interface>\n"

        for _vnic in obj_attr_list["extra_vnics"] :
            _xml_template += "\t\t<interface type='bridge'>\n"
            _xml_template += "\t\t\t<source bridge='" + _vnic[1] + "'/>\n"
#            _xml_template += "\t\t\t<mac address='" + str(obj_attr_list["cloud_vm_mac"]) + "'/>\n"
            
            if obj_attr_list["netmode"] == "virtio" :
                _xml_template += "\t\t\t<model type='virtio'/>\n"
    
            _xml_template += "\t\t</interface>\n"

        obj_attr_list["extra_vnics"] = str(obj_attr_list["extra_vnics"])

        if obj_attr_list["arch"]  == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
            _port = str(30000 + int(obj_attr_list["counter"]))
            
            _xml_template += "\t\t<serial type='tcp'>\n"
            _xml_template += "\t\t\t<source mode='bind' host='0.0.0.0' service='" + _port + "'/>\n"
            _xml_template += "\t\t\t<protocol type='telnet'/>\n"
            _xml_template += "\t\t\t<target port='0'/>\n"
            _xml_template += "\t\t\t<alias name='serial0'/>\n"
            _xml_template += "\t\t\t<address type='spapr-vio' reg='0x30000000'/>\n"
            _xml_template += "\t\t</serial>\n"
            _xml_template += "\t\t<console type='tcp'>\n"
            _xml_template += "\t\t\t<source mode='bind' host='0.0.0.0' service='" + _port + "'/>\n"
            _xml_template += "\t\t\t<protocol type='telnet'/>\n"
            _xml_template += "\t\t\t<target type='serial' port='0'/>\n"
            _xml_template += "\t\t\t<alias name='serial0'/>\n"
            _xml_template += "\t\t\t<address type='spapr-vio' reg='0x30000000'/>\n"
            _xml_template += "\t\t</console>\n"
        
        else :        
            _xml_template += "\t\t<serial type='pty'>\n"
            _xml_template += "\t\t\t<target port='0'/>\n"
            _xml_template += "\t\t</serial>\n"
            _xml_template += "\t\t<console type='pty'>\n"
            _xml_template += "\t\t\t<target port='0'/>\n"
            _xml_template += "\t\t</console>\n"
            _xml_template += "\t\t<input type='tablet' bus='usb'>\n"
            _xml_template += "\t\t\t<alias name='input0'/>\n"
            _xml_template += "\t\t</input>\n"
            _xml_template += "\t\t<input type='mouse' bus='ps2'/>\n"
            _xml_template += "\t\t<graphics type='vnc' port='-1' autoport='yes' listen='" + obj_attr_list["host_cloud_ip"] + "' keymap='en-us'/>\n"
            _xml_template += "\t\t<video>\n"
            if obj_attr_list["arch"]  == "x86_64" :
                _xml_template += "\t\t\t<model type='cirrus' vram='9216' heads='1'/>\n"
            else :
                _xml_template += "\t\t\t<model type='vga' vram='9216' heads='1'/>\n"
            _xml_template += "\t\t</video>\n"

        if obj_attr_list["hypervisor"] == "xen" :
            _xml_template += "\t\t<memballoon model='xen'/>\n"
        else :
            if obj_attr_list["arch"]  == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
                True
            else :
                _xml_template += "\t\t<memballoon model='virtio'/>\n"
        
        _xml_template += "\t</devices>\n"

        if obj_attr_list["arch"]  == "ppc64" or obj_attr_list["arch"] == "ppc64le" :
            _xml_template += "\t<seclabel type='none'/>\n"

        _xml_template += "</domain>\n"
    
        return _xml_template
