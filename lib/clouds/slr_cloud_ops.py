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
    Created on Fev 24, 2014

    SoftLayer Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from subprocess import Popen, PIPE
from uuid import uuid5, UUID
from random import choice
import socket

import SoftLayer.API

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

class SlrCmds(CommonCloudFunctions) :
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
        self.nodeman = False
        self.sshman = False
        self.imageman = False
        self.expid = expid
        self.ft_supported = False

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "SoftLayer Cloud"

    @trace
    def connect(self, access, authentication_data, region) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            

            _username, _api_key, _api_type = authentication_data.split('-')
                        
            if access.lower().count("private") :
                _api_endpoint = SoftLayer.API_PRIVATE_ENDPOINT
            else :
                _api_endpoint = SoftLayer.API_PUBLIC_ENDPOINT

            self.slconn = SoftLayer.Client (username = _username.strip(), \
                                            api_key= _api_key.strip(), \
                                            endpoint_url = _api_endpoint)

            self.slconn['Account'].getObject()

            _region = SoftLayer.MessagingManager(self.slconn).get_endpoint(datacenter = region)
            
            _msg = "Selected region is " + str(region) +  " (" + _region + ")"
                                    
            if _api_type.lower().count("baremetal") :
                self.nodeman= SoftLayer.HardwareManager(self.slconn)
            else :
                self.nodeman= SoftLayer.VSManager(self.slconn)

            self.sshman = SoftLayer.SshKeyManager(self.slconn)
                
            self.imageman = SoftLayer.ImageManager(self.slconn)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "SoftLayer connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "SoftLayer connection successful."
                cbdebug(_msg)
                return _status, _msg, _region
    
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
                for _key_pair in self.sshman.list_keys() :
                    if _key_pair["label"] == key_name :
                        _key_pair_found = True

                if not _key_pair_found :
                    _pub_key_fn = vm_defaults["credentials_dir"] + '/'
                    _pub_key_fn += vm_defaults["ssh_key_name"] + ".pub"

                    _msg = "Creating the ssh key pair \"" + key_name + "\""
                    _msg += " on VMC " + vmc_name + ", using the public key \""
                    _msg += _pub_key_fn + "\"..."
                    cbdebug(_msg, True)
                    
                    _fh = open(_pub_key_fn, 'r')
                    _pub_key = _fh.read()
                    _fh.close()
                                        
                    self.sshman.add_key(_pub_key, key_name)
                    _key_pair_found = True

            if security_group_name :
                _security_group_found = True

                '''
                At the moment, there isn't a "security group" object/abstraction
                (i.e., fine-grained network access control for CCIs/VSs) in 
                SoftLayer.
                '''

#                _msg = "Checking if the security group \"" + security_group_name
#                _msg += "\" is created on VMC " + vmc_name + "...."
#                cbdebug(_msg, True)

#                _security_group_found = False
#                for security_group in self.oskconncompute.security_groups.list() :
#                    if security_group.name == security_group_name :
#                        _security_group_found = True
    
