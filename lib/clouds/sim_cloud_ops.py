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

    SimCloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint
from uuid import uuid5, NAMESPACE_DNS

from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from ..auxiliary.data_ops import str2dic, DataOpsException
from ..remote.network_functions import Nethashget 
from shared_functions import CldOpsException, CommonCloudFunctions 

class SimCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.ft_supported = False

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench SimCloud."
    
    @trace
    def test_vmc_connection(self, vmc_hn, access, credentials, extra_info) :
        '''
        TBD
        '''
        return True

    def generate_random_ip_address(self) :
        '''
        TBD
        '''
        _ip = ".".join(str(randint(1, 255)) for _octect in range(4))
        return _ip
        
    def generate_random_mac_address(self) :
        '''
        TBD
        '''
        _mac_template = [ 0x00, 0x16, 0x3e, randint(0x00, 0x7f), randint(0x00, 0xff), randint(0x00, 0xff) ]
        _mac = ':'.join(map(lambda x: "%02x" % x, _mac_template))
        return _mac

    def generate_random_uuid(self) :
        _uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,1000000000000000000)))).upper()
        return _uuid

    @trace
    def get_virtual_hardware_config(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _vhw_config = {}
            _vhw_config["pico32"] = "vcpus:1,vmemory:192,vstorage:2048,vnics:1"
            _vhw_config["nano32"] = "vcpus:1,vmemory:512,vstorage:61440,vnics:1"
            _vhw_config["micro32"] = "vcpus:1,vmemory:1024,vstorage:61440,vnics:1"
            _vhw_config["copper32"] = "vcpus:1,vmemory:2048,vstorage:61440,vnics:1"
            _vhw_config["bronze32"] = "vcpus:1,vmemory:2048,vstorage:179200,vnics:1"
            _vhw_config["iron32"] = "vcpus:2,vmemory:2048,vstorage:179200,vnics:1"
            _vhw_config["silver32"] = "vcpus:4,vmemory:2048,vstorage:358400,vnics:1"
            _vhw_config["gold32"] = "vcpus:8,vmemory:4096,vstorage:358400,vnics:1"
            _vhw_config["cooper64"] = "vcpus:2,vmemory:4096,vstorage:61440,vnics:1"
            _vhw_config["bronze64"]  = "vcpus:2,vmemory:4096,vstorage:870400,vnics:1"
            _vhw_config["silver64"] = "vcpus:4,vmemory:8192,vstorage:1048576,vnics:1"
            _vhw_config["gold64"] = "vcpus:8,vmemory:16384,vstorage:1048576,vnics:1"
            _vhw_config["platinum64"] = "vcpus:16,vmemory:16384,vstorage:2097152,vnics:1"
    
            _vhw_config["premium"] = "cpu_upper:1000,cpu_lower:1000,memory_upper:100,memory_lower:100"
            _vhw_config["standard"] = "cpu_upper:1000,cpu_lower:500,memory_upper:100,memory_lower:50"
            _vhw_config["value"] = "cpu_upper:-1,cpu_lower:0,memory_upper:100,memory_lower:0"
            
            if "size" not in obj_attr_list :
                obj_attr_list["size"] = "micro32"

            if "class" not in obj_attr_list :
                obj_attr_list["class"] = "standard"
            
            _curr_vhw_config = _vhw_config[obj_attr_list["size"]] + ',' + _vhw_config[obj_attr_list["class"]]
            _curr_vhw_config = str2dic(_curr_vhw_config)
            obj_attr_list.update(_curr_vhw_config)
            _status = 0
        
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "virtual hardware configuration parameters could not be "
                _msg += "determined:" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "virtual hardware configuration parameters were "
                _msg += "successfully determined."
                cbdebug(_msg)
                return True

    def discover_hosts(self, obj_attr_list, vmc_extra_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_uuid"]
        obj_attr_list["hosts"] = _host_uuid
        obj_attr_list["host_count"] = 1
        obj_attr_list["host_list"] = {}
        obj_attr_list["host_list"][_host_uuid] = vmc_extra_attr_list
        obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
        obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
        obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = obj_attr_list["cloud_ip"]
        obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
        obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
        obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = obj_attr_list["cloud_hostname"]
        obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["cloud_hostname"]
        obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
        obj_attr_list["host_list"][_host_uuid]["cloud_uuid"] = obj_attr_list["cloud_uuid"]
        obj_attr_list["host_list"][_host_uuid]["uuid"] = obj_attr_list["cloud_uuid"]
        obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
        obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"
        obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
        obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
        obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
        obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
        _time_mark_prc = int(time())
        obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start
        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _msg = "Ok"
            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\""
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

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = self.generate_random_ip_address()

            _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
            _fmsg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."

            obj_attr_list["cloud_uuid"] = self.generate_random_uuid()

            obj_attr_list["arrival"] = int(time())
            
            if obj_attr_list["discover_hosts"].lower() == "true" :
                _vmc_extra_attr_list = {}
                _vmc_extra_attr_list["cores"] = 4
                self.discover_hosts(obj_attr_list, _vmc_extra_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
            
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
            
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
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on SimCloud \"" + obj_attr_list["cloud_name"]
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
                _msg += "on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list):
        '''
        TBD
        '''
        obj_attr_list["last_known_state"] = "running with ip assigned"
        obj_attr_list["cloud_ip"] = self.generate_random_ip_address()
        obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_uuid"] + ".simcloud.com"
        return True        

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        return True
    
    def is_vm_ready(self, obj_attr_list) :
        
        if self.is_vm_running(obj_attr_list) :
            
            self.pause_after_provision_if_requested(obj_attr_list)
            
            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
    
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_uuid"] = "cb-" + obj_attr_list["username"] + '-' + "vm_" + obj_attr_list["name"].split("_")[1] + '-' + obj_attr_list["role"]
            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_uuid"]
            
            obj_attr_list["cloud_mac"] = self.generate_random_mac_address()
            self.get_virtual_hardware_config(obj_attr_list)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            if obj_attr_list["role"] != "willfail" :
                True
            else :
                _status = 7778
                _msg = "Failed to create VM image"
                raise CldOpsException(_msg, _status)
 
            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
            
            obj_attr_list["host_name"] = obj_attr_list["vmc_name"]
            obj_attr_list["host_cloud_ip"] = obj_attr_list["vmc_cloud_ip"]

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            obj_attr_list["arrival"] = int(time())

            obj_attr_list["mgt_005_file_transfer"] = "0"

            obj_attr_list["mgt_006_application_start"] = "0"
            
            _msg = "Fake sending files to " + obj_attr_list["name"] + " (" + obj_attr_list["cloud_ip"] + ")..."
            cbdebug(_msg, True)

            _status = 0

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
            if "lvt_cnt" in obj_attr_list :
                del obj_attr_list["lvt_cnt"]
                
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation was rolled back)"
                cberr(_msg, True)
                
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                self.vmdestroy(obj_attr_list)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

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
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on SimCloud \"" + obj_attr_list["cloud_name"]
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

            _time_mark_crs = int(time())
            obj_attr_list["captured_image_name"] = obj_attr_list["name"] + "_at_" + str(_time_mark_crs)
            
            obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]
                      
            _msg = "Waiting for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
            _msg += "\"..."
            cbdebug(_msg, True)
            
            sleep(1.0)
            
            _time_mark_crc = int(time())
            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs

            _msg = "VM " + obj_attr_list["name"] + " capture request completed."
            cbdebug(_msg)

            _msg = "VM capture is not implemented for \"SimClouds\""
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
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]

            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = \
                _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate completed."
            cbdebug(_msg)
            sleep(5)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not have its runstate changed "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "had its runstate successfully "
                _msg += "changed on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            for _vm in obj_attr_list["vms"].split(',') :
                if _vm.count("faildb2") :
                    _fmsg = "Forced failure during AI definition"

            if _fmsg == "Forced failure during AI definition" :
                _status = 181
            else :
                _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on SimCloud \"" + obj_attr_list["cloud_name"]
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
                _msg += " on SimCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on SimCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg
