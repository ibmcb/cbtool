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

from lib.auxiliary.data_ops import str2dic, dic2str
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import Nethashget
from lib.stores.redis_datastore_adapter import RedisMgdConn
    
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

    @trace
    def get_svm_stub(self, obj_attr_list) :
        '''
        TBD
        '''
        if "svm_stub_ip" in obj_attr_list :
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
            
            if self.is_vm_ready(obj_attr_list) :
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - time_mark_prs
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "Booting...")
                break
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "still not ready. Will wait for " + str(_wait)
                _msg += " seconds and check again."
                cbdebug(_msg)
                sleep(_wait)
                _curr_tries += 1
    
        if _curr_tries < _max_tries :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "started successfully, got IP address " + obj_attr_list["cloud_ip"]
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

        if "real_ip" in obj_attr_list and obj_attr_list["real_ip"] == "False" :
            _network_reachable = True
        else :
            if not self.get_svm_stub(obj_attr_list) :
                _network_reachable = False 
            else: 
                _network_reachable = True

        _curr_tries = 0

        if not _network_reachable :
            _msg = "Trying to establish network connectivity to "
            _msg +=  obj_attr_list["name"] + " (cloud-assigned uuid "
            _msg += obj_attr_list["cloud_uuid"] + "), on IP address "
            _msg += obj_attr_list["cloud_ip"] + "..."
            cbdebug(_msg, True)

            _nh_conn = Nethashget(obj_attr_list["cloud_ip"])
            sleep(_wait)
            while not _network_reachable and _curr_tries < _max_tries :

                if "async" not in obj_attr_list or obj_attr_list["async"].lower() == "false" :
                    if threading.current_thread().abort :
                        _msg = "VM Create Aborting..."
                        _status = 123
                        raise CldOpsException(_msg, _status)

                if _nh_conn.check_port(22, "TCP") :
                    obj_attr_list["mgt_004_network_acessible"] = int(time()) - time_mark_prc 
                    self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "Network accessible now. Continuing...")
                    _network_reachable = True
                    break
                else :
                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                    _msg += "still not network reachable. Will wait for " + str(_wait)
                    _msg += " seconds and check again."
                    cbdebug(_msg)
                    sleep(_wait)
                    _curr_tries += 1

        else :
            _msg = "Fake trying to establish network connectivity to "
            _msg +=  obj_attr_list["name"] + " (cloud-assigned uuid "
            _msg += obj_attr_list["cloud_uuid"] + "), on IP address "
            _msg += obj_attr_list["cloud_ip"] + "..."
            cbdebug(_msg, True)
            sleep(_wait)
            obj_attr_list["mgt_004_network_acessible"] = int(time()) - time_mark_prc 
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "Network accessible now. Continuing...")

        if _curr_tries < _max_tries :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "is network reachable (boot process finished successfully)"
            cbdebug(_msg)
            obj_attr_list["arrival"] = int(time())

            # It should be mgt_006, NOT mgt_005
            obj_attr_list["mgt_006_application_start"] = "0"
            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "Application starting up...")
        else :
            _msg = "" + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
            _msg += "is not network reachable after " + str(_max_tries * _wait) + " seconds.... "
            _msg += "Giving up."
            cberr(_msg, True)
            raise CldOpsException(_msg, 89)

    @trace
    def pause_on_attach_if_requested(self, obj_attr_list):
        '''
        TBD
        '''
        if obj_attr_list["staging"] != "pause_on_vm_attach" :
            return

        if "pause_complete" in obj_attr_list :
            return

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], "VM", "pause_on_attach")
            target_uuid = obj_attr_list["ai"] if obj_attr_list["ai"] != "none" else obj_attr_list["uuid"]
            self.osci.publish_message(obj_attr_list["cloud_name"], "VM", "pause_on_attach", target_uuid + ";vmready;" + dic2str(obj_attr_list), 1, 3600)
            cbdebug("VM " + obj_attr_list["cloud_uuid"] + " pausing on attach for continue signal ....")
            for message in sub_channel.listen() :
                args = str(message["data"]).split(";")
                if len(args) != 3 :
                    cbdebug("Message is not for me: " + str(args))
                    continue
                uuid, status, info = args
                if target_uuid == uuid and status == "continue" :
                    _status = 0
                    obj_attr_list["pause_complete"] = True
                    break
            sub_channel.unsubscribe()

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        finally :
            if _status :
                _msg = "Error while pause_on_attach: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Finished pause_on_attach for " + self.get_description()
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
