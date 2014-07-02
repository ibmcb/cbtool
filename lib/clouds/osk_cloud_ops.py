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
    Created on Fev 3, 2012

    OpenStack Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from uuid import uuid5, UUID
from random import choice
import socket

from novaclient.v1_1 import client
from novaclient import exceptions as novaexceptions

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, value_suffix
from lib.remote.network_functions import hostname2ip
from lib.remote.process_management import ProcessManagement
from shared_functions import CldOpsException, CommonCloudFunctions 

class OskCmds(CommonCloudFunctions) :
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
        self.oskconncompute = False
        self.oskconnstorage = False
        self.expid = expid
        self.ft_supported = False
        self.lvirt_conn = {}
    
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack Compute Cloud"

    @trace
    def connect(self, access_url, authentication_data, region) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _username, _password, _tenant = authentication_data.split('-')
            _username = _username.replace("_dash_",'-')
            _password = _password.replace("_dash_",'-')
            _tenant = _tenant.replace("_dash_",'-')

            self.oskconncompute = client.Client(_username, _password, _tenant, \
                                         access_url, region_name=region, \
                                         service_type="compute")
            self.oskconncompute.flavors.list()

            self.oskconnstorage = client.Client(_username, _password, _tenant, \
                                         access_url, region_name=region, \
                                         service_type="volume")

            self.oskconnstorage.volumes.list()


            _region = region
            _msg = "Selected region is " + str(region)
            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "OpenStack connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "OpenStack connection successful."
                cbdebug(_msg)
                return _status, _msg, _region

    @trace
    def disconnect(self) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if self.oskconncompute :
                self.oskconncompute.client.http.close()


            if self.oskconnstorage :
                self.oskconnstorage.client.http.close()

            _status = 0

        except novaexceptions, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except AttributeError :
            # If the "close" method does not exist, proceed normally.
            _msg = "The \"close\" method does not exist or is not callable" 
            cbwarn(_msg)
            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "OpenStack disconnection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "OpenStack disconnection successful."
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
            self.connect(access, credentials, vmc_name)

            if not key_name :
                _key_pair_found = True
            else :
                _msg = "Checking if the ssh key pair \"" + key_name + "\" is created"
                _msg += " on VMC " + vmc_name + "...."
                cbdebug(_msg, True)
                
                _key_pair_found = False
                for _key_pair in self.oskconncompute.keypairs.list() :
                    if _key_pair.name == key_name :
                        _key_pair_found = True

                if not _key_pair_found :
                    _msg = "Creating the ssh key pair \"" + key_name + "\""
                    _msg += " on VMC " + vmc_name + "...."
                    cbdebug(_msg, True)
                    self.oskconncompute.keypairs.create(key_name)
                    _key_pair_found = True

            if security_group_name :

                _msg = "Checking if the security group \"" + security_group_name
                _msg += "\" is created on VMC " + vmc_name + "...."
                cbdebug(_msg, True)

                _security_group_found = False
                for security_group in self.oskconncompute.security_groups.list() :
                    if security_group.name == security_group_name :
                        _security_group_found = True
    
                if not _security_group_found :
                    _msg = "ERROR! Please create the security group \"" 
                    _msg += security_group_name + "\" in "
                    _msg += "OpenStack before proceeding."
                    _fmsg = _msg 
                    cberr(_msg, True)
            else :
                _security_group_found = True

            if vm_defaults["floating_ip"] :

                _floating_pool_list = self.oskconncompute.floating_ip_pools.list()

                if len(_floating_pool_list) == 1 :
                    vm_defaults["floating_pool"] = _floating_pool_list[0].name
                    
                    _msg = "A single floating IP pool (\"" 
                    _msg += vm_defaults["floating_pool"] + "\") was found on this"
                    _msg += " VMC. Will use this as the floating pool."
                    cbdebug(_msg, True)

                _msg = "Checking if the floating pool \""
                _msg += vm_defaults["floating_pool"] + "\" can be found on VMC "
                _msg += vmc_name + "..."
                cbdebug(_msg, True)
                
                _floating_pool_found = False

                for _floating_pool in _floating_pool_list :
                    if _floating_pool.name == vm_defaults["floating_pool"] :
                        _floating_pool_found = True
                                
                if not (_floating_pool_found) :
                    _msg = "ERROR! Please make sure that the floating IP pool "
                    _msg += vm_defaults["floating_pool"] + "\" can be found"
                    _msg += " VMC " + vmc_name
                    _fmsg = _msg 
                    cberr(_msg, True)

            if vm_defaults["prov_netname"] == vm_defaults["run_netname"] :
                _net_str = "network \"" + vm_defaults["prov_netname"] + "\""
            else :
                _net_str = "networks \"" + vm_defaults["prov_netname"] + "\""
                _net_str += " and " + "\"" + vm_defaults["run_netname"] + "\""

            _msg = "Checking if the " + _net_str + " can be found on VMC " + vmc_name + "..."
            cbdebug(_msg, True)
            _prov_netname_found = False
            _run_netname_found = False

            for _network in self.oskconncompute.networks.list() :
                if _network.label == vm_defaults["prov_netname"] :
                    _prov_netname_found = True
                
                if _network.label == vm_defaults["run_netname"] :
                    _run_netname_found = True
                
                # Sometimes clouds have hundreds or thousands of networks
                # just leave the loop early, if possible.    
                if _run_netname_found and _prov_netname_found :
                    break
                
            if not (_run_netname_found and _prov_netname_found) :
                _msg = "ERROR! Please make sure that the " + _net_str + " can be found"
                _msg += " VMC " + vmc_name
                _fmsg = _msg 
                cberr(_msg, True)

            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _registered_image_list = self.oskconncompute.images.list()
            _registered_imageid_list = []

            for _registered_image in _registered_image_list :
                _registered_imageid_list.append(_registered_image.name)

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
                    _msg += "xWARNING Image id for VM roles \""
                    _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                    _msg += _imageid + "\" is NOT registered "
                    _msg += "(attaching VMs with any of these roles will result in error).\n"

            if not len(_detected_imageids) :
                _msg = "ERROR! None of the image ids used by any VM \"role\" were detected"
                _msg += " in this OpenStack cloud. Please register at least one "
                _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
                cberr(_msg, True)
            else :
                _msg = _msg.replace("yx",'')
                _msg = _msg.replace('x',"         ")
                _msg = _msg[:-2]
                if len(_msg) :
                    cbdebug(_msg, True)

            if not (_run_netname_found and _prov_netname_found and \
                    _key_pair_found and _security_group_found and len(_detected_imageids)) :
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
            self.disconnect()
            if _status :
                _msg = "VMC \"" + vmc_name + "\" did not pass the connection test."
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC \"" + vmc_name + "\" was successfully tested."
                cbdebug(_msg, True)
                return _status, _msg

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])
                
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            _host_list = self.oskconncompute.hypervisors.list()

            obj_attr_list["host_count"] = len(_host_list)

            _service_ids_found = {}
            for _host in _host_list :

                # Sometimes, the same hypervisor is reported more than once,
                # with slightly different names. We need to remove (in fact,
                # avoid the insertion of) duplicates.
                if not _host.service["id"] in _service_ids_found :
                    # Host UUID is artificially generated
                    _host_uuid = str(uuid5(UUID('4f3f2898-69e3-5a0d-820a-c4e87987dbce'), \
                                           obj_attr_list["cloud_name"] + str(_host.service["id"])))
                    obj_attr_list["host_list"][_host_uuid] = {}
                    obj_attr_list["hosts"] += _host_uuid + ','
                    
                    _extended_info = _host._info
                    
                    if "service" in _extended_info :
                        if "host" in _extended_info["service"] :
                            _actual_host_name = _extended_info["service"]["host"]
                    else :
                        _actual_host_name = _host.hypervisor_hostname
                        
                    if "modify_host_names" in obj_attr_list and \
                    obj_attr_list["modify_host_names"].lower() != "false" :
                        _queried_host_name = _actual_host_name.split(".")[0] + '.' + obj_attr_list["modify_host_names"]
                    else :
                        _queried_host_name = _actual_host_name

                    obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], \
                    obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_queried_host_name)

                    obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = \
                    _actual_host_name

                    if obj_attr_list["host_list"][_host_uuid]["cloud_ip"] == obj_attr_list["cloud_ip"] :
                        obj_attr_list["host_list"][_host_uuid]["function"] = "controller"
                    else :
                        obj_attr_list["host_list"][_host_uuid]["function"] = "compute"
                    obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                    obj_attr_list["host_list"][_host_uuid]["memory_size"] = _host.memory_mb
                    obj_attr_list["host_list"][_host_uuid]["cores"] = _host.vcpus
                    obj_attr_list["host_list"][_host_uuid]["hypervisor_type"] = _host.hypervisor_type                    
                    obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
                    obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                    obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
                    obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
                    obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
                    obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
                    obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
                    obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
                    obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
                    obj_attr_list["host_list"][_host_uuid]["simulated"] = "False"
                    obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]
                    if "login" in obj_attr_list :
                        obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["login"]
                    else :
                        obj_attr_list["host_list"][_host_uuid]["login"] = "root"                
                    obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
                    obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
                    _time_mark_prc = int(time())
                    obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start
                    _service_ids_found[ _host.service["id"]] = "1"

            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

            self.additional_host_discovery (obj_attr_list)
            self.populate_interface(obj_attr_list)
            
            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except socket.gaierror, e :
            _status = 453
            _fmsg = "While discovering hosts, CB needs to resolve one of the "
            _fmsg += "OpenStack host names: " + _queried_host_name + ". "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."
                    
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            if _status :
                _msg = "HOSTS belonging to VMC " + obj_attr_list["name"] + " could not be "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = str(obj_attr_list["host_count"]) + "HOSTS belonging to "
                _msg += "VMC " + obj_attr_list["name"] + " were successfully "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

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
                _instances = self.oskconncompute.servers.list()
                for _instance in _instances :
                    if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _running_instances = True
                        if  _instance.status == "ACTIVE" :
                            _msg = "Terminating instance: " 
                            _msg += _instance.id + " (" + _instance.name + ")"
                            cbdebug(_msg, True)
                            _instance.delete()

                        if _instance.status == "BUILD" :
                            _msg = "Will wait for instance "
                            _msg += _instance.id + "\"" 
                            _msg += " (" + _instance.name + ") to "
                            _msg += "start and then destroy it."
                            cbdebug(_msg, True)
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
            _volumes = self.oskconnstorage.volumes.list()
            for _volume in _volumes :
                if _volume.display_name :
                    if _volume.display_name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _volume.delete()

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\""
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

            if not _status :
                _x, _y, _hostname = self.connect(obj_attr_list["access"], \
                                                 obj_attr_list["credentials"], \
                                                 obj_attr_list["name"])
    
                obj_attr_list["cloud_hostname"] = _hostname
                _resolve = obj_attr_list["access"].split(':')[1].replace('//','')
                _x, obj_attr_list["cloud_ip"] = hostname2ip(_resolve)
                obj_attr_list["arrival"] = int(time())
    
                if obj_attr_list["discover_hosts"].lower() == "true" :                   
                    _msg = "Discovering hosts on VMC \"" + obj_attr_list["name"] + "\"....."
                    cbdebug(_msg, True)
                    _status, _fmsg = self.discover_hosts(obj_attr_list, _time_mark_prs)
                else :
                    obj_attr_list["hosts"] = ''
                    obj_attr_list["host_list"] = {}
                    obj_attr_list["host_count"] = "NA"
                    
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except socket.herror:
            _status = 1200
            _fmsg = "The IP address \"" + _resolve + "\" - used by the OpenSTack"
            _fmsg += " Controller - is not mapped to a Hostname. "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."

        except socket.gaierror:
            _status = 1200
            _fmsg = "The Hostname \"" + _resolve + "\" - used by the OpenSTack"
            _fmsg += " Controller - is not mapped to an IP. "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."
                        
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def get_flavors(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _flavor_list = self.oskconncompute.flavors.list()

            _status = 168
            _fmsg = "Please check if the defined flavor is present on this "
            _fmsg += "OpenStack Cloud"

            _flavor = False
            for _idx in range(0,len(_flavor_list)) :
                if _flavor_list[_idx].name.count(obj_attr_list["size"]) :
                    _flavor = _flavor_list[_idx]
                    _status = 0
                    break

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Flavor (" +  obj_attr_list["size"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _flavor

    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = self.oskconncompute.images.list()

            _fmsg += "Please check if the defined image name is present on this "
            _fmsg += "OpenStack Cloud"

            _imageid = False

            _candidate_images = []

            for _idx in range(0,len(_image_list)) :
                if obj_attr_list["randomize_image_name"].lower() == "false" and \
                _image_list[_idx].name == obj_attr_list["imageid1"] :
                    _imageid = _image_list[_idx]
                    break
                elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                _image_list[_idx].name.count(obj_attr_list["imageid1"]) :
                    _candidate_images.append(_image_list[_idx])
                else :                     
                    True

            if  obj_attr_list["randomize_image_name"].lower() == "true" :
                _imageid = choice(_candidate_images)

            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _imageid

    def get_networks(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _network_list = self.oskconncompute.networks.list()

            _status = 168
            _fmsg = "Please check if the defined network is present on this "
            _fmsg += "OpenStack Cloud"

            _networkid = False
            for _idx in range(0,len(_network_list)) :
                if _network_list[_idx].label.count(obj_attr_list["prov_netname"]) :
                    _networkid = _network_list[_idx]
                    _status = 0
                    break

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Network (" +  obj_attr_list["prov_netname"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _networkid
                            
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

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on OpenStack \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on OpenStack \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        
        _networks = instance.addresses.keys()

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

            _address_list = instance.addresses[_run_network]

            if len(_address_list) :
                
                for _address in _address_list :
                    cbdebug(_address["OS-EXT-IPS:type"])

                    if _address["OS-EXT-IPS:type"] == obj_attr_list["address_type"] :
                        obj_attr_list["cloud_ip"] = '{0}'.format(_address["addr"])
                        break
                        

                if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                    obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
                elif obj_attr_list["hostname_key"] == "cloud_ip" :
                    obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')

                if obj_attr_list["prov_netname"] == obj_attr_list["run_netname"] :
                    if obj_attr_list["cloud_ip"] != "undefined" :
                        obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]
                        return True
                    else :
                        return False
                else :
                    if _networks.count(obj_attr_list["prov_netname"]) :
                        _msg = "Network \"" + obj_attr_list["prov_netname"] + "\" found."
                        cbdebug(_msg)
                        _prov_network = _networks[_networks.index(obj_attr_list["prov_netname"])]
                    else :
                        _msg = "Network \"" + obj_attr_list["prov_netname"] + "\" found."
                        _msg += "Using the first network (\"" + _networks[0] + "\") instead)."
                        cbdebug(_msg)
                        _prov_network = _networks[0]

                    _address_list = instance.addresses[_prov_network]
        
                    if len(_address_list) :
        
                        for _address in _address_list :
        
                            if _address["OS-EXT-IPS:type"] == obj_attr_list["address_type"] :
                                obj_attr_list["cloud_ip"] = obj_attr_list["cloud_ip"]
                                return True

            else :
                _status = 1181
                _msg = "IP address list for network " + str(_run_network) + " is empty."
                cberr(_msg)
                raise CldOpsException(_msg, _status)                
        else :
            return False

    @trace
    def get_mac_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''

        if "cloud_mac" in obj_attr_list : 
            if obj_attr_list["cloud_mac"] == "True" :
                #If the MAC retrieval fails, just ignore it.
                #Nested 'try' is fine for now.
                try :
                    _virtual_interfaces = self.oskconncompute.virtual_interfaces.list(instance.id)
                    if _virtual_interfaces and len(_virtual_interfaces) :
                        obj_attr_list["cloud_mac"] = _virtual_interfaces[0].mac_address
                except :
                    obj_attr_list["cloud_mac"] = "N/A"
            else :
                obj_attr_list["cloud_mac"] = "N/A"
        return True

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all") :
        '''
        TBD
        '''
        try :
            _search_opts = {}

            if identifier != "all" :
                if obj_type == "vm" :
                    _search_opts["name"] = identifier
                else :
                    _search_opts["display_name"] = identifier

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if obj_type == "vm" :            
                _instances = self.oskconncompute.servers.list(search_opts = _search_opts)
            else :
                _instances = self.oskconnstorage.volumes.list(search_opts = _search_opts)
            
            if len(_instances) > 0 :

                if identifier == "all" :   
                    return _instances
                else :

                    if obj_type == "vv" :
                        return _instances[0]

                    for _instance in _instances :

                        _metadata = _instance.metadata

                        if "experiment_id" in _metadata :
                            if _metadata["experiment_id"] == self.expid :
                                return _instance
                    return False
            else :
                return False

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_running(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try :
            _instance = self.get_instances(obj_attr_list, "vm", \
                                           obj_attr_list["cloud_vm_name"])
            if _instance :
                if _instance.status == "ACTIVE" :
                    return _instance
                elif _instance.status == "ERROR" :
                    _msg = "Instance \"" + obj_attr_list["cloud_vm_name"] + "\"" 
                    _msg += " reported an error (from OpenStack)"
                    _status = 1870
                    cberr(_msg)
                    if fail :
                        raise CldOpsException(_msg, _status)                    
                else :
                    return False
            else :
                return False

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''

        _instance = self.is_vm_running(obj_attr_list)

        if _instance :
            obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"

            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")

            if self.get_ip_address(obj_attr_list, _instance) :
                if not obj_attr_list["userdata"] or self.get_openvpn_client_ip(obj_attr_list) :
                    obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                    return True
        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            
        return False

    @trace
    def get_host_and_instance_name(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        
        # There is a lot of extra information that can be obtained through
        # the "_info" attribute. However, a new connection has to be 
        # established to access the most up-to-date data on this attribute
        # Not sure how stable it will be with newer versions of the API. 
        _instance = self.is_vm_running(obj_attr_list, fail = fail)
        
        if _instance :
            if "OS-EXT-SRV-ATTR:host" in _instance._info :
                obj_attr_list["host_name"] = _instance._info['OS-EXT-SRV-ATTR:host']
            else :
                obj_attr_list["host_name"] = "unknown"

            if "OS-EXT-SRV-ATTR:instance_name" in _instance._info :
                obj_attr_list["instance_name"] = _instance._info['OS-EXT-SRV-ATTR:instance_name']
            else :
                obj_attr_list["instance_name"] = "unknown"
        else :
            obj_attr_list["instance_name"] = "unknown"            
            obj_attr_list["host_name"] = "unknown"
        return True

    @trace
    def floating_ip_allocate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            fips = self.oskconncompute.floating_ips.list()

            if len(fips) < 1 :
                return self.oskconncompute.floating_ips.create(obj_attr_list["floating_pool"]).ip
            else :
                for fip in fips :
                    if fip.instance_id == None :
                        return fip.ip

            print "A"
            return self.oskconncompute.floating_ips.create(obj_attr_list["floating_pool"]).ip

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

            if "cloud_vv" in obj_attr_list :
    
                obj_attr_list["last_known_state"] = "about to send volume create request"
    
                obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["cloud_name"]
                obj_attr_list["cloud_vv_name"] += '-' + "vv"
                obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]            
    
                _msg = "Creating a volume, with size " 
                _msg += obj_attr_list["cloud_vv"] + " GB, on VMC \"" 
                _msg += obj_attr_list["vmc_name"] + "\""
                cbdebug(_msg, True)
    
                _instance = self.oskconnstorage.volumes.create(obj_attr_list["cloud_vv"], \
                                                               snapshot_id = None, \
                                                               display_name = obj_attr_list["cloud_vv_name"], \
                                                               display_description = None, \
                                                               volume_type = None, \
                                                               availability_zone = None, \
                                                               imageRef = None)
                
                sleep(int(obj_attr_list["update_frequency"]))
        
                obj_attr_list["cloud_vv_uuid"] = '{0}'.format(_instance.id)
    
                _msg = "Attaching the newly created Volume \"" 
                _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                cbdebug(_msg)
    
                # There is weird bug on the python novaclient code. Don't change the
                # following line, it is supposed to be "oskconncompute", even though
                # is dealing with volumes. Will explain latter.
                self.oskconncompute.volumes.create_server_volume(obj_attr_list["cloud_vm_uuid"], \
                                                                 obj_attr_list["cloud_vv_uuid"], \
                                                                 "/dev/vdd")

            else :
                obj_attr_list["cloud_vv_uuid"] = "none"

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            else :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])
        
            if "cloud_vv_uuid" in obj_attr_list and obj_attr_list["cloud_vv_uuid"].lower() != "none" :
                
                _instance = self.get_instances(obj_attr_list, "vv", obj_attr_list["cloud_vv_name"])
    
                if _instance :
    
                    _msg = "Sending a destruction request for the Volume" 
                    _msg += " previously attached to \"" 
                    _msg += obj_attr_list["name"] + "\""
                    _msg += " (cloud-assigned uuid " 
                    _msg += obj_attr_list["cloud_vv_uuid"] + ")...."
                    cbdebug(_msg, True)
    
                    if len(_instance.attachments) :
                        _server_id = _instance.attachments[0]["server_id"]
                        _attachment_id = _instance.attachments[0]["id"]
                        # There is weird bug on the python novaclient code. Don't change the
                        # following line, it is supposed to be "oskconncompute", even though
                        # is dealing with volumes. Will explain latter.
                        self.oskconncompute.volumes.delete_server_volume(_server_id, _attachment_id)
    
                    self.oskconnstorage.volumes.delete(_instance)
                    
            _status =  0
                    
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def set_cgroup(self, obj_attr_list) :
        '''
        TBD
        '''

        _status = 189
        _fmsg = "About to import libvirt...."

        _state_code2value = {}
        _state_code2value["1"] = "running"
        _state_code2value["2"] = "blocked"
        _state_code2value["3"] = "paused"
        _state_code2value["4"] = "shutdown"
        # Temporarily renaming "shutoff" to "save"
        _state_code2value["5"] = "save"
        _state_code2value["6"] = "crashed"


        _cgroups_mapping = {}
        _cgroups_mapping["mem_hard_limit"] = "memory.limit_in_bytes"
        _cgroups_mapping["mem_soft_limit"] = "memory.soft_limit_in_bytes"
        
        try :        

            import libvirt

            _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                    "HOST", \
                                                    True, \
                                                    obj_attr_list["host_name"], \
                                                    False)

            _hypervisor_type = _host_attr_list["hypervisor_type"].lower()

            if _hypervisor_type == "qemu" :
                _astr = "/system"
            else :
                _astr = ""

            _host_name = _host_attr_list["cloud_hostname"]

            _host_ip = _host_attr_list["cloud_ip"]


            obj_attr_list["resource_limits"] = str2dic(obj_attr_list["resource_limits"].replace(';',',').replace('-',':'))

            _proc_man = ProcessManagement(username = "root", \
                                          hostname = _host_ip, \
                                          cloud_name = obj_attr_list["cloud_name"])

            for _key in obj_attr_list["resource_limits"] :

                _base_dir = obj_attr_list["cgroups_base_dir"]
                if _key.count("mem") :
                    _subsystem = "memory"

                # The cgroups/libvirt interface is currently broken (for memory limit
                # control). Will have to ssh into the node and set cgroup limits 
                # manually.
                
                #instance_data.setMemoryParameters(params={'swap_hard_limit': 9007199254740991L, 'hard_limit': 3631000L}, flags=libvirt.VIR_DOMAIN_AFFECT_LIVE)

                _value = str(value_suffix(obj_attr_list["resource_limits"][_key]))

                _cmd = "echo " + _value + " > " + _base_dir + _subsystem +"/machine/"
                _cmd += obj_attr_list["instance_name"] + ".libvirt-" + _hypervisor_type
                _cmd += "/" + _cgroups_mapping[_key]

                _msg = "Altering the \"" + _cgroups_mapping[_key] + "\" parameter"
                _msg += " on the \"" +_subsystem + "\" subsystem on cgroups for"
                _msg += " instance \"" + obj_attr_list["instance_name"] + "\" with "
                _msg += " the value \"" + _value + "\"..."
                cbdebug(_msg, True)

                _status, _result_stdout, _fmsg = _proc_man.run_os_command(_cmd)

            if not _status :
                
                if _host_name not in self.lvirt_conn or not self.lvirt_conn[_host_name] :        
                    _msg = "Attempting to connect to libvirt daemon running on "
                    _msg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\"...."
                    cbdebug(_msg)
    
                    self.lvirt_conn[_host_name] = libvirt.open( _hypervisor_type + "+tcp://" + _host_ip + _astr)
                    
                    _msg = "Connection to libvirt daemon running on hypervisor ("
                    _msg += _hypervisor_type + ") \"" + _host_ip + "\" successfully established."
                    cbdebug(_msg)
    
                    instance_data = self.lvirt_conn[_host_name].lookupByName(obj_attr_list["instance_name"])
    
                    obj_attr_list["lvirt_os_type"] = instance_data.OSType()
    
                    obj_attr_list["lvirt_scheduler_type"] = instance_data.schedulerType()[0]
        
                # All object uuids on state store are case-sensitive, so will
                # try to just capitalize the UUID reported by libvirt
    #                obj_attr_list["cloud_uuid"] = instance_data.UUIDString().upper()
    #                obj_attr_list["uuid"] = obj_attr_list["cloud_uuid"]
    #                obj_attr_list["cloud_lvid"] = instance_data.name()
    
                _gobj_attr_list = instance_data.info()
    
                obj_attr_list["lvirt_vmem"] = str(_gobj_attr_list[1])
                obj_attr_list["lvirt_vmem_current"] = str(_gobj_attr_list[2])
                obj_attr_list["lvirt_vcpus"] = str(_gobj_attr_list[3])
    
                _state_code = str(_gobj_attr_list[0])
                if _state_code in _state_code2value :
                    obj_attr_list["lvirt_state"] = _state_code2value[_state_code]
                else :
                    obj_attr_list["lvirt_state"] = "unknown"
    
                if _state_code == "1" :
    
                    _vcpu_info = instance_data.vcpus()
    
                    for _vcpu_nr in range(0, int(obj_attr_list["lvirt_vcpus"])) :
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_pcpu"] = str(_vcpu_info[0][_vcpu_nr][3])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_time"] =  str(_vcpu_info[0][_vcpu_nr][2])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_state"] =  str(_vcpu_info[0][_vcpu_nr][1])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_map"] = str(_vcpu_info[1][_vcpu_nr])
    
                    _sched_info = instance_data.schedulerParameters()
    
                    obj_attr_list["lvirt_vcpus_soft_limit"] = str(_sched_info["cpu_shares"])
    
                    if "vcpu_period" in _sched_info :
                        obj_attr_list["lvirt_vcpus_period"] = str(float(_sched_info["vcpu_period"]))
                        obj_attr_list["lvirt_vcpus_quota"] = str(float(_sched_info["vcpu_quota"]))
                        obj_attr_list["lvirt_vcpus_hard_limit"] = str(float(obj_attr_list["lvirt_vcpus_quota"]) / float(obj_attr_list["lvirt_vcpus_period"]))
    
                    if "memoryParameters" in dir(instance_data) :    
                        _mem_info = instance_data.memoryParameters(0)
    
                        obj_attr_list["lvirt_mem_hard_limit"] = str(_mem_info["hard_limit"])
                        obj_attr_list["lvirt_mem_soft_limit"] = str(_mem_info["soft_limit"])
                        obj_attr_list["lvirt_mem_swap_hard_limit"] = str(_mem_info["swap_hard_limit"])
    
                    if "blkioParameters" in dir(instance_data) :
                        _diskio_info = instance_data.blkioParameters(0)
                        obj_attr_list["lvirt_diskio_soft_limit"] = "unknown"
                        if _diskio_info :
                            if "weight" in _diskio_info :
                                obj_attr_list["lvirt_diskio_soft_limit"] = str(_diskio_info["weight"])
    
    
                _status = 0

        except libvirt.libvirtError, msg :
            _fmsg = "Error while attempting to connect to libvirt daemon running on "
            _fmsg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\":"
            _fmsg += msg
            cberr(_fmsg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while attempting to set resource limits for VM " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)

            else :
                _msg = "Successfully set resource limits for VM " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)

            return _status, _msg

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _fault = "No info"

            obj_attr_list["cloud_vm_uuid"] = "NA"
            _instance = False

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["cloud_name"]
            obj_attr_list["cloud_vm_name"] += '-' + "vm"
            obj_attr_list["cloud_vm_name"] += obj_attr_list["name"].split("_")[1]
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

            obj_attr_list["last_known_state"] = "about to connect to openstack manager"

            if obj_attr_list["floating_ip"].lower() == "true" :
                obj_attr_list["address_type"] = "floating"
            else :
                obj_attr_list["address_type"] = "fixed"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            obj_attr_list["last_known_state"] = "about to get flavor and image list"

            if obj_attr_list["security_groups"].lower() == "false" :
                _security_groups = None
            else :
                # "Security groups" must be a list
                _security_groups = []
                _security_groups.append(obj_attr_list["security_groups"])

            if obj_attr_list["key_name"].lower() == "false" :
                _key_name = None
            else :
                _key_name = obj_attr_list["key_name"]

            obj_attr_list["last_known_state"] = "about to send create request"

            _flavor = self.get_flavors(obj_attr_list)            
            _imageid = self.get_images(obj_attr_list)

            if "host_name" in obj_attr_list :
#                _scheduler_hints = { "force_hosts" : obj_attr_list["host_name"] }
                _availability_zone = "nova:" + obj_attr_list["host_name"]
            else :
#                _scheduler_hints = None
                _availability_zone = None
                
            _scheduler_hints = None

            if "userdata" in obj_attr_list and obj_attr_list["userdata"] :
                _userdata = obj_attr_list["userdata"]
                _config_drive = True
            else :
                _config_drive = None                
                _userdata = None

            _meta = {}
            if "meta_tags" in obj_attr_list :
                if obj_attr_list["meta_tags"] != "empty" and \
                obj_attr_list["meta_tags"].count(':') and \
                obj_attr_list["meta_tags"].count(',') :
                    _meta = str2dic(obj_attr_list["meta_tags"])
            
            _meta["experiment_id"] = obj_attr_list["experiment_id"]

            _networkid = self.get_networks(obj_attr_list)
            _netid = [{"net-id" : _networkid.id}]

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            _msg = "Starting an instance on OpenStack, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" (" + str(_imageid) + ") and "
            _msg += "size \"" + obj_attr_list["size"] + "\" (" + str(_flavor) + ")"

#            if _scheduler_hints :
#                _msg += ", with scheduler hints \"" + str(_scheduler_hints) + "\" "

            if _availability_zone :
                _msg += ", on the availability zone \"" + str(_availability_zone) + "\" "

            _msg += ", network identifier \"" + str(_netid) + "\","
            _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
            cbdebug(_msg, True)
            
            _instance = self.oskconncompute.servers.create(name = obj_attr_list["cloud_vm_name"], \
                                                    image = _imageid, \
                                                    flavor = _flavor, \
                                                    security_groups = _security_groups, \
                                                    key_name = _key_name, \
                                                    scheduler_hints = _scheduler_hints, \
                                                    availability_zone = _availability_zone, \
                                                    meta = _meta, \
                                                    config_drive = _config_drive, \
                                                    userdata = _userdata, \
                                                    nics = _netid)

            if _instance :
                
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = '{0}'.format(_instance.id)

                _status, _fmsg = self.vvcreate(obj_attr_list)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                if "floating_ip" in obj_attr_list :

                    if obj_attr_list["floating_ip"].lower() == "true" :
                        _msg = "Adding a floating IP to " + obj_attr_list["name"] + "..."
                        cbdebug(_msg, True)
                        _instance.add_floating_ip(self.floating_ip_allocate(obj_attr_list))

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.get_mac_address(obj_attr_list, _instance)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                self.get_host_and_instance_name(obj_attr_list)

                if "resource_limits" in obj_attr_list :
                    _status, _fmsg = self.set_cgroup(obj_attr_list)
                else :
                    _status = 0

            else :
                _fmsg = "Failed to obtain instance's (cloud assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100
                
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :

            self.disconnect()

            if _status :
                
                _vminstance = self.get_instances(obj_attr_list, "vm", \
                                               obj_attr_list["cloud_vm_name"])

                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "

                if _vminstance :
                    # Not the best way to solve this problem. Will improve later.
                    
                    if not self.is_vm_running(obj_attr_list) :
                        if "fault" in dir(_vminstance) :
                            if "message" in _vminstance.fault : 
                                print _vminstance.fault
                                _msg += "\n\t" + _vminstance.fault["message"] + "\n: "
                            #if "details" in _vminstance.fault : 
                            #    _msg += _vminstance.fault["details"] + ":"
                    # Try to make a last attempt effort to get the hostname,
                    # even if the VM creation failed.

                    self.get_host_and_instance_name(obj_attr_list, fail = False)

                    _vminstance.delete()

                    if "cloud_vv" in obj_attr_list :
                        self.vvdestroy(obj_attr_list)

                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)
                
                raise CldOpsException(_msg, _status)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _msg = "Sending a termination request for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
            
                _instance.delete()
                sleep(_wait)

                while not _instance :
                    _instance = self.get_instances(obj_attr_list, "vm", \
                                           obj_attr_list["cloud_vm_name"])
                    sleep(_wait)
            else :
                True

            _status, _fmsg = self.vvdestroy(obj_attr_list)

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
             
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
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

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent."
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _instance.create_image(obj_attr_list["captured_image_name"], None)
                sleep(_wait)

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries : 
                    _vm_images = self.oskconncompute.images.list()
                    for _vm_image in _vm_images :
                        if _vm_image.name == obj_attr_list["captured_image_name"] :
                            if _vm_image.status == "ACTIVE" :
                                _vm_image_created = True
                                _time_mark_crc = int(time())
                                obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    if "mgt_103_capture_request_completed" not in obj_attr_list :
                        obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs
                        
                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing. "
                    _msg += "Will wait " + obj_attr_list["update_frequency"]
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    sleep(int(obj_attr_list["update_frequency"]))             
                    _curr_tries += 1

            else :
                _fmsg = "This instance does not exist"
                _status = 1098

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "" + obj_attr_list["name"] + ""
                _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _fmsg +=  "could not be captured after " + str(_max_tries * _wait) + " seconds.... "
                cberr(_msg)
            else :
                _status = 0
            
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()   
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        if not self.oskconncompute :
            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"])

        operation = obj_attr_list["mtype"]

        _msg = "Sending a " + operation + " request for "  + obj_attr_list["name"]
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)
        
        # This is a migration, so we need to poll very frequently
        # If it is a micro-checkpointing operation, then poll normally
        _orig_freq = int(obj_attr_list["update_frequency"])
        _wait = 1 if operation == "migrate" else _orig_freq
        _wait = min(_wait, _orig_freq)
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        if _wait < _orig_freq :
            _max_tries = _max_tries * (_orig_freq / _wait) 
        
        _time_mark_crs = int(time())            
        try :
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])
    
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _instance.live_migrate(obj_attr_list["destination_name"].replace("host_", ""))
                
                obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]
                
                while True and _curr_tries < _max_tries : 
                    sleep(_wait)             
                    _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
                    
                    if _instance.status not in ["ACTIVE", "MIGRATING"] :
                        _status = 4328
                        _msg = "Migration of instance failed, OpenStack state is: " + _instance.status
                        raise CldOpsException(_msg, _status)
                    
                    if _instance.status == "ACTIVE" :
                        _time_mark_crc = int(time())
                        obj_attr_list["mgt_503_" + operation + "_request_completed"] = _time_mark_crc - _time_mark_crs
                        break

                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing " + operation
                    _msg += ". Will wait " + str(_wait)
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    _curr_tries += 1
            else :
                _fmsg = "This instance does not exist"
                _status = 1098
            
            _status = 0
    
        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
        
        except Exception, e :
            _status = 349201
            _fmsg = str(e)
            
        finally :
            self.disconnect()            
            if "mgt_503_" + operation + "_request_completed" not in obj_attr_list :
                obj_attr_list["mgt_999_" + operation + "_request_failed"] = int(time()) - _time_mark_crs
                        
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be " + operation + "ed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully " + operation + "ed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
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
    
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

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

            _instance = self.get_instances(obj_attr_list, "vm", \
                                              obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    _instance.pause()
                elif _ts == "save" :
                    _instance.suspend()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.unpause()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.resume()
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on OpenStack Cloud"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\" :" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on OpenStack Cloud"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list) :
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
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
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
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
