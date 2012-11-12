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
from lib.stores.mongodb_datastore_adapter import MongodbMgdConn
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions, get_startup_commands

from base_operations import BaseObjectOperations
from background_operations import BackgroundObjectOperations
from DocXMLRPCServer import DocXMLRPCServer
from DocXMLRPCServer import DocXMLRPCRequestHandler
from sys import stdout, path
import sys
from lib.auxiliary.cli import CBCLI
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
        
unused_cli = CBCLI(do_nothing = True)
fake_stdout = FakeStdout()

class API():
    @trace
    def __init__(self, pid, passive, active, background) :
        self.passive = passive
        self.active = active
        self.background = background
        self.pid = pid
        self.msattrs = None

        '''
          If there is a "help_*" function available, run it
          and capture the resulting docstring and store it
          in the API's docstring
        '''
        for name, func in inspect.getmembers(self) :
            if func is not None and inspect.isroutine(func) and not name.count("__"):
                fake_stdout.switch()
                try :
                    unused_cli.do_help(func.__name__)
                    func.__func__.__doc__ = fake_stdout.capture_msg 
                    True
                except Exception, obj:
                    pass
                fake_stdout.unswitch()
   
            
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
        attributes = parse_cld_defs_file(self.pid, definitions)
        commands = get_startup_commands(attributes, return_all_options = True)
        return {"msg" : "Success", "status" : 0, "result": commands }
    
    def cldattach(self, model, name, cloud_definitions = None) :
        result = self.active.cldattach({}, model + " " + name, cloud_definitions, "cloud-attach")[2]
        self.passive.osci = self.background.osci = self.active.osci
        if not int(result["status"]) and not self.msattrs:
            msattrs = self.cldshow(name, "metricstore")["result"]
            self.passive.mscp = msattrs 
            self.background.mscp = msattrs
            self.active.mscp = msattrs 
            self.passive.conn_check("MS")
            self.background.conn_check("MS")
            self.active.conn_check("MS")
            self.msattrs = msattrs 
        return result

    def cldlist(self, set_default_cloud = "false"):
        return self.passive.list_objects({}, set_default_cloud, "cloud-list")[2]
    
    def vmlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "vm-list")[2]
    
    def svmlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "svm-list")[2]
    
    def vmclist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "vmc-list")[2]
    
    def hostlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "host-list")[2]
    
    def vmcrslist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "vmcrs-list")[2]
    
    def applist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "ai-list")[2]
    
    def aidrslist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "aidrs-list")[2]
    
    def hostlist(self, cloud_name, state = "default", limit = "none"):
        return self.passive.list_objects({}, cloud_name + " " + state + " " + str(limit), "host-list")[2]
    
    def poollist(self, cloud_name):
        return self.passive.globallist({}, cloud_name + " " + "X+pools+VMCs", "global-list")[2]
                
    def cldshow(self, cloud_name, object = "all") :
        return self.passive.show_object({"name": cloud_name}, cloud_name + " " + object, "cloud-show")[2]
    
    def statealter(self, cloud_name, identifier, new_state):
        return self.passive.alter_state({"name": cloud_name}, cloud_name + " " + identifier + " " + new_state, "state-alter")[2]
    
    def stateshow(self, cloud_name, state = ""):
        return self.passive.show_state({"name": cloud_name}, cloud_name + " " + state, "state-show")[2]
    
    def vmshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "vm-show")[2]
    
    def svmshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "svm-show")[2]
    
    def vmcshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "vmc-show")[2]
    
    def hostshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "host-show")[2]
    
    def appshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "ai-show")[2]
    
    def aidrsshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "aidrs-show")[2]
    
    def vmcrsshow(self, cloud_name, identifier, key = "all"):
        return self.passive.show_object({}, cloud_name + " " + identifier + " " + key, "vmcrs-show")[2]
         
    def reset_refresh(self, cloud_name):
        return self.passive.reset_refresh({}, cloud_name, "api-reset")[2]
    
    def should_refresh(self, cloud_name):
        return self.passive.should_refresh({}, cloud_name, "api-check")[2]
    
    def vmresize(self, cloud_name, identifier, resource, value):
        return self.active.vmresize({}, cloud_name + " " + identifier + " " + resource + "=" + str(value), "vm-resize")[2]
    
    def appresume(self, cloud_name, identifier, async = False):
        return self.apprestore(cloud_name, identifier, async)
    
    def apprestore(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " attached" + (" " + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + " " + identifier + " attached", "ai-runstate")[2]
    
    def appsave(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " save" + (" " + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + " " + identifier + " save", "ai-runstate")[2]
        
    def appsuspend(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " fail" + (" " + async), "ai-runstate")[2]
        else :
            return self.active.airunstate({}, cloud_name + " " + identifier + " fail", "ai-runstate")[2]
    
    def vmrestore(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " attached" + (" " + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + " " + identifier + " attached", "vm-runstate")[2]
    
    def vmsave(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " save" + (" " + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + " " + identifier + " save", "vm-runstate")[2]
    
    def vmresume(self, cloud_name, identifier, async = False):
        return self.vmrestore(cloud_name, identifier, async)
    
    def vmsuspend(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " fail" + (" " + async), "vm-runstate")[2]
        else :
            return self.active.vmrunstate({}, cloud_name + " " + identifier + " fail", "vm-runstate")[2]
        
    def cldalter(self, cloud_name, object, attribute, value):
        return self.passive.alter_object({"name": cloud_name}, cloud_name + " " + object + " " + attribute + "=" + str(value), "cloud-alter")[2]
    
    def appalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + " " + identifier + " " + attribute + "=" + str(value), "ai-alter")[2]
    
    def vmalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + " " + identifier + " " + attribute + "=" + str(value), "vm-alter")[2]
    
    def aidrsalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + " " + identifier + " " + attribute + "=" + str(value), "aidrs-alter")[2]
    
    def vmcalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + " " + identifier + " " + attribute + "=" + str(value), "vmc-alter")[2]
    
    def vmcrsalter(self, cloud_name, identifier, attribute, value):
        return self.passive.alter_object({}, cloud_name + " " + identifier + " " + attribute + "=" + str(value), "vmcrs-alter")[2]
    
    def vmcattach(self, cloud_name, identifier, async = False):
        if async :
            if identifier == "all" :
                return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "vmc-attachall")[2]
            else :
                return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "vmc-attach")[2]
        else :
            if identifier == "all" :
                return self.active.vmcattachall(cloud_name + " " + identifier, "vmc-attachall")[2]
            else :
                return self.active.objattach({}, cloud_name + " " + identifier, "vmc-attach")[2]
    
    def vmcrsattach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "vmcrs-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + " " + identifier, "vmcrs-attach")[2]
    
    def appattach(self, cloud_name, type, load_level = "default", load_duration = "default", lifetime = "none", aidrs = "none", async = False):
        parameters = cloud_name + " " + type + " " + str(load_level) + " " + str(load_duration) + " " + str(lifetime) + " " + aidrs
        if async :
            return self.background.background_execute(parameters + (" " + async), "ai-attach")[2]
        else :
            return self.active.objattach({}, parameters, "ai-attach")[2]
    
    def appinit(self, cloud_name, type, load_level = "default", load_duration = "default", lifetime = "none", aidrs = "none"):
        return self.background.appinit(cloud_name, type, str(load_level), str(load_duration), str(lifetime), aidrs)
    
    def apprun(self, cloud_name, uuid) :
        return self.background.apprun(uuid)
    
    def aidrsattach(self, cloud_name, pattern, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + pattern + (" " + async), "aidrs-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + " " + pattern, "aidrs-attach")[2]

    def vmattach(self, cloud_name, role, vmc_pool = "auto", size = "default", async = False):
        parameters = cloud_name + " " + role + " " + vmc_pool + " " + size
        if async :
            return self.background.background_execute(parameters + (" " + async), "vm-attach")[2]
        else :
            return self.active.objattach({}, parameters, "vm-attach")[2]
        
    def svmattach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "svm-attach")[2]
        else :
            return self.active.objattach({}, cloud_name + " " + identifier, "svm-attach")[2]
    
    def vminit(self, cloud_name, role, vmc_pool = "auto", size = "default"):
        return self.background.vminit(cloud_name, role, vmc_pool, size)
    
    def vmrun(self, cloud_name, uuid):
        return self.background.vmrun(uuid)
    
    def vmdetach(self, cloud_name, identifier, force = False, async = False):
        force = "force" if force else "false"
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " " + force + (" " + async), "vm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier + " " + force, "vm-detach")[2]
    
    def svmdetach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "svm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier, "svm-detach")[2]
        
    def svmfail(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " fail" + (" " + async), "svm-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier + " fail", "svm-detach")[2]
    
    def vmcdetach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "vmc-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier, "vmc-detach")[2]
    
    def vmcrsdetach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "vmcrs-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier, "vmcrs-detach")[2]
    
    def appdetach(self, cloud_name, identifier = "all", force = False, async = False):
        force = "force" if force else "false"
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + " " + force + (" " + async), "ai-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier + " " + force, "ai-detach")[2]
    
    def aidrsdetach(self, cloud_name, identifier, async = False):
        if async :
            return self.background.background_execute(cloud_name + " " + identifier + (" " + async), "aidrs-detach")[2]
        else :
            return self.active.objdetach({}, cloud_name + " " + identifier, "aidrs-detach")[2]
    
    def viewshow(self, cloud_name, object, criterion, expression, sorting = "default", filter = "default"):
        return self.passive.show_view({"name": cloud_name}, cloud_name + " " + object + " " + criterion + " " + expression + " " + sorting + " " + filter, "view-show")[2]
    
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
        self.server.register_instance(self.api)
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
