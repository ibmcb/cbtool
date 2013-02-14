#!/usr/bin/env python
'''
Created on Aug 27, 2011

PLM Object OperationsLibrary

@author: Marcio A. Silva, Michael R. Hines
'''
from time import time
from socket import gethostbyname
from sys import path
import threading, xmlrpclib, re

path.append('/'.join(path[0].split('/')[0:-2]))
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.hotplug_rem_ops import HotplugMgdConn

class CldOpsException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg

class PlmCmds() :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci) :
        '''
        TBD
        '''
        self.pid = pid
        self.osci = osci
        self.plmconn = False
        self.ft_supported = True

    @trace
    def dic_to_rpc_kwargs(self, service, function_name, attrs) :
        '''
          A way to populate arguments of the remote function
          without manually digging through the dictionary to
          find all the variables. Just dump into the dict
          and it gets populated as an argument
        '''
        kwargs = {}
        status, fmsg, sig = service.get_signature(function_name)
        for var in sig : 
            if var in attrs and var != "self" and attrs[var] != None : 
                value = attrs[var]
                if isinstance(value, str) :
                    value = value.strip().lower()
                    if value == "" :
                        continue
                    if value == "true" :
                        value = True
                    elif value == "false" :
                        value = False

                kwargs[var] = value 

        # Keys that are common inputs to most API functions
        default_keys = {"cloud_lvid" : "tag", "vmc_cloud_ip" : "hypervisor_ip"}

        for key in default_keys.keys() :
            if key in attrs :
                kwargs[default_keys[key]] = attrs[key]
                
        return kwargs

    @trace
    def connect(self, webservice_url) :
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

            self.plmconn = plmServiceClient("http://" + webservice_url)
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
                cbdebug("PLM connection successful.")

    @trace
    def groupcleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :    
            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
            
            _fmsg = "Group \"" + obj_attr_list["name"] + "\""
            _fmsg = " could not be cleaned up on this Parallel Libvirt Manager."
    
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.group_cleanup(obj_attr_list["name"], obj_attr_list["tag"], obj_attr_list["userid"])

            cbdebug(_msg, True)
            return 0, _msg, None

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def groupregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.group_register(obj_attr_list["group_name"])
            if _info : 
                if len(_info) :
                    obj_attr_list.update(_info)

            cbdebug(_msg, True)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def groupsdescribe(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.groups_describe(obj_attr_list["group_name"])

            del obj_attr_list["access"]
            del obj_attr_list["group_name"]
            del obj_attr_list["userid"]
                
            if len(_info) :
                obj_attr_list.update(_info)
                
            cbdebug(_msg, True)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def groupunregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.group_unregister(obj_attr_list["group_name"])

            if _info : 
                if len(_info) :
                    obj_attr_list.update(_info)

            cbdebug(_msg, True)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def nodecleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "Hypervisor node \"" + obj_attr_list["name"] + "\""
            _fmsg = " could not be cleaned-up on this Parallel Libvirt Manager."
            
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.node_cleanup(obj_attr_list["name"], obj_attr_list["tag"], obj_attr_list["userid"])
            
            cbdebug(_msg)
            return _status, _msg, _info

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def noderegister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :    
            obj_attr_list["uuid"] = "undefined"
            
            _fmsg = "Hypervisor node \"" + obj_attr_list["name"] + "\" ("
            _fmsg = obj_attr_list["uuid"] + ") could not be registered "
            _fmsg += " on this Parallel Libvirt Manager."
    
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.node_register(obj_attr_list["name"], obj_attr_list["function"])
            obj_attr_list.update(_info)
            obj_attr_list["uuid"] = obj_attr_list["cloud_uuid"]
            obj_attr_list["arrival"] = int(time())
            
            # A way to specify an alternative IP address for a hypervisor
            # This alternative 'destination' represents a faster NIC
            # (such as infiniband) to be used for other types of traffic
            
            if "replication_nodes" in obj_attr_list :
                _replication_nodes = obj_attr_list["replication_nodes"]
            else :
                _replication_nodes = ""
    
            if _replication_nodes.strip() != "" :
                _rnodes = str2dic(_replication_nodes)
                if obj_attr_list["name"] in _rnodes :
                    obj_attr_list["svm_destination"] = gethostbyname(_rnodes[obj_attr_list["name"]])
                
            if "svm_destination" not in obj_attr_list :
                obj_attr_list["svm_destination"] = obj_attr_list["cloud_ip"]

            cbdebug(_msg, True)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    def nodedescribe(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.nodes_describe(obj_attr_list["function"], obj_attr_list["name"])

            del obj_attr_list["access"]
            del obj_attr_list["name"]
            del obj_attr_list["function"]
            del obj_attr_list["userid"]

            if len(_info) :
                obj_attr_list.update(_info)
                
            cbdebug(_msg, True)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace
    def nodeunregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :    
            obj_attr_list["uuid"] = "undefined"
            
            _fmsg = "Hypervisor node \"" + obj_attr_list["name"] + "\" ("
            _fmsg = obj_attr_list["uuid"] + ") could not be unregistered "
            _fmsg += " on this Parallel Libvirt Manager."
    
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.node_unregister(obj_attr_list["name"], obj_attr_list["function"])
            
            if len(_info) :
                obj_attr_list.update(_info)
                obj_attr_list["uuid"] = obj_attr_list["cloud_uuid"]
            obj_attr_list["departure"] = int(time())

            cbdebug(_msg, True)
            return 0, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

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
        try :       
            status = 100
            _fmsg = "unknown error"

            self.connect(obj_attr_list["access"])
            kwargs = self.dic_to_rpc_kwargs(self.plmconn, "instance_run", obj_attr_list)
            _status, _msg, _result = self.plmconn.instance_run(**kwargs)

            if _result :
                obj_attr_list.update(_result)

            # Restore to configured size
            if "configured_size" in obj_attr_list and not self.get_svm_stub(obj_attr_list) :
                self.resize_to_configured_default(obj_attr_list)
            status = 0
        
        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
        
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
                return status, _fmsg, None
            else :
                return status, _msg, obj_attr_list

    def vmsdescribe(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.instances_describe(obj_attr_list["tag"])

            del obj_attr_list["access"]
            del obj_attr_list["tag"]
            del obj_attr_list["userid"]
            if len(_info) :
                obj_attr_list.update(_info)

            cbdebug(_msg)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace        
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "instance_destroy", obj_attr_list)
        _status, _msg, _result = self.plmconn.instance_destroy(**kwargs)

        if _result :
            obj_attr_list.update(_result)

        return _status, _msg, _result

    @trace
    def vmresize_actual(self, obj_attr_list) :
        '''
        TBD
        '''
        cbdebug("VM " + obj_attr_list["name"] + " resize request sent.", True)

        _vg = ValueGeneration(self.pid)
        tag = obj_attr_list["cloud_uuid"]
        desc = obj_attr_list["resource_description"]
        hypervisor_ip = obj_attr_list["vmc_cloud_ip"]

        if not self.is_vm_running(obj_attr_list) :
            return 0, "VM is not running"

        cbdebug("Getting resource state for Guest " + tag)
        _status, _fmsg, _guest_info = self.plmconn.get_domain_full_info(tag, hypervisor_ip)
        
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
                
                self.plmconn.set_domain_cpu(tag, "cpu_shares", str(_cpu_sl), hypervisor_ip)
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

                self.plmconn.set_domain_cpu(tag, "vcpu_quota", str(_cpu_hl), hypervisor_ip)
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

                self.plmconn.set_domain_memory(tag, "current_memory", str(_mem_hl * 1024), hypervisor_ip)
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
        _msg += "resized on plmloud \"" + obj_attr_list["cloud_name"]
        _msg += "\"."
        cbdebug(_msg)
        return 0, _msg

    @trace        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.instance_alter_state(obj_attr_list["tag"], obj_attr_list["state"])

            del obj_attr_list["access"]
            del obj_attr_list["tag"]
            del obj_attr_list["userid"]
            if len(_info) :
                obj_attr_list.update(_info)

            cbdebug(_msg)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    @trace        
    def vmreplicate_start(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "ft_start", obj_attr_list)
        self.plmconn.ft_start(**kwargs)
        _msg = "Replication for VM " + obj_attr_list["primary_name"] + " was successfully started."
        cbdebug(_msg, True)
        return 0, _msg
    
    @trace
    def vmreplicate_status(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "ft_status", obj_attr_list)
        return 0, self.plmconn.ft_status(**kwargs)
            
    @trace
    def vm_fixpause(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "resume", obj_attr_list)
        self.plmconn.resume(**kwargs)
        _msg = "VM " + obj_attr_list["name"] + " was resumed."
        cbdebug(_msg, True)
        return 0, _msg

    @trace
    def vmreplicate_resume(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "ft_resume", obj_attr_list)
        _status, _fmsg, unused = self.plmconn.ft_resume(**kwargs)

        _msg = "SVM FT stub " + obj_attr_list["name"]
        
        if _status :
            _msg += " could not take over for failed primary VM" + _fmsg
            '''
            Do not throw exception. Domain still exists, even if it failed to resume.
            An exception will prevent it from getting logically re-located to the new
            standby host and thus fail to get cleaned up from the 
            data store properly.
            raise CldOpsException(_msg, _status)
            '''
        else :
            _msg += " has taken over for failed primary VM."
            
        cbdebug(_msg, True)
        return 0, _msg

    @trace
    def vmreplicate_stop(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])
        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "ft_stop", obj_attr_list)
        _status, _fmsg, unused = self.plmconn.ft_stop(**kwargs)
        '''
        A failure to stop replication is not fatal.
        It should not prevent the stub from being destroyed....
        '''
        _msg = "SVM FT replication for " + obj_attr_list["primary_name"]
        _msg += (" could not be stopped: " + _fmsg) if _status else " was stopped."
            
        cbdebug(_msg, True)
        return 0, _msg

    def storpoolcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            kwargs = self.dic_to_rpc_kwargs(self.plmconn, "storagepool_create", obj_attr_list)
            _status, _msg, _result = self.plmconn.storagepool_create(**kwargs)

            if _result :
                obj_attr_list.update(_result)
        
        except PLMException, obj :
            _status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
        
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = obj.msg
        
        except KeyboardInterrupt :
            _status = 42 
            _fmsg = "CTRL-C interrupt: " + obj.msg
        
        except Exception, obj :
            _status = 43
            _fmsg = str(obj)
        
        finally :
            if _status :
                self.storpooldestroy(obj_attr_list)
                return _status, _fmsg, None
            else :
                return _status, _msg, obj_attr_list

    def storpoolsdescribe(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.storagepools_describe(obj_attr_list["tag"])

            del obj_attr_list["access"]
            del obj_attr_list["tag"]
            del obj_attr_list["userid"]
            if len(_info) :
                obj_attr_list.update(_info)

            cbdebug(_msg)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return status, _fmsg, None
        
        except CldOpsException, obj :
            status = obj.status
            _fmsg = obj.msg
            return status, _fmsg, None

        except Exception, obj :
            status = 43
            _fmsg = str(obj)
            return status, _fmsg, None

    def storpooldestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])

        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "storagepool_destroy", obj_attr_list)
        _status, _msg, _result = self.plmconn.storagepool_destroy(**kwargs)

        if _result :
            obj_attr_list.update(_result)

        return _status, _msg, _result

    @trace
    def volcreate(self, obj_attr_list) :
        '''
        TBD
        '''        
        try :       
            _status = 100
            _fmsg = "unknown error"

            self.connect(obj_attr_list["access"])
            kwargs = self.dic_to_rpc_kwargs(self.plmconn, "volume_create", obj_attr_list)
            _status, _msg, _result = self.plmconn.volume_create(**kwargs)

            if _result :
                obj_attr_list.update(_result)
        
        except PLMException, obj :
            _status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
        
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = obj.msg
        
        except KeyboardInterrupt :
            _status = 42 
            _fmsg = "CTRL-C interrupt: " + obj.msg
        
        except Exception, obj :
            _status = 43
            _fmsg = str(obj)
        
        finally :
            if _status :
                self.voldestroy(obj_attr_list)
                return _status, _fmsg, None
            else :
                return _status, _msg, obj_attr_list

    def volsdescribe(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            self.connect(obj_attr_list["access"])
            _status, _msg, _info = self.plmconn.volumes_describe(obj_attr_list["tag"])

            del obj_attr_list["access"]
            del obj_attr_list["tag"]
            del obj_attr_list["userid"]
            if len(_info) :
                obj_attr_list.update(_info)

            cbdebug(_msg)
            return _status, _msg, obj_attr_list

        except PLMException, obj :
            _status = obj.status
            _fmsg = "PLM Exception: " + obj.msg
            return _status, _fmsg, None
        
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = obj.msg
            return _status, _fmsg, None

        except Exception, obj :
            _status = 43
            _fmsg = str(obj)
            return _status, _fmsg, None
        
    @trace        
    def voldestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        self.connect(obj_attr_list["access"])

        kwargs = self.dic_to_rpc_kwargs(self.plmconn, "volume_destroy", obj_attr_list)
        _status, _msg, _result = self.plmconn.volume_destroy(**kwargs)

        if _result :
            obj_attr_list.update(_result)

        return _status, _msg, _result
    

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
