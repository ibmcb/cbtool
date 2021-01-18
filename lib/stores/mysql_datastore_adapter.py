#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2020 DigitalOcean, Inc. 

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
    Created on June 16th, 2020

    Mysql data management operations library

    @author: Michael Galaxy 
'''

import json
import threading
import mysql.connector
import traceback

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.stores.common_datastore_adapter import MetricStoreMgdConn

class MetricStoreMgdConnException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg

class MysqlMgdConn(MetricStoreMgdConn) :
    @trace
    def __init__(self, parameters) :
        MetricStoreMgdConn.__init__(self, parameters)
        self.username = self.mysql_username
        self.port = self.mysql_port
        self.version = mysql.connector.__version__.split('.')[0]
        self.conn_mutex = threading.Lock()
        self.operation_mutex = threading.Lock()
        self.mysql_conn = False

    @trace
    def connect(self, tout) :
        try:
            #if tout and tout > 0:            
            #    MysqlMgdConn.conn.set_connection_timeout(tout)

            if not self.mysql_conn or not self.mysql_conn.is_connected() :
                cbdebug("Opening to: " + self.database)
                self.mysql_conn = mysql.connector.connect(host = self.host, port = self.port, user = self.username, password = self.password)
                cursor = self.mysql_conn.cursor()
                try :
                    cursor.execute("use " + self.database)
                except mysql.connector.Error as err :
                    if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                        cbwarn("Database not found. Will create later.")
                cursor.close()

            _msg = "A connection to MySQL running on host "
            _msg += self.host + ", port " + str(self.port)
            _msg += ", with a timeout of "
            _msg += str(tout) + "s was established."
            cbdebug(_msg)

        except mysql.connector.Error as err :
            if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                _msg = "Something is wrong with your MySQL user name or password."
                cberr(_msg)
                raise MetricStoreMgdConnException(str(_msg), 1)
            else:
                _msg = "Unknown MySQL error: " + str(err)
                cberr(_msg)
                raise MetricStoreMgdConnException(str(_msg), 2)

    @trace
    def disconnect(self) :
        try:
            if "disconnect" in dir(self.mysql_conn) :
                self.mysql_conn.disconnect()
                self.mysql_conn = False
                _msg = "A connection to MySQL running on host "
                _msg += self.host + ", port " + str(self.port)
                _msg += " was terminated."
                cbdebug(_msg)

        except mysql.connector.Error as err :
            _msg = "Unable to terminate a connection with MySQL "
            _msg += "server on host " + self.host + " port "
            _msg += str(self.port) + ": "
            _msg += str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 3)

    @trace
    def conn_check(self, hostov = False, dbov = False, tout = False) :
        self.conn_mutex.acquire()
        if not self.mysql_conn or not self.mysql_conn.is_connected() :

            # If connection exists, but it is not healthy cleanup the
            # existing connection
            if self.mysql_conn and not self.mysql_conn.is_connected() :
                self.disconnect()

            if hostov :
                self.host = hostov

            if dbov :
                self.database = dbov

            if tout :
                self.timeout = tout
                
            try :
                self.connect(self.timeout)
            except MetricStoreMgdConnException as obj :
                self.conn_mutex.release()
                raise MetricStoreMgdConnException(obj.msg, 2)
            except Exception as e :
                self.conn_mutex.release()
                raise(e)

        assert(self.mysql_conn)
        assert(self.mysql_conn.is_connected())
        cursor = self.mysql_conn.cursor()
        self.conn_mutex.release()
        return cursor
            
    @trace
    def initialize_metric_store(self, username) :
        username = username.replace('-',"dash")

        try :
            cursor = self.conn_check()        

            if not self.database :
                cursor.execute("create database " + self.database)
                cursor.execute("use " + self.database)

            _latest_tables = [ \
                            "latest_management_VM_" + username, \
                            "latest_management_HOST_" + username, \
                            "latest_runtime_os_VM_" + username, \
                            "latest_runtime_os_HOST_" + username, \
                            "latest_runtime_app_VM_" + username, \
                            "reported_management_VM_metric_names_" + username, \
                            "reported_runtime_app_VM_metric_names_" + username, \
                            "reported_runtime_os_HOST_metric_names_" + username, \
                            "reported_runtime_os_VM_metric_names_" + username \
                            ]

            _indexed_tables = [ "trace_" + username, \
                            "management_HOST_" + username, \
                            "management_VM_" + username, \
                            "runtime_os_VM_" + username, \
                            "runtime_app_VM_" + username, \
                            "runtime_os_HOST_" + username ]

            cursor.execute("show tables")

            _tables_found = [] 

            for x in cursor:
              _tables_found.append(x[0])

            for _table in (_latest_tables + _indexed_tables) :
                if _table not in _tables_found :
                    statement = "create table " + _table + "(" + \
                            "id int auto_increment primary key," + \
                            "document json NOT NULL," + \
                            "`expid` VARCHAR(255) GENERATED ALWAYS AS (`document` ->> '$.expid')," + \
                            "`_id` VARCHAR(255) GENERATED ALWAYS AS (`document` ->> '$._id')," + \
                            "`time` VARCHAR(255) GENERATED ALWAYS AS (`document` ->> '$.time')," + \
                            "`uuid` VARCHAR(255) GENERATED ALWAYS AS (`document` ->> '$.uuid')," + \
                            "`dashboard_polled` VARCHAR(255) GENERATED ALWAYS AS (`document` ->> '$.dashboard_polled')" + \
                        ")"
                    cursor.execute(statement)

                    if _table in _indexed_tables : 
                        cursor.execute("CREATE INDEX `expid_idx` ON `" + _table + "`(`expid`)")
                        cursor.execute("CREATE INDEX `time_idx` ON `" + _table + "`(`time`)")
                        cursor.execute("CREATE INDEX `uuid_idx` ON `" + _table + "`(`uuid`)")
                        cursor.execute("CREATE INDEX `dashboard_polled_idx` ON `" + _table + "`(`dashboard_polled`)")
            cursor.close()
            self.mysql_conn.commit()
            self.disconnect()
            return True

        except mysql.connector.Error as err :
            self.disconnect()
            _msg = "Unable to complete database initialization: "
            _msg += str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 4)

    def make_restrictions(self, criteria, join = "and", level = 0) :
        full_list = ""
        restrictions = []
        for _key in criteria.keys() :
            _value = criteria[_key]
            if isinstance(_value, set) :
                _msg = "1) We cannot yet handle this criteria: " + str(criteria)
                cberr(_msg)
                raise MetricStoreMgdConnException(_msg, 41)
            elif isinstance(_value, dict) :
                for subkey in _value.keys() :
                    if subkey.lower() == "$regex" :
                        if _value[subkey] :
                            restrictions.append("document->>'$." + _key + "' REGEXP '" + str(_value[subkey]) + "'")
                    elif subkey.lower() == "$exists" :
                        if not isinstance(_value[subkey], bool) :
                            _msg = "2) We cannot yet handle this criteria: " + str(_value)
                            cberr(_msg)
                            raise MetricStoreMgdConnException(_msg, 41)

                        if _value[subkey] :
                            restrictions.append("document->>'$." + _key + "' IS NOT NULL")
                        else :
                            restrictions.append("document->>'$." + _key + "' IS NULL")
                    else :
                        _msg = "3) We cannot yet handle this criteria: " + str(subkey)
                        cberr(_msg)
                        raise MetricStoreMgdConnException(_msg, 41)
            elif isinstance(_value, list) :
                # Handle this group below 
                continue
            else :
                _newvalue = _value
                if isinstance(_value, bytes) :
                    _newvalue = _value.decode("utf-8")
                restrictions.append("document->>'$." + _key + "' = '" + str(_newvalue) + "'")

        if len(restrictions) :
            full_list += (" " + join + " ").join(restrictions)

        for _key in criteria.keys() :
            if _key.lower() == "$or" or _key.lower() == "$and" :
                _value = criteria[_key]
                if isinstance(_value, list) :
                    subdict = {}
                    for subitem in _value :
                        if not isinstance(subitem, dict) :
                            _msg = "4) We cannot yet handle this criteria: " + str(subitem)
                            cberr(_msg)
                            raise MetricStoreMgdConnException(_msg, 41)
                        subdict.update(subitem)
                    sub_restrictions = self.make_restrictions(subdict, join = _key[1:], level = level + 1)
                    if sub_restrictions.strip() != "" :
                        full_list += " and (" + sub_restrictions + ")"
                else :
                    _msg = "5) We cannot yet handle this criteria: " + str(_value)
                    cberr(_msg)
                    raise MetricStoreMgdConnException(_msg, 41)

        if full_list.strip() != "" :
            if level == 0 :
                return " where " + full_list
            else :
                return full_list

        return ""

    def flush_metric_store(self, username, partial = False, criteria = {}) :
        username = username.replace('-',"dash")

        try :
            cursor = self.conn_check()        
            _tables = ["latest_management_VM_" + username, \
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

            for _table in _tables :
                if partial and len(criteria) :
                    statement = "delete from " + _table + self.make_restrictions(criteria)
                    cursor.execute(statement) 
                else :
                    cursor.execute("delete from " + _table)

            cursor.close()
            self.mysql_conn.commit()
            self.disconnect()
            return True
        except mysql.connector.Error as err :
            self.disconnect()
            _msg = "Unable to flush metric store: " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 5)

    @trace
    def add_document(self, table, document, disconnect_finish = False) :
        table = table.replace('-',"dash")
        self.operation_mutex.acquire()
        lastrowid = -1

        try :
            cursor = self.conn_check()

            if "_id" in document and isinstance(document["_id"], bytes) :
                document["_id"] = document["_id"].decode("utf-8")
            statement = "insert into " + table + " (document) values ('" + json.dumps(document) + "')"
            result = cursor.execute(statement)
            if cursor.rowcount != 1 :
                self.mysql_conn.rollback()
                raise MetricStoreMgdConnException("Add failed w/ statement: " + statement, 65)
            cursor.close()
            self.mysql_conn.commit()
            lastrowid = cursor.lastrowid
            if disconnect_finish :
                self.disconnect()

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to insert document into table \"" + table + "\": " 
            _msg += str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 6)
        except Exception as e :
            self.operation_mutex.release()
            raise MetricStoreMgdConnException(str(e), 64)

        self.operation_mutex.release()
        return lastrowid 
 
    @trace
    def find_document(self, table, criteria, allmatches = False, \
                      sortkeypairs = None, limitdocuments = 0, \
                      documentfields = None, disconnect_finish = False) :

        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()

            statement = "select "

            if documentfields is not None :
                convertedfields = []
                for field in documentfields :
                    convertedfields.append("document->>'$." + field + "'")
                   
                statement += ",".join(["id"] + convertedfields)
            else :
                statement += " id,document "

            statement += " from " + table + " " + self.make_restrictions(criteria)

            if sortkeypairs :
                keylist = []
                for keypair in sortkeypairs :
                    # FIXME: I'm unsure of how to have different directional sort criteria for multiple
                    # sorted keys. Will have to look into that later, so for the time being,
                    # I'm dropping the direction.
                    keylist.append("document->>'$." + keypair[0] + "'")
                statement += " order by " + ",".join(keylist)

            if not allmatches or limitdocuments :
                if limitdocuments > 0 :
                    statement += " limit " + str(limitdocuments)
                else :
                    statement += " limit 1"

            _results = []

            # FIXME: We need to figure out how to safely allow iterators over
            # the live connection. But for now, let's just extract all the results
            result = cursor.execute(statement)
            while True :
                rows = cursor.fetchmany(4)
                if not len(rows) :
                    break
                for resultset in rows :
                    original_mysql_id = resultset[0]
                    document = False
                    if documentfields is not None :
                        document = {}
                        for idx in range(1, len(resultset)) :
                           document[documentfields[idx - 1]] = resultset[idx].decode()
                    else :
                        if isinstance(resultset[1], str) :
                            document = json.loads(resultset[1])
                        else :
                            assert(isinstance(resultset[1], dict))
                            document = resultset[1]

                    document["original_mysql_id"] = original_mysql_id
                    _results.append(document)

            cursor.close()
            self.operation_mutex.release()

            if allmatches :
                return _results
            else :
                if len(_results) >= 1 :
                    return _results[0]

            return None 

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to retrieve documents from the table \""
            _msg += table + ": "  + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 7)       
        except Exception as e:
            for line in traceback.format_exc().splitlines() :
                cbdebug(line)
            raise e

    @trace
    def update_document(self, table, document, disconnect_finish = False) :
        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()

            if "_id" in document and isinstance(document["_id"], bytes) :
                document["_id"] = document["_id"].decode("utf-8")

            if "original_mysql_id" not in document :
                if "_id" in document :
                    # Attempt to find the original ID first
                    statement = "select id from " + table + " where _id = '" + document["_id"] + "'"
                    cursor.execute(statement)
                    while True :
                        rows = cursor.fetchmany(1)
                        if not len(rows) :
                            break
                        for (original_mysql_id,) in rows :
                            document["original_mysql_id"] = original_mysql_id

                if "original_mysql_id" not in document :
                    cursor.close()
                    self.operation_mutex.release()
                    cbwarn("This document does not have a pre-existing identifier. Cannot update. Will insert first")
                    document["original_mysql_id"] = self.add_document(table, document, disconnect_finish = disconnect_finish)
                    return

            statement = "update " + table + " set document = '" + json.dumps(document) + "' where id = " + str(document["original_mysql_id"])
            result = cursor.execute(statement)
            cursor.close()
            self.mysql_conn.commit()

            if disconnect_finish :
                self.disconnect()

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to update documents from the table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 8)
        except Exception as e :
            self.operation_mutex.release()
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 67)

        self.operation_mutex.release()

    @trace
    def delete_document(self, table, criteria, disconnect_finish = False) :
        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            
            cursor = self.conn_check()
            statement = "delete from " + table + self.make_restrictions(criteria)
            cursor.execute(statement) 
            cursor.close()
            self.mysql_conn.commit()
            if disconnect_finish :
                self.disconnect()

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to remove document from the table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 9)

        self.operation_mutex.release()

    # FIXME: I am unable to find any callers of this function
    @trace
    def cleanup_collection(self, table, disconnect_finish = False) :
        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()
            statement = "delete from " + table
            cursor.execute(statement) 
            cursor.close()
            self.mysql_conn.commit()
            if disconnect_finish :
                self.disconnect()
            self.operation_mutex.release()
            return True

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to drop all documents from the table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 10)

    @trace
    def count_document(self, table, criteria, disconnect_finish = False) :
        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()
            statement = "select * from " + table + self.make_restrictions(criteria)
            result = cursor.execute(statement)
            count = 0
            if result is not None :
                count = result.rowcount
            else :
                rows = cursor.fetchmany(4)
                for resultset in rows :
                    count += 1 
            cursor.close()
            if disconnect_finish :
                self.disconnect()
            self.operation_mutex.release()
            return count

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to count documents on the table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 11)
        except Exception as e:
            for line in traceback.format_exc().splitlines() :
                cbdebug(line)
            raise e

    def get_reported_objects(self, table, disconnect_finish = False) :
        table = table.replace('-',"dash")

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()
            _result = {}
            _attributes = [ "vm_name", "role", "ai_name", "type", "aidrs_name", "pattern" ]
            for _attribute in _attributes :
                _result[_attribute + 's'] = []

            statement = "select id, document from " + table
            cursor.execute(statement)
            while True :
                rows = cursor.fetchmany(4)
                if not len(rows) :
                    break
                for (original_mysql_id, _document) in rows :
                    for _attribute in _attributes :
                        if _attribute == "vm_name" :
                            _attribute_r = "name"
                        else :
                            _attribute_r = _attribute
                            
                        if _attribute_r in _document :
                            if not _result[_attribute + 's'].count(_document[_attribute_r]) :
                                _result[_attribute + 's'].append(_document[_attribute_r])
            
            cursor.close()
            if disconnect_finish :
                self.disconnect()
            self.operation_mutex.release()
            return _result

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to get reported attributes on the table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 12)

    # I could not find any code that uses this function
    #def get_time_boundaries(self, table, disconnect_finish = False) :

    def get_experiment_list(self, table, disconnect_finish = False) :
        table = table.replace('-',"dash")
        _experiment_list = [] 

        self.operation_mutex.acquire()
        try :
            cursor = self.conn_check()
            
            statement = "select distinct(expid) from " + table + " where expid is not NULL"
            cursor.execute(statement)

            while True :
                rows = cursor.fetchmany(4)
                if not len(rows) :
                    break
                for (expid) in rows :
                    _experiment_list.append(expid)

            cursor.close()
            if disconnect_finish :
                self.disconnect()

            self.operation_mutex.release()
            return _experiment_list

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to get time experiment list for table \""
            _msg += table + ": " + str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 14)

    @trace
    def get_info(self) :
        self.operation_mutex.acquire()
        try :
            _output = []
            cursor = self.conn_check()
            cursor.execute("show variables")
            while True :
                rows = cursor.fetchmany(4)
                if not len(rows) :
                    break
                for row in rows :
                    if row[0] in ["version"] : 
                        _output.append([row[0], row[1]])
            
            cursor.execute("select sum(data_length + index_length)/1024/1024 'size' FROM information_schema.TABLES")
            while True :
                rows = cursor.fetchmany(4)
                if not len(rows) :
                    break
                for row in rows :
                    _output.append(["Data Size (MB)", str(float(row[0]))])

            cursor.close()
            self.operation_mutex.release()
            return _output

        except mysql.connector.Error as err :
            self.operation_mutex.release()
            _msg = "Unable to get info for database " + self.database + ": " 
            _msg += str(err)
            cberr(_msg)
            raise MetricStoreMgdConnException(str(_msg), 15)
        except Exception as e :
            self.operation_mutex.release()
            cbdebug("No workey: " + str(e))
