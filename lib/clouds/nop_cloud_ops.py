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

    NullOpCloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time
from random import choice

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.process_management import ProcessManagement
from lib.auxiliary.data_ops import str2dic, dic2str, DataOpsException
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

class NopCmds(CommonCloudFunctions) :
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
        self.expid = expid
        self.additional_rc_contents = ''        

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench NoOpCloud"

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}) :
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
                _msg = self.get_description() + " connection to failed: " + _fmsg
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

            self.connect(access, credentials, vmc_name, vm_defaults)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_defaults, vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it"
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
    def check_images(self, vmc_name, vm_templates, vmc_defaults, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')
  
        _map_name_to_id = {}
        _map_uuid_to_name = {}
        
        _registered_imageid_list = []
        if True :
            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid != "to_replace" :
                    if not self.is_cloud_image_uuid(_imageid) :
                        if _imageid in _map_name_to_id :
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                        else :
                            _map_name_to_id[_imageid] = _imageid
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
    
                        if _map_name_to_id[_imageid] not in _registered_imageid_list :
                            _registered_imageid_list.append(_map_name_to_id[_imageid])  
                    else :
                        if _imageid not in _registered_imageid_list :
                            _registered_imageid_list.append(_imageid)

        _map_name_to_id["baseimg"] = self.generate_random_uuid("baseimg")
        _map_uuid_to_name[self.generate_random_uuid("baseimg")] = "baseimg"

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_uuid_to_name, vm_defaults)

        if "images_uuid2name" not in vmc_defaults :
            vmc_defaults["images_uuid2name"] = dic2str(_map_uuid_to_name)

        if "images_name2uuid" not in vmc_defaults :            
            vmc_defaults["images_name2uuid"] = dic2str(_map_name_to_id)
                
        return _detected_imageids

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        obj_attr_list["initial_hosts"] = obj_attr_list["initial_hosts"].split(',')
        obj_attr_list["host_count"] = len(obj_attr_list["initial_hosts"])
    
        for _host_n in range(0, obj_attr_list["host_count"]) :
            _host_uuid = self.generate_random_uuid()
            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]

            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], \
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(obj_attr_list["initial_hosts"][_host_n], True)                

            obj_attr_list["host_list"][_host_uuid]["name"] = "host_"  + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["cloud_vm_uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
            obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"
            obj_attr_list["host_list"][_host_uuid]["cores"] = 16
            obj_attr_list["host_list"][_host_uuid]["memory"] = 131072
            obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
            obj_attr_list["host_list"][_host_uuid]["simulated"] = False
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

        obj_attr_list["initial_hosts"] = ','.join(obj_attr_list["initial_hosts"])

        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _status = 0
            
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

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]

            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["cloud_hostname"], False)
            
            obj_attr_list["cloud_ip"].replace("undefined", "undefined_" + str(obj_attr_list["counter"])) 

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()

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
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _status = 100
            _nr_instances = "NA"
            _fmsg = "An error has occurred, but no error message was captured"                        
            _nr_instances = self.osci.count_object(obj_attr_list["cloud_name"], "VM", "RESERVATIONS")

        except Exception as e :
            _status = 23
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
        if "cloud_ip" in obj_attr_list and obj_attr_list["cloud_ip"] != "undefined" :
            obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]
            obj_attr_list["run_cloud_ip"] = obj_attr_list["cloud_ip"]
        else :
            _status = 1181
            _msg = "For " + self.get_description() + ", the IP address of each VM has to be" 
            _msg += " supplied on the \"vmattach\" (e.g., \"vmattach <role>"
            _msg += " [optional parametes] cloud_ip=X.Y.Z.W)."
            cberr(_msg)
            raise CldOpsException(_msg, _status)

        obj_attr_list["cloud_hostname"] = "vm_" + obj_attr_list["cloud_ip"].replace('.','_')
        
        return True

    @trace
    def get_instances(self, obj_attr_list) :
        '''
        TBD
        '''
        return True
    
    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])
                
            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                
                obj_attr_list["boot_volume_imageid1"] = obj_attr_list["imageid1"]                
                if obj_attr_list["imageid1"] in _map_uuid_to_name :
                    obj_attr_list["imageid1"] = _map_uuid_to_name[obj_attr_list["imageid1"]]
                    _status = 0                    
                else :
                    _fmsg = "image does not exist"
                    _status = 1817                    
            else :
                if obj_attr_list["imageid1"] in _map_name_to_uuid :
                    obj_attr_list["boot_volume_imageid1"] = _map_name_to_uuid[obj_attr_list["imageid1"]]
                    _status = 0                    
                else :
                    _fmsg = "image does not exist"
                    _status = 1817
