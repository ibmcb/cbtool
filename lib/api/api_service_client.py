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

    @author: Michael R. Galaxy

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
from xmlrpc.client import Server
import xmlrpc.client
import pwd
import sys
import re
import os
import traceback

path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../")
path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../../")

from lib.stores.stores_initial_setup import load_metricstore_adapter
from time import time, strftime, strptime, localtime
from datetime import datetime
import copy
import socket
import inspect
from threading import Lock

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
        _now = datetime.utcnow()
    else :
        _now = datetime.utcfromtimestamp(supplied_epoch_time)

    _date = _now.date()

    result = ("%02d" % _date.month) + "/" + ("%02d" % _date.day) + "/" + ("%04d" % _date.year)

    result += strftime(" %I:%M:%S %p",
                        strptime(str(_now.hour) + ":" + str(_now.minute) + ":" + \
                                 str(_now.second), "%H:%M:%S"))

    result += " UTC"
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

mutex = Lock()

class APIClient(Server):

    def api_error_check(self, func):
        '''
        TBD
        '''
        def wrapped(*args, **kwargs):
            try :
                mutex.acquire()
                resp = func(*args, **kwargs)
                mutex.release()
            except Exception as e :
                mutex.release()
                for line in traceback.format_exc().splitlines() :
                    print(line)
                raise e
            if int(resp["status"]) :
                raise APIException(str(resp["status"]), resp["msg"])
            if self.print_message :
                print(resp["msg"])
            return resp["result"]
        return wrapped

    def dashboard_conn_check(self, cloud_name, msattrs = None, username = None, experiment_id = None, check_for_vpn = False):
        '''
        TBD
        '''
        if not self.msattrs :
            """
            Open a connection to the metric store
            """
            self.msattrs = self.cldshow(cloud_name, "metricstore") if msattrs is None else msattrs
        # We are opted-out of the VPN by default. But, when inside a virtual machine,
        # we need to opt-in.
        if check_for_vpn :
            use_vpn_ip = str(self.cldshow(cloud_name, "vm_defaults")["use_vpn_ip"]).lower()
            if use_vpn_ip == "true" :
                self.msattrs['host'] = self.cldshow(cloud_name, "vpn")["server_bootstrap"]

        self.msci = load_metricstore_adapter(self.msattrs)
        self.username = self.cldshow(cloud_name, "time")["username"] if username is None else username
        self.experiment_id = self.cldshow(cloud_name, "time")["experiment_id"] if experiment_id is None else experiment_id

    def __init__ (self, service_url, print_message = False):

        '''
         This rewrites the xmlrpc function bindings to use a
         decorator so that we can check the return status of API
         functions before returning them back to the client
         It allows the client object to directly inherit all
         of the API calls exposed on the server side to the
         client side without writing ANOTHER lookup table.
        '''

        _orig_Method = xmlrpc.client._Method

        '''
        XML-RPC doesn't support keyword arguments,
        so we have to do it ourselves...
        '''
        class KeywordArgMethod(_orig_Method):
            def __call__(self, *args, **kwargs):
                args = list(args)
                if kwargs:
                    args.append(("kwargs", kwargs))
                return _orig_Method.__call__(self, *args)

        xmlrpc.client._Method = KeywordArgMethod

        Server.__init__(self, service_url)

        setattr(self, "_ServerProxy__request", self.api_error_check(self._ServerProxy__request))
        self.vms = {}
        self.hosts = {}
        self.msattrs = None
        self.msci = None
        self.username = None
        self.print_message = print_message
        self.last_refresh = datetime.now()

    def check_for_new_vm(self, cloud_name, identifier):
        '''
        TBD
        '''
        info = self.vmshow(cloud_name, identifier)
        print(identifier + " configured: (" + info["vcpus"] + ", " + info["vmemory"] + ")")

        if "configured_size" in info :
            print("   Eclipsed size: (" + info["vcpus_max"] + ", " + info["vmemory_max"] + ")")

        if info["ai"] != "none" :
            app = self.appshow(cloud_name, info["ai_name"])
        else :
            app = None

        return APIVM(identifier, info, app)

    def refresh_vms(self, cloud_name, force, state = "") :
        '''
        TBD
        '''
        try :
            self.experiment_id = self.cldshow(cloud_name, "time")["experiment_id"]

            if not force :
                if not self.should_refresh(cloud_name, str(self.last_refresh)) :
                    #print "VM list unchanged (" + str(len(self.vms)) + " vms) ..."
                    return False

            self.last_refresh = time()

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

        except APIException as obj :
            print("Check VM API Problem (" + str(obj.status) + "): " + obj.msg)
            return False

        except socket.error as obj :
            print("API not available: " + str(obj))
            return False

    def get_performance_data(self, cloud_name, uuid, metric_class = "runtime", object_type = "VM", metric_type = "os", latest = False, samples = 0, expid = "auto") :
        '''
        TBD
        '''
        self.dashboard_conn_check(cloud_name)

        if str(uuid).lower() == "all" :
            uuid = None

        if metric_class == "runtime" :
            _object_type = metric_class + '_' + metric_type + '_' + object_type
        else :
            _object_type = metric_class + '_' + object_type

        if latest :
            _allmatches = True
            _collection_name = "latest_" + _object_type + "_" + self.username
            _limitdocuments = 0
        else :
            if samples != 0 :
                _allmatches = False
                _limitdocuments = samples
            else :
                _allmatches = True
                _limitdocuments = 0

            _collection_name = _object_type + "_" + self.username

        _criteria = {}

        if expid != "auto" :
            _criteria["expid"] = expid

        if uuid :
            _criteria["uuid"] = uuid

        metrics = self.msci.find_document(_collection_name, \
                                          _criteria, \
                                          limitdocuments = _limitdocuments, \
                                          allmatches = _allmatches)

        if isinstance(metrics, dict) :
            _metrics = []
            _metrics.append(metrics)
            metrics = _metrics

#        if uuid and metrics :
#            if metrics :
#                if "count" in dir(metrics) :
#                    _samples = metrics.count()
#
#                    if _samples == 0 :
#                        metrics = None

#                    if _samples == 1 :
#                        _metrics = []
#                        _metrics.append(metrics)
#                        metrics = _metrics

        if metrics is None :
            _msg = "No " + metric_class + ' ' + _object_type + '(' + str(metric_type) + ") data available."
#            raise APINoSuchMetricException(1, _msg")

        return metrics

    def get_latest_app_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "runtime", "VM", "app", True, 0, expid)
        if uuid in self.vms :
            self.vms[uuid].app_metrics = _metrics

        return _metrics

    def get_latest_system_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "runtime", "VM", "os", True, 0, expid)
        if uuid in self.vms :
            self.vms[uuid].system_metrics = _metrics

        return _metrics

    def get_latest_management_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "management", "VM", "os", True, 0, expid)

        return _metrics

    def get_app_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "runtime", "VM", "app", False, 0, expid)
        if uuid in self.vms :
            self.vms[uuid].app_metrics = _metrics

        return _metrics

    def get_system_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "runtime", "VM", "os", False, 0, expid)
        if uuid in self.vms :
            self.vms[uuid].system_metrics = _metrics

        return _metrics

    def get_management_data(self, cloud_name, uuid, expid = "auto") :
        '''
        TBD
        '''
        _metrics = self.get_performance_data(cloud_name, uuid, "management", "VM", "os", False, 0, expid)

        return _metrics
