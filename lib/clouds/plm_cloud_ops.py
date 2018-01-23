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

PLM Object Operations Library

@author: Marcio A. Silva, Michael R. Hines
'''
from time import time, sleep
from sys import path

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.hotplug_rem_ops import HotplugMgdConn
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

class PlmCmds(CommonCloudFunctions) :
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
        self.plmconn = False
        self.expid = expid
        self.ft_supported = False

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Parallel Libvirt Manager"

    @trace
    def connect(self, api_url, extra_param1, extra_parm2) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _orig_Method = xmlrpclib._Method
            
            class KeywordArgMethod(_orig_Method):     
                def __call__(self, *args, **kwargs):
                    args = list(args) 
                    if kwargs:
                        args.append(("kwargs", kwargs))
                    return _orig_Method.__call__(self, *args)
            
            xmlrpclib._Method = KeywordArgMethod

            self.plmconn = plmServiceClient("http://" + api_url)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "PLM connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "PLM connection successful."
                cbdebug(_msg)
                return _status, _msg, api_url

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

            _status = 0

        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

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

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            # if not self.plmconn : Fails with the following error: 
            #<Fault 1: '<type \'exceptions.Exception\'>:method "__nonzero__" is not supported'>
            # Instead of checking for a value, we instead check of the type of
            # self.plm.conn is boolean. Weird, I know :-).
            if type(self.plmconn) is type(False) :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])
                
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            _status, _msg, _host_list = self.plmconn.nodes_describe("computenode", "all")

            obj_attr_list["host_count"] = len(_host_list)
    
            for _host_uuid in _host_list.keys() :

                obj_attr_list["host_list"][_host_uuid] = {}
                obj_attr_list["hosts"] += _host_uuid + ','
                obj_attr_list["host_list"][_host_uuid].update(_host_list[_host_uuid])
                obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
                obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
                obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
                obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
                obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
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
    
            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

            self.additional_host_discovery (obj_attr_list)
            self.populate_interface(obj_attr_list)
            
            _status = 0

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "HOSTS belonging to VMC " + obj_attr_list["name"] + " could not be "
                _msg += "discovered on PLM cluster \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = str(obj_attr_list["host_count"]) + "HOSTS belonging to "
                _msg += "VMC " + obj_attr_list["name"] + " were successfully "
                _msg += "discovered on PLM cluster \"" + obj_attr_list["cloud_name"]
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

            if type(self.plmconn) is type(False) :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

            _tag = "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]

            _status, _msg, _info = self.plmconn.group_cleanup(obj_attr_list["name"], _tag, obj_attr_list["username"])

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on PLM cluster \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on PLM cluster \"" + obj_attr_list["cloud_name"] + "\""
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

            if not _status :
                if type(self.plmconn) is type(False) :
                    self.connect(obj_attr_list["access"], \
                                 obj_attr_list["credentials"], \
                                 obj_attr_list["name"])

                _status, _msg, _info = self.plmconn.group_register(obj_attr_list["name"])
                _network_address = _info["computenodes"].split(',')[0]
                obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(_network_address)
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

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on PLM cluster \"" + obj_attr_list["cloud_name"]
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
            
            if type(self.plmconn) is type(False) :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])            

            _status, _msg, _info = self.plmconn.group_unregister(obj_attr_list["name"])
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_prc - _time_mark_drs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on PLM cluster \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    @trace    
    def get_ssh_keys(self, key_name, key_contents, key_fingerprint, registered_key_pairs, internal, connection) :
        '''
        TBD
        '''

        registered_key_pairs[key_name] = key_fingerprint + "-NA"

        return True

    @trace            
    def create_ssh_key(self, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        return True

    def is_vm_running(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 

            _status, _msg, _info = self.plmconn.instances_describe(obj_attr_list["cloud_vm_name"])

            if not _status :
                if len(_info) :
                    if obj_attr_list["uuid"] in _info :
                        if _info[obj_attr_list["uuid"]]["state"] == "running" :
                            return True
                    else :
                        return False
                else :
                    return False

        except PLMException, obj:
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
        if self.is_vm_running(obj_attr_list) :

            _status, _msg, _info = self.plmconn.instances_describe(obj_attr_list["cloud_vm_name"])

            if not _status :

                if _info[obj_attr_list["uuid"]]["cloud_ip"] != "NA" :
                    obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                    obj_attr_list["run_cloud_ip"] = _info[obj_attr_list["uuid"]]["cloud_ip"]
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["run_cloud_ip"]
                    # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
                    obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
                    return True
                else :
                    obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"
                    return False
            else :
                obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"
                return False                
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

        except Exception, e :
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
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _instance = False
          
            obj_attr_list["tag"] = "cb-" + obj_attr_list["username"]
            obj_attr_list["tag"] += '-' + obj_attr_list["cloud_name"]
            obj_attr_list["tag"] += '-' + "vm"
            obj_attr_list["tag"] += obj_attr_list["name"].split("_")[1]
            obj_attr_list["tag"] += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["tag"] += '-' + obj_attr_list["ai_name"]  

            obj_attr_list["tag"] = obj_attr_list["tag"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to PLM"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if type(self.plmconn) is type(False) :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])  

#            if self.is_vm_running(obj_attr_list) :
#                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
#                _msg += "\" is already running. It needs to be destroyed first."
#                _status = 187
#                cberr(_msg)
#                raise CldOpsException(_msg, _status)

            _msg = "Starting an instance on PLM, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" and "
            _msg += "size \"" + obj_attr_list["size"] + "\""
            _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
            cbdebug(_msg, True)

            _vm_dict = {}
            _vm_dict["root_disk_format"] = obj_attr_list["root_disk_format"]
            _vm_dict["imageids"] = []
            for _idx in range(1, int(obj_attr_list["imageids"]) + 1) :
                imageid = obj_attr_list["imageid" + str(_idx)]
                if _vm_dict["root_disk_format"] == "qcow2" :
                    _vm_dict["imageids"].append(imageid + ".raw")

            _vm_dict["group"] = obj_attr_list["vmc_name"]

            _vm_dict["userid"] = obj_attr_list["username"]
            _vm_dict["tag"] = obj_attr_list["tag"]
            _vm_dict["size"] = obj_attr_list["size"]

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            _status, _msg, _result = self.plmconn.instance_run(**_vm_dict)

            if not _status :
                del _result["state"]

                _name = obj_attr_list["name"]
                obj_attr_list.update(_result)
                obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_lvid"]
                obj_attr_list["name"] = _name

                sleep(int(obj_attr_list["update_frequency"]))

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

        except PLMException, obj:
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
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)

                if self.is_vm_running(obj_attr_list) :
                    self.vmdestroy(obj_attr_list)

                raise CldOpsException(_msg, _status)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on PLM cluster \"" + obj_attr_list["cloud_name"] + "\"."
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

            if type(self.plmconn) is type(False) :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"]) 
            
            _wait = int(obj_attr_list["update_frequency"])
            
            if self.is_vm_running(obj_attr_list) :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
            
                _vm_dict = {}
                _vm_dict["tag"] = obj_attr_list["cloud_lvid"]
                _status, _msg, _result = self.plmconn.instance_destroy(**_vm_dict)
                sleep(_wait)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
            else :
                True

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
             
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on PLM cluster \"" + obj_attr_list["cloud_name"]
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

            if not self.plmconn :
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
            
            if _ts == "fail" :
                _status, _msg, _info = self.plmconn.instance_alter_state(obj_attr_list["cloud_lvid"], "suspend")
            elif _ts == "save" :
                _status, _msg, _info = self.plmconn.instance_alter_state(obj_attr_list["cloud_lvid"], "save")
            elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                _status, _msg, _info = self.plmconn.instance_alter_state(obj_attr_list["cloud_lvid"], "resume")
            elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                _status, _msg, _info = self.plmconn.instance_alter_state(obj_attr_list["cloud_lvid"], "restore")
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except PLMException, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on PLM cluster"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\" :" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on PLM cluster"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\"."
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

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on PLM cluster \"" + obj_attr_list["cloud_name"]
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

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on PLM cluster \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on PLM cluster \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

class PLMException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
        
# List of exceptions that are allowed.  Only exceptions listed here will be reconstructed
# from an xmlrpclib.Fault instance.
allowed_errors = [PLMException]

error_pat = re.compile('(?P<exception>[^;]*);(?P<msg>[^;]*);(?P<status>.*$)')

class ExceptionUnmarshaller (xmlrpclib.Unmarshaller) :
    '''
    TBD
    '''
    def close(self) :
        '''
        TBD
        '''
        # return response tuple and target method
        if self._type is None or self._marks:
            raise xmlrpclib.ResponseError()
        if self._type == "fault":
            d = self._stack[0]
            m = error_pat.match(d['faultString'])
            if m:
                exception_name = m.group('exception')
                msg = m.group('msg')
                status = m.group('status')
                for exc in allowed_errors:
                    if exc.__name__ == exception_name:
                        raise exc(msg, status)

            # Fall through and just raise the fault
            raise xmlrpclib.Fault(**d)
        return tuple(self._stack)

class ExceptionTransport (xmlrpclib.Transport) :
    '''
    TBD
    '''
    def getparser (self) :
        '''
        TBD
        '''
        unmarshaller = ExceptionUnmarshaller()
        parser = xmlrpclib.ExpatParser(unmarshaller)
        return parser, unmarshaller

def plm_error_check(func) :
    '''
    TBD
    '''
    def wrapped(*args, **kwargs) :
        '''
        TBD
        '''
        try :
            _status = 100
            resp = func(*args, **kwargs)
            status = int(resp["status"])
            if status < 0 :
                raise CldOpsException(func.__name__ + " failed: " + resp["msg"], status)

            return status, resp["msg"], resp["result"]
        except PLMException, obj :
            raise CldOpsException(func.__name__ + " failed: " + obj.msg, obj.status)

    return wrapped

class plmServiceClient (xmlrpclib.ServerProxy) :
    '''
    TBD
    '''
    def __init__ (self, *args, **kwargs) :
        '''
        TBD
        '''
        # Supply our own transport
        kwargs['transport'] = ExceptionTransport()
        xmlrpclib.ServerProxy.__init__(self, *args, **kwargs)
        setattr(self, "_ServerProxy__request", plm_error_check(self._ServerProxy__request))
