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
    Created on Jan 3, 2012

    EC2 Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint
from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import hostname2ip

from shared_functions import CldOpsException, CommonCloudFunctions 

from boto.ec2 import regions
from boto import exception as AWSException 

class Ec2Cmds(CommonCloudFunctions) :
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
        self.ec2conn = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Amazon Elastic Compute Cloud"

    @trace
    def connect(self, access_key_id, secret_key, region = "us-east-1") :
        '''
        TBD
        '''
        try :
            _status = 100
            _region_list = regions(aws_access_key_id = access_key_id, \
                                   aws_secret_access_key = secret_key)

            _region_info = False
            for _idx in range(0,len(_region_list)) :
                if _region_list[_idx].name == region :
                    _region_info = _region_list[_idx]
                    _region_hostname = _region_info.endpoint
                    _msg = "Selected region is " + str(_region_info.name)
                    cbdebug(_msg)
                    break

            if _region_info :
                self.ec2conn = _region_info.connect(aws_access_key_id = \
                                                    access_key_id, \
                                                    aws_secret_access_key = \
                                                    secret_key)
                _status = 0
            else :
                _fmsg = "Unknown " + self.get_description() + " region (" + region + ")"
                
        except AWSException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, _region_hostname

    def check_images(self, vmc_name, vm_templates) :
        '''
        TBD
        '''
        _msg = "Checking if the imageids associated to each \"VM role\" are"
        _msg += " registered on VMC \"" + vmc_name + "\"...."
        cbdebug(_msg, True)

        _map_name_to_id = {}

        _wanted_images = []
        for _vm_role in vm_templates.keys() :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if _imageid not in _wanted_images and _imageid != "to_replace" :
                if self.is_cloud_image_uuid(_imageid) :
                    _wanted_images.append(_imageid)
                else :
                    if _imageid in _map_name_to_id :
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    else :                        
                        _x_img = self.ec2conn.get_all_images(filters = {"name": _imageid + '*'})
                        if _x_img:
                            _map_name_to_id[_imageid] = _x_img[0].id    
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                            _wanted_images.append(_x_img[0].id)
                        else :
                            _map_name_to_id[_imageid] = "ami-" + '0' + ''.join(["%s" % randint(0, 9) for num in range(0, 6)])
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                                                        
        _registered_image_list = self.ec2conn.get_all_images(image_ids=_wanted_images)
                        
        _registered_imageid_list = []

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image.id)

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list)

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
            self.connect(access, credentials, vmc_name)

            _key_pair_found = self.check_ssh_key(vmc_name, key_name, vm_defaults)

            _security_group_found = self.check_security_group(vmc_name, security_group_name)

            _detected_imageids = self.check_images(vmc_name, vm_templates)

            if not (_key_pair_found and _security_group_found) :
                _fmsg += ": Check the previous errors, fix it (using " + self.get_description() + "'s web"
                _fmsg += " GUI (AWS Console) or ec2-* CLI utilities"
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
                _msg = "VMC \"" + vmc_name + "\" did not pass the connection test.\n"
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC \"" + vmc_name + "\" was successfully tested.\n"
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"])

            _pre_existing_instances = False
            _reservations = self.ec2conn.get_all_instances()

            _running_instances = True
            while _running_instances :
                _running_instances = False
                for _reservation in _reservations :
                    for _instance in _reservation.instances :
                        if "Name" in _instance.tags :
                            if _instance.tags[u'Name'].count("cb-" + obj_attr_list["username"]) and _instance.state == u'running' :
                                _instance.terminate()
                                _running_instances = True
                sleep(int(obj_attr_list["update_frequency"]))

            _msg = "All running instances on the VMC " + obj_attr_list["name"]
            _msg += " were terminated"
            cbdebug(_msg)

            sleep(int(obj_attr_list["update_frequency"])*5)

            _msg = "Now all EBS volumes belonging to the just terminated "
            _msg += "instances on the VMC " + obj_attr_list["name"] + " will "
            _msg += "also be removed."
            cbdebug(_msg)
            
            _volumes = self.ec2conn.get_all_volumes()

            if len(_volumes) :
                for unattachedvol in _volumes :
                    if unattachedvol.status == 'available' :
                        _msg = unattachedvol.id + ' ' + unattachedvol.status
                        _msg += "... was deleted"
                        cbdebug(_msg)
                        unattachedvol.delete()
                    else:
                        _msg = unattachedvol.id + ' ' + unattachedvol.status
                        _msg += "... still attached and could not be deleted"
                        cbdebug(_msg)
            else :
                _msg = "No volumes to remove"
                cbdebug(_msg)

            _status = 0

        except AWSException, obj :
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
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\""
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

            _x, _y, _hostname = self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"])

            obj_attr_list["cloud_hostname"] = _hostname
            obj_attr_list["cloud_ip"] = gethostbyname(_hostname)
            obj_attr_list["arrival"] = int(time())

            if obj_attr_list["discover_hosts"].lower() == "true" :
                _msg = "Host discovery for VMC \"" + obj_attr_list["name"]
                _msg += "\" request, but " + self.get_description() + " does not"
                _msg += " allow it. Ignoring for now....."
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

        except AWSException, obj :
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
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
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

        except AWSException, obj :
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
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _private_hostname = '{0}'.format(obj_attr_list["instance_obj"].private_dns_name)
            _private_ip_address = '{0}'.format(obj_attr_list["instance_obj"].private_ip_address)
            _public_hostname = '{0}'.format(obj_attr_list["instance_obj"].public_dns_name)
            _public_hostname, _public_ip_address = hostname2ip(_public_hostname)
            if obj_attr_list["run_netname"] == "private" :
                obj_attr_list["cloud_hostname"] = _private_hostname
                obj_attr_list["run_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["cloud_hostname"] = _public_hostname
                obj_attr_list["run_cloud_ip"] = _public_ip_address

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            if str(obj_attr_list["use_vpn_ip"]).lower() == "true" and str(obj_attr_list["vpn_only"]).lower() == "true" :
                assert(self.get_attr_from_pending(obj_attr_list))

                if "cloud_init_vpn" not in obj_attr_list :
                    cbdebug("Instance VPN address not yet available.")
                    return False
                cbdebug("Found VPN IP: " + obj_attr_list["cloud_init_vpn"])
                obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_init_vpn"]
            else :
                if obj_attr_list["prov_netname"] == "private" :
                    obj_attr_list["prov_cloud_ip"] = _private_ip_address
                else :
                    obj_attr_list["prov_cloud_ip"]  = _public_ip_address

            return True
        except :
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all") :
        '''
        TBD
        '''
        
        try :
            if obj_type == "vm" :
                if identifier == "vmuuid" :
                    if "cloud_vm_uuid" in obj_attr_list and obj_attr_list["cloud_vm_uuid"] != "NA" :
                        _reservations = self.ec2conn.get_all_instances(obj_attr_list["cloud_vm_uuid"])
                        if _reservations :
                            _instance = _reservations[0].instances[0]
                            obj_attr_list["instance_obj"] = _instance
                            return _instance
                        
                if identifier == "name" :
                    _reservations = self.ec2conn.get_all_instances()
                    _instances = [i for r in _reservations for i in r.instances]
                    for _instance in _instances :
                        if "Name" in _instance.tags :
                            if _instance.tags["Name"] == obj_attr_list["cloud_vm_name"] :
                                obj_attr_list["instance_obj"] = _instance
                                return _instance
                return False
            
            else :
                _instance = []

                if identifier == "vvuid" :
                    if "cloud_vv_uuid" in obj_attr_list and obj_attr_list["cloud_vv_uuid"].lower() != "none" :
                        _instance = self.ec2conn.get_all_volumes(volume_ids = [obj_attr_list["cloud_vv_uuid"]])

                if identifier == "vmuuid" :
                    if "cloud_vm_uuid" in obj_attr_list and obj_attr_list["cloud_vm_uuid"].lower() != "none" :
                        _instance = self.ec2conn.get_all_volumes(filters={'attachment.instance-id': obj_attr_list["cloud_vm_uuid"]})

                if len(_instance) :    
                    _volume=_instance[0]
                else :
                    return False
                    
        except AWSException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)
        
        except Exception, msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
            raise CldOpsException(_fmsg, _status)

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

            if "instance_obj" not in obj_attr_list :
                _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")
            else :
                _instance = obj_attr_list["instance_obj"]

            if _instance :
                _instance_state = _instance.update()
            else :
                _instance_state = "non-existent"
            
            if _instance_state == "running" :                
                return True
            else :
                return False

        except AWSException, obj :
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

    @trace
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"


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

                _instance =  self.ec2conn.create_volume(obj_attr_list["cloud_vv"], obj_attr_list["instance_obj"].placement)

                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vv_uuid"] = '{0}'.format(_instance.id)

                _msg = "Attaching the newly created Volume \"" 
                _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                cbdebug(_msg)

                _instance.attach(obj_attr_list["cloud_vm_uuid"], "/dev/xvdb")

            else :
                obj_attr_list["cloud_vv_uuid"] = "none"

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException, obj :
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
                _msg += " on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            else :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            _instance = self.get_instances(obj_attr_list, "vv", identifier)

            if _instance :
                _msg = "Sending a destruction request for the Volume" 
                _msg += " previously attached to \"" 
                _msg += obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + identifier + ")...."
                cbdebug(_msg, True)

                _volume_detached = False

                while not _volume_detached and _curr_tries < _max_tries :

                    _status = _instance.status

                    if _status == 'available' :
                        _instance.delete()                 
                        _volume_detached = True

                    else :
                        _msg = " Volume previously attached to \"" 
                        _msg += obj_attr_list["name"] + "\""
                        _msg += " (cloud-assigned uuid " 
                        _msg += identifier + ") status "
                        _msg += "is still \"" + _status + "\". "
                        _msg += "Will wait " + str(_wait)
                        _msg += " seconds and try again."
                        cbdebug(_msg)

                        sleep(_wait)
                        _curr_tries += 1                           

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = " Volume previously attached to \"" 
                _fmsg += obj_attr_list["name"] + "\""
                _fmsg += " (cloud-assigned uuid " 
                _fmsg += identifier + ") "
                _fmsg +=  "could not be destroyed after " + str(_max_tries * _wait) + " seconds.... "
                cberr(_msg)
            else :
                _status = 0
                    
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException, obj :
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
                _msg += " on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
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
            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if not self.ec2conn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            # "Security groups" must be a list
            _security_groups = []
            _security_groups.append(obj_attr_list["security_groups"])

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Starting an instance on " + self.get_description() + ", using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" and size \""
            _msg += obj_attr_list["size"] + "\" on VMC \""
            _msg += obj_attr_list["vmc_name"] + "\" (with security groups \""
            _msg += str(_security_groups) + "\")."
            cbdebug(_msg, True)

            _reservation = self.ec2conn.run_instances(image_id = obj_attr_list["imageid1"], \
                                                      instance_type = obj_attr_list["size"], \
                                                      key_name = obj_attr_list["key_name"], \
                                                      user_data = self.populate_cloudconfig(obj_attr_list),
                                                      security_groups = _security_groups)

            if _reservation :

                sleep(int(obj_attr_list["update_frequency"]))
                
                _instance = _reservation.instances[0]
        
                _instance.add_tag("Name", obj_attr_list["cloud_vm_name"])            
                
                obj_attr_list["cloud_vm_uuid"] = '{0}'.format(_instance.id)
                obj_attr_list["instance_obj"] = _instance

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                _status, _fmsg = self.vvcreate(obj_attr_list)
                          
                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = "unknown"

                self.take_action_if_requested("VM", obj_attr_list, "provision_finished")

                if "instance_obj" in obj_attr_list : 
                    del obj_attr_list["instance_obj"]
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

        except AWSException, obj :
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
                _msg += "on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
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
                _msg += "created on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
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

            if not self.ec2conn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")
            
            if _instance :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                _instance.terminate()

                sleep(_wait)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
            else :
                True
                        
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs            
             
            _status, _fmsg = self.vvdestroy(obj_attr_list, "vvuid")
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
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

            if not self.ec2conn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

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

                _captured_imageid = self.ec2conn.create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = self.ec2conn.get_all_images(_captured_imageid)

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
                _msg += " on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on Elastic Compute Cloud \"" + obj_attr_list["cloud_name"]
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
                         obj_attr_list["vmc_name"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")

            if _instance :
                if _ts == "fail" :
                    _instance.stop()
                elif _ts == "save" :
                    _instance.stop()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.start()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.start()
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on Elastic Compute Cloud \"" 
                _msg += obj_attr_list["cloud_name"] + "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on Elastic Compute Cloud \"" 
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
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
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
            self.take_action_if_requested("AI", obj_attr_list, current_step)            
            _status = 0

        except Exception, msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg