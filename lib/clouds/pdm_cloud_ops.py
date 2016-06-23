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

    PDM Cloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint, choice
from uuid import uuid5, NAMESPACE_DNS, UUID

import docker
from docker.errors import APIError

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.process_management import ProcessManagement
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

class PdmCmds(CommonCloudFunctions) :
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
        self.dockconn = {}
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Parallel Docker Manager."

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}, diag = False, generate_rc = False) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
                        
            for _endpoint in access.split(',') :
                _endpoint_ip = _endpoint.split('//')[1].split(':')[0]

                if _endpoint_ip not in self.dockconn :
                    self.dockconn[_endpoint_ip] = docker.Client(base_url=_endpoint)
                    self.dockconn[_endpoint_ip].ping()

            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "PDM connection to endpoint \"" + _endpoint_ip + "\" failed: " + _fmsg
                cberr(_msg)                    
                raise CldOpsException(_msg, _status)
            else :
                _msg = "PDM connection successful."
                cbdebug(_msg)
                return _status, _msg, ''
    
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True, True)

            _run_netname_found = True
            _prov_netname_found = True
            _key_pair_found = True
            
            _detected_imageids = self.check_images(vmc_name, vm_templates)
            
            if not (_run_netname_found and _prov_netname_found and \
                    _key_pair_found and len(_detected_imageids)) :
                _msg = "Check the previous errors, fix it (using OpenStack's web"
                _msg += " GUI (horizon) or nova CLI"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            _status = 0

        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = "VMC \"" + vmc_name + "\" did not pass the connection test."
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC \"" + vmc_name + "\" was successfully tested.\n"
                cbdebug(_msg, True)
                return _status, _msg

    def generate_random_uuid(self, name) :
        '''
        TBD
        '''
        _uuid = str(uuid5(UUID('6cb8e707-0fc5-5f55-88d4-d4fed43e64a8'), str(name))).upper()
        return _uuid

    def name_resolution(self, obj_attr_list, _object = "VMC") :
        '''
        TBD
        '''
        try :
            if _object == "VMC" :
                obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["cloud_hostname"])
            else :
                obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(obj_attr_list["host_cloud_ip"])
                obj_attr_list["host_name"] = obj_attr_list["host_name"].split('.')[0]             
        except :
            obj_attr_list["cloud_ip"] = "undefined_" + str(obj_attr_list["counter"])

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        for _endpoint in self.dockconn :
            _host_info = self.dockconn[_endpoint].info()
            _host_uuid = self.generate_random_uuid(_host_info["Name"])

            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
#            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = self.generate_random_ip_address()
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = _host_info["Name"]

            obj_attr_list["host_list"][_host_uuid]["name"] = "host_"  + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["cloud_vm_uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
            obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"
            obj_attr_list["host_list"][_host_uuid]["cores"] = _host_info["NCPU"]
            obj_attr_list["host_list"][_host_uuid]["memory"] = _host_info["MemTotal"]/(1024*1024)
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = _endpoint             
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

            _msg = "Removing all VMs previously created on VMC \""
            _msg += obj_attr_list["name"] + "\" (only VM names starting with"
            _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
            _msg += "\")....."
            cbdebug(_msg, True)
            _running_instances = True

            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False

                for _endpoint in self.dockconn :
                    _container_list = self.dockconn[_endpoint].containers(all=True)
                    for _container in _container_list :
                        for _name in _container["Names"] :
                            _name = _name[1:]
                            if _name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :

                                _running_instances = True
    
                                _msg = "Terminating instance: " 
                                _msg += _container["Id"] + " (" + str(_name) + ")"
                                cbdebug(_msg, True)
                                
                                if  _container["State"] == "running" :
                                    self.dockconn[_endpoint].kill(_container["Id"])
    
                                self.dockconn[_endpoint].remove_container(_container["Id"])
                            
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
                                       
            _msg = "Ok"
            _status = 0

        except APIError, obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""
                        
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on PDM Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    def check_images(self, vmc_name, vm_templates) :
        '''
        TBD
        '''

        for _endpoint in self.dockconn.keys() :

            _msg = " PDM Cloud status: Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC " + vmc_name + " (endpoint " + _endpoint + ")..."
            #cbdebug(_msg)
            print _msg,

            _registered_image_list = self.dockconn[_endpoint].images()
            _registered_imageid_list = []
    
            for _registered_image in _registered_image_list :
                _registered_imageid_list.append(_registered_image["RepoTags"][0])
    
            _required_imageid_list = {}
            
            for _vm_role in vm_templates.keys() :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid not in _required_imageid_list :
                    _required_imageid_list[_imageid] = []
                _required_imageid_list[_imageid].append(_vm_role)
    
            _msg = 'y'
    
            _detected_imageids = {}
            _undetected_imageids = {}
    
            for _imageid in _required_imageid_list.keys() :
    
                # Unfortunately we have to check image names one by one,
                # because they might be appended by a generic suffix for
                # image randomization (i.e., deploying the same image multiple
                # times as if it were different images.
                _image_detected = False
                for _registered_imageid in _registered_imageid_list :
                    if str(_registered_imageid).count(_imageid) :
                        _image_detected = True
                        _detected_imageids[_imageid] = "detected"
                    else :
                        _undetected_imageids[_imageid] = "undetected"
    
                if _image_detected :
                    True
    #                    _msg += "xImage id for VM roles \"" + ','.join(_required_imageid_list[_imageid]) + "\" is \""
    #                    _msg += _imageid + "\" and it is already registered.\n"
                else :
                    _msg += "zWARNING Image id for VM roles \""
                    _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                    _msg += _imageid + "\" is NOT registered "
                    _msg += "(attaching VMs with any of these roles will result in error).\n"
    
            if not len(_detected_imageids) :
                _msg = "ERROR! None of the image ids used by any VM \"role\" were detected"
                _msg += " in this VMC " + vmc_name + " (endpoint " + _endpoint + "). Please register at least one "
                _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
                cberr(_msg, True)
                return _detected_imageids
            else :
                _cmsg = "done"
                print _cmsg
                
                _msg = _msg.replace("yz",'')
                _msg = _msg.replace('z',"         ")
                _msg = _msg[:-2]
                if len(_msg) :
                    cbdebug(_msg, True)        

        return _detected_imageids

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
                         obj_attr_list["name"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]

            self.name_resolution(obj_attr_list)

            _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
            _fmsg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\"."

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

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on PDM Cloud \"" + obj_attr_list["cloud_name"]
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
                _msg += "on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on PDM Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", endpoints = "all", identifier = "all") :
        '''
        TBD
        '''

        _instances = []
        _fmsg = "Error while getting instances"

        if endpoints == "all" :
            _endpoints = self.dockconn.keys()
        else :
            _endpoints = [endpoints]
                      
        try :
            for _endpoint in _endpoints :            
                if obj_type == "vm" :
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].containers(all=True)
                                                                       
                    else :
                        _instances += self.dockconn[_endpoint].containers(filters = {"name" : identifier})
                else :
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].volumes(all=True)

     
                    else :
                        _instances += self.dockconn[_endpoint].volumes(filters = {"name" : identifier})
                        
            if len(_instances) == 1 :
                _instances = _instances[0]
                
            return _instances
        
        except Exception, _fmsg :
            return []

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''

        obj_attr_list["cloud_mac"] = "NA"
                        
        _networks = self.instance_info["NetworkSettings"]["Networks"].keys()
        
        if len(_networks) :
            
            if _networks.count(obj_attr_list["run_netname"]) :
                _msg = "Network \"" + obj_attr_list["run_netname"] + "\" found."
                cbdebug(_msg)
                _run_network = _networks[_networks.index(obj_attr_list["run_netname"])]
            else :
                _msg = "Network \"" + obj_attr_list["run_netname"] + "\" found."
                _msg += "Using the first network (\"" + _networks[0] + "\") instead)."
                cbdebug(_msg)
                _run_network = _networks[0]
            
            _address = self.instance_info["NetworkSettings"]["Networks"][_run_network]["IPAddress"]

            _mac = self.instance_info["NetworkSettings"]["Networks"][_run_network]["MacAddress"]

            if len(_address) :

                obj_attr_list["run_cloud_ip"] = _address

                if obj_attr_list["port_mapping"] :
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["host_cloud_ip"]
                else :
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["run_cloud_ip"]

                # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
                obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
                
                obj_attr_list["cloud_mac"] = _mac
                
                return True
            else :
                return False
        else :
            return False

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :

            if "host_ip" in obj_attr_list :
                _host_ip = obj_attr_list["host_cloud_ip"]
            else :
                _host_ip = "all"
                
            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _instance_state = _instance["State"]
            else :
                _instance_state = "non-existent"
            
            if _instance_state == "running" :
                self.instance_info = _instance
                return True
            else :
                return False
        
        except Exception, e :
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
        
    def select_host(self, obj_attr_list) :
        '''
        TBD
        '''
        obj_attr_list["host_cloud_ip"] = choice(self.dockconn.keys())
        self.name_resolution(obj_attr_list, "VM")
        return True
    
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_vm_uuid"] = "NA"
            
            if "cloud_vm_name" not in obj_attr_list :
                obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["cloud_name"]
                obj_attr_list["cloud_vm_name"] += '-' + "vm"
                obj_attr_list["cloud_vm_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]


                if obj_attr_list["ai"] != "none" :            
                    obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]

            obj_attr_list["cloud_mac"] = "NA"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            if obj_attr_list["ports_base"].lower() != "false" :
                obj_attr_list["port_mapping"] = int(obj_attr_list["ports_base"]) + int(obj_attr_list["name"].replace("vm_",''))
                _ports_mapping = [ (22, 'tcp') ]
                _port_bindings = { '22/tcp' : ('0.0.0.0', obj_attr_list["port_mapping"])}

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["port_mapping"])
                
            else :
                obj_attr_list["port_mapping"] = None
                _ports_mapping = None
                _port_bindings = None
                                                
            self.select_host(obj_attr_list)
            
            _time_mark_prs = int(time())            
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Starting an instance on PDM Cloud, using the imageid \"" 
            _msg +=  obj_attr_list["imageid1"] + " \"" + "and size \"" 
            _msg += obj_attr_list["size"] + "\" on VMC \"" 
            _msg += obj_attr_list["vmc_name"] + "\" (endpoint \"" + obj_attr_list["host_cloud_ip"] + "\")"
            cbdebug(_msg, True)

            _host_config = self.dockconn[obj_attr_list["host_cloud_ip"]].create_host_config(network_mode = obj_attr_list["netname"], \
                                                                                            port_bindings = _port_bindings)
            
            _instance = self.dockconn[obj_attr_list["host_cloud_ip"]].create_container(image = obj_attr_list["imageid1"], \
                                                                                 hostname = obj_attr_list["cloud_vm_name"], \
                                                                                 detach = True, \
                                                                                 name = obj_attr_list["cloud_vm_name"], \
                                                                                 ports = _ports_mapping, \
                                                                                 host_config = _host_config)
