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

"""
    Library functions to allow VMs to perform operations on Object and Metric
    stores remotely

    @author: Michael R. Hines, Marcio A. Silva

"""
from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, \
INFO, WARN, CRITICAL
from logging.handlers import logging, SysLogHandler, RotatingFileHandler
from time import time, sleep, mktime
from datetime import datetime
from sys import path, argv, stdout
from subprocess import Popen, PIPE, STDOUT
from json import dumps,loads
from hashlib import sha1
from base64 import b64encode

import os
import fnmatch
import socket
import re
import urllib

#for _path, _dirs, _files in os.walk(os.path.abspath(path[0])):
#    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
#        path.append(_path.replace("/lib/auxiliary",''))
#        break

#import scripts.common.et.ElementTree as ET

cwd = (re.compile(".*\/").search(os.path.realpath(__file__)).group(0))

from lib.auxiliary.code_instrumentation import VerbosityFilter, MsgFilter
from lib.auxiliary.code_instrumentation import cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import makeTimestamp

class NetworkException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status

class Nethashget :
    '''
    TBD
    '''
    def __init__(self, hostname, port = None) :
        self.hostname = hostname
        if port :
            self.port = int(port)
        else :
            self.port = None
        self.socket = None

    def connect(self) :
        '''
        TBD
        '''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, int(self.port)))

    def nmap(self, port = None, protocol = "TCP") :
        '''
        TBD
        '''
        try :
            if protocol == "TCP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif protocol == "UDP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5)
            self.socket.connect((self.hostname, self.port if port is None else port))
            return True
        
        except socket.error, msg :
            _msg = "Unable to connect to " + protocol + " port " + str(port)
            _msg += " on host " + self.hostname + ": " + str(msg)
            print(_msg)
            raise NetworkException(str(_msg), "1")
            self.socket.close()
            self.socket = None

    def check_port(self, port = None, protocol = "TCP") :
        '''
        TBD
        '''
        try :
            if protocol == "TCP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif protocol == "UDP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5)
            self.socket.connect((self.hostname, self.port if port is None else port))
            return True

        except socket.error, msg :
            _msg = "Unable to connect to " + protocol + " port " + str(port)
            _msg += " on host " + self.hostname + ": " + str(msg)
            print(_msg)
            return False
            self.socket.close()
            self.socket = None

def nmap(port) :
    '''
    TBD
    '''
    if len(argv) < 3 :
        print ("Need ip address and collection frequency")
        exit(1)

    app = Nethashget(argv[2])

    _msg = "Application on " + argv[2] + ":" + str(port) + " is not available"

    try : 
        if app.nmap(port) is False :
            print(_msg)
            exit(1)
    except NetworkException, msg :
        print(_msg)
        exit(1)
    return argv[1], argv[2]

def refresh_os_cache() :
    '''
    TBD
    '''
    _cmd = "source " + cwd + "/cb_common.sh"

    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (_output_stdout, _output_stderr) = proc_h.communicate()

    if proc_h.returncode > 0 :
        return _output_stderr
    else :
        return _output_stdout.strip()

def get_my_ip() :
    '''
    TBD
    '''
    _cmd = "ip -o addr show $(ip route | grep default"
    _cmd += " | grep -oE \"dev [a-z]+[0-9]+\" | sed \"s/dev //g\") "
    _cmd += "| grep -Eo \"[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*\" | grep -v 255"

    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (_output_stdout, _output_stderr) = proc_h.communicate()

    if proc_h.returncode > 0 :
        return _output_stderr
    else :
        return _output_stdout.strip()
    
def get_uuid_from_ip(ipaddr) :
    '''
    TBD
    '''
    
    try :
        _fmsg = ""

        _uuid = None

        _ipaddr = ipaddr.split('-')[0]

        _fn = "/etc/hosts"
        _fh = open(_fn, "r")
        _fc = _fh.readlines()
        _fh.close()

        for _line in _fc :
            _line = _line.strip()
            if _line.count(_ipaddr) and not _line.count("just_for_lost") :
                _line = _line.split(",")
                _uuid = _line[-1]
            else :
                True
        
        _status = 0

    except IOError, msg :
        _status = 10
        _fmsg = str(msg) 
    
    except OSError, msg :
        _status = 20
        _fmsg = str(msg) 
    
    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "Failure while getting uuid from IP: " + _fmsg
            print _msg
            exit(2)
        else :
            return _uuid

def get_stores_parms() :
    '''
    TBD
    '''
    try :
        _status = 100
        _fmsg = ""
        _home = os.environ["HOME"]        
        _from_file = False
        _fn = _home + "/cb_os_parameters.txt"
        _fh = open(_fn, "r")
        _fc = _fh.readlines()
        _fh.close()

        _my_uuid = False
        _oscp = {}
        for _line in _fc :
            _line = _line.strip()
            if _line.count("#OSKN-") :
                _oscp["kind"] = _line[6:]
            elif _line.count("#OSHN-") :
                _oscp["host"] = _line[6:]
            elif _line.count("#OSPN-") :
                _oscp["port"] = _line[6:]
            elif _line.count("#OSDN-") :
                _oscp["dbid"] = _line[6:]
            elif _line.count("#OSTO-") :
                _oscp["timout"] = _line[6:]
            elif _line.count("#OSCN-") :
                _oscp["cloud_name"] = _line[6:]
            elif _line.count("#OSMO-") :
                _oscp["mode"] = _line[6:]
            elif _line.count("#VMUUID-") :
                _my_uuid = _line[8:]                
            elif _line.count("#OSOI-") :
                _oscp["experiment_inst"] = _line[6:].replace(':' + _oscp["cloud_name"],'')
                _oscp["pid"] = _oscp["experiment_inst"]
            else :
                True

        _oscp["protocol"] = "TCP"
        _oscp["redis_conn"] = False

        _home = os.environ["HOME"]        
        _fn = _home + "/cb_os_cache.txt"
        _fh = open(_fn, "r")
        _fc = _fh.readlines()
        _fh.close()

        use_vpn = False
        for _line in _fc :
            _line = _line.strip()
            if _line.count("use_vpn_ip") and _line.count("True") :
                use_vpn = True
                break

        _mscp = {}
        for _line in _fc :
            _line = _line.strip()
            if _line.count("metricstore") :
                _line = _line.split("metricstore")
                _line = _line[1].split()
                _mscp[_line[0]] = _line[1]
            elif _line.count("time experiment_id") :
                _line = _line.split("experiment_id")
                _mscp["experiment_id"] = _line[1].strip()
            else :
                True

        _mscp["mongodb_conn"] = False

        _lscp = {}
        _lscp["hostname"] = None
        _lscp["port"] = None

        for _line in _fc :
            _line = _line.strip()
            if _line.count("logstore") :
                _line = _line.split("logstore")
                _line = _line[1].split()
                _lscp[_line[0]] = _line[1]
            elif _line.count("metric_aggregator_ip") :
                _line = _line.split("metric_aggregator_ip")
                _lscp["metric_aggregator_ip"] = _line[1]
            else :
                True

        if use_vpn :
            for _line in _fc :
                _line = _line.strip()
                if _line.count("server_bootstrap") :
                    _mscp["host"] = _line.split("server_bootstrap")[1].strip()
                    _lscp["hostname"] = _mscp["host"]
                    break

        if _oscp["mode"] == "scalable" :
            _lscp["hostname"] = _lscp["metric_aggregator_ip"]

        _status = 0

    except IOError, msg :
        _status = 10
        _fmsg = str(msg) 
    
    except OSError, msg :
        _status = 20
        _fmsg = str(msg) 

    except Exception, e:
        status = 30
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Failure while getting Object Store parameters: " + _fmsg
            print _msg
            exit(2)
        else :
            _msg = "Object Store parameters obtained successfully."
            return _my_uuid, _oscp, _mscp, _lscp

