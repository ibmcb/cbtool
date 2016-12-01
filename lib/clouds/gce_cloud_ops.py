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
    Created on Oct 20, 2015

    GCE Object Operations Library

    @author: Marcio A. Silva
'''
import httplib2

from time import time, sleep

from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.ssh_ops import get_ssh_key
from lib.remote.network_functions import hostname2ip

from shared_functions import CldOpsException, CommonCloudFunctions 

from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build 
import googleapiclient.errors as GCEException

class GceCmds(CommonCloudFunctions) :
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
        self.gceconn = False
        self.instances_project= None
        self.images_project = None
        self.zone = None
        self.instance_info = None
        self.expid = expid
        self.http_conn = {}

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Google Compute Engine"

    @trace
    def connect(self, project, secret_key, zone = "us-east1-b", http_conn_id = None) :
        '''
        TBD
        '''
        try :
            _status = 100
            if not self.instances_project :
                project = project.split(',')
                if len(project) == 2 :
                    self.images_project, self.instances_project = project
                else :
                    self.instances_project = project[0]
                    self.images_project = self.instances_project

            _credentials = GoogleCredentials.get_application_default()
                                    
            self.gceconn = build('compute', 'v1', credentials=_credentials)

            _http_conn_id = "common"
            if http_conn_id :
                _http_conn_id = http_conn_id

            if _http_conn_id not in self.http_conn :  
                self.http_conn[_http_conn_id] = _credentials.authorize(http = httplib2.Http())
                        
            _zone_list = self.gceconn.zones().list(project=self.instances_project).execute()["items"]            

            _zone_info = False
            for _idx in range(0,len(_zone_list)) :
                if _zone_list[_idx]["description"] == zone :
                    _zone_info = _zone_list[_idx]
                    _zone_hostname = _zone_info["region"]
                    _msg = "Selected zone is " + str(_zone_info["description"])
                    cbdebug(_msg)
                    break

            if _zone_info :
                self.zone = zone
                _status = 0
            else :
                _fmsg = "Unknown GCE zone (" + zone + ")"
                
        except GCEException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = "GCE connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :

                _msg = "GCE connection successful."
                cbdebug(_msg)
                return _status, _msg, _zone_hostname

    def check_ssh_key(self, vmc_name, key_name, vm_defaults, http_conn_id) :
        '''
        TBD
        '''

        _key_pair_found = False      
        
        if not key_name :
            _key_pair_found = True
        else :
            _msg = "Checking if the ssh key pair \"" + key_name + "\" is created"
            _msg += " on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _pub_key_fn = vm_defaults["credentials_dir"] + '/'
            _pub_key_fn += vm_defaults["ssh_key_name"] + ".pub"

            _key_type, _key_contents, _key_fingerprint = get_ssh_key(_pub_key_fn, "common")

            if not _key_contents :
                _fmsg = _key_type 
                cberr(_fmsg, True)
                return False

            vm_defaults["ssh_key_contents"] = _key_contents
            vm_defaults["ssh_key_type"] = _key_type
            
            _keys_available = []
            _metadata = self.gceconn.projects().get(project=self.instances_project).execute(http = self.http_conn[http_conn_id])
            for _element in _metadata['commonInstanceMetadata']['items'] :
                if _element["key"] == "sshKeys" :
                    for _component in _element["value"].split('\n') :
                        _component = _component.split(' ')
                        if len(_component) == 3 :
                            _keys_available.append(_component)
                                                    
            _key_pair_found = False

            for _available_key_pair in _keys_available :
                _available_key_name = _available_key_pair[0].split(':')[0]

                if _available_key_name == key_name :
                    _msg = "A key named \"" + key_name + "\" was found "
                    _msg += "on VMC " + vmc_name + ". Checking if the key"
                    _msg += " contents are correct."
                    cbdebug(_msg)                    
                    _available_key_contents = _available_key_pair[1]
                    
                    if len(_available_key_contents) > 1 and len(_key_contents) > 1 :

                        if _available_key_contents == _key_contents :
                            _msg = "The contents of the key \"" + key_name
                            _msg += "\" on the VMC " + vmc_name + " and the"
                            _msg += " one present on directory \"" 
                            _msg += vm_defaults["credentials_dir"] + "\" ("
                            _msg += vm_defaults["ssh_key_name"] + ") are the same."
                            cbdebug(_msg)
                            _key_pair_found = True
                            break
                        else :
                            _msg = "The contents of the key \"" + key_name
                            _msg += "\" on the VMC " + vmc_name + " and the"
                            _msg += " one present on directory \"" 
                            _msg += vm_defaults["credentials_dir"] + "\" ("
                            _msg += vm_defaults["ssh_key_name"] + ") differ."
                            cbdebug(_msg)
                            break
                        
            _key_pair_found = True
            
            if not _key_pair_found :

                _msg = "ERROR: Please go to Google Developers Console -> Compute Engine"
                _msg += " -> Metadata and add the contents of the public key \""
                _msg += _pub_key_fn + "\" there..."
                cberr(_msg, True)
                                    
            return _key_pair_found
        
    def check_security_group(self,vmc_name, security_group_name) :
        '''
        TBD
        '''

        _security_group_name = False
        
        if security_group_name :

            _msg = "Checking if the security group \"" + security_group_name
            _msg += "\" is created on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _security_group_found = False
            for security_group in self.gceconn.get_all_security_groups() :
                if security_group.name == security_group_name :
                    _security_group_found = True

            if not _security_group_found :
                _msg = "ERROR! Please create the security group \"" 
                _msg += security_group_name + "\" in "
                _msg += "Google CE before proceeding."
                _fmsg = _msg
                cberr(_msg, True)
        else :
            _security_group_found = True

        return _security_group_found

    def check_images(self, vmc_name, vm_templates, http_conn_id) :
        '''
        TBD
        '''
        _msg = "Checking if the imageids associated to each \"VM role\" are"
        _msg += " registered on VMC " + vmc_name + " (project " + self.images_project
        _msg += ")...."
        cbdebug(_msg, True)

        _wanted_images = []
        for _vm_role in vm_templates.keys() :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if _imageid not in _wanted_images and _imageid != "to_replace" :
                _wanted_images.append(_imageid)

        _registered_image_list = self.gceconn.images().list(project=self.images_project).execute(http = self.http_conn[http_conn_id])["items"]
        _registered_imageid_list = []

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image["name"])

        _required_imageid_list = {}

        for _vm_role in vm_templates.keys() :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if _imageid != "to_replace" :
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
                _msg += "x WARNING Image id for VM roles \""
                _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                _msg += _imageid + "\" is NOT registered "
                _msg += "(attaching VMs with any of these roles will result in error).\n"

        if not len(_detected_imageids) :
            _msg = "WARNING! None of the image ids used by any VM \"role\" were detected"
            _msg += " in this GCE cloud! "            
            #_msg += "of the following images: " + ','.join(_undetected_imageids.keys())
            cbwarn(_msg, True)
        else :
            _msg = _msg.replace("yx",'')
            _msg = _msg.replace("x ","          ")
            _msg = _msg[:-2]
            if len(_msg) :
                cbdebug(_msg, True)    

        return _detected_imageids
        
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            self.connect(access, credentials, vmc_name, vmc_name)

            _key_pair_found = self.check_ssh_key(vmc_name, key_name, vm_defaults, vmc_name)
            #_security_group_found = self.check_security_group(vmc_name, security_group_name)
            _security_group_found = True
            _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_name)

            if not (_key_pair_found and _security_group_found) :
                _fmsg = ''                
                _fmsg += ": Check the previous errors, fix it (using GCE's web"
                _fmsg += " GUI (Google Developer's Console) or gcloud CLI utility"
                _status = 1178
                raise CldOpsException(_fmsg, _status) 

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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"], obj_attr_list["name"])

            _pre_existing_instances = False

            _running_instances = True

            while _running_instances :
                _running_instances = False

                _instance_list = self.get_instances({}, "vm", "all")                
                
                for _instance in _instance_list :

                    if _instance["name"].count("cb-" + obj_attr_list["username"]) and _instance["status"] == u'RUNNING' :
                        self.gceconn.instances().delete(project = self.instances_project, \
                                                        zone = self.zone, \
                                                        instance = _instance["name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                        _running_instances = True


                sleep(int(obj_attr_list["update_frequency"]))

            _msg = "All running instances on the VMC " + obj_attr_list["name"]
            _msg += " were terminated"
            cbdebug(_msg)

            sleep(int(obj_attr_list["update_frequency"])*5)

            _msg = "Now all volumes belonging to the just terminated "
            _msg += "instances on the VMC " + obj_attr_list["name"] + " will "
            _msg += "also be removed."
            cbdebug(_msg)
            
            _volume_list = self.get_instances({}, "vv", "all")

            if len(_volume_list) :
                for _volume in _volume_list :
                    if _volume["name"].count("cb-" + obj_attr_list["username"]) :
                        if not "users" in _volume :
                            _msg = _volume["id"] + " detached "
                            _msg += "... was deleted"
                            cbdebug(_msg)
                            self.gceconn.disks().delete(project = self.instances_project, zone = self.zone, disk = _volume["name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                        else:
                            _msg = _volume["id"] + ' '
                            _msg += "... still attached and could not be deleted"
                            cbdebug(_msg)
            else :
                _msg = "No volumes to remove"
                cbdebug(_msg)

            _status = 0

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\""
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
                _msg = "Removing all VMs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VMs names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)                
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            _x, _y, _hostname = self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"], obj_attr_list["name"])

            obj_attr_list["cloud_hostname"] = _hostname
            obj_attr_list["cloud_ip"] = gethostbyname(_hostname.split('/')[2])
            obj_attr_list["arrival"] = int(time())

            if obj_attr_list["discover_hosts"].lower() == "true" :
                _msg = "Host discovery for VMC \"" + obj_attr_list["name"]
                _msg += "\" request, but GCE does not allow it. Ignoring for now....."
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

            _status = 0

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
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

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :

            _private_ip_address = self.instance_info["networkInterfaces"][0]["networkIP"]
            _public_ip_address = self.instance_info["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
                       
            _public_hostname = obj_attr_list["cloud_vm_name"] + '.' + obj_attr_list["vmc_name"]
            _private_hostname = obj_attr_list["cloud_vm_name"] + '.' + obj_attr_list["vmc_name"]
                        
            if obj_attr_list["run_netname"] == "private" :
                obj_attr_list["cloud_hostname"] = _private_hostname
                obj_attr_list["run_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["cloud_hostname"] = _public_hostname
                obj_attr_list["run_cloud_ip"] = _public_ip_address

            if obj_attr_list["prov_netname"] == "private" :
                obj_attr_list["prov_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["prov_cloud_ip"]  = _public_ip_address

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
            
            return True
        except :
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all") :
        '''
        TBD
        '''

        _instances = []
        _fmsg = "Error while getting instances"
              
        try :
            if obj_type == "vm" :
                if identifier == "all" :
                    _instance_list = self.gceconn.instances().list(project = self.instances_project, \
                                                                   zone = self.zone).execute()
                                                                   
                else :
                    _instance_list = self.gceconn.instances().get(project = self.instances_project, \
                                                                   zone = self.zone, \
                                                                   instance = identifier).execute(http = self.http_conn[obj_attr_list["name"]])
           
            else :
                if identifier == "all" :
                    _instance_list = self.gceconn.disks().list(project = self.instances_project, \
                                                                   zone = self.zone).execute()
 
                else :
                    _instance_list = self.gceconn.disks().get(project = self.instances_project, \
                                                                   zone = self.zone, \
                                                                   disk = identifier).execute(http = self.http_conn[obj_attr_list["name"]])
                    
            if "items" in _instance_list :
                _instances = _instance_list["items"]

            elif "status" in _instance_list :
                _instances = _instance_list
                
            return _instances
        
        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)
        
        except Exception, _fmsg :
            return []

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :
                _instance_state = _instance["status"]
            else :
                _instance_state = "non-existent"
            
            if _instance_state == "RUNNING" :
                self.instance_info = _instance
                return True
            else :
                return False

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)
        
        except Exception, msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
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

    def wait_until_operation(self, obj_attr_list, opid) :
        '''
        TBD
        '''

        _msg = "Waiting for " + obj_attr_list["name"] + " operation to finish..."
        cbdebug(_msg, True)
    
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        sleep(_wait)
        
        while _curr_tries < _max_tries :
            _start_pooling = int(time())

            _op = self.gceconn.zoneOperations().get(project = self.instances_project, \
                                                           zone = self.zone, \
                                                           operation = opid["name"]).execute(http = self.http_conn[obj_attr_list["name"]])
            
            if _op['status'] == 'DONE':
                if 'error' in _op :
                    raise CldOpsException(_op["error"], 2001)

                if "cloud_vm_uuid" in obj_attr_list :
                    if obj_attr_list["cloud_vm_uuid"] == "NA" :
                        obj_attr_list["cloud_vm_uuid"] = _op["id"]

                return True
            else:
                sleep(_wait)
                _curr_tries += 1
                
        _fmsg = obj_attr_list["name"] + " operation did not finish after "
        _fmsg += str(_max_tries * _wait) + " seconds... "
        _fmsg += "Giving up."
        
        raise CldOpsException(_op["error"], 2001)        

    @trace
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_vv_uuid"] = "none"
            obj_attr_list["cloud_vv_name"] = "none"
            if "cloud_vv" in obj_attr_list :
    
                obj_attr_list["last_known_state"] = "about to send volume create request"
    
                obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vv_name"] += '-' + "vv"
                obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]            

                _msg = "Creating a volume, with size " 
                _msg += obj_attr_list["cloud_vv"] + " GB, on VMC \"" 
                _msg += obj_attr_list["vmc_name"] + "\""
                cbdebug(_msg, True)


                _config = {
                    'name': obj_attr_list["cloud_vv_name"], 
                    'description' : "used by " + obj_attr_list["cloud_vm_name"],
                    'sizeGb' : obj_attr_list["cloud_vv"],
                }

                _fmsg = _msg

                _operation = self.gceconn.disks().insert(project = self.instances_project, \
                                                         zone = self.zone, \
                                                         body = _config).execute(http = self.http_conn[obj_attr_list["name"]])

                if self.wait_until_operation(obj_attr_list, _operation) :
                    _instance =  self.get_instances(obj_attr_list, "vv", obj_attr_list["cloud_vv_name"])
                    
                    obj_attr_list["cloud_vv_uuid"] = _instance["id"]
                    obj_attr_list["cloud_vv_source"] = _instance["selfLink"]
                    
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEException, obj :
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
            if _status :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            else :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vvdestroy(self, obj_attr_list, identifier) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vv_name"])

            if _instance :
                _msg = "Sending a destruction request for the Volume" 
                _msg += " previously attached to \"" 
                _msg += obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + identifier + ")...."
                cbdebug(_msg, True)

                _operation = self.gceconn.disks().delete(project = self.instances_project, \
                                                             zone = self.zone, \
                                                             disk = obj_attr_list["cloud_vv_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)

            _status = 0
                    
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
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
            
            obj_attr_list["cloud_vm_uuid"] = "NA"
            _instance = False

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] 
            obj_attr_list["cloud_vm_name"] += '-' + "vm" + obj_attr_list["name"].split("_")[1] 
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to gce manager"
            obj_attr_list["project"] = self.instances_project

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            _status, _fmsg = self.vvcreate(obj_attr_list)

            # "Security groups" must be a list
            _security_groups = []
            _security_groups.append(obj_attr_list["security_groups"])

            if obj_attr_list["role"] == "check" :
                if obj_attr_list["imageid1"].count("ubuntu") :
                    _actual_project = "ubuntu-os-cloud"
                elif obj_attr_list["imageid1"].count("rhel") :                    
                    _actual_project = "rhel-cloud"            
                elif obj_attr_list["imageid1"].count("centos") :                    
                    _actual_project = "centos-cloud"            
            else :
                _actual_project = self.images_project
                                            
            _source_disk_image = "projects/" + _actual_project + "/global/images/" + obj_attr_list["imageid1"]
            _machine_type = "zones/" + obj_attr_list["vmc_name"] + "/machineTypes/" + obj_attr_list["size"]

            _config = {
                'name': obj_attr_list["cloud_vm_name"],
                'machineType': _machine_type,
        
                # Specify the boot disk and the image to use as a source.
                'disks': [
                    {
                        'boot': True,
                        'autoDelete': True,
                        'initializeParams': {
                            'sourceImage': _source_disk_image,
                        }
                    }
                ],
        
                # Specify a network interface with NAT to access the public
                # internet.
                'networkInterfaces': [{
                    'network': 'global/networks/default',
                    'accessConfigs': [
                        {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                    ]
                }],
        
                # Allow the instance to access cloud storage and logging.
                'serviceAccounts': [{
                    'email': 'default',
                    'scopes': [
                        'https://www.googleapis.com/auth/devstorage.read_write',
                        'https://www.googleapis.com/auth/logging.write'
                    ]
                }],
        
                # Metadata is readable from the instance and allows you to
                # pass configuration from deployment scripts to instances.
                'metadata': {
                    'items': [{
                        'key': 'expid',
                        'value': obj_attr_list["experiment_id"]
                    }, {
                        'key': 'use',
                        'value': "cloudbench"
                    }, {
                        'key': 'sshKeys',
                        'value': obj_attr_list["login"] + ':' + \
                        obj_attr_list["ssh_key_type"] + ' ' + \
                        obj_attr_list["ssh_key_contents"].strip('\n') + ' ' + \
                        obj_attr_list["ssh_key_name"].strip('\n') + "@orchestrator"
                    }]            
                }
            }


            if obj_attr_list["cloud_vv_uuid"] != "none":
                _msg = "Attaching the newly created Volume \"" 
                _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                cbdebug(_msg)
            
                _config["disks"].append({'boot': False, \
                                         "autoDelete" : True, \
                                         "source" : obj_attr_list["cloud_vv_source"]})

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Starting an instance on GCE (project \"" + self.instances_project
            _msg += "\"), using the imageid \"" + obj_attr_list["imageid1"] 
            _msg += "\" (project \"" + self.images_project + "\") and size \"" 
            _msg += obj_attr_list["size"] + "\" on VMC \""
            _msg += obj_attr_list["vmc_name"] + "\" (with security groups \""
            _msg += str(_security_groups) + "\")."
            cbdebug(_msg, True)

            sleep(float(obj_attr_list["name"].replace("vm_",'')) + 1.0)

            _operation = self.gceconn.instances().insert(project = self.instances_project, \
                                                         zone = self.zone, \
                                                         body = _config).execute(http = self.http_conn[obj_attr_list["name"]])
            
            if self.wait_until_operation(obj_attr_list, _operation) :

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = "unknown"

                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916

            else :
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                _status = 100

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            
            if "instance_obj" in obj_attr_list :
                del obj_attr_list["instance_obj"]
                
            if _status :

                _msg = "VM " + obj_attr_list["uuid"] + " could not be created "
                _msg += "on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)

                if "cloud_vm_uuid" in obj_attr_list :
                    if obj_attr_list["cloud_vm_uuid"] != "NA" :
                        obj_attr_list["mgt_deprovisioning_request_originated"] = int(time())
                        self.vmdestroy(obj_attr_list)
                else :
                    if _instance :
                        _instance.terminate()

                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
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

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                _operation = self.gceconn.instances().delete(project = self.instances_project, \
                                                             zone = self.zone, \
                                                             instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
            else :
                True

            _status, _fmsg = self.vvdestroy(obj_attr_list, "vvuid")
                        
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs            
             
            _status, _fmsg = self.vvdestroy(obj_attr_list, "vmuid")

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
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

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if not self.gceconn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])

            _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")

            if _instance :
                
                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent. "
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _captured_imageid = self.gceconn.create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = self.gceconn.get_all_images(_captured_imageid)

                    if len(_image_instance)  :
                        if _image_instance[0].state == "pending" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    _msg = "\"" + obj_attr_list["name"] + "\""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing capture. "
                    _msg += "Will wait " + str(_wait)
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    sleep(_wait)             
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

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be captured "
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
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
    
            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

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
                if _ts == "fail" :
                    _operation = self.gceconn.instances().stop(project = self.instances_project, \
                                                               zone = self.zone, \
                                                               instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                elif _ts == "save" :
                    _operation = self.gceconn.instances().stop(project = self.instances_project, \
                                                               zone = self.zone, \
                                                               instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                                                               
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _operation = self.gceconn.instances().start(project = self.instances_project, \
                                                                zone = self.zone, \
                                                                instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                                                                
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _operation = self.gceconn.instances().start(project = self.instances_project, \
                                                                zone = self.zone, \
                                                                instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on Compute Engine Cloud \"" 
                _msg += obj_attr_list["cloud_name"] + "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on Compute Engine Cloud \"" 
                _msg += obj_attr_list["cloud_name"] + "\"."
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

        except Exception, msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on GCE \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
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
            self.take_action_if_requested("AI", obj_attr_list, current_step)            
            _status = 0

        except Exception, msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on Compute Engine Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on Compute Engine Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
