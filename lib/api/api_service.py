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
    API Service RPC Relay
    @author: Michael R. Hines
'''
from os import chmod, makedirs
from sys import path
from os.path import isdir
from time import asctime, localtime, sleep, time
from fileinput import FileInput

from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.auxiliary.code_instrumentation import trace, cblog, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.value_generation import ValueGeneration
from lib.auxiliary.data_ops import dic2str, makeTimestamp
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions, get_available_clouds
from lib.operations.base_operations import BaseObjectOperations
from lib.operations.background_operations import BackgroundObjectOperations

from DocXMLRPCServer import DocXMLRPCServer
from DocXMLRPCServer import DocXMLRPCRequestHandler
from sys import stdout, path
import sys
from functools import wraps
import inspect
import threading
import SocketServer
 
"""
    This class is used to avoid Double-Documentation
    It captures the standard output of a function to be
    used later in a pydoc __doc__ docstring.
"""
class FakeStdout():
    def switch(self):
        self.old_stdout = sys.stdout
        sys.stdout = self
        self.capture_msg = ""
    def unswitch(self):
        sys.stdout = self.old_stdout
        
    def flush(self):
        self.old_stdout.flush()
        
    def write(self, msg):
        self.capture_msg += msg
        
fake_stdout = FakeStdout()

def unwrap_kwargs(func, spec):
    def wrapper(*args, **kwargs):
        if args and isinstance(args[-1], list) and len(args[-1]) == 2 and "kwargs" == args[-1][0]:
            return func(*args[:-1], **args[-1][1])
        else:
            return func(*args, **kwargs)
        
    wrapper.__doc__ = str(spec)
    if func.__doc__ is not None :
        wrapper.__doc__ +=  "\n\n" + func.__doc__
    return wrapper

class API():
    @trace
    def __init__(self, pid, passive, active, background) :
        self.passive = passive
        self.active = active
        self.background = background
        self.pid = pid

        from lib.auxiliary.cli import help 
        '''
          If there is a "help_*" function available, run it
          and capture the resulting docstring and store it
          in the API's docstring
        '''
        for name, func in inspect.getmembers(self) :
            if func is not None and inspect.isroutine(func) and not name.count("__"):
                fake_stdout.switch()
                try :
                    if help(func.__name__) :
                        func.__func__.__doc__ = fake_stdout.capture_msg 
                except Exception, obj:
                    pass
                fake_stdout.unswitch()
    @trace
    def success(self, msg, result) :
        cbdebug(msg)
        return {"status" : 0, "msg" : msg, "result" : result }

    @trace
    def error(self, status, msg, result) :
        cberr(msg)
        return {"status" : status, "msg" : msg, "result" : result }
    
    @trace
    def get_functions(self):
        '''
        List the names of all the available API functions
        '''
        return self.success("success", self.signatures)
    
    @trace
    def get_signature(self, name):
        '''
        Get the list of arguments of a specific API function
        '''
        return self.success("signature", self.signatures[name])
    
   
            
    '''
        This simple command table tries to preserve the best of both worlds.
        We make direct calls into lib/operations without having to have an
        extensive lookup table.
    
        It's important not to perform any exception handling here, or the
        lookup table would be overly complicated.
    
        Furthermore, we make sure each lib/operations function that we are
        interested in exposing returns the appropriate result and ignore
        the formatted output result.
        
        The client-side of the API will do the appropriate error checking
        and will propogate exceptions properly across the API boundary
        to the client code.
    '''

            
    def cldparse(self, definitions):
        attributes, unused_definitions = parse_cld_defs_file(definitions)
        clouds = get_available_clouds(attributes, return_all_options = True)
        return {"msg" : "Success", "status" : 0, "result": { "clouds": clouds, "attributes" : attributes} }

    def cldattach(self, model, name, cloud_definitions = None, temp_attr_list = "empty=empty", uni_attrs = None) :
        return self.active.cldattach({}, model + ' ' + name + ' ' + temp_attr_list, cloud_definitions, "cloud-attach", uni_attrs)[2]
    
    def clddetach(self, name) :
        return self.active.clddetach({}, name, "cloud-detach")[2]

    def cldlist(self, set_default_cloud = "false"):
        return self.passive.list_objects({}, set_default_cloud, "cloud-list")[2]

    def expid(self, cloud_name, experiment_name = ''):
        return self.passive.expid({"name" : cloud_name}, cloud_name + ' ' + experiment_name, "expid-manage")[2]

    def vmlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "vm-list")[2]

    def svmlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "svm-list")[2]

    def vmclist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "vmc-list")[2]

    def hostlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "host-list")[2]

    def vmcrslist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "vmcrs-list")[2]

    def firslist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "firs-list")[2]

    def applist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "ai-list")[2]

    def appdrslist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + ' ' + state + ' ' + str(limit), "aidrs-list")[2]

    def poollist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + ' ' + "X+pools+VMCs", "global-list")[2]

    def cldshow(self, cloud_name, object_type) :
        return self.passive.show_object({"name": cloud_name}, cloud_name + ' ' + object_type, "cloud-show")[2]

    def statealter(self, cloud_name, identifier, new_state):
        return self.passive.alter_state({"name": cloud_name}, cloud_name + ' ' + identifier + ' ' + new_state, "state-alter")[2]

    def stateshow(self, cloud_name, state = ""):
        return self.passive.show_state({"name": cloud_name}, cloud_name + ' ' + state, "state-show")[2]

    def typeshow(self, cloud_name, vapp_type) :
        return self.passive.globalshow({}, cloud_name + ' ' + vapp_type + " ai_templates type", "global-show")[2]

    def patternshow(self, cloud_name, pattern) :
        return self.passive.globalshow({}, cloud_name + ' ' + pattern + " aidrs_templates pattern", "global-show")[2]

    def patternalter(self, cloud_name, pattern_name, attribute, value):
        return self.passive.globalalter({}, cloud_name + ' ' + pattern_name + ' ' + attribute + "=" + value + " aidrs_templates pattern", "global-alter")[2]

    def typealter(self, cloud_name, type_name, attribute, value):
        return self.passive.globalalter({}, cloud_name + ' ' + type_name + ' ' + attribute + "=" + value + " ai_templates type", "global-alter")[2]

    def roleshow(self, cloud_name, role) :
        return self.passive.globalshow({}, cloud_name + ' ' + role + " vm_templates role", "global-show")[2]

    def rolealter(self, cloud_name, role_name, attribute, value):
        return self.passive.globalalter({}, cloud_name + ' ' + role_name + ' ' + attribute + "=" + value + " vm_templates role", "global-alter")[2]
    
    def vmshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "vm-show")[2]
    
    def svmshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "svm-show")[2]
    
    def vmcshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "vmc-show")[2]
    
    def hostshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "host-show")[2]
    
    def appshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "ai-show")[2]
    
    def appdrsshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "aidrs-show")[2]
    
    def vmcrsshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "vmcrs-show")[2]

    def firsshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + ' ' + identifier + ' ' + key, "firs-show")[2]

    def reset_refresh(self, cloud_name):
        return self.passive.reset_refresh({}, cloud_name, "api-reset")[2]
    
    def should_refresh(self, cloud_name):
        return self.passive.should_refresh({}, cloud_name, "api-check")[2]
    
    def vmresize(self, cloud_name, identifier, resource, value):
        return self.active.vmresize({}, cloud_name + ' ' + identifier + ' ' + resource + "=" + str(value), "vm-resize")[2]
    
    def appresume(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " attached resume" + ' ' + firs + (' ' + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + ' ' + identifier + " attached resume" + ' ' + firs, "ai-runstate")[2]

    def apprestore(self, cloud_name, identifier, async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " attached restore" + (' ' + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + ' ' + identifier + " attached restore", "ai-runstate")[2]
        
    def appcapture(self, cloud_name, identifier, vmcrs = "none",  async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + vmcrs + (' ' + async), "ai-capture")[2]
        else :
            return self.active.aicapture({}, cloud_name + ' ' + identifier + ' ' + vmcrs, "ai-capture")[2]
        
    def vmcapture(self, cloud_name, identifier, vmcrs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + vmcrs + (' ' + async), "vm-capture")[2]
        else :
            return self.active.vmcapture({}, cloud_name + ' ' + identifier + ' ' + vmcrs, "vm-capture")[2]
        
    def migrate(self, cloud_name, identifier, destination, protocol = "tcp", interface = "default", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + destination + ' ' + protocol + ' ' + interface + (' ' + async), "vm-migrate")[2]
        else :
            return self.active.migrate({}, cloud_name + ' ' + identifier + ' ' + destination + ' ' + protocol + ' ' + interface, "vm-migrate")[2]
        
    def hostfail(self, cloud_name, identifier, firs = "none", async = False):
        parameters = cloud_name + ' ' + identifier + ' ' + firs
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "host-fail")[2]
        else :
            return self.active.hostfail_repair({}, parameters, "host-fail")[2]
        
    def hostrepair(self, cloud_name, identifier, async = False):
        parameters = cloud_name + ' ' + identifier
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "host-repair")[2]
        else :
            return self.active.hostfail_repair({}, parameters, "host-repair")[2]
        
    def appresize(self, cloud_name, identifier, role, delta, async = False):
        parameters = cloud_name + ' ' + identifier + ' ' + role + ' ' + delta
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "ai-resize")[2]
        else :
            return self.active.airesize({}, parameters, "ai-resize")[2]
    
    def appsave(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " save" + ' ' + firs + (' ' + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + ' ' + identifier + " save" + ' ' + firs, "ai-runstate")[2]
        
    def vmrunstate(self, cloud_name, identifier, runstate, command = "unknown", firs = "none", async = False):
        parameters = cloud_name + ' ' + identifier + ' ' + runstate + ' ' + command + ' ' + firs
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, parameters, "vm-runstate")[2]

    def apprunstate(self, cloud_name, identifier, runstate, command = "unknown", firs = "none", async = False):
        parameters = cloud_name + ' ' + identifier + ' ' + runstate + ' ' + command + ' ' + firs
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, parameters, "ai-runstate")[2]
        
    def appfail(self, cloud_name, identifier, firs = "none", async = False):
        return self.appsuspend(cloud_name, identifier, firs, async)
    
    def apprepair(self, cloud_name, identifier, firs = "none", async = False):
        return self.appresume(cloud_name, identifier, firs, async)
    
    def appsuspend(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " fail" + ' ' + firs + (' ' + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + ' ' + identifier + " fail" + ' ' + firs, "ai-runstate")[2]
    
    def vmrestore(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " attached restore" + ' ' + firs (' ' + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + ' ' + identifier + " attached restore" + ' ' + firs, "vm-runstate")[2]
    
    def vmsave(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " save" + ' ' + firs + (' ' + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + ' ' + identifier + " save" + ' ' + firs, "vm-runstate")[2]
    
    def vmresume(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " attached resume" + ' ' + firs +(' ' + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + ' ' + identifier + " attached resume" + ' ' + firs, "vm-runstate")[2]
        
    def vmfail(self, cloud_name, identifier, firs = "none", async = False):
        return self.vmsuspend(cloud_name, identifier, firs, async)
    
    def vmrepair(self, cloud_name, identifier, firs = "none", async = False):
        return self.vmresume(cloud_name, identifier, firs, async)
    
    def vmsuspend(self, cloud_name, identifier, firs = "none", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " fail" + ' ' + firs + (' ' + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + ' ' + identifier + " fail" + ' ' + firs, "vm-runstate")[2]
        
    def cldalter(self, cloud_name, object, attribute, value):
        return self.passive.alter_object({"name": cloud_name}, cloud_name + ' ' + object + ' ' + attribute + "=" + str(value), "cloud-alter")[2]
    
    def appalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "ai-alter")[2]
    
    def vmalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "vm-alter")[2]
    
    def appdrsalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "aidrs-alter")[2]
    
    def vmcalter(self, cloud_name, identifier, attribute, value) :
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "vmc-alter")[2]
    
    def vmcrsalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "vmcrs-alter")[2]

    def firsalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + ' ' + identifier + ' ' + attribute + "=" + str(value), "firs-alter")[2]
    
    def vmcattach(self, cloud_name, identifier, temp_attr_list = "empty=empty", async = False) :
        if async and str(async).count("async") :
            if identifier == "all" :
                return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + temp_attr_list + (' ' + async), "vmc-attachall")[2]
            else :
                return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + temp_attr_list + (' ' + async), "vmc-attach")[2]
        else :
            if identifier == "all" :
                return self.active.vmcattachall({}, cloud_name + ' ' + identifier + ' ' + temp_attr_list, "vmc-attachall")[2]
            else :
                return self.active.objattach({}, cloud_name + ' ' + identifier + ' ' + temp_attr_list, "vmc-attach")[2]
    
    def vmcrsattach(self, cloud_name, identifier, scope = '', max_simultaneous_cap_reqs = '', max_total_cap_reqs = '', ivmcat = '', min_cap_age = '', temp_attr_list = "empty=empty", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + scope + ' ' + max_simultaneous_cap_reqs + ' ' +  max_total_cap_reqs + ' ' + ivmcat + ' ' + min_cap_age + ' ' + temp_attr_list + (' ' + async), "vmcrs-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + ' ' + identifier + ' ' + scope + ' ' + max_simultaneous_cap_reqs + ' ' + max_total_cap_reqs + ' ' + ivmcat + ' ' + min_cap_age + ' ' + temp_attr_list, "vmcrs-attach")[2]

    def firsattach(self, cloud_name, identifier, scope = '', max_simultaenous_faults = '', max_total_faults = '', ifat = '', min_fault_age = '', ftl = '', temp_attr_list = "empty=empty", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + scope + ' ' + max_simultaenous_faults + ' ' + max_total_faults + ' ' + ifat + ' ' + min_fault_age + ' ' + ftl + ' ' + temp_attr_list + (' ' + async), "firs-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + ' ' + identifier + ' ' + scope + ' ' + max_simultaenous_faults + ' ' + max_total_faults + ' ' + ifat + ' ' + min_fault_age + ' ' + ftl + ' ' + temp_attr_list, "firs-attach")[2]
    
    def appattach(self, cloud_name, type, load_level = "default", load_duration = "default", lifetime = "none", aidrs = "none", pause_step = "none", temp_attr_list = "empty=empty", async = False):
        parameters = cloud_name + ' ' + type + ' ' + str(load_level) + ' ' + str(load_duration) + ' ' + str(lifetime) + ' ' + aidrs + ' ' + pause_step + ' ' + temp_attr_list
        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "ai-attach")[2]
        else :
            return self.active.objattach({}, parameters, "ai-attach")[2]
    
    def appinit(self, cloud_name, type, load_level = "default", load_duration = "default", lifetime = "none", aidrs = "none", pause_step = "prepare_provision_complete"):
        return self.appattach(cloud_name, type, str(load_level), str(load_duration), str(lifetime), aidrs, pause_step)
    
    def apprun(self, cloud_name, uuid) :
        return self.apprunstate(cloud_name, uuid, "attached", "run")
    
    def appdrsattach(self, cloud_name, pattern, temp_attr_list = "empty=empty", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + pattern + ' ' + temp_attr_list + (' ' + async), "aidrs-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + ' ' + pattern + ' ' + temp_attr_list, "aidrs-attach")[2]

    def vmattach(self, cloud_name, role, vm_location = "auto", meta_tags = "empty", size = "default", pause_step = "none", temp_attr_list = "empty=empty", async = False):
        parameters = cloud_name + ' ' + role + ' ' + vm_location + ' ' + meta_tags + ' ' + size + ' ' + pause_step + ' ' + temp_attr_list

        if async and str(async).count("async") :
            return self.active.background_execute(parameters + (' ' + async), "vm-attach")[2]
        else :
            return self.active.objattach({}, parameters, "vm-attach")[2]
        
    def svmattach(self, cloud_name, identifier, temp_attr_list = "empty=empty", async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + temp_attr_list + (' ' + async), "svm-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + ' ' + identifier + ' ' + temp_attr_list, "svm-attach")[2]
    
    def vminit(self, cloud_name, role, vmc_pool = "auto", size = "default", pause_step = "prepare_provision_complete"):
        return self.vmattach(cloud_name, role, vmc_pool, size, pause_step)
    
    def vmrun(self, cloud_name, uuid):
        return self.vmrunstate(cloud_name, uuid, "attached", "run")
    
    def vmdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "vm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "vm-detach")[2]
    
    def svmdetach(self, cloud_name, identifier, force = False, async = False):
        '''
        force not currently used here...
        '''
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + (' ' + async), "svm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier, "svm-detach")[2]
        
    def svmfail(self, cloud_name, identifier, async = False):
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + " fail" + (' ' + async), "svm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + " fail", "svm-detach")[2]
    
    def vmcdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "vmc-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "vmc-detach")[2]
        
    def vmccleanup(self, cloud_name, identifier) :
        return self.active.vmccleanup({}, cloud_name + ' ' + identifier, "vmc-cleanup")[2]
    
    def vmcrsdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "vmcrs-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "vmcrs-detach")[2]

    def firsdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "firs-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "vmcrs-detach")[2]
    
    def appdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "ai-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "ai-detach")[2]
    
    def appdrsdetach(self, cloud_name, identifier, force = False, async = False):
        force = str(force).lower() if force else "false"
        if async and str(async).count("async") :
            return self.active.background_execute(cloud_name + ' ' + identifier + ' ' + force + (' ' + async), "aidrs-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + ' ' + identifier + ' ' + force, "aidrs-detach")[2]
    
    def viewshow(self, cloud_name, object, criterion, expression, sorting = "default", filter = "default"):
        return self.passive.show_view({"name": cloud_name}, cloud_name + ' ' + object + ' ' + criterion + ' ' + expression + ' ' + sorting + ' ' + filter, "view-show")[2]
    
    def monlist(self, cloud_name, object_type):
        result = self.passive.monitoring_list(cloud_name + ' ' + object_type, "mon-list")[2]
        return result
    
    def waitfor(self, cloud_name, time, update_interval = "default"):
        return self.passive.wait_for({}, cloud_name + ' ' + time + ' ' + str(update_interval), "wait-for")[2]
    
    def stats(self, cloud_name):
        return self.passive.stats({"name": cloud_name}, cloud_name, "stats-get")[2]
    
    def typelist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + " ai_templates+types+AIs", "global-list")[2]
    
    def rolelist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + " vm_templates+roles+VMs", "global-list")[2]
    
    def patternlist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + " aidrs_templates+patterns+AIDRSs", "global-list" )[2]
    
    def viewlist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + " query+criteria+VIEWs", "global-list")[2]
    
class AsyncDocXMLRPCServer(SocketServer.ThreadingMixIn,DocXMLRPCServer): pass

class APIService ( threading.Thread ):
    
    @trace
    def __init__(self, pid, passive, active, background, debug, port, hostname) :
        super(APIService, self).__init__()
        self._stop = threading.Event()
        self.pid = pid
        self.abort = False
        self.aborted = False
        self.port = port 
        self.hostname = hostname 
        self.api = API(pid, passive, active, background)
        cbdebug("Initializing API Service on port " + str(self.port))
        if debug is None :
            self.server = AsyncDocXMLRPCServer((self.hostname, int(self.port)), allow_none = True)
        else :
            self.server = DocXMLRPCServer((self.hostname, int(self.port)), allow_none = True)
        self.server.abort = False
        self.server.aborted = False
        self.server.set_server_title("API Service (xmlrpc)")
        self.server.set_server_name("API Service (xmlrpc)")
        #self.server.register_introspection_functions()
        self.api.signatures = {}
        for methodtuple in inspect.getmembers(self.api, predicate=inspect.ismethod) :
            name = methodtuple[0]
            if name in ["__init__", "success", "error" ] :
                continue
            func = getattr(self.api, name)
            argspec = inspect.getargspec(func) 
            spec = argspec[0]
            defaults = [] if argspec[3] is None else argspec[3]
            num_spec = len(spec)
            num_defaults = len(defaults)
            diff = num_spec - num_defaults
            named = diff - 1
            doc = "Usage: "
            for x in range(1, diff) :
                doc += spec[x] + ", "
            for x in range(diff, num_spec) :
                doc += spec[x] + " = " + str(defaults[x - diff]) + ", "
            doc = doc[:-2]
            self.api.signatures[name] = {"args" : spec[1:], "named" : named }
            self.server.register_function(unwrap_kwargs(func, doc), name)
#        self.server.register_instance(self.api)
        cbdebug("API Service started")

    @trace
    def run(self):
        cbdebug("API Service waiting for requests...")
        self.server.serve_forever()
        cbdebug("API Service shutting down...")
        
    @trace
    def stop (self) :
        cbdebug("Calling API Service shutdown....")
        self._stop.set()
        self.server.shutdown()
