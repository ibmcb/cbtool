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
    Created on Jan 3, 2012

    EC2 Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint
from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, is_number, DataOpsException
from lib.remote.network_functions import hostname2ip

from .shared_functions import CldOpsException, CommonCloudFunctions 

from boto.ec2 import regions
from boto import exception as AWSException 
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping


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
        self.additional_rc_contents = ''        
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
                
        except AWSException as obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as msg :
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

            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)

            _security_group_found = self.check_security_group(vmc_name, security_group_name)

            _detected_imageids = self.check_images(vmc_name, vm_templates, vm_defaults)

            if not (_key_pair_found and _security_group_found) :
                _fmsg += ": Check the previous errors, fix it (using " + self.get_description() + "'s web"
                _fmsg += " GUI (AWS Console) or ec2-* CLI utilities"
                _status = 1178
                raise CldOpsException(_fmsg, _status) 

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
    def check_images(self, vmc_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _map_name_to_id = {}
        _map_id_to_name = {}
        
        _wanted_images = []
        for _vm_role in list(vm_templates.keys()) :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if _imageid not in _wanted_images and _imageid != "to_replace" :
                if self.is_cloud_image_uuid(_imageid) :
                    _wanted_images.append(_imageid)
                else :
                    if _imageid in _map_name_to_id and _map_name_to_id[_imageid] != _imageid :
                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    else :                        
                        _x_img = self.ec2conn.get_all_images(filters = {"name": _imageid + '*'})
                        if _x_img:
                            _map_name_to_id[_imageid] = _x_img[0].id    
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                            _wanted_images.append(_x_img[0].id)
                        else :
                            _map_name_to_id[_imageid] = _imageid
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])

                        _map_id_to_name[_map_name_to_id[_imageid]] = _imageid
                        
        _registered_image_list = self.ec2conn.get_all_images(image_ids=_wanted_images)
                        
        _registered_imageid_list = []

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image.id)

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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"])

            _pre_existing_instances = False
            _reservations = self.ec2conn.get_all_instances()

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _running_instances = True
            while _running_instances :
                _running_instances = False
                for _reservation in _reservations :
                    for _instance in _reservation.instances :
                        if "Name" in _instance.tags :
                            if _instance.tags['Name'].count("cb-" + obj_attr_list["username"] + "-" + obj_attr_list["cloud_name"]) and _instance.state == 'running' :
                                cbdebug("Terminating instance: " + _instance.tags['Name'], True)
                                _instance.terminate()
                                _running_instances = True
                sleep(int(obj_attr_list["update_frequency"]))

            sleep(int(obj_attr_list["update_frequency"]) * 5)

            self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')

            _volumes = self.ec2conn.get_all_volumes()

            if len(_volumes) :
                for unattachedvol in _volumes :
                    if "Name" in unattachedvol.tags and unattachedvol.tags['Name'].count("cb-" + obj_attr_list["username"] + "-" + obj_attr_list["cloud_name"]) and unattachedvol.status == 'available' :
                        cbdebug("Terminating volume: " + unattachedvol.tags['Name'], True)
                        unattachedvol.delete()
                    else:
                        _msg = unattachedvol.id + ' ' + unattachedvol.status
                        _msg += "... still attached and could not be deleted"
                        cbdebug(_msg)

            _status = 0

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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

            _x, _y, _hostname = self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"])

            obj_attr_list["cloud_hostname"] = _hostname + "_" + obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = gethostbyname(_hostname)
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

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

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

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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

                _reservations = self.ec2conn.get_all_instances()

                for _reservation in _reservations :
                    for _instance in _reservation.instances :
                        if "Name" in _instance.tags :
                            if _instance.tags['Name'].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                                if str(_instance.update()).count("running") :
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

        for _key_pair in self.ec2conn.get_all_key_pairs() :
            registered_key_pairs[_key_pair.name] = _key_pair.fingerprint + "-NA"

            #self.ec2conn.delete_key_pair(key_name)
            
        return True

    @trace
    def get_security_groups(self, vmc_name, security_group_name, registered_security_groups) :
        '''
        TBD
        '''

        for _security_group in self.ec2conn.get_all_security_groups() :
            registered_security_groups.append(_security_group.name)

        return True

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
            obj_attr_list["public_cloud_ip"] = _public_ip_address

            if obj_attr_list["run_netname"] == "private" :
                obj_attr_list["cloud_hostname"] = _private_hostname
                obj_attr_list["run_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["cloud_hostname"] = _public_hostname
                obj_attr_list["run_cloud_ip"] = _public_ip_address

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

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
                    if str(obj_attr_list["cloud_vm_uuid"]).lower() != "none" :
                        _reservations = self.ec2conn.get_all_instances(obj_attr_list["cloud_vm_uuid"])
                        if _reservations :
                            _instance = _reservations[0].instances[0]
                            obj_attr_list["instance_obj"] = _instance
                            return _instance
                        
                if identifier == "name" :
                    _reservations = self.ec2conn.get_all_instances()
                    _instances = [i for r in _reservations for i in r.instances]
                    if _instance :
                        for _instance in _instances :
                            if "Name" in _instance.tags :
                                if _instance.tags["Name"] == obj_attr_list["cloud_vm_name"] :
                                    obj_attr_list["instance_obj"] = _instance
                                    return _instance
                return False
            
            else :
                _instance = []

                if identifier == "vvuid" :
                    if obj_attr_list["cloud_vv_uuid"].lower() != "none" :
                        _instance = self.ec2conn.get_all_volumes(volume_ids = [obj_attr_list["cloud_vv_uuid"]])

                if identifier == "vmuuid" :
                    if str(obj_attr_list["cloud_vm_uuid"]).lower() != "none" :
                        _instance = self.ec2conn.get_all_volumes(filters={'attachment.instance-id': obj_attr_list["cloud_vm_uuid"]})

                if len(_instance) :    
                    _volume=_instance[0]
                    return _volume
                else :
                    return False
                    
        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)
        
        except Exception as msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
            raise CldOpsException(_fmsg, _status)

    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _candidate_images = None
            
            _fmsg = "An error has occurred, but no error message was captured"

            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                _candidate_images = self.ec2conn.get_all_images(image_ids = [ obj_attr_list["imageid1"] ])                    
            else :
                _candidate_images = self.ec2conn.get_all_images(filters = {"name": obj_attr_list["imageid1"] })

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg +=  self.get_description()

            if _candidate_images :
                obj_attr_list["imageid1"] = _candidate_images[0].name
                obj_attr_list["boot_volume_imageid1"] = _candidate_images[0].id 
                _status = 0
            
        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

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
        self.ec2conn.import_key_pair(key_name, (key_type + ' ' + key_contents).encode('utf-8'))

        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        
        if len(imageid) > 4 :
            if imageid[0:4] == "ami-" :
                if is_number(imageid[5:], True) :
                    return True
                    
        return False

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

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)
        
        except Exception as msg :
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
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_vv_instance"] = False

            if "cloud_vv_type" not in obj_attr_list :
                obj_attr_list["cloud_vv_type"] = "standard"
            
            if "cloud_vv" in obj_attr_list and str(obj_attr_list["cloud_vv"]).lower() != "false" :

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)
    
                obj_attr_list["last_known_state"] = "about to send volume create request"
                if "instance_obj" in obj_attr_list :
                    _location = obj_attr_list["instance_obj"].placement
                else :
                    _location = obj_attr_list["vmc_name"] + 'a'
                    
                if obj_attr_list["cloud_vv_iops"] != "0":
                    obj_attr_list["cloud_vv_instance"] = self.ec2conn.create_volume(
                            int(obj_attr_list["cloud_vv"]),
                            _location,
                            volume_type = obj_attr_list["cloud_vv_type"],
                            iops = obj_attr_list["cloud_vv_iops"])
                else:
                    obj_attr_list["cloud_vv_instance"] = self.ec2conn.create_volume(
                            int(obj_attr_list["cloud_vv"]),
                            _location,
                            volume_type = obj_attr_list["cloud_vv_type"])

                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vv_instance"].add_tags({'Name': obj_attr_list["cloud_vv_name"]})

                obj_attr_list["cloud_vv_uuid"] = '{0}'.format(obj_attr_list["cloud_vv_instance"].id)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
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

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :

                _instance = self.get_instances(obj_attr_list, "vv", identifier)
    
                if _instance :
                    self.common_messages("VV", obj_attr_list, "destroying", 0, '')
    
                    _volume_detached = False
    
                    while not _volume_detached and _curr_tries < _max_tries :
    
                        _status = _instance.status
    
                        if _status == 'available' :
                            cbdebug("Deleting...", True)
                            _instance.delete()                 
                            cbdebug("Deleted.", True)
                            _volume_detached = True
    
                        else :
                            _msg = " Volume previously attached to \"" 
                            _msg += obj_attr_list["name"] + "\""
                            _msg += " (cloud-assigned uuid " 
                            _msg += identifier + ") status "
                            _msg += "is still \"" + _status + "\". "
                            _msg += "Will wait " + str(_wait)
                            _msg += " seconds and try again."
                            cbdebug(_msg, True)
    
                            sleep(_wait)
                            _instance = self.get_instances(obj_attr_list, "vv", identifier)
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
                    
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

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
            _reservation = False
            
            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)

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

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"
            
            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)

            obj_attr_list["config_drive"] = False

            # We need the instance placemente information before creating the actual volume
            #self.vvcreate(obj_attr_list)

            if "cloud_rv_type" not in obj_attr_list :
                obj_attr_list["cloud_rv_type"] = "standard"

            _bdm = BlockDeviceMapping()
            '''
            Options:
            gp2 (== ssd)
            io1 (also ssd)
            st1 (not sure)
            sc1 (cold?)
            standard (spinners)
            '''

            if obj_attr_list["cloud_rv_iops"] == "0":
                _iops = None
            else:
                _iops = obj_attr_list["cloud_rv_iops"]

            if "cloud_rv" in obj_attr_list and obj_attr_list["cloud_rv"] != "0":
                _size = obj_attr_list["cloud_rv"]
            else:
                _size = None

            _bdm['/dev/sda1'] = BlockDeviceType(volume_type = obj_attr_list["cloud_rv_type"], delete_on_termination=True, iops=_iops, size=_size)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            self.pre_vmcreate_process(obj_attr_list)
            _reservation = self.ec2conn.run_instances(image_id = obj_attr_list["boot_volume_imageid1"], \
                                                      instance_type = obj_attr_list["size"], \
                                                      key_name = obj_attr_list["key_name"], \
                                                      user_data = self.populate_cloudconfig(obj_attr_list),
                                                      block_device_map = _bdm,
                                                      security_groups = _security_groups)

            if _reservation :

                sleep(int(obj_attr_list["update_frequency"]))
                
                _instance = _reservation.instances[0]
        
                _instance.add_tag("Name", obj_attr_list["cloud_vm_name"])            
                
                obj_attr_list["cloud_vm_uuid"] = '{0}'.format(_instance.id)
                obj_attr_list["instance_obj"] = _instance

                self.vvcreate(obj_attr_list)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                if obj_attr_list["cloud_vv_instance"] :
                    self.common_messages("VV", obj_attr_list, "attaching", _status, _fmsg)
                    obj_attr_list["cloud_vv_instance"].attach(obj_attr_list["cloud_vm_uuid"], "/dev/xvdc")
                
                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = "unknown"

                self.take_action_if_requested("VM", obj_attr_list, "provision_finished")
                    
                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status and _reservation is not False :
                cbdebug("Error after VM creation. Cleanup...", True)
                self.vmdestroy_repeat(obj_attr_list)

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

            if not self.ec2conn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0
                
            _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")

            if _instance :

                self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                _instance.terminate()

                sleep(_wait)

                while self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries :
                    sleep(_wait)
                    _curr_tries += 1                    
            else :
                True

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs            

            _status, _fmsg = self.vvdestroy(obj_attr_list, "vvuid")

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :

            if "instance_obj" in obj_attr_list : 
                del obj_attr_list["instance_obj"]            
            
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

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                _captured_imageid = self.ec2conn.create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = self.ec2conn.get_all_images(image_ids = [ _captured_imageid ])

                    if len(_image_instance)  :

                        if _image_instance[0].state == "available" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    sleep(_wait)             
                    _curr_tries += 1

                if _curr_tries > _max_tries  :
                    _status = 1077
                    _fmsg = "" + obj_attr_list["name"] + ""
                    _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _fmsg +=  "could not be captured after " + str(_max_tries * _wait) + " seconds.... "
                else :
                    _status = 0

            else :
                _fmsg = "This instance does not exist"
                _status = 1098
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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
                         obj_attr_list["vmc_name"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

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

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            if not self.ec2conn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                _candidate_images = self.ec2conn.get_all_images(image_ids= [ obj_attr_list["imageid1"] ])                    
            else :
                _candidate_images = self.ec2conn.get_all_images(filters = {"name": obj_attr_list["imageid1"] })

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += self.get_description()

            if _candidate_images :
                obj_attr_list["imageid1"] = _candidate_images[0].name
                obj_attr_list["boot_volume_imageid1"] = _candidate_images[0].id
                self.ec2conn.deregister_image(obj_attr_list["boot_volume_imageid1"], delete_snapshot=True)

                _wait = int(obj_attr_list["update_frequency"])
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])

                _image_deleted = False                
                while not _image_deleted and _curr_tries < _max_tries :

                    _candidate_images = self.ec2conn.get_all_images(image_ids= [ obj_attr_list["boot_volume_imageid1"] ])                    

                    if not len(_candidate_images) :
                        _image_deleted = True
                    else :
                        sleep(_wait)
                        _curr_tries += 1
                        
            _status = 0

        except AWSException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg
