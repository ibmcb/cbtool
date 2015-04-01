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
    Created on Nov 27, 2011

    Base Object Operations Library
    
    @author: Marcio A. Silva, Michael R. Hines
'''
import socket
import re
import os 

from os import chmod, access, F_OK
from time import time, sleep
from random import randint, choice, uniform
from uuid import uuid5, NAMESPACE_DNS
from hashlib import sha1
from base64 import b64encode
from pwd import getpwuid
from subprocess import Popen, PIPE

from lib.auxiliary.code_instrumentation import trace, cblog, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.value_generation import ValueGeneration
from lib.auxiliary.data_ops import message_beautifier, dic2str, str2dic, is_valid_temp_attr_list, DataOpsException
from lib.auxiliary.data_ops import selective_dict_update
from lib.remote.network_functions import Nethashget 
from lib.remote.ssh_ops import repeated_ssh
from lib.remote.process_management import ProcessManagement

class BaseObjectOperations :
    '''
    TBD
    '''
    default_cloud = None
    proc_man_os_command = ProcessManagement()

    @trace
    def __init__ (self, osci, msci, attached_clouds = []) :
        '''
        TBD
        '''
        self.username = getpwuid(os.getuid())[0]
        self.pid = "TEST_" + self.username 
        self.osci = osci
        self.msci = msci 
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../.."
        self.attached_clouds = attached_clouds
        self.thread_pools = {}
        self.coi = {}
        self.expid = None

    class ObjectOperationException(Exception) :
        @trace
        def __init__(self, msg, status):
            Exception.__init__(self)
            self.msg = msg
            self.status = status
        @trace
        def __str__(self):
            return self.msg

    @trace
    def get_cloud_parameters(self, cloud_name) :
        '''
        TBD
        '''
        try :
            return self.osci.get_object(cloud_name, "CLOUD", False, cloud_name, False)

        except self.osci.ObjectStoreMgdConnException, obj :
            _msg = "Unable to get parameters for the cloud " + cloud_name
            _msg += ". Are you sure that this cloud is attached to this "
            _msg += "experiment? " + str(obj.msg) + ""
            cberr(_msg)
            raise self.ObjectOperationException(_msg, obj.status)

    @trace
    def set_cloud_operations_instance(self, cloud_model) :
        '''
        TBD
        '''
        try :
            
            if cloud_model not in self.coi :
                self.coi[cloud_model] = {}

            if "ops_module" not in self.coi[cloud_model] :
                self.coi[cloud_model]["ops_module"] = \
                __import__("lib.clouds." + cloud_model + "_cloud_ops", \
                           fromlist = [cloud_model.capitalize() + "Cmds"])
            
            if "ops_class" not in self.coi[cloud_model] :
                self.coi[cloud_model]["ops_class"] = \
                getattr(self.coi[cloud_model]["ops_module"], \
                        cloud_model.capitalize() + "Cmds")
            
            if self.pid + '-' + self.expid not in self.coi[cloud_model] :
                self.coi[cloud_model][self.pid + '-' + self.expid] = \
                self.coi[cloud_model]["ops_class"](self.pid, self.osci, self.expid) 

            return True

        except ImportError, msg :
            _msg = str(msg)
            cberr(_msg)
            raise self.ObjectOperationException(8, _msg)

        except AttributeError, msg :
            _msg = str(msg)
            cberr(_msg)
            raise self.ObjectOperationException(8, _msg)

    def cleanup_comments_command(self, parameters) :
        ''' 
        TBD
        '''
        if parameters.count('#') :
            _processed_parameters = ''
            _parameters = parameters.split()
            for _parameter in _parameters :
                if not _parameter.count('#') :
                    _processed_parameters += _parameter + ' '
                else :
                    break
            parameters = _processed_parameters

        return parameters
  
    @trace
    def parse_cli(self, object_attribute_list, parameters, command) :
        '''
        TBD
        '''
        _status = 0

        command = self.cleanup_comments_command(command)

        if BaseObjectOperations.default_cloud is None :
            if not command.count("cloud-attach") and len(parameters.split()) > 0:
                object_attribute_list["cloud_name"] = parameters.split()[0]
        else :
            if not command.count("cloud-attach") and not parameters.count(" async"):
                if len(parameters) > 0 :
                    _possible_cloud_name = parameters.split()[0]
                    if _possible_cloud_name == BaseObjectOperations.default_cloud :
                        True
                    elif _possible_cloud_name in self.attached_clouds :
                        True 
                    else :
                        parameters = BaseObjectOperations.default_cloud + ' ' + parameters
                else :
                    parameters = BaseObjectOperations.default_cloud + ' ' + parameters
                object_attribute_list["cloud_name"] = parameters.split()[0]

        object_attribute_list["command"] = command + ' ' + parameters

        '''
        The temporary attribute list, in the form attribute1=value1;...;attributeN=valueN
        has to be cleaned up from the command parameter list, for all "attach"
        commands.
        '''
        if command.count("attach") :
            _parameters = []
            _temp_parameters = parameters.split()
            for _temp_parameter in _temp_parameters :
                if is_valid_temp_attr_list(_temp_parameter) :
                    object_attribute_list["temp_attr_list"] = _temp_parameter
                else :
                    _parameters.append(_temp_parameter)
        else :            
            _parameters = parameters.split()

        _length = len(_parameters)

        ######### "ACTIVE" OPERATION PARAMETER PARSING - BEGIN #########
        if command == "cloud-attach" :
            object_attribute_list["cloud_filename"] = None 
            if len(_parameters) >= 1 :
                object_attribute_list["model"] = _parameters[0]
            if len(_parameters) >= 2 :
                object_attribute_list["cloud_name"] = _parameters[1]
            if len(_parameters) >= 3 :
                object_attribute_list["cloud_filename"]  = _parameters[1]
            if len(_parameters) < 2 :
                _status = 9
                _msg = "Usage: cldattach <cloud model> <cloud name> [definitions file] "
            else :
                object_attribute_list["name"] = object_attribute_list["cloud_name"]

        elif command == "cloud-detach" :
            if _length :
                object_attribute_list["name"] = _parameters[0]
            else :
                _status = 9
                _msg = "Usage: clddetach <cloud name>"

        elif command == "mon-extract" :
            if _length == 3 :
                object_attribute_list["type"] = _parameters[1]
                object_attribute_list["metric_type"] = _parameters[2]
                object_attribute_list["expid"] = "current"
            elif _length == 4 :
                object_attribute_list["type"] = _parameters[1]
                object_attribute_list["metric_type"] = _parameters[2]
                object_attribute_list["expid"] = _parameters[3]
            else :
                _status = 9
                _msg = "Usage: monextract <cloud name> <object type> <metric type> [experiment id]"
                
        elif command == "host-fail" :
            if _length >= 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["situation"] = _parameters[2]                
                object_attribute_list["firs"] = "none"
            if _length >= 4 :
                object_attribute_list["firs"] = _parameters[3]
            if _length < 2:
                _status = 9
                _msg = "Usage: hostfail <cloud name> <host name> <situation> [parent] [mode]"
                
        elif command == "host-repair" :
            if _length >= 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["situation"] = _parameters[2]                
                object_attribute_list["firs"] = "none"
            if _length >= 4 :
                object_attribute_list["firs"] = _parameters[3]
            if _length < 2:
                _status = 9
                _msg = "Usage: hostfail <cloud name> <host name> <situation> [parent] [mode]"

        elif command == "vmc-cleanup" :
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length < 2 :
                _status = 9
                _msg = "Usage: vmccleanup <cloud name> <vmc name>"

        elif command == "vmc-attach" :
            if _length == 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["pool"] = "auto"
            elif _length == 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["pool"] = _parameters[2]
            else :
                _status = 9
                _msg = "Usage: vmcattach <cloud name> <vmc name> [pool] [mode]"

        elif command == "vmc-attachall" :
            if _length > 1 :
                True
            else :
                _status = 9
                _msg = "Usage: vmcattach <cloud name> <vmc name> [pool] [mode]"

        elif command == "vmc-detach" :
            object_attribute_list["force_detach"] = "false"
            
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[2]
            if _length < 2 :
                _status = 9
                _msg = "Usage: vmcdetach <cloud name> <vmc name> [force] [mode]"
    
        elif command == "vm-attach" :
            object_attribute_list["pool"] = "auto"
            object_attribute_list["meta_tags"] = "empty"
            object_attribute_list["size"] = "default"
            object_attribute_list["staging"] = "none"

            if _length >= 2 :
                object_attribute_list["role"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["pool"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["meta_tags"] = _parameters[3]
            if _length >= 5:
                object_attribute_list["size"] = _parameters[4]
            if _length >= 6 :
                object_attribute_list["staging"] = _parameters[5]
            if _length < 2 :
                _status = 9
                _msg = "Usage: vmattach <cloud name> <role> [vmc pool/host name] [meta_tags] [size] [action after attach] [mode]"

            object_attribute_list["name"] = "to generate"
            
        elif command == "vm-detach" :
            object_attribute_list["force_detach"] = "false"
            
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[2]
            if _length < 2:
                _status = 9
                _msg = "Usage: vmdetach <cloud name> <vm name> [force] [mode]"
                
        elif command == "vm-debug" :
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length < 2:
                _status = 9
                _msg = "Usage: vmdebug <cloud name> <vm name>"
                
        elif command == "vm-runstate" :
            object_attribute_list["suspected_command"] = "unknown" 
            object_attribute_list["firs"] = "none"
            if _length >= 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["target_state"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["suspected_command"] = _parameters[3] 
            if _length >= 5 :
                object_attribute_list["firs"] = _parameters[4]
            if _length < 3:
                _status = 9
                _msg = "Usage: vmrunstate <cloud name> <vm name> <runstate> [parent] [mode]"

        elif command == "vm-capture" :
            if _length == 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["vmcrs"] = "none"
            
            if _length > 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["vmcrs"] = _parameters[2]

            if _length < 2:
                _status = 9
                _msg = "Usage: vmcapture <cloud name> <vm name> [parent] [mode]"
                
        elif command == "api-check":
            
            if _length >= 1 :
                object_attribute_list["time"] = _parameters[1]
                
        elif command == "vm-migrate" or command == "vm-protect":
            object_attribute_list["interface"] = "default" 
            object_attribute_list["mtype"] = command.split("-")[1]
            
            if _length >= 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["destination"] = _parameters[2] 
                object_attribute_list["protocol"] = "default"
                
                
            if _length >= 4 :
                object_attribute_list["protocol"] = _parameters[3]
                
            if _length >= 5 :
                object_attribute_list["interface"] = _parameters[4]

        elif command == "vm-login" or command == "vm-display":
            object_attribute_list["mtype"] = command.split("-")[1]
            
            if _length >= 1 :
                object_attribute_list["name"] = _parameters[1]

        elif command == "vm-resize" :
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["resource_description"] = ','.join(_parameters[2:])
                object_attribute_list["resource_description"] = object_attribute_list["resource_description"].replace('=',':')

            if _length < 2:
                _status = 9
                _msg = "Usage: vmresize <cloud name> <vm name> <resource specification>"

        elif command == "ai-attach" :
            object_attribute_list["load_level"] = "default"
            object_attribute_list["load_duration"] = "default"
            object_attribute_list["lifetime"] = "none"
            object_attribute_list["aidrs"] = "none"
            object_attribute_list["staging"] = "none"
            
            if _length >= 2 :
                object_attribute_list["type"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["load_level"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["load_duration"] = _parameters[3]
            if _length >= 5 :
                object_attribute_list["lifetime"] = _parameters[4]
            if _length >= 6 :
                object_attribute_list["aidrs"] = _parameters[5]
            if _length >= 7 :
                object_attribute_list["staging"] = _parameters[6]
            if _length < 2:
                _status = 9
                _msg = "Usage: aiattach <cloud name> <type> [load level] [load duration] [lifetime] [parent] [action after VM attach] [mode]"

            object_attribute_list["name"] = "to generate"    

        elif command == "ai-runstate" :
            object_attribute_list["suspected_command"] = "unknown"
            object_attribute_list["firs"] = "none"
            if _length >= 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["target_state"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["suspected_command"] = _parameters[3] 
            if _length >= 5 :
                object_attribute_list["firs"] = _parameters[4]
            if _length < 3:
                _status = 9
                _msg = "Usage: airestore|aisave|airun <cloud name> <ai name> [parent] [mode]"
                
        elif command == "ai-detach" :
            object_attribute_list["force_detach"] = "false"
            
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[2]
            if _length < 2:
                _status = 9
                _msg = "Usage: aidetach <cloud name> <ai name> [force] [mode]"

        elif command == "ai-capture" :
            if _length == 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["vmcrs"] = "none"
            
            if _length > 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["vmcrs"] = _parameters[2]

            if _length < 2:
                _status = 9
                _msg = "Usage: aicapture <cloud name> <ai identifier> [parent] [mode]"

        elif command == "ai-resize" :
            if _length >= 4 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["role"] = _parameters[2]
                object_attribute_list["quantity"] = _parameters[3]
                if _parameters[3][0] != "+" and _parameters[3][0] != "-" :
                    _length = -1
            if _length < 4 :
                _status = 9
                _msg = "Usage: airesize <cloud name> <ai name> <role> (+/-)<delta>"

        elif command == "aidrs-attach" :
            object_attribute_list["max_ais"] = "default"
            object_attribute_list["iait"] = "default"
            object_attribute_list["lifetime"] = "default"
            object_attribute_list["load_level"] = "default"
            object_attribute_list["load_duration"] = "default"
            
            if _length >= 2 :
                object_attribute_list["pattern"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["max_ais"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["iait"] = _parameters[3]
            if _length >= 5 :
                object_attribute_list["lifetime"] = _parameters[4]
            if _length >= 6 :
                object_attribute_list["load_level"] = _parameters[5]
            if _length >= 7 :
                object_attribute_list["load_duration"] = _parameters[6]
            if _length < 2:
                _status = 9
                _msg = "Usage: aidrsattach <cloud name> <pattern> [max AIs] [inter ai arrival time] [ai lifetime] [ai load level] [ai load duration] [mode]"

            object_attribute_list["name"] = "to generate"    

        elif command == "aidrs-detach" :
            object_attribute_list["force_detach"] = "false"
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[1]
            if _length < 2 :
                _status = 9
                _msg = "Usage: aidrsdetach <cloud name> <aidrs name> [force] [mode]"
                
        elif command == "vmcrs-attach" :
            object_attribute_list["max_simultaneous_cap_reqs"] = "default"
            object_attribute_list["max_total_cap_reqs"] = "default"            
            object_attribute_list["min_cap_age"] = "default"
            object_attribute_list["ivmcat"] = "default"
            
            if _length >= 2 :
                object_attribute_list["pattern"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["scope"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["max_simultaneous_cap_reqs"] = _parameters[3]
            if _length >= 5 :
                object_attribute_list["max_total_cap_reqs"] = _parameters[4]
            if _length >= 6 :
                object_attribute_list["ivmcat"] = _parameters[5]
            if _length >= 7 :
                object_attribute_list["min_cap_age"] = _parameters[6]
            if _length < 2:
                _status = 9
                _msg = "Usage: vmcrsattach <cloud name> <pattern> [scope] [max simultaneous capreqs] [max total capreqs] [inter vm cap req arrival time] [min capture age] [mode]"

            object_attribute_list["name"] = "to generate"  

        elif command == "vmcrs-detach" :
            object_attribute_list["force_detach"] = "false"
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[1]
            if _length < 2 :
                _status = 9
                _msg = "Usage: vmcrsdetach <cloud name> <vmcrs name> [force] [mode]"

        elif command == "firs-attach" :
            object_attribute_list["max_simultaneous_faults"] = "default"
            object_attribute_list["max_total_faults"] = "default"            
            object_attribute_list["min_fault_age"] = "default"
            object_attribute_list["ifat"] = "default"
            object_attribute_list["ftl"] = "default"
            
            if _length >= 2 :
                object_attribute_list["pattern"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["scope"] = _parameters[2]
            if _length >= 4 :
                object_attribute_list["max_simultaneous_faults"] = _parameters[3]
            if _length >= 5 :
                object_attribute_list["max_total_faults"] = _parameters[4]
            if _length >= 6 :
                object_attribute_list["ifat"] = _parameters[5]
            if _length >= 7 :
                object_attribute_list["min_fault_age"] = _parameters[6]
            if _length >= 8 :
                object_attribute_list["ftl"] = _parameters[7]
            if _length < 2:
                _status = 9
                _msg = "Usage: firsattach <cloud name> <pattern> [scope] [max simultaneous faults] [max total faults] [inter fault arrival time] [min fault age] [fault time length] [mode]"

            object_attribute_list["name"] = "to generate"  

        elif command == "firs-detach" :
            object_attribute_list["force_detach"] = "false"
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["force_detach"] = _parameters[1]
            if _length < 2 :
                _status = 9
                _msg = "Usage: firsdetach <cloud name> <vmcrs name> [force] [mode]"

        ######### "ACTIVE" OPERATION PARAMETER PARSING - END #########

        ######### "PASSIVE" OPERATION PARAMETER PARSING - BEGIN ######### 
        elif command == "cloud-list" :
            object_attribute_list["state"] = "all"
            object_attribute_list["set_default_cloud"] = "true" 
            object_attribute_list["name"] = ''
            object_attribute_list["cloud_name"] = ''
            
            if len(_parameters) >= 1 :
                object_attribute_list["set_default_cloud"] = _parameters[0]
                
            if len(_parameters) < 0 :
                _status = 9
                _msg = "Usage: cldlist"

        elif command == "global-list" :
            if _length > 1 :
                if _parameters[1].count('+') > 1 :
                    object_attribute_list["global_object"] = _parameters[1].split('+')[0]
                    object_attribute_list["object_attribute"] =  _parameters[1].split('+')[1]
                    object_attribute_list["object_type"] =  _parameters[1].split('+')[2]
                    object_attribute_list["command"] = object_attribute_list["object_attribute"][:-1] + "list " + _parameters[0]
                else :
                    _status = 9
                    _msg = "Usage: " + _parameters[0].split('+')[1][:-1] + "list <cloud name>"
            else :
                _status = 9
                _msg = "Usage: " + _parameters[0].split('+')[1][:-1] + "list <cloud name>"

        elif command == "mon-list" :
            if _length > 1 :
                object_attribute_list["type"] = _parameters[1]
            else :
                _status = 9
                _msg = "Usage: monlist <cloud name> <object type>"

        # "cloud-list", "global_list", and "mon-list" are special cases. All 
        # others are handled here        
        elif command.count("list") and not command.count("view") :
            object_attribute_list["state"] = "attached"
            object_attribute_list["limit"] = "none"
            if _length >= 2 :
                # 'default' means 'attached', but that need not necessarily
                # be true in the future.
                if _parameters[1] != "default" :
                    object_attribute_list["state"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["limit"] = _parameters[2]
            if _length < 1 :
                _status = 9
                _msg = "Usage: " + command.split('-')[0] + "list <cloud name>" 
                
        elif command == "cloud-show" :
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[0]
                object_attribute_list["specified_attributes"] = ''
                for _attribute in _parameters[1:] :
                    object_attribute_list["specified_attributes"] += _attribute + '-'
                object_attribute_list["specified_attributes"] = object_attribute_list["specified_attributes"][:-1]
                
            if _length < 2 :
                _status = 9
                _msg = "Usage: cldshow <cloud name> <attribute>"

        elif command == "view-show" :

            object_attribute_list["sorting"] = "arrival"
            object_attribute_list["filter"] = "all"   

            if _length >= 4 :
                object_attribute_list["object_type"] = _parameters[1].upper()
                object_attribute_list["criterion"] = _parameters[2].upper()
                object_attribute_list["expression"] = _parameters[3].upper()             
            
            if _length >= 5 :
                if _parameters[4].lower() != "default" :
                    object_attribute_list["sorting"] = _parameters[4].upper()
                
            if _length >= 6 :
                if _parameters[5].lower() != "default" :
                    object_attribute_list["filter"] = _parameters[5].upper()
            
            if _length < 4 :
                _status = 9
                _msg = "Usage: viewshow <cloud name> <object type> <criterion> <expression> [sorting] [filter]"

        elif command == "state-show" :
            if _length == 2 :
                object_attribute_list["filter"] = _parameters[1]
            elif _length < 1 :
                _status =  9
                _msg = "Usage: stateshow <cloud name> [state filter]"

        elif command == "global-show" :
            if _length > 3 :
                object_attribute_list["global_object"] = _parameters[2]
                object_attribute_list["object_attribute"] =  _parameters[3]
                object_attribute_list["object_type"] =  _parameters[2].split('_')[0].upper()
                object_attribute_list["command"] = _parameters[3] + "show " + _parameters[0] + ' ' + _parameters[1] 
                object_attribute_list["attribute_name"] = _parameters[1]
            else :
                _status = 9
                for _parameter in _parameters :
                    if _parameter == "role" or _parameter == "type" or _parameter == "pattern" :
                        _msg = "Usage: " + _parameter + "show <cloud name> <" + _parameter + ">"

        # "cloud-show", "view-show", "state-show" and "global-show" are
        # special cases. All others are handled here.
        elif command.count("show") and not command.count("view") :
            if _length >= 2 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["specified_attributes"] = 'all'
                
            if _length == 3 :
                object_attribute_list["specified_attributes"] = _parameters[2]
                
            if _length < 2 :
                _status = 9
                _msg = "Usage: " + command.split('-')[0]
                _msg += "show <cloud name> <"
                _msg += command.split('-')[0] + " identifier>" 
                _msg += " <attribute1>,<attribute2>,...,<attributeN>"

        elif command == "cloud-alter" :
            if _length >= 3:
                object_attribute_list["specified_attributes"] = _parameters[1]
                object_attribute_list["specified_kv_pairs"] = ''
                for _kv in _parameters[2:] :
                    object_attribute_list["specified_kv_pairs"] += _kv + ','
                object_attribute_list["specified_kv_pairs"] = object_attribute_list["specified_kv_pairs"][:-1]
            else :
                _status = 9
                _msg = "Usage: cldalter <cloud name> <attribute> <key>=<value>"

        elif command == "global-alter" :
            if _length == 5 :
                object_attribute_list["global_object"] = _parameters[3]
                object_attribute_list["specified_attribute"] = _parameters[1]
                object_attribute_list["specified_kv_pair"] = _parameters[1] + '_' + _parameters[2]
                object_attribute_list["attribute_name"] = _parameters[4]
                object_attribute_list["object_type"] =  _parameters[3].split('_')[0].upper()
            else :
                _status = 9
                for _parameter in _parameters :
                    if _parameter == "role" or _parameter == "type" or _parameter == "pattern" :
                        _msg = "Usage: " + _parameter + "alter <cloud name> <" 
                        _msg += _parameter + "name> " + "<attribute>=<value>"
            
        elif command == "state-alter" :
            if _length == 3 :
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["specified_state"] = _parameters[2]
            else :
                _status =  9
                _msg = "Usage: statealter <cloud name> <object identifier> <new state>"

        # "cloud-alter" and "state-alter" are the special cases. All others
        # are handled here.                
        elif command.count("alter") :
            if _length == 3:
                object_attribute_list["name"] = _parameters[1]
                object_attribute_list["specified_kv_pairs"] = _parameters[-1]
 
            if _length < 3 :
                _status = 9
                _msg = "Usage: " + command.split('-')[0] + "alter <"
                _msg += command.split('-')[0] + " identifier>" 
                _msg += " <cloud name> <attribute1>=<value1>,<attribute2>=<value2>,...,<attributeN>=<valueN>"

        elif command == "wait-for" :
            if len(_parameters) == 2 :
                object_attribute_list["specified_time"] = _parameters[1]
                object_attribute_list["interval"] = "default"
            elif len(_parameters) == 3 :
                object_attribute_list["specified_time"] = _parameters[1]
                object_attribute_list["interval"] = _parameters[2]
            else :
                _status =  9
                _msg = "Usage: waitfor <cloud_name> <time> [update interval]"

        elif command == "wait-until" :
            if parameters.count('=') :
                if _length == 3 :
                    object_attribute_list["type"] = _parameters[1]
                    object_attribute_list["counter"] = _parameters[2].split('=')[0]
                    object_attribute_list["value"] = _parameters[2].split('=')[1]
                    object_attribute_list["interval"] = 20
                    if int(object_attribute_list["value"]) :
                        object_attribute_list["direction"] = "increasing"
                    else :
                        object_attribute_list["direction"] = "decreasing"
                elif _length == 4 :
                    object_attribute_list["type"] = _parameters[1]
                    object_attribute_list["counter"] = _parameters[2].split('=')[0]
                    object_attribute_list["value"] = _parameters[2].split('=')[1]
                    object_attribute_list["direction"] = _parameters[3] 
                    object_attribute_list["interval"] = 20
                elif _length == 5 :
                    object_attribute_list["type"] = _parameters[1]
                    object_attribute_list["counter"] = _parameters[2].split('=')[0]
                    object_attribute_list["value"] = _parameters[2].split('=')[1]
                    object_attribute_list["direction"] = _parameters[3]
                    object_attribute_list["interval"] = _parameters[4]
                else :
                    _status =  9
                    _msg = "Usage: waituntil <cloud name> <object type> <counter>=<value> [direction] [update interval]"
            else :
                _status =  9
                _msg = "Usage: waituntil <cloud name> <object type> <counter>=<value> [direction] [update interval]"

        elif command == "wait-on" :
            if _length >= 4 :
                object_attribute_list["type"] = _parameters[1]
                object_attribute_list["channel"] = _parameters[2]
                object_attribute_list["keyword"] = _parameters[3]
                object_attribute_list["timeout"] = 86400   
            else :
                _status =  9
                _msg = "Usage: waiton <cloud name> <object type> <channel> <keyword>"

            if _length == 5 :
                object_attribute_list["timeout"] = _parameters[4]

        elif command == "msg-pub" :
            if _length >= 4 :
                object_attribute_list["type"] = _parameters[1]
                object_attribute_list["channel"] = _parameters[2]
                object_attribute_list["message"] = ' '.join(_parameters[3:])
            else :
                _status =  9
                _msg = "Usage: msgpub <cloud name> <object type> <channel> <message>"

        elif command == "stats-get" :
            if _length >= 2 :
                object_attribute_list["type"] = _parameters[1]
            if _length >= 3 :
                object_attribute_list["output"] = _parameters[2]
                                
            if not _length :
                _status =  9
                _msg = "Usage: stats <cloud name> [object type] [output]"

        elif command == "shell-execute" :
            if _length >= 2 :
                object_attribute_list["cmdexec"] = ' '.join(_parameters[1:]) 
            else :
                _status =  9
                _msg = "Usage: Usage: shell <cloud name> <command name>"

        elif command == "expid-manage" :
            if _length >= 1 :
                object_attribute_list["cmdexec"] = ' '.join(_parameters[1:]) 
            else :
                _status =  9
                _msg = "Usage: expid <cloud name> <experiment id>"
        
        ######### "PASSIVE" OPERATION PARAMETER PARSING - END ######### 

        else :
            _status = 10
            _parameters = None
            _msg = "Unknown command: " + command
        
        if not _status :
            _msg = "Command \"" + command + "\", with parameters \""
            _msg += ','.join(_parameters) + "\" parsed successfully"
            cbdebug(_msg)
        else :
            cberr(_msg)

        return _status, _msg
                
    @trace
    def initialize_object(self, obj_attr_list, cmd) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _obj_type = "unknown"

            obj_attr_list["command_originated"] = int(time())
            obj_attr_list["tracking"] = "none"

            _cloud_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "CLOUD")
 
            if _cloud_list :
                _cloud_list = list(_cloud_list)
            else :
                _cloud_list = []

            if len(obj_attr_list["cloud_name"],) :
                _time_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "time", False)
                self.expid = _time_attr_list["experiment_id"]

            if not cmd.count("cloud-list") :
                if obj_attr_list["cloud_name"] in _cloud_list :
                    # Cloud is attached, we can proceed
                    True
                else :
                    _msg = "The cloud \"" + obj_attr_list["cloud_name"] + "\" is not yet attached "
                    _msg += "to this experiment. Please attach it first."
                    _status = 9876
                    raise self.ObjectOperationException(_msg, _status)
                
            _obj_type, _operation = cmd.split('-')
            _obj_type = _obj_type.upper()

            ######### "ACTIVE" OPERATION OBJECT INITIALIZATION - BEGIN #########
            if cmd.count("cleanup") :
                obj_attr_list["experiment_id"] = self.expid

                _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])
                
                _vmc_defaults = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                     "vmc_defaults", False)

                obj_attr_list["model"] = _cloud_parameters["model"]
                selective_dict_update(obj_attr_list, _vmc_defaults)

                _status = 0
                
            elif cmd == "mon-repair" :
                _status = 0

            elif cmd == "shell-execute" :
                _status = 0
                
            elif cmd == "mon-extract" :
                _mon_parameters = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "mon_defaults", False)
                obj_attr_list["current_experiment_id"] = self.expid
                
                selective_dict_update(obj_attr_list, _mon_parameters)

                _status = 0

            elif cmd == "mon-list" :
                _mon_parameters = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "mon_defaults", False)                
                selective_dict_update(obj_attr_list, _mon_parameters)

                _status = 0

            elif cmd == "vmc-attachall" :
                _status = 0

            elif cmd.count("attach") :

                _postpone_counter = False

                obj_attr_list["experiment_id"] = self.expid

                obj_attr_list["mgt_001_provisioning_request_originated"] = obj_attr_list["command_originated"]
                obj_attr_list["mgt_002_provisioning_request_sent"] = "0"
                obj_attr_list["mgt_003_provisioning_request_completed"] = "0"
                if _obj_type == "VM" :
                    obj_attr_list["mgt_005_file_transfer"] = "0"                                
                    obj_attr_list["mgt_006_application_start"] = "0"
                    
                _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])

                '''
                    Staging operations which contain the keyword 'prepare' indicate that this process
                    must fork a background process first to perform the actual object attachment.
                    In which case, we don't actually want to generate a name for this object - 
                    we want the child process to do it instead.
                '''
                if "staging" in obj_attr_list and obj_attr_list["staging"].count("prepare") :
                    _postpone_counter = True

                if not _postpone_counter :
                    _obj_counter = self.osci.update_counter(obj_attr_list["cloud_name"], _obj_type, \
                                                            "COUNTER", \
                                                            "increment")

                # VMCs have pre-defined names (usually by the cloud itself), 
                # all other object names are generated on the fly, so they never
                # "exist" before attachment (a new VM, AI or AIDRS will be created
                # every time an "attach" command is run).
                if _obj_type == "VMC" :
                    _object_exists = self.osci.object_exists(obj_attr_list["cloud_name"], _obj_type, \
                                                             obj_attr_list["name"], \
                                                             True)
                    _space_obj_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", \
                                                                False, \
                                                                "space", \
                                                                False)

                    obj_attr_list["base_dir"] = _space_obj_attr_list["base_dir"]
                else :
                    _object_exists = False

                if obj_attr_list["name"] == "to generate" :
                    if _postpone_counter :
                        obj_attr_list["name"] = "unused"
                    else :
                        obj_attr_list["name"] = _obj_type.lower() + '_' + str(_obj_counter)

                obj_attr_list["cloud_name"] = _cloud_parameters["name"]
                obj_attr_list["model"] = _cloud_parameters["model"]

                if _object_exists :
                    _fmsg = _obj_type + " object " + obj_attr_list["name"] + " already "
                    _fmsg += "instantiated on the object store. To change its "
                    _fmsg += "attributes/state, use the " + _obj_type.lower() 
                    _fmsg += "alter command or explicitly detach and attach this "
                    _fmsg += "object back to this experiment."
                    _status = 98
                    
                else :
                    _obj_defaults = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                         _obj_type.lower() + "_defaults", \
                                                         False)

                    '''
                    Unpack and update the obj_attr_list dictionary with the keys
                    from the "temporary" object attributes list before performing
                    the "selective dictionary update"
                    '''

                    if not "temp_attr_list" in obj_attr_list :
                        obj_attr_list["temp_attr_list"] = "empty=empty"

                    if obj_attr_list["temp_attr_list"] != "empty=empty" :
                        _temp_attr_list = obj_attr_list["temp_attr_list"].replace(';',',')
                        _temp_attr_list = _temp_attr_list.replace('=',':')
                        _temp_attr_list = str2dic(_temp_attr_list)
                        obj_attr_list.update(_temp_attr_list)

                    '''
                    Now we perform the "selective" dictionary update. It is
                    "selective" in the sense that any already set key will not
                    be overwritten by the keys in <OBJECT_TYPE>_DEFAULTS, as it
                    would normally occur with the "update" method from python
                    '''

                    selective_dict_update(obj_attr_list, _obj_defaults)

                    obj_attr_list["counter"] = self.osci.update_counter(obj_attr_list["cloud_name"], "GLOBAL", \
                                                                        "experiment_counter", \
                                                                        "increment")
                    obj_attr_list["comments"] = ''
                    _dir_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "space", \
                                                     False)
                        
                    obj_attr_list["base_dir"] = _dir_list["base_dir"]
                    obj_attr_list["identity"] = _dir_list["ssh_key_name"]

                    if _obj_type == "VM" :
                        obj_attr_list["jars_dir"] = _dir_list["jars_dir"]
                        obj_attr_list["exclude_list"] = _dir_list["base_dir"] + "/exclude_list.txt"
                        obj_attr_list["daemon_dir"] = _dir_list["vm_daemon_dir"]

                        if "openvpn_server_address" not in _dir_list or _dir_list["openvpn_server_address"].lower().strip() == "false" :
                            obj_attr_list["userdata"] = None
                        else :
                            _pending_fn = self.osci.pending_object_fn(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"])
                            openvpn_fh = open(_dir_list["openvpn_client_config_prefix"] + "-" + obj_attr_list["cloud_name"] + ".conf")
                            _openvpn_contents = openvpn_fh.read()
                            openvpn_fh.close()
                            _openvpn_contents = _openvpn_contents.replace("DESTINATION", _dir_list["openvpn_server_address"])
                            
                            openvpn_server_and_port = _dir_list["openvpn_bootstrap_address"] + " -p " + str(self.osci.port)
                            obj_attr_list["userdata"] = _pending_fn + "\n" + openvpn_server_and_port + "\n" + _openvpn_contents
                            obj_attr_list["openvpn_server_address"] = _dir_list["openvpn_server_address"]
                            obj_attr_list["openvpn_bootstrap_address"] = _dir_list["openvpn_bootstrap_address"]
            
                    self.get_counters(obj_attr_list["cloud_name"], obj_attr_list)
                       
                    _status = 0

            elif cmd.count("detach") or cmd.count("capture") or \
                cmd.count("runstate") or cmd.count("resize") or \
                cmd.count("restore") or cmd.count("console") or \
                cmd.count("migrate") or cmd.count("protect") or \
                cmd.count("login") or cmd.count("display") :
                
                if "target_state" in obj_attr_list and obj_attr_list["target_state"] == "attached" and obj_attr_list["suspected_command"] == "run" :
                    obj_attr_list["uuid"] = obj_attr_list["name"]
                    _status = 483920
                    _fmsg = "Going to resume AI from pending initialized state..."
                    return _status, _fmsg
                                        
                if obj_attr_list["name"] == "all" :
                    _status = 912543
                    _fmsg = "need to pass through the appropriate 'all' function"
                    return _status, _fmsg
                _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])

                self.pre_select_object(obj_attr_list, _obj_type, _cloud_parameters["username"])

                if '_' not in obj_attr_list["name"] and '-' not in obj_attr_list["name"] and _obj_type.upper() != "VMC" :
                        obj_attr_list["name"] = _obj_type.lower() + "_" + obj_attr_list["name"]
                    
                _object_exists = self.osci.object_exists(obj_attr_list["cloud_name"], _obj_type, \
                                                         obj_attr_list["name"], \
                                                         True)

                if not _object_exists :
                    _fmsg = "Object " + obj_attr_list["name"] + " is not instantiated on the object store."

                    if cmd.count("detach") :
                        _fmsg += "There is no need for explicitly detach it from "
                        _fmsg += "this experiment."
                        _status = 37
                    elif cmd.count("capture") :
                        _fmsg += "Cannot capture object."
                        _status = 38
                    elif cmd.count("runstate") :
                        _fmsg += "Cannot change object's run state."
                        _status = 39
                    elif cmd.count("resize") :
                        _fmsg += "Cannot resize object."
                        _status = 40
                    elif cmd.count("migrate") :
                        _fmsg += "Cannot migrate object."
                        _status = 41
                    elif cmd.count("protect") :
                        _fmsg += "Cannot protect object."
                        _status = 41
                    elif cmd.count("login") :
                        _fmsg += "Cannot login to object."
                        _status = 42
                    elif cmd.count("display") :
                        _fmsg += "Cannot display object."
                        _status = 43
                else :
                    _status = 0
                    _obj_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], _obj_type, \
                                        True, obj_attr_list["name"], False)

                    _preserved_command = obj_attr_list["command"]
                    _preserved_command_originated = obj_attr_list["command_originated"]

                    obj_attr_list.update(_obj_attr_list)

                    obj_attr_list["command"] = _preserved_command
                    obj_attr_list["command_originated"] = _preserved_command_originated
            
                    if cmd.count("capture") :
                        obj_attr_list["mgt_101_capture_request_originated"] = obj_attr_list["command_originated"]
                        if obj_attr_list["capture_supported"].lower() != "true" :
                            _msg = "Capture operations are not supported on \"" + _cloud_parameters["description"] + "\" clouds." 
                            _status = 9000
                            raise self.ObjectOperationException(_msg, _status)
                    elif cmd.count("migrate") or cmd.count("protect") :
                        op = cmd.split("-")[1]
                        obj_attr_list["mgt_501_" + op + "_request_originated"] = obj_attr_list["command_originated"]
                        
                        vmc_attr = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
                        host_attr = self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, obj_attr_list["host"], False)
                        
                        dest_name = obj_attr_list["destination"]
                        
                        if not dest_name[:5] == "host_" :
                            dest_name = "host_" + dest_name 
                            
                        if host_attr["name"] == dest_name :
                            _msg = "Source and destination hosts are the same. Try again."
                            _status = 9421
                            raise self.ObjectOperationException(_msg, _status) 
                            
                        if not self.osci.object_exists(obj_attr_list["cloud_name"], "HOST", dest_name, True) :
                            _msg = "Destination HOST object for migration does not exist: " + obj_attr_list["destination"]
                            _status = 9001
                            raise self.ObjectOperationException(_msg, _status)
                        
                        dest_host_attr = self.osci.get_object(obj_attr_list["cloud_name"], "HOST", True, dest_name, False)
                        dest_vmc_attr = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, dest_host_attr["vmc"], False)
                        
                        obj_attr_list["destination_vmc"] = dest_vmc_attr["uuid"]
                        obj_attr_list["destination_vmc_cloud_ip"] = dest_vmc_attr["cloud_ip"]
                        obj_attr_list["destination_vmc_name"] = dest_vmc_attr["name"]
                        obj_attr_list["destination_vmc_pool"] = dest_vmc_attr["pool"]
                        
                        if vmc_attr[op + "_supported"].lower() != "true" :
                            _msg = op + " operations are not supported on the source: " + vmc_attr["name"]
                            _status = 9002
                            raise self.ObjectOperationException(_msg, _status)
                        
                        if dest_vmc_attr[op + "_supported"].lower() != "true" :
                            _msg = op  + " operations are not supported on the destination: " + dest_name 
                            _status = 9002
                            raise self.ObjectOperationException(_msg, _status)
                            
                        obj_attr_list["destination_name"] = dest_name
                        obj_attr_list["destination_uuid"] = dest_host_attr["uuid"]
                        obj_attr_list["destination"] = dest_name.split("host_", 1)[1]
                        
                        if obj_attr_list["interface"] == "default" :
                            if dest_host_attr[op + "_interface"] != "default" :
                                obj_attr_list["interface"] = dest_host_attr[op + "_interface"]
                            else :
                                obj_attr_list["interface"] = obj_attr_list["destination"]
                        
                        obj_attr_list["destination_ip"] = dest_host_attr["cloud_ip"]
                        
                        choices = obj_attr_list[op + "_protocol_supported"].split(",")
                            
                        obj_attr_list["choices"] = ",".join(choices)
                            
                        if obj_attr_list["protocol"] == "default" :
                                
                            if (op + "_protocol") in obj_attr_list :
                                obj_attr_list["protocol"] = obj_attr_list[op + "_protocol"]
                            else :
                                cbwarn("default " + op + "_protocol not specified for this cloud." \
                                    " Will assume defaults.", True)
                                obj_attr_list["protocol"] = choices[0]
                                    
                        if obj_attr_list["protocol"] not in choices :
                            raise self.ObjectOperationException(op + " protocol " + obj_attr_list["protocol"] + \
                                                                " not supported. Please choose one of: " + \
                                                                    " ".join(choices), 9003)
                                
                    elif cmd.count("runstate") :
                        obj_attr_list["mgt_201_runstate_request_originated"] = obj_attr_list["command_originated"]
                        if obj_attr_list["runstate_supported"].lower() != "true" :
                            _msg = "Runstate operations are not supported on \"" + _cloud_parameters["description"] + "\" clouds." 
                            _status = 9000
                            raise self.ObjectOperationException(_msg, _status)
                    elif cmd.count("resize") :
                        obj_attr_list["mgt_301_resize_request_originated"] = obj_attr_list["command_originated"]
                        if obj_attr_list["resize_supported"].lower() != "true" :
                            _msg = "Resize operations are not supported on \"" + _cloud_parameters["description"] + "\" clouds." 
                            _status = 9000
                            raise self.ObjectOperationException(_msg, _status)
                    elif cmd.count("detach") :
                        obj_attr_list["mgt_901_deprovisioning_request_originated"] = obj_attr_list["command_originated"]
                    elif cmd.count("login") or cmd.count("display") :
                        pass
                    else :
                        False
            ######### "ACTIVE" OPERATION OBJECT INITIALIZATION - END #########

            ######### "PASSIVE" OPERATION OBJECT INITIALIZATION - BEGIN #########
            elif cmd == "cloud-list" :
                _fmsg = ""
                _status = 0

            elif cmd == "global-list" :
                _fmsg = ""
                _status = 0

            elif cmd == "global-show" :
                _fmsg = ""
                _status = 0

            elif cmd == "global-alter" :
                _fmsg = ""
                _status = 0

            elif cmd == "wait-until" :
                _status = 0
                
            # This is not an error. Do not delete.
            elif cmd.count("api") :
                _status = 0

            elif cmd.count("list") or \
            cmd.count("show") or \
            cmd.count("alter") or \
            cmd.count("stats") or \
            cmd.count("expid-manage") :

                _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])
                obj_attr_list["username"] = _cloud_parameters["username"]
                if cmd.count("show") or cmd.count("alter") :
                    if '_' not in obj_attr_list["name"]  and '-' not in obj_attr_list["name"] and _obj_type.upper() != "VMC":
                        obj_attr_list["name"] = _obj_type.lower() + "_" + obj_attr_list["name"]

                    if _obj_type.lower().count("counter") :
                        _status = self.get_counters(obj_attr_list["cloud_name"], obj_attr_list)   

                if cmd.count("alter") :
                    _status = self.get_counters(obj_attr_list["cloud_name"], obj_attr_list)
                
                if cmd.count("stats") :
                    obj_attr_list["command"] = obj_attr_list["command"].replace("stats-get", "stats")
     
                obj_attr_list["regression"] = _cloud_parameters["regression"]
                obj_attr_list["cloud_name"] = _cloud_parameters["name"]
                obj_attr_list["cloud_model"] = _cloud_parameters["model"]
                obj_attr_list["all"] = _cloud_parameters["all"]
                _status = 0
            ######### "PASSIVE" OPERATION OBJECT INITIALIZATION - END #########
            
            else :
                _fmsg = "Unknown operation for " + _obj_type + " object: "
                _fmsg += cmd
                _msg = _fmsg
                _status = 35

            obj_attr_list["command"] = obj_attr_list["command"].replace("-", '').replace("cloud", "cld")

            if _operation + "_parallel" not in obj_attr_list and not cmd.count("api-check") and not cmd.count("list") :
                if self.msci :
                    self.get_counters(obj_attr_list["cloud_name"], obj_attr_list)
                    self.record_management_metrics(obj_attr_list["cloud_name"], _obj_type, obj_attr_list, "trace")

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = _obj_type + " object initialization failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = _obj_type + " object initialization success."
                cbdebug(_msg)

            return _status, _msg

    @trace    
    def admission_control(self, obj_type, obj_attr_list, transaction) :
        '''
        TBD
        '''
        try :            
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _admission_control_limits = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                             "admission_control", False)
            if transaction == "attach" :
                if obj_type != "AI" :
                    _reservation = self.osci.update_counter(obj_attr_list["cloud_name"], obj_type, \
                                                            "RESERVATIONS", \
                                                            "increment")
                else :
                    # Since AIs have to wait for the VMs to be created, the
                    # reservation is already taken during the "pre-attach AI"
                    # phase.
                    _reservation = self.osci.count_object(obj_attr_list["cloud_name"], "AI", "RESERVATIONS")
                    
                if int(_reservation) > int(_admission_control_limits[obj_type.lower() + "_max_reservations"]) :
                    _status = 101
                    _fmsg = "Reservations for " + obj_type + " objects exhausted."
                    self.osci.update_counter(obj_attr_list["cloud_name"], obj_type, "RESERVATIONS", \
                                                            "decrement")

                    raise self.ObjectOperationException(_fmsg, 10)
                
                if obj_type == "VM" :
                    vmc = obj_attr_list["vmc"]
                        
                    _msg = "Increasing the \"number of VMs\" counter for the VMC: " + vmc 
                    cbdebug(_msg)
                    _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                      vmc, False, "nr_vms", 1, True)
                    _msg = "New value is " + str(_vmc_reservation)
                    cbdebug(_msg)

                    _vmc_attrs = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, vmc, False)
                    if int(_vmc_reservation) > int(_vmc_attrs["max_vm_reservations"]) :
                        _status = 102
                        _fmsg ="VMC-wide reservations for VM objects exhausted."
                        raise self.ObjectOperationException(_fmsg, 10)

                    # This key can be safely deleted. It should not be written
                    # in the datastore as part of the "VM" object (it is already
                    # part of the "VMC" object.
                    if "vmc_max_vm_reservations" in obj_attr_list :
                        del obj_attr_list["vmc_max_vm_reservations"]
                
                else :

                    True

            elif transaction == "migrate" :
                vmc = obj_attr_list["destination_vmc"]
                    
                _msg = "Increasing the \"number of VMs\" counter for the VMC: " + vmc 
                cbdebug(_msg)
                _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                  vmc, False, "nr_vms", 1, True)
                _msg = "New value is " + str(_vmc_reservation)
                cbdebug(_msg)

                _vmc_attrs = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, vmc, False)
                if int(_vmc_reservation) > int(_vmc_attrs["max_vm_reservations"]) :
                    _status = 102
                    _fmsg ="VMC-wide reservations for VM objects exhausted."
                    raise self.ObjectOperationException(_fmsg, 10)
                    
            elif transaction == "rollbackmigrate" :
                vmc = obj_attr_list["destination_vmc"]
                
                _msg = "Decreasing the \"number of VMs\" counter for the "
                _msg += "VMC " + vmc + " due to a rollback."
                cbdebug(_msg)
                _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                                 vmc, False, "nr_vms", -1, True)

                _msg = "New value is " + str(_vmc_reservation)
                cbdebug(_msg)
                
            elif transaction == "migratefinish" :
                vmc = obj_attr_list["vmc"]
                
                _msg = "Decreasing the \"number of VMs\" counter for the "
                _msg += "VMC " + vmc + " after migration finished."
                cbdebug(_msg)
                _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                                 vmc, False, "nr_vms", -1, True)

                _msg = "New value is " + str(_vmc_reservation)
                cbdebug(_msg)

            elif transaction == "detach" :
                _reservation = self.osci.update_counter(obj_attr_list["cloud_name"], obj_type, "RESERVATIONS", \
                                                            "decrement")

                if obj_type == "VM" :

                    _msg = "Decreasing the \"number of VMs\" counter for the "
                    _msg += "VMC " + obj_attr_list["vmc"]
                    cbdebug(_msg)
                    _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                                     obj_attr_list["vmc"], \
                                                                     False, \
                                                                     "nr_vms", \
                                                                     -1, True)

                    _msg = "New value is " + str(_vmc_reservation)
                    cbdebug(_msg)

                elif obj_type == "AI" :

                    if "aidrs" in obj_attr_list and \
                    obj_attr_list["aidrs"] != "none" \
                    and self.osci.object_exists(obj_attr_list["cloud_name"], "AIDRS", obj_attr_list["aidrs"], False) :
                        _msg = "This AI was generated by the AIDRS \""
                        _msg += obj_attr_list["aidrs"]+ "\". Decreasing the "
                        _msg += "parameter \"number of AIs\" on this AIDRS object."
                        cbdebug(_msg)
                        _aidrs_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AIDRS", \
                                                                         obj_attr_list["aidrs"], \
                                                                         False, \
                                                                         "nr_ais", \
                                                                         -1, \
                                                                         True)
                        _msg = "New value is " + str(_aidrs_reservation)
                        cbdebug(_msg)

                else :
                    True

            elif transaction == "rollbackdetach" :
                self.osci.update_counter(obj_attr_list["cloud_name"], obj_type, "RESERVATIONS", \
                                         "increment")

                if obj_type == "VM" :
                    _msg = "Increasing the \"number of VMs\" counter for the "
                    _msg += "VMC " + obj_attr_list["vmc"] + " due to a "
                    _msg += "rollback."
                    cbdebug(_msg)
                    _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                                     obj_attr_list["vmc"], \
                                                                     False, \
                                                                     "nr_vms", \
                                                                     1, True)

                    _msg = "New value is " + str(_vmc_reservation)
                    cbdebug(_msg)
                        
                elif obj_type == "AI" :

                    if "aidrs" in obj_attr_list and obj_attr_list["aidrs"] != "none" :
                        _msg = "This AI was generated by the AIDRS \""
                        _msg += obj_attr_list["aidrs"]+ "\". Increasing the "
                        _msg += "parameter \"number of AIs\" on this AIDRS object"
                        _msg += "due to a rollback"
                        cbdebug(_msg)
                        _aidrs_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AIDRS", \
                                                                         obj_attr_list["aidrs"], \
                                                                         False, \
                                                                         "nr_ais",\
                                                                          1, \
                                                                          True)
                        _msg = "New value is " + str(_aidrs_reservation)
                        cbdebug(_msg)

                else :
                    True

            elif transaction == "rollbackattach" :
                self.osci.update_counter(obj_attr_list["cloud_name"], obj_type, "RESERVATIONS", \
                                         "decrement")
                
                if obj_type == "VM" :
                    vmc = obj_attr_list["vmc"]
                    _msg = "Decreasing the \"number of VMs\" counter for the "
                    _msg += "VMC " + vmc + " due to a "
                    _msg += "rollback."
                    cbdebug(_msg)
                    _vmc_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMC", \
                                                                     vmc, False, "nr_vms", -1, True)

                    _msg = "New value is " + str(_vmc_reservation)
                    cbdebug(_msg)

                elif obj_type == "AI" :

                    if "aidrs" in obj_attr_list and obj_attr_list["aidrs"] != "none" :
                        _msg = "This AI was generated by the AIDRS \""
                        _msg += obj_attr_list["aidrs"]+ "\". Decreasing the "
                        _msg += "parameter \"number of AIs\" on this AIDRS object"
                        _msg += "due to a rollback"
                        cbdebug(_msg)
                        _aidrs_reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AIDRS", \
                                                                         obj_attr_list["aidrs"], \
                                                                         False, \
                                                                         "nr_ais",\
                                                                          -1, \
                                                                          True)
                        _msg = "New value is " + str(_aidrs_reservation)
                        cbdebug(_msg)

                else :
                    True

            else :
                _msg = "Unknown transaction type: " + transaction
                raise self.ObjectOperationException(_msg, 11)

            _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _fmsg = str(obj.msg)
            
        except KeyError, e :
            _fmsg = str(e)
            _status = 2341
        
        finally :
            
            _imsg = "Reservation for " + obj_type + " object " + obj_attr_list["uuid"]
            if _status :
                _msg = _imsg + " could not be obtained: " + _fmsg
                cberr(_msg, True)
                raise self.ObjectOperationException(_msg, 1024)
            else :
                if transaction == "attach" :
                    _word = "obtained."
                elif transaction == "rollbackdetach" :
                    _word = "re-obtained"
                else :
                    _word = "released"
                _msg = _imsg + " was successfully " + _word + '.'
                cbdebug(_msg)
                return True

    @trace    
    def speculative_admission_control(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            

            _admission_control_limits = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                             "admission_control", \
                                                             False)
            # We need to check if the number of AI reservations was exhausted 
            # BEFORE issuing the creation of new VMs.
            _reservation = self.osci.update_counter(obj_attr_list["cloud_name"], "AI", "RESERVATIONS", "increment")

            if int(_reservation) > int(_admission_control_limits["ai_max_reservations"]) :
                _status = 101
                _fmsg = "Reservations for AI objects exhausted."
                self.osci.update_counter(obj_attr_list["cloud_name"], "AI", "RESERVATIONS", "decrement")
                raise self.ObjectOperationException(_fmsg, 10)

            if "aidrs" in obj_attr_list and obj_attr_list["aidrs"] != "none" \
            and self.osci.object_exists(obj_attr_list["cloud_name"], "AIDRS", obj_attr_list["aidrs"], False) :

                _msg = "This AI was generated by the AIDRS \""
                _msg += obj_attr_list["aidrs"]+ "\". Increasing the "
                _msg += "parameter \"number of AIs\" on this AIDRS object."
                cbdebug(_msg)
                _reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AIDRS", \
                                                                 obj_attr_list["aidrs"], \
                                                                 False, "nr_ais", 1, True)
                _msg = "New value is " + str(_reservation)
                cbdebug(_msg)

                if int(_reservation) > int(obj_attr_list["max_ais"]) :
                    _status = 102
                    _fmsg ="AIDRS-wide reservations for AI objects exhausted."
                    _reservation = self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AIDRS", \
                                                                     obj_attr_list["aidrs"], \
                                                                     False, \
                                                                     "nr_ais", -1, True)
                    self.osci.update_counter(obj_attr_list["cloud_name"], "AI", "RESERVATIONS", "decrement")
                    raise self.ObjectOperationException(_fmsg, 10)

                # This key can be safely deleted. It should not be written
                # in the datastore as part of the "AI" object (it is already
                # part of the "AIDRS" object.
                del obj_attr_list["max_ais"]

            # Now we check if the number of VMs that this AI requires is higher
            # than the number of current reservations
            _current_vm_reservations = self.osci.count_object(obj_attr_list["cloud_name"], "VM", "RESERVATIONS")

            _vm_counter = len(obj_attr_list["vms"].split(','))
            
            if _vm_counter + int(_current_vm_reservations) > int(_admission_control_limits["vm_max_reservations"]) :
                _fmsg = "Reservations for VMs objects (for this AI) exhausted."
                raise self.ObjectOperationException(_fmsg, 28)
            else :
                _msg = "Speculatively checked that there are enough reservations"
                _msg += " for all VM objects for this AI."
                cbdebug(_msg)

            # Now the VMs cane be created in parallel
            if _vm_counter > int(obj_attr_list["attach_parallelism"]) :
                obj_attr_list["attach_parallelism"] = int(obj_attr_list["attach_parallelism"])
            else :
                obj_attr_list["attach_parallelism"] = _vm_counter

            _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _fmsg = str(obj.msg)
        
        finally :
            if _status :
                _msg = "Speculative admission control failed: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_fmsg, 10)
            else :
                _msg = "Speculative admission control success."
                cbdebug(_msg)
            return True

    @trace    
    def fast_uuid_to_name(self, cloud_name, obj_type, obj_uuid, translation_cache = False) :
        '''
        This function receives an object type and objet UUID and returns a name.
        It optionally can receive a dictionary that has UUID->name pairs 
        - to be used as a cache - to save network accesses to the object store.
        It was built specially to be used with the *list commands (human users 
        normally do not like to  see UUIDs when they ask for a list of objects).
        Perhaps this function would fit better in the "auxiliary" directory, in
        the "data_ops.py" file, but we are really,really trying to keep all
        accesses to the object store concentrated on the files on the 
        "operations" directory.
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _obj_name = "(orphan)"

        try :
            if translation_cache :
                if obj_uuid in translation_cache :
                    _obj_name = translation_cache[obj_uuid]
                else :
                    _obj_attr_list = self.osci.get_object(cloud_name, obj_type, False, \
                                                          obj_uuid, False)
                    _obj_name = _obj_attr_list["name"]
                    translation_cache[obj_uuid] = _obj_name
            else :
                _obj_attr_list = self.osci.get_object(cloud_name, obj_type, True, \
                                                      obj_uuid, False)
                _obj_name = _obj_attr_list["name"]

            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _fmsg = str(obj.msg)
            _status = 0
        
        finally :
            if _status :
                _msg = "Fast uuid to name translation failed: " + _fmsg
                cberr(_msg)
            else :
                #_msg = "Fast uuid to name translation success."
                #cbdebug(_msg)
                pass
            return _obj_name

    @trace
    def initialize_metric_name_list(self, obj_attr_list) :
        '''
        TBD
        '''
        _collection_names = [ "reported_management_VM_metric_names", \
                             "reported_runtime_os_HOST_metric_names", \
                             "reported_runtime_os_VM_metric_names", \
                             "reported_runtime_app_VM_metric_names" ]

        _mon_parameters = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "mon_defaults", False)

        for _collection_name in _collection_names :
            _document = {}
            _document["expid"] = self.expid
            _document["_id"] = b64encode(sha1(_document["expid"]).digest())
            for _metric_name in _mon_parameters[_collection_name.lower()].split(',') :
                _document[_metric_name] = "1"
            self.msci.update_document(_collection_name + '_' + _mon_parameters["username"], _document)

    @trace
    def pre_select_object(self, obj_attr_list, obj_type, username) :
        '''
        TBD
        '''
        try :
            _status = 100
            if obj_attr_list["name"] in ["random", "youngest", "oldest"] :
                _obj_list = self.osci.query_by_view(obj_attr_list["cloud_name"], obj_type, "BYUSERNAME", username)
                if _obj_list :
                    if obj_attr_list["name"] == "random" :
                        obj_attr_list["name"] = choice(_obj_list).split('|')[1] 
                    elif obj_attr_list["name"] == "youngest" : 
                        _obj_list = self.osci.query_by_view(obj_attr_list["cloud_name"], obj_type, "BYUSERNAME", username)
                        obj_attr_list["name"] = _obj_list[-1].split('|')[-1]
                    elif obj_attr_list["name"] == "oldest" :
                        _obj_list = self.osci.query_by_view(obj_attr_list["cloud_name"], obj_type, "BYUSERNAME", username)
                        obj_attr_list["name"] = _obj_list[0].split('|')[-1]
                    _status = 0
                else :
                    _fmsg = "Not enough " + obj_type + "s attached to select from"
                    _status = 165
            else :
                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = obj_type + " object pre-selection failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, 10)
            else :
                _msg = obj_type + " object pre-selection success."
                cbdebug(_msg)
                return True
            
    @trace
    def get_vms_and_role(self, sut_component):
        '''
        TBD
        '''
        _vars = sut_component.split("_x_")

        _nr_vms = _vars[0]
        _vm_role = _vars[1].lower()
            
        return _nr_vms, _vm_role

    @trace
    def propagate_ai_attributes_to_vm(self, vm_role, cloud_ips, obj_attr_list) :
        '''
        TBD
        '''
        if vm_role + "_pref_host" in obj_attr_list :
            _pool = obj_attr_list[vm_role + "_pref_host"]
        else :
            if vm_role + "_pref_pool" in obj_attr_list :
                _pool = obj_attr_list[vm_role + "_pref_pool"]
            else :
                _pool = "auto"

        if vm_role + "_meta_tag" in obj_attr_list :
            _meta_tag = obj_attr_list[vm_role + "_meta_tag"]
        else :
            _meta_tag = "empty"

        if vm_role + "_size" in obj_attr_list :
            _size = obj_attr_list[vm_role + "_size"]
        else :
            _size = 'default'

        _extra_parms = "sut=" + obj_attr_list["sut"]

        if "credentials" in obj_attr_list :
            _extra_parms += ",credentials=" + obj_attr_list["credentials"]

        if "access" in obj_attr_list :
            _extra_parms += ",access=" + obj_attr_list["access"]
        
        if vm_role + "_netid" in obj_attr_list :
            _extra_parms += ",netid=" + obj_attr_list[vm_role + "_netid"]

        if vm_role + "_imageid1" in obj_attr_list :
            _extra_parms += ",imageid1=" + obj_attr_list[vm_role + "_imageid1"]

        if vm_role + "_login" in obj_attr_list :
            _extra_parms += ",login=" + obj_attr_list[vm_role + "_login"]

        if vm_role + "_resource_limits" in obj_attr_list :
            _extra_parms += ",resource_limits=" + obj_attr_list[vm_role + "_resource_limits"]

        if vm_role + "_cloud_vv" in obj_attr_list :
            _extra_parms += ",cloud_vv=" + obj_attr_list[vm_role + "_cloud_vv"]

        if vm_role + "_cloud_vv_type" in obj_attr_list :
            _extra_parms += ",cloud_vv_type=" + obj_attr_list[vm_role + "_cloud_vv_type"]

        if vm_role + "_sla_provisioning_target" in obj_attr_list :
            _extra_parms += ",sla_provisioning_target=" + obj_attr_list[vm_role + "_sla_provisioning_target"]            

        if vm_role + "_cloud_ips" in obj_attr_list :
            if not vm_role in cloud_ips :
                cloud_ips[vm_role] = obj_attr_list[vm_role + "_cloud_ips"].split(';')

        if obj_attr_list["load_balancer"].strip().lower() == "true" :
            _size = 'load_balanced_default'        

        return _pool, _meta_tag, _size, _extra_parms

    @trace
    def create_vm_list_for_ai(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _app_type = obj_attr_list["type"]
            obj_attr_list["parallel_operations"] = {}
            _vm_attach_command_lines = []
            obj_attr_list["vms"] = ''

            _vm_counter = 0  
            _vm_creation_list = {}
            _vm_command_list = ''

            _tiers = obj_attr_list["sut"].split("->")
            
            obj_attr_list["sut"] = ''
            for _tier in _tiers :
                if _tier.count("_x_") :
                    obj_attr_list["sut"] += _tier + "->"
                else :
                    obj_attr_list["sut"] += "1_x_" + _tier + "->"

            obj_attr_list["sut"] = obj_attr_list["sut"][:-2]
            _tiers = obj_attr_list["sut"].split("->")

            '''
            Support load balancer configurations on-the-fly.
            '''
            
            if "load_balancer" not in obj_attr_list :
                obj_attr_list["load_balancer"] = "false"
            
            if obj_attr_list["load_balancer"].strip().lower() == "true" :
                for _tier_nr in range(0, len(_tiers)) :
                    if _tiers[_tier_nr].split("_x_")[1] == obj_attr_list["load_generator_role"] :
                        _nr_child_vms, _child_role = self.get_vms_and_role(_tiers[_tier_nr + 1])
                        obj_attr_list["load_balancer_target_role"] = _child_role
                        _tiers[_tier_nr + 1] = obj_attr_list["load_balancer_target_children"] + "_x_" + _child_role
                        _tiers.insert(_tier_nr + 1, "1_x_lb")

                obj_attr_list["sut"] = "->".join(_tiers)
            else :
                obj_attr_list["load_balancer_target_role"] = "none"

            _vm_nr = 1
            _cloud_ips = {}
            for _tier_nr in range(0, len(_tiers)) :

                _nr_vms, _vm_role = self.get_vms_and_role(_tiers[_tier_nr])

                if _vm_role == obj_attr_list["load_generator_role"] :
                    if len(_tiers) > 1 :
                        obj_attr_list["load_generator_target_role"] = _tiers[_tier_nr + 1].split("_x_")[1]
                    else :
                        obj_attr_list["load_generator_target_role"] = _tiers[_tier_nr].split("_x_")[1]

                _pool, _meta_tag, _size, _extra_parms = \
                self.propagate_ai_attributes_to_vm(_vm_role, _cloud_ips, obj_attr_list) 

                _attach_action = obj_attr_list["staging"]

                _vg = ValueGeneration(self.pid)
                _nr_vms = int(_vg.get_value(_nr_vms, _nr_vms))

                for _idx in range(0, int(_nr_vms)) :
                    if _vm_role in _cloud_ips :
                        if _extra_parms != '' :
                            _cloud_ip = ','
                        else :
                            _cloud_ip = ''
                        _cloud_ip += "cloud_ip=" + _cloud_ips[_vm_role].pop()
                    else :
                        _cloud_ip = ''

                    obj_attr_list["parallel_operations"][_vm_counter] = {} 
                    _pobj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,10000000000000000) + _vm_counter)))
                    _pobj_uuid = _pobj_uuid.upper()
                    obj_attr_list["vms"] += _pobj_uuid + ','
                    obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _pobj_uuid
                    obj_attr_list["parallel_operations"][_vm_counter]["ai"] = obj_attr_list["uuid"]
                    obj_attr_list["parallel_operations"][_vm_counter]["ai_name"] = obj_attr_list["name"]
                    obj_attr_list["parallel_operations"][_vm_counter]["aidrs"] = obj_attr_list["aidrs"]
                    obj_attr_list["parallel_operations"][_vm_counter]["aidrs_name"] = obj_attr_list["aidrs_name"]
                    obj_attr_list["parallel_operations"][_vm_counter]["pattern"] = obj_attr_list["pattern"]
                    obj_attr_list["parallel_operations"][_vm_counter]["type"] = obj_attr_list["type"]
                    obj_attr_list["parallel_operations"][_vm_counter]["base_type"] = obj_attr_list["base_type"]
                    obj_attr_list["parallel_operations"][_vm_counter]["mode"] = obj_attr_list["mode"]
                    obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] +\
                     ' ' + _vm_role + ' ' + _pool + ' ' + _meta_tag + ' ' +\
                      _size + ' ' + _attach_action + ' ' + _extra_parms + _cloud_ip
                    obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-attach"
                    _vm_command_list += obj_attr_list["cloud_name"] + ' ' +\
                     _vm_role + ", " + _pool + ", " + _meta_tag + ", " +\
                      _size + ", " + _attach_action + ", " + _extra_parms + _cloud_ip + "; "
                      
                    _vm_counter += 1

            if not "drivers_per_sut" in obj_attr_list :
                obj_attr_list["drivers_per_sut"] = 0
 
            if not "suts" in obj_attr_list :
                obj_attr_list["suts"] = 1

            if int(obj_attr_list["drivers_per_sut"]) :
                _nr_drivers = int(obj_attr_list["suts"])/int(obj_attr_list["drivers_per_sut"])
            else :
                _nr_drivers = 0
                
            # This section needs to be re-done (or maybe removed)
            for _idx in range(0, int(_nr_drivers)) :
                obj_attr_list["parallel_operations"][_vm_counter] = {} 
                _pobj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,10000000000000000) + _vm_counter)))
                _pobj_uuid = _pobj_uuid.upper()
                obj_attr_list["vms"] += _pobj_uuid + ','
                obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _pobj_uuid
                obj_attr_list["parallel_operations"][_vm_counter]["ai"] = obj_attr_list["uuid"]
                obj_attr_list["parallel_operations"][_vm_counter]["as"] = obj_attr_list["as"]
                obj_attr_list["parallel_operations"][_vm_counter]["type"] = obj_attr_list["type"]
                obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] +\
                 " driver_" + _app_type + ' ' + _pool + ' ' + _meta_tag +\
                  ' ' + _size + ' ' + _attach_action
                obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-attach"
                _vm_command_list += obj_attr_list["cloud_name"] + " driver_" +\
                 _app_type + ", " + ' ' + _pool + ' ' + _meta_tag + ' ' +\
                  _size + ' ' + _attach_action + "; "
                _vm_counter += 1

            obj_attr_list["vms"] = obj_attr_list["vms"][:-1]
            obj_attr_list["vms_nr"] = _vm_counter
            obj_attr_list["drivers_nr"] = _nr_drivers

            obj_attr_list["osp"] = dic2str(self.osci.oscp())
            obj_attr_list["msp"] = dic2str(self.msci.mscp())
                        
            if obj_attr_list["staging"] + "_complete" in obj_attr_list :
                self.osci.publish_message(obj_attr_list["cloud_name"], \
                                          "VM", \
                                          "staging", \
                                          obj_attr_list["uuid"] + ";vmcount;" + str(_vm_counter), \
                                          1, \
                                          3600)

            _msg = "VM attach command list is: " + _vm_command_list
            cbdebug(_msg)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM list creation failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM list creation success."
                cbdebug(_msg)
                return True

    @trace
    def assign_roles(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _roles = 0            
            _vm_list = obj_attr_list["vms"].split(',')

            if "load_manager_role" in obj_attr_list :

                for _vm in _vm_list :
                    _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                    if _vm_role == obj_attr_list["load_manager_role"] :

                        _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", \
                                                             False, \
                                                             _vm_uuid, \
                                                             False)
                
                        obj_attr_list["cloud_ip"] = _vm_attr_list["cloud_ip"]
                        obj_attr_list["cloud_hostname"] = _vm_attr_list["cloud_hostname"]
                        obj_attr_list["load_manager_vm"] = _vm_uuid
                        obj_attr_list["load_manager_ip"] = _vm_attr_list["cloud_ip"]
                        _roles +=1
                        break

            if "load_generator_role" in obj_attr_list :
                
                if obj_attr_list["load_generator_role"] == obj_attr_list["load_manager_role"] :
                        obj_attr_list["load_generator_vm"] = obj_attr_list["load_manager_vm"]
                        obj_attr_list["load_generator_ip"] = obj_attr_list["load_manager_ip"]
                        _roles +=1
                else :

                    for _vm in _vm_list :
                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                        if _vm_role == obj_attr_list["load_generator_role"] :

                            _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", \
                                                                 False, \
                                                                 _vm_uuid, \
                                                                 False)

                            obj_attr_list["load_generator_vm"] = _vm_uuid
                            obj_attr_list["load_generator_ip"] = _vm_attr_list["cloud_ip"]
                            _roles +=1
                            break

            if "metric_aggregator_role" in obj_attr_list :

                if obj_attr_list["metric_aggregator_role"] == obj_attr_list["load_manager_role"] :
                        obj_attr_list["metric_aggregator_vm"] = obj_attr_list["load_manager_vm"]
                        obj_attr_list["metric_aggregator_ip"] = obj_attr_list["load_manager_ip"]
                        _roles +=1
                else :

                    for _vm in _vm_list :
                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                        if _vm_role == obj_attr_list["metric_aggregator_role"] :

                            _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", \
                                                                 False, \
                                                                 _vm_uuid, \
                                                                 False)

                            obj_attr_list["metric_aggregator_vm"] = _vm_uuid
                            obj_attr_list["metric_aggregator_ip"] = _vm_attr_list["cloud_ip"]
                            _roles +=1
                            break

            if "load_generator_target_role" in obj_attr_list :

                if obj_attr_list["load_generator_target_role"] == obj_attr_list["load_generator_role"] :
                        obj_attr_list["load_generator_target_vm"] = obj_attr_list["load_generator_vm"]
                        obj_attr_list["load_generator_target_ip"] = obj_attr_list["load_generator_ip"]
                else :
                    obj_attr_list["load_generator_target_vm"] = ''
                    obj_attr_list["load_generator_target_ip"] = ''

                    for _vm in _vm_list :
                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                        if _vm_role == obj_attr_list["load_generator_target_role"] :

                            _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", \
                                                                 False, \
                                                                 _vm_uuid, \
                                                                 False)

                            obj_attr_list["load_generator_target_vm"] += _vm_uuid + ','
                            obj_attr_list["load_generator_target_ip"] += _vm_attr_list["cloud_ip"] + ','

                    obj_attr_list["load_generator_target_vm"] = obj_attr_list["load_generator_target_vm"][:-1]
                    obj_attr_list["load_generator_target_ip"] = obj_attr_list["load_generator_target_ip"][:-1]
                    
            if "load_balancer_target_role" in obj_attr_list :

                if obj_attr_list["load_balancer_target_role"] == "none" :
                        obj_attr_list["load_balancer_target_vm"] = "none"
                        obj_attr_list["load_balancer_target_ip"] = "none"
                else :
                    obj_attr_list["load_balancer_target_vm"] = ''
                    obj_attr_list["load_balancer_target_ip"] = ''

                    for _vm in _vm_list :
                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')

                        if _vm_role == obj_attr_list["load_balancer_target_role"] :

                            _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", \
                                                                 False, \
                                                                 _vm_uuid, \
                                                                 False)

                            obj_attr_list["load_balancer_target_vm"] += _vm_uuid + ','
                            obj_attr_list["load_balancer_target_ip"] += _vm_attr_list["cloud_ip"] + ','

                    obj_attr_list["load_balancer_target_vm"] = obj_attr_list["load_balancer_target_vm"][:-1]
                    obj_attr_list["load_balancer_target_ip"] = obj_attr_list["load_balancer_target_ip"][:-1]

            if _roles < 3 :
                _fmsg = "One of the roles for this AI (\"load generator\", "
                _fmsg += "\"load manager\", or \"metric_aggregator\") was not "
                _fmsg += "specified."
                _status = 9
            else :
                _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM role assignement failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM role assignement success."
                cbdebug(_msg)
                return True

    @trace
    def parallel_vm_config_for_ai(self, cloud_name, ai_uuid, operation) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _ai_attr_list = self.osci.get_object(cloud_name, "AI", False, ai_uuid, False)

            _obj_types = []
            _vm_names = []
            _vm_hns = []
            _vm_roles = []
            _vm_ip_addrs = []
            _vm_logins = []
            _vm_passwds = []
            _vm_priv_keys = []
            _vm_config_files = []
            _vm_post_boot_commands = []
            
            _vm_list = _ai_attr_list["vms"].split(',')

            _run_generic_scripts = False

            for _vm in _vm_list :
                
                _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                            
                _obj_attr_list = self.osci.get_object(cloud_name, "VM", False, _vm_uuid, False)

                _obj_types.append("VM")
                
                _vm_names.append(_obj_attr_list["name"])
                _vm_hns.append(_obj_attr_list["cloud_hostname"])
                _vm_roles.append(_obj_attr_list["role"])
                _vm_ip_addrs.append(_obj_attr_list["prov_cloud_ip"])
                _vm_logins.append(_obj_attr_list["login"])
                _vm_passwds.append(None)

                if "ssh_config_file" in _obj_attr_list :
                    _vm_config_files.append(_obj_attr_list["ssh_config_file"])
                else :
                    _vm_config_files.append(None)

                if not access(_obj_attr_list["identity"], F_OK) :
                    _obj_attr_list["identity"] = _obj_attr_list["identity"].replace(_obj_attr_list["username"], _obj_attr_list["login"])
                    _obj_attr_list["identity"] = _obj_attr_list["identity"].replace('/' + _obj_attr_list["local_dir_name"] + '/', '/' + _obj_attr_list["remote_dir_name"] + '/')                    
                _vm_priv_keys.append(_obj_attr_list["identity"])

                _vm_post_boot_commands.append("~/" + _obj_attr_list["remote_dir_name"] + "/scripts/common/cb_post_boot.sh")

            if operation == "setup" or operation == "resize" :

                if "run_generic_scripts" in _obj_attr_list and \
                _obj_attr_list["run_generic_scripts"].lower() != "false" :

                    _msg = "Performing generic application instance post_boot "
                    _msg += "configuration on all VMs belonging to " + _ai_attr_list["name"] + "..."                
                    cbdebug(_msg, True)
                    self.osci.pending_object_set(cloud_name, "AI", ai_uuid, "status", _msg)

                else :
                    _msg = "Bypassing generic VM post_boot configuration on all "
                    _msg += "VMs belonging to " + _ai_attr_list["name"] + "..."                
                    cbdebug(_msg, True)

                # This variable is permanent, now (for as long as the daemon lives)
                # but these parameters can still change across daemon invocations,
                # so we need to be sure to update them in case they are changed
                # by the user between one VApp to the next.
                
                self.proc_man_os_command.cloud_name =  _ai_attr_list["cloud_name"]
                self.proc_man_os_command.username = _vm_logins[0]
                self.proc_man_os_command.priv_key = _vm_priv_keys[0]
                self.proc_man_os_command.config_file = _vm_config_files[0]

                _status, _xfmsg = self.proc_man_os_command.parallel_run_os_command(_vm_post_boot_commands, \
                                                                    _vm_ip_addrs, \
                                                                    int(_ai_attr_list["attempts"]), \
                                                                    int(_ai_attr_list["update_frequency"]), \
                                                                    _ai_attr_list["execute_parallelism"], \
                                                                    _obj_attr_list["run_generic_scripts"], \
                                                                    _ai_attr_list["debug_remote_commands"])

                if _status :

                    _status = 1495
                    _fmsg = "Failure while executing generic post_boot configuration on "
                    _fmsg += "on all VMs beloging to " + _ai_attr_list["name"] + ": "
                    _fmsg += _xfmsg

            else :
                _status = 0

            # In the defaults, an application have multiple initialization phases
            # define for a particular application. So, the way this works is that
            # the user may specify commands (on the cloud defaults file) to be run 
            # in all of the applications in the form:
            # "<application type>_<role>_SETUP1" = command1
            # "<application type>_<role>_SETUP2" = command2 and so forth.

            # We then take that command and run it inside each VM in parallel.
            # When the last command completes inside all the VMs, we move to the next
            # command and repeat.

            # Just assuming the user will not have more than 100 initialization scripts
            # for each VM
            if not _status :
                
                if "run_application_scripts" in _ai_attr_list and \
                _ai_attr_list["run_application_scripts"].lower() != "false" :
                
                    _msg = "Running application-specific \"" + operation + "\" "
                    _msg += "configuration on all VMs belonging to " + _ai_attr_list["name"] + "..."                
                    cbdebug(_msg, True)
                    notify_client_refresh = False
                    if "first_app_run_finished" not in _ai_attr_list or \
                        _ai_attr_list["first_app_run_finished"].lower() != "true" :
                        notify_client_refresh = True
                        self.osci.update_object_attribute(_ai_attr_list["cloud_name"], "AI", _ai_attr_list["uuid"], \
                              False, "first_app_run_finished", "true")
                        _ai_attr_list["first_app_run_finished"] = "true"
                        
                        
                    self.osci.pending_object_set(cloud_name, "AI", ai_uuid, "status", _msg, notify_client_refresh)

                else :
                    _msg = "Bypassing application-specific configuration on all "
                    _msg += "VMs beloging to " + _ai_attr_list["name"] + "..."  
                    cbdebug(_msg, True)
                    _status = 0

                if "dont_start_load_manager" in _ai_attr_list and \
                    _ai_attr_list["dont_start_load_manager"].lower() == "true" :
                    _msg = "Load Manager will NOT be automatically"
                    _msg += " started during the deployment of "
                    _msg += _ai_attr_list["name"] + "..."                
                    cbdebug(_msg, True)

                if "dont_start_qemu_scraper" in _ai_attr_list and \
                    _ai_attr_list["dont_start_qemu_scraper"].lower() == "true" :
                    _msg = "QEMU Scraper will NOT be automatically"
                    _msg += " started during the deployment of "
                    _msg += _ai_attr_list["name"] + "..."                
                    cbdebug(_msg, True)

                _lmr = False
                
                for _num in range(1, 100) :
                    _found = False
                    _vm_command_list = []
                    for _idx in range(0, len(_vm_names)) :
                        _command_key = _vm_roles[_idx] + '_' + operation + str(_num)
    
                        if _command_key in _ai_attr_list :
                            if len(_ai_attr_list[_command_key]) > 1 :
                                _command = "~/" + _ai_attr_list[_command_key]
                                _found = True
                            else :
                                _command = "/bin/true"
                        else :
                            _command = "/bin/true"
    
                        _vm_command_list.append(_command)
    
                    if not _found :

                        if _lmr or operation != "setup" :
                            break
                        else :
                            if "dont_start_load_manager" in _ai_attr_list \
                            and _ai_attr_list["dont_start_load_manager"].lower() == "true" :
                                _lmr = True

                            else :
                                # This needs to be done only once, at the AI's
                                # initial deployment.
                                _lmr = _ai_attr_list["load_manager_role"]
                                
                                _msg = "Adding the startup of the load manager to the "
                                _msg += "list of commands. It will be executed on the "
                                _msg += "VM with the role \"" + _lmr + "\""
                                cbdebug(_msg)
                                
                                _ai_attr_list[_lmr + '_' + operation + str(_num + 1)] = "cb_start_load_manager.sh"

                                # The scraper startup is conditional only upon
                                # enablement of the load manager as well.
                                if "dont_start_qemu_scraper" not in _ai_attr_list \
                                       or _ai_attr_list["dont_start_qemu_scraper"].lower() != "true" :
                                    _msg = "Adding the startup of the qemu scraper to the "
                                    _msg += "list of commands. It will be executed on the "
                                    _msg += "VM with the role \"" + _lmr + "\""
                                    cbdebug(_msg)
                                    
                                    _ai_attr_list[_lmr + '_' + operation + str(_num + 2)] = "cb_start_qemu_scraper.sh"

                    if _ai_attr_list["run_application_scripts"].lower() != "false" :
                        _msg = "The following command list will be executed: "
                        _msg += ','.join(_vm_command_list)
                        cbdebug(_msg)
    
                        # Now run the application-specific initializations
                        _msg = "Executing command list described on " + operation
                        _msg += " step " + str(_num) + "..."
                        cbdebug(_msg)
                    else :
                        if _ai_attr_list["debug_remote_commands"].lower() != "false" :
                            _msg = operation.upper() + str(_num)
                            cbdebug(_msg, True)

                    self.proc_man_os_command.cloud_name =  _ai_attr_list["cloud_name"]
                    self.proc_man_os_command.username = _vm_logins[0]
                    self.proc_man_os_command.priv_key = _vm_priv_keys[0]

                    _status, _xfmsg = self.proc_man_os_command.parallel_run_os_command(_vm_command_list, \
                                                                        _vm_ip_addrs, \
                                                                        int(_ai_attr_list["attempts"]), \
                                                                        int(_ai_attr_list["update_frequency"]), \
                                                                        _ai_attr_list["execute_parallelism"], \
                                                                        _ai_attr_list["run_application_scripts"], 
                                                                        _ai_attr_list["debug_remote_commands"])

                    if _status :
    
                        _fmsg = "Failure while executing application-specific configuration on "
                        _fmsg += "on all VMs beloging to " + _ai_attr_list["name"] + ":\n "
                        _fmsg += _xfmsg
                        break

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Parallel VM configuration failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Parallel VM configuration success."
                cbdebug(_msg)
            return _status, _msg

    @trace
    def runstate_list_for_ai(self, obj_attr_list, target_state) :
        '''
        TBD
        '''
        obj_attr_list["parallel_operations"] = {}
        _vm_counter = 0
        _vm_list = obj_attr_list["vms"].split(',')
        _vm_command_list = ''
        try :
            for _vm in _vm_list :
                _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "VM", _vm_uuid)
                if target_state == "save" and _current_state != "attached" :
                    _vm_uuid = False
                elif target_state == "fail" and _current_state != "attached" :
                    _vm_uuid = False
                elif target_state == _current_state :
                    _vm_uuid = False

                if _vm_uuid :
                    obj_attr_list["parallel_operations"][_vm_counter] = {}
                    obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _vm_uuid
                    obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] + ' ' + _vm_name + " " + target_state
                    obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-runstate"
                    _vm_counter += 1
                    _vm_command_list += obj_attr_list["cloud_name"] + ' ' + _vm_name + ' ' + target_state + ', '

            obj_attr_list["state_changed_vms"] = _vm_counter

            if _vm_counter > int(obj_attr_list["runstate_parallelism"]) :
                obj_attr_list["runstate_parallelism"] = int(obj_attr_list["runstate_parallelism"])
            else :
                obj_attr_list["runstate_parallelism"] = _vm_counter

            _msg = "VM runstate command list is: " + _vm_command_list
            cbdebug(_msg)

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VM list state modification failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM list state modification success."
                cbdebug(_msg)
                return True

    @trace
    def destroy_vm_list_for_ai(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            obj_attr_list["parallel_operations"] = {}
            _vm_counter = 0

            _vm_list = obj_attr_list["vms"].split(',')

            if "exclude_vm" in obj_attr_list :
                _msg = "Excluding VM object " + obj_attr_list["exclude_vm"] 
                _msg += " from the list of VMs to be destroyed."
                cbdebug(_msg)
                _vm_uuid_to_exclude = obj_attr_list["exclude_vm"]
            else :
                _vm_uuid_to_exclude = "none"

            _vm_command_list = ''

            for _vm in _vm_list :

                if not _vm.count('|') :
                    # We expect this code path to be executed only rarely. That
                    # is why it is left so unoptimized.
                    if self.osci.object_exists(obj_attr_list["cloud_name"], "VM", _vm, False) :
                        _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", False, _vm, False)
                        _vm_uuid = _vm
                        _vm_role = _vm_attr_list["role"]
                        _vm_name = _vm_attr_list["name"]
                    else :
                        _vm_uuid = False
                else :
                    _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                    if not self.osci.object_exists(obj_attr_list["cloud_name"], "VM", _vm_uuid, False) :
                        _vm_uuid = False
                   
                if _vm_uuid and _vm_uuid != _vm_uuid_to_exclude :
                    obj_attr_list["parallel_operations"][_vm_counter] = {}
                    obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] + ' ' + _vm_name + " true"
                    obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _vm_uuid 
                    obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-detach"
                    _vm_counter += 1
                    _vm_command_list += obj_attr_list["cloud_name"] + ' ' + _vm_name + " true" + ', '

            obj_attr_list["destroy_vms"] = _vm_counter

            _msg = "VM detach command list is: " + _vm_command_list
            cbdebug(_msg)

            _status = 0
    
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VM list destruction failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM list destruction success."
                cbdebug(_msg)
                return True

    @trace
    def get_counters(self, cloud_name, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _mon_defaults = self.osci.get_object(cloud_name, "GLOBAL", False, "mon_defaults", False)
            
            _key_list = _mon_defaults["trace_attributes"].split(',')         
            
            for _key in _key_list :
                if _key.count("reservations") or _key.count("arrived") or \
                _key.count("departed") or _key.count("failed") or _key.count("arriving") :
                    _obj_type, _counter_type = _key.upper().split('_')
                    obj_attr_list[_key] = self.get_object_count(cloud_name, _obj_type, _counter_type)

            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
    
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "Counter state collection failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Counter state collection success."
                cbdebug(_msg)
            return _status

    @trace
    def record_management_metrics(self, cloud_name, obj_type, obj_attr_list, operation) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _mon_defaults = self.osci.get_object(cloud_name, "GLOBAL", False, "mon_defaults", False)

            if operation == "trace" :

                _trace_key = "trace_" + _mon_defaults["username"]
                _trace_key_list = _mon_defaults["trace_attributes"].split(',')
                _trace_attr_list = {}
                _trace_attr_list["expid"] = self.expid
                _trace_attr_list["dashboard_polled"] = False
                
                for _key in obj_attr_list.keys() :
                    if _key in _trace_key_list :
                        _trace_attr_list[_key] = obj_attr_list[_key]

                self.msci.add_document(_trace_key, _trace_attr_list)            

                _status = 0

            else :

                _mgt_attr_list = {}
                _mgt_attr_list["expid"] = self.expid 

                if obj_type.upper() == "VM" or obj_type.upper() == "HOST" :

                    _management_key = "management_" + obj_type.upper() + '_' + _mon_defaults["username"]
                    _latest_key = "latest_management_" + obj_type.upper() + '_' + _mon_defaults["username"]

                    _key_list = _mon_defaults[obj_type.lower() + "_attributes"].split(',')

                    for _key in obj_attr_list.keys() :
                        if _key in _key_list or _key.count("mgt"):
                            _mgt_attr_list[_key] = obj_attr_list[_key]

                    _mgt_attr_list["_id"] = obj_attr_list["uuid"]
                    _mgt_attr_list["obj_type"] = obj_type
                    _mgt_attr_list["state"] = self.osci.get_object_state(cloud_name, obj_type, obj_attr_list["uuid"])

                    if operation == "attach" :

                        self.compute_sla(cloud_name, obj_type, obj_attr_list, operation, _mgt_attr_list)

                        if obj_type.upper() == "VM" :

                            _mgt_attr_list["utc_offset_delta"] = \
                            self.compute_utc_offset(cloud_name, obj_type, obj_attr_list)

                        self.msci.add_document(_management_key, _mgt_attr_list)
                        self.msci.add_document(_latest_key, _mgt_attr_list)
                        
                    elif operation == "runstate" :
                        self.msci.update_document(_management_key, _mgt_attr_list)
                        self.msci.update_document(_latest_key, _mgt_attr_list)

                    elif operation == "detach" :

                        _criteria = { "_id" : obj_attr_list["uuid"] }

                        self.msci.update_document(_management_key, _mgt_attr_list)

                        self.msci.delete_document(_latest_key, _criteria)

                        # This was added directly by the VM, but it has to be
                        # deleted by us.
                        self.msci.delete_document("latest_runtime_app_" + obj_type.upper() + '_' + _mon_defaults["username"], _criteria) 

                        # This was added directly by gmetad, but it has to be
                        # deleted by us.
                        self.msci.delete_document("latest_runtime_os_" + obj_type.upper() + '_' + _mon_defaults["username"], _criteria) 

                elif obj_type.upper() == "AI" :

                    _management_key = "management_VM_" + _mon_defaults["username"]
                    _latest_key = "latest_management_VM_" + _mon_defaults["username"]

                    _key_list = _mon_defaults["vm_attributes"].split(',')
                    
                    _vm_list = obj_attr_list["vms"].split(',')

                    if operation == "attach" :
        
                        for _vm in _vm_list :
                            _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                            _vm_attr_list = self.osci.get_object(cloud_name, "VM", False, _vm_uuid, False)

                            _mgt_attr_list["obj_type"] = "VM"
                            for _key in _vm_attr_list.keys() :
                                if _key in _key_list or _key.count("mgt"):
                                    _mgt_attr_list[_key] = _vm_attr_list[_key]
        
                            _mgt_attr_list["_id"] = _vm_uuid
                            _mgt_attr_list["state"] = self.osci.get_object_state(cloud_name, "VM", _vm_attr_list["uuid"])
    
                            _mgt_attr_list["utc_offset_delta"] = \
                            self.compute_utc_offset(cloud_name, "VM", _vm_attr_list)

                            self.compute_sla(cloud_name, "VM", _vm_attr_list, operation, _mgt_attr_list)
                            
                            self.msci.add_document(_management_key, _mgt_attr_list)
                            self.msci.add_document(_latest_key, _mgt_attr_list)
            
                _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.msci.MetricStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :

            if _status :
                _msg = "Management (" + operation + ") metrics record failure: " + _fmsg
                cberr(_msg)
#                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "Management (" + operation + ") metrics record success."
                cbdebug(_msg)
                return True

    @trace
    def compute_utc_offset(self, cloud_name, obj_type, obj_attr_list) :
        '''
        TBD
        '''
        
        if "utc_offset_on_vm" not in obj_attr_list :
            obj_attr_list["utc_offset_on_vm"] = 0

        _utc_offset_delta = int(obj_attr_list["utc_offset_on_orchestrator"]) \
            - int(obj_attr_list["utc_offset_on_vm"])

        self.osci.update_object_attribute(cloud_name, \
                                          obj_type, \
                                          obj_attr_list["uuid"], \
                                          False, \
                                          "utc_offset_delta", \
                                          _utc_offset_delta)

        return _utc_offset_delta

    def compute_sla(self, cloud_name, obj_type, obj_attr_list, operation, mgt_attr_list) :
        '''
        TBD
        '''
        
        _total_provisioning_time = 0
        
        if "sla_provisioning_target" in obj_attr_list :
            for _key in obj_attr_list.keys() :
                if _key.count("mgt") :
                    if _key.count("provisioning") :
                        if not _key.count("originated") and not _key.count("sla") :
                            _total_provisioning_time += int(obj_attr_list[_key])

            if _total_provisioning_time > int(obj_attr_list["sla_provisioning_target"]) :
                _sla_provisioning = "violated"
            else :
                _sla_provisioning = "ok"
    
            self.osci.update_object_attribute(cloud_name, \
                                              obj_type, \
                                              obj_attr_list["uuid"], \
                                              False, \
                                              "sla_provisioning", \
                                              _sla_provisioning)

            obj_attr_list["sla_provisioning"] = _sla_provisioning

            self.osci.add_to_view(cloud_name, obj_type, obj_attr_list, "BYSLA_PROVISIONING", "arrival")

            mgt_attr_list["mgt_sla_provisioning"] = _sla_provisioning

        return True

    @trace
    def get_load(self, cloud_name, obj_attr_list, raw = False, \
                 previous_load = False, previous_duration = False, \
                 previous_load_id = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if raw :
                _status = 0

            else :
                if not previous_load :
                    previous_load = 0
                    
                if not previous_duration :
                    previous_duration = 0
                    
                if not previous_load_id :
                    previous_load_id = 0

                _vg = ValueGeneration(self.pid)
                obj_attr_list["current_load_level"] = int(_vg.get_value(obj_attr_list["load_level"], previous_load))                
                obj_attr_list["current_load_duration"] = int(_vg.get_value(obj_attr_list["load_duration"], previous_duration))
                obj_attr_list["current_load_profile"] = obj_attr_list["load_profile"]
                obj_attr_list["current_load_id"] = int(previous_load_id) + 1

                _msg = "The selected load level for load id " 
                _msg += str(obj_attr_list["current_load_id"]) + "(load profile \""
                _msg += obj_attr_list["current_load_profile"] + "\") was "  
                _msg += str(obj_attr_list["current_load_level"])
                _msg += " and it will be applied to the sut for "
                _msg += str(obj_attr_list["current_load_duration"]) + " seconds."
                cbdebug(_msg)

                _status = 0

        except ValueGeneration.ValueGenerationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Load parameters determination failure: " + _fmsg
                cberr(_msg)
                return False
            else :
                _msg = "Load parameters determination success."
                cbdebug(_msg)
                return True

    @trace
    def get_aidrs_params(self, cloud_name, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _iait_parms = obj_attr_list["iait"]
            _ai_lifetime = obj_attr_list["lifetime"]

            _vg = ValueGeneration(self.pid)
            obj_attr_list["current_inter_arrival_time"] = float((_vg.get_value(_iait_parms)))
            _aidrs_overload = False

            _current_ai_reservations = self.osci.count_object(cloud_name, "AI", "RESERVATIONS")

            _admission_control_limits = self.osci.get_object(cloud_name, "GLOBAL", False, \
                                                             "admission_control", \
                                                             False)

            if int(_current_ai_reservations) >= int(_admission_control_limits["ai_max_reservations"]) :
                _aidrs_overload = 1

            if "nr_ais" in obj_attr_list and int(obj_attr_list["nr_ais"]) >= int(obj_attr_list["max_ais"]) :
                _aidrs_overload = 2
                
            _active = int(self.get_object_count(cloud_name, "AI", "ARRIVING"))
            _active += int(self.get_object_count(cloud_name, "AI", "DEPARTING"))
            
            if _active >= int(obj_attr_list["daemon_parallelism"]) :
                _aidrs_overload = 3

            _msg = "The selected inter-AI arrival time was "
            _msg += str(obj_attr_list["current_inter_arrival_time"] ) + " seconds."
            cbdebug(_msg)            

            if _aidrs_overload :
                _status = _aidrs_overload
            else :             
                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ValueGeneration.ValueGenerationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                if _status == 1 :
                    _msg = "GLOBAL MAX AI RESERVATIONS REACHED"
                elif _status == 2 :
                    _msg = "AIDRS-WIDE MAX AIS REACHED"
                elif _status == 3 :
                    _msg = "GLOBAL DAEMON PARALLELISM REACHED"
                else :
                    _msg = "Parameters for AIDRS determination failure: " + _fmsg
                cberr(_msg)
                # That is right, it is supposed to be "True"
                return True, _msg
            else :
                _msg = "Parameters for AIDRS determination success."
                cbdebug(_msg)
                # That is right, it is supposed to be "False"
                return False, ''

    @trace
    def update_object_attribute(self, cloud_name, obj_type, obj_uuid, \
                                obj_attr, obj_val) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.osci.update_object_attribute(cloud_name, obj_type, obj_uuid, False, \
                                              obj_attr, obj_val)
                
            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = obj_type + " object attribute update failure: " + _fmsg
                cberr(_msg)
                return False
            else :
                _msg = obj_type + " object attribute update success."
                cbdebug(_msg)
                return True
    
    @trace
    def get_object_attribute(self, cloud_name, obj_type, obj_uuid, obj_attr) :
        '''
        TBD
        '''
        try :
            _value = None
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _obj_attr_list = self.osci.get_object(cloud_name, obj_type, False, obj_uuid, False)
            
            if obj_attr in _obj_attr_list :
                _value = _obj_attr_list[obj_attr]
                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = obj_type + " object attribute get failure: " + _fmsg
                cberr(_msg)
                return False
            else :
                _msg = obj_type + " object attribute get success."
                cbdebug(_msg)
                return _value 

    @trace
    def update_process_list(self, cloud_name, obj_type, obj_id, obj_pid, \
                            operation) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _process_identifier = obj_type + '-' + obj_id

            if operation == "add" :
                self.osci.add_to_list(cloud_name, "GLOBAL", "running_processes", _process_identifier)
                _status = 0
            elif operation == "remov" :
                self.osci.remove_from_list(cloud_name, "GLOBAL", "running_processes", _process_identifier)
                _status = 0
            else :
                False

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = obj_type + " object pid \"" + _process_identifier + "\" "
                _msg += operation + "ed to list failure: " + _fmsg
                cberr(_msg)
                return False
            else :
                _msg = obj_type + " object pid \"" + _process_identifier + "\" "
                _msg += operation + "ed to list success "
                cbdebug(_msg)
                return True

    @trace
    def get_object_count(self, cloud_name, obj_type, counter = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not counter :
                _counter_value = str(self.osci.count_object(cloud_name, obj_type))
                _status = 0
            elif counter in [ "RESERVATIONS", "ARRIVED", "DEPARTED", "FAILED" ] :
                _counter_value = str(self.osci.count_object(cloud_name, obj_type, counter))
                _status = 0
            elif counter == "ARRIVING" :
                _counter_value = str(self.get_process_object(cloud_name, obj_type, "attach"))
                _status = 0
            elif counter == "DEPARTING" :
                _counter_value = str(self.get_process_object(cloud_name, obj_type, "detach"))
                _status = 0
            elif counter == "CAPTURING" :
                _counter_value = str(self.get_process_object(cloud_name, obj_type, "capture"))
                _status = 0
            elif counter == "MIGRATING" :
                _counter_value = str(self.get_process_object(cloud_name, obj_type, "migrate"))
                _status = 0
            elif counter == "PROTECTING" :
                _counter_value = str(self.get_process_object(cloud_name, obj_type, "protect"))
                _status = 0
            else :
                _counter_value = str(self.osci.count_object(cloud_name, obj_type, counter))
                _status = 0
                if _counter_value == "None" :
                    _counter_value = str(self.osci.count_object(cloud_name, obj_type, counter.lower()))
                    _status = 0

                if _counter_value == "None" :
                    _status = 1827
                    _fmsg = "Unknown counter type: " + counter

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg =  obj_type + " counter " + str(counter) + " failure: " + _fmsg
                cberr(_msg)
                return "-1"
            else :
                _msg =  obj_type + " counter " + str(counter) + " success."
                cbdebug(_msg)
                return _counter_value

    @trace
    def get_process_object(self, cloud_name, obj_type, operation) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _process_number = 0
            for _process in self.osci.get_list(cloud_name, "GLOBAL", "running_processes") :
                if _process.count(obj_type) and _process.count(operation) :
                    _process_number +=1

            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "List of processes for object "  + obj_type + " failure: " + _fmsg
                cberr(_msg)
                return False
            else :
                _msg = "List of processes for object "  + obj_type + " success."
                cbdebug(_msg)
                return _process_number

    @trace
    def wait_for_port_ready(self, hostname, port, try_once = False) :
        '''
        TBD
        '''
        while True :
            try:
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
                s.bind((hostname, int(port)))
                s.close()
                break
            except socket.error, (value, message) :
                if value == 98 : 
                    cbwarn("Previous port " + str(port) + " taken! ...")
                    if try_once :
                        return False
                    sleep(30)
                    continue
                else :
                    cberr("Could not test port " + str(port) + " liveness: " +  message)
                    raise
        return True

    @trace
    def auto_allocate_port(self, name, obj_attr_list, obj_type, obj_id, address):
        '''
        Generic function for reserving a port on a VM object basis.
        Currently used by: QEMU gdb debugger
        Also used by UI to allocate gnome-terminal and spice ports for in-browser display.
        '''
        throw = False
        _lock = False
        base_name = name + "_port_base"
        max_name = name + "_port_max"
        used_name = name + "_port_used"
        
        if obj_attr_list[name].strip().lower() != "true" :
            return 0, "Not configured"
            
        _status = 100
        _fmsg = "Could not find available port: " + base_name + "/" + max_name
            
        try :
            _lock = self.osci.acquire_lock(obj_attr_list["cloud_name"], obj_type, obj_id, "allocate_port", 1)
            used_ports = self.get_object_attribute(obj_attr_list["cloud_name"], obj_type, obj_id, used_name)
            
            if used_ports and used_ports.strip() != "" :
                used_ports = str2dic(used_ports)
            else :
                used_ports = {}
            _nh_conn = Nethashget(address)
            for _curr_port in range(int(obj_attr_list[base_name]), \
                                    int(obj_attr_list[max_name])) :
                if str(_curr_port) not in used_ports :
                    if not _nh_conn.check_port(_curr_port, "TCP") :
                        used_ports[_curr_port] = obj_attr_list["uuid"]
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], obj_type, obj_id, \
                              False, used_name, dic2str(used_ports), False)
                        obj_attr_list[name + "_port"] = _curr_port
                        _status = 0
                        break
        except Exception, e :
            throw = e 
            
        finally :
            if _lock :
                self.osci.release_lock(obj_attr_list["cloud_name"], obj_type, obj_id, _lock)
            if throw :
                raise throw
            
        return _status, _fmsg
    
    @trace
    def auto_free_port(self, name, obj_attr_list, obj_type, obj_id, address) :
        '''
        TBD
        '''
        throw = False
        _lock = False
        used_name = name + "_used"
        
        if obj_attr_list[name].strip().lower() != "true" :
            return 0, "Not configured"
        
        try :
            _lock = self.osci.acquire_lock(obj_attr_list["cloud_name"], obj_type, obj_id, "allocate_port", 1)
            
            used_ports = self.get_object_attribute(obj_attr_list["cloud_name"], obj_type, obj_id, used_name)
            
            if used_ports :
                used_ports = str2dic(used_ports)
                del used_ports[str(obj_attr_list[name + "_port"])]
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], obj_type, obj_id, \
                                  False, used_name, dic2str(used_ports), False)
        except Exception, e :
            throw = e 
            
        finally :
            if _lock :
                self.osci.release_lock(obj_attr_list["cloud_name"], obj_type, obj_id, _lock)
            if throw :
                raise throw

    @trace
    def compare_refresh(self, cloud_name, last_refresh) :
        _cloud_parameters = self.get_cloud_parameters(cloud_name)
        
        if float(_cloud_parameters["client_should_refresh"]) > float(last_refresh) :
            return True
        
        return False

    @trace
    def update_host_os_perfmon(self, obj_attr_list) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])

            _space_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "space", False)
            _monitor_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "mon_defaults", False)
            _api_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "api_defaults", False)
            _log_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "logstore", False)

            if _monitor_attr_list["collect_from_host"].lower() == "true" :

                _gmetad_config_fc = ""
                _gmetad_config_fc += "xml_port " + _monitor_attr_list["collector_host_aggregator_port"] + '\n'
                _gmetad_config_fc += "interactive_port " + _monitor_attr_list["collector_host_summarizer_port"] + '\n'
                _gmetad_config_fc += "plugins_dir " + _space_attr_list["base_dir"] + '/' + _monitor_attr_list["collector_plugins_dir_suffix"] + '\n'
                _gmetad_config_fc += "data_source \"localhost\" " + _monitor_attr_list["collector_aggregator_host_address"] + ":"  + _monitor_attr_list["collector_host_port"] + '\n'
