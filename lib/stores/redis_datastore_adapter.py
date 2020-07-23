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
    Created on Jan 29, 2011

    Redis data management operations library

    @author: Marcio A. Silva
'''

import os
import traceback

from time import sleep, time
from random import randint
from os import path
from pwd import getpwuid
from datetime import datetime

from redis import Redis, ConnectionError, ResponseError
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import makeTimestamp
from lib.auxiliary.config import get_my_parameters, set_my_parameters 

class RedisMgdConn :
    '''
    TBD
    '''

    @trace
    def __init__(self, parameters) :
        # For the moment, it's safe to assume one unique username
        # per CLI process or API process
        self.pid = self.experiment_inst = "TEST_" + getpwuid(os.getuid())[0]
        set_my_parameters(self, parameters)
        self.redis_conn = False
        makeTimestamp()

    def oscp(self) :
        return get_my_parameters(self)

    class ObjectStoreMgdConnException(Exception):
        '''
        TBD
        '''
        def __init__(self, msg, status):
            Exception.__init__(self)
            self.msg = msg
            self.status = status
        def __str__(self):
            return self.msg

    @trace
    def connect(self, tout) :
        '''
        TBD
        '''    
        _test_key = str(randint(0, 100000000000000))
        _test_value = '1'  

        try:

            if tout > 0:
                self.redis_conn = Redis(host = self.host, port = self.port, \
                                        db = self.dbid, password = None, \
                                        socket_timeout = tout, decode_responses=True)
            else :
                self.redis_conn = Redis(host = self.host, port = self.port, \
                                        db = self.dbid, password = None, decode_responses=True)

            self.redis_conn.set(_test_key, _test_value)
            self.redis_conn.delete(_test_key)   
            _msg = "A connection with the Redis server on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.dbid) + ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)
            return self.redis_conn

        except ConnectionError as msg :
            _msg = "Unable to establish a connection with the Redis "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.dbid) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 74)

    @trace
    def disconnect(self) :
        '''
        TBD
        '''    

        try:

            if self.redis_conn :
                self.redis_conn.connection_pool.disconnect()

            _msg = "A connection with the Redis server on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.dbid) + ", was terminated."
            cbdebug(_msg)
            return True

        except ConnectionError as msg :
            _msg = "Unable to terminate a connection with the Redis "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.dbid) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 75)

    @trace
    def conn_check(self) :
        '''
        TBD
        '''
        if not self.redis_conn :
            try :
                self.connect(self.timout)
            except self.ObjectStoreMgdConnException as obj :
                raise self.ObjectStoreMgdConnException(obj.msg, 3)

    @trace        
    def initialize_object_store(self, cloud_name, cloud_kv_list, cond) :
        '''
        TBD
        '''
        self.conn_check()

        obj_inst = self.experiment_inst + ":" + cloud_name

        try :

            if cond :
                if self.redis_conn.sismember(self.experiment_inst + ":CLOUD", cloud_name) :
                    # When the Object Store does not get initialized, we need to get 
                    # the experiment id from there.
                    _time_attr_list = self.get_object(cloud_name, "GLOBAL", False, "time", False)
                    cloud_kv_list["time"]["experiment_id"] = _time_attr_list["experiment_id"]
                    
                    _msg = "The cloud \"" + cloud_name + "\" is "
                    _msg += "already instantiated on this object store. It "
                    _msg += "does not need to be explicitly instantiated again."
                    cbdebug(_msg)
                    return False
                else :
                    cloud_kv_list["time"]["experiment_id"] = "EXP"

            self.redis_conn.sadd(self.experiment_inst + ":CLOUD", cloud_name)

            for _key in list(cloud_kv_list["ai_templates"].keys()) :
                if _key.count("_sut") :
                    _actual_ai_type_name = _key.replace("_sut", '')

                    _roles = cloud_kv_list["ai_templates"][_actual_ai_type_name + "_sut"].split('->')

                    _role_list = ''
                    for _role in _roles :
                        _role = _role.split("_x_")
                        if len(_role) == 2 :
                            _role_list += _role[1] + ','
                        else :
                            _role_list += _role[0] + ','                            

                    cloud_kv_list["ai_templates"][_actual_ai_type_name + "_role_list"] = _role_list[0:-1]

            _cld_attrs = cloud_kv_list["query"]["cloud_attributes"].split(',')
            for _cld_attr in _cld_attrs :
                self.redis_conn.hset(self.experiment_inst + ":CLOUD:" + \
                                     cloud_name, _cld_attr, \
                                     cloud_kv_list[_cld_attr])

            for _object_type in cloud_kv_list["query"]["object_type_list"].split(',') :
                if _object_type.lower() in cloud_kv_list["query"] :
                    for _view_type in cloud_kv_list["query"][_object_type.lower() ].split(',') :
                        self.redis_conn.zadd(obj_inst + ':' + _object_type + ":VIEW", {_view_type: 1})

            _global_objects_list = cloud_kv_list["setup"]["global_object_list"].split(',')

            for _global_object in _global_objects_list :

                if _global_object.upper() == "TIME" :
                    cloud_kv_list[_global_object]["experiment_id"] = \
                    ((cloud_kv_list[_global_object]["experiment_id"] + \
                      '-' + makeTimestamp().replace(' ', '-')).replace('/',\
                                                                       '-')).replace(':',\
                                                                                     '-')
                if _global_object == "fi_templates" :
                    for _key in list(cloud_kv_list[_global_object].keys()) :
                        cloud_kv_list[_global_object][_key] = \
                        cloud_kv_list[_global_object][_key].replace("___", ' ')

                self.create_object(cloud_name, "GLOBAL", _global_object, \
                                   cloud_kv_list[_global_object], False, False)

            for _object_type in cloud_kv_list["query"]["object_type_list"].split(',') :
                _criterion_list = cloud_kv_list["query"][_object_type.lower()].replace(',', ' or ')
                _criterion_list = _criterion_list.replace("BY", '')
                self.add_to_list(cloud_name, "GLOBAL", "view_criteria", (_object_type + ':' + _criterion_list).lower())

            for _key in list(cloud_kv_list["ai_templates"].keys()) :
                if _key.count("_sut") :
                    _actual_ai_type_name = _key.replace("_sut", '')

                    for _key_suffix in ["load_profile", "sut", \
                                        "load_generator_role", "load_manager_role",\
                                        "metric_aggregator_role", "capture_role",\
                                        "load_profile", "load_level",\
                                        "load_duration", "profiles", "category" ] :

                        if _actual_ai_type_name + '_' + _key_suffix not in cloud_kv_list["ai_templates"] :
                            _msg = "The AI type \"" + _actual_ai_type_name + "\""
                            _msg += " is missing the mandatory parameter \"" 
                            _msg += _key_suffix + "\"." 
                            raise self.ObjectStoreMgdConnException(str(_msg), 90)

                        _category = _actual_ai_type_name + '_' + _key_suffix

                    if path.exists(cloud_kv_list["space"]["scripts_dir"] + '/' + _actual_ai_type_name) :
                        self.add_to_list(cloud_name, "GLOBAL", "ai_types", _actual_ai_type_name)

                        _typelist_entry = cloud_kv_list["ai_templates"][_category] 
                        _typelist_entry += '/' + _actual_ai_type_name 
                        _typelist_entry += " (" + cloud_kv_list["ai_templates"][_actual_ai_type_name + "_profiles"].replace(',',", ") + ")"

                        self.add_to_list(cloud_name, "GLOBAL", "ai_types", _typelist_entry)

            if "aidrs_templates" in cloud_kv_list :
                for _key in list(cloud_kv_list["aidrs_templates"].keys()) :
                    if _key.count("_type") :
                        self.add_to_list(cloud_name, "GLOBAL", "aidrs_patterns", _key.replace("_type", ''))

            if "vmcrs_templates" in cloud_kv_list :
                for _key in list(cloud_kv_list["vmcrs_templates"].keys()) :
                    if _key.count("_scope") :
                        self.add_to_list(cloud_name, "GLOBAL", "vmcrs_patterns", _key.replace("_scope", ''))

            if "firs_templates" in cloud_kv_list :
                for _key in list(cloud_kv_list["firs_templates"].keys()) :
                    if _key.count("_scope") :
                        self.add_to_list(cloud_name, "GLOBAL", "firs_patterns", _key.replace("_scope", ''))
            
            if "fi_templates" in cloud_kv_list :
                for _key in list(cloud_kv_list["fi_templates"].keys()) :
                    if _key.count("_fault") :
                        self.add_to_list(cloud_name, "GLOBAL", "fi_situations", _key.replace("_fault", ''))

            if "vm_templates" in cloud_kv_list :
                for _key in list(cloud_kv_list["vm_templates"].keys()) :
                    self.add_to_list(cloud_name, "GLOBAL", "vm_roles", _key)

            self.reset_counters(cloud_name, cloud_kv_list)

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 93)

        except ResponseError as msg :
            _msg = "Unable to initialize the contents of the Redis "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + " database " + str(self.dbid) + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 76)

    def reset_counters(self, cloud_name, cloud_kv_list, reset_exp_counter = True, counter_list = None) :
        '''
        TBD
        '''
        self.conn_check()

        obj_inst = self.experiment_inst + ":" + cloud_name
        
        try :

            if reset_exp_counter :
                self.redis_conn.set(obj_inst + ":GLOBAL:experiment_counter", "0")
            
            if not counter_list :
                _object_list = cloud_kv_list["query"]["object_type_list"].upper().split(',')
                _query_list = cloud_kv_list["query"]["object_type_list"]
            else :
                _object_list = counter_list.split(',')
                _query_list = _object_list
            
            for _object_type in _object_list :
                if _object_type in _query_list :
                    _counters = ["COUNTER", "ARRIVED", "DEPARTED", "FAILED", "RESERVATIONS"]
                    for _counter in _counters :
                        _obj_count_fn = obj_inst + ':' + _object_type + ':' + _counter
                        self.redis_conn.set(_obj_count_fn, 0)

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 6)

        except ResponseError as msg :
            _msg = "Unable to initialize the contents of the Redis "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + " database " + str(self.dbid) + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 77)

    @trace
    def flush_object_store(self, cloud_name = None) :
        '''
        'cloud_name' is used if we're using a shared Redis database, don't simply drop the entire database, but instead only flush the keys identified by the cloud name in question.
        '''
        self.conn_check()
        if cloud_name is None :
            self.redis_conn.flushdb()
        else :
            cloud_name = cloud_name.upper()
            # use an iterator
            _dropped = 0
            try :
                for key in self.redis_conn.scan_iter("*" + cloud_name + "*") :
                    parts = key.split(":")
                    # Do not delete keys where cloud names have matching substrings.
                    for part in parts :
                        # Only delete the exact cloud name
                        if part == cloud_name :
                            _dropped += 1
                            self.redis_conn.delete(key)
                            break
                _members = self.redis_conn.smembers(self.experiment_inst + ":CLOUD")
                cbdebug("Dropped " + str(_dropped) + " keys for cloud " + cloud_name)
                for _member in _members :
                    if _member == cloud_name :
                        cbdebug("Dropped cloud " + cloud_name)
                        self.redis_conn.srem(self.experiment_inst + ":CLOUD", cloud_name)
                        break
            except Exception as e :
                raise self.ObjectStoreMgdConnException("Failed to cleanup object store using cloud name: " + cloud_name + ": " + str(e), 83)

    @trace
    def clean_object_store(self, cloud_name, cloud_kv_list) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        try :

            _query = self.get_object(cloud_name, "GLOBAL", False, "query", False)

            _global_objects_list = cloud_kv_list["all"].split(',')
            
            for _global_object in _global_objects_list :
                _x_attr_list = {} 
                self.destroy_object(cloud_name, "GLOBAL", _global_object, _x_attr_list, False)

            self.redis_conn.srem(self.experiment_inst + ":CLOUD", cloud_name)
            self.redis_conn.delete(self.experiment_inst + ":CLOUD:" + cloud_name)

            for _object_type in _query["object_type_list"].split(',') :
                _obj_fn = obj_inst + ':' + _object_type
                self.redis_conn.delete(_obj_fn + ":RESERVATIONS")
                self.redis_conn.delete(_obj_fn + ":TAG")
                self.redis_conn.delete(_obj_fn + ":VIEW")
                self.redis_conn.delete(_obj_fn + ":DEPARTED")
                self.redis_conn.delete(_obj_fn + ":ARRIVED")
                self.redis_conn.delete(_obj_fn + ":FAILED")
                self.redis_conn.delete(_obj_fn + ":COUNTER")

                _finished_tracking_uuids = self.get_object_list(cloud_name, "FINISHEDTRACKING" + _object_type)
                if _finished_tracking_uuids :
                    for _finished_tracking_uuid in _finished_tracking_uuids :
                        self.redis_conn.delete(obj_inst + ":FINISHEDTRACKING" + _object_type + ':' + _finished_tracking_uuid)
                self.redis_conn.delete(obj_inst + ":FINISHEDTRACKING" + _object_type)

                for _view_type in _query[_object_type.lower() ].split(',') :
                    self.redis_conn.delete(obj_inst + ':' + _object_type + ":VIEW:" + _view_type)

            self.redis_conn.delete(obj_inst + ":GLOBAL:experiment_counter")
            self.redis_conn.delete(obj_inst + ":GLOBAL:vmc_pools")
            self.redis_conn.delete(obj_inst + ":GLOBAL:host_names")
            self.redis_conn.delete(obj_inst + ":GLOBAL:aidrs_patterns")
            self.redis_conn.delete(obj_inst + ":GLOBAL:vmcrs_patterns")
            self.redis_conn.delete(obj_inst + ":GLOBAL:firs_patterns")
            self.redis_conn.delete(obj_inst + ":GLOBAL:ai_types")
            self.redis_conn.delete(obj_inst + ":GLOBAL:view_criteria")
            self.redis_conn.delete(obj_inst + ":GLOBAL:vm_roles")
            self.redis_conn.delete(obj_inst + ":GLOBAL")

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 7)

        except ResponseError as msg :
            _msg = "Unable to flush the contents of the Redis "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + " database " + str(self.dbid) + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 78)
    
    @trace    
    def update_cloud(self, cloud_name, cld_attrs) :
        '''
        TBD
        '''
        self.conn_check()

        try :
            for attr in list(cld_attrs.keys()) :
                self.redis_conn.hset(self.experiment_inst + ":CLOUD:" + \
                                     cloud_name, attr, cld_attrs[attr])

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 8)

        except ResponseError as msg :
            _msg = "Unable to update cloud attributes for "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + " database " + str(self.dbid) + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 79)

    @trace
    def signal_api_refresh(self, cloud_name) :
        '''
        TBD
        '''
        self.conn_check()
        try :
            _cloud_parameters = self.get_object(cloud_name, "CLOUD", False, cloud_name, False)
            _cloud_parameters["client_should_refresh"] = str(time())
            self.update_cloud(cloud_name, _cloud_parameters)
        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 9)

        except ResponseError as msg :
            _msg = "Failed to signal API refresh! "  + msg
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 10)
            
    @trace
    def object_exists(self, cloud_name, obj_type, obj_id, can_be_tag, check_timeout = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        if obj_type == "CLOUD" :
            _obj_inst_fn = self.experiment_inst + ":" + obj_type
        else :
            _obj_inst_fn = obj_inst + ":" + obj_type
        _obj_id_fn = _obj_inst_fn + ":" + obj_id
        _obj_uuid = obj_id    

        try :
            if can_be_tag :
                _obj_uuid = False

                _query_object = self.get_object(cloud_name, "GLOBAL", False, "query", False)

                _mandatory_tags = _query_object["mandatory_tags"].split(',')

                for _tag in _mandatory_tags :
                    _tag = _tag.upper()
                    _tag_inst_fn = obj_inst + ":" + obj_type + ':TAG:' + _tag
                    _obj_tag_fn = _tag_inst_fn + ":" + obj_id

                    _obj_exists = self.redis_conn.sismember(_tag_inst_fn, \
                                                            obj_id)
                    if _obj_exists :
                        _msg = obj_type + " object with the tag \"" + _tag
                        _msg += "\" = \"" + obj_id + "\" was retrieved from the"
                        _msg += " tag list (FQTN:" + _tag_inst_fn + ")."
                        cbdebug(_msg)
                        _obj_id_fn = self.redis_conn.get(_obj_tag_fn)
                        _obj_uuid = _obj_id_fn.split(':')[3]
                        break

            if _obj_uuid :
                _obj_exists = self.redis_conn.sismember(_obj_inst_fn, _obj_uuid)
            else :
                _obj_uuid = obj_id
                _obj_exists = self.redis_conn.sismember(_obj_inst_fn, obj_id)
                
            if _obj_exists :
                if check_timeout :
                    if not self.redis_conn.exists(_obj_id_fn) :
                        _obj_exists = False

            if _obj_exists :
                _msg = obj_type + " object " + obj_id + " exists (UUID: " + _obj_uuid + "). "
                cbdebug(_msg)
                return _obj_uuid
            else :
                _msg = obj_type + " object " + obj_id + " does not exist."
                cbdebug(_msg)
                return False

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            raise e

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 11)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_id + "'s existence could not be " 
            _msg += "checked: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 12)

    @trace
    def create_object(self, cloud_name, obj_type, obj_uuid, obj_attr_list, lock, cond, \
                      expiration = False) :
        '''
        TBD
        '''

        self.conn_check()

        obj_inst = self.experiment_inst + ":" + cloud_name
        self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + obj_uuid
        _max_vms_per_vmc = False

        try :

            if lock :
                _create_lock = self.acquire_lock(cloud_name, obj_type, \
                                                 obj_uuid, "create_object", 1)    
            if cond :
                if self.object_exists(cloud_name, obj_type, obj_uuid, False) :
                    _msg = obj_type + " object " + obj_uuid + " could not be "
                    _msg += "added to object list because it already exists "
                    _msg += "there (FQIN: " + _obj_inst_fn + ")." 
                    cberr(_msg)
                    raise self.ObjectStoreMgdConnException(str(_msg), 13)

            self.redis_conn.sadd(_obj_inst_fn, obj_uuid)
            _msg = obj_type + " object " + obj_uuid + " added to object list "
            _msg += "(FQIN " + _obj_inst_fn + ")."
            cbdebug(_msg)

            for _key, _value in obj_attr_list.items() :
                self.update_object_attribute(cloud_name, obj_type, obj_uuid, \
                                             False, _key, _value, False)

            if expiration :
                self.redis_conn.expire(_obj_inst_fn + ':' + obj_uuid, int(expiration))

            if obj_type != "GLOBAL" and obj_type != "COLLECTOR" and \
                not obj_type.count("TRACKING") and \
                not obj_type.count("PENDING") :

                _query_object = self.get_object(cloud_name, "GLOBAL", False, "query", False)

                if "submitter" in obj_attr_list :
                    _mandatory_tags = [ "name" ]
                else :
                    _mandatory_tags = _query_object["mandatory_tags"].split(',')

                for _tag in _mandatory_tags :
                    if _tag in obj_attr_list :
                        self.tag_object(cloud_name, _tag.upper(), obj_attr_list[_tag], \
                                        obj_type, obj_uuid)

                _mandatory_views = _query_object[obj_type.lower()].split(',')

                for _criterion in _mandatory_views :
                    if "departure" in obj_attr_list :
                        self.add_to_view(cloud_name, obj_type, obj_attr_list, _criterion, "departure")
                    if "arrival" in obj_attr_list :
                        self.add_to_view(cloud_name, obj_type, obj_attr_list, _criterion, "arrival")

#                if obj_type == "VM" :
#                    self.add_to_view(cloud_name, "VM", obj_attr_list, "BYVMC", )

                # Now that we know the expiration command can be applied to whole
                # hash sets, this section of code will probably be removed in the
                # future.
                if "lifetime" in obj_attr_list and not "submitter" in obj_attr_list :
                    if obj_attr_list["lifetime"] != "none" :
                        _obj_life_fn = _obj_id_fn + ":SHOULDBEALIVE"
                        self.redis_conn.set(_obj_life_fn, \
                                            int(obj_attr_list["lifetime"]))
                        self.redis_conn.expire(_obj_life_fn, \
                                               int(obj_attr_list["lifetime"]))

                if obj_type == "VMC" :
                    _obj_count_fn = _obj_inst_fn + ':' + obj_uuid + ":RESERVATIONS"
                    self.redis_conn.set(_obj_count_fn, 0)
                    self.add_to_list(cloud_name, "GLOBAL", "vmc_pools", obj_attr_list["pool"].upper())

                if obj_type == "HOST" :
                    _obj_count_fn = _obj_inst_fn + ':' + obj_uuid + ":RESERVATIONS"
                    self.redis_conn.set(_obj_count_fn, 0)
                    self.add_to_list(cloud_name, "GLOBAL", "host_names", obj_attr_list["name"][5:].upper())

                if "initial_state" in obj_attr_list :
                    _initial_state = obj_attr_list["initial_state"]
                else :
                    _initial_state = "attached"
                    
                _obj_state_fn = _obj_inst_fn + ':' + obj_uuid + ":STATE"
                self.redis_conn.set(_obj_state_fn, _initial_state)

                if str(obj_attr_list["notification"]).lower() != "false" :
                    if obj_attr_list["notification_channel"].lower() == "auto" :
                        _channel = "ARRIVAL"
                    else :
                        _channel = obj_attr_list["notification_channel"]

                    _message = obj_type + " object " + obj_uuid + " (" + \
                    obj_attr_list["name"] + ") arrived"
                    self.publish_message(cloud_name, obj_type, _channel, _message, \
                                         1, \
                                         float(obj_attr_list["timeout"]))

            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _create_lock)
            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _create_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 14)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_uuid + " could not be created: " 
            _msg += str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _create_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 15)

    @trace
    def get_object_list(self, cloud_name, obj_type, auto_cleanup = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        if obj_type == "CLOUD" :
            _obj_inst_fn = self.experiment_inst + ':' + obj_type
        else :
            _obj_inst_fn = obj_inst + ':' + obj_type


        try :    
            _members = self.redis_conn.smembers(_obj_inst_fn)
            if  len(_members) :
                _msg = obj_type + " object list retrieved (FQIN: "
                _msg += _obj_inst_fn + ")."        
                cbdebug(_msg)
                
                if auto_cleanup :
                    _new_members = []
                    for _member in _members :
                        if not self.redis_conn.exists(_obj_inst_fn + ':' + _member) :
                            self.redis_conn.srem(_obj_inst_fn, _member)                            
                        else :
                            _new_members.append(_member)
                    _members = _new_members
            else :
                _msg = obj_type + " object list retrieved, but is empty "
                _msg += "(FQIN: " + _obj_inst_fn + ")."
                cbdebug(_msg)
                _members = False
      
            return _members

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 16)

        except ResponseError as msg :
            _msg = obj_type + " object list could not be retrieved:"
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 17)

    @trace
    def count_object(self, cloud_name, obj_type, counter_name = "none") :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        if counter_name != "none" :
            _obj_inst_fn = obj_inst + ':' + obj_type + ':' + counter_name
            if self.redis_conn.type(_obj_inst_fn) == "set" :
                _nr_objects = self.redis_conn.scard(_obj_inst_fn)
            else :
                _nr_objects = self.redis_conn.get(_obj_inst_fn)
        else :
            _obj_inst_fn = obj_inst + ':' + obj_type
            _nr_objects = self.redis_conn.scard(_obj_inst_fn)

        try :
            _msg = obj_type + " object number counted (FQIN: "
            _msg += _obj_inst_fn + ")."        
            cbdebug(_msg)
            return _nr_objects

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 18)

        except ResponseError as msg :
            _msg = obj_type + " object list could not be retrieved:"
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 19)

    @trace
    def get_object_state(self, cloud_name, obj_type, obj_uuid) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ':' + obj_uuid

        try :
            _state = self.redis_conn.get(_obj_inst_fn + ":STATE")

            _msg = obj_type + " object state retrieved (FQIN: "
            _msg += _obj_inst_fn + ")."
            cbdebug(_msg)
            return _state

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 20)

        except ResponseError as msg :
            _msg = obj_type + " object state could not be retrieved:"
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 21)

    @trace
    def set_object_state(self, cloud_name, obj_type, obj_uuid, value) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ':' + obj_uuid

        try :
            _state = self.redis_conn.set(_obj_inst_fn + ":STATE", value)

            _msg = obj_type + " object state updated to " + value + " (FQIN: "
            _msg += _obj_inst_fn + ")."
            cbdebug(_msg)
            return _state

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 21)

        except ResponseError as msg :
            _msg = obj_type + " object state could not be updated:"
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 22)

    @trace
    def get_object(self, cloud_name, obj_type, can_be_tag, obj_id, lock) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        if obj_type == "CLOUD" :
            _obj_inst_fn = self.experiment_inst + ':' + obj_type
        else :
            _obj_inst_fn = obj_inst + ':' + obj_type

        try :
            if lock :
                _get_lock = self.acquire_lock(cloud_name, obj_type, obj_id, "get_object", 1)

            _obj_uuid = self.object_exists(cloud_name, obj_type, obj_id, can_be_tag)

            if not _obj_uuid :
                _msg = obj_type + " object " + str(obj_id) + " could not be "
                _msg += "retrieved from object list (FQIN: " + _obj_inst_fn
                _msg += ")."
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 23)

            _obj_id_fn = _obj_inst_fn + ':' + _obj_uuid    
            _obj_id_dict = self.redis_conn.hgetall(_obj_id_fn)
            if len(_obj_id_dict) :
                _msg = obj_type + " object " + str(_obj_uuid) + " attribute " 
                _msg += "list retrieved (FQON: " + _obj_id_fn + ")."
                cbdebug(_msg)
                return _obj_id_dict
            else :
                _msg = obj_type + " object " + str(_obj_uuid) + " attribute " 
                _msg += "list could not be retrieved (FQON: " + _obj_id_fn
                _msg += ")."
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 80)

            if lock :
                self.release_lock(cloud_name, obj_type, obj_id, _get_lock)
            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_id, _get_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 91)

        except ResponseError as msg :
            _msg = obj_type + " object " + str(_obj_uuid) + " could not be " 
            _msg += "retrieved (FQON: " + _obj_id_fn + ") : " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_id, _get_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 92)

################################################################################
    @trace
    def pending_object_fn(self, cloud_name, obj_type, obj_uuid):
        return self.experiment_inst + ":" + cloud_name + ':' + obj_type + ":PENDING:" + obj_uuid
    
    @trace        
    def pending_object_set(self, cloud_name, obj_type, obj_uuid, obj_key, obj_value, \
                           notify_client_refresh = True, parent = None, parent_type = None, lock = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
        
        if notify_client_refresh :
            self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type + ":PENDING"

        try :
            _obj_id_fn = _obj_inst_fn + ':' + obj_uuid    

            if isinstance(obj_value, bool) or obj_value == None :
                obj_value = str(obj_value)
            _val = self.redis_conn.hset(_obj_id_fn, obj_key, obj_value)
            
            if parent and parent_type :
                self.pending_object_get(cloud_name, parent_type, parent, obj_key, failcheck = False)

            _msg =  obj_type + " object " + obj_uuid + " pending " + obj_key
            _msg += " was updated with the value \""
            _msg += str(obj_value) + "\" (FQON: " + _obj_id_fn + ")."
            cbdebug(_msg)

            return _val

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 24)

        except ResponseError as msg :
            _msg =  obj_type + " FAILED object " + obj_uuid + " pending " + obj_key
            _msg += " was updated with the value \""
            _msg += str(obj_value) + "\" (FQON: " + _obj_id_fn + "): "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 25)
        
    @trace        
    def pending_object_remove(self, cloud_name, obj_type, obj_uuid, obj_key, lock = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ":PENDING"
        
        try :

            _obj_id_fn = _obj_inst_fn + ':' + obj_uuid    

            _val = self.redis_conn.hdel(_obj_id_fn, obj_key)

            _msg =  obj_type + " object " + obj_uuid + " pending " + obj_key 
            _msg += " was deleted."
            _msg += " (FQON: " + _obj_id_fn + ")."
            cbdebug(_msg)

            return _val

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 26)

        except ResponseError as msg :
            _msg =  obj_type + " FAILED object " + obj_uuid + " pending " + obj_key
            _msg += " delete  \""
            _msg += " (FQON: " + _obj_id_fn + "): "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 27)
        
    @trace        
    def pending_object_exists(self, cloud_name, obj_type, obj_uuid, obj_key, lock = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ":PENDING"

        try :
            _obj_id_fn = _obj_inst_fn + ':' + obj_uuid    
            
            if obj_key :    
                return self.redis_conn.hexists(_obj_id_fn, obj_key)
            else :
                return self.redis_conn.exists(_obj_id_fn)

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 28)

        except ResponseError as msg :
            _msg =  obj_type + " FAILED object " + obj_uuid + " pending status " 
            _msg += " retrieved \""
            _msg += " (FQON: " + _obj_id_fn + "): "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 29)
    @trace        
    def pending_object_get(self, cloud_name, obj_type, obj_uuid, obj_key = "all", failcheck = True, lock = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ":PENDING"

        if obj_key == "all" :
            _check_key = None
        else :
            _check_key = obj_key
            
        try :
            _obj_id_fn = _obj_inst_fn + ':' + obj_uuid    

            if not self.pending_object_exists(cloud_name, obj_type, obj_uuid, _check_key) :
                _msg = "Pending " + obj_type + " object key " + str(obj_key) + " could not be "
                _msg += "found in hash set (FQIN: " + _obj_inst_fn
                _msg += ")."
                cberr(_msg)
                if failcheck :
                    raise self.ObjectStoreMgdConnException(str(_msg), 30)
                return False

            if obj_key == "all" :
                _val = self.redis_conn.hgetall(_obj_id_fn)
            else :
                _val = self.redis_conn.hget(_obj_id_fn, obj_key)

            _msg =  obj_type + " object " + obj_uuid + " pending " + obj_key
            _msg += " was retrieved."
            _msg += " (FQON: " + _obj_id_fn + ")."
            cbdebug(_msg)

            return _val

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 31)

        except ResponseError as msg :
            _msg =  obj_type + " FAILED object " + obj_uuid + " pending status " 
            _msg += " retrieved \""
            _msg += " (FQON: " + _obj_id_fn + "): "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 32)
################################################################################

    @trace        
    def update_object_attribute(self, cloud_name, obj_type, obj_id, can_be_tag, obj_key, \
                                obj_value, counter = False, lock = False) :
        '''
        TBD
        '''
        self.conn_check()

        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type

        try :
            if lock :
                _update_lock = self.acquire_lock(cloud_name, obj_type, obj_id, \
                                                 "update_object", 1)

            _obj_uuid = self.object_exists(cloud_name, obj_type, obj_id, can_be_tag)

            if not _obj_uuid :
                _msg = obj_type + " object " + str(obj_id) + " could not be "
                _msg += "retrieved from object list (FQIN: " + _obj_inst_fn
                _msg += ")."
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 33)

            _obj_id_fn = _obj_inst_fn + ':' + _obj_uuid    

            #cbdebug("Trying to store: " + str(_obj_id_fn) + ": " + str(obj_key) + " = " + str(obj_value), True)

            if counter :
                _val = self.redis_conn.hincrby(_obj_id_fn, obj_key, obj_value)
            else :
                if isinstance(obj_value,  bool) or obj_value == None : 
                    _val = self.redis_conn.hset(_obj_id_fn, obj_key, str(obj_value))
                else :
                    _val = self.redis_conn.hset(_obj_id_fn, obj_key, obj_value)

            _msg =  obj_type + " object " + _obj_uuid + " attribute \"" 
            _msg += str(obj_key) + "\" was updated with the value \""
            _msg += str(obj_value) + "\" (FQON: " + _obj_id_fn + ")."
            cbdebug(_msg)

            if lock :
                self.release_lock(cloud_name, obj_type, _obj_uuid, _update_lock)
            return _val

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, _obj_uuid, _update_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 34)

        except ResponseError as msg :
            _msg =  obj_type + " object " + _obj_uuid + " attribute \"" 
            _msg += str(obj_key) + "\" was updated with the value \""
            _msg += str(obj_value) + "\" (FQON: " + _obj_id_fn + "): "
            _msg += str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, _obj_uuid, _update_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 35)

    @trace
    def remove_object_attribute(self, cloud_name, obj_type, obj_id, can_be_tag, obj_key) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type

        try :
            _obj_uuid = self.object_exists(cloud_name, obj_type, obj_id, can_be_tag)
            
            if not _obj_uuid :
                _msg = obj_type + " object " + str(obj_id) + " could not be "
                _msg += " retrieved from object list (FQIN: " + _obj_inst_fn
                _msg += ")."
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 36)
            
            _obj_id_fn = _obj_inst_fn + ':' + str(_obj_uuid)

            self.redis_conn.hdel(_obj_id_fn, obj_key)
            _msg = obj_type + " object " + obj_id + " had the attribute "
            _msg += "\"" + obj_key + "\" removed (FQON: " + _obj_id_fn
            _msg += ")."
            cbdebug(_msg)

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 37)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_id + " could not have the "
            _msg += "attribute \"" + obj_key + "\" removed (FQON: " + _obj_id_fn
            _msg += ")."
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 38)

    @trace
    def update_object_views(self, cloud_name, obj_type, obj_uuid, obj_attr_list, action, lock):
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
        self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + obj_uuid

        if lock :
            _destroy_lock = self.acquire_lock(cloud_name, obj_type, obj_uuid, \
                                            "remove_object_attribute", 1)

        try :    
            if not self.object_exists(cloud_name, obj_type, obj_uuid, False) :
                _msg = obj_type + " object " + str(obj_uuid) + " could not be "
                _msg += " retrieved from object list (FQIN: " + _obj_inst_fn
                _msg += ").There is no need to explicitly destroy it."     
                cbdebug(_msg)
                return True
            
            if obj_type != "GLOBAL" and obj_type != "COLLECTOR" and \
            not obj_type.count("TRACKING") and \
            not obj_type.count("PENDING") and obj_attr_list is not None :
            
                _query_object = self.get_object(cloud_name, "GLOBAL", False, "query", False)
                _mandatory_views = _query_object[obj_type.lower()].split(',')
                for _criterion in _mandatory_views :
                    if action == "remove" :
                        self.remove_from_view(cloud_name, obj_type, obj_attr_list, _criterion)
                    elif action == "add" :
                        if "departure" in obj_attr_list :
                            self.add_to_view(cloud_name, obj_type, obj_attr_list, _criterion, "departure")
                        if "arrival" in obj_attr_list :
                            self.add_to_view(cloud_name, obj_type, obj_attr_list, _criterion, "arrival")
                        
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            return True
                    
        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 39)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_uuid + " could not be destroyed:" 
            _msg += ' ' + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 40)
        
    @trace
    def destroy_object(self, cloud_name, obj_type, obj_uuid, obj_attr_list, lock) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
        self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + obj_uuid

        if lock :
            _destroy_lock = self.acquire_lock(cloud_name, obj_type, obj_uuid, \
                                            "remove_object_attribute", 1)

        try :    
            if not self.object_exists(cloud_name, obj_type, obj_uuid, False) :
                _msg = obj_type + " object " + str(obj_uuid) + " could not be "
                _msg += " retrieved from object list (FQIN: " + _obj_inst_fn
                _msg += ").There is no need to explicitly destroy it."     
                cbdebug(_msg)
                return True

            self.redis_conn.srem(_obj_inst_fn, obj_uuid)
            _msg = obj_type + " object " + obj_uuid + " removed from object "
            _msg += "list (FQIN" + _obj_inst_fn + ")."
            cbdebug(_msg)

            self.redis_conn.delete(_obj_id_fn) 
            _msg = obj_type + " object " + obj_uuid + " attribute list removed "
            _msg += "(FQON" + _obj_id_fn + ")."
            cbdebug(_msg)

            if obj_type != "GLOBAL" and obj_type != "COLLECTOR" and \
            not obj_type.count("TRACKING") and \
            not obj_type.count("PENDING") and obj_attr_list is not None :
                self.update_counter(cloud_name, "GLOBAL", "experiment_counter", "increment")

                _query_object = self.get_object(cloud_name, "GLOBAL", False, "query", False)

                if "submitter" in obj_attr_list :
                    _mandatory_tags = [ "name" ]
                else :
                    _mandatory_tags = _query_object["mandatory_tags"].split(',')

                for _tag in _mandatory_tags :
                    if _tag in obj_attr_list :
                        self.untag_object(cloud_name, _tag.upper(), obj_attr_list[_tag], \
                                          obj_type, obj_uuid)

                _query_object = self.get_object(cloud_name, "GLOBAL", False, "query", False)
                _mandatory_views = _query_object[obj_type.lower()].split(',')
                for _criterion in _mandatory_views :
                    self.remove_from_view(cloud_name, obj_type, obj_attr_list, _criterion)

                if "lifetime" in obj_attr_list and obj_type != "AS"  :
                    if obj_attr_list["lifetime"] != "none" :
                        _obj_life_fn = _obj_id_fn + ":SHOULDBEALIVE"
                        self.redis_conn.delete(_obj_life_fn)

                if obj_type == "VMC" or obj_type == "HOST" :
                    _obj_count_fn = _obj_inst_fn + ':' + obj_uuid + ":RESERVATIONS"
                    self.redis_conn.delete(_obj_count_fn)

                _obj_state_fn = _obj_inst_fn + ':' + obj_uuid + ":STATE"
                self.redis_conn.delete(_obj_state_fn)

                if str(obj_attr_list["notification"]).lower() != "false" :
                    if obj_attr_list["notification_channel"].lower() == "auto" :
                        _channel = "DEPARTURE"
                    else :
                        _channel = obj_attr_list["notification_channel"]
                    _message = obj_type + " object " + obj_uuid + " (" + \
                    obj_attr_list["name"] + ") departed"
                    self.publish_message(cloud_name, obj_type, _channel, _message, \
                                         1, \
                                         float(obj_attr_list["timeout"]))

            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 41)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_uuid + " could not be destroyed:" 
            _msg += ' ' + str(msg)
            cberr(_msg)
            if lock :
                self.release_lock(cloud_name, obj_type, obj_uuid, _destroy_lock)
            raise self.ObjectStoreMgdConnException(str(_msg), 42)

    @trace
    def tag_object(self, cloud_name, tag_type, tag_value, obj_type, obj_uuid) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
    
        _tag_inst_fn = obj_inst + ':' + obj_type + ":TAG"
        _tag_type_fn = _tag_inst_fn + ':' + tag_type
        _tag_name_fn = _tag_type_fn + ':' + tag_value
        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + obj_uuid

        try :    
            _obj_exists = self.redis_conn.sismember(_tag_type_fn, tag_value)

            if _obj_exists :
                _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
                _msg += "\" is already part of the tag list (i.e., it is applied"
                _msg += " to an object already)."
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), "2")

            self.redis_conn.sadd(_tag_inst_fn, tag_type)
            self.redis_conn.sadd(_tag_type_fn , tag_value)
            _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
            _msg += " was added to the tag list (FQTN: " + _tag_type_fn + ")."        
            cbdebug(_msg)

            self.redis_conn.set(_tag_name_fn, _obj_id_fn) 
            _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
            _msg += " was pointed to the " + obj_type + " object " 
            _msg += obj_uuid + " (FQON: " + _obj_id_fn + ")."
            cbdebug(_msg)

            _tag_type = tag_type.lower()

            self.update_object_attribute(cloud_name, obj_type, obj_uuid, False, _tag_type, \
                                         tag_value, False)
            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 43)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_uuid + " could not be tagged "
            _msg += " with \"" + tag_type + "\" = \"" + tag_value + " (FQTN: "
            _msg += _tag_inst_fn + "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 44)

    @trace
    def untag_object(self, cloud_name, tag_type, tag_value, obj_type, obj_uuid) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _tag_inst_fn = obj_inst + ':' + obj_type + ":TAG"
        _tag_type_fn = _tag_inst_fn + ':' + tag_type
        _tag_name_fn = _tag_type_fn + ':' + tag_value

        try :
            _obj_exists = self.redis_conn.sismember(_tag_type_fn, tag_value)

            if not _obj_exists :
                _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
                _msg += " is not part of the tag list. There is no need for " 
                _msg += "explicitly delete it"
                cbdebug(_msg)
                return True

            self.redis_conn.srem(_tag_type_fn , tag_value)
            _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
            _msg += " was removed from the tag list (FQTN: " + _tag_type_fn
            _msg += ")."    
            cbdebug(_msg)

            self.redis_conn.delete(_tag_name_fn)         
            _msg = "The tag \"" + tag_type + "\" with value \"" + tag_value
            _msg += " was removed (FQTN: " + _tag_type_fn + ")."
            cbdebug(_msg)
            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 45)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_uuid + " could not be untagged "
            _msg += "  (FQTN: " + _tag_type_fn + "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 46)

    @trace
    def add_to_list(self, cloud_name, obj_type, list_name, obj_identifier, score = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
        self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type + ':' + list_name

        try :
            if not score :
                self.redis_conn.sadd(_obj_inst_fn, obj_identifier)
            else :
                self.redis_conn.zadd(_obj_inst_fn, {obj_identifier: score}) 

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 47)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_identifier + " could not be added "
            _msg += " to the list " + list_name + " (FQLN: " + _obj_inst_fn
            _msg += "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 48)

    @trace
    def get_list(self, cloud_name, obj_type, list_name, score = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type + ':' + list_name

        try :

            if not score :
                _list = self.redis_conn.smembers(_obj_inst_fn)
            else :
                _list = self.redis_conn.zrangebyscore(_obj_inst_fn, "-inf", \
                                                      "+inf", None, None, True)
            return _list

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 49)

        except ResponseError as msg :
            _msg = obj_type + " object list " + list_name + " could not be "
            _msg += "retrieved (FQLN: " + _obj_inst_fn + "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 50)

    @trace
    def remove_from_list(self, cloud_name, obj_type, list_name, obj_identifier, score = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name
        self.signal_api_refresh(cloud_name)

        _obj_inst_fn = obj_inst + ':' + obj_type + ':' + list_name

        try :
            if not score :
                self.redis_conn.srem(_obj_inst_fn, obj_identifier)
            else :
                self.redis_conn.zrem(_obj_inst_fn, obj_identifier)

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 51)

        except ResponseError as msg :
            _msg = obj_type + " object " + obj_identifier + " could not be removed "
            _msg += "from the list " + list_name + " (FQLN: " + _obj_inst_fn
            _msg += "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 52)

    @trace
    def add_to_view(self, cloud_name, obj_type, obj_attr_list, criterion, ordering) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _view_inst_fn = obj_inst + ':' + obj_type + ':VIEW'
        _view_criterion_fn = _view_inst_fn + ':' + criterion

        try :
            _obj_attr = criterion[2:].lower()

            if _obj_attr in obj_attr_list :

                _view_expression_fn = _view_criterion_fn + ':' + str(obj_attr_list[_obj_attr]).upper()

                _object_identifier = obj_attr_list["uuid"] + '|' + obj_attr_list["name"]

                if ordering == "departure" and "departure" in obj_attr_list :
                    self.redis_conn.zadd(_view_expression_fn + "_D", {_object_identifier: obj_attr_list["departure"]})
                    _msg = obj_type + " object " + _object_identifier  + " was added to "
                    _msg += "the \"" + criterion + " view (FQVN: " + _view_expression_fn
                    _msg += "), sorted by \"departure\" time."
                    cbdebug(_msg)

                elif ordering == "arrival" and "arrival" in obj_attr_list :
                    if criterion == "BYUSERNAME" :
                        self.redis_conn.zadd(_view_expression_fn + "_N", {_object_identifier: obj_attr_list["counter"]})
                    self.redis_conn.zadd(_view_expression_fn + "_A", {_object_identifier: obj_attr_list["arrival"]})
                    _msg = obj_type + " object " + _object_identifier  + " was added to "
                    _msg += "the \"" + criterion + " view (FQVN: " + _view_expression_fn
                    _msg += "), sorted by \"arrival\" time."
                    cbdebug(_msg)

                else :          
                    _msg = obj_type + " object " + _object_identifier
                    _msg += " does not have the attribute \""
                    _msg += _obj_attr + "\". Therefore, it will "
                    _msg += "not be added to the view \"" + criterion + "\" "
                    _msg += "(FQVN: " + _view_inst_fn + "), sorted by \""
                    _msg += ordering + "\" time."
                    cbdebug(_msg)

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 53)

        except ResponseError as msg :
            _msg = obj_type + " object " + _object_identifier + " could not be "
            _msg = " added to the \"" + criterion + " view (FQVN: "
            _msg += _view_expression_fn + "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 54)

    @trace
    def query_by_view(self, cloud_name, obj_type, criterion, expression, \
                      ordering = "arrival", ordering_filter = "all", \
                      scores = False) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _view_inst_fn = obj_inst + ':' + obj_type + ':VIEW'
        _view_criterion_fn = _view_inst_fn + ':' + criterion
        
        _view_expression_fn = _view_criterion_fn + ':' + expression.upper() + '_' + ordering[0].upper()

        try :
            if ordering_filter == "all" :
                _list = self.redis_conn.zrangebyscore(_view_expression_fn, \
                                                      "-inf", "+inf", \
                                                      None, None, scores)

            elif ordering_filter == "overdue" :
                _now = int(time())
                _list = self.redis_conn.zrangebyscore(_view_expression_fn, \
                                                      "-inf", _now, None, \
                                                      None, scores)

            elif ordering_filter.count("minage") :
                _x,_minage = ordering_filter.split(':')
                _minage = int(time()) - int(_minage)
                _list = self.redis_conn.zrangebyscore(_view_expression_fn, \
                                                      "-inf", _minage, None, None, \
                                                      scores)

            else :
                if scores :
                    _list = [ "Empty", "Empty" ]     
                else :
                    _list = [ "Empty" ]

            return _list

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 55)

        except ResponseError as msg :
            _msg = obj_type + " object id(s) could not be retrieved from the \""
            _msg += criterion + "\" view (FQVN: " + _view_expression_fn + "), "
            _msg += "sorted by \"" + ordering + "\" time : "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 56)

    def get_remote_time(self):
        '''
        TBD
        '''
        self.conn_check()
        
        try :
            _result = self.redis_conn.time()
        except :
            _result = self.redis_conn.execute_command("time")

        return _result
    
    @trace
    def remove_from_view(self, cloud_name, obj_type, obj_attr_list, criterion) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _view_inst_fn = obj_inst + ':' + obj_type + ':VIEW'
        _view_criterion_fn = _view_inst_fn + ':' + criterion

        try :
            
            _obj_attr = criterion[2:].lower()

            _object_identifier = obj_attr_list["uuid"] + '|' + obj_attr_list["name"]

            if _obj_attr in obj_attr_list :

                _view_expression_fn = _view_criterion_fn + ':' + str(obj_attr_list[_obj_attr]).upper()

                if "departure" in obj_attr_list :
                    self.redis_conn.zrem(_view_expression_fn + "_D", _object_identifier)
                    _msg = obj_type + " object " + _object_identifier  + " was removed from "
                    _msg += "the \"" + criterion + " view (FQVN: " + _view_expression_fn
                    _msg += "), sorted by \"departure\" time."
                    cbdebug(_msg)
                    
                if "arrival" in obj_attr_list :
                    if criterion == "BYUSERNAME" :
                        self.redis_conn.zrem(_view_expression_fn + "_N", _object_identifier)

                    self.redis_conn.zrem(_view_expression_fn + "_A", _object_identifier)
                    if criterion == "BYUSERNAME":
                        self.redis_conn.zrem(_view_expression_fn + "_N", _object_identifier)
                    _msg = obj_type + " object " + _object_identifier  + " was removed from "
                    _msg += "the \"" + criterion + " view (FQVN: " + _view_expression_fn
                    _msg += "), sorted by \"arrival\" time."
                    cbdebug(_msg)

            else :
                _msg = obj_type + " object " + _object_identifier
                _msg += " does not have the attribute \""
                _msg += _obj_attr + "\". Therefore, it will "
                _msg += "not be added to the view \"" + criterion + "\" "
                _msg += "(FQVN: " + _view_inst_fn + "), sorted by \"arrival\""
                _msg += " OR \"departure\" time."
                cbdebug(_msg)

            return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 57)

        except ResponseError as msg :
            _msg = obj_type + " object " + _object_identifier + " could not be "
            _msg = " removed from the \"" + criterion + " view (FQVN: "
            _msg += _view_expression_fn + "): " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 58)

    @trace        
    def publish_message(self, cloud_name, obj_type, channel, message, tries, tout) :
        '''
        TBD
        '''
        obj_inst = self.experiment_inst + ":" + cloud_name
        _redis_conn = self.connect(tout)

        _comm_chn = obj_inst + ':' + obj_type + ':' + channel
        _msg = "Attempting the publish message \"" + message + "\""
        _msg += " on the command channel " + _comm_chn
        cbdebug(_msg)

        _max_tries = tries + 1

        while _max_tries + 1 :

            try :

                _nr_recv = _redis_conn.publish(_comm_chn, message)

                if _nr_recv :
                    _msg = "Message: " + message + " was successfully"
                    _msg += " published on the channel " + _comm_chn
                    _msg += ", and received by " + str(_nr_recv)
                    _msg += " clients."
                    cbdebug(_msg)
                    return True
                else :
                    _msg = "Message: " + message + " was successfully"
                    _msg += " published on the channel " + _comm_chn
                    _msg += ", but wasn't received by anyone. Will try "
                    _msg += str(_max_tries) + " more times."
                    cbdebug(_msg)
                    _max_tries = _max_tries - 1
                    sleep(5)
                return True

            except ConnectionError as msg :
                _msg = "The connection to the data store seems to be "
                _msg += "severed: " + str(msg)
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 59)

            except ResponseError as msg :
                _msg = "Message " + message + " could not be published on the "
                _msg += "channel " + _comm_chn + ": " + str(msg)
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 60)

    @trace    
    def subscribe(self, cloud_name, obj_type, channel, timeout = 86500) :
        '''
        TBD
        '''
        obj_inst = self.experiment_inst + ":" + cloud_name
        _unsubscribe = False

        while not _unsubscribe :

            _redis_conn = self.connect(timeout)
            _redis_conn_pubsub = _redis_conn.pubsub()

            _comm_chn = obj_inst + ':' + obj_type + ':' + channel
 
            _msg = "Attempting the subscribe to channel " + _comm_chn
            cbdebug(_msg)

            try :
                _redis_conn_pubsub.subscribe(_comm_chn)

                _msg = "Subscribed on channel " + channel + " successful."
                cbdebug(_msg)
                return _redis_conn_pubsub
                            
            except ConnectionError as msg :
                _msg = "The connection to the data store seems to be "
                _msg += "severed: " + str(msg)
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 61)
    
            except ResponseError as msg :
                _msg = "Channel " + channel + " could not be subscribed "
                _msg += ": " + str(msg)
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 62)

    @trace
    def update_counter(self, cloud_name, obj_type, obj_id, delta) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + str(obj_id)

        try :
            if delta.count("increment") :
                _new_value = self.redis_conn.incr(_obj_id_fn) 
            elif delta.count("decrement") :
                _new_value = self.redis_conn.decr(_obj_id_fn)
            else :
                _msg = "The \"update counter\" method accepts only \"increment"
                _msg += "\" or \"decrement\" as parameters"
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), "2")

            _msg = "Object " + _obj_id_fn + " was atomically " + delta
            _msg += "ed. The new value is: " + str(_new_value)
            cbdebug(_msg)
            return _new_value

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 63)

        except ResponseError as msg :
            _msg = "Object " + _obj_id_fn + " could not be atomically " + delta
            _msg += "ed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 64)

    @trace
    def get_counter(self, cloud_name, obj_type, obj_id) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_inst_fn = obj_inst + ':' + obj_type
        _obj_id_fn = _obj_inst_fn + ':' + str(obj_id)
        
        try :
            _curr_value = self.redis_conn.get(_obj_id_fn) 
            _msg = "Object " + _obj_id_fn + " current value is " + str(_curr_value)
            cbdebug(_msg)
            return _curr_value

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 65)

        except ResponseError as msg :
            _msg = "Object " + _obj_id_fn + " could not retrieved: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 66)

    @trace
    def acquire_lock(self, cloud_name, obj_type, obj_id, id_str, tout_fct) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_lock_inst_fn = obj_inst + ':LOCK:' + obj_type
        _obj_lock_id_fn = _obj_lock_inst_fn + ':' + str(obj_id)

        _start_execution = time()
        _lock_str = str(randint(0,100000000000000)) + '-' + id_str

        try :
            _obj_id_lock = self.redis_conn.setnx(_obj_lock_id_fn, _lock_str)

            _msg = "First attempt to get the lock on the key "
            _msg += _obj_lock_id_fn + " resulted in "
            _msg += str(_obj_id_lock)
            cbdebug(_msg)

            while not _obj_id_lock :    # return 0 if not set
                _msg = "Could not get a lock on the key "
                _msg += _obj_lock_id_fn + "(" + str(_obj_id_lock) + ")"
                _msg += ". Will try again in 2 seconds"
                cbdebug(_msg)

                sleep(2)

                _obj_id_lock = self.redis_conn.setnx(_obj_lock_id_fn, _lock_str)    
                _current_time = time() - _start_execution

                if _current_time > self.timout/tout_fct :
                    _msg = "Unable to get the lock on key " + _obj_lock_id_fn
                    _msg += ". After a tout of " + str(self.timout/tout_fct )
                    _msg += " seconds. "
                    cberr(_msg)
                    raise self.ObjectStoreMgdConnException(str(_msg), 67) 

            # retrieve the lock string again
            _lock = self.redis_conn.get(_obj_lock_id_fn)

            if _lock == _lock_str :
                _msg = "SETNX worked and subsequent GET worked too."
                _msg += "Seems to have a lock on the key."
                _msg += _obj_lock_id_fn
                cbdebug(_msg)
            else :
                _msg = "SETNX worked, but subsequent GET did not."
                _msg += "Do not have the lock on the key."
                _msg += _obj_lock_id_fn
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 68)

            _msg = "Will set an expiration time on the lock "
            _msg += "at the key " + _obj_lock_id_fn
            cbdebug(_msg)

            # set a tout on _obj_lock_id_fn. The KEY will be deleted
            # automatically after the tout has expired
            self.redis_conn.expire(_obj_lock_id_fn, int(self.timout/tout_fct))

            _msg = "Got a lock on the key " + _obj_lock_id_fn
            cbdebug(_msg)
            return _lock_str

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 69)

        except ResponseError as msg :
            _msg = "Unable to get the lock on key " + _obj_lock_id_fn + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 70)

    @trace
    def release_lock(self, cloud_name, obj_type, obj_id, lock_str) :
        '''
        TBD
        '''
        self.conn_check()
        obj_inst = self.experiment_inst + ":" + cloud_name

        _obj_lock_inst_fn = obj_inst + ':LOCK:' + obj_type
        _obj_lock_id_fn = _obj_lock_inst_fn + ':' + str(obj_id)

        try :
            _lock_str_got = self.redis_conn.get(_obj_lock_id_fn)

            if not _lock_str_got :
                _msg = "Released the lock on the key " + _obj_lock_id_fn
                _msg += ". There is no lock in effect there. "
                cbdebug(_msg)
                return True

            elif _lock_str_got != lock_str :
                _msg = "Unable to release the lock on the key " + _obj_lock_id_fn
                _msg += ". I am not the owner of the lock. "
                _msg += " The lock string is " + _lock_str_got
                cberr(_msg)
                raise self.ObjectStoreMgdConnException(str(_msg), 71)

            elif _lock_str_got == lock_str :
                _msg = "I am the process who has lock on the key " + _obj_lock_id_fn
                _msg += ". Proceeding to delete it. "
                _msg += " The lock string is " + _lock_str_got
                cbdebug(_msg)

            if self.redis_conn.delete(_obj_lock_id_fn) :
                if not self.redis_conn.get(_obj_lock_id_fn) :
                    _msg = " - Released the lock on the key "
                    _msg += _obj_lock_id_fn
                    cbdebug(_msg)
                    return True

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 72)

        except ResponseError as msg :
            _msg = "Unable to get the lock on key " + _obj_lock_id_fn + ": "
            _msg += str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 73)

    @trace
    def get_info(self) :
        '''
        TBD
        '''
        self.conn_check()

        try :
            _info = self.redis_conn.info()
            _dbsize = self.redis_conn.dbsize()
            
            _output = []
            _output.append(["Used Memory", _info["used_memory_human"]])            
            _output.append(["Redis Version", _info["redis_version"]])
            _output.append(["Uptime (in seconds)", str(_info["uptime_in_seconds"])])
            _output.append(["Total Connections Received", str(_info["total_connections_received"])])
            _output.append(["Total Commands Processed", str(_info["total_commands_processed"])])
            _output.append(["Number of Keys ", str(_dbsize)])
            return _output

        except ConnectionError as msg :
            _msg = "The connection to the data store seems to be "
            _msg += "severed: " + str(msg)
            cberr(_msg)
            raise self.ObjectStoreMgdConnException(str(_msg), 89)
