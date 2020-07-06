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
    Created on Fev 24, 2014

    SoftLayer Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import choice, randint

import SoftLayer
from SoftLayer import exceptions as slexceptions

import traceback

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, is_number
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

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
        self.additional_rc_contents = ''        
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
                self.slconn = SoftLayer.create_client_from_env (username = _username.strip(), \
                                                                api_key= _api_key.strip(), \
                                                                endpoint_url = SoftLayer.API_PRIVATE_ENDPOINT)
            else :
                self.slconn = SoftLayer.create_client_from_env (username = _username.strip(), \
                                                                api_key= _api_key.strip(), \
                                                                endpoint_url = SoftLayer.API_PUBLIC_ENDPOINT)            

            _resp = self.slconn.call('Account', 'getObject')

            _datacenters = SoftLayer.VSManager(self.slconn).get_create_options()['datacenters']
            for _dcitem in _datacenters :
                if region == _dcitem['template']['datacenter']['name'] :
                    _region = _dcitem['template']['datacenter']['name']

            _msg = "Selected region is " + str(region) +  " (" + _region + ")"

            if _api_type.lower().count("baremetal") :
                self.nodeman = SoftLayer.HardwareManager(self.slconn)
            else :
                self.nodeman = SoftLayer.VSManager(self.slconn)

            self.sshman = SoftLayer.SshKeyManager(self.slconn)

            self.imageman = SoftLayer.ImageManager(self.slconn)

            _status = 0

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg =  self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
        
                _msg =  self.get_description() + " connection successful."
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

            self.connect(access, credentials, vmc_name)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults, False, vmc_name)
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, access, vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it (using GCE's web"
                _msg += " GUI (Google Developer's Console) or gcloud CLI utility"
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

        _prov_netname_found = True
        _run_netname_found = True
            
        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, access, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        if access == "private" :    
            _registered_image_list = self.imageman.list_private_images()
        else :    
            _registered_image_list = self.imageman.list_public_images()   

        _registered_imageid_list = []

        _map_name_to_id = {}
        _map_id_to_name = {}

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image["id"])
            _map_name_to_id[str(_registered_image["name"].encode('utf-8').strip())] = str(_registered_image["id"])

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

        return _detected_imageids

    @trace
    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        obj_attr_list["initial_hosts"] = ''.split(',')
        obj_attr_list["host_count"] = len(obj_attr_list["initial_hosts"])
    
        return True

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

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')

            _running_instances = True
            while _running_instances and _curr_tries < _max_tries :

                _running_instances = False

                _instances = self.nodeman.list_instances(datacenter = obj_attr_list["name"])

                for _instance in _instances :

                    if _instance["hostname"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _running_instances = True

                        _instance_details = self.nodeman.get_instance(int(_instance["id"]))

                        if not ("activeTransaction" in _instance_details) :
                            if "billingItem" in _instance_details :
                                if  _instance_details["status"]["keyName"] == "ACTIVE" :
                                    _msg = "Terminating instance: " 
                                    _msg += _instance_details["globalIdentifier"] 
                                    _msg += " (" + _instance_details["hostname"] + ")"
                                    cbdebug(_msg, True)                              
                                    self.nodeman.cancel_instance(_instance["globalIdentifier"])

                        if "activeTransaction" in _instance_details :
                            _msg = "Will wait for instance "
                            _msg += _instance_details["globalIdentifier"] + "\"" 
                            _msg += " (" + _instance_details["hostname"] + ") to "
                            _msg += "be fully deleted"
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
            
        except CldOpsException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

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

            if not _status :
                _x, _y, _hostname = self.connect(obj_attr_list["access"], \
                                                 obj_attr_list["credentials"], \
                                                 obj_attr_list["name"])
    
                obj_attr_list["cloud_hostname"] = _hostname.replace("https://",'')

                _x, obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["cloud_hostname"])

                obj_attr_list["arrival"] = int(time())
    
            if str(obj_attr_list["discover_hosts"]).lower() == "true" :
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            _time_mark_prc = int(time())
                    
            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

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
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"                        
            _nr_instances = 0

            for _vmc_uuid in self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC") :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                      "VMC", False, _vmc_uuid, \
                                                      False)
                
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], _vmc_attr_list["name"])

                sleep(15)

                _instance_list = self.get_instances({"vmc_name": _vmc_attr_list["name"]}, "vm", "all")                

                if _instance_list :
                    for _instance in _instance_list :
                        if "hostname" in _instance :
                            if "status" in _instance :
                                if "keyName" in _instance["status"] :
                                    if _instance["status"]["keyName"] == "ACTIVE" :
                                        if _instance["hostname"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                                            _nr_instances += 1

        except Exception as e :
            _status = 23
            _nr_instances = "NA"
            _fmsg = "(While counting instance(s) through API call \"list\") " + str(e)

        finally :
            return _nr_instances

    @trace
    def get_ssh_keys(self, vmc_name, key_name, key_contents, key_fingerprint, registered_key_pairs, internal, connection) :
        '''
        TBD
        '''

        for _key_pair in self.sshman.list_keys() :
            registered_key_pairs[_key_pair["label"]] = _key_pair["fingerprint"] + '-' + str(_key_pair["id"])
            #self.sshman.delete_key(_keyid)

        return True

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

            object_mask = 'id, globalIdentifier, hostname, domain, fullyQualifiedDomainName, primaryBackendIpAddress, primaryIpAddress, lastKnownPowerState.name, powerState, maxCpu, maxMemory, datacenter, activeTransaction.transactionStatus[friendlyName,name], status, provisionDate'

            if identifier != "all" :
                _instances = self.nodeman.list_instances(mask=object_mask,datacenter = obj_attr_list["vmc_name"], hostname = identifier)
            else :
                _instances = self.nodeman.list_instances(mask=object_mask,datacenter = obj_attr_list["vmc_name"])

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

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)
            
    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "captured_image_name" in obj_attr_list :
                _img_key = "captured_image_name"
            else :
                _img_key = "imageid1"
            
            for _image_access in [ "private", "public"] :           
                if _image_access == "private" :
                    if self.is_cloud_image_uuid(obj_attr_list[_img_key]) :
                        _image_list =  self.imageman.list_private_images(id = obj_attr_list[_img_key])
                    else :
                        _image_list =  self.imageman.list_private_images(name = obj_attr_list[_img_key])                    
                else :
                    if self.is_cloud_image_uuid(obj_attr_list[_img_key]) :
                        _image_list =  self.imageman.list_public_images(id = obj_attr_list[_img_key])
                    else :
                        _image_list =  self.imageman.list_public_images(name = obj_attr_list[_img_key])

                _fmsg = "Please check if the defined image name is present on this "
                _fmsg += self.get_description()
    
                _image = False
    
                _candidate_images = []
    
                if self.is_cloud_image_uuid(obj_attr_list[_img_key]) :
                    _match_key = "id"
                else :
                    _match_key = "name"                
                
                for _idx in range(0,len(_image_list)) :
                    _image_list[_idx]["name"] = _image_list[_idx]["name"].encode('utf-8').strip()
                    
                    if obj_attr_list["randomize_image_name"].lower() == "false" and \
                    str(_image_list[_idx][_match_key]) == obj_attr_list[_img_key] :
                        _imageid = _image_list[_idx]["globalIdentifier"]
    
                        _candidate_images.append(_image_list[_idx])
                    
                    elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                    _image_list[_idx].name.count(obj_attr_list[_img_key]) :
                        _candidate_images.append(_image_list[_idx])
                    else :                     
                        True
    
                if len(_candidate_images) :
                    if  obj_attr_list["randomize_image_name"].lower() == "true" :
                        _image = choice(_candidate_images)
                    else :
                        _image = _candidate_images[0]
    
                    obj_attr_list["imageid1"] = _image["name"]
                    obj_attr_list["boot_globalid_imageid1"] = _image["globalIdentifier"]                 
                    obj_attr_list["boot_volume_imageid1"] = _image["id"] 
    
                    _status = 0
                    break

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :

            if _status :
                if _img_key == "imageid1" :
                    _msg = "Image Name (" +  obj_attr_list["imageid1"] + " ) not found: " + _fmsg
                    cberr(_msg, True)
                    raise CldOpsException(_msg, _status)
                else :
                    return _image
            else :
                return _image

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
        self.sshman.add_key(key_type + ' ' + key_contents, key_name)

        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        if len(imageid) == 7 and is_number(imageid) :            
            return True
        
        if len(imageid) == 36 and imageid.count('-') == 4 :
            return True
        
        return False

    @trace
    def is_vm_running(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try :
            
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                
                if "provisionDate" not in _instance :
                    return False
                
                if _instance["provisionDate"] == "" :
                    return False

                return True

            return False

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            if fail :
                raise CldOpsException(_fmsg, _status)
            else :
                return False

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''
        if self.is_vm_running(obj_attr_list) :

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
    
            if _instance :
                obj_attr_list["last_known_state"] = "ACTIVE without ip assigned"
    
                if self.get_ip_address(obj_attr_list, _instance) :
                    obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                    return True
        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            
        return False

    @trace
    def vm_placement(self, obj_attr_list) :
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
                _msg = "VM placement failed: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace
    def vvcreate(self, obj_attr_list, kwargs) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "cloud_vv_type" not in obj_attr_list :
                obj_attr_list["cloud_vv_type"] = "NOT SUPPORTED"

            if "cloud_vv" in obj_attr_list :

                obj_attr_list["last_known_state"] = "about to send volume create request"

#                kwargs["disks"].append(obj_attr_list["cloud_vv"])
                
                obj_attr_list["cloud_vv_uuid"] = "IMPLICIT"

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

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

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "not supported" and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" and str(obj_attr_list["cloud_vv_uuid"]).lower() != "implicit" :    
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
            
            _instance = False

            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)
            
            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"

            obj_attr_list["instance_creation_status"] = 1
            
            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if not self.nodeman or not self.sshman or not self.imageman :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)

            obj_attr_list["config_drive"] = False

            _kwargs = { "hourly": True, \
                        "domain": "softlayer.com", \
                        "hostname": obj_attr_list["cloud_vm_name"], \
                        "datacenter": obj_attr_list["vmc_name"], \
                        "image_id" : obj_attr_list["boot_globalid_imageid1"], \
                        "nic_speed" : int(obj_attr_list["nic_speed"]), \
                        'local_disk': True, \
                        } 

            if obj_attr_list["size"].count('-') :            
                _vcpus,_vmemory = obj_attr_list["size"].split('-')
                
                obj_attr_list["vcpus"] = _vcpus
                obj_attr_list["vmemory"] = _vmemory

                _kwargs["cpus"] = int(obj_attr_list["vcpus"])
                _kwargs["memory"] = int(obj_attr_list["vmemory"])
            else :
                _kwargs["flavor"] = obj_attr_list["size"]

            self.vvcreate(obj_attr_list, _kwargs)
            
            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])
            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            _key_id = self.sshman.list_keys(label = obj_attr_list["key_name"])[0]["id"]

            _kwargs["ssh_keys"] = [ int(_key_id) ]

            if len(obj_attr_list["private_vlan"]) > 2 :
                _kwargs["private_vlan"] = int(obj_attr_list["private_vlan"])

            if len(obj_attr_list["private_subnet"]) > 2 :
                _kwargs["private_subnet"] = int(obj_attr_list["private_subnet"])

            if obj_attr_list["private_network_only"].lower() == "true" :
                _kwargs["private"] = True

            self.pre_vmcreate_process(obj_attr_list)

            _kwargs["userdata"] = self.populate_cloudconfig(obj_attr_list)
                
            _instance = self.nodeman.create_instance(**_kwargs)

            if _instance :

                obj_attr_list["instance_creation_status"] = 2

                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _instance["globalIdentifier"]

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["instance_creation_status"] = 0
                
                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916

            else :
                _fmsg = "Failed to obtain instance's (cloud assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100
                
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)            
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
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0
            
            _instance = self.wait_until_transaction(obj_attr_list)
            
            if _instance :

                self.common_messages("VM", obj_attr_list, "destroying", 0, '')
                
                if int(obj_attr_list["instance_creation_status"]) == 2 :
                    self.nodeman.wait_for_transaction(_instance["id"], \
                                                     int(obj_attr_list["update_attempts"]), \
                                                     int(obj_attr_list["update_frequency"]))

                if int(obj_attr_list["instance_creation_status"]) != 1 :
                    self.nodeman.cancel_instance(obj_attr_list["cloud_vm_uuid"])
                    sleep(_wait)
    
                    while self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries :
                        sleep(_wait)
                        _curr_tries += 1
                        
            else :
                True

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
             
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

            if not self.nodeman or not self.imageman :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.wait_until_transaction(obj_attr_list)

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                self.nodeman.capture(obj_attr_list["cloud_vm_uuid"], obj_attr_list["captured_image_name"])

                sleep(_wait)

                _vm_being_captured = False
                
                while not _vm_being_captured and _curr_tries < _max_tries : 

                    obj_attr_list["images_access"] = "private"

                    _image_instance = self.get_images(obj_attr_list)
                    
                    if _image_instance :
                        _instance = self.wait_until_transaction(obj_attr_list)
                        _time_mark_crc = int(time())
                        obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs                        
                        _vm_being_captured = False
                        break

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
                cberr(_fmsg)
            else :
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

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _instance = self.wait_until_transaction(obj_attr_list)

            if _instance :

                if _ts == "fail" :
                    self.slconn.pause(id = obj_attr_list["cloud_vm_uuid"])
                elif _ts == "save" :
                    self.slconn.powerOff(id = obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.resume(id = obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.powerOn(id = obj_attr_list["cloud_vm_uuid"])

            _instance = self.wait_until_transaction(obj_attr_list)
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs
                        
            _status = 0

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
            _image_instance = False
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            if not self.nodeman or not self.imageman :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            obj_attr_list["images_access"] = "private"

            _image_instance = self.get_images(obj_attr_list)
                
            if _image_instance :

                self.imageman.delete_image(obj_attr_list["boot_globalid_imageid1"])

                _wait = int(obj_attr_list["update_frequency"])
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])

                _image_deleted = False
                       
                while not _image_deleted and _curr_tries < _max_tries :

                    _image_instance = self.get_images(obj_attr_list)                    

                    if not _image_instance :
                        _image_deleted = True
                    else :
                        sleep(_wait)
                        _curr_tries += 1
                        
            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg
        
    @trace
    def wait_until_transaction(self, obj_attr_list) :
        '''
        TBD
        '''
        _wait = int(obj_attr_list["update_frequency"])
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])

        _active_transaction = True

        while _active_transaction and _curr_tries < _max_tries :
            
            _instance = self.get_instances(obj_attr_list, "vm", \
                                   obj_attr_list["cloud_vm_name"])
                        
            if _instance :
                if "activeTransaction" in _instance :
                    sleep(_wait)
                    _curr_tries += 1
                else :
                    _active_transaction = False
            else :
                _active_transaction = False
                
        return _instance
