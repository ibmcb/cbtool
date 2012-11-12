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
    API Service XML-RPC Relay

    @author: Michael R. Hines

    This is the "library" of the API.

    It works by extending the native XML-RPC function calls
    into abstractions that make sense from a cloud and
    application perspective just as, say, Amazon or OpenStack
    would do. 

    So, you create a APIClient() object and then
    perform calls on that object that get send across
    to perform various operations.
'''

from sys import path
from xmlrpclib import Server
import sys
import re
import os

path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../")
path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../../")

from lib.stores.mongodb_datastore_adapter import MongodbMgdConn
from time import time, strftime, strptime, localtime
from datetime import datetime
import copy
import socket
import inspect

class APIException(Exception) :
    def __init__(self, status, msg):
        Exception.__init__(self)
        self.msg = msg
        self.status = str(status)
    def __str__(self):
        return self.msg
        
class APINoSuchMetricException(Exception) :
    def __init__(self, status, msg):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg
        
class APINoDataException(Exception) :
    def __init__(self, status, msg):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg
        
def makeTimestamp(supplied_epoch_time = False) :
    '''
    TBD
    '''
    if not supplied_epoch_time :
        _now = datetime.now()
    else :
        _now = datetime.fromtimestamp(supplied_epoch_time)
        
    _date = _now.date()

    result = ("%02d" % _date.month) + "/" + ("%02d" % _date.day) + "/" + ("%04d" % _date.year)
        
    result += strftime(" %I:%M:%S %p", 
                        strptime(str(_now.hour) + ":" + str(_now.minute) + ":" + \
                                 str(_now.second), "%H:%M:%S"))
        
    result += strftime(" %Z", localtime(time())) 
    return result

class APIVM():
    def __init__(self, name, info, app):
        self.name = name
        self.role = info["role"]
        self.uuid = info["uuid"]
        self.app_metrics = None
        self.system_metrics = None
        self.info = info 
        self.app = app 
        self.started = int(info["arrival"])
        self.vcpus = info["vcpus"]
        self.vmemory = info["vmemory"]
        self.new = True
        makeTimestamp()
        
    def val(self, key, dict):
        if dict is None :
            raise APINoSuchMetricException(1, "No data available.")
        
        if key in dict :
            return dict[key]
        else :
            raise APINoSuchMetricException(1, "No such metric: " + key)
        
    def app(self, key):
        return float(self.val(key, self.app_metrics)["val"])
    
    def system(self, key):
        return float(self.val(key, self.system_metrics)["val"])
    
class APIClient(Server):
    def api_error_check(self, func):
        def wrapped(*args, **kwargs):
            if self.server_msci_initialized == False:
                self.server_msci_initialized = None
                try :
                    clouds = self.cldlist()
                except Exception, e :
                    self.server_msci_initialized = False 
                    raise APIException("124", str(e))
                    
                if len(clouds) > 0 :
                    print "Initializing remote mongo connection..."
                    try :
                        # This attach is a no-op
                        # Just used to initialize the mongodb connection
                        # On the server side
                        self.cldattach(clouds[0]["model"], clouds[0]["name"])
                    except Exception, e :
                        self.server_msci_initialized = False 
                        raise APIException("123", str(e))
                    self.server_msci_initialized = True
                else :
                    self.server_msci_initialized = False 
                
            resp = func(*args, **kwargs)
            if int(resp["status"]) :
                raise APIException(str(resp["status"]), resp["msg"])
            return resp["result"]
        return wrapped
    
    def dashboard_conn_check(self, cloud_name, msattrs = None, username = None):
        if not self.msattrs :
            """
            Open a connection to the metric store
            """
            self.msattrs = self.cldshow(cloud_name, "metricstore") if msattrs is None else msattrs
            self.msci = MongodbMgdConn ("elasticity", self.msattrs["hostname"], int(self.msattrs["port"]), self.msattrs["database"], float(self.msattrs["timeout"]), "unused")
            self.username = self.cldshow(cloud_name, "time")["username"] if username is None else username

    def __init__ (self, service_url):
        
        '''
         This rewrites the xmlrpc function bindings to use a
         decorator so that we can check the return status of API
         functions before returning them back to the client
         It allows the client object to directly inherit all
         of the API calls exposed on the server side to the
         client side without writing ANOTHER lookup table.
        '''
        
        Server.__init__(self, service_url)
        setattr(self, "_ServerProxy__request", self.api_error_check(self._ServerProxy__request))
        
        self.vms = {}
        self.msattrs = None
        self.msci = None
        self.username = None
        self.server_msci_initialized = False
        
    def check_for_new_vm(self, cloud_name, identifier):
        info = self.vmshow(cloud_name, identifier)
        print identifier + " configured: (" + info["vcpus"] + ", " + info["vmemory"] + ")" 
            
        if "configured_size" in info :
            print "   Eclipsed size: (" + info["vcpus_max"] + ", " + info["vmemory_max"] + ")"
            
        if info["ai"] != "none" :
            app = self.appshow(cloud_name, info["ai_name"])
        else :
            app = None
            
        return APIVM(name, info, app)
    
    def refresh_vms(self, cloud_name, force, state = "") :
        try :
            self.expid = self.cldshow(cloud_name, "time")["experiment_id"]

            if not force :
                if not self.should_refresh(cloud_name) : 
                    #print "VM list unchanged (" + str(len(self.vms)) + " vms) ..."
                    return False
                
            old_vms = copy.copy(self.vms)
            
            for obj in self.stateshow(cloud_name, state) :
                if obj["type"] != "AI" :
                    continue

                sibling_uuids = []
                for vm in self.appshow(cloud_name, obj["name"])["vms"].split(",") :
                    uuid, role, name = vm.split("|") 

                    if uuid not in self.vms :
                        self.vms[uuid] = self.check_for_new_vm(name)
                        sibling_uuids.append(uuid)

                    if uuid in old_vms : 
                        del old_vms[uuid]

                for me in sibling_uuids :
                    myself = self.vms[me]
                    myself.siblings = []
                    for sibling in sibling_uuids :
                        if sibling != myself :
                            sib = self.vms[sibling]
                            myself.siblings.append(sib)
                            if sib.role.count("client") :
                                myself.client = sib
                    
            for uuid in old_vms :
                del self.vms[uuid] 
        
            self.reset_refresh(cloud_name)
            return True
        except APIException, obj :
            print "Check VM API Problem (" + str(obj.status) + "): " + obj.msg
            return False
        except socket.error, obj :
            print "API not available: " + str(obj)
            return False
        
    def get_latest_data(self, cloud_name, uuid, type):
        self.dashboard_conn_check(cloud_name)
        metrics = self.msci.find_document("latest_" + type + "_" + self.username, {"uuid" : uuid})
        
        if metrics is None :
            raise APINoSuchMetricException(1, "No " + type + " data available.")
        
        return metrics
    
    def get_latest_app_data(self, uuid):
        self.vms[uuid].app_metrics = self.get_latest_data(uuid, "runtime_app_VM") 
        
    def get_latest_system_data(self, uuid):
        self.vms[uuid].system_metrics = self.get_latest_data(uuid, "runtime_os_VM") 
