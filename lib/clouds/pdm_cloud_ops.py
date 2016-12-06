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
from random import choice, randint
from uuid import uuid5, UUID
from os.path import expanduser

import docker
from docker.errors import APIError

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
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
        self.swarm_ip = False
        self.api_error_counter = {}
        self.max_api_errors = 10
        
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Parallel Docker Manager Cloud"

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
                    self.dockconn[_endpoint_ip] = docker.Client(base_url = _endpoint, timeout = 180)
                _host_info = self.dockconn[_endpoint_ip].info()
                
                if not _host_info["SystemStatus"] :
                    True
                else :
                    _x = _endpoint.replace("tcp://",'').split(':')
                    self.swarm_ip = _x[0]
                    self.swarm_port = _x[1]

            _status = 0
            
        except Exception, e :
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
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True, True)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            _key_pair_found = True
            
            _detected_imageids = self.check_images(vmc_name, vm_templates)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it (using OpenStack's web"
                _msg += " GUI (horizon) or nova CLI"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            if len(_detected_imageids) :
                _status = 0               
            else :
                _status = 1

        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status > 1 :
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

        _access_list = ''
        for _endpoint in self.dockconn :
            _info = self.dockconn[_endpoint].info()
            if _info["SystemStatus"] :
                for _item in _info["SystemStatus"] :
                    if _item[1].count(':') == 1 :
                        _ip, _port = _item[1].split(':')
                        _hostname, _ip = hostname2ip(_item[0].strip())
                        _access_list += "tcp://" + _ip + ':' + _port + ','

        if len(_access_list) :
            _access_list = _access_list[0:-1]
    
            self.connect(_access_list, \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"])

        for _endpoint in self.dockconn :
            _host_info = self.dockconn[_endpoint].info()
            
            if not _host_info["SystemStatus"] :
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

                obj_attr_list["host_list"][_host_uuid]["hypervisor_type"] = "docker"
                                                    
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

            _msg = "Removing all VVs previously created on VMC \""
            _msg += obj_attr_list["name"] + "\" (only VV names starting with"
            _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
            _msg += "\")....."
            cbdebug(_msg, True)

            for _endpoint in self.dockconn :
                _volume_list = self.dockconn[_endpoint].volumes()["Volumes"]
                if _volume_list :
                    for _volume in _volume_list :
                        if _volume["Name"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                            self.dockconn[_endpoint].remove_volume(name=_volume["Name"])

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
                _msg += "on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    def check_images(self, vmc_name, vm_templates) :
        '''
        TBD
        '''

        for _endpoint in self.dockconn.keys() :

            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC \"" + vmc_name + "\" (endpoint " + _endpoint + ")..."
            cbdebug(_msg, True)
    
            _map_name_to_id = {}

            _registered_image_list = self.dockconn[_endpoint].images()
            _registered_imageid_list = []
                
            for _registered_image in _registered_image_list :                
                _registered_imageid_list.append(_registered_image["Id"].split(':')[1])                
                _map_name_to_id[_registered_image["RepoTags"][0].replace(":latest",'')] = _registered_image["Id"].split(':')[1]
                
            for _vm_role in vm_templates.keys() :            
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]                
                if _imageid != "to_replace" :
                    if _imageid in _map_name_to_id :                     
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    else :
                        _map_name_to_id[_imageid] = "aaaa0" + ''.join(["%s" % randint(0, 9) for num in range(0, 59)])
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])                        
    
            _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list)

            if not _detected_imageids :
                return _detected_imageids

        return _detected_imageids

    def check_networks(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        _prov_netname = vm_defaults["netname"]
        _run_netname = vm_defaults["netname"]

        _net_str = "network \"" + _prov_netname + "\""

        _prov_netname_found = False
        _run_netname_found = False

        for _endpoint in self.dockconn.keys() :

            _msg = "Checking if the " + _net_str + " can be "
            _msg += "found on VMC " + vmc_name + " (endpoint " + _endpoint + ")..."
            cbdebug(_msg, True)

            for _network in self.dockconn[_endpoint].networks() :
                if _network["Name"] == _prov_netname :
                    _prov_netname_found = True
                    
                if _network["Name"] == _run_netname :
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
            _fmsg += " on "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid(obj_attr_list["name"])

            obj_attr_list["arrival"] = int(time())
            
            if obj_attr_list["discover_hosts"].lower() == "true" :
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            if self.swarm_ip :
#                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
#                                                  "GLOBAL", \
#                                                  "ai_defaults", \
#                                                  False, \
#                                                  "host_swarm", \
#                                                  self.swarm_ip)

                if "cloud_name" in obj_attr_list :
                    _file = expanduser("~") + "/cbrc-" + obj_attr_list["cloud_name"].lower()
                else :
                    _file = expanduser("~") + "/cbrc"
                    
                _file_fd = open(_file, 'w')
                _file_fd.write("export DOCKER_HOST=tcp://" + self.swarm_ip + ':' + self.swarm_port + "\n")

                if "cloud_name" in obj_attr_list :                        
                    _file_fd.write("export CB_CLOUD_NAME=" + obj_attr_list["cloud_name"] + "\n")
                    _file_fd.write("export CB_USERNAME=" + obj_attr_list["username"] + "\n")
                    
                _file_fd.close()
            
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
                _msg += "on "  + self.get_description() + " Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on "  + self.get_description() + " Cloud \"" + obj_attr_list["cloud_name"]
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
                _msg += "on "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
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
        _call = "NA"
        
        if endpoints == "all" :
            _endpoints = self.dockconn.keys()
        else :
            _endpoints = [endpoints]
                      
        try :
            for _endpoint in _endpoints :            
                if obj_type == "vm" :
                    _call = "containers()"
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].containers(all=True)
                                                                       
                    else :
                        _instances += self.dockconn[_endpoint].containers(filters = {"name" : identifier})
                else :
                    _call = "volumes()"                    
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].volumes()
     
                    else :
                        for _volume in self.dockconn[_endpoint].volumes()["Volumes"] :
                            if _volume["Name"] == identifier :
                                _instances += _volume
                        
            if len(_instances) == 1 :
                _instances = _instances[0]

            _status = 0
        
        except APIError, obj:
            _status = 18127
            _xfmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException, obj :
            _status = obj.status
            _xfmsg = str(obj.msg)

        except Exception, e :
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

                if str(obj_attr_list["ports_base"]).lower() != "false" :
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
            if "host_cloud_ip" in obj_attr_list :
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
                
                _instance_name = _instance["Names"][0][1:]
                _host_name = _instance_name.replace(obj_attr_list["cloud_vm_name"],'')
                _host_name = _host_name.replace('/','').strip()
                                
                if len(_host_name) :
                    obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(_host_name.strip())
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
        if self.swarm_ip :
            obj_attr_list["host_cloud_ip"] = self.swarm_ip
        else :
            obj_attr_list["host_cloud_ip"] = choice(self.dockconn.keys())
            
        self.name_resolution(obj_attr_list, "VM")
        return True

    @trace        
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"


            if "cloud_vv" in obj_attr_list :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])

                obj_attr_list["last_known_state"] = "about to send volume create request"
    
                obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["cloud_name"]
                obj_attr_list["cloud_vv_name"] += '-' + "vv"
                obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]  


                if "cloud_vv_type" in obj_attr_list :
                    _volume_type = obj_attr_list["cloud_vv_type"]
                else :
                    _volume_type = "local"

                _msg = "Creating a " + _volume_type + " volume, with size " 
                _msg += obj_attr_list["cloud_vv"] + ", on VMC \"" 
                _msg += obj_attr_list["vmc_name"] + "\""
                cbdebug(_msg, True)
                
                _mark1 = int(time())
                _vv = self.dockconn[obj_attr_list["host_cloud_ip"]].create_volume(name=obj_attr_list["cloud_vv_name"], driver=_volume_type)
                _mark2 = int(time())

                obj_attr_list["pdm_002_create_volume_time"] = _mark2 - _mark1
                
                if _volume_type == "local" :
                    obj_attr_list["cloud_vv_uuid"] = _vv["Mountpoint"]

                obj_attr_list["cloud_vv_mpt"] = _vv["Mountpoint"]

            else :
                obj_attr_list["cloud_vv_uuid"] = "none"

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
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            else :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vvdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"


            if "cloud_vv_uuid" in obj_attr_list and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :

                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])
                
                _instance = self.get_instances(obj_attr_list, \
                                               "vv", \
                                               obj_attr_list["host_cloud_ip"], \
                                               obj_attr_list["cloud_vv_name"])
                    
                if _instance :
    
                    _msg = "Sending a destruction request for the Volume" 
                    _msg += " previously attached to \"" 
                    _msg += obj_attr_list["name"] + "\""
                    _msg += " (cloud-assigned uuid " 
                    _msg += obj_attr_list["cloud_vv_uuid"] + ")...."
                    cbdebug(_msg, True)
    
                self.dockconn[obj_attr_list["host_cloud_ip"]].remove_volume(name=obj_attr_list["cloud_vv_name"])
                                
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
                _msg += " on " +  self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on "  + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = self.dockconn[obj_attr_list["host_cloud_ip"]].images()

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg +=  self.get_description()

            _imageid = False

            _candidate_images = []

            for _image in _image_list :
                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :                 
                    if _image["RepoTags"][0].count(obj_attr_list["imageid1"]) :
                        _candidate_images.append(obj_attr_list["imageid1"])
                else :
                    if _image["Id"].split(':')[1] == obj_attr_list["imageid1"] :
                        _candidate_images.append(obj_attr_list["imageid1"])                        

            if not len(_candidate_images) :
                self.dockconn[obj_attr_list["host_cloud_ip"]].pull(obj_attr_list["imageid1"])

                _image_list = self.dockconn[obj_attr_list["host_cloud_ip"]].images()
                _candidate_images = []
    
                for _image in _image_list :
                    if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :                 
                        if _image["RepoTags"][0].count(obj_attr_list["imageid1"]) :
                            _candidate_images.append(obj_attr_list["imageid1"])
                    else :
                        if _image["Id"].split(':')[1] == obj_attr_list["imageid1"] :
                            _candidate_images.append(obj_attr_list["imageid1"])                        

            if len(_candidate_images) :                   
                _status = 0
            else :
                _fmsg = "Unable to pull image \"" + obj_attr_list["imageid1"] + "\""
                _fmsg += " to "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."
                _status = 1927
            
        except APIError, obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ") not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
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
            
            if self.swarm_ip :
                obj_attr_list["host_swarm"] = self.swarm_ip
            else :
                obj_attr_list["host_swarm"] = "None"

            if len(obj_attr_list["pubkey_contents"]) == 1 :
                _fh = open(obj_attr_list["identity"] + '.pub', 'r')
                _pub_key = _fh.read()
                _fh.close()
                obj_attr_list["pubkey_contents"] = _pub_key.replace("ssh-rsa ",'')
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                  "GLOBAL", \
                                                  "vm_defaults", \
                                                  False, \
                                                  "pubkey_contents", \
                                                  obj_attr_list["pubkey_contents"])

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            if str(obj_attr_list["ports_base"]).lower() != "false" :
                obj_attr_list["prov_cloud_port"] = int(obj_attr_list["ports_base"]) + int(obj_attr_list["name"].replace("vm_",''))
                _ports_mapping = [ (22, 'tcp') ]
                _port_bindings = { '22/tcp' : ('0.0.0.0', obj_attr_list["prov_cloud_port"])}

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])
                
            else :
                _ports_mapping = None
                _port_bindings = None
                                                
            self.select_host(obj_attr_list)

            _cpu, _memory = obj_attr_list["size"].split('-')
                        
            _time_mark_prs = int(time())            
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vvcreate(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            self.get_images(obj_attr_list)
            
            _msg = "Starting an instance on " + self.get_description() + ", using the imageid \"" 
            _msg +=  obj_attr_list["imageid1"] + " \"" + "and size \"" 
            _msg += obj_attr_list["size"] + "\", connected to the network \"" 
            _msg += obj_attr_list["netname"] + "\", on VMC \"" 
            _msg += obj_attr_list["vmc_name"] + "\" (endpoint \"" + obj_attr_list["host_cloud_ip"] + "\")"
            cbdebug(_msg, True)

            _volumes = []
            _binds = []
            
            if "cloud_vv_name" in obj_attr_list :
                _binds = [ obj_attr_list["cloud_vv_name"] + ":/mnt/cbvol1:rw"]                
                _volumes = [ "/mnt/cbvol1" ]

            _mark1 = int(time())
            _host_config = self.dockconn[obj_attr_list["host_cloud_ip"]].create_host_config(network_mode = obj_attr_list["netname"], \
                                                                                            port_bindings = _port_bindings, 
                                                                                            binds = _binds, \
                                                                                            mem_limit = str(_memory) + 'm')
                
            _mark2 = int(time())
            obj_attr_list["pdm_003_create_host_config_time"] = _mark2 - _mark1
                        
            _instance = self.dockconn[obj_attr_list["host_cloud_ip"]].create_container(image = obj_attr_list["imageid1"], \
                                                                                 hostname = obj_attr_list["cloud_vm_name"], \
                                                                                 detach = True, \
                                                                                 name = obj_attr_list["cloud_vm_name"], \
                                                                                 ports = _ports_mapping, \
                                                                                 volumes = _volumes, \
                                                                                 host_config = _host_config, \
#                                                                                 command = "/sbin/my_init", \
                                                                                 environment = {"CB_SSH_PUB_KEY" : obj_attr_list["pubkey_contents"], "CB_LOGIN" : obj_attr_list["login"]})

            _mark3 = int(time())
            
            obj_attr_list["pdm_004_create_docker_time"] = _mark3 - _mark2
                        
            obj_attr_list["cloud_vm_uuid"] = _instance["Id"]

            self.dockconn[obj_attr_list["host_cloud_ip"]].start(obj_attr_list["cloud_vm_uuid"])
            
            _mark4 = int(time())
            
            obj_attr_list["pdm_005_start_docker_time"] = _mark4 - _mark3
                        
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            obj_attr_list["pdm_006_instance_creation_time"] = obj_attr_list["mgt_003_provisioning_request_completed"]

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            obj_attr_list["pdm_007_instance_reachable"] = obj_attr_list["mgt_004_network_acessible"]
            
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
            _status = 23
            _fmsg = str(e)

        finally :
                
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg

                if str(obj_attr_list["leave_instance_on_failure"]).lower() == "true" :
                    _msg += " (Will leave the VM running due to experimenter's request)"
                    cberr(_msg, True)
                else :
                    _msg += " (The VM creation will be rolled back)"
                    cberr(_msg, True)                    
                    obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                    self.vmdestroy(obj_attr_list)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."
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

            if str(obj_attr_list["host_swarm"]).lower() != "none" :
                self.swarm_ip = obj_attr_list["host_swarm"]

            if self.swarm_ip :
                _host_ip = self.swarm_ip
            else :
                _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if len(_instance) :
                _msg = "Sending a termination request for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
                                    
                if  _instance["State"] == "running" :                    
                    self.dockconn[_host_ip].kill(obj_attr_list["cloud_vm_uuid"])

                self.dockconn[_host_ip].remove_container(_instance["Id"])

            if "cloud_vv" in obj_attr_list :
                self.vvdestroy(obj_attr_list)
                
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
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            if str(obj_attr_list["host_swarm"]).lower() != "none" :
                self.swarm_ip = obj_attr_list["host_swarm"]

            if self.swarm_ip :
                _host_ip = self.swarm_ip
            else :
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

                _msg = obj_attr_list["name"] + " capture request sent."
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                self.dockconn[_host_ip].commit(_instance["Id"], repository=obj_attr_list["captured_image_name"])

                sleep(_wait)

                obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs

                if "mgt_103_capture_request_completed" not in obj_attr_list :
                    obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs
                        
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
                _msg += "could not be captured "
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
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
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            if str(obj_attr_list["host_swarm"]).lower() != "none" :
                self.swarm_ip = obj_attr_list["host_swarm"]

            if self.swarm_ip :
                _host_ip = self.swarm_ip
            else :
                _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    self.dockconn[_host_ip].pause(obj_attr_list["cloud_vm_uuid"])
                elif _ts == "save" :
                    self.dockconn[_host_ip].stop(obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    self.dockconn[_host_ip].unpause(obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    self.dockconn[_host_ip].start(obj_attr_list["cloud_vm_uuid"])
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
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
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on " + self.get_description()
                _msg += " \"" + obj_attr_list["cloud_name"] + "\" :" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on " + self.get_description()
                _msg += " \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg, True)
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

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
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
                _msg += " on "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

