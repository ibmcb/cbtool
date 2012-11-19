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
    Created on Aug 27, 2011

    Initial Setup for all Cloudbench stores

    @author: Marcio Silva
'''

from os import mkdir, listdir, path
from shutil import rmtree
from time import sleep

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.process_management import ProcessManagement
from lib.remote.network_functions import Nethashget, NetworkException 
from redis_datastore_adapter import RedisMgdConn
from mongodb_datastore_adapter import MongodbMgdConn

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
                        print _msg
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = _stores_path + '/' + _username + "_redis.conf"
                _cmd = "redis-server " + _config_file_fn

                _proc_man =  ProcessManagement(username = _username)
                
                _redis_pid = _proc_man.get_pid_from_cmdline("redis-server")      

                if not _redis_pid :
                    global_objects["objectstore"]["port"] = _proc_man.get_free_port(global_objects["objectstore"]["port"], protocol = "tcp")
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
                        print _msg
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

            _instance_dir = global_objects["space"]["instance_dir"]

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
    
    except NetworkException, obj :
        _msg = "An Object Store of the kind \"Redis\" on node "
        _msg += _hostname + ", " + _protocol + " port " + str(_hostport)
        _msg += ", database id \"" + str(_databaseid)
        _msg += "\" seems to be down: " + str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
            
    except RedisMgdConn.ObjectStoreMgdConnException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
    
    except OSError :
        _status = 10
        _msg = "Experiment directory " + _instance_dir
        _msg += " could not be removed. "
        raise StoreSetupException(_msg, 9)

    except Exception, e :
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

    try :
        if operation == "check" :

            if _usage == "shared" :

                _hostport = int(global_objects["logstore"]["port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "root")
                    _rsyslog_pid = _proc_man.get_pid_from_cmdline("rsyslogd")
    
                    _cmd = "/sbin/rsyslogd -i /var/run/syslogd.pid -c 5"
                    if not _rsyslog_pid :
                        _msg = "Unable to detect a shared rsyslog server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print _msg
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_rsyslog.conf"
                _cmd = "rsyslogd -f " + _config_file_fn + " -c 4 " + "-i " + global_objects["space"]["stores_working_dir"] + "/rsyslog.pid"

                _proc_man =  ProcessManagement(username = _username)
                _rsyslog_pid = _proc_man.get_pid_from_cmdline(_cmd)     

                if not _rsyslog_pid :
                    global_objects["logstore"]["port"] = _proc_man.get_free_port(global_objects["logstore"]["port"], protocol = "udp")
                    _hostport = int(global_objects["logstore"]["port"])
                    
                    _config_file_contents = global_objects["logstore"]["config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("DOLLAR", '$')
                    _config_file_contents = _config_file_contents.replace("RSYSLOG", "RSYSLOG_")
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])
                    _config_file_contents = _config_file_contents.replace(';','\n')
                    _config_file_contents = _config_file_contents.replace("--", ';')

                    _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_rsyslog.conf"
                    _config_file_fd = open(_config_file_fn, 'w')
                    _config_file_fd.write(_config_file_contents)
                    _config_file_fd.close()

                    _rsyslog_pid = _proc_man.start_daemon(_cmd)
             
                    if not _rsyslog_pid :
                        _msg = "Unable to detect a private rsyslog server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"
                        print _msg
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

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)
        
    except NetworkException, obj :
        _msg = "Syslog Log Store on server " + _hostname + ", " + _protocol
        _msg += " port " + str(_hostport) + " seems to be down:" + str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except Exception, e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

def mongodb_metricstore_setup(global_objects, operation = "check") :
    '''
    TBD
    '''
    _protocol = global_objects["metricstore"]["protocol"]
    _hostname = global_objects["metricstore"]["hostname"]
    _databaseid = global_objects["metricstore"]["database"]
    _timeout = float(global_objects["metricstore"]["timeout"])
    _username = global_objects["mon_defaults"]["username"]
    _usage = global_objects["metricstore"]["usage"].lower()

    try :
        if operation == "check" :

            if _usage == "shared" :          

                _hostport = int(global_objects["metricstore"]["port"])
                
                if not pre_check_port(_hostname, _hostport, _protocol) :
                    _proc_man =  ProcessManagement(username = "root")
                    _mongodb_pid = _proc_man.get_pid_from_cmdline("mongod")
    
                    _cmd = "/usr/local/bin/mongod -f /etc/mongod.conf --pidfilepath /var/run/mongod.pid"
                    if not _mongodb_pid :
                        _msg = "Unable to detect a shared MongoDB server daemon running. "
                        _msg += "Please try to start one (e.g., " + _cmd + ")"                    
                        print _msg
                        exit(8)

            else :
                _usage = "private"

                _config_file_fn = global_objects["space"]["stores_working_dir"] + '/' + _username + "_mongod.conf"
                _cmd = "mongod -f " + _config_file_fn + " --pidfilepath " + global_objects["space"]["stores_working_dir"] + "/mongod.pid"
    
                _proc_man =  ProcessManagement(username = _username)
                _mongodb_pid = _proc_man.get_pid_from_cmdline("mongod")

                if not _mongodb_pid :
                    global_objects["metricstore"]["port"] = _proc_man.get_free_port(global_objects["metricstore"]["port"], protocol = "tcp")
                    _hostport = int(global_objects["metricstore"]["port"])
                    
                    _config_file_contents = global_objects["metricstore"]["config_string"].replace('_', ' ')
                    _config_file_contents = _config_file_contents.replace("REPLPORT", str(_hostport))
                    _config_file_contents = _config_file_contents.replace("REPLSTORESWORKINGDIR", global_objects["space"]["stores_working_dir"])
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
                        print _msg
                        exit(8)

                else :
                    global_objects["metricstore"]["port"] = _proc_man.get_port_from_pid(_mongodb_pid[0])
                    _hostport = int(global_objects["metricstore"]["port"])

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
            
            _status = 0
            
        return _status, _msg

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except NetworkException, obj :
        _msg = "A Metric Store of the kind \"MongoDB\" on node "
        _msg += _hostname + ", " + _protocol + " port " + str(_hostport)
        _msg += ", database id \"" + str(_databaseid) + "\" seems to be down: "
        _msg += str(obj.msg) + '.'
        cberr(_msg)
        raise StoreSetupException(_msg, 8)

    except MongodbMgdConn.MetricStoreMgdConnException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)
        raise StoreSetupException(_msg, 9)

    except Exception, e :
        _status = 23
        _msg = str(e)
        raise StoreSetupException(_msg, 9)

def hard_reset(global_objects) :
    '''
    TBD
    '''
    try :
        _msg = "Killing all processes"
        cbdebug(_msg)
        _proc_man =  ProcessManagement()
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f cloud-")
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f ai-")
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f vm-")
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f submit-")
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f capture-")
        _proc_man.run_os_command("pkill -9 -u " + global_objects["space"]["username"] + " -f gmetad.py")
        _proc_man.run_os_command("screen -wipe")

        _msg = "Flushing Object Store" 
        cbdebug(_msg) 
        _rmc = RedisMgdConn(global_objects["objectstore"])
        _rmc.flush_object_store()

        _msg = "Flushing Metric Store"
        cbdebug(_msg)
        _mmc = MongodbMgdConn(global_objects["metricstore"])
        _mmc.flush_metric_store(global_objects["mon_defaults"]["username"])

        _msg = "Success"
        _status = 0

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except MongodbMgdConn.MetricStoreMgdConnException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except RedisMgdConn.ObjectStoreMgdConnException, obj :
        _status = str(obj.status)
        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
        _msg = str(e)
    
    finally :
        if _status :
            print _msg
            exit(_status)
        else :
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

    except NetworkException, obj :
        return False