#                    obj_attr_list["boot_volume_imageid1"] = self.generate_random_uuid(obj_attr_list["imageid1"])
            
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
        if self.get_instances(obj_attr_list) :
            return True
        else :
            return False
        
    @trace    
    def is_vm_ready(self, obj_attr_list) :

        if self.is_vm_running(obj_attr_list) :
            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
        return False

    @trace
    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''
        _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)

        _host_list = _vmc_attr_list["hosts"].split(',')

        _host_uuid = choice(_host_list)
        _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, _host_uuid, False)
        obj_attr_list["host_name"] = _host_attr_list["cloud_hostname"]
        obj_attr_list["host_cloud_ip"] = _host_attr_list["cloud_ip"]

        return True

    def vvcreate(self, obj_attr_list) :
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
    
                obj_attr_list["cloud_vv_uuid"] = "NOT SUPPORTED"

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

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "not supported" and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :    
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

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()

            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)

            obj_attr_list["vcpus"] = "NA"
            obj_attr_list["vmemory"] = "NA" 
            obj_attr_list["vstorage"] = "NA"
            obj_attr_list["vnics"] = "NA"
            obj_attr_list["size"] = "NA"
            obj_attr_list["class"] = "NA"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vm_placement(obj_attr_list)

            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)

            self.vvcreate(obj_attr_list)

            self.pre_vmcreate_process(obj_attr_list)            

            self.take_action_if_requested("VM", obj_attr_list, "provision_started")
 
            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                
                _status = 916

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

            self.common_messages("VM", obj_attr_list, "destroying", 0, '')

            if obj_attr_list["cloud_ip"] != "undefined" and obj_attr_list["role"] != "check" :
    
                _proc_man = ProcessManagement(username = obj_attr_list["login"], \
                                              cloud_name = obj_attr_list["cloud_name"], \
                                              hostname = obj_attr_list["cloud_ip"], \
                                              priv_key = obj_attr_list["identity"])
    
                _cmd = "~/cb_cleanup.sh; rm ~/cb_*"  
    
                _msg = "Shutting down CloudBench Load Manager/Metric Aggregator on "
                _msg += "VM \"" + obj_attr_list["name"] + "\" by executing the " 
                _msg += "command \"" + _cmd + "\""
                cbdebug(_msg, True)

                _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)

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

            _time_mark_crs = int(time())
            
            if obj_attr_list["captured_image_name"] == "auto" :
                obj_attr_list["captured_image_name"] = obj_attr_list["name"] + "_at_" + str(_time_mark_crs)
            
            obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]
                      
            self.common_messages("VM", obj_attr_list, "capturing", 0, '')

            _img_uuid = self.generate_random_uuid(obj_attr_list["captured_image_name"])
            _img_name = obj_attr_list["captured_image_name"]
            
            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])

            _map_uuid_to_name[_img_uuid] = _img_name
            _map_name_to_uuid[_img_name] = _img_uuid
            
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              obj_attr_list["vmc"], \
                                              False, \
                                              "images_uuid2name", \
                                              dic2str(_map_uuid_to_name), \
                                              False)

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              obj_attr_list["vmc"], \
                                              False, \
                                              "images_name2uuid", \
                                              dic2str(_map_name_to_uuid), \
                                              False)
            
            _time_mark_crc = int(time())
            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
            
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
        
    @trace        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''        
        return 0, "NOT SUPPORTED"
      

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
            _img_name = obj_attr_list["name"]

            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", True, obj_attr_list["vmc_name"], False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])                

            if _img_name in _map_name_to_uuid :
                _img_uuid = _map_name_to_uuid[_img_name]
                obj_attr_list["boot_volume_imageid1"] = _img_uuid
                del _map_name_to_uuid[_img_name]
                del _map_uuid_to_name[_img_uuid]
                
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              _vmc_attr_list["uuid"], \
                                              False, \
                                              "images_uuid2name", \
                                              dic2str(_map_uuid_to_name), \
                                              False)

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "VMC", \
                                              _vmc_attr_list["uuid"], \
                                              False, \
                                              "images_name2uuid", \
                                              dic2str(_map_name_to_uuid), \
                                              False)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg        
