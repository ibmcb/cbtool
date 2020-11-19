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
    Created on Mar 21, 2012

    MongoDB data management operations library

    @author: Marcio A. Silva
'''

import pymongo

from lib.stores.common_datastore_adapter import MetricStoreMgdConn, MetricStoreMgdConnException
from pymongo import MongoClient
from pymongo import errors as PymongoException

def print_standalone(str) :
    print(str)

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

class MongodbMgdConn(MetricStoreMgdConn) :
    '''
    TBD
    '''

    @trace
    def __init__(self, parameters) :
        MetricStoreMgdConn.__init__(self, parameters)
        self.username = str(self.mongodb_username)
        self.port = self.mongodb_port
        self.mongodb_conn = False
        
        if pymongo.has_c() is False:
            msg = "WARNING: You do not have the pymongo C extensions installed. Data retrieval performance will be slow"
            cberr(msg)
            print(msg)

        self.version = pymongo.version.split('.')[0]

    @trace
    def connect(self, tout) :
        '''
        TBD
        '''
        try:

            if tout > 0:            
                
                _conn = MongoClient(host = self.host, port = self.port, \
                                    maxPoolSize=10)
            else :
                _conn = MongoClient(host = self.host, port = self.port, \
                                    max_pool_size=10)

            self.mongodb_conn = _conn
            
            _msg = "A connection to MongoDB running on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.database) + ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)            
            return self.mongodb_conn

        except PymongoException as msg :
            True

        except :
            True
        # This was added here just because some MongoDBs don't accept the 
        # "max_pool_size" parameter
        try:

            if tout > 0:
                _conn = MongoClient(host = self.host, port = self.port)
            else :
                _conn = MongoClient(host = self.host, port = self.port)

            self.mongodb_conn = _conn
            
            _msg = "A connection to MongoDB running on host "
            _msg += self.host + ", port " + str(self.port) + ", database"
            _msg += ' ' + str(self.database) + ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)            
            return self.mongodb_conn

        except PymongoException as msg :
            _msg = "Unable to establish a connection with the MongoDB "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.database) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def disconnect(self) :
        '''
        TBD
        '''    
        try:

            if "disconnect" in dir(self.mongodb_conn) :
                self.mongodb_conn.disconnect()
                self.mongodb_conn = False
                _msg = "A connection to MongoDB running on host "
                _msg += self.host + ", port " + str(self.port) + ", database"
                _msg += ' ' + str(self.database) + ", was terminated."
                cbdebug(_msg)
                return self.mongodb_conn

        except PymongoException as msg :
            _msg = "Unable to terminate a connection with the MongoDB "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + "database " + str(self.database) + ": "
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def conn_check(self, hostov = False, dbov = False, tout = False) :
        '''
        TBD
        '''
        if not self.mongodb_conn :
            if hostov :
                self.host = hostov

            if dbov :
                self.database = dbov

            if tout :
                self.timeout = tout
                
            try :
                self.connect(self.timeout)
                
            except MetricStoreMgdConnException as obj :
                raise MetricStoreMgdConnException(obj.msg, 2)
            
            if self.password and len(self.password) > 2 and str(self.password).lower() != "false" :
                try :
                    _auth_cmd = "mongo -u \"<YOUR ADMIN\" -p \"<YOUR ADMINPASS>\" "
                    _auth_cmd += "--authenticationDatabase \"admin\" --eval "
                    _auth_cmd += "\"db.createUser({user: '" + self.username 
                    _auth_cmd += "', pwd: '" + self.password + "', roles: [ { role:"
                    _auth_cmd += " 'readWrite', db: 'metrics' } ]})\" " 
                    _auth_cmd += self.host + ":" + str(self.port) + '/' + self.database

                    self.mongodb_conn[self.database].authenticate(self.username, self.password, mechanism='MONGODB-CR')

                except PymongoException as errmsg :
                    _msg = "Unable to authenticate against the database \"" + self.database
                    _msg += "\":" + str(errmsg) + ". \nPlease create the user there (i.e., directly on "
                    _msg += self.host + ") using the following command:\n"                    
                    _msg += _auth_cmd
                    raise MetricStoreMgdConnException(_msg, 2)
    
                except Exception as e:
                    _msg = "Unable to authenticate against the database \"" + self.database
                    _msg += "\":" + str(e) + ". \nPlease create the user there (i.e., directly on "
                    _msg += self.host + ") using the following command:\n"               
                    _msg += _auth_cmd
                    raise MetricStoreMgdConnException(_msg, 2)

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
                #_collection_handle.drop()
                
            _collections = [ "trace_" + username, \
                            "management_HOST_" + username, \
                            "management_VM_" + username, \
                            "runtime_os_VM_" + username, \
                            "runtime_app_VM_" + username, \
                            "runtime_os_HOST_" + username ]

            for _collection in _collections :
                _collection_handle = self.mongodb_conn[self.database][_collection]
                
                if int(self.version) < 3 :
                    _collection_handle.ensure_index("dashboard_polled")
                    _collection_handle.ensure_index("expid")
                    _collection_handle.ensure_index("time")
                    _collection_handle.ensure_index("uuid")
                else :
                    _collection_handle.create_index("dashboard_polled")
                    _collection_handle.create_index("expid")
                    _collection_handle.create_index("time")
                    _collection_handle.create_index("uuid")

            self.disconnect()
            return True

        except PymongoException as msg :
            _msg = "Unable to initialize all documents on "
            _msg += "\" on collection \"" + _collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    def flush_metric_store(self, username, partial = False, criteria = {}) :
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
                            "reported_runtime_os_VM_metric_names_" + username ]

            for _collection in _collections :
                _collection_handle = self.mongodb_conn[self.database][_collection]
                if partial :
                    _collection_handle.remove(criteria)
                else :
                    _collection_handle.drop()

            self.disconnect()
            return True

        except PymongoException as msg :
            _msg = "Unable to initialize all documents on "
            _msg += "\" on collection \"" + _collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def add_document(self, collection, document, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")
        
        try :
            _collection_handle = self.mongodb_conn[self.database][collection]

            if int(self.version) < 3 :
                _collection_handle.insert(document)
            else :
                if "_id" in document :
                    _collection_handle.replace_one({'_id': document["_id"]}, document, upsert = True)
                else :
                    _collection_handle.insert_one(document)

            if disconnect_finish :
                self.disconnect()
            return True

        except PymongoException as msg :
            _msg = "Unable to insert document \"" + document
            _msg += "\" on collection \"" + collection + "\": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)
 
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
                                                   projection = documentfields)
            else :

                _results = _collection_handle.find_one(criteria, \
                                                       sort = sortkeypairs, \
                                                       projection = documentfields)

            if disconnect_finish :
                self.disconnect()

            return _results

        except PymongoException as msg :
            _msg = "Unable to retrieve documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)       

    @trace
    def update_document(self, collection, document, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            
            if int(self.version) < 3 :
                _collection_handle.save(document)
            else :
                # This insane behavior is supposed to be the "expected behavior"
                # according to https://jira.mongodb.org/browse/SERVER-14322
                try: 
                    _collection_handle.replace_one({'_id': document["_id"]}, document, upsert = True)
                except :
                    _collection_handle.replace_one({'_id': document["_id"]}, document, upsert = True)                

            if disconnect_finish :
                self.disconnect()

        except PymongoException as msg :
            _msg = "Unable to update documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    @trace
    def delete_document(self, collection, criteria, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            
            if int(self.version) < 3 :            
                _collection_handle.remove(criteria)
            else :
                _collection_handle.delete_one(criteria)
                
            if disconnect_finish :
                self.disconnect()

        except PymongoException as msg :
            _msg = "Unable to remove document from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

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

        except PymongoException as msg :
            _msg = "Unable to drop all documents from the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

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

        except PymongoException as msg :
            _msg = "Unable to count documents on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

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

        except PymongoException as msg :
            _msg = "Unable to get reported attributes on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

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

        except PymongoException as msg :
            _msg = "Unable to get time boundaries on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

    def get_experiment_list(self, collection, disconnect_finish = False) :
        '''
        TBD
        '''
        self.conn_check()

        collection = collection.replace('-',"dash")

        _experiment_list = None
        try :
            _collection_handle = self.mongodb_conn[self.database][collection]
            
            #_experiment_list = _collection_handle.distinct('expid')

            # The document is getting too big, but a workaround was found.
            # TODO: Find a more permanent solution to this.
            _experiment_list_agg = _collection_handle.aggregate([ {"$group": {"_id": '$expid'}} ])
            _experiment_list = ([_v['_id'] for _v in _experiment_list_agg])

            if disconnect_finish :
                self.disconnect()

            return _experiment_list

        except PymongoException as msg :
            _msg = "Unable to get time boundaries on the collection \""
            _msg += collection + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)

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

        except PymongoException as msg :
            _msg = "Unable to get info database " + self.database + ": " 
            _msg += str(msg) + '.'
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 1)
