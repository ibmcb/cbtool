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

    NullOpCloud Object Operations Library

    @author: Marcio A. Silva
'''
from time import time, sleep
from random import randint
from uuid import uuid5, NAMESPACE_DNS

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.process_management import ProcessManagement
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

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

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench NoOpCloud."
    
    @trace
    def test_vmc_connection(self, vmc_hn, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        return True

    def generate_random_uuid(self) :
        _uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,1000000000000000000)))).upper()
        return _uuid

    def get_ip_from_hostname(self, obj_attr_list) :
        try :
            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["cloud_hostname"])
        except :
            obj_attr_list["cloud_ip"] = "undefined_" + str(obj_attr_list["counter"])

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''
        _auto_name = False
        if len(obj_attr_list["initial_hosts"]) < 2 :
            _auto_name = True
            obj_attr_list["host_count"] = int(obj_attr_list["hosts_per_vmc"])
        else :
            obj_attr_list["initial_hosts"] = obj_attr_list["initial_hosts"].split(',')
            obj_attr_list["host_count"] = len(obj_attr_list["initial_hosts"])
    
        for _host_n in range(0, obj_attr_list["host_count"]) :
            _host_uuid = self.generate_random_uuid()
            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
#            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = self.generate_random_ip_address()
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            if _auto_name :
                obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = "simhost" + obj_attr_list["name"][-1] + str(_host_n)
            else :
                obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = obj_attr_list["initial_hosts"][_host_n]

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
            obj_attr_list["host_list"][_host_uuid]["simulated"] = "True"
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
                _msg += "on NullOpCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\""
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
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])            

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]

            self.get_ip_from_hostname(obj_attr_list)

            _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
            _fmsg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\"."

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

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on NullOpCloud \"" + obj_attr_list["cloud_name"]
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
                _msg += "on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on NullOpCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        return True
    
    def is_vm_ready(self, obj_attr_list) :

        obj_attr_list["last_known_state"] = "running with ip assigned"
        return True
    
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid()

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] 
            obj_attr_list["cloud_vm_name"] += '-' + "vm_" 
            obj_attr_list["cloud_vm_name"] += obj_attr_list["name"].split("_")[1] 
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]  

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
                        
            obj_attr_list["cloud_mac"] = "NA"
            obj_attr_list["vcpus"] = "NA"
            obj_attr_list["vmemory"] = "NA" 
            obj_attr_list["vstorage"] = "NA"
            obj_attr_list["vnics"] = "NA"
            obj_attr_list["size"] = "NA"
            obj_attr_list["class"] = "NA"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["host_name"] = "NA"

            if "cloud_ip" in obj_attr_list and obj_attr_list["cloud_ip"] != "undefined" :
                obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]
                obj_attr_list["run_cloud_ip"] = obj_attr_list["cloud_ip"]
            else :
                _status = 1181
                _msg = "For NullOp Clouds, the IP address of each VM has to be" 
                _msg += " supplied on the \"vmattach\" (e.g., \"vmattach <role>"
                _msg += " [optional parametes] cloud_ip=X.Y.Z.W)."
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            obj_attr_list["cloud_hostname"] = "vm_" + obj_attr_list["cloud_ip"].replace('.','_')

            if "meta_tags" in obj_attr_list :
                if obj_attr_list["meta_tags"] != "empty" and \
                obj_attr_list["meta_tags"].count(':') and \
                obj_attr_list["meta_tags"].count(',') :
                    obj_attr_list["meta_tags"] = str2dic(obj_attr_list["meta_tags"])
                else :
                    obj_attr_list["meta_tags"] = "empty"
            else :
                obj_attr_list["meta_tags"] = "empty"
 
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")
 
            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                
                _status = 916

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
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation was rolled back)"
                cberr(_msg, True)
                
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                self.vmdestroy(obj_attr_list)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\"."
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
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

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
                _msg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully "
                _msg += "destroyed on NullOpCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list, current_step) :
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
                _msg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on NullOpCloud \"" + obj_attr_list["cloud_name"]
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

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on NullOpCloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on NullOpCloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