def setup_syslog(verbosity, quiet = False, logdest = "syslog") :
    '''
    TBD
    '''
    try :

        _fmsg = ""
        _status = 100
        
        _my_uuid, _oscp, _mscp, _lscp = get_stores_parms()
        
        # HACK ALERT - A very crude "syslog facility selector"
        _syslog_selector = {}
        _syslog_selector["16"] = SysLogHandler.LOG_LOCAL0
        _syslog_selector["17"] = SysLogHandler.LOG_LOCAL1
        _syslog_selector["18"] = SysLogHandler.LOG_LOCAL2
        _syslog_selector["19"] = SysLogHandler.LOG_LOCAL3
        _syslog_selector["20"] = SysLogHandler.LOG_LOCAL4
        _syslog_selector["21"] = SysLogHandler.LOG_LOCAL5
        _syslog_selector["22"] = SysLogHandler.LOG_LOCAL6
        _syslog_selector["23"] = SysLogHandler.LOG_LOCAL7
  
        _verbosity = int(verbosity)

        logger = getLogger()

        # Reset the logging handlers
        while len(logger.handlers) != 0 :
            logger.removeHandler(logger.handlers[0])

        if logdest == "console" or (not _lscp["hostname"] or not _lscp["port"]) :
            hdlr = StreamHandler(stdout)
        else :
            _facility = int(21)

            if _facility > 23 or _facility < 16 :
                _facility = 23

            hdlr = SysLogHandler(address = (_lscp["hostname"], \
                                            int(_lscp["port"])), \
                                            facility=_syslog_selector[str(_facility)])

        formatter = Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

        if _verbosity :
            if int(_verbosity) >= 6 :
                logger.setLevel(DEBUG)
            elif int(_verbosity) >= 5 :
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(_verbosity) >= 4 :
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(_verbosity) >= 3 :
                # Filter out gmetad logging statements
                hdlr.addFilter(VerbosityFilter("gmetad"))
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from the "remote"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("remote"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                hdlr.addFilter(MsgFilter("Exit point"))
                hdlr.addFilter(MsgFilter("Entry point"))
                logger.setLevel(DEBUG)
            elif int(_verbosity) >= 2 :
                # Filter out gmetad logging statements
                hdlr.addFilter(VerbosityFilter("gmetad"))
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from all modules in the
                # "collectors" subdirectory.
                hdlr.addFilter(VerbosityFilter("collectors"))
                # Used to filter out all function calls from the "remote"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("remote"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(_verbosity) == 1 :
                # Filter out gmetad logging statements
                hdlr.addFilter(VerbosityFilter("gmetad"))
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                # Used to filter out all function calls from all modules in the
                # "collectors" subdirectory.
                hdlr.addFilter(VerbosityFilter("collectors"))
                # Used to filter out all function calls from the "remote"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("remote"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("clouds"))
                logger.setLevel(DEBUG)
        else :
            logger.setLevel(INFO)

        if quiet :
            logger.setLevel(ERROR)

        _status = 0

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Failure while setting up syslog channel: " + _fmsg
            print _msg
            exit(2)
        else :
            _msg = "Syslog channel set up successfully."
            return True

def get_ms_conn(mscp = None, cn = None) :
    '''
    TBD
    '''
    try :
        _status = 100
        _fmsg = ""
        _my_uuid, _oscp, _mscp, _lscp = get_stores_parms()

        _ms_adapter = __import__("lib.stores." + _mscp["kind"] + "_datastore_adapter", \
                                 fromlist=[_mscp["kind"].capitalize() + "MgdConn"])

        _ms_conn_class = getattr(_ms_adapter, _mscp["kind"].capitalize() + "MgdConn")
        
        _msci = _ms_conn_class(_mscp)
        
        _status = 0

    except ImportError, msg :
        _status = 20
        _fmsg = str(msg)

    except AttributeError, msg :
        _status = 20
        _fmsg = str(msg)
    
    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "Failure while setting up metric store adapter: " + _fmsg
            print _msg
            exit(2)
        else :
            _msg = "Metric store adapter set up successfully."
            return _msci, _my_uuid, _mscp["experiment_id"], _mscp["username"]

def get_os_conn(oscp = None) :
    '''
    TBD
    '''
    try :
        _fmsg = ""

        if not oscp :
            _my_uuid, _oscp, _mscp, _lscp = get_stores_parms()
        else :
            _oscp = oscp

        _os_adapter = __import__("lib.stores." + _oscp["kind"] + "_datastore_adapter", \
                                 fromlist=[_oscp["kind"].capitalize() + "MgdConn"])

        _os_conn_class = getattr(_os_adapter, _oscp["kind"].capitalize() + "MgdConn")
        
        _cloud_name = _oscp["cloud_name"]

        _osci = _os_conn_class(_oscp)
        
        _status = 0

    except ImportError, msg :
        _status = 20
        _fmsg = str(msg)

    except AttributeError, msg :
        _status = 20
        _fmsg = str(msg)
    
    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "Failure while setting up object store adapter: " + _fmsg
            print _msg
            exit(2)
        else :
            _msg = "Object store adapter set up successfully."
            return _osci, _my_uuid, _cloud_name

def is_number(val) :
    '''
    TBD
    '''
    try:
        _val = float(val)
        if _val == 0.0 :
            return True
        else :
            return _val
    
    except ValueError:
        return False

def update_avg_acc_max_min(metrics_dict, uuid, username) :
    '''
    TBD
    '''

    _fn = "/tmp/" + username + '_' + uuid + "_avg_acc"

    _acc_dict = {}

    if os.access(_fn, os.F_OK) :
        _fh = open(_fn, "r")
        _fc = _fh.read()
        _fh.close()

        _acc_dict = loads(_fc)

#    _extra_metrics = {}

    _curr_load_id = float(metrics_dict["app_load_id"]["val"])
    
    for _metric in metrics_dict.keys() :

        if _metric.count("app_") and not _metric.count("load_id") :
            if is_number(metrics_dict[_metric]["val"]) :
                
                if not _metric in _acc_dict :
                    _acc_dict[_metric] = {}
                    _acc_dict[_metric]["acc"] = 0
                    _acc_dict[_metric]["max"] = -1
                    _acc_dict[_metric]["min"] = 100000000000000000
                                                                                                    
                _old_value = float(_acc_dict[_metric]["acc"])
                _old_max = float(_acc_dict[_metric]["max"])
                _old_min = float(_acc_dict[_metric]["min"])
                                
                if _metric.count("_errors") :
#                    _mkey = _metric.replace("app_", "app_acc_")
#                    _extra_metrics[_mkey] = {}
#                    _extra_metrics[_mkey]["units"] = metrics_dict[_metric]["units"]
                                                        
                    _curr_err = float(metrics_dict[_metric]["val"])
                    
                    if _curr_err > 1.0 :
                        _curr_err = 1.0

                    if _curr_err > _old_max :
                        _acc_dict[_metric]["max"] = _curr_err

                    if _curr_err < _old_min :
                        _acc_dict[_metric]["min"] = _curr_err

                    _new_val = _old_value + _curr_err
                    _acc_dict[_metric]["acc"] = _new_val                    
#                    _extra_metrics[_mkey]["val"] = _new_val

                    metrics_dict[_metric]["acc"] = _acc_dict[_metric]["acc"]

                else :

#                    _mkey = _metric.replace("app_", "app_avg_")
#                    _extra_metrics[_mkey] = {}
#                    _extra_metrics[_mkey]["units"] = metrics_dict[_metric]["units"]

                    _curr_val = float(metrics_dict[_metric]["val"])

                    if _curr_val > _old_max :
                        _acc_dict[_metric]["max"] = _curr_val

                    if _curr_val < _old_min :
                        _acc_dict[_metric]["min"] = _curr_val
                        
                    _new_val = _old_value + _curr_val
                    _acc_dict[_metric]["acc"] = _new_val                     

#                    _extra_metrics[_mkey]["val"] = _new_val  / _curr_load_id
                    metrics_dict[_metric]["avg"] = _acc_dict[_metric]["acc"] / _curr_load_id

                    metrics_dict[_metric]["max"] = _acc_dict[_metric]["max"]
                    metrics_dict[_metric]["min"] = _acc_dict[_metric]["min"]

            else :
                if _metric.count("app_sla_runtime") :

                    if not _metric in _acc_dict :
                        _acc_dict[_metric] = {}
                        _acc_dict[_metric]["acc"] = 0
                        _acc_dict[_metric]["max"] = -1
                        _acc_dict[_metric]["min"] = 100000000000000000
                                                                                                        
                    _old_value = float(_acc_dict[_metric]["acc"])
                    _old_max = float(_acc_dict[_metric]["max"])
                    _old_min = float(_acc_dict[_metric]["min"])
                        
                    if metrics_dict[_metric]["val"] == "violated" :
                        _curr_err = 1.0
                    else :
                        _curr_err = 0.0
                                                
#                    _mkey = "app_sla_runtime_errors"
#                    _extra_metrics[_mkey] = {}
#                    _extra_metrics[_mkey]["units"] = "num"

                    _new_val = _old_value + _curr_err
                    _acc_dict[_metric]["acc"] = _new_val                      
#                    _extra_metrics[_mkey]["val"] = _new_val
                    metrics_dict[_metric]["acc"] = _acc_dict[_metric]["acc"]                  

#    metrics_dict.update(_extra_metrics)

    _fc = dumps(_acc_dict, indent = 4)
    _fh = open(_fn, "w")
    _fh.write(_fc)
    _fh.close()

    return True

def unit_convert(convstr, unit, value) :
    '''
    TBD
    '''
    if convstr :
        _conversion_dict = {}
        _conversion_dict["s"] = { "s": 1, "ms": 1000, "us": 1000000, "ns": 1000000000}
        _conversion_dict["ms"] = { "s": 1/float(1000), "ms": 1, "us": 1000, "ns": 1000000}
        _conversion_dict["us"] = { "s": 1/float(1000000), "ms": 1/float(1000), "us": 1, "ns": 1000}
        _conversion_dict["ns"] = { "s": 1/float(1000000000), "ms": 1/float(1000000), "us": 1/float(1000), "ns": 1}
    
        _source, _destination = convstr.split("_to_")

        if unit == _source :        
            if _source in _conversion_dict :
                if _destination in _conversion_dict[_source] :
                    try :
                        unit = _destination
                        value = float(value) * float(_conversion_dict[_source][_destination])
                    except :
                        pass
            
    return unit, value
                                                
def report_app_metrics(metriclist, sla_targets_list, ms_conn = "auto", \
                       os_conn = "auto", reset_syslog = True, force_conversion = None) :

    # When using the VPN, it's possible that the
    # object store's address for different services
    # has changed. We may have to repopulate some values.
    refresh_os_cache()

    if ms_conn == "auto" :
        _msci, _my_uuid, _expid, _username = get_ms_conn()
    else :
        _msci = ms_conn[0]
        _my_uuid = ms_conn[1]
        _expid = ms_conn[2]
        _username = ms_conn[3]
        
    if os_conn == "auto" :
        _osci, _my_uuid, _cloud_name = get_os_conn()
    else :
        _osci = os_conn[0]
        _my_uuid = os_conn[1]
        _cloud_name = os_conn[2]

    if reset_syslog :                
        setup_syslog(1)

    try :
        _metrics_dict = {}
        _sla_targets_dict = {}
        _reported_metrics_dict = {}

        _msg = "SLA violation verification"
        cbdebug(_msg)

        for _sla_target in sla_targets_list.split() :
            _sla_target = _sla_target.split(':')
            if len(_sla_target) == 2 :
                if len(_sla_target[1]) :
                    _key = _sla_target[0].replace('sla_runtime_target_','')                
                    _sla_targets_dict[_key] = _sla_target[1]

        _sla_status = "ok"
        for _metric in metriclist.split() :
            _metric = _metric.split(':')
            if len(_metric[1]) :
                _metric[2], _metric[1] = unit_convert(force_conversion, _metric[2], _metric[1])
                _metrics_dict["app_"  + _metric[0]] = {}
                _metrics_dict["app_"  + _metric[0]]["val"] = _metric[1]
                _metrics_dict["app_"  + _metric[0]]["units"] = _metric[2]

                if _metric[0] in _sla_targets_dict :

                    _sla_target, _condition = _sla_targets_dict[_metric[0]].split('-')

                    if len(str(_metric[1])) :

                        _metrics_dict["app_sla_runtime"] = {}
                        _metrics_dict["app_sla_runtime"]["units"] = ' '
                        
                        if _condition == "gt" :
                            if float(_metric[1]) >= float(_sla_target) :
                                True
                            else :
                                _sla_status = "violated"
                                cbwarn("SLA VIOLATION!!!!!")

                        if _condition == "lt" :
                            if float(_metric[1]) <= float(_sla_target) :
                                True
                            else :
                                _sla_status = "violated"
                                cbwarn("SLA VIOLATION!!!!!")

        if "app_sla_runtime" in _metrics_dict :
            _metrics_dict["app_sla_runtime"]["val"] = _sla_status
    
        _metrics_dict["time"] = _metrics_dict["time"] = int(time())
        _metrics_dict["time_cbtool"] = _osci.get_remote_time()[0]
        _metrics_dict["time_h"] = makeTimestamp() 
        _metrics_dict["time_cbtool_h"] = makeTimestamp(_metrics_dict["time_cbtool"])
        _metrics_dict["expid"] = _expid
        _metrics_dict["uuid"] = _my_uuid
        
        obj_attr_list = False

        _msg = "SLA violation status update"
        cbdebug(_msg)
        
        for _m in [ "sla_runtime", "errors" ] :
            
            if "app_" + _m in _metrics_dict :
                
                obj_attr_list = _osci.get_object(_cloud_name, "VM", False, _my_uuid, False)

                if "sticky_" + _m in obj_attr_list :
                    _previous_m = obj_attr_list["sticky_" + _m]
                    _current_m = _previous_m
                else :
                    _previous_m = obj_attr_list[_m]
                    _current_m = _metrics_dict["app_" + _m]["val"]

                if is_number(_previous_m) :
                    if float(_previous_m) > 0 :
                        _previous_m = "yes"
                    else :
                        _previous_m = "no"
    
                if is_number(_current_m) :
                    if float(_current_m) > 0 :
                        _current_m = "yes"
                    else :
                        _current_m = "no"

                _username = obj_attr_list["username"]
                
                _xmsg = '.'
                if str(obj_attr_list["sticky_app_status"]).lower() == "true" :                    
                    if _current_m == "violated" or _current_m == "yes" :
                        _xmsg = " (Due to \"application status stickyness)."
                        _osci.update_object_attribute(_cloud_name, \
                                                      "VM", \
                                                      _my_uuid, \
                                                      False, \
                                                      "sticky_" + _m, \
                                                      _current_m)

                if _previous_m == _current_m :
                    _msg = "Previous " + _m + " (\"" + _previous_m
                    _msg += "\") and New (\"" + _current_m + "\")"
                    _msg += " are the same. No updates needed" + _xmsg
                    cbdebug(_msg)
                else :
                    _msg = "Previous " + _m + " status (\"" + _previous_m
                    _msg += "\") and New (\"" + _current_m + "\")"
                    _msg += " are different. Updating attributes and views on the"
                    _msg += " Metric Store"
                    cbdebug(_msg)
                    _osci.update_object_attribute(_cloud_name, \
                                                  "VM", \
                                                  _my_uuid, \
                                                  False, \
                                                  _m, \
                                                  _current_m)

                    obj_attr_list[_m] = _previous_m
                    _osci.remove_from_view(_cloud_name, "VM", obj_attr_list, "BY" + _m.upper())
                                        
                    obj_attr_list[_m] = _current_m
                    _osci.add_to_view(_cloud_name, "VM", obj_attr_list, "BY" + _m.upper(), "arrival")

        _msg = "Determine average,min,max"
        cbdebug(_msg)
        
        update_avg_acc_max_min(_metrics_dict, _my_uuid, _username)

        _msg = "Report metrics"
        cbdebug(_msg)

        if "app_load_id" in _metrics_dict and _metrics_dict["app_load_id"]["val"] == "1" :
            _new_reported_metrics_dict = {}
            for _key in _metrics_dict.keys() :
                if not _key.count("time") and not _key.count("uuid") and not _key.count("time_h") :
                    _new_reported_metrics_dict[_key] = "1"
            _new_reported_metrics_dict["expid"] = _expid
            _new_reported_metrics_dict["_id"] = b64encode(sha1(_expid).digest())
            _reported_metrics_dict = \
            _msci.find_document("reported_runtime_app_VM_metric_names_" + \
                                _username, {"_id" : _new_reported_metrics_dict["_id"]})

            if not _reported_metrics_dict :
                _reported_metrics_dict = {}
                
            _reported_metrics_dict.update(_new_reported_metrics_dict)

        _msci.add_document("runtime_app_VM_" + _username, _metrics_dict)
        _msg = "Application Metrics reported successfully. Data package sent was: \"" 
        _msg += str(_metrics_dict) + "\""
        cbdebug(_msg)

        _metrics_dict["_id"] = _metrics_dict["uuid"]
        _msci.update_document("latest_runtime_app_VM_" + _username, _metrics_dict)
        _msg = "Latest app performance data updated successfully"
        cbdebug(_msg)

        if len(_reported_metrics_dict) :
            _msci.update_document("reported_runtime_app_VM_metric_names_" + _username, _reported_metrics_dict)
            _msg = "Reported runtime application metric names collection "
            _msg += "updated successfully. Data package sent was: \""
            _msg += str(_reported_metrics_dict) + "\""
            cbdebug(_msg)

        if str(obj_attr_list["notification"]).lower() != "false" :
            if obj_attr_list["notification_channel"].lower() == "auto" :
                _channel = "APPLICATION"
            else :
                _channel = obj_attr_list["notification_channel"]

            _message = "VM object " + _my_uuid + " (" + obj_attr_list["name"] 
            _message += ") submitted a new set of application metrics"

            _osci.publish_message(obj_attr_list["cloud_name"], "VM", _channel, _message, \
                                 1, \
                                 float(obj_attr_list["timeout"]))

        _status = 0
        
    except _msci.MetricStoreMgdConnException, obj :
        _status = obj.status
        _fmsg = str(obj.msg)

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Application performance metrics record failure: " + _fmsg
            cberr(_msg)
            return False
        else :
            return True

#def wget(url) :
#    '''
#    TBD
#    '''
#    try :
#        handle = urllib.urlopen(url)
#        if handle is None :
#            print("Url " + url + " seems unavailable")
#            return None
#        tree = ET.parse(handle)
#        if tree is None :
#            print("Tree could not be built from : " + url)
#            return None
#        return tree
#    except Exception, msg :
#        print(str(msg))
#        return None

def collect_db_one(command) :
    '''
    TBD
    '''
    p = Popen(command, shell=True, stdout=PIPE)
    output = None 
    err = ""
    for line in p.stdout :
        if "Transactions" in line :
            output = line
        err += line    
    p.wait()
    if output is None :
        print("ERROR collecting from database: \n" + err)
        return 0

    result = re.compile('.*Transactions: ([0-9]+)').match(output)
    return int(result.group(1))

def collect_db(role, dbtype, port, auth, query) :
    '''
    TBD
    '''
    delay, ip = nmap(port) 
    rate = 0
    latency = 0
    
    command = "java -Xmx10m -Xms10m -jar ~/sdc.jar " \
        + dbtype + " " + ip + " " + str(port) + " " + auth + " \"" + query + "\""
    
    count1 = collect_db_one(command)
    time1 = time()
    sleep(float(10))
    count2 = collect_db_one(command)
    time2 = time()
    
    if count1 > 0 and count2 > 0 and count2 > count1:
        count = count2 - count1
        secs = time2 - time1
        rate = int(count / secs)
        latency = 0
    report_app_metrics(role, rate, latency)

def collect_apache(role, grep) :
    '''
    TBD
    '''
    delay, ip = nmap(80)
    rate = 0
    latency = 0
    url = "http://" + ip + "/tm?" + grep
    print("Requesting URL: " + url)

    handle = urllib.urlopen(url)

    if handle is None :
        print("Url " + url + " seems unavailable")
        return (0, 0)

    for line in handle.readlines() :
        if "AVERAGE" in line :
            latency = int(re.compile('.*<td>([0-9]+)').match(line).group(1))
            continue
        if "HITS" in line :
            rate = int(re.compile('.*<td>([0-9]+)').match(line).group(1))
            rate /= int(delay)
            continue
        
    urllib.urlopen("http://" + ip + "/tm?reset").read()
    report_app_metrics(role, rate, latency)

def et_find(path, tree) :
    '''
    TBD
    '''
    elems = tree.find(path)
    if elems is None :
        print("path " + path + " not found")
    return elems

def collect_was(role, port, ejb_name) :
    '''
    TBD
    '''
    delay, ip = nmap(port)
    rate = 0
    latency = 0
    
    path= "Node/Server/Stat/Stat[@name='" + ejb_name + "']"
    url = "http://" + ip + ":" + str(port) + "/wasPerfTool/servlet/perfservlet?module=beanModule"
    tree1 = wget(url)
    if tree1 is None : return (0, 0)
    sleep(5)
    tree2 = wget(url)
    if tree2 is None : return (0, 0)

    countpath = path + "/CountStatistic[@ID='11']"
    totalpath = path + "/TimeStatistic[@ID='12']"

    count1 = et_find(countpath, tree1)
    total1 = et_find(totalpath, tree1)
    count2 = et_find(countpath, tree2)
    total2 = et_find(totalpath, tree2)

    if count1 is None or count2 is None or total1 is None or total2 is None: 
        return (0, 0)
    
    count = int(count2.attrib['count']) - int(count1.attrib['count'])

    if count > 0 :
        total = int(total2.attrib['totalTime']) - int(total1.attrib['totalTime'])
        if total > 0 :
            latency = total / count
            rate = count / 5 

    report_app_metrics(role, rate, latency)
