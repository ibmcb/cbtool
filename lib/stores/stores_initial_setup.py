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
    Created on Aug 27, 2011

    Initial Setup for all Cloudbench stores

    @author: Marcio Silva
'''

import socket
import traceback

from os import mkdir, listdir, path, access, F_OK, W_OK

from shutil import rmtree
from time import sleep

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.process_management import ProcessManagement
from lib.remote.network_functions import Nethashget, hostname2ip, NetworkException
from lib.stores.common_datastore_adapter import MetricStoreMgdConn, MetricStoreMgdConnException
from .redis_datastore_adapter import RedisMgdConn
from .mongodb_datastore_adapter import MongodbMgdConn
from .mysql_datastore_adapter import MysqlMgdConn

class StoreSetupException(Exception):
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg

def load_metricstore_adapter(msattrs) :
    _ms_adapter = __import__("lib.stores." + msattrs["kind"] + "_datastore_adapter", \
                             fromlist=[msattrs["kind"].capitalize() + "MgdConn"])

    _ms_conn_class = getattr(_ms_adapter, msattrs["kind"].capitalize() + "MgdConn")
    
    return _ms_conn_class(msattrs)

def redis_objectstore_setup(global_objects, operation, cloud_name = None) :
    '''
    TBD
    '''
    _protocol = global_objects["objectstore"]["protocol"]
    _hostname = global_objects["objectstore"]["host"]
    _databaseid = int(global_objects["objectstore"]["dbid"])
    _timeout = float(global_objects["objectstore"]["timout"])
    _username = global_objects["objectstore"]["username"]
    _usage = global_objects["objectstore"]["usage"].lower()

    try :
        _instance_dir = global_objects["space"]["instance_dir"]

        if operation == "check" :

            _stores_path = global_objects["space"]["stores_working_dir"]
            if not path.exists(_stores_path) :
                cbdebug("Making stores working directory: " + _stores_path)
                mkdir(_stores_path)
                
            if _usage == "shared" :
                _hostport = int(global_objects["objectstore"]["port"])
                _proc_man =  ProcessManagement(username = "root")

                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _redis_pid = _proc_man.get_pid_from_cmdline("redis-server")

                    _cmd = "/usr/local/bin/redis-server /etc/redis.conf"
                    if not _redis_pid :
                        _msg = "Unable to detect a shared Redis server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print(_msg)
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = _stores_path + '/' + _username + "_redis.conf"
                _cmd = "redis-server " + _config_file_fn

                _proc_man =  ProcessManagement(username = _username)
                
                _redis_pid = _proc_man.get_pid_from_cmdline("redis-server")      

                if not _redis_pid :
                    _hostport = int(global_objects["objectstore"]["port"])

                    _config_file_contents = global_objects["objectstore"]["config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])
                    _config_file_contents = _config_file_contents.replace(';','\n')

                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()

                    _redis_pid = _proc_man.start_daemon(_cmd)

                    if not _redis_pid :
                        _msg = "Unable to detect a private Redis server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"
                        print(_msg)
                        exit(8)
                else :
                    global_objects["objectstore"]["port"] = _proc_man.get_port_from_pid(_redis_pid[0]) 
                    _hostport = int(global_objects["objectstore"]["port"])

            _nh_conn = Nethashget(_hostname)

            _nh_conn.nmap(_hostport, _protocol)
            _msg = "An Object Store of the kind \"Redis\" (" + _usage + ") "
            _msg += "on node " + _hostname + ", " + _protocol 
            _msg += " port " + str(_hostport) + ", database id \""
            _msg += str(_databaseid) + "\" seems to be running."
            _status = 0

        else :
            if not cloud_name :
                raise StoreSetupException("Name of cloud is required for the 'initialize' mode", 22)
            
            operation = "initialize"

            _hostport = int(global_objects["objectstore"]["port"])

            _collection_names = [ "reported_management_vm_metric_names", \
                                 "reported_runtime_os_host_metric_names", \
                                 "reported_runtime_os_vm_metric_names", \
                                 "host_management_metrics_header", \
                                 "vm_management_metrics_header", \
                                 "host_runtime_os_metrics_header", \
                                 "vm_runtime_os_metrics_header", \
                                 "vm_runtime_app_metrics_header", \
                                 "trace_header" ]

            for _collection_name in _collection_names : 
                for _component in global_objects["mon_defaults"][_collection_name].split(',') :
                    if _component.lower() in global_objects["mon_defaults"] :
                        global_objects["mon_defaults"][_collection_name] = \
                        global_objects["mon_defaults"][_collection_name].replace(_component, \
                                                                                 global_objects["mon_defaults"][_component.lower()] + ',')
                global_objects["mon_defaults"][_collection_name] = \
                global_objects["mon_defaults"][_collection_name][:-1].replace(",,",',')

            _rmc = RedisMgdConn(global_objects["objectstore"])

            # First we remove the leftovers from previous experiments.
            if _rmc.initialize_object_store(cloud_name, global_objects, True) :
                if not path.exists(_instance_dir) :
                    mkdir(_instance_dir)

                for _file_name in listdir(_instance_dir) :
                    _file_name = path.join(_instance_dir, _file_name)
                    if path.isdir(_file_name) :
                        rmtree(_file_name)

                _msg = "Folders (but not data) underneath experiment "
                _msg += "directory " + _instance_dir + " were removed."
                cbdebug(_msg)

                _msg = "The Redis datastore was successfully initialized on server " + _hostname
                _msg += ", port " + str(_hostport) + ", database id \"" + str(_databaseid)
                _msg += "\"."
                cbdebug(_msg)
                _status = 0

            else :
                _msg = "The Object Store of the kind \"Redis\" was successfully initialized "
                _msg += "on node " + _hostname + ". To change its "
                _msg += "attributes/state, use the *alter commands"
                _msg += "(e.g., cldalter, vmcalter, vmalter) or explicity detach "
                _msg += "and attach this cloud back to this experiment."
                cbdebug(_msg)
                _status = 0

        return _status, _msg
    
    except NetworkException as obj :
        _msg = "An Object Store of the kind \"Redis\" on node "
        _msg += _hostname + ", " + _protocol + " port " + str(_hostport)
        _msg += ", database id \"" + str(_databaseid)
        _msg += "\" seems to be down: " + str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
            
    except RedisMgdConn.ObjectStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
    
    except OSError :
        _status = 10
        _msg = "Experiment directory " + _instance_dir
        _msg += " could not be removed, "
        _msg += " or stores directory " + _stores_path + " could not be created."
        raise StoreSetupException(_msg, 9)

    except Exception as e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)
    
def syslog_logstore_setup(global_objects, operation = "check") :
    '''
    TBD
    '''
    _hostname = global_objects["logstore"]["hostname"]
    _protocol = global_objects["logstore"]["protocol"]
    _username = global_objects["logstore"]["username"]
    _usage = global_objects["logstore"]["usage"].lower()
    _stores_wk_dir = global_objects["space"]["stores_working_dir"]
    _log_dir = global_objects["space"]["log_dir"]

    try :
        _name, _ip = hostname2ip(_hostname)        
        
        if operation == "check" :

            if _usage == "shared" :
                _hostport = int(global_objects["logstore"]["port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "root")
                    _rsyslog_pid = _proc_man.get_pid_from_cmdline("rsyslogd")
    
                    _cmd = "/sbin/rsyslogd -i /var/run/syslogd.pid "

                    if not _rsyslog_pid :
                        _msg = "Unable to detect a shared rsyslog server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print(_msg)
                        exit(8)

            else :
                _usage = "private"

                _proc_man =  ProcessManagement(username = _username)

                _config_file_fn = _stores_wk_dir + '/' + _username + "_rsyslog.conf"
                _cmd = "rsyslogd -f " + _config_file_fn + " " + "-i " + _stores_wk_dir + "/rsyslog.pid"

                if not access(_config_file_fn, F_OK) :
                    # File was deleted, but the rsyslog process is still dangling
                    _proc_man.run_os_command("sudo pkill -9 -f " + _config_file_fn)

                if not access(_log_dir, W_OK) :
                    # The directory does not even exist, kill any rsyslog processes still dangling
                    _proc_man.run_os_command("sudo pkill -9 -f " + _config_file_fn)                    
                    _proc_man.run_os_command("sudo mkdir -p " + _log_dir + " && sudo chmod 777 " + _log_dir)

                _rsyslog_pid = _proc_man.get_pid_from_cmdline(_cmd)     

                if not _rsyslog_pid :
                    _hostport = int(global_objects["logstore"]["port"])

                    _config_file_contents = global_objects["logstore"]["config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("DOLLAR", '$')
                    _config_file_contents = _config_file_contents.replace("RSYSLOG", "RSYSLOG_")
                    _config_file_contents = _config_file_contents.replace("**", "_")
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLLOGDIR", _log_dir)
                    _config_file_contents = _config_file_contents.replace("REPLUSER", _username + '_')                    
                    _config_file_contents = _config_file_contents.replace(';','\n')
                    _config_file_contents = _config_file_contents.replace("--", ';')

                    _config_file_fn = _stores_wk_dir + '/' + _username + "_rsyslog.conf"
                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()

                    _rsyslog_pid = _proc_man.start_daemon(_cmd)
             
                    if not _rsyslog_pid :
                        _msg = "Unable to detect a private rsyslog server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"
                        print(_msg)
                        exit(8)

                else :
                    _config_file_fd = open(_config_file_fn, 'r')
                    _config_file_contents = _config_file_fd.readlines()
                    _config_file_fd.close()

                    for _line in _config_file_contents :
                        if _line.count("UDPServerRun") :
                            global_objects["logstore"]["port"] = _line.split()[1]
                            _hostport = int(global_objects["logstore"]["port"])
                            break

        _nh_conn = Nethashget(_hostname)

        _nh_conn.nmap(_hostport, _protocol)
        _msg = "A Log Store of the kind \"rsyslog\" (" + _usage + ") "
        _msg += "on node " + _hostname + ", " + _protocol
        _msg += " port " + str(_hostport) + " seems to be running."
        cbdebug(_msg)
        _status = 0
        return _status, _msg
    
    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
        
    except NetworkException as obj :
        _msg = "Syslog Log Store network error: " + str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except Exception as e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

def mongodb_metricstore_setup(global_objects, operation = "check") :
    '''
    TBD
    '''
    _protocol = global_objects["metricstore"]["protocol"]
    _hostname = global_objects["metricstore"]["host"]
    _databaseid = global_objects["metricstore"]["database"]
    _timeout = float(global_objects["metricstore"]["timeout"])
    _username = global_objects["mon_defaults"]["username"]
    _usage = global_objects["metricstore"]["usage"].lower()

    try :
        if operation == "check" :

            if _usage == "shared" :          

                _hostport = int(global_objects["metricstore"]["mongodb_port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "root")
                    _mongodb_pid = _proc_man.get_pid_from_cmdline("mongod -f")
    
                    _cmd = "/usr/local/bin/mongod -f /etc/mongod.conf --pidfilepath /var/run/mongod.pid"
                    if not _mongodb_pid :
                        _msg = "Unable to detect a shared MongoDB server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print(_msg)
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_mongod.conf"
                _cmd = "mkdir -p " + global_objects["space"]["stores_working_dir"]  + "/logs; mongod -f " + _config_file_fn + " --pidfilepath " + global_objects["space"]["stores_working_dir"] + "/mongod.pid"
    
                _proc_man =  ProcessManagement(username = _username)
                _mongodb_pid = _proc_man.get_pid_from_cmdline("mongod -f")

                if not _mongodb_pid :
                    _hostport = int(global_objects["metricstore"]["mongodb_port"])

                    _config_file_contents = global_objects["metricstore"]["mongodb_config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])
                    _config_file_contents = _config_file_contents.replace("**", "_")
                    _config_file_contents = _config_file_contents.replace("--", '=')
                    _config_file_contents = _config_file_contents.replace(';','\n')

                    _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_mongod.conf"
                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()
    
                    _mongodb_pid = _proc_man.start_daemon(_cmd)
                    
                    sleep(5)

                    if not _mongodb_pid :
                        _msg = "Unable to detect a private MongoDB server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"
                        print(_msg)
                        exit(8)

                else :
                    global_objects["metricstore"]["mongodb_port"] = _proc_man.get_port_from_pid(_mongodb_pid[0])
                    _hostport = int(global_objects["metricstore"]["mongodb_port"])

            _nh_conn = Nethashget(_hostname)

            _nh_conn.nmap(_hostport, _protocol)
            _msg = "A Metric Store of the kind \"MongoDB\" (" + _usage + ") "
            _msg += "on node " + _hostname + ", " + _protocol
            _msg += " port " + str(_hostport) + ", database id \"" + str(_databaseid)
            _msg += "\" seems to be running."
            cbdebug(_msg)
            _status = 0

        else:
            operation = "initialize"
            _mmc = MongodbMgdConn(global_objects["metricstore"])
            _mmc.initialize_metric_store(_username)
            
            _msg = "The Metric Store of the kind \"MongoDB\" was successfully initialized "
            _msg += "on node: " + str(global_objects["metricstore"])
            cbdebug(_msg)
            _status = 0
            
        return _status, _msg

    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except NetworkException as obj :
        _msg = "A Metric Store of the kind \"MongoDB\" on node "
        _msg += _hostname + ", " + _protocol + " port " + str(_hostport)
        _msg += ", database id \"" + str(_databaseid) + "\" seems to be down: "
        _msg += str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except MetricStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except Exception as e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

def mysql_metricstore_setup(global_objects, operation = "check") :
    _protocol = global_objects["metricstore"]["protocol"]
    _hostname = global_objects["metricstore"]["host"]
    _databaseid = global_objects["metricstore"]["database"]
    _timeout = float(global_objects["metricstore"]["timeout"])
    _username = global_objects["mon_defaults"]["username"]
    _usage = global_objects["metricstore"]["usage"].lower()
    _hostport = int(global_objects["metricstore"]["mysql_port"])

    try :
        if operation == "check" :

            if _usage == "shared" :          

                _hostport = int(global_objects["metricstore"]["mysql_port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "mysql")
                    _mysql_pid = _proc_man.get_pid_from_cmdline("mysqld")
    
                    if not _mysql_pid :
                        _msg = "Unable to detect a shared Mysql server daemon running. "
                        _msg += "Please try to start one."
                        print(_msg)
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_mysqld.conf"
                _cmd = "mkdir -p " + global_objects["space"]["stores_working_dir"]  + "/logs; mysqld --defaults-file=" + _config_file_fn
    
                _proc_man =  ProcessManagement(username = _username)
                _pid = _proc_man.get_pid_from_cmdline("mysqld --defaults-file=" + _config_file_fn)

                if not _pid :
                    _hostport = int(global_objects["metricstore"]["mysql_port"])

                    _config_file_contents = global_objects["metricstore"]["mysql_config_string"]
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLUSER", _username)
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])
                    _config_file_contents = _config_file_contents.replace("--", '=')
                    _config_file_contents = _config_file_contents.replace('**', '-')
                    _config_file_contents = _config_file_contents.replace(';','\n')

                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()
    
                    _pid = _proc_man.start_daemon(_cmd)
                    
                    sleep(5)

                    if not _pid :
                        _msg = "Unable to detect a private MysqlDB server daemon running. "
                        _msg += "You may need to issue $ sudo apt-get install apparmor-utils && sudo aa-complain /usr/bin/mysqld, followed by: " + _cmd + ")"
                        print(_msg)
                        exit(8)

                else :
                    global_objects["metricstore"]["mysql_port"] = _proc_man.get_port_from_pid(_pid[0])
                    _hostport = int(global_objects["metricstore"]["mysql_port"])

            _nh_conn = Nethashget(_hostname)

            _nh_conn.nmap(_hostport, _protocol)
            _msg = "A Metric Store of the kind \"Mysql\" (" + _usage + ") "
            _msg += "on node " + _hostname + ", " + _protocol
            _msg += " port " + str(_hostport) + ", database id \"" + str(_databaseid)
            _msg += "\" seems to be running."
            cbdebug(_msg)
            _status = 0

        _mmc = MysqlMgdConn(global_objects["metricstore"])
        _mmc.initialize_metric_store(_username)
        
        _msg = "The Metric Store of the kind \"Mysql\" was successfully initialized "
        _msg += "on node: " + str(global_objects["metricstore"]["host"]) + " " + _protocol + " port " + str(_hostport)
        cbdebug(_msg)
        _status = 0
            
        return _status, _msg

    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except NetworkException as obj :
        _msg = "A Metric Store of the kind \"Mysql\" on node "
        _msg += _hostname + ", " + _protocol + " port " + str(_hostport)
        _msg += ", database id \"" + str(_databaseid) + "\" seems to be down: "
        _msg += str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except MetricStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except Exception as e :
        for line in traceback.format_exc().splitlines() :
            cberr(line, True)
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

def rsync_filestore_setup(global_objects, operation = "check") :
    '''
    TBD
    '''
    _hostname = global_objects["filestore"]["hostname"]
    _protocol = global_objects["filestore"]["protocol"]
    _username = global_objects["filestore"]["username"]
    _port = global_objects["filestore"]["port"]
    _usage = global_objects["filestore"]["usage"].lower()
    _base_dir = global_objects["space"]["base_dir"]
    _stores_wk_dir = global_objects["space"]["stores_working_dir"]
    _log_dir = global_objects["space"]["log_dir"]

    try :
        _name, _ip = hostname2ip(_hostname)        
        
        if operation == "check" :

            if _usage == "shared" :

                _hostport = int(global_objects["filestore"]["port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "root")
                    _rsync_pid = _proc_man.get_pid_from_cmdline("rsync --daemon")
    
                    _cmd = "rsync --daemon"

                    if not _rsync_pid :
                        _msg = "Unable to detect a shared rsync server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print(_msg)
                        exit(8)

            else :
                _usage = "private"

                _proc_man =  ProcessManagement(username = _username)
                
                _config_file_fn = _stores_wk_dir + '/' + _username + "_rsync.conf"
                _cmd = "rsync --daemon --config " + _config_file_fn

                if not access(_config_file_fn, F_OK) :
                    # File was deleted, but the rsync process is still dangling
                    _proc_man.run_os_command("sudo pkill -9 -f " + _config_file_fn)

                _rsync_pid = _proc_man.get_pid_from_cmdline(_cmd)

                if not _rsync_pid :

                    _proc_man.run_os_command("sudo rm -rf " + _stores_wk_dir + '/' + _username + "_rsyncd.pid")
                    
                    _hostport = int(global_objects["filestore"]["port"])
                    
                    _config_file_contents = global_objects["filestore"]["config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("DOLLAR", '$')
                    _config_file_contents = _config_file_contents.replace("REPLEQUAL", '=')                    
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLLOGDIR", _log_dir)
                    _config_file_contents = _config_file_contents.replace("REPLUSERU", _username + '_')
                    _config_file_contents = _config_file_contents.replace("REPLUSER", _username)                    
                    _config_file_contents = _config_file_contents.replace("REPLBASEDIR", _base_dir)
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])                                         
                    _config_file_contents = _config_file_contents.replace(';','\n')
                    _config_file_contents = _config_file_contents.replace("--", ';')

                    _config_file_fn = _stores_wk_dir + '/' + _username + "_rsync.conf"
                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()
                    
                    _rsync_pid = _proc_man.start_daemon("sudo " + _cmd)

                    if not _rsync_pid :
                        _msg = "Unable to detect a private rsyslog server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"
                        print(_msg)
                        exit(8)

                else :
                    _config_file_fd = open(_config_file_fn, 'r')
                    _config_file_contents = _config_file_fd.readlines()
                    _config_file_fd.close()

                    for _line in _config_file_contents :
                        if _line.count("port=") :
                            global_objects["filestore"]["port"] = _line.split('=')[1]
                            _hostport = int(global_objects["filestore"]["port"])
                            break

        _nh_conn = Nethashget(_hostname)
        
        _nh_conn.nmap(_hostport, _protocol)
        _msg = "A File Store of the kind \"rsync\" (" + _usage + ") "
        _msg += "on node " + _hostname + ", " + _protocol
        _msg += " port " + str(_hostport) + " seems to be running."
        cbdebug(_msg)
        _status = 0
        return _status, _msg
    
    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
        
    except NetworkException as obj :
        _msg = "Rsync File Store network error: " + str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except Exception as e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

'''
Hard resets delete data from Mongo, which is bad.
Soft reset should be the default for regular usage,
so data is not lost.
''' 
    
def reset(global_objects, soft = True, cloud_name = None) :
    '''
    TBD
    '''
    try :

        _stores_wk_dir = global_objects["space"]["stores_working_dir"]
        _log_dir = global_objects["space"]["log_dir"]
        _username = global_objects["space"]["username"]
        _logstore_username = global_objects["logstore"]["username"]
        _filestore_username = global_objects["filestore"]["username"]
        
        _filestore_config_file_fn = _stores_wk_dir + '/' + _filestore_username + "_rsync.conf"
            
        _msg = "    Killing all processes..."
        print(_msg, end=' ')
        _proc_man =  ProcessManagement()
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f cbact")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f cloud-api")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f cloud-gui")        
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f ai-")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f vm-")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f submit-")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f capture-")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f gmetad.py")
        _proc_man.run_os_command("pkill -9 -u " + _username + " -f gtkCBUI_")
        print("done")

        _proc_man.run_os_command("screen -wipe")

        _proc_man.run_os_command("rm -rf " + global_objects["space"]["generated_configurations_dir"] + '/' + _username + "_cb_lastcloudrc")
        _proc_man.run_os_command("rm -rf /tmp/restart_cb*" + global_objects["logstore"]["username"] + '*')
        _proc_man.run_os_command("rm -rf /tmp/" + _username + "_*-*-*-*-*_avg_acc")
        
        _msg = "    Flushing Object Store..." 
        print(_msg, end=' ')
        _rmc = RedisMgdConn(global_objects["objectstore"])

        '''
        If and only if the object store is being shared and a default 'STARTUP_CLOUD' or cloud on
        the command line has been provided,
        then we can selectively flush the database
        instead of wholly dropping it.
        '''
        if global_objects["objectstore"]["usage"].lower() == "private" :
            # Backwards-compatible behavior
            cloud_name = None
        _rmc.flush_object_store(cloud_name)

        print("done")

        _msg = "    Flushing Log Store..."
        print(_msg, end=' ')
        if global_objects["logstore"]["usage"].lower() != "shared" :
            _proc_man.run_os_command("pkill -9 -u " + _logstore_username + " -f rsyslogd")
        _file_list = []
        _file_list.append("operations.log")
        _file_list.append("report.log")
        _file_list.append("submmiter.log")
        _file_list.append("loadmanager.log")
        _file_list.append("gui.log")
        _file_list.append("remotescripts.log")
        _file_list.append("messages.log")            
        _file_list.append("monitor.log")
        _file_list.append("subscribe.log")

        for _fn in  _file_list :
            if global_objects["logstore"]["usage"].lower() != "shared" :
                _proc_man.run_os_command("rm -rf " + _log_dir + '/' + _logstore_username + '_' + _fn)
            _proc_man.run_os_command("touch " + _log_dir + '/' + _logstore_username + '_' + _fn)
        _status, _msg = syslog_logstore_setup(global_objects, "check")
        
        global_objects["logstore"]["just_restarted"] = True
        
        print("done")
        
        #_msg = "Flushing File Store..."
        #print _msg,
        #_proc_man.run_os_command("sudo pkill -9 -u root -f \"rsync --daemon --config " + _filestore_config_file_fn +"\"", raise_exception = False)
        #_proc_man.run_os_command("sudo rm -rf " + _stores_wk_dir + '/' + _filestore_username + "_rsyncd.pid")

        #_status, _msg = rsync_filestore_setup(global_objects, "check")
        #print "done"
        
        if not soft :
            _msg = "    Flushing Metric Store..."
            print(_msg, end=' ')
            _mmc = load_metricstore_adapter(global_objects["metricstore"])
            _mmc.flush_metric_store(global_objects["mon_defaults"]["username"])
            print("done")

        print('\n')                        
        _msg = ""
        _status = 0

    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except MetricStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except MetricStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except RedisMgdConn.ObjectStoreMgdConnException as obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except Exception as e :
        _status = 23
        _msg = str(e)
    
    finally :
        return _status, _msg

def pre_check_port(hostname, hostport, protocol) :
    '''
    TBD
    '''
    _status = 100
    _msg = "An error has occurred, but no error message was captured"

    try :
        _nh_conn = Nethashget(hostname)

        _nh_conn.nmap(hostport, protocol)
        return True

    except NetworkException as obj :
        return False