#               _gmetad_config_fc += "data_source \"" + _monitor_attr_list["hostname"]  + "\" " + _monitor_attr_list["hostname"] + ":"  + _monitor_attr_list["collector_host_port"] + '\n'
#                _hosts = self.osci.get_object_list(obj_attr_list["cloud_name"], "HOST")
#                if _hosts :
#                    for _host_uuid in _hosts :
#                        _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, _host_uuid, False)
#                        _gmetad_config_fc += "data_source \"" + _host_attr_list["cloud_ip"] + "\" " + _host_attr_list["cloud_ip"] + ":"  + _monitor_attr_list["collector_host_port"] + '\n'
                            
                _gmetad_config_fc += "mongodb {\n"
                _gmetad_config_fc += "path " + _space_attr_list["base_dir"] + '\n'
                _gmetad_config_fc += "api http://" + _api_attr_list["hostname"] + ':' + _api_attr_list["port"] + '\n'
                _gmetad_config_fc += "cloud_name " + obj_attr_list["cloud_name"] + '\n'
                _gmetad_config_fc += "}\n"
                
                _gmetad_config_fn = _space_attr_list["base_dir"] + "/" + obj_attr_list["cloud_name"] + "_gmetad-hosts.conf"
                
                _gmetad_config_fd = open(_gmetad_config_fn, 'w')
                _gmetad_config_fd.write(_gmetad_config_fc)
                _gmetad_config_fd.close()

                _proc_man = ProcessManagement(username = _monitor_attr_list["username"], cloud_name = obj_attr_list["cloud_name"])
                _api_pid = _proc_man.get_pid_from_cmdline("gmetad.py")

                if len(_api_pid) :
                    cbdebug("Killing the running Host OS performance monitor (gmetad.py)......")
                    _proc_man.kill_process("gmetad.py")
                
                cbdebug("Starting a new Host OS performance monitor daemon (gmetad.py)......", True)
                _base_cmd = _space_attr_list["base_dir"] + '/' + _monitor_attr_list["collector_executable_path_suffix"]
                _base_cmd += " -c " + _gmetad_config_fn
                _base_cmd += " --cn " + obj_attr_list["cloud_name"]
                _cmd = _base_cmd + " --syslogn " + _log_attr_list["hostname"]
                _cmd += " --syslogp " + _log_attr_list["port"]
                _cmd += " --syslogf " + _log_attr_list["monitor_host_facility"]
                _cmd += " -d 4"
                
                cbdebug(_cmd)

                _gmetad_pid = _proc_man.start_daemon(_cmd)

                if len(_gmetad_pid) :
                    _msg = "Host OS performance monitor daemon (gmetad.py) "
                    _msg += "started successfully. The process id is "
                    _msg += str(_gmetad_pid[0]) + " (using ports "
                    _msg += _monitor_attr_list["collector_host_aggregator_port"]
                    _msg += " and " + _monitor_attr_list["collector_host_summarizer_port"]
                    _msg += ")."
                    cbdebug(_msg, True)
                    _status = 0
                else :
                    _fmsg = "\nHost monitor failed to start. To discover why, please run: \n\n" + \
                            _base_cmd + " -d 5\n\n... and report the results as a bug...\n"

            else :
                _msg = "Attribute \"collect_from_host\" was set to \"false\". "
                _msg += "Skipping Host OS performance monitor daemon startup"
                cbdebug(_msg, True)
                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except ProcessManagement.ProcessManagementException, obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status and _status != 1111:
                _msg = "Host OS performance monitor daemon startup failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "Host OS performance monitor daemon startup success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def package(self, status, msg, result):
        '''
        TBD
        '''
        msg = message_beautifier(msg)
        return status, msg, {"status" : status, "msg" : msg, "result" : result}

    @trace
    def update_cloud_attribute(self, cloud_name , key, value):
        '''
        TBD
        '''
        _cloud_parameters = self.get_cloud_parameters(cloud_name)
        _cloud_parameters[key] = value 
        self.osci.update_cloud(cloud_name, _cloud_parameters)

    @trace
    def background_execute(self, parameters, command) :
        '''
        TBD
        '''
        try :
            _result = {}
            _status = 100
            _smsg = ''
            _fmsg = "unknown error"
            _obj_type, _operation = command.split('-')
            _obj_type = _obj_type.upper()

            # Some small pre-processing is in order. We just need to remove the
            # word "async" from the parameter list
            _p_parameters = parameters.split()
            _parameters = ''
            _parallel_operations = 1
            _inter_spawn_time = False
            for _parameter in _p_parameters :
                if not _parameter.count("async") :
                    _parameters += _parameter + ' '
                else :
                    if _parameter.count('=') :
                        _x, _parallel_operations = _parameter.split('=')
                        if _parameter.count(":") :
                            _parallel_operations, _inter_spawn_time = _parallel_operations.split(':')

                        _msg = "Going to start " + _parallel_operations + " \""
                        _msg += command.replace('-','') + "\" operations in parallel. "

                        if _inter_spawn_time :
                            _msg += "Wait time between each operation is " + _inter_spawn_time + " seconds."
                        print _msg

            _obj_attr_list = {}

            # The parse_cli method is used just to get the cloud name and
            # object name.
            _status, _fmsg = self.parse_cli(_obj_attr_list, _parameters, command)

            if BaseObjectOperations.default_cloud is not None and \
            _parameters.split()[0] != BaseObjectOperations.default_cloud :
                _parameters = BaseObjectOperations.default_cloud + ' ' + _parameters
                _status = 0

            '''
            If any parameter contains a comma (that is the case for "meta_tags"
            and temporary key-value pairs, then "protect" it by converting them
            to some special, very unlikely to be use sequence. We cannot simply
            get rid of the command on meta_tags and temporary key-value pairs, 
            because it is used by the dic2str function to create a dictionary
            later.
            '''
            _parameters = _parameters.replace(',',"+_*")

            '''
            Also protect the ">", used in an AI's sut description (connectivity
            is indicated by "->", since this character has a special meaning for
            the shell interpreter
            '''

            _parameters = _parameters.replace("->","-+-+-+")

            if not _status :
                _cloud_parameters = self.get_cloud_parameters(_obj_attr_list["cloud_name"])
                
                if not command.lower().count("all") and not parameters.count("all") :
                    self.pre_select_object(_obj_attr_list, _obj_type, _cloud_parameters["username"])    
                    
                if "name" in _obj_attr_list and not _obj_attr_list["name"].lower().count(_obj_type.lower() + "_")  \
                    and _obj_type != "HOST" and _obj_type != "VMC" \
                    and (not _obj_attr_list["name"].count("-") == 4) :
                    _obj_attr_list["name"] = _obj_type.lower() + "_" + _obj_attr_list["name"]

                #if not command.count("detachall") :
                #    _parallel_operations = 1
 
                for _op in range(0,int(_parallel_operations)) :

                    if command.count("attach") or command.count("capture") :
                        
                        _obj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0, \
                                                                             1000000000000000000)))).upper()
                        _obj_attr_list["uuid"] = _obj_uuid
        
                        _cmd = self.path + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.osci.oscp())
                        _cmd += " --msp=" + dic2str(self.msci.mscp())
                        _cmd += " --oop=" + ','.join(_parameters.split())
                        _cmd += " --operation=" + command
                        _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                        _cmd += " --uuid=" + _obj_uuid
                        _cmd += " --daemon"
                        #_cmd += "  --debug_host=localhost"
                        
                    elif command.count("detach") and not command.count("detachall") :

                        if parameters.count("all") :
                            _obj_uuid = "ALL"
                        else :
                            _obj_uuid = self.osci.object_exists(_obj_attr_list["cloud_name"], _obj_type, \
                                                                _obj_attr_list["name"], \
                                                                True)
    
                        if not _obj_uuid :
                            _fmsg = "Object " + _obj_attr_list["name"] + " is not instantiated on the object store."
                            _fmsg += "There is no need for explicitly detach it from "
                            _fmsg += "this experiment."
                            _status = 37
    
                        else :
                            _cmd = self.path + "/cbact"
                            _cmd += " --procid=" + self.pid
                            _cmd += " --osp=" + dic2str(self.osci.oscp())
                            _cmd += " --msp=" + dic2str(self.msci.mscp())
                            _cmd += " --oop=" + ','.join(_parameters.split())
                            _cmd += " --operation=" + command
                            _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                            _cmd += " --uuid=" + _obj_uuid
                            _cmd += " --daemon"
                            #_cmd += "  --debug_host=localhost"
    
                    elif command.count("runstate") or \
                    command.count("fail") or command.count("repair") or \
                    command.count("save") or command.count("restore") or \
                    command.count("resize") or command.count("detachall") or \
                    command.count("migrate") or command.count("protect") or \
                    command.count("login") or command.count("display") :
    
                        if _obj_type != "HOST" and ("suspected_command" not in _obj_attr_list or _obj_attr_list["suspected_command"] != "run") :
                            _obj_uuid = self.osci.object_exists(_obj_attr_list["cloud_name"], _obj_type, \
                                                                _obj_attr_list["name"], \
                                                                True)
                        else : 
                            _obj_uuid = _obj_attr_list["name"]
    
                        if not _obj_uuid :
                            _fmsg = "Object " + _obj_attr_list["name"] + " is not instantiated on the object store."
                            _fmsg += "It cannot be used on this experiment."
                            _status = 37
    
                        else :
                            _cmd = self.path + "/cbact"
                            _cmd += " --procid=" + self.pid
                            _cmd += " --osp=" + dic2str(self.osci.oscp())
                            _cmd += " --msp=" + dic2str(self.msci.mscp())
                            _cmd += " --oop=" + ','.join(_parameters.split())
                            _cmd += " --operation=" + command
                            _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                            _cmd += " --uuid=" + _obj_uuid
                            _cmd += " --daemon"
                            #_cmd += "  --debug_host=localhost"
                    else :
                        _msg = "Unknown Operation" + command
                        _status = 100
    
                    if not _status :
                        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
        
                        if _proc_h.pid :
                                _obj_id = _obj_uuid + '-' + _operation
                                self.update_process_list(_obj_attr_list["cloud_name"], _obj_type, \
                                                         _obj_id, \
                                                         str(_proc_h.pid), "add")
                                _smsg += "Operation \"" + command + "\" will be processed "
                                _smsg += "asynchronously, through the command \""
                                _smsg += _cmd + "\". The process id is "
                                _smsg += str(_proc_h.pid) + ".\n"
                                _status = 0
        
                        else :
                            _status = 9
                            _fmsg = "Unable to spawn a new process with the command line \""
                            _fmsg += _cmd + "\". No PID was obtained."

                    if _inter_spawn_time :
                        _msg = command.replace('-','') + ' ' + str(_op + 1) + " dispatched..."
                        cbdebug(_msg, True)
                        if _op < (int(_parallel_operations) - 1) :
                            sleep(int(_inter_spawn_time))               
                            
                    _result = _obj_attr_list
                    
        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Background operation execution failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Background operation execution success. " + _smsg
                cbdebug(_msg)
            return self.package(_status, _msg, _result)