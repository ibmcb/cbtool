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
    Created on Jun 22, 2011

    Common Functions Shared by all Clouds.

    @author: Michael R. Galaxy, Marcio A. Silva
'''
import threading
import re
import os 
import copy
import json
import traceback
import socket

from copy import deepcopy
from time import time, sleep
from uuid import uuid5, UUID, NAMESPACE_DNS
from socket import gethostbyname
from random import randint

from lib.auxiliary.data_ops import str2dic, dic2str, value_suffix, get_bootstrap_command, DataOpsException
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import Nethashget, hostname2ip
from lib.stores.redis_datastore_adapter import RedisMgdConn
from lib.remote.process_management import ProcessManagement
from lib.remote.ssh_ops import get_ssh_key

import re, os
cwd = (re.compile(".*\/").search(os.path.realpath(__file__)).group(0)) + "/../../"

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

    def __init__ (self, pid, osci, expid = '') :
        '''
        TBD
        '''
        self.pid = pid
        self.osci = osci
        self.expid = expid
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../.."

    @trace
    def lock (self, cloud_name, obj_type, obj_id, id_str):
        '''
        TBD
        '''
        try:
            _lock = self.osci.acquire_lock(cloud_name, obj_type, obj_id, id_str, 1)
            return _lock

        except RedisMgdConn.ObjectStoreMgdConnException as obj :
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

        except RedisMgdConn.ObjectStoreMgdConnException as obj :
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

        except Exception as e :
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
    def get_host_list(self, obj_attr_list) :
        '''
        TBD
        '''
        _host_list = []
        _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", 
                                              False, obj_attr_list["vmc"], False)
        for _uuid in _vmc_attr_list["hosts"].split(",") :
            _host_attr_list = eval(self.osci.get_object(obj_attr_list["cloud_name"], "HOST", 
                                                  False, _uuid, False))
            _host_list.append((_host_attr_list["name"], _uuid))
        
        return _host_list 

    @trace
    def parse_endpoint(self, endpoint, protocol, port_number) :
        '''
        TBD
        '''
        if not endpoint.count("//") :
            endpoint = protocol + "://" + endpoint
            
        if not endpoint.split("//")[1].count(':') :
            if port_number :
                endpoint += ':' + port_number

        _endpoint_ip_port = endpoint.split('//')[1]

        _endpoint_name, _endpoint_ip = hostname2ip(_endpoint_ip_port.split(':')[0], True)                
                
        return endpoint, _endpoint_name, _endpoint_ip
                    
    @trace
    def wait_for_instance_ready(self, obj_attr_list, time_mark_prs) :
        '''
        TBD
        '''     
        _msg = "Waiting for " + obj_attr_list["log_string"]  + ", to start..."
        self.pending_set(obj_attr_list, _msg)
        cbdebug(_msg, True)
           
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        sleep(_wait)

        _abort = "false"
        _x_fmsg = ''

        while _curr_tries < _max_tries and _abort == "false" :
            _start_pooling = int(time())

            _abort, _x_fmsg = self.pending_cloud_decide_abortion(obj_attr_list, "instance creation")

            if "nosync" not in obj_attr_list or str(obj_attr_list["nosync"]).lower() == "false" :
                if threading.current_thread().abort :
                    _msg = obj_attr_list["log_string"] + " Create Aborting..."
                    _status = 123
                    raise CldOpsException(_msg, _status)

            if obj_attr_list["check_boot_started"].count("poll_cloud") :
                _msg = "Check if " + obj_attr_list["log_string"]  + " has started by querying the"
                _msg += " cloud directly."
                cbdebug(_msg)
                _vm_started = self.is_vm_ready(obj_attr_list)

            elif obj_attr_list["check_boot_started"].count("subscribe_on_") :

                if obj_attr_list["role"] == "predictablevm" :
                    _string_to_search = "11111111-1111-1111-1111-111111111111 has started"
                else :
                    _string_to_search = obj_attr_list["cloud_vm_uuid"] + " has started"

                _channel_to_subscribe = obj_attr_list["check_boot_started"].replace("subscribe_on_",'')

                done_key = obj_attr_list["check_boot_started"]
                if done_key not in obj_attr_list or not obj_attr_list[done_key] :
                    _msg = "Check if " + obj_attr_list["log_string"] + " has started by subscribing"
                    _msg += " to channel \"" + str(_channel_to_subscribe)
                    _msg += "\" and waiting for the message \""
                    _msg += _string_to_search + "\"."
                    cbdebug(_msg)

                    obj_attr_list[done_key] = False
                    _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", _channel_to_subscribe, _max_tries * _wait)
                    self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "STARTING", obj_attr_list["cloud_vm_uuid"])
                
                    try :
                        for _message in _sub_channel.listen() :
                            if str(_message["data"]).count(_string_to_search) :
                                _vm_started = True
                                cbdebug(obj_attr_list["log_string"] + ": Message received: " + str(_message["data"]), True)
                                break
                            cbdebug(obj_attr_list["log_string"] + ": Ignoring message: " + str(_message["data"]), True)

                        _sub_channel.unsubscribe()
                        obj_attr_list[done_key] = True 
                    except Exception as e :
                        cberr(obj_attr_list["log_string"] + " listen starting failed: " + str(e), True)
                        self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "STARTING", obj_attr_list["cloud_vm_uuid"])
                        _sub_channel.unsubscribe()
                        raise e
                    self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "STARTING", obj_attr_list["cloud_vm_uuid"])
                _vm_started = self.is_vm_ready(obj_attr_list)

            elif obj_attr_list["check_boot_started"].count("wait_for_") :
                _boot_wait_time = int(obj_attr_list["check_boot_started"].replace("wait_for_",''))

                _msg = "Assuming that " + obj_attr_list["log_string"] + " is booted after"
                _msg += " waiting for " + str(_boot_wait_time) + " seconds."
                cbdebug(_msg, True)

                if _boot_wait_time :
                    sleep(_boot_wait_time)                    
                _vm_started = self.is_vm_ready(obj_attr_list)                 

            else :
                _vm_started = False

            _pooling_time = int(time() - _start_pooling)

            if _pooling_time <= _wait :
                _actual_wait = _wait - _pooling_time
            else :
                _msg = "The time spent on pooling for \"ready\" status for "
                _msg += obj_attr_list["log_string"] + "(" + str(_pooling_time) 
                _msg += " s) is actually longer than the "
                _msg += "interval between pooling attempts (" + str(_wait) + " s)."
                cbdebug(_msg, True)
                _actual_wait = 0

            if str(obj_attr_list["use_vpn_ip"]).lower() != "false" and obj_attr_list["netname"] != "none" :
                if self.get_attr_from_pending(obj_attr_list, "cloud_init_vpn") :
                    obj_attr_list["last_known_state"] = "ACTIVE with (vpn) ip assigned"
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_init_vpn"]  
                    cbdebug("VPN address for " + obj_attr_list["log_string"] + " found: " + obj_attr_list["prov_cloud_ip"])                    
                    if obj_attr_list["cloud_ip"] == "undefined" :
                        cbdebug("Cloud has not finished returning remaining IP information.")
                        _vm_started = False
                    else :
                        _vm_started = True
                else :
                    obj_attr_list["last_known_state"] = "ACTIVE with (vpn) ip unassigned"
                    cbdebug("VPN address for " + obj_attr_list["log_string"] + " not yet available.")                    
                    _vm_started = False
                                        
            if  _vm_started :
                self.take_action_if_requested("VM", obj_attr_list, "provision_complete")
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - time_mark_prs
                self.pending_set(obj_attr_list, "Booting...")
                break
            else :
                _msg = "(" + str(_curr_tries) + ") " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "still not ready. Will wait for " + str(_actual_wait)
                _msg += " seconds and check again."
                cbdebug(_msg)
                sleep(_actual_wait)
                _curr_tries += 1
                self.pending_set(obj_attr_list, _msg)
    
        if _curr_tries < _max_tries :
            if _abort != "false" :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was aborted " + _x_fmsg + ". Giving up."
                cberr(_msg, True)
                raise CldOpsException(_msg, 71)                
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "started successfully, got IP address " + obj_attr_list["cloud_ip"]
                self.pending_set(obj_attr_list, _msg)
                cbdebug(_msg)
                return _time_mark_prc
        
        else :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
            _msg += "is not ready after " + str(_max_tries * _wait) + " seconds... "
            _msg += "Giving up."
            cberr(_msg, True)
            raise CldOpsException(_msg, 71)

    @trace        
    def get_attr_from_pending(self, obj_attr_list, key = "all") :
        '''
        TBD
        '''
        if str(obj_attr_list["is_jumphost"]).lower() == "false" :

            _pending_attr_list = self.osci.pending_object_get(obj_attr_list["cloud_name"], \
                                                              "VM", obj_attr_list["uuid"], \
                                                              key, False)

            if _pending_attr_list :                
                
                if key == "all" :
                    for _key in [ "cloud_init_rsync", \
                                  "cloud_init_bootstrap", \
                                  "cloud_init_vpn"] :
                        if _key in _pending_attr_list :
                            obj_attr_list[_key] = _pending_attr_list[_key]
    
                else :                
                    obj_attr_list[key] = _pending_attr_list
    
                return True                

        return False

    @trace
    def wait_for_instance_boot(self, obj_attr_list, time_mark_prc) :
        '''
        TBD
        '''

        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        _network_reachable = False 
        _curr_tries = 0 

        if not _network_reachable :

            _msg = "Trying to establish network connectivity to " + obj_attr_list["log_string"]  
            _msg += ", on IP address " + obj_attr_list["prov_cloud_ip"] 
            _msg += " (using method \"" + obj_attr_list["check_boot_complete"] + "\")" 
            
            if str(obj_attr_list["use_jumphost"]).lower() == "false" :
                _msg += "..."
            else :
                _msg += " via jumphost " + obj_attr_list["jumphost_ip"] + "..."
                obj_attr_list["check_boot_complete"] = "run_command_/bin/true"
                
            cbdebug(_msg, True)
            
            sleep(_wait)

            _abort = "false"
            _x_fmsg = '' 
            
            while not _network_reachable and _curr_tries < _max_tries and _abort != "true" :
                _start_pooling = int(time())

                _abort, _x_fmsg = self.pending_cloud_decide_abortion(obj_attr_list, "instance boot")

                if "nosync" not in obj_attr_list or str(obj_attr_list["nosync"]).lower() == "false" :
                    if threading.current_thread().abort :
                        _msg = "VM Create Aborting..."
                        _status = 123
                        raise CldOpsException(_msg, _status)

                if obj_attr_list["check_boot_complete"].count("tcp_on_") :

                    _nh_conn = Nethashget(obj_attr_list["prov_cloud_ip"])
                    _port_to_check = obj_attr_list["check_boot_complete"].replace("tcp_on_",'')

                    _msg = "Check if " + obj_attr_list["log_string"] + " is booted by "
                    _msg += "attempting to establish a TCP connection to port "
                    _msg += str(_port_to_check) + " on address "
                    _msg += obj_attr_list["prov_cloud_ip"]
                    cbdebug(_msg)
                    
                    _vm_is_booted = _nh_conn.check_port(int(_port_to_check), "TCP")

                elif obj_attr_list["check_boot_complete"].count("cloud_ping") :

                    _msg = "Check if " + obj_attr_list["log_string"] + " is booted by "
                    _msg += "attempting to establish network connectivity "
                    _msg += "through the cloud's API"
                    cbdebug(_msg)

                    _vm_is_booted = self.is_vm_alive(obj_attr_list)

                elif obj_attr_list["check_boot_complete"].count("subscribe_on_") :

                    _string_to_search = obj_attr_list["prov_cloud_ip"] + " is "
                    _string_to_search += "booted"

                    _channel_to_subscribe = obj_attr_list["check_boot_complete"].replace("subscribe_on_",'')

                    done_key = obj_attr_list["check_boot_complete"]
                    if done_key not in obj_attr_list or not obj_attr_list[done_key] :
                        _msg = "Check if " + obj_attr_list["log_string"] + " has booted by "
                        _msg += "subscribing to channel \"" + str(_channel_to_subscribe)
                        _msg += "\" and waiting for the message \""
                        _msg += _string_to_search + "\"."
                        cbdebug(_msg)

                        obj_attr_list[done_key] = False

                        self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_BOOTING", obj_attr_list["prov_cloud_ip"])

                        try :
                            _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", _channel_to_subscribe, _max_tries * _wait)
                            for _message in _sub_channel.listen() :

                                if str(_message["data"]).count(_string_to_search) :
                                    _vm_is_booted = True
                                    break

                            obj_attr_list[done_key] = True 
                            _sub_channel.unsubscribe()
                        except Exception as e :
                            cberr(obj_attr_list["log_string"] + " listen vms_booting failed: " + str(e), True)
                            self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_BOOTING", obj_attr_list["prov_cloud_ip"])
                            _sub_channel.unsubscribe()
                            raise e
                        self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_BOOTING", obj_attr_list["prov_cloud_ip"])

                elif obj_attr_list["check_boot_complete"].count("wait_for_") :
                    _boot_wait_time = int(obj_attr_list["check_boot_complete"].replace("wait_for_",''))

                    _msg = "Assuming that " + obj_attr_list["log_string"]
                    _msg += " is booted after waiting for " + str(_boot_wait_time) + " seconds."
                    cbdebug(_msg)

                    if _boot_wait_time :
                        sleep(_boot_wait_time)
                    _vm_is_booted = True                 

                elif obj_attr_list["check_boot_complete"].count("run_command_") :
                    _command_to_run = obj_attr_list["check_boot_complete"].replace("run_command_",'')
                    _command_to_run = _command_to_run.replace("____",' ')

                    _msg = "Check if " + obj_attr_list["log_string"]  + " has booted by "
                    _msg += "running the command \"" + str(_command_to_run) + "\""
                    cbdebug(_msg)

                    if _curr_tries <= _max_tries/3 :                        
                        _connection_timeout = int(obj_attr_list["update_frequency"])/2
                    elif _curr_tries > _max_tries/3 and _curr_tries < 2*_max_tries/3 :
                        _connection_timeout = int(obj_attr_list["update_frequency"])
                        obj_attr_list["comments"] += "Had to increase ssh timeout. "
                    else :
                        _connection_timeout = int(obj_attr_list["update_frequency"])*2
                        obj_attr_list["comments"] += "Had to increase ssh timeout one more time. "

                    if str(obj_attr_list["use_jumphost"]).lower() == "true" :
                        if "ssh_config_file" in obj_attr_list:
                            _ssh_conf_file = obj_attr_list["ssh_config_file"]
                        else:                            
                            _ssh_conf_file = None
                    else :
                        _ssh_conf_file = None

                    _proc_man = ProcessManagement(username = obj_attr_list["login"], \
                                                  cloud_name = obj_attr_list["cloud_name"], \
                                                  hostname = obj_attr_list["prov_cloud_ip"], \
                                                  priv_key = obj_attr_list["identity"], \
                                                  config_file = _ssh_conf_file,
                                                  connection_timeout = _connection_timeout)

                    try :
                        _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_command_to_run, \
                                                                                           "127.0.0.1", \
                                                                                           1, \
                                                                                           0, \
                                                                                           obj_attr_list["transfer_files"], \
                                                                                           obj_attr_list["debug_remote_commands"])

                        if not _status :
                            _vm_is_booted = True
                        else :
                            _vm_is_booted = False
                    except :
                        _vm_is_booted = False
                
                elif obj_attr_list["check_boot_complete"].count("snmpget_poll") :
                    import netsnmp
                    # Send SNMP GET message.  Flag VM as booted if any response at all is recieved
                    _vm_is_booted = False

                    try : 
                        _msg = "Check if " + obj_attr_list["log_string"]  + " has booted by "
                        _msg += "opening SNMP session to " + obj_attr_list["prov_cloud_ip"]
                        cbdebug(_msg)

                        _snmp_wait_time = _wait * 1000000
                        _snmp_version = int(obj_attr_list["snmp_version"])
                        _snmp_comm = str(obj_attr_list["snmp_community"])
                        _snmp_session = netsnmp.Session(Version=_snmp_version, \
                                                        DestHost=obj_attr_list["prov_cloud_ip"], \
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

                _pooling_time = int(time()) - _start_pooling
    
                if _pooling_time <= _wait :
                    _actual_wait = _wait - _pooling_time
                else :
                    _msg = "The time spent on pooling for \"booted\" status (" + str(_pooling_time) 
                    _msg += " s) is actually longer than the "
                    _msg += "interval between pooling attempts (" + str(_wait) + " s)."
                    cbdebug(_msg, True)
                    _actual_wait = 0
                
                if _vm_is_booted :
                    self.take_action_if_requested("VM", obj_attr_list, "provision_finished")
                    _time_mark_ib = int(time())
                    obj_attr_list["mgt_004_network_acessible"] = int(time()) - time_mark_prc
                    obj_attr_list["time_mark_aux"] = _time_mark_ib
                    self.pending_set(obj_attr_list, "Network accessible now. Continuing...")
                    _network_reachable = True
                    break

                else :
                    _msg = "(" + str(_curr_tries) + ") " + obj_attr_list["name"]
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still not network reachable. Will wait for " + str(_actual_wait)
                    _msg += " seconds and check again."
                    self.pending_set(obj_attr_list, _msg)
                    cbdebug(_msg)
                    sleep(_actual_wait)
                    _curr_tries += 1

        if _curr_tries < _max_tries :
            if _abort != "false" :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was aborted " + _x_fmsg + ". Giving up."
                cberr(_msg, True)                
                raise CldOpsException(_msg, 89)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "is network reachable (boot process finished successfully)"
                cbdebug(_msg)
                obj_attr_list["arrival"] = int(time())
    
                # It should be mgt_006 and mgt_007 NOT mgt_005
                obj_attr_list["mgt_006_instance_preparation"] = "0"
                obj_attr_list["mgt_007_application_start"] = "0"
                self.pending_set(obj_attr_list, "Application starting up...")
                self.get_attr_from_pending(obj_attr_list, "all")

        else :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
            _msg += "is not network reachable after " + str(_max_tries * _wait) + " seconds.... "
            _msg += "Giving up."
            cberr(_msg, True)
            raise CldOpsException(_msg, 89)

    @trace        
    def pending_set(self, obj_attr_list, msg) :
        '''
        TBD
        '''
        if obj_attr_list["ai"] != "none" :
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                         obj_attr_list["uuid"], "status", msg, \
                                         parent=obj_attr_list["ai"], parent_type="AI")
        else :
            if str(obj_attr_list["is_jumphost"]).lower() == "false" :
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                             obj_attr_list["uuid"], "status", msg) 

    @trace
    def pending_cloud_decide_abortion(self, obj_attr_list, _reason = "abort") :
        '''
        TBD
        '''
        _abort = "false"
        _x_fmsg = ''
        if str(obj_attr_list["sla_provisioning_abort"]).lower() == "true" :
            if "sla_provisioning_target" in obj_attr_list :
                _provisioning_time = int(time()) - int(obj_attr_list["mgt_001_provisioning_request_originated"])
                
                if _provisioning_time > int(obj_attr_list["sla_provisioning_target"]) :
                    self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", \
                                             obj_attr_list["uuid"], "abort", _reason)
                    
                    _x_fmsg= "(due to SLA provisioning target violation)" 
                    
        try :            
            _abort = self.osci.pending_object_get(obj_attr_list["cloud_name"], \
                                                  "VM", \
                                                  obj_attr_list["uuid"], \
                                                  "abort").lower()
        except :
            pass

        return _abort, _x_fmsg
                        
    @trace
    def take_action_if_requested(self, obj_type, obj_attr_list, current_step):
        '''
        TBD
        '''

        if "staging" not in obj_attr_list :
            return
        
        if not obj_attr_list["staging"].count(current_step) :
            return

        _current_staging = obj_attr_list["staging"] 
               
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["staging"] == "pause_" + current_step :

                if current_step == "provision_originated" :
                    obj_attr_list["last_known_state"] = "waiting for signal"

                _max_tries = int(obj_attr_list["update_attempts"])
                _wait = int(obj_attr_list["update_frequency"])

                # Always subscribe for the VM channel, no matter the object
                _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", "staging", _max_tries * _wait)
    
                if obj_type == "VM" and obj_attr_list["ai"] != "none" and current_step.count("all_vms") :
                    _target_uuid = obj_attr_list["ai"]
                    _target_name = obj_attr_list["ai_name"]
                    _cloud_vm_uuid = obj_attr_list["cloud_vm_uuid"] 
                else :
                    _target_uuid = obj_attr_list["uuid"]
                    _target_name = obj_attr_list["name"]
                    _cloud_vm_uuid = _target_uuid

                self.osci.publish_message(obj_attr_list["cloud_name"], \
                                          obj_type, \
                                          "staging", \
                                          _target_uuid + ";vmready;" + dic2str(obj_attr_list),\
                                           1, \
                                           3600)

                done_key = "pause_" + current_step
                if done_key not in obj_attr_list or not obj_attr_list[done_key] :
                    _msg = obj_type + ' ' + _cloud_vm_uuid + " ("
                    _msg += _target_name + ") pausing on attach for continue signal ...."
                    cbdebug(_msg, True)

                    obj_attr_list[done_key] = False
                    self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "PAUSING", _cloud_vm_uuid)
                    try :
                        for _message in _sub_channel.listen() :
                            _args = str(_message["data"]).split(";")

                            if len(_args) != 3 :
        #                        cbdebug("Message is not for me: " + str(_args))
                                continue

                            _id, _status, _info = _args

                            if (_id == _target_uuid or _id == _target_name) and _status == "continue" :
                                obj_attr_list[obj_attr_list["staging"] + "_complete"] = int(time())

                                if _info.count(":") :

                                    _add_obj_attr_list = str2dic(_info)
                                    obj_attr_list.update(_add_obj_attr_list)

                                _status = 0
                                break

                        obj_attr_list[done_key] = True 
                        _sub_channel.unsubscribe()
                    except Exception as e :
                        cberr(_target_name + " listen pausing failed: " + str(e), True)
                        self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "PAUSING", _cloud_vm_uuid)
                        _sub_channel.unsubscribe()
                        raise e

                    self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "PAUSING", _cloud_vm_uuid)

                _status = 0

            elif obj_attr_list["staging"] == "execute_" + current_step :

                if current_step == "provision_originated" :
                    obj_attr_list["last_known_state"] = "about to execute script"

                _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                              cloud_name = obj_attr_list["cloud_name"])

                _json_contents = copy.deepcopy(obj_attr_list)

                if obj_type == "AI" :
                    _json_contents["vms"] = {}
                    if "vms" in obj_attr_list and current_step != "deprovision_finished" :
                        _vm_id_list = obj_attr_list["vms"].split(',')
                        for _vm_id in _vm_id_list :
                            _vm_uuid = _vm_id.split('|')[0]
                            if len(_vm_uuid) :
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

                obj_attr_list[obj_attr_list["staging"] + "_stdout"] = _result_stdout
                obj_attr_list[obj_attr_list["staging"] + "_stderr"] = _result_stderr

                if not _status :
                    self.process_script_output(obj_attr_list, current_step)
                    
            obj_attr_list[_current_staging + "_complete"] = int(time())
            
        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except OSError as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
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
                    if value.strip() == "" :
                        continue
                    if value.lower().strip() == "true" :
                        value = True
                    elif value.lower().strip() == "false" :
                        value = False

                kwargs[var] = value 

        # Keys that are common inputs to most API functions
        default_keys = {"cloud_vm_uuid" : "tag", "vmc_cloud_ip" : "hypervisor_ip"}

        for key in list(default_keys.keys()) :
            if key in attrs :
                kwargs[default_keys[key]] = attrs[key]
                
        return kwargs
    
    @trace
    def update_libvirt_variables(self, obj_attr_list):
        '''
        After restore from disk, the VM's parameters (such as VNC/Spice display
        ports) may have changed. Other things may potentially change in the future. 
        We need to re-update the data store to include any new pieces of information. 
        '''
        for var in ["display_port", "display_protocol" ] :
            if var in obj_attr_list :
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                  obj_attr_list["uuid"], False, \
                                                  var, obj_attr_list[var])
    
    @trace
    def populate_interface(self, obj_attr_list) :
        '''
        A way to specify an alternative IP address for a hypervisor
        This alternative 'interface' represents a faster NIC
        (such as RDMA) to be used for other types of traffic
        '''

        for op in ["migrate", "protect"] :
            if str(obj_attr_list[op + "_supported"]).lower() != "true" :
                continue
        
            if op + "_interfaces" in obj_attr_list :
                interfaces = obj_attr_list[op + "_interfaces"]
                _ivmcs = str2dic(interfaces)
            else :
                interfaces = ""
                _ivmcs = {}
                
            for _host_uuid in obj_attr_list["hosts"].split(',') :
                obj_attr_list["host_list"][_host_uuid][op + "_interface"] = "default"
                
                if interfaces.strip() == "" :
                    continue
                
                hostname = obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                if hostname in _ivmcs : 
                    iface = _ivmcs[hostname]
                    try :
                        obj_attr_list["host_list"][_host_uuid][op + "_interface"] = gethostbyname(iface)
                    except Exception as msg :
                        _fmsg = "Could not lookup interface " + iface + " for hostname " + hostname + " (probably bad /etc/hosts): " + str(msg)
                        raise CldOpsException(_fmsg, 1295)

    @trace
    def check_ssh_key(self, vmc_name, key_names, vm_defaults, internal = False, connection = None, check = True) :
        '''
        TBD
        '''

        _key_pair_found = False      
        
        for key_name in key_names :
            if not key_names :
                _key_pair_found = True
                break
            else :
                _msg = "Checking if the ssh key pair \"" + key_name + "\" is created"
                _msg += " on VMC " + vmc_name + "...."
                if not internal :
                    cbdebug(_msg, True)
                else :
                    cbdebug(_msg)
                    
                _pub_key_fn = vm_defaults["credentials_dir"] + '/'
                _pub_key_fn += vm_defaults["ssh_key_name"] + ".pub"

                _key_type, _key_contents, _key_fingerprint = get_ssh_key(_pub_key_fn, self.get_description())

                vm_defaults["pubkey_contents"] = _key_type + ' ' + _key_contents

                if not _key_contents :
                    _fmsg = _key_type
                    cberr(_fmsg, True)
                    return False

                if not check :
                    _key_pair_found = True
                else :
                    _key_pair_found = False
    
                    _registered_key_pairs = {}
                    
                    self.get_ssh_keys(vmc_name, key_name, _key_contents, _key_fingerprint, _registered_key_pairs, internal, connection)
    
                    for _key_pair in list(_registered_key_pairs.keys()) :
                        if _key_pair == key_name :
                            _msg = "A key named \"" + key_name + "\" was found "
                            _msg += "on VMC " + vmc_name + ". Checking if the key"
                            _msg += " contents are correct."
                            cbdebug(_msg)
                            _keyfp, _keyid = _registered_key_pairs[_key_pair].split('-')
    
                            if len(_key_fingerprint) > 1 and len(_keyfp) > 1 :
    
                                if _key_fingerprint == _keyfp :
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
                                    _msg += ". Either delete this key's fingerprint or pick a new one."
                                    cbdebug(_msg, True)
                                    break
    
                    if not _key_pair_found :
    
                        _msg = "    Creating the ssh key pair \"" + key_name + "\""
                        _msg += " on VMC " + vmc_name + ", using the public key \""
                        _msg += _pub_key_fn + "\"..."
                        
                        if not internal :
                            cbdebug(_msg, True)
                        else :
                            cbdebug(_msg)
    
                        try :
                            self.create_ssh_key(vmc_name, key_name, _key_type, _key_contents, _key_fingerprint, vm_defaults, connection)
    
                        except Exception as e :
                            if vm_defaults["abort_after_ssh_upload_failure"] :
                                raise e
                            else :
                                cbwarn("Key upload failed, but user has asked us to continue: " + str(e), True)
    
                        _key_pair_found = True

            return _key_pair_found    

    @trace
    def check_security_group(self, vmc_name, security_group_name) :
        '''
        TBD
        '''
    
        _security_group_name = False
        
        if security_group_name :
    
            _msg = "Checking if the security group \"" + security_group_name
            _msg += "\" is created on VMC " + vmc_name + "...."
            cbdebug(_msg, True)
    
            _security_group_found = False
            
            _registered_security_groups = []

            self.get_security_groups(vmc_name, security_group_name, _registered_security_groups)
            
            for _registered_security_group in _registered_security_groups :
                if _registered_security_group == security_group_name :
                    _security_group_found = True
    
            if not _security_group_found :
                _msg = "ERROR! Please create the security group \"" 
                _msg += security_group_name + "\" in "
                _msg += self.get_description() + " before proceeding."
                _fmsg = _msg
                cberr(_msg, True)
        else :
            _security_group_found = True
    
        return _security_group_found

    @trace        
    def base_check_images(self, vmc_name, vm_templates, registered_imageid_list, map_id_to_name, vm_defaults) :
        '''
        TBD
        '''        
        
        _required_imageid_list = {}

        _vm_templates = deepcopy(vm_templates)
        if str(vm_defaults["nest_containers_enabled"]).lower() == "false" :
            if "nest_containers_base_image"  in _vm_templates :
                del _vm_templates["nest_containers_base_image"]

        for _vm_role in list(_vm_templates.keys()) :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if self.is_cloud_image_uuid(_imageid) :
                if _imageid not in _required_imageid_list :
                    _required_imageid_list[_imageid] = []
                _required_imageid_list[_imageid].append(_vm_role)
                
        _msg = 'y'

        _detected_imageids = {}
        _undetected_imageids = {}

        #cbdebug("Required list: " + str(_required_imageid_list), True)
        #cbdebug("Registered list: " + str(registered_imageid_list), True)
        #cbdebug("Mapped list: " + str(map_id_to_name), True)
        for _imageid in list(_required_imageid_list.keys()) :
            
            # Unfortunately we have to check image names one by one,
            # because they might be appended by a generic suffix for
            # image randomization (i.e., deploying the same image multiple
            # times as if it were different images.
            _image_detected = False
            for _registered_imageid in registered_imageid_list :
                #cbdebug("Comparing " + _registered_imageid + " to " + _imageid, True)
                if str(_registered_imageid).count(_imageid) :
                    _image_detected = True
                    _detected_imageids[_imageid] = "detected"
                else :
                    _undetected_imageids[_imageid] = "undetected"
            
            if _image_detected :                
                _msg += "x INFO    Image id for VM roles \"" + ','.join(_required_imageid_list[_imageid]) + "\" is \""
                _msg += _imageid + "\" "
                if _imageid in map_id_to_name :
                    _msg += "(\"" + map_id_to_name[_imageid].strip() + "\") "
                _msg += "and it is already registered.\n"
            else :
                _msg += "x WARNING Image id for VM roles \""
                _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                _msg += _imageid + "\" "
                if _imageid in map_id_to_name :
                    _msg += "(\"" + map_id_to_name[_imageid].strip() + "\") "                
                _msg += "is NOT registered "
                _msg += "(attaching VMs with any of these roles will result in error).\n"

        if not len(_detected_imageids) :
            _msg = "WARNING! None of the image ids used by any VM \"role\" were detected"
            _msg += " in this " + self.get_description() + " !"
#            _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
            cbwarn(_msg, True)
        else :
            _msg = _msg.replace("yx",'')
            _msg = _msg.replace("x ","          ")
            _msg = _msg[:-2]
            if len(_msg) :
                cbdebug(_msg, True)    

        return _detected_imageids

    @trace
    def populate_cloudconfig(self, obj_attr_list) :
        '''
        TBD
        '''
        if ("userdata" not in obj_attr_list or str(obj_attr_list["userdata"]).lower() == "false") and obj_attr_list["use_vpn_ip"].lower() == "false" :
            #cbdebug("Skipping userdata: " + str(obj_attr_list["userdata"]), True)
            return None

        obj_attr_list["cloudinit_keys"] += ',' + obj_attr_list["pubkey_contents"] 

        obj_attr_list["cloudinit_keys"] = obj_attr_list["cloudinit_keys"].replace("____",' ')

        cloudconfig = "#cloud-config\n"
        cloudconfig += "ssh_pwauth: true\n"
        cloudconfig += "disable_root: false\n"
        cloudconfig += "\nusers:\n"
        cloudconfig += "- name: " + obj_attr_list["login"] + "\n"
        if str(obj_attr_list["password"]).lower() != "false" :
            cloudconfig += "  lock-passwd: false\n"
            cloudconfig += "  lock_passwd: false\n"
            cloudconfig += "  passwd: " + obj_attr_list["password"].replace("DOLLAR", "$") + "\n"        
        else :
            cloudconfig += "  lock-passwd: true\n"
        cloudconfig += "  home: /home/" + obj_attr_list["login"] + "\n"
        cloudconfig += "  shell: /bin/bash\n"        
        cloudconfig += "  sudo: ALL=(ALL) NOPASSWD:ALL\n"

        if obj_attr_list["userdata_ssh"].lower() == "true" :        
            cloudconfig += "  ssh_authorized_keys:\n"
            for _k in obj_attr_list["cloudinit_keys"].split(',') : 
                if len(_k) > 370 :
                    cloudconfig += "   - " + _k + '\n'

        if obj_attr_list["userdata_ssh"].lower() == "true" :
            cloudconfig += "\n\n"
            cloudconfig += "  ssh_authorized_keys:\n"
            for _k in obj_attr_list["cloudinit_keys"].split(',') : 
                if len(_k) > 370 :
                    cloudconfig += "   - " + _k + '\n'
        cloudconfig += "\n"

        cloudconfig += "\nwrite_files:\n"
        cloudconfig += "  - path: /tmp/cb_post_boot.sh\n"
        cloudconfig += "    content: |\n"
            
        if obj_attr_list["userdata_post_boot"].lower() == "true" :
            cloudconfig += self.create_bootstrap_script(obj_attr_list)
        else :
            cloudconfig += "      #!/bin/bash\n"
            cloudconfig += "      /bin/true\n"

        if obj_attr_list["use_vpn_ip"].lower() == "true" :
            
            if "cloudinit_packages" in obj_attr_list and obj_attr_list["cloudinit_packages"].lower() != "false" :
                obj_attr_list["cloudinit_packages"] += ";openvpn;redis-tools" 
            else :
                obj_attr_list["cloudinit_packages"] = "openvpn;redis-tools"
            
            conf_destination = "/etc/openvpn/" + obj_attr_list["cloud_name"] + "_client-cb-openvpn-cloud.conf"            
            targets = []
            targets.append(("/configs/generated/" + obj_attr_list["cloud_name"] + "_client-cb-openvpn.conf", conf_destination))
            targets.append(("/util/openvpn/client_connected.sh", "/etc/openvpn/client_connected.sh"))

            for target in targets :
                (src, dest) = target
                cbdebug("src: " + src + " dest: " + dest)
                cloudconfig += """
  - path: """ + dest + """
    content: |
"""
                fhname = cwd + src
                cbdebug("Opening: " + fhname)
                fh = open(fhname, 'r')
                while True :
                    line = fh.readline()
                    if not line :
                        break

                    line = line.replace("USER", obj_attr_list["username"])
                    line = line.replace("CLOUD_NAME", obj_attr_list["cloud_name"])
                    if str(obj_attr_list["vpn_redis_discovery"]).lower() == "true" :
                        line = line.replace("SERVER_BOOTSTRAP", obj_attr_list["vpn_server_bootstrap"])
                    else :
                        line = line.replace("SERVER_BOOTSTRAP", obj_attr_list["vpn_redis_discovery"])
                    line = line.replace("UUID", obj_attr_list["uuid"])
                    line = line.replace("OSCI_PORT", str(self.osci.port))
                    line = line.replace("OSCI_DBID", str(self.osci.dbid))
                    if line.count("remote ") :
                        line = "remote " + obj_attr_list["vpn_server_ip"] + " " + obj_attr_list["vpn_server_port"] + "\n"
                    cloudconfig += "      " + line

                    if line.count("remote ") :
                        cloudconfig += "      up /etc/openvpn/client_connected.sh\n"
                fh.close()

        if obj_attr_list["userdata_post_boot"].lower() == "true" or obj_attr_list["use_vpn_ip"].lower() != "false" or obj_attr_list["cloudinit_commands"].lower() != "false" :
            cloudconfig += "\nruncmd:\n"
            cloudconfig += "  - chmod +x /tmp/cb_post_boot.sh\n"

            if obj_attr_list["cloudinit_commands"].lower() != "false" :
                for _cmd in obj_attr_list["cloudinit_commands"].split(';') :
                    cloudconfig += "  - " + _cmd.replace("____",' ') + '\n'
                    
            # We can't run the userdata from cloudbench until the VPN is connected,
            # so only run it if we're not using the VPN.
            # Otherwise, /etc/openvpn/client_connected.sh will do it.
            if obj_attr_list["use_vpn_ip"].lower() == "false" :
                cloudconfig += "  - /tmp/cb_post_boot.sh\n"
            else :
                cloudconfig += "  - chmod +x /etc/openvpn/client_connected.sh\n"
                cloudconfig += "  - mv " + conf_destination + " /tmp/cbvpn.conf\n"
                cloudconfig += "  - rm -f /etc/openvpn/*.conf /etc/openvpn/*.ovpn\n"
                cloudconfig += "  - mv /tmp/cbvpn.conf " + conf_destination + "\n"
                cloudconfig += "  - mkdir -p /var/log/openvpn\n"
                #cloudconfig += "  - openvpn --daemon --config " + conf_destination + "\n"
                cloudconfig += "  - systemctl start openvpn@" + obj_attr_list["cloud_name"] + "_client-cb-openvpn-cloud.service\n"
                cloudconfig += "  - service openvpn start\n"
                
        # Check to see if the user requested packages to be installed for this VM role via cloud-init
        if obj_attr_list["cloudinit_packages"].lower() != "false" :
            cbdebug("Will instruct cloud-init to install packages \"" + obj_attr_list["cloudinit_packages"].replace(';',' ') + "\" on " + obj_attr_list["log_string"], True)
            cloudconfig += """
packages:"""
            for package in obj_attr_list["cloudinit_packages"].split(";") :
                cloudconfig += """
  - """ + package
        #cbdebug("Final userdata: \n" + str(cloudconfig))

        return cloudconfig

    def create_bootstrap_script(self, obj_attr_list) :
        '''
        TBD
        '''
    
        _attempts = str(5)
        _sleep = str(2)
        
        _fshn = obj_attr_list["filestore_host"]
        _fspn = obj_attr_list["filestore_port"]
        _fsun = obj_attr_list["filestore_username"]
        _ldn = obj_attr_list["local_dir_name"]
    
        _rln = obj_attr_list["login"] 
        
        _ohn = obj_attr_list["objectstore_host"]
        _opn = obj_attr_list["objectstore_port"]
        _odb = obj_attr_list["objectstore_dbid"]
        
        _cn = obj_attr_list["cloud_name"]
        
        if str(obj_attr_list["vpn_redis_discovery"]).lower() == "true" :
            _ohn = obj_attr_list["vpn_server_bootstrap"]
        else :
            _ohn = obj_attr_list["vpn_redis_discovery"]
        _fshn = obj_attr_list["vpn_server_bootstrap"]

        _pad = "      " 
    
        _bootstrap_script = _pad + "#!/bin/bash\n\n"
        _bootstrap_script += _pad + "# This VM is part of experiment id \"" + obj_attr_list["experiment_id"] + "\""
        _bootstrap_script += _pad + "\n"            
        _bootstrap_script += _pad + "mkdir -p /var/log/cloudbench\n"    
        _bootstrap_script += _pad + "\n"        
        _bootstrap_script += _pad + "chmod 777 /var/log/cloudbench\n"
        _bootstrap_script += _pad + "\n"
        
        _bootstrap_script += get_bootstrap_command(obj_attr_list, True)
        
        _bootstrap_script += _pad + "if [[ $(cat " + obj_attr_list["remote_dir_home"] + "/cb_os_parameters.txt | grep -c \"#OSOI-" + "TEST_" + obj_attr_list["username"] + ":" + obj_attr_list["cloud_name"] + "\") -ne 0 ]]\n"
        _bootstrap_script += _pad + "then\n"
        _bootstrap_script += _pad + "    redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " hset TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:PENDING:" + obj_attr_list["uuid"] + " cloud_init_bootstrap  true\n"
        _bootstrap_script += _pad + "fi\n"
        _bootstrap_script += _pad + "\n"
        _bootstrap_script += _pad + "counter=0\n\n"    
        _bootstrap_script += _pad + "while [[ \"$counter\" -le " + _attempts + " ]]\n"
        _bootstrap_script += _pad + "do\n"
        _bootstrap_script += _pad + "    rsync -az --delete --no-o --no-g --inplace rsync://" + _fshn + ':' + _fspn + '/' + _fsun + "_cb" + "/exclude_list.txt /tmp/exclude_list\n"
        _bootstrap_script += _pad + "    if [[ $? -eq 0 ]]\n"
        _bootstrap_script += _pad + "    then\n"
        _bootstrap_script += _pad + "        break\n"
        _bootstrap_script += _pad + "    else\n"    
        _bootstrap_script += _pad + "        sleep " + _sleep + "\n"
        _bootstrap_script += _pad + "        counter=\"$(( $counter + 1 ))\"\n"        
        _bootstrap_script += _pad + "    fi\n"
        _bootstrap_script += _pad + "done\n"
        _bootstrap_script += _pad + "counter=0\n\n"        
        _bootstrap_script += _pad + "while [[ \"$counter\" -le " + _attempts + " ]]\n"
        _bootstrap_script += _pad + "do\n"
        _bootstrap_script += _pad + "    rsync -az --exclude-from '/tmp/exclude_list' --delete --no-o --no-g --inplace rsync://" + _fshn + ':' + _fspn + '/' + _fsun + "_cb/ " +  obj_attr_list["remote_dir_path"] + "/\n"
        _bootstrap_script += _pad + "    if [[ $? -eq 0 ]]\n"
        _bootstrap_script += _pad + "    then\n"
        _bootstrap_script += _pad + "        redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " hset TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:PENDING:" + obj_attr_list["uuid"] + " cloud_init_rsync true\n"    
        _bootstrap_script += _pad + "        break\n"    
        _bootstrap_script += _pad + "    else\n"    
        _bootstrap_script += _pad + "        sleep " + _sleep + "\n"
        _bootstrap_script += _pad + "        counter=\"$(( $counter + 1 ))\"\n"    
        _bootstrap_script += _pad + "    fi\n"
        _bootstrap_script += _pad + "done\n"
        _bootstrap_script += _pad + "chown -R " + _rln + ':' + _rln + ' ' + obj_attr_list["remote_dir_path"] + "/\n" 
                
        _bootstrap_script += _pad + "\n"      
        _bootstrap_script += _pad + "\n"                    
        _bootstrap_script += _pad + "VMUUID=$(grep -ri " + obj_attr_list["experiment_id"] + " /var/lib/cloud/ | grep user-data | cut -d '/' -f 6 | head -n 1)\n"
        _bootstrap_script += _pad + "redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " publish TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:BOOT " + "\"VM $VMUUID is booted\"\n"
        _bootstrap_script += _pad + "exit 0\n"    
            
        return _bootstrap_script

    @trace                                                                        
    def generate_random_uuid(self, name = None, seed = '6cb8e707-0fc5-5f55-88d4-d4fed43e64a8') :
        '''
        TBD
        '''
        if not name  :        
            _uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,1000000000000000000)))).upper()
        else :
            _uuid = str(uuid5(UUID(seed), str(name))).upper()
        return _uuid

    @trace
    def generate_random_ip_address(self) :
        '''
        TBD
        '''
        _ip = ".".join(str(randint(1, 255)) for _octect in range(4))
        return _ip

    @trace       
    def generate_random_mac_address(self) :
        '''
        TBD
        '''
        _mac_template = [ 0x00, 0x16, 0x3e, randint(0x00, 0x7f), randint(0x00, 0xff), randint(0x00, 0xff) ]
        _mac = ':'.join(["%02x" % x for x in _mac_template])
        return _mac

    @trace       
    def generate_rc(self, cloud_name, obj_attr_list, extra_rc_contents) :
        '''
        TBD
        '''
        _file = obj_attr_list["generated_configurations_dir"] + '/' + obj_attr_list["username"] + "_cb_lastcloudrc"
            
        _file_fd = open(_file, 'w')

        _file_fd.write(extra_rc_contents)
        _file_fd.write("export CB_CLOUD_NAME=" + cloud_name + "\n")
        _file_fd.write("export CB_USERNAME=" + obj_attr_list["username"] + "\n")
        _file_fd.close()
        return True

    @trace
    def parse_cloud_connection_file(self, file_name) :
        '''
        TBD
        '''
        
        _parameter_map = {}
                    
        if file_name.count('~') :
            file_name = file_name.replace('~', os.path.expanduser('~'))

        if file_name.count('/') and not (file_name.count("http://") or file_name.count("https://")):
            if os.access(file_name, os.F_OK) :
                _msg = "    Attempting to parse cloud connection file \"" + file_name + "\"..."
                cbdebug(_msg, True)
                _fh = open(file_name, 'r')
                _contents = _fh.read()
                _fh.close()
                
                for _line in _contents.split('\n') :
                    if len(_line) :
                        if _line[0] != "#" :
                            if _line[0:7] == "export " :
                                _line = _line.replace("export ", '')
                
                            if _line.count("=") == 1 :
                                _key, _value = _line.split('=')
                                if _value.count("${") and _value.count(':') :
                                    _value = _value.split(':')[1][1:-1]
                                _parameter_map[_key] = _value.replace('"','')     
    
                _msg = "Done parsing cloud connection file \"" + file_name + "\"."
                cbdebug(_msg)
                    
        return _parameter_map

    @trace
    def set_cgroup(self, obj_attr_list) :
        '''
        TBD
        '''

        _status = 189
        _fmsg = "About to import libvirt...."

        _state_code2value = {}
        _state_code2value["1"] = "running"
        _state_code2value["2"] = "blocked"
        _state_code2value["3"] = "paused"
        _state_code2value["4"] = "shutdown"
        # Temporarily renaming "shutoff" to "save"
        _state_code2value["5"] = "save"
        _state_code2value["6"] = "crashed"


        _cgroups_mapping = {}
        _cgroups_mapping["mem_hard_limit"] = "memory.limit_in_bytes"
        _cgroups_mapping["mem_soft_limit"] = "memory.soft_limit_in_bytes"
        
        try :        

            import libvirt

            _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                    "HOST", \
                                                    True, \
                                                    obj_attr_list["host_name"], \
                                                    False)

            _hypervisor_type = str(_host_attr_list["hypervisor_type"]).lower()

            if _hypervisor_type == "qemu" :
                _astr = "/system"
            else :
                _astr = ""

            _host_name = _host_attr_list["cloud_hostname"]

            _host_ip = _host_attr_list["cloud_ip"]

            obj_attr_list["resource_limits"] = str2dic(obj_attr_list["resource_limits"].replace(';',',').replace('-',':'))

            _proc_man = ProcessManagement(username = "root", \
                                          hostname = _host_ip, \
                                          cloud_name = obj_attr_list["cloud_name"])

            for _key in obj_attr_list["resource_limits"] :

                _base_dir = obj_attr_list["cgroups_base_dir"]
                if _key.count("mem") :
                    _subsystem = "memory"

                # The cgroups/libvirt interface is currently broken (for memory limit
                # control). Will have to ssh into the node and set cgroup limits 
                # manually.
                
                _value = str(value_suffix(obj_attr_list["resource_limits"][_key]))

                _cmd = "echo " + _value + " > " + _base_dir + _subsystem +"/machine/"
                _cmd += obj_attr_list["instance_name"] + ".libvirt-" + _hypervisor_type
                _cmd += "/" + _cgroups_mapping[_key]

                _msg = "Altering the \"" + _cgroups_mapping[_key] + "\" parameter"
                _msg += " on the \"" +_subsystem + "\" subsystem on cgroups for"
                _msg += " instance \"" + obj_attr_list["instance_name"] + "\" with "
                _msg += " the value \"" + _value + "\"..."
                cbdebug(_msg, True)

                _status, _result_stdout, _fmsg = _proc_man.run_os_command(_cmd)
                
            if _host_name not in self.lvirt_conn or not self.lvirt_conn[_host_name] :        
                _msg = "Attempting to connect to libvirt daemon running on "
                _msg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\"...."
                cbdebug(_msg)

                self.lvirt_conn[_host_name] = libvirt.open( _hypervisor_type + "+tcp://" + _host_ip + _astr)
                
                _msg = "Connection to libvirt daemon running on hypervisor ("
                _msg += _hypervisor_type + ") \"" + _host_ip + "\" successfully established."
                cbdebug(_msg)

                instance_data = self.lvirt_conn[_host_name].lookupByName(obj_attr_list["instance_name"])

                obj_attr_list["lvirt_os_type"] = instance_data.OSType()

                obj_attr_list["lvirt_scheduler_type"] = instance_data.schedulerType()[0]
    
            # All object uuids on state store are case-sensitive, so will
            # try to just capitalize the UUID reported by libvirt
#                obj_attr_list["cloud_uuid"] = instance_data.UUIDString().upper()
#                obj_attr_list["uuid"] = obj_attr_list["cloud_uuid"]
#                obj_attr_list["cloud_lvid"] = instance_data.name()

            _gobj_attr_list = instance_data.info()

            obj_attr_list["lvirt_vmem"] = str(_gobj_attr_list[1])
            obj_attr_list["lvirt_vmem_current"] = str(_gobj_attr_list[2])
            obj_attr_list["lvirt_vcpus"] = str(_gobj_attr_list[3])

            _state_code = str(_gobj_attr_list[0])
            if _state_code in _state_code2value :
                obj_attr_list["lvirt_state"] = _state_code2value[_state_code]
            else :
                obj_attr_list["lvirt_state"] = "unknown"

            if _state_code == "1" :

                _vcpu_info = instance_data.vcpus()

                for _vcpu_nr in range(0, int(obj_attr_list["lvirt_vcpus"])) :
                    obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_pcpu"] = str(_vcpu_info[0][_vcpu_nr][3])
                    obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_time"] =  str(_vcpu_info[0][_vcpu_nr][2])
                    obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_state"] =  str(_vcpu_info[0][_vcpu_nr][1])
                    obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_map"] = str(_vcpu_info[1][_vcpu_nr])

                _sched_info = instance_data.schedulerParameters()

                obj_attr_list["lvirt_vcpus_soft_limit"] = str(_sched_info["cpu_shares"])

                if "vcpu_period" in _sched_info :
                    obj_attr_list["lvirt_vcpus_period"] = str(float(_sched_info["vcpu_period"]))
                    obj_attr_list["lvirt_vcpus_quota"] = str(float(_sched_info["vcpu_quota"]))
                    obj_attr_list["lvirt_vcpus_hard_limit"] = str(float(obj_attr_list["lvirt_vcpus_quota"]) / float(obj_attr_list["lvirt_vcpus_period"]))

                if "memoryParameters" in dir(instance_data) :    
                    _mem_info = instance_data.memoryParameters(0)

                    obj_attr_list["lvirt_mem_hard_limit"] = str(_mem_info["hard_limit"])
                    obj_attr_list["lvirt_mem_soft_limit"] = str(_mem_info["soft_limit"])
                    obj_attr_list["lvirt_mem_swap_hard_limit"] = str(_mem_info["swap_hard_limit"])

                if "blkioParameters" in dir(instance_data) :
                    _diskio_info = instance_data.blkioParameters(0)
                    obj_attr_list["lvirt_diskio_soft_limit"] = "unknown"
                    if _diskio_info :
                        if "weight" in _diskio_info :
                            obj_attr_list["lvirt_diskio_soft_limit"] = str(_diskio_info["weight"])

        except libvirt.libvirtError as msg :
            _fmsg = "Error while attempting to connect to libvirt daemon running on "
            _fmsg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\":"
            _fmsg += msg
            cberr(_fmsg)

        except ProcessManagement.ProcessManagementException as obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while attempting to set resource limits for " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)

            else :
                _msg = "Successfully set resource limits for " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)

            return _status, _msg

    @trace
    def process_script_output(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        _temp_dict = None

#        if "time_breakdown_keys" not in obj_attr_list :
#            obj_attr_list["time_breakdown_keys"] = ''

        if "execute_" + current_step + "_stdout" in obj_attr_list :
            if obj_attr_list["execute_" + current_step + "_stdout"].count("staging") or \
            obj_attr_list["execute_" + current_step + "_stdout"].count("tenant") or \
            obj_attr_list["execute_" + current_step + "_stdout"].count("namespace") :
                _temp_dict = str2dic(obj_attr_list["execute_" + current_step + "_stdout"].replace('\n',''), False)

        if _temp_dict :

            if obj_attr_list["name"].count("ai_") and current_step == "provision_originated":
                if "vm_extra_parms" not in obj_attr_list :
                    obj_attr_list["vm_extra_parms"] = ''                    
                else :
                    obj_attr_list["vm_extra_parms"] += ','
                                        
                for _key in list(_temp_dict.keys()) :
                    if not _key.count("staging") :
                        obj_attr_list["vm_extra_parms"] += _key + '=' + _temp_dict[_key] + ','
                    else :
                        obj_attr_list["vm_attach_action"] = _temp_dict["vm_staging"]
                        
                obj_attr_list["vm_extra_parms"] = obj_attr_list["vm_extra_parms"][0:-1]
                obj_attr_list.update(_temp_dict)
                        
            if obj_attr_list["name"].count("vm_") :
                obj_attr_list.update(_temp_dict)               

            '''
            print obj_attr_list["counter"]
            if obj_attr_list["counter"] == "1" :
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                  "GLOBAL", \
                                                  "time_breakdown_keys", \
                                                  False, \
                                                  "time_breakdown_keys", \
                                                  obj_attr_list["time_breakdown_keys"])
            '''    
        return True

    @trace
    def annotate_time_breakdown(self, obj_attr_list, name, start, diff = True) :
        '''
        TBD
        '''
        if "time_breakdown_keys" not in obj_attr_list :
            obj_attr_list["time_breakdown_keys"] = ''
            for _key in list(obj_attr_list.keys()) :
                if _key.count(obj_attr_list["model"]) and _key.count("_time") :
                    obj_attr_list["time_breakdown_keys"] += _key + ','
            
        _key_name = obj_attr_list["model"] + '_' + str(obj_attr_list["time_breakdown_step"]).zfill(3) + '_' + name
        obj_attr_list["time_breakdown_step"] = int(obj_attr_list["time_breakdown_step"]) + 1
        obj_attr_list["time_breakdown_keys"] += _key_name + ','
        
        if diff :  
            obj_attr_list[_key_name] = time() - start
        else :
            obj_attr_list[_key_name] = start

        if obj_attr_list["name"] == "vm_1" or obj_attr_list["name"] == "vm_10" :
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                              "GLOBAL", \
                                              "mon_defaults", \
                                              False, \
                                              "time_breakdown_keys", \
                                              obj_attr_list["time_breakdown_keys"])
        return True

    @trace
    def determine_instance_name(self, obj_attr_list) :
        '''
        TBD
        '''
        
        if "cloud_vm_name" not in obj_attr_list :
            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["cloud_name"]
            obj_attr_list["cloud_vm_name"] += '-' + "vm"
            obj_attr_list["cloud_vm_name"] += obj_attr_list["name"].split("_")[1]

            if "extended_instance_names" in obj_attr_list and str(obj_attr_list["extended_instance_names"]).lower() == "true" :
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

                if obj_attr_list["ai"] != "none" :
                    obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

                if "vm_name_suffix" in obj_attr_list :
                    obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"] + '-' + obj_attr_list["vm_name_suffix"]

        if "cloud_vv_name" not in obj_attr_list :       
            obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
            obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["cloud_name"]
            obj_attr_list["cloud_vv_name"] += '-' + "vv"
            obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
            obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]  

            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["ai_name"]  

        obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
        obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]

        obj_attr_list["volume_creation_failure_message"] = "none"
        obj_attr_list["volume_creation_status"] = 0
        
        return True

    @trace
    def determine_key_name(self, obj_attr_list, separator = '_') :
        '''
        TBD
        '''
        if "tenant" in obj_attr_list :
            _x = separator + obj_attr_list["tenant"] + separator
        else :
            _x = separator

        if separator != '_' :
            obj_attr_list["key_name"] = obj_attr_list["key_name"].replace('_', separator)
            
        if not obj_attr_list["key_name"].count(",") and not obj_attr_list["key_name"].count(obj_attr_list["username"] + '_') :
            obj_attr_list["key_name"] = obj_attr_list["username"] + separator + obj_attr_list["key_name"]

        return obj_attr_list["key_name"].split(",")

    @trace
    def pre_vmcreate_process(self, obj_attr_list, extra = None) :
        '''
        TBD
        '''
        if "meta_tags" in obj_attr_list :
            if obj_attr_list["meta_tags"] != "empty" and \
            obj_attr_list["meta_tags"].count(':') and \
            obj_attr_list["meta_tags"].count(',') :
                obj_attr_list["meta_tags"] = str2dic(obj_attr_list["meta_tags"])
            else :
                obj_attr_list["meta_tags"] = "empty"
        else :
            obj_attr_list["meta_tags"] = "empty"

        if str(obj_attr_list["key_name"]).lower() == "false" :
            obj_attr_list["key_name"] = None
    
        return True
    
    @trace
    def post_vmboot_process(self, obj_attr_list) :
        '''
        TBD
        '''
        if "meta_tags" in obj_attr_list :
            if obj_attr_list["meta_tags"] != "empty" :
                obj_attr_list["meta_tags"] = dic2str(obj_attr_list["meta_tags"])

        if "libcloud_image_inst" in obj_attr_list :
            del obj_attr_list["libcloud_image_inst"]

        if "libcloud_size_inst" in obj_attr_list :
            del obj_attr_list["libcloud_size_inst"]

        if "libcloud_location_inst" in obj_attr_list :
            del obj_attr_list["libcloud_location_inst"]

        if "libcloud_public_ip_inst" in obj_attr_list :
            del obj_attr_list["libcloud_public_ip_inst"]

        if "libcloud_vnic_inst" in obj_attr_list :
            del obj_attr_list["libcloud_vnic_inst"]

        if "instance_obj" in obj_attr_list :
            del obj_attr_list["instance_obj"]
        
        if "cloud_vv_instance" in obj_attr_list :
            del obj_attr_list["cloud_vv_instance"]

        if "k8s_instance" in obj_attr_list :
            del obj_attr_list["k8s_instance"]

        return True

    @trace
    def vmdestroy_repeat_and_check(self, obj_attr_list) :
        try :
            _status, _fmsg = self.vmdestroy(obj_attr_list)
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = obj.msg
        return _status, _fmsg

    @trace
    def vmdestroy_repeat(self, obj_attr_list) :
        '''
        We need to ensure that for any clouds which set DETACH_ATTEMPTS = -1 or > 1 that
        we try agressively to delete that resource before returning, or else we may be
        causing the user more money than they intended to spend.
        '''

        _fails_left = 0 # A really dumb unit testing mechanism. Has no effect at zero.
        _wait = int(obj_attr_list["update_frequency"])
        _max_detach_tries = int(obj_attr_list["detach_attempts"])
        _finished = False

        _status, _fmsg = self.vmdestroy_repeat_and_check(obj_attr_list)

        cbdebug(obj_attr_list["name"] + ": Starting with: " + str(_max_detach_tries))

        while not _finished and (_max_detach_tries > 0 or _max_detach_tries == -1) :
            if not _status and _fails_left == 0 :
                _finished = True
                break

            if _max_detach_tries > 0 :
                _max_detach_tries = _max_detach_tries - 1

            cbwarn(obj_attr_list["name"] + ": Attempts left: " + (str(_max_detach_tries) if _max_detach_tries >= 0 else "infinite"), True)

            if _max_detach_tries == 0 :
                break

            if _fails_left > 0 :
                _fails_left = _fails_left - 1
                cbwarn(obj_attr_list["name"] + ": Synthetic Problem with instance destroy, trying again...", True)
            else:
                cbwarn(obj_attr_list["name"] + ": Problem with instance destroy, trying again...", True)

            _wait = self.backoff(obj_attr_list, _wait)

            _status, _fmsg = self.vmdestroy_repeat_and_check(obj_attr_list)

        return _status, _fmsg

    @trace    
    def common_messages(self, obj_type, obj_attr_list, operation, status, failure_msg) :
        '''
        TBD
        '''
        if operation == "checking" :
            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC \"" + obj_attr_list["name"] + "\""
            if "endpoint" in obj_attr_list :
                _msg += " (endpoint \"" + obj_attr_list["endpoint"] + "\")"
            _msg += "...."
            cbdebug(_msg, True)
            return status, _msg

        if "cloud_name" in obj_attr_list :
            _full_cloud_id = " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" "

        _result = " was successfully "
        if status :
            _result = " could not be "

        if obj_type == "VMC" :

            if operation == "connected" :

                if status > 1 :
                    _msg = "VMC \"" + obj_attr_list["name"] + "\" did not pass the connection test."
                    _msg += "\" : " + failure_msg
                    cberr(_msg, True)
                    raise CldOpsException(_msg, status)
                else :
                    _msg = "VMC \"" + obj_attr_list["name"] + "\" was successfully tested.\n"
                    cbdebug(_msg, True)
                    return status, _msg
            
            if operation == "cleaned up" or operation == "registered" or operation == "unregistered" :
                _full_obj_id = "VMC " + obj_attr_list["name"] 
                if "uuid" in obj_attr_list : 
                    _full_obj_id += " (" + obj_attr_list["uuid"] + ")"
                
                if status :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                    cberr(_msg)
                    raise CldOpsException(_msg, status)
                else :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id
                    if operation == "cleaned up" :
                        cbdebug(_msg)
                    else :
                        cbdebug(_msg, True)                    
                    return status, _msg
                
            if operation == "cleaning up vms" :
                _msg = "(" + str(obj_attr_list["tenant"] if "tenant" in obj_attr_list else "default") + ") " + "Removing all VMs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VM names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)                
                return status, _msg

            if operation == "cleaning up vvs" :
                _msg = "(" + str(obj_attr_list["tenant"] if "tenant" in obj_attr_list else "default") + ") " + "Removing all VVs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VV names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)              
                return status, _msg

        elif obj_type == "HOST" :
            _full_obj_id = "HOST set belonging to VMC " + obj_attr_list["name"] + " (" + obj_attr_list["uuid"] + ")"
            
            if status :
                _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                cberr(_msg)
                raise CldOpsException(_msg, status)
            else :
                _msg = _full_obj_id + _result + operation + _full_cloud_id
                cbdebug(_msg)                    
                return status, _msg

        elif obj_type == "VM" :
            _full_obj_id = obj_attr_list["name"] + " (" + obj_attr_list["cloud_vm_uuid"] + ")"

            if operation == "creating" :
                _msg = "Starting instance \"" + obj_attr_list["cloud_vm_name"] 
                _msg += "\" on " + self.get_description()
                _msg += ", using the image \"" + str(obj_attr_list["imageid1"]) + "\""
                _msg += " (" + str(obj_attr_list["boot_volume_imageid1"])
                
                if "hypervisor_type" in obj_attr_list :
                    _msg += ' ' + obj_attr_list["hypervisor_type"]
                    
                _msg += ") and size \"" + obj_attr_list["size"] + "\"" 
                if "flavor" in obj_attr_list :
                    _msg += " (" + str(obj_attr_list["flavor"]) + ")"

                if obj_attr_list["nest_containers_enabled"].strip().lower() == "true" :
                    _msg += ", container: " + obj_attr_list["container_role"]

                if "availability_zone" in obj_attr_list :
                    if str(obj_attr_list["availability_zone"]).lower() != "none" :
                        _msg += ", on the availability zone \"" + str(obj_attr_list["availability_zone"]) + "\""

                if "block_device_mapping" in obj_attr_list :    
                    if len(obj_attr_list["block_device_mapping"]) :
                        _msg += ", with \"block_device_mapping=" + str(obj_attr_list["block_device_mapping"]) + "\""

                if obj_attr_list["prov_netname"] == obj_attr_list["run_netname"] :
                    _msg += ", connected to network \"" + obj_attr_list["prov_netname"] + "\""
                else :                
                    _msg += ", connected to networks \"" + obj_attr_list["prov_netname"]
                    _msg += "\" and \"" + obj_attr_list["run_netname"] + "\""
                    
                _msg += ", on VMC \"" + obj_attr_list["vmc_name"] + "\""

                if "host_name" in obj_attr_list :
                    _msg += " (host \"" + obj_attr_list["host_name"] + "\")"
                
                if "tenant" in obj_attr_list :
                    _msg += ", under tenant \"" + obj_attr_list["tenant"] + "\""
                                        
                _msg += ", injecting the contents of the pub ssh key \""
                _msg += str(obj_attr_list["key_name"]) + "\" (userdata is \""
                _msg += str(obj_attr_list["config_drive"]) + "\")."
                cbdebug(_msg, True)
                return '', ''

            if operation == "destroying" :
                _msg = "Sending a termination request for instance "  + obj_attr_list["cloud_vm_name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)                
                return '',''

            if operation == "capturing" :
                _msg = "Waiting for instance " + obj_attr_list["cloud_vm_name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)                
                return '',''

            if operation == "runstate altering" :
                _msg = "Sending a runstate change request (from \"" 
                _msg += obj_attr_list["current_state"] + "\" to \"" 
                _msg += obj_attr_list["target_state"] + "\") for " + obj_attr_list["cloud_vm_name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)                
                return '',''
            
            if operation == "migrating" :
                _msg = "Sending a " + obj_attr_list["mtype"] + " request for instance "  + obj_attr_list["cloud_vm_name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
                return '',''
            
            if operation == "created" :
                
                obj_attr_list["instance_creation_status"] = status
                obj_attr_list["instance_creation_failure_message"] = "none"
                                
                if status :
                    obj_attr_list["instance_creation_failure_message"] = failure_msg 
                    
                    _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
    
                    if str(obj_attr_list["leave_instance_on_failure"]).lower() == "true" :
                        _msg += " (Will leave the VM running due to experimenter's request)"
                        cberr(_msg, True)
                    else :
                        _msg += " (The VM creation will be rolled back)"
                        cberr(_msg, True)
                        
                        obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                        self.vmdestroy_repeat(obj_attr_list)
                            
                    raise CldOpsException(_msg, status)
                
                else :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id
                    cbdebug(_msg)
                    return status, _msg            
            else :
                if status :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                    cberr(_msg, True)
                    raise CldOpsException(_msg, status)
                else :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id
                    cbdebug(_msg)
                    return status, _msg

        elif obj_type == "VV" :

            if operation == "creating" :
    
                _msg = "Creating volume \"" + obj_attr_list["cloud_vv_name"] + "\""                    
                _msg += ", type \"" + str(obj_attr_list["cloud_vv_type"]) + "\""
                if str(obj_attr_list["boot_from_volume"]).lower() == "true" and obj_attr_list["cloud_vv_name"].count("-vbv") :
                    _msg += ", from image \"" + obj_attr_list["imageid1"] + "\" (boot_volume)"
                else :                
                    _msg += ", with size " + str(obj_attr_list["cloud_vv"]) + " GB,"
                _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
                cbdebug(_msg, True)
                return '', ''

            if operation == "attaching" :
                _msg = "Attaching the newly created Volume \""
                _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                cbdebug(_msg, True)
                return '', ''

            if operation == "detaching" :
                _msg = "Detaching the Volume \""
                _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vv_uuid"] + "\") from instance \""
                _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                cbdebug(_msg, True)
                return '', ''

            if operation == "destroying" :
                _msg = "Sending a destruction request for the "
                _msg += "volume \"" + obj_attr_list["cloud_vv_name"] + "\" ("
                _msg += "cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] 
                _msg += ") previously attached to \"" + obj_attr_list["cloud_vm_name"] + "\""
                _msg += " (cloud-assigned uuid " 
                _msg += obj_attr_list["cloud_vm_uuid"] + ")...."
                cbdebug(_msg, True)
                return '', ''

            else :                        
                                
                _full_obj_id = "Volume " + obj_attr_list["cloud_vv_name"]
                _full_obj_id += " (" + obj_attr_list["cloud_vv_uuid"] + "), to be "
                _full_obj_id += "attached to " +  obj_attr_list["cloud_vm_name"] 

                if operation == "created" :
                    obj_attr_list["volume_creation_status"] = status
                    obj_attr_list["volume_creation_failure_message"] = "none"
                                        
                if status :
                    if operation == "created" :                        
                        obj_attr_list["volume_creation_failure_message"] = failure_msg
                        
                    _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                    cberr(_msg, True)
                    raise CldOpsException(_msg, status)
                else :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id
                    cbdebug(_msg)
                    return status, _msg

        elif obj_type == "IMG" :
            if operation == "deleting" :
                _msg = "Sending a deletion request for the image \"" + obj_attr_list["name"]
                _msg += "\"" + _full_cloud_id
                cbdebug(_msg, True)
                return '', ''                
            else :                                
                _full_obj_id = "Image " + str(obj_attr_list["imageid1"])
                _full_obj_id += " (" + str(obj_attr_list["boot_volume_imageid1"]) + ")"
                
                if status :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                    cberr(_msg, True)
                    raise CldOpsException(_msg, status)
                else :
                    _msg = _full_obj_id + _result + operation + _full_cloud_id
                    cbdebug(_msg, True)
                    return status, _msg

        elif obj_type == "AI" :
            _full_obj_id = obj_attr_list["name"] + " (" + obj_attr_list["uuid"] + ")"

            if operation == "defined" :
                _x_msg = " (will now be fully deployed)"
            else :
                _x_msg = ''
                            
            if status :
                _msg = _full_obj_id + _result + operation + _full_cloud_id + ":  " + failure_msg
                cberr(_msg, True)
                raise CldOpsException(_msg, status)
            else :
                _msg = _full_obj_id + _result + operation + _full_cloud_id + _x_msg
                cbdebug(_msg, True)                    
                return status, _msg

        return '', ''

    @trace        
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"          
            self.take_action_if_requested("AI", obj_attr_list, current_step)                    
            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("AI", obj_attr_list, "defined", _status, _fmsg)
            return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0            
            self.take_action_if_requested("AI", obj_attr_list, current_step)            

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("AI", obj_attr_list, "undefined", _status, _fmsg)
            return _status, _msg

    @trace
    def backoff(self, obj_attr_list, delay) :
        # Sleep and simply double the delay
        sleep(delay)
        if "max_backoff" in obj_attr_list and str(obj_attr_list["max_backoff"]).lower() != "false" :
            delay = min(delay * 2, int(obj_attr_list["max_backoff"]))
            cbdebug("Backoff increased to " + str(delay) + " seconds.", False if "update_frequency" in obj_attr_list and (delay > (int(obj_attr_list["update_frequency"]) * 2)) else True)
        return delay
    
    @trace    
    def ship_cloud_init_iso(self, obj_attr_list) :
        '''
        TBD
        '''

        _cloud_init_contents = {}
        _cloud_init_contents["meta-data"] = "instance-id: " + str(obj_attr_list["cloud_vm_name"]) + "\n"
        _cloud_init_contents["meta-data"] += "local-hostname: " + str(obj_attr_list["cloud_vm_name"]) + "\n"

        _cloud_init_contents["user-data"] = self.populate_cloudconfig(obj_attr_list)

        _cloud_init_instance_path = "/tmp/" + str(obj_attr_list["cloud_vm_name"])

        if not os.path.exists(_cloud_init_instance_path) :
            os.makedirs(_cloud_init_instance_path)

        try:
            for _file in [ "user-data", "meta-data" ] :
                _cloud_init_fn = _cloud_init_instance_path + '/' + _file
                _cloud_init_fd = open(_cloud_init_fn, 'w')
                _cloud_init_fd.write(_cloud_init_contents[_file])
                _cloud_init_fd.close()
                os.chmod(_cloud_init_fn, 0o644)

        except IOError as msg :
            _msg = "######Error writing file \"" + _cloud_init_fn  + "\":" + str(msg)
            cberr(_msg, True, False)
            exit(4)

        except OSError as msg :
            _msg = "######Error writing file \"" + _cloud_init_fn  + "\":" + str(msg)
            cberr(_msg, True, False)
            exit(4)

        except Exception as e :
            _msg = "######Error writing file \"" + _cloud_init_fn  + "\":" + str(e)
            cberr(_msg, True, False)
            exit(4)

        _proc_man = ProcessManagement()

        _iso_fn = str(obj_attr_list["cloud_vm_name"]) + ".iso"

        _geniso_cmd = "cd " + _cloud_init_instance_path + "; "
        _geniso_cmd += "genisoimage -output " + _iso_fn
        _geniso_cmd += " -volid cidata -joliet -rock user-data meta-data; "
        _geniso_cmd += "scp " +  _cloud_init_instance_path + '/' + _iso_fn
        _geniso_cmd += ' ' + obj_attr_list["host_remote_user"] + "@" + obj_attr_list["host_cloud_ip"] + ":" + obj_attr_list["host_remote_dir"] + _iso_fn

        _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_geniso_cmd)

        return True