#                                                                                 command = "/sbin/my_init", \
#                                                                                 environment = {"PATH" : "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})

            obj_attr_list["cloud_vm_uuid"] = _instance["Id"]

            self.dockconn[obj_attr_list["host_cloud_ip"]].start(obj_attr_list["cloud_vm_uuid"])
                       
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                _status = 916

        except APIError, obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            print "A"
            _status = 23
            _fmsg = str(e)

        finally :
            if "lvt_cnt" in obj_attr_list :
                del obj_attr_list["lvt_cnt"]
                
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation was rolled back)"
                cberr(_msg, True)
                
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                self.vmdestroy(obj_attr_list)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["host_cloud_ip"], obj_attr_list["cloud_vm_name"])

            if len(_instance) :
                _msg = "Sending a termination request for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                                    
                if  _instance["State"] == "running" :

                    self.dockconn[obj_attr_list["host_cloud_ip"]].kill(obj_attr_list["cloud_vm_uuid"])

                self.dockconn[obj_attr_list["host_cloud_ip"]].remove_container(_instance["Id"])

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            _status = 0

        except APIError, obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

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
                _msg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on PDM Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, "all_vms_booted")

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on PDM Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0
            self.take_action_if_requested("AI", obj_attr_list, current_step)            

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on PDM Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on PDM Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