#                if not _security_group_found :
#                    _msg = "ERROR! Please create the security group \"" 
#                    _msg += security_group_name + "\" in "
#                    _msg += "SoftLayer before proceeding."
#                    _fmsg = _msg 
#                    cberr(_msg, True)
#            else :
#                _security_group_found = True
            
            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            if vm_defaults["images_access"] == "private" :    
                _registered_image_list = self.imageman.list_private_images()
            else :    
                _registered_image_list = self.imageman.list_public_images()                

            _registered_imageid_list = []

            for _registered_image in _registered_image_list :
                _registered_imageid_list.append(_registered_image["name"])

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
#                       _msg += "xImage id for VM roles \"" + ','.join(_required_imageid_list[_imageid]) + "\" is \""
#                       _msg += _imageid + "\" and it is already registered.\n"
                else :
                    _msg += "xWARNING Image id for VM roles \""
                    _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                    _msg += _imageid + "\" is NOT registered "
                    _msg += "(attaching VMs with any of these roles will result in error).\n"

            if not len(_detected_imageids) :
                _msg = "ERROR! None of the image ids used by any VM \"role\" were detected"
                _msg += " in this SoftLayer cloud. Please register at least one "
                _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
                cberr(_msg, True)
            else :
                _msg = _msg.replace("yx",'')
                _msg = _msg.replace('x',"         ")
                _msg = _msg[:-2]
                if len(_msg) :
                    cbdebug(_msg, True)

            if not (_key_pair_found and _security_group_found and len(_detected_imageids)) :
                _msg = "Check the previous errors, fix it (using SoftLayer's Portal"
                _msg += "or sl CLI"
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
                _msg = "VMC \"" + vmc_name + "\" was successfully tested."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.nodeman :
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

                _instances = self.nodeman.list_instances(datacenter = obj_attr_list["name"])

                for _instance in _instances :
                    if _instance["hostname"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _running_instances = True

                        if not ("activeTransaction" in _instance) :
                            if  _instance["status"]["keyName"] == "ACTIVE" :
                                if self.nodeman.wait_for_transaction(_instance["id"], 1, 1) :                                                                
                                    _msg = "Terminating instance: " 
                                    _msg += _instance["globalIdentifier"] + " (" + _instance["hostname"] + ")"
                                    cbdebug(_msg, True)                              
                                    self.nodeman.cancel_instance(_instance["id"])

                        if "activeTransaction" in _instance :
                            _msg = "Will wait for instance "
                            _msg += _instance["globalIdentifier"] + "\"" 
                            _msg += " (" + _instance["hostname"] + ") to "
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
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on SoftLayer Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\""
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
    
                obj_attr_list["cloud_hostname"] = _hostname.replace("https://",'')

                _x, obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["cloud_hostname"])

                obj_attr_list["arrival"] = int(time())
    
            if obj_attr_list["discover_hosts"].lower() == "true" :
                _msg = "Host discovery for VMC \"" + obj_attr_list["name"]
                _msg += "\" request, but SoftLayer does not allow it. Ignoring for now....."
                cbdebug(_msg, True)
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
                    
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on SoftLayer Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["images_access"] == "private" :    
                _image_list =  self.imageman.list_private_images()
            else :    
                _image_list = self.imageman.list_public_images()  

            _fmsg += "Please check if the defined image name is present on this "
            _fmsg += "SoftLayer Cloud"

            _imageid = False

            _candidate_images = []

            for _idx in range(0,len(_image_list)) :
                if obj_attr_list["randomize_image_name"].lower() == "false" and \
                _image_list[_idx]["name"] == obj_attr_list["imageid1"] :
                    _imageid = _image_list[_idx]["globalIdentifier"]
                    break
                elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                _image_list[_idx].name.count(obj_attr_list["imageid1"]) :
                    _candidate_images.append(_image_list[_idx])
                else :                     
                    True

            if  obj_attr_list["randomize_image_name"].lower() == "true" :
                _image = choice(_candidate_images)
                _imageid = _image["globalIdentifier"] 

            _status = 0

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
                _msg += "on SoftLayer \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on SoftLayer \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        
        if obj_attr_list["prov_netname"] == "private" :
            _key = "Backend"

        elif obj_attr_list["prov_netname"] == "public" :
            _key = ''

        if ("primary" + _key + "IpAddress") in instance :
            obj_attr_list["prov_cloud_ip"] = instance["primary" + _key + "IpAddress"]
            obj_attr_list["run_cloud_ip"] = instance["primary" + _key + "IpAddress"]

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            obj_attr_list["cloud_hostname"] = instance["hostname"]

            return True
        else :
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all") :
        '''
        TBD
        '''
        try :
            _search_opts = {}

            if identifier != "all" :
                _instances = self.nodeman.list_instances(datacenter = obj_attr_list["vmc_name"], hostname = identifier)
            else :
                _instances = self.nodeman.list_instances(datacenter = obj_attr_list["vmc_name"])                

            if not self.nodeman:
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])
            
            if len(_instances) > 0 :

                if identifier == "all" :   
                    return _instances
                else :
                    return _instances[0]
            else :
                return False

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    @trace
    def is_vm_running(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try :
            _instance = self.get_instances(obj_attr_list, "vm", \
                                           obj_attr_list["cloud_vm_name"])
            if _instance :
                if not ("activeTransaction" in _instance) :
                    return _instance
                else :
                    if _instance["status"]["name"].lower().count("error") :
                        _msg = "Instance \"" + obj_attr_list["cloud_vm_name"] + "\"" 
                        _msg += " reported an error (from SoftLayer)"
                        _status = 1870
                        cberr(_msg)
                        if fail :
                            raise CldOpsException(_msg, _status)                    
                    else :
                        return False
            else :
                return False

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

            obj_attr_list["last_known_state"] = "about to connect to SoftLayer manager"

            if not self.nodeman or not self.sshman or not self.imageman :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            obj_attr_list["last_known_state"] = "about to get flavor and image list"

            if obj_attr_list["key_name"].lower() == "false" :
                _key_name = None
            else :
                _key_name = obj_attr_list["key_name"]

            obj_attr_list["last_known_state"] = "about to send create request"

            _imageid = self.get_images(obj_attr_list)

            _vcpus,_vmemory = obj_attr_list["size"].split('-')
            
            obj_attr_list["vcpus"] = _vcpus
            obj_attr_list["vmemory"] = _vmemory
            
            _meta = {}
            if "meta_tags" in obj_attr_list :
                if obj_attr_list["meta_tags"] != "empty" and \
                obj_attr_list["meta_tags"].count(':') and \
                obj_attr_list["meta_tags"].count(',') :
                    _meta = str2dic(obj_attr_list["meta_tags"])
            
            _meta["experiment_id"] = obj_attr_list["experiment_id"]

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            _msg = "Starting an instance on SoftLayer, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" (" + str(_imageid) + ") and "
            _msg += "size \"" + obj_attr_list["size"] + "\", "
            _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
            cbdebug(_msg, True)

            _key_id = self.sshman.list_keys(label = obj_attr_list["key_name"])[0]["id"]

            _kwargs = { "cpus": int(obj_attr_list["vcpus"]), \
                       "memory": int(obj_attr_list["vmemory"]), \
                       "hourly": True, \
                       "domain": "softlayer.com", \
                       "hostname": obj_attr_list["cloud_vm_name"], \
                       "datacenter": obj_attr_list["vmc_name"], \
                       "image_id" : _imageid, \
                       "ssh_keys" : [ int(_key_id) ], \
                       "nic_speed" : int(obj_attr_list["nic_speed"])}

            if len(obj_attr_list["private_vlan"]) > 2 :
                _kwargs["private_vlan"] = int(obj_attr_list["private_vlan"])

            if obj_attr_list["private_network_only"].lower() == "true" :
                _kwargs["private"] = True
                
            _instance = self.nodeman.create_instance(**_kwargs)

            if _instance :

                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _instance["globalIdentifier"]

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                
                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916

            else :
                _fmsg = "Failed to obtain instance's (cloud assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100
                
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
                _vminstance = self.get_instances(obj_attr_list, "vm", \
                                               obj_attr_list["cloud_vm_name"])

                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                
                if _vminstance :
                    self.nodeman.wait_for_transaction(_instance["id"], \
                                                     int(obj_attr_list["update_attempts"]), \
                                                     int(obj_attr_list["update_frequency"]))
                    self.nodeman.cancel_instance(obj_attr_list["cloud_vm_uuid"])

                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)
                
                raise CldOpsException(_msg, _status)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _time_mark_drs = int(time())
            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                
            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            if not self.nodeman:
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :

                _msg = "Wait until all active transactions for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += " are finished...."
                cbdebug(_msg, True)

                while not self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries : 

                    sleep(int(obj_attr_list["update_frequency"]))      
                    _curr_tries += 1

                _msg = "Sending a termination request for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
            
                self.nodeman.cancel_instance(obj_attr_list["cloud_vm_uuid"])
                sleep(_wait)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
            else :
                True

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
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on SoftLayer Cloud \"" + obj_attr_list["cloud_name"]
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

            if not self.nodeman or not self.imageman :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                _msg = "Wait until all active transactions for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += " are finished...."
                cbdebug(_msg, True)

                while not self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries : 

                    sleep(int(obj_attr_list["update_frequency"]))      
                    _curr_tries += 1

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent."
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                self.nodeman.capture(obj_attr_list["cloud_vm_uuid"], obj_attr_list["captured_image_name"])

                sleep(_wait)

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_being_captured = False

                while not _vm_being_captured and _curr_tries < _max_tries : 

                    if self.is_vm_running(obj_attr_list) :
                        _time_mark_crc = int(time())
                        obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs                        
                        _vm_being_captured = False
                        break

                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing. "
                    _msg += "Will wait " + obj_attr_list["update_frequency"]
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    sleep(int(obj_attr_list["update_frequency"]))             
                    _curr_tries += 1

                if "mgt_103_capture_request_completed" not in obj_attr_list :
                    obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs

                if obj_attr_list["images_access"] == "private" :    
                    _vm_image =  self.imageman.list_private_images(name = obj_attr_list["captured_image_name"])
                else :    
                    _vm_image = self.imageman.list_public_images(name = obj_attr_list["captured_image_name"])

                if len(_vm_image) and not "mgt_999_capture_request_failed" in obj_attr_list :
                    _status = 0

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

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            if not self.nodeman :    
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

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                _msg = "Wait until all active transactions for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += " are finished...."
                cbdebug(_msg, True)

                while not self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries : 

                    sleep(int(obj_attr_list["update_frequency"]))      
                    _curr_tries += 1

                if _ts == "fail" :
                    self.slconn.pause(id = obj_attr_list["cloud_vm_uuid"])
                elif _ts == "save" :
                    self.slconn.powerOff(id = obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.resume(id = obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.powerOn(id = obj_attr_list["cloud_vm_uuid"])
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
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
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on SoftLayer Cloud"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\" :" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on SoftLayer Cloud"
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
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on SoftLayer Cloud \"" + obj_attr_list["cloud_name"]
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
                _msg += " on SoftLayer Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on SoftLayer Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg