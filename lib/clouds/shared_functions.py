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
    Created on Jun 22, 2011

    Common Functions Shared by all Clouds.

    @author: Michael R. Hines, Marcio A. Silva
'''
from time import time, sleep
import threading
import re
import os 
import copy
import json
import netsnmp

from lib.auxiliary.data_ops import str2dic, dic2str
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import Nethashget
from lib.stores.redis_datastore_adapter import RedisMgdConn
from lib.remote.process_management import ProcessManagement
    
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

class CommonCloudFunctions:
    '''
    TBD
    '''

    def __init__ (self, pid, osci) :
        '''
        TBD
        '''
        self.pid = pid
        self.osci = osci
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../.."

    @trace
    def lock (self, cloud_name, obj_type, obj_id, id_str):
        '''
        TBD
        '''
        try:
            _lock = self.osci.acquire_lock(cloud_name, obj_type, obj_id, id_str, 1)
            return _lock

        except RedisMgdConn.ObjectStoreMgdConnException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            return False

    @trace
    def unlock (self, cloud_name, obj_type, obj_id, lock) :
        '''
        TBD
        '''
        try:
            self.osci.release_lock(cloud_name, obj_type, obj_id, lock)
            return True

        except RedisMgdConn.ObjectStoreMgdConnException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            return False

    def additional_host_discovery (self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        try :
            if "additional_discovery" in obj_attr_list :
                if len(obj_attr_list["additional_discovery"]) > 1 :
                    _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                                  cloud_name = obj_attr_list["cloud_name"])
        
                    _cmd = obj_attr_list["additional_discovery"]
                    _cmd = _cmd.replace("--"," --")

                    _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)
                    _extra_attr_list = json.loads(_result_stdout)
        
                    for _host_uuid in obj_attr_list["hosts"].split(',') :
                        if obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] in _extra_attr_list :
                            obj_attr_list["host_list"][_host_uuid].update(_extra_attr_list[obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]])            
                    _status = 0
                else :
                    _status = 0
            else :
                _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while running additional discovery: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace
    def get_svm_stub(self, obj_attr_list) :
        '''
        TBD
        '''
        if "svm_stub_ip" in obj_attr_list :
            if not obj_attr_list["svm_stub_ip"] :
                return False
            if not self.ft_supported :
                _msg = "Fault-Tolerant Stub VMs are not implemented for " + self.get_description()
                _status = 1024
                raise CldOpsException(_msg, _status)
            return True
        return False

    @trace
    def wait_for_instance_ready(self, obj_attr_list, time_mark_prs) :
        '''
        TBD
        '''
        _msg = "Waiting for " + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") to start..."
        self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], _msg)
        cbdebug(_msg, True)
    
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        sleep(_wait)
        
        while _curr_tries < _max_tries :
            if "async" not in obj_attr_list or obj_attr_list["async"].lower() == "false" :
                if threading.current_thread().abort :
                    _msg = "VM Create Aborting..."
                    _status = 123
                    raise CldOpsException(_msg, _status)

            if obj_attr_list["check_boot_started"].count("poll_cloud") :
                _msg = "Check if the VM \"" + obj_attr_list["name"]
                _msg += "\" (" + obj_attr_list["cloud_uuid"] + ") has started by "
                _msg += "querying the cloud directly."
                cbdebug(_msg)                
                _vm_started = self.is_vm_ready(obj_attr_list) 

            elif obj_attr_list["check_boot_started"].count("subscribe_on_") :

                _string_to_search = obj_attr_list["cloud_uuid"] + " has started"

                _channel_to_subscribe = obj_attr_list["check_boot_started"].replace("subscribe_on_",'')

                _msg = "Check if the VM \"" + obj_attr_list["name"]
                _msg += "\" (" + obj_attr_list["cloud_uuid"] + ") has started by "
                _msg += "subscribing to channel \"" + str(_channel_to_subscribe)
                _msg += "\" and waiting for the message \""
                _msg += _string_to_search + "\"."
                cbdebug(_msg)

                self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_STARTING", obj_attr_list["cloud_uuid"])                 
                _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", _channel_to_subscribe)
                for _message in _sub_channel.listen() :
                    if str(_message["data"]).count(_string_to_search) :
                        _vm_started = True
                        break
    
                _sub_channel.unsubscribe()
                self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_STARTING", obj_attr_list["cloud_uuid"])
                _vm_started = self.is_vm_ready(obj_attr_list) 

            elif obj_attr_list["check_boot_started"].count("wait_for_") :
                _boot_wait_time = int(obj_attr_list["check_boot_started"].replace("wait_for_",''))

                _msg = "Assuming that the VM \"" + obj_attr_list["cloud_name"]
                _msg += "\" (" + obj_attr_list["name"] + ") is booted after"
                _msg += " waiting for " + str(_boot_wait_time) + " seconds."
                cbdebug(_msg, True)

                if _boot_wait_time :
                    sleep(_boot_wait_time)
                _vm_started = self.is_vm_ready(obj_attr_list)                 

            else :
                _vm_started = False

                
            if  _vm_started :
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - time_mark_prs
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "Booting...")
                break
            else :
                _msg = "(" + str(_curr_tries) + ") " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "still not ready. Will wait for " + str(_wait)
                _msg += " seconds and check again."
                cbdebug(_msg)
                sleep(_wait)
                _curr_tries += 1
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], _msg)
    
        if _curr_tries < _max_tries :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "started successfully, got IP address " + obj_attr_list["cloud_ip"]
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], _msg)
            cbdebug(_msg)
            return _time_mark_prc
        else :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "is not ready after " + str(_max_tries * _wait) + " seconds.... "
            _msg += "Giving up."
            cberr(_msg, True)
            raise CldOpsException(_msg, 71)

    @trace
    def wait_for_instance_boot(self, obj_attr_list, time_mark_prc) :
        '''
        TBD
        '''

        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])

        if not self.get_svm_stub(obj_attr_list) :
            _network_reachable = False 
        else: 
            _network_reachable = True

        _curr_tries = 0

        if not _network_reachable :

            _msg = "Trying to establish network connectivity to "
            _msg +=  obj_attr_list["name"] + " (cloud-assigned uuid "
            _msg += obj_attr_list["cloud_uuid"] + "), on IP address "
            _msg += obj_attr_list["prov_cloud_ip"] + "..."
            cbdebug(_msg, True)
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], _msg)

            sleep(_wait)

            while not _network_reachable and _curr_tries < _max_tries :

                if "async" not in obj_attr_list or obj_attr_list["async"].lower() == "false" :
                    if threading.current_thread().abort :
                        _msg = "VM Create Aborting..."
                        _status = 123
                        raise CldOpsException(_msg, _status)

                if obj_attr_list["check_boot_complete"].count("tcp_on_") :
                    
                    _nh_conn = Nethashget(obj_attr_list["prov_cloud_ip"])
                    _port_to_check = obj_attr_list["check_boot_complete"].replace("tcp_on_",'')
                    
                    _msg = "Check if the VM \"" + obj_attr_list["cloud_name"]
                    _msg += "\" (" + obj_attr_list["name"] + ") is booted by "
                    _msg += "attempting to establish a TCP connection to port "
                    _msg += str(_port_to_check) + " on address "
                    _msg += obj_attr_list["prov_cloud_ip"]
                    cbdebug(_msg)
                    
                    _vm_is_booted = _nh_conn.check_port(int(_port_to_check), "TCP")

                elif obj_attr_list["check_boot_complete"].count("subscribe_on_") :

                    _string_to_search = obj_attr_list["prov_cloud_ip"] + " is "
                    _string_to_search += "booted"
                    
                    _channel_to_subscribe = obj_attr_list["check_boot_complete"].replace("subscribe_on_",'')

                    _msg = "Check if the VM \"" + obj_attr_list["name"]
                    _msg += "\" (" + obj_attr_list["cloud_uuid"] + ") has started by "
                    _msg += "subscribing to channel \"" + str(_channel_to_subscribe)
                    _msg += "\" and waiting for the message \""
                    _msg += _string_to_search + "\"."
                    cbdebug(_msg)

                    self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_BOOTING", obj_attr_list["prov_cloud_ip"])
                    
                    _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", _channel_to_subscribe)
                    for _message in _sub_channel.listen() :

                        if str(_message["data"]).count(_string_to_search) :
                            _vm_is_booted = True
                            break
        
                    _sub_channel.unsubscribe()
                    self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_BOOTING", obj_attr_list["prov_cloud_ip"])

                elif obj_attr_list["check_boot_complete"].count("wait_for_") :
                    _boot_wait_time = int(obj_attr_list["check_boot_complete"].replace("wait_for_",''))

                    _msg = "Assuming that the VM \"" + obj_attr_list["cloud_name"]
                    _msg += "\" (" + obj_attr_list["name"] + ") is booted after"
                    _msg += " waiting for " + str(_boot_wait_time) + " seconds."
                    cbdebug(_msg)

                    if _boot_wait_time :
                        sleep(_boot_wait_time)
                    _vm_is_booted = True                 
                
                elif obj_attr_list["check_boot_complete"].count("snmpget_poll") :
                    # Send SNMP GET message.  Flag VM as booted if any response at all is recieved
                    _vm_is_booted = False

                    try : 
                        _msg = "Opening SNMP session to " + obj_attr_list["cloud_ip"]
                        cbdebug(_msg)

                        _snmp_wait_time = _wait * 1000000
                        _snmp_version = int(obj_attr_list["snmp_version"])
                        _snmp_comm = str(obj_attr_list["snmp_community"])
                        _snmp_session = netsnmp.Session(Version=_snmp_version, DestHost=obj_attr_list["cloud_ip"], \
                                                        Community=_snmp_comm, \
                                                        Timeout=_snmp_wait_time, Retries=0)

                        _vars = netsnmp.VarList(netsnmp.Varbind(obj_attr_list["snmp_variable"], '0'))

                        _snmp_response = _snmp_session.get(_vars)

                    except :
                        if _snmp_session.ErrorStr :
                            _msg = "Error in SNMP handler : " + _snmp_session.ErrorStr
                        else :
                            _msg = "Unknown error in SNMP handler."
                        cbdebug(_msg)
                        _status = 200
                        raise CldOpsException(_msg, _status)
                    if (_snmp_response[0] != None ) :
                        _vm_is_booted = True
                        _msg = "SNMP Response: " + str(_snmp_response)
                        cbdebug(_msg)

                else :
                    _vm_is_booted = False
                    _msg = "Warning: No valid method specified to determined if VM has booted."
                    cbdebug(_msg, True)    
                    
                if _vm_is_booted :
                    obj_attr_list["mgt_004_network_acessible"] = int(time()) - time_mark_prc 
                    self.osci.pending_object_set(obj_attr_list["cloud_name"], \
                                                 "VM", obj_attr_list["uuid"], \
                                                 "Network accessible now. Continuing...")
                    _network_reachable = True
                    break

                else :
                    _msg = "(" + str(_curr_tries) + ") " + obj_attr_list["name"]
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                    _msg += "still not network reachable. Will wait for " + str(_wait)
                    _msg += " seconds and check again."
                    self.osci.pending_object_set(obj_attr_list["cloud_name"], \
                                                 "VM", \
                                                 obj_attr_list["uuid"], \
                                                 _msg)
                    cbdebug(_msg)
                    sleep(_wait)
                    _curr_tries += 1

        if _curr_tries < _max_tries :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "is network reachable (boot process finished successfully)"
            cbdebug(_msg)
            obj_attr_list["arrival"] = int(time())

            # It should be mgt_006, NOT mgt_005
            obj_attr_list["mgt_006_application_start"] = "0"
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                         obj_attr_list["uuid"], \
                                         "Application starting up...")
        else :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "is not network reachable after " + str(_max_tries * _wait) + " seconds.... "
            _msg += "Giving up."
            cberr(_msg, True)
            raise CldOpsException(_msg, 89)

    @trace
    def take_action_if_requested(self, obj_type, obj_attr_list, current_step):
        '''
        TBD
        '''
        if not obj_attr_list["staging"].count(current_step) :
            return

        if obj_attr_list["staging"] + "_complete" in obj_attr_list : 
            return

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["staging"] == "pause_" + current_step :

                # Always subscribe for the VM channel, no matter the object
                _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", "staging")
    
                if obj_type == "VM" and obj_attr_list["ai"] != "none" :
                    _target_uuid = obj_attr_list["ai"]
                    _target_name = obj_attr_list["ai_name"]
                    _cloud_uuid = obj_attr_list["cloud_uuid"] 
                else :
                    _target_uuid = obj_attr_list["uuid"]
                    _target_name = obj_attr_list["name"]
                    _cloud_uuid = _target_uuid

                self.osci.publish_message(obj_attr_list["cloud_name"], \
                                          obj_type, \
                                          "staging", \
                                          _target_uuid + ";vmready;" + dic2str(obj_attr_list),\
                                           1, \
                                           3600)

                _msg = obj_type + ' ' + _cloud_uuid + " ("
                _msg += _target_name + ") pausing on attach for continue signal ...."
                cbdebug(_msg, True)

                for _message in _sub_channel.listen() :
                    _args = str(_message["data"]).split(";")
    
                    if len(_args) != 3 :
                        #cbdebug("Message is not for me: " + str(_args))
                        continue

                    _id, _status, _info = _args
    
                    if (_id == _target_uuid or _id == _target_name) and _status == "continue" :
                        obj_attr_list[obj_attr_list["staging"] + "_complete"] = int(time())
                        _status = 0
                        break
    
                _sub_channel.unsubscribe()

                _status = 0

            elif obj_attr_list["staging"] == "execute_" + current_step :

                _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                              cloud_name = obj_attr_list["cloud_name"])

                _json_contents = copy.deepcopy(obj_attr_list)

                if obj_type == "AI" :
                    _json_contents["vms"] = {}

                    _vm_id_list = obj_attr_list["vms"].split(',')
                    for _vm_id in _vm_id_list :
                        _vm_uuid = _vm_id.split('|')[0]
                        _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", False, _vm_uuid, False)
                        _json_contents["vms"][_vm_attr_list["uuid"]] = _vm_attr_list 

                obj_attr_list["execute_json_filename"] = "/tmp/" 
                obj_attr_list["execute_json_filename"] += obj_attr_list["execute_json_filename_prefix"]
                obj_attr_list["execute_json_filename"] += "_vapp_" + obj_attr_list["cloud_name"] 
                obj_attr_list["execute_json_filename"] += "_" + obj_attr_list["name"] + "_" 
                obj_attr_list["execute_json_filename"] += obj_attr_list["uuid"] + ".json"

                _json_fh = open(obj_attr_list["execute_json_filename"], 'w')
                _json_fh.write(json.dumps(_json_contents, sort_keys = True, indent = 4))
                _json_fh.close()
                
                _msg = "JSON contents written to " 
                _msg += obj_attr_list["execute_json_filename"] + '.'
                cbdebug(_msg, True)

                _cmd = obj_attr_list["execute_script_name"] + ' '
                _cmd += obj_attr_list["execute_json_filename"]

                _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)

                _msg = "Command \"" + _cmd + "\" executed, with return code " + str(_status)
                cbdebug(_msg, True)

            obj_attr_list[obj_attr_list["staging"] + "_complete"] = int(time())

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except OSError, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while staging: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Finished staging for " + self.get_description()
                cbdebug(_msg)

            return _status, _msg
        
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
        default_keys = {"cloud_uuid" : "tag", "vmc_cloud_ip" : "hypervisor_ip"}

        for key in default_keys.keys() :
            if key in attrs :
                kwargs[default_keys[key]] = attrs[key]
                
        return kwargs
