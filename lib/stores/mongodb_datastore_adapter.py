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
    Created on Mar 21, 2012

    MongoDB data management operations library

    @author: Marcio A. Silva
'''

import os
import pymongo

from time import sleep, time
from random import randint
from pwd import getpwuid
from lib.auxiliary.config import get_my_parameters, set_my_parameters 

from pymongo import Connection
from pymongo import errors as PymongoException

def print_standalone(str) :
    print str

def trace_nothing(aFunc):
    return aFunc

try :
    from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
except :
    cbdebug = print_standalone
    cberr = print_standalone
    cbwarn = print_standalone
    cbinfo = print_standalone
    cbcrit = print_standalone
    trace = trace_nothing

class MongodbMgdConn :
    '''
    TBD
    '''

    @trace
    def __init__(self, parameters) :
        '''
        TBD
        '''
        set_my_parameters(self, parameters)
        self.pid = "TEST_" + getpwuid(os.getuid())[0]
        self.mongodb_conn = False
        if pymongo.has_c() is False:
            msg = "WARNING: You do not have the pymongo C extensions installed. Data retrieval performance will be slow"
            cberror(msg)
            print(msg)

    class MetricStoreMgdConnException(Exception):
        '''
        TBD
        '''
        def __init__(self, msg, status):
            Exception.__init__(self)
            self.msg = msg
            self.status = status
        def __str__(self):
            return self.msg

    def mscp(self) :
        return get_my_parameters(self)
        
    @trace
    def connect(self, tout) :
        '''
        TBD
        '''
        try:

            if tout > 0:
                _conn = Connection(host = self.host, port = self.port, \
                                    max_pool_size=10, network_timeout = tout)
            else :
                _conn = Connection(host = self.host, port = self.port, \
                                    max_pool_size=10)

            self.mongodb_conn = _conn
            
            _msg = "A connection to MongoDB running on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.database) + ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)
            return self.mongodb_conn

        except PymongoException, msg :
            True

        # This was added here just because some MongoDBs don't accept the 
        # "max_pool_size" parameter
        try:

            if tout > 0:
                _conn = Connection(host = self.host, port = self.port, \
                                   network_timeout = tout)
            else :
                _conn = Connection(host = self.host, port = self.port)

            self.mongodb_conn = _conn
            
            _msg = "A connection to MongoDB running on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.database) + ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)
            return self.mongodb_conn

        except PymongoException, msg :
            _msg = "Unable to establish a connection with the MongoDB "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.database) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def disconnect(self) :
        '''
        TBD
        '''    
        try:

            self.mongodb_conn.disconnect()
            self.mongodb_conn = False
            _msg = "A connection to MongoDB running on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.database) + ", was terminated."
            cbdebug(_msg)
            return self.mongodb_conn

        except PymongoException, msg :
            _msg = "Unable to terminate a connection with the MongoDB "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.database) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def conn_check(self) :
        '''
        TBD
        '''
        if not self.mongodb_conn :
            try :
                self.connect(self.timeout)
            except self.MetricStoreMgdConnException, obj :
                raise self.MetricStoreMgdConnException(obj.msg, 2)

    @trace
    def initialize_metric_store(self, username) :
        '''
        TBD
        '''
        self.conn_check()

        username = username.replace('-',"dash")

        try :
            _collections = [ \
                            "latest_management_VM_" + username, \
                            "latest_management_HOST_" + username, \
                            "latest_runtime_os_VM_" + username, \
                            "latest_runtime_os_HOST_" + username, \
                            "latest_runtime_app_VM_" + username \
                            ]

            for _collection in _collections :
                _collection_handle = self.mongodb_conn[self.database][_collection]
                _collection_handle.drop()
                
            _collections = [ "trace_" + username, \
                            "management_HOST_" + username, \
                            "management_VM_" + username, \
                            "runtime_os_VM_" + username, \
                            "runtime_app_VM_" + username, \
                            "runtime_os_HOST_" + username ]

            for _collection in _collections :
                _collection_handle = self.mongodb_conn[self.database][_collection]
                _collection_handle.ensure_index("dashboard_polled")
                _collection_handle.ensure_index("expid")
                _collection_handle.ensure_index("time")
                _collection_handle.ensure_index("uuid")

            self.disconnect()
            return True

        except PymongoException, msg :
            _msg = "Unable to initialize all documents on "
            _msg += "\" on collection \"" + _collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    def flush_metric_store(self, username) :
        '''
        TBD
        '''
        self.conn_check()

        username = username.replace('-',"dash")

        try :
            _collections = ["latest_management_VM_" + username, \
                            "latest_management_HOST_" + username, \
                            "latest_runtime_os_VM_" + username, \
                            "latest_runtime_os_HOST_" + username, \
                            "latest_runtime_app_VM_" + username, \
                            "trace_" + username, \
                            "management_HOST_" + username, \
                            "management_VM_" + username, \
                            "runtime_os_VM_" + username, \
                            "runtime_app_VM_" + username, \
                            "runtime_os_HOST_" + username, \
                            "reported_management_VM_metric_names_" + username, \
                            "reported_runtime_app_VM_metric_names_" + username, \
                            "reported_runtime_os_HOST_metric_names_" + username, \
                            "reported_runtime_os_VM_metric_names_" + username, \
                            ]

            for _collection in _collections :
                _collection_handle = self.mongodb_conn[self.database][_collection]
                _collection_handle.drop()

            self.disconnect()
            return True

        except PymongoException, msg :
            _msg = "Unable to initialize all documents on "
            _msg += "\" on collection \"" + _collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def add_document(self, collection, document, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _collection_handle.insert(document)
            if disconnect_finish :
                self.disconnect()
            return True

        except PymongoException, msg :
            _msg = "Unable to insert document \"" + document
            _msg += "\" on collection \"" + collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)
 
    @trace
    def find_document(self, collection, criteria, allmatches = False, \
                      sortkeypairs = None, limitdocuments = 0, \
                      documentfields = None, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]

            if allmatches :
                _results = _collection_handle.find(criteria, \
                                                   sort = sortkeypairs, \
                                                   limit = limitdocuments, \
                                                   fields = documentfields)
            else :
                _results = _collection_handle.find_one(criteria, \
                                                       sort = sortkeypairs, \
                                                       fields = documentfields)

            if disconnect_finish :
                self.disconnect()

            return _results

        except PymongoException, msg :
            _msg = "Unable to retrieve documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)       

    @trace
    def update_document(self, collection, document, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _collection_handle.save(document)

            if disconnect_finish :
                self.disconnect()

        except PymongoException, msg :
            _msg = "Unable to update documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def delete_document(self, collection, criteria, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _collection_handle.remove(criteria)
            if disconnect_finish :
                self.disconnect()

        except PymongoException, msg :
            _msg = "Unable to remove document from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def cleanup_collection(self, collection, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _collection_handle.drop()
            if disconnect_finish :
                self.disconnect()
            return True

        except PymongoException, msg :
            _msg = "Unable to drop all documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def count_document(self, collection, criteria, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _matches = _collection_handle.find(criteria)
            if disconnect_finish :
                self.disconnect()
            return _matches.count()

        except PymongoException, msg :
            _msg = "Unable to count documents on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    def get_reported_objects(self, collection, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _result = {}
            _attributes = [ "vm_name", "role", "ai_name", "type", "aidrs_name", "pattern" ]
            for _attribute in _attributes :
                _result[_attribute + 's'] = []

            _collection_handle = self.mongodb_conn[self.database][collection]
            _documents = _collection_handle.find()
            for _document in _documents :
                for _attribute in _attributes :
                    if _attribute == "vm_name" :
                        _attribute_r = "name"
                    else :
                        _attribute_r = _attribute
                        
                    if _attribute_r in _document :
                        if not _result[_attribute + 's'].count(_document[_attribute_r]) :
                            _result[_attribute + 's'].append(_document[_attribute_r])
            
            if disconnect_finish :
                self.disconnect()
            return _result

        except PymongoException, msg :
            _msg = "Unable to get reported attributes on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    def get_time_boundaries(self, collection, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            _start_time = _collection_handle.find(spec = {}, fields = {"time" : "1"}, sort = [("time" , 1)], limit = 1)[0]["time"]
            _end_time = _collection_handle.find(spec = {}, fields = {"time" : "1"}, sort = [("time" , -1)], limit = 1)[0]["time"]

            if disconnect_finish :
                self.disconnect()

            return _start_time, _end_time

        except PymongoException, msg :
            _msg = "Unable to get time boundaries on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def get_info(self) :
        '''
        TBD
        '''
        self.conn_check()

        try :
            _buildinfo = self.mongodb_conn[self.database].command("buildinfo")
            _dbstats = self.mongodb_conn[self.database].command("dbstats")

            _output = []
            _output.append(["MongoDB Version", _buildinfo["version"]]) 
            _output.append(["Storage Size", str(_dbstats["storageSize"])])
            #_output.append(["File Size", _buildinfo["fileSize"]]) 
            _output.append(["Data Size", str(_dbstats["dataSize"])])
            _output.append(["Index Size", str(_dbstats["indexSize"])])
            _output.append(["Average Object Size", str(_dbstats["avgObjSize"])])
            _output.append(["Collections", str(_dbstats["collections"])])           
            
            return _output

        except PymongoException, msg :
            _msg = "Unable to get info database " + self.database + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise self.MetricStoreMgdConnException(str(_msg), 1)
