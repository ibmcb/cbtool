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

from time import time, sleep
import threading, xmlrpclib, re

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.hotplug_rem_ops import HotplugMgdConn
from shared_functions import CldOpsException, CommonCloudFunctions 

class FTCException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status) :
        '''
        TBD
        '''
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg
        
# List of exceptions that are allowed.  Only exceptions listed here will be reconstructed
# from an xmlrpclib.Fault instance.
allowed_errors = [FTCException]

error_pat = re.compile('(?P<exception>[^;]*);(?P<msg>[^;]*);(?P<status>.*$)')

class ExceptionUnmarshaller (xmlrpclib.Unmarshaller) :
    '''
    TBD
    '''
    def close(self):
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

def ftc_error_check(func) :
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
        except FTCException, obj :
            raise CldOpsException(func.__name__ + " failed: " + obj.msg, obj.status)

    return wrapped

class FTCServiceClient (xmlrpclib.ServerProxy) :
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
        setattr(self, "_ServerProxy__request", ftc_error_check(self._ServerProxy__request))

class FtcCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci, expid) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.ft_supported = True
        self.ftcconn = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Cloudbench FTCloud."

    @trace
    def connect(self, webservice_url) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _orig_Method = xmlrpclib._Method
            
            '''
            XML-RPC doesn't support keyword arguments,
            so we have to do it ourselves
            '''
            class KeywordArgMethod(_orig_Method):     
                def __call__(self, *args, **kwargs):
                    args = list(args) 
                    if kwargs:
                        args.append(("kwargs", kwargs))
                    return _orig_Method.__call__(self, *args)
            
            xmlrpclib._Method = KeywordArgMethod

            self.ftcconn = FTCServiceClient(webservice_url)
            _status = 0
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "FTC connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                cbdebug("FTC connection successful.")
    
    @trace
    def test_vmc_connection(self, vmc_hn, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        self.connect(access)
        self.ftcconn.test(vmc_hn)

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_uuid"]
        obj_attr_list["hosts"] = _host_uuid
        obj_attr_list["host_count"] = 1
        obj_attr_list["host_list"] = {}
        obj_attr_list["host_list"][_host_uuid] = obj_attr_list["hostextra"] 
        obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
        obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
        obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = obj_attr_list["cloud_ip"]
        obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
        obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
        obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = obj_attr_list["cloud_hostname"]
        obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["cloud_hostname"]
        obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
        obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
        obj_attr_list["host_list"][_host_uuid]["alternate_interface"] = "default"
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
        
        self.populate_interface(obj_attr_list)
        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        self.ftcconn.node_cleanup(obj_attr_list["name"], "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"], disk_format = obj_attr_list["disk_format"])
        _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned up "
        _msg += "on FTCloud \"" + obj_attr_list["cloud_name"] + "\""
        cbdebug(_msg)
        return 0, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        '''
        TBD
        '''
        _time_mark_prs = int(time())

        obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])            

        if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
            self.vmccleanup(obj_attr_list)

        obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
        
        _fmsg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
        _fmsg += " on TAcloud \"" + obj_attr_list["cloud_name"] + "\"."

        self.connect(obj_attr_list["access"])
        _status, _fmsg, info = self.ftcconn.node_register(obj_attr_list["name"])
        obj_attr_list.update(info)
        obj_attr_list["arrival"] = int(time())
        

        if obj_attr_list["discover_hosts"].lower() == "true" :
            self.discover_hosts(obj_attr_list, _time_mark_prs)
        else :
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
            obj_attr_list["host_count"] = "NA"
        
        _time_mark_prc = int(time())
        obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
        
        _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
        _msg += "registered on FTCloud \"" + obj_attr_list["cloud_name"] + "\"."
        cbdebug(_msg, True)
        return 0, _msg

    @trace
    def vmcunregister(self, obj_attr_list) :
        '''
        TBD
        '''
        _time_mark_drs = int(time())

        if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
            obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

        obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])    
    
        if "cleanup_on_detach" in obj_attr_list and obj_attr_list["cleanup_on_detach"] == "True" :
            self.vmccleanup(obj_attr_list)

        _time_mark_prc = int(time())
        obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_prc - _time_mark_drs
        
        _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
        _msg += "unregistered on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg, True)
        return 0, _msg

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        _status, _fmsg, ip = self.ftcconn.get_ip_address(obj_attr_list["cloud_mac"])
        if ip is None :
            cbdebug("ip address not ready for mac " + obj_attr_list["cloud_mac"])
            return False

        obj_attr_list["cloud_ip"] = ip
        return True
        
    @trace
    def is_vm_running(self, obj_attr_list) :
        '''
        TBD
        '''
        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "is_domain_active", obj_attr_list)
        return self.ftcconn.is_domain_active(**kwargs)

    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''
        if self.is_vm_running(obj_attr_list) :

            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")

            if self.get_ip_address(obj_attr_list) :
                cbdebug("VM " + obj_attr_list["name"] + " received IP: " + obj_attr_list["cloud_ip"])
                obj_attr_list["cloud_hostname"] = "cb-" + obj_attr_list["cloud_ip"].replace('.', '-')
                obj_attr_list["last_known_state"] = "running with ip assigned"
                obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
        return False

    def resize_to_configured_default(self, obj_attr_list) :
        '''
        TBD
        '''
        obj_attr_list["resource_description"] = { "cpu_nr" : int(obj_attr_list["vcpus_configured"])}
        self.vmresize_actual(obj_attr_list)
        obj_attr_list["resource_description"] = { "mem_hl" : str(int(obj_attr_list["vmemory_configured"]))}
        self.vmresize_actual(obj_attr_list)
        del obj_attr_list["resource_description"]

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        obj_attr_list["cloud_uuid"] = "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"] + '-' + "vm_" + obj_attr_list["name"].split("_")[1] + '-' + obj_attr_list["role"]
        obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_uuid"]
        obj_attr_list["host_name"] = obj_attr_list["vmc_name"]
        obj_attr_list["host_cloud_ip"] = obj_attr_list["vmc_cloud_ip"]

        self.connect(obj_attr_list["access"])

        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "run_instances", obj_attr_list)
        kwargs["imageids"] = []
        for _idx in range(1, int(obj_attr_list["imageids"]) + 1) :
            imageid = obj_attr_list["imageid" + str(_idx)]
            if obj_attr_list["disk_format"].lower() != "lvm" :
                imageid += "." + obj_attr_list["disk_format"]
            kwargs["imageids"].append(imageid)

        _status, _fmsg, result = self.ftcconn.run_instances(**kwargs)

        obj_attr_list.update(result)

        _time_mark_prs = int(time())
        obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])
            
        try :
            status = 100
            _fmsg = "unknown error"
            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
            # Restore to configured size
            if "configured_size" in obj_attr_list :
                self.resize_to_configured_default(obj_attr_list)
            status = 0
        except FTCException, obj :
            status = obj.status
            _fmsg = "FTC Exception: " + obj.msg
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
        except KeyboardInterrupt :
            status = 42 
            _fmsg = "CTRL-C interrupt: " + obj.msg
        except Exception, obj :
            status = 43
            _fmsg = str(obj)
        finally :
            if status :
                self.vmdestroy(obj_attr_list)
                raise CldOpsException("FTC Exception: " + _fmsg, status)

        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
        _msg += "was successfully created"
        _msg += " on FTCloud \"" + obj_attr_list["cloud_name"] + "\"."
        cbdebug(_msg)
        return 0, _msg

    @trace        
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _time_mark_drs = int(time())
        
        if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
            obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
            
        obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
            _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])
        
        self.connect(obj_attr_list["access"])

        _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)

        storage_keys = []
        for _idx in range(1, int(obj_attr_list["imageids"]) + 1) :
            _pool_key = "poolbase" + str(_idx)
            if _pool_key in obj_attr_list :
                storage_keys.append(obj_attr_list[_pool_key])

        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "destroy_instances", obj_attr_list)
        self.ftcconn.destroy_instances(storage_keys, **kwargs)

        _time_mark_drc = int(time())
        obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
            _time_mark_drc - _time_mark_drs
            
        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
        _msg += "was successfully "
        _msg += "destroyed on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
        return 0, _msg

    @trace
    def vmresize_actual(self, obj_attr_list) :
        '''
        TBD
        '''
        cbdebug("VM " + obj_attr_list["name"] + " resize request sent.", True)

        _vg = ValueGeneration(self.pid)
        tag = obj_attr_list["cloud_uuid"]
        desc = obj_attr_list["resource_description"]
        hypervisor_ip = obj_attr_list["host_cloud_ip"]

        if not self.is_vm_running(obj_attr_list) :
            return 0, "VM is not running"

        cbdebug("Getting resource state for Guest " + tag)
        _status, _fmsg, _guest_info = self.ftcconn.get_domain_full_info(tag, hypervisor_ip)
        
        try :
            if "cpu_nr" in desc :
                _msg = "Set the number of CPUs for Guest " + tag
                _msg = "(" + obj_attr_list["cloud_ip"] + ")."
                cbdebug(_msg)
        
                _hpg_cnt = HotplugMgdConn(self.pid, obj_attr_list["cloud_ip"], "root", obj_attr_list["identity"])
                _active_cpus = 0
                _cpu_list = _hpg_cnt.get_cpus_state()
                for _cpu_number, _cpu_state in enumerate(_cpu_list) :
                    if _cpu_state == '1' :
                        _active_cpus += 1
                _hpg_cnt.set_active_cpus(desc["cpu_nr"])
                _msg = "CPU number for Guest " + tag
                _msg += " (" + obj_attr_list["cloud_ip"] + ") set to " + str(desc["cpu_nr"]) 
                _msg += " from " + str(_active_cpus) + '.'
                _xmsg = _msg
                cbdebug(_msg, True)
                
                del desc["cpu_nr"]

            if "cpu_sl" in desc :
                cbdebug("Setting CPU Soft Limit for Guest " + tag)
                
                _cpu_sl = _vg.value_suffix(desc["cpu_sl"], False)
                
                self.ftcconn.set_domain_cpu(tag, "cpu_shares", str(_cpu_sl), hypervisor_ip)
                _msg = "CPU Soft Limit for Guest \"" + obj_attr_list["cloud_uuid"]
                _msg += "\" successfully set to " + str(_cpu_sl) + " from "
                _msg += str(_guest_info["vcpus_soft_limit"]) + '.'
                cbdebug(_msg, True)
                del desc["cpu_sl"]
                    

            if "cpu_hl" in desc :
                _msg = "Setting CPU Hard Limit for Guest \"" + obj_attr_list["cloud_uuid"]
                _msg += "\"."
                cbdebug(_msg)
                
                _cpu_hl = int(float(desc["cpu_hl"]) * \
                    float(_guest_info["vcpus_period"]))

                self.ftcconn.set_domain_cpu(tag, "vcpu_quota", str(_cpu_hl), hypervisor_ip)
                _msg = "CPU Hard Limit for Guest " + tag 
                _msg += " successfully set to " + str(desc["cpu_hl"])
                _msg += " from " + str(_guest_info["vcpus_hard_limit"]) + '.'
                cbdebug(_msg, True)
                del desc["cpu_hl"]

            if "mem_sl" in desc :
                cbdebug("Setting MEMORY Soft Limit for Guest " + tag)

                _mem_sl = _vg.value_suffix(desc["mem_sl"], True)
                cbdebug("Resource Control Not implemented", True)
                del desc["mem_sl"]

            if "mem_hl" in desc :
                cbinfo("Setting MEMORY Hard Limit for Guest " + tag)
                _mem_hl = _vg.value_suffix(desc["mem_hl"], True)

                self.ftcconn.set_domain_memory(tag, "current_memory", str(_mem_hl * 1024), hypervisor_ip)
                _msg = "MEMORY Hard Limit (virtio balloon) for Guest " + tag 
                _msg += " successfully set to " + str(_mem_hl)
                _msg += " KB from " + str(_guest_info["current_memory"]) + "KB ."
                cbdebug(_msg, True)
                del desc["mem_hl"]
        except ValueGeneration.ValueGenerationException, obj :
            raise CldOpsException("resize failure: " + obj.msg, obj.status)

        except HotplugMgdConn.HotplugMgdConnException, obj :
            raise CldOpsException("resize failure: " + obj.msg, obj.status)
            
        for resource in desc.keys() :
            return 420, "No such resource to resize: " + resource

        return 0, "Success"

    @trace        
    def vmresize(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])

        _time_mark_crs = int(time())            
        obj_attr_list["mgt_302_resize_request_sent"] = _time_mark_crs - obj_attr_list["mgt_301_resize_request_originated"]

        _msg = "Sending a resize request for "  + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)

        self.vmresize_actual(obj_attr_list)
        _time_mark_crc = int(time())
        obj_attr_list["mgt_303_resize_request_completed"] = _time_mark_crc - _time_mark_crs

        cbdebug("VM " + obj_attr_list["name"] + " resize request completed.")

        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
        _msg += "was successfully "
        _msg += "resized on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
        return 0, _msg
    
    @trace        
    def vmmigrate(self, obj_attr_list) :
        self.connect(obj_attr_list["access"])
        operation = obj_attr_list["operation"]
        _time_mark_crs = int(time())            
        obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]

        _msg = "Sending a " + operation + " request for "  + obj_attr_list["name"]
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)

        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "migrate", obj_attr_list)
        _status, _msg, _result = self.ftcconn.migrate(**kwargs)

        _time_mark_crc = int(time())
        obj_attr_list["mgt_503_" + operation + "_request_completed"] = _time_mark_crc - _time_mark_crs

        cbdebug("VM " + obj_attr_list["name"] + " " + operation + " request completed.")

        if not _status :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "was successfully "
            _msg += operation + "ed on FTCloud \"" + obj_attr_list["cloud_name"]
            _msg += "\"."
            cbdebug(_msg)
        return _status, _msg

    @trace        
    def vmrunstate(self, obj_attr_list) :
        _ts = obj_attr_list["target_state"]
        _cs = obj_attr_list["current_state"]

        self.connect(obj_attr_list["access"])

        if "mgt_201_runstate_request_originated" in obj_attr_list :
            _time_mark_rrs = int(time())
            obj_attr_list["mgt_202_runstate_request_sent"] = \
                _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]

        _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)

        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "suspend", obj_attr_list)

        if _ts == "fail" :
            self.ftcconn.suspend(**kwargs)
        elif _ts == "save" :
            self.ftcconn.save(**kwargs)
        elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
            self.ftcconn.resume(**kwargs)
        elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
            self.ftcconn.restore(**kwargs)
            if "configured_size" in obj_attr_list :
                # For some reason, restored VMs don't maintain their previous
                # size properties. Go figure.
                self.resize_to_configured_default(obj_attr_list)
        
        _time_mark_rrc = int(time())
        obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs
            
        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
        _msg += "had its runstate successfully "
        _msg += "changed on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
        return 0, _msg

    @trace
    def vm_fixpause(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.ftcconn, "resume", obj_attr_list)
        self.ftcconn.resume(**kwargs)
        _msg = "VM " + obj_attr_list["name"] + " was resumed."
        cbdebug(_msg, True)
        return 0, _msg

    @trace        
    def aidefine(self, obj_attr_list) :
        '''
        TBD
        '''
        self.take_action_if_requested("AI", obj_attr_list, "all_vms_booted")
        _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
        _msg += "defined on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
        return 0, _msg

    @trace        
    def aiundefine(self, obj_attr_list) :
        '''
        TBD
        '''
        _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
        _msg += "undefined on FTCloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg, True)
        return 0, _msg
