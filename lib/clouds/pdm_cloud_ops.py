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

    PDM Cloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import choice, randint
from os.path import expanduser

import docker
import traceback
from docker.errors import APIError

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, is_number, DataOpsException
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

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
        self.additional_rc_contents = ''
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
            _endpoint_ip = "NA"            
            _fmsg = "An error has occurred, but no error message was captured"
                        
            for _endpoint in access.split(',') :

                _endpoint, _endpoint_name, _endpoint_ip= self.parse_endpoint(_endpoint, "tcp", "2375")
                
                if _endpoint_ip not in self.dockconn :
                    self.dockconn[_endpoint_ip] = docker.DockerClient(base_url = _endpoint, timeout = 180)

                _host_info = self.dockconn[_endpoint_ip].info()
                
                if not _host_info["SystemStatus"] :
                    True
                else :
                    _x = _endpoint.replace("tcp://",'').split(':')
                    self.swarm_ip = _x[0]
                    self.swarm_port = _x[1]

            if generate_rc :
                if self.swarm_ip :                       
                    self.additional_rc_contents = "export DOCKER_HOST = tcp://" + self.swarm_ip + ':' + self.swarm_port + "\n"
 
            _status = 0
            
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
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it (using Docker CLI)"
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

        for _endpoint in list(self.dockconn.keys()) :

            _msg = "Checking if the " + _net_str + " can be "
            _msg += "found on VMC " + vmc_name + " (endpoint " + _endpoint + ")..."
            cbdebug(_msg, True)

            for _network in self.dockconn[_endpoint].networks.list() :
                if _network.name == _prov_netname :
                    _prov_netname_found = True
                    
                if _network.name == _run_netname :
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
    def check_images(self, vmc_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''

        _map_name_to_id = {}
        _map_id_to_name = {}

        for _endpoint in list(self.dockconn.keys()) :

            self.common_messages("IMG", { "name": vmc_name, "endpoint" : _endpoint }, "checking", 0, '')

            _registered_image_list = self.dockconn[_endpoint].images.list()
            _registered_image_name_list = []

            # Don't pre-download images. Ask the docker server to tell us
            # if the image exists first. We will downloaded the first time the
            # instance passes through vmcreate() instead, just as we do for VMs.
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                search = vm_defaults["image_prefix"] + _imageid
                try :
                    # Remote docker pulls cannot operate with sha1 hashes. Stick to names only,
                    # and incorporate the remote prefix, in case one exists. This forces the use
                    # of a private or remote registry (such as the dockerhub). 
                    # Locally-only built images will no longer work.
                    data = self.dockconn[_endpoint].images.get_registry_data(search)
                    if search not in _registered_image_name_list :
                        _registered_image_name_list.append(search)
                    _map_name_to_id[_imageid] = search 
                except docker.errors.NotFound as e :
                    pass
                
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid != "to_replace" :
                    if _imageid in _map_name_to_id and _map_name_to_id[_imageid] != _imageid :
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    else :
                        _map_name_to_id[_imageid] = _imageid
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    _map_id_to_name[_map_name_to_id[_imageid]] = _imageid
            
            _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_image_name_list, _map_id_to_name, vm_defaults)

            # active_operations has code to prepend the prefix, even though we've already done it.
            # Undo that.
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid.count(vm_defaults["image_prefix"]) :
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _imageid.replace(vm_defaults["image_prefix"], ""))
            
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

        _access_list = ''
        for _endpoint in self.dockconn :
            _info = self.dockconn[_endpoint].info()
            if _info["SystemStatus"] :
                for _item in _info["SystemStatus"] :
                    if _item[1].count(':') == 1 :
                        _ip, _port = _item[1].split(':')
                        _hostname, _ip = hostname2ip(_item[0].strip(), True)
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
                obj_attr_list["host_list"][_host_uuid]["cores"] = _host_info["NCPU"]
                obj_attr_list["host_list"][_host_uuid]["memory"] = _host_info["MemTotal"]/(1024*1024)
                obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
                obj_attr_list["host_list"][_host_uuid]["simulated"] = False
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

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _running_instances = True

            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False

                for _endpoint in self.dockconn :
                    _container_list = self.dockconn[_endpoint].containers.list(all=True)
                    for _container in _container_list :
                        _name = _container.name
                        if _name[0] == "/" :
                            _name = _name[1:]
                        if _name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :

                            _running_instances = True

                            _msg = "Terminating instance: " 
                            _msg += _container.id + " (" + str(_name) + ")"
                            cbdebug(_msg, True)
                            
                            if  _container.status == "running" :
                                _container.kill()

                            _container.remove()
                            
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

            self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')

            for _endpoint in self.dockconn :
                _volume_list = self.dockconn[_endpoint].volumes.list()
                if _volume_list :
                    for _volume in _volume_list :
                        if _volume.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                            _volume.remove()

            _msg = "Ok"
            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""
                        
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
                         obj_attr_list["name"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]

            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["name"], False)

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid(obj_attr_list["name"])

            obj_attr_list["arrival"] = int(time())
            
            if str(obj_attr_list["discover_hosts"]).lower() == "true" :
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


                for _endpoint in self.dockconn :
                    _container_list = self.dockconn[_endpoint].containers.list(all=True)
                    for _container in _container_list :
                        _name = _container.name
                        if _name[0] == "/" :
                            _name = _name[1:]
                        if _name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
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
        _networks = list(obj_attr_list["instance_info"]["NetworkSettings"]["Networks"].keys())
                
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
            
            _address = obj_attr_list["instance_info"]["NetworkSettings"]["Networks"][_run_network]["IPAddress"]

            _mac = obj_attr_list["instance_info"]["NetworkSettings"]["Networks"][_run_network]["MacAddress"]

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
    def get_instances(self, obj_attr_list, obj_type = "vm", endpoints = "all", identifier = "all") :
        '''
        TBD
        '''

        _instances = []
        _fmsg = "Error while getting instances"
        _call = "NA"
        
        if endpoints == "all" :
            _endpoints = list(self.dockconn.keys())
        else :
            _endpoints = [endpoints]

        try :
            for _endpoint in _endpoints :
                if obj_type == "vm" :
                    _call = "containers()"
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].containers.list(all=True)
                        
                    else :
                        _instance_list = self.dockconn[_endpoint].containers.list(all=True, filters = {"name" : identifier})
                        for _instance in _instance_list :
                            _name = _instance.name
                            if _name[0] == "/" :
                                _name = _name[1:]
                            if identifier == _name :
                                _instances.append(_instance)
                        
                else :
                    _call = "volumes()"                    
                    if identifier == "all" :
                        _instances += self.dockconn[_endpoint].volumes.list()
     
                    else :
                        for _volume in self.dockconn[_endpoint].volumes.list() :
                            if _volume.name == identifier :
                                _instances += _volume
                        
            if len(_instances) == 1 :
                _instances = _instances[0]

            _status = 0
        
        except APIError as obj:
            _status = 18127
            _xfmsg = "API Error " + str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException as obj :
            _status = obj.status
            _xfmsg = "Cloud Exception " + str(obj.msg)

        except Exception as e :
            _status = 23
            _xfmsg = "Exception " + str(e)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            
        finally :
            
            if _status :
                _fmsg = "(While getting instance(s) through API call \"" + _call + "\") : " + _xfmsg
                
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

            _image_list = self.dockconn[obj_attr_list["host_cloud_ip"]].images.list()

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg +=  self.get_description()

            _candidate_images = []
            imagename = obj_attr_list["imageid1"]

            for _image in _image_list :                
                if self.is_cloud_image_uuid(imagename) :
                    if _image.id.split(':')[1] == imagename :
                        _candidate_images.append(_image)
                else :
                    if len(_image.tags) :
                        if _image.tags[0].count(imagename) :
                            _candidate_images.append(_image)   

            if not len(_candidate_images) :
                self.dockconn[obj_attr_list["host_cloud_ip"]].images.pull(imagename)

                _image_list = self.dockconn[obj_attr_list["host_cloud_ip"]].images.list()
                _candidate_images = []
    
                for _image in _image_list :
                    if self.is_cloud_image_uuid(imagename) :
                        if len(_image.tags) :
                            if _image.tags[0].count(imagename) :
                                _candidate_images.append(_image)
                    else :
                        if _image.id.split(':')[1] == imagename :
                            _candidate_images.append(_image)  

            if len(_candidate_images) :
                obj_attr_list["boot_volume_imageid1"] = _candidate_images[0].id
                obj_attr_list["imageid1"] = _candidate_images[0].tags[0]
                _status = 0
            else :
                _fmsg = "Unable to pull image \"" + imagename + "\""
                _fmsg += " to "  + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\"."
                _status = 1927
            
        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  imagename + ") not found: " + _fmsg
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

            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

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
        #if len(imageid) == 64 and is_number(imageid, True) :
        #    return True
        #return False 
        return True

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
                _instance_state = _instance.status
            else :
                _instance_state = "non-existent"

            if _instance_state == "running" :
                obj_attr_list["instance_info"] = _instance.attrs
                
                _instance_name = _instance.name
                if _instance_name[0] == "/" :
                    _instance_name = _instance_name[1:]
                _host_name = _instance_name.replace(obj_attr_list["cloud_vm_name"],'')
                _host_name = _host_name.replace('/','').strip()
                                
                if len(_host_name) :
                    obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(_host_name.strip(), True)                    
                            
                return True
            else :
                return False
        
        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace    
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

    @trace        
    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''
        if self.swarm_ip :
            obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(self.swarm_ip, True)            
        else :
            obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(choice(list(self.dockconn.keys())), True)

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
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

                obj_attr_list["last_known_state"] = "about to send volume create request"                                
                _mark_a = time()
                _vv = self.dockconn[obj_attr_list["host_cloud_ip"]].volumes.create(name=obj_attr_list["cloud_vv_name"], driver=obj_attr_list["cloud_vv_type"])
                self.annotate_time_breakdown(obj_attr_list, "create_volume_time", _mark_a)
                
                if obj_attr_list["cloud_vv_type"] == "local" :
                    obj_attr_list["cloud_vv_uuid"] = _vv["Mountpoint"]

                obj_attr_list["cloud_vv_mpt"] = _vv["Mountpoint"]

            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

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

                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])
                
                _instance = self.get_instances(obj_attr_list, \
                                               "vv", \
                                               obj_attr_list["host_cloud_ip"], \
                                               obj_attr_list["cloud_vv_name"])
                    
                if _instance :
                    self.common_messages("VV", obj_attr_list, "destroying", 0, '')
                    _instance.remove()
                                
            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

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
            
            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)
            
            if self.swarm_ip :
                obj_attr_list["host_swarm"] = self.swarm_ip
            else :
                obj_attr_list["host_swarm"] = "None"

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
                _port_bindings = { '22/tcp' : ('0.0.0.0', obj_attr_list["prov_cloud_port"])}

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])

                if str(obj_attr_list["extra_ports"]).lower() != "false" :
                    obj_attr_list["extra_ports"] = obj_attr_list["extra_ports"].replace('_',',')
                    _extra_port_list = obj_attr_list["extra_ports"].split(',')
                    for _extra_port in _extra_port_list :
                        _extra_mapped_port = int(obj_attr_list["extra_ports_base"]) + len(_extra_port_list) - 1 + int(obj_attr_list["name"].replace("vm_",'')) + _extra_port_list.index(_extra_port)
                        _port_bindings[ _extra_port + '/tcp'] = ('0.0.0.0', _extra_mapped_port)
            else :
                _port_bindings = None

            _devices = []
            if str(obj_attr_list["extra_devices"]).lower() != "false" :
                for _device in obj_attr_list["extra_devices"].split(',') :
                    _devices.append(_device) 

            _privileged = False
            if str(obj_attr_list["privileged"]).lower() != "false" :
                _privileged = True

            self.vm_placement(obj_attr_list)

            _cpu, _memory = obj_attr_list["size"].split('-')

            if "userdata" not in obj_attr_list :
                obj_attr_list["userdata"] = "auto"
                
            if obj_attr_list["userdata"] != "none" :
                obj_attr_list["config_drive"] = True
            else :
                obj_attr_list["config_drive"] = False
                        
            _time_mark_prs = int(time())            
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)

            self.vvcreate(obj_attr_list)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            _volumes = {} 
            
            if "cloud_vv" in obj_attr_list :
                if "data_dir" in obj_attr_list :
                    _mapped_dir = obj_attr_list["data_dir"]
                else :
                    _mapped_dir = "/mnt/cbvol1"
                _volumes = { _mapped_dir: { 'bind': obj_attr_list["cloud_vv_name"] + ':' + _mapped_dir, 'mode': "rw" } }

            self.pre_vmcreate_process(obj_attr_list)

            _mark_a = time()
            self.annotate_time_breakdown(obj_attr_list, "create_host_config_time", _mark_a)

            _mark_a = time()
            _instance = self.dockconn[obj_attr_list["host_cloud_ip"]].containers.create(image = obj_attr_list["imageid1"], \
                                                                                 hostname = obj_attr_list["cloud_vm_name"], \
                                                                                 detach = True, \
                                                                                 name = obj_attr_list["cloud_vm_name"], \
                                                                                 network_mode = obj_attr_list["netname"], \
                                                                                 mem_limit = str(_memory) + 'm', \
                                                                                 ports = _port_bindings, \
                                                                                 devices = _devices, \
                                                                                 privileged = _privileged, 
                                                                                 ulimits = [{"name": "nofile", "soft": 32768, "hard": 32768}], \
                                                                                 shm_size = obj_attr_list["shm_size"], \
                                                                                 volumes = _volumes, \
#                                                                                 command = "/sbin/my_init", \
                                                                                 environment = {"CB_SSH_PUB_KEY" : obj_attr_list["pubkey_contents"], "CB_LOGIN" : obj_attr_list["login"]})

            self.annotate_time_breakdown(obj_attr_list, "instance_creation_time", _mark_a)
                        
            obj_attr_list["cloud_vm_uuid"] = _instance.id

            _mark_a = time()
            _instance.start()
            self.annotate_time_breakdown(obj_attr_list, "instance_start_time", _mark_a)
                        
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
            
            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
            
            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                _status = 916

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

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
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        finally :

            if "instance_info" in obj_attr_list :
                del obj_attr_list["instance_info"]

            if "mgt_003_provisioning_request_completed" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_active_time", obj_attr_list["mgt_003_provisioning_request_completed"], False)
            
            if "mgt_004_network_acessible" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_reachable_time", obj_attr_list["mgt_004_network_acessible"], False)            
            
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
                         obj_attr_list["vmc_name"], obj_attr_list["name"])
            
            _wait = int(obj_attr_list["update_frequency"])
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0
            
            if str(obj_attr_list["host_swarm"]).lower() != "none" :
                self.swarm_ip = obj_attr_list["host_swarm"]

            if self.swarm_ip :
                _host_ip = self.swarm_ip
            else :
                _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if _instance :
                self.common_messages("VM", obj_attr_list, "destroying", 0, '')
                                    
                if isinstance(_instance, list) and len(_instance) == 1:
                    cbdebug("Instance is: " + str(_instance), True)
                    _instance = _instance[0]

                if  _instance.status == "running" :
                    _instance.kill()

                _instance.remove()

                while _instance and _curr_tries < _max_tries :
                    _instance = self.get_instances(obj_attr_list, "vm", _host_ip, \
                                           obj_attr_list["cloud_vm_name"])

                    sleep(_wait)
                    _curr_tries += 1

            if "cloud_vv" in obj_attr_list :
                self.vvdestroy(obj_attr_list)
                
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
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

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                self.dockconn[_host_ip].containers.commit(_instance.id, repository=obj_attr_list["captured_image_name"])

                sleep(_wait)

                obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs

                if "mgt_103_capture_request_completed" not in obj_attr_list :
                    obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs
                        
                _status = 0
            
        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

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
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            if str(obj_attr_list["host_swarm"]).lower() != "none" :
                self.swarm_ip = obj_attr_list["host_swarm"]

            if self.swarm_ip :
                _host_ip = self.swarm_ip
            else :
                _host_ip = obj_attr_list["host_cloud_ip"]

            _instance = self.get_instances(obj_attr_list, "vm", _host_ip, obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    _instance.pause()
                elif _ts == "save" :
                    _instance.stop()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.unpause()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.start()
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs
                        
            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

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

            for _endpoint in self.dockconn :
                _image_list = self.dockconn[_endpoint].images.list()

                for _image in _image_list :
                    imagename = obj_attr_list["imageid1"]
                    if self.is_cloud_image_uuid(imagename) :
                        if _image.id.split(':')[1] == imagename :
                            if len(_image.tags) :
                                obj_attr_list["imageid1"] = _image.tags[0]
                            obj_attr_list["boot_volume_imageid1"] = _image.id
                            self.dockconn[_endpoint].images.remove()
                            break
                    else :
                        if len(_image.tags) :                        
                            if _image.tags[0].count(imagename) :
                                obj_attr_list["boot_volume_imageid1"] = _image.id
                                self.dockconn[_endpoint].images.remove()
                                break
                        
            _status = 0

        except APIError as obj:
            _status = 18127
            _fmsg = str(obj.message) + " \"" + str(obj.explanation) + "\""

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg
