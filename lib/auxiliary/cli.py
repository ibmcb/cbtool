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
    Created on Aug 22, 2011

    Experiment Command Processor Command Line Interface

    @author: Marcio Silva, Michael R. Hines
'''

import os
import sys
import readline

from cmd import Cmd
from pwd import getpwuid
from sys import stdout, path
from subprocess import Popen, PIPE
from optparse import OptionParser
from re import sub, compile
from time import time
import re


from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO
from logging.handlers import logging, SysLogHandler, RotatingFileHandler
from lib.auxiliary.code_instrumentation import VerbosityFilter, MsgFilter, AntiMsgFilter, STATUS
from lib.stores.stores_initial_setup import StoreSetupException
from lib.auxiliary.data_ops import message_beautifier, dic2str
from lib.remote.process_management import ProcessManagement
from lib.operations.active_operations import ActiveObjectOperations
from lib.operations.passive_operations import PassiveObjectOperations
from lib.operations.background_operations import BackgroundObjectOperations
from lib.operations.base_operations import BaseObjectOperations
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.stores.mongodb_datastore_adapter import MongodbMgdConn
from lib.stores.redis_datastore_adapter import RedisMgdConn
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions

class CBCLI(Cmd) :

    @trace
    def __init__ (self, definitions = None) :
        '''
        TBD
        '''
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../"
        self.cld_attr_lst = {"logstore" : {}, "user-defined" : {}} # will be overriden later
        self.username = getpwuid(os.getuid())[0]
        self.pid = "TEST_" + self.username 
        history = self.path + "/.cb_history"
        self.console = None
        self.active_operations = None
        self.passive_operations = None
        self.background_operations = None
        self.attached_clouds = []
        Cmd.__init__(self)
        Cmd.prompt = "() "
        Cmd.emptyline = self.emptyline()

        _status = 100
        _msg = "An error has occurred, but no error message was captured"

        # See if the '-f' option exists
        self.setup_default_options()
        
        if self.options.debug_host is not None :
            import debug
            print str(path)
            import pydevd
            pydevd.settrace(host=self.options.debug_host)
    
        try :

            self.cld_attr_lst = {}
            _msg = "Parsing \"cloud definitions\" file....."
            print _msg,

            self.cld_attr_lst = parse_cld_defs_file(None, True, self.options.config)
            self.setup_default_options()

            oscp = self.cld_attr_lst["objectstore"].copy()
            del oscp["config_string"]
            del oscp["usage"]

            mscp = self.cld_attr_lst["metricstore"].copy()
            del mscp["config_string"]
            del mscp["usage"]

            if not os.path.exists(history) :
                _file = open(history, 'w')
                _file.write('')
                _file.close()

            readline.set_history_length(10000)
            readline.read_history_file(history) 

            self.os_func, self.ms_func, self.ls_func = \
            load_store_functions(self.cld_attr_lst)
    
            print "Checking \"Object Store\".....",        
            _status, _msg = self.os_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')
    
            print "Checking \"Log Store\".....",     
            _status, _msg = self.ls_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')
    
            print "Checking \"Metric Store\".....", 
            _status, _msg = self.ms_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')
            
            oscp = self.cld_attr_lst["objectstore"].copy()
            del oscp["config_string"]
            del oscp["usage"]

            self.osci = RedisMgdConn(oscp)
            self.msci = MongodbMgdConn(mscp)

        except StoreSetupException, obj :
            _status = str(obj.status)
            _msg = str(obj.msg)

        except IOError :
            pass
        
        except OSError, msg :
            print("OSError: " + str(msg))
            pass

        except Exception, e :
            _status = 23
            _msg = str(e)

        finally :
            if _status :
                print(_msg)
                exit(_status)

    @trace
    def setup_default_options(self) :
        '''
        Do command line parsing
        '''
        usage = '''usage: %prog [options] [command]
        '''
        self.parser = OptionParser(usage)
        
        self.parser.add_option("--debug_host", dest = "debug_host", metavar = "<ip address>", \
                      default = None, \
                      help = "Point CloudBench to a remote debugger")
        
        # Tracefile options
        self.parser.add_option("-t", "--trace", dest = "tracefile", metavar = "TRACE", \
                          default = None if "trace" not in self.cld_attr_lst["user-defined"] \
                            else self.cld_attr_lst["user-defined"]["trace"], \
                          help = "Points to a trace file to be loaded at the " + \
                          "beginning of execution")
        
        # API options
        self.parser.add_option("--apiport", dest = "apiport", metavar = "APIP", \
                               default = "7070", \
                               help ="Set the API port number")
        self.parser.add_option("--apiparms", dest = "apiparms", metavar = "APIM", \
                               default = "", \
                               help ="Set the API parameters")
        self.parser.add_option("--apihost", dest = "apihost", metavar = "APIH", \
                           default = "localhost", \
                           help ="Set the API hostname")
        # Log options
        self.parser.add_option("--logdest", dest = "logdest", metavar = "LDEST", \
                          default = "syslog", \
                          help ="Set the log destination (console|filename|syslog)")
    
        # Syslog options
        self.parser.add_option("--syslogn", dest = "syslogn", metavar ="TBID", \
                          default = "127.0.0.1" if "hostname" not in self.cld_attr_lst["logstore"] \
                            else self.cld_attr_lst["logstore"]["hostname"], \
                          help = "Set the syslog's ip/hostname" )
        self.parser.add_option("--syslogp", dest = "syslogp", metavar ="TBID", \
                          default = 514 if "port" not in self.cld_attr_lst["logstore"] \
                            else self.cld_attr_lst["logstore"]["port"], \
                          help = "Set the syslog's port" )
        self.parser.add_option("--syslogf", dest = "syslogf", metavar ="TBID", \
                          default = 16 if "attach_facility" not in self.cld_attr_lst["logstore"] \
                            else self.cld_attr_lst["logstore"]["attach_facility"], \
                          help = "Set the syslog's facility" )
    
        self.parser.add_option("-c", "--config", dest = "config", default = None, 
                          help = "Manually specific the path to a configuration file.")
        
        # Hard Reset
        self.parser.add_option("-f", "--hard_reset", dest = "hard_reset", action = "store_true", \
                          help = "Hard reset (flushes Object Store and Metric Store before starting a new experiment).")
    
        # Verbosity Options
        self.parser.add_option("-v", "--verbosity", dest = "verbosity", metavar = "LV", \
                          default = 2 if "verbosity" not in self.cld_attr_lst["logstore"] \
                            else self.cld_attr_lst["logstore"]["verbosity"], \
                          help = "Set verbosity level.")
    
        self.parser.add_option("-s", dest = "show_cmd_status", action = "store_true", \
                          help = "Show internal status messages of commands as they execute")
    
        self.parser.add_option("-q", dest = "quiet", action = "store_true", \
                          help = "Set quiet output.")
    
        self.parser.set_defaults()
        (self.options, self.args) = self.parser.parse_args()
        
    @trace
    def setup_logging(self, options) :
        '''
        TBD
        '''
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
    
        if int(options.syslogf) > 23 or int(options.syslogf) < 16 :
            options.syslogf = 21 
    
        logger = getLogger()
    
        status_handler = StreamHandler(stdout)
    
        # Reset the logging handlers
        while len(logger.handlers) != 0 :
            logger.removeHandler(logger.handlers[0])
    
        if options.logdest == "console" :
            hdlr = StreamHandler(stdout)
        elif options.logdest == "syslog" :
            hdlr = SysLogHandler(address = (options.syslogn, int(options.syslogp)), \
                                 facility=_syslog_selector[str(options.syslogf)])
        else :
            hdlr = RotatingFileHandler(options.logdest, maxBytes=20971520, \
                                       backupCount=20)
        formatter = Formatter('%(asctime)s %(levelname)s %(message)s')
        status_formatter = Formatter('%(message)s')
        status_handler.setFormatter(status_formatter)
        hdlr.setFormatter(formatter)
        hdlr.addFilter(MsgFilter(STATUS))
        status_handler.addFilter(AntiMsgFilter(STATUS))
    
        if not options.show_cmd_status and \
            self.cld_attr_lst["logstore"]["show_cmd_status"].strip().lower() == "no" :
            status_handler.addFilter(MsgFilter(STATUS))
                    
        logger.addHandler(hdlr)
        logger.addHandler(status_handler)
    
        if options.verbosity :
            if int(options.verbosity) >= 5 :
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 4 :
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 3 :
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 2 :
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
            elif int(options.verbosity) == 1 :
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
    
        if options.quiet :
            logger.setLevel(ERROR)

    @trace
    def start_api_and_gui(self) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            print "Checking for a running API service daemon.....", 

            _proc_man = ProcessManagement(username = self.cld_attr_lst["objectstore"]["username"])

            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp()) 
            _cmd += " --msp=" + dic2str(self.msci.mscp()) 
            _cmd += " --operation=cloud-api"
            _cmd += " --apiport=" + self.cld_attr_lst["api_defaults"]["port"]
            _cmd += " --apihost=" + self.cld_attr_lst["api_defaults"]["hostname"]
            _cmd += " --syslogp=" + self.cld_attr_lst["logstore"]["port"]
            _cmd += " --syslogf=" + self.cld_attr_lst["logstore"]["api_facility"]
            _cmd += " --syslogh=" + self.cld_attr_lst["logstore"]["hostname"]
            _cmd += " --verbosity=" + self.cld_attr_lst["logstore"]["verbosity"]
            _cmd += " --daemon"
            #_cmd += " --debug_host=localhost"

            cbdebug(_cmd) 

            _api_pid = _proc_man.start_daemon(_cmd, \
                                              self.cld_attr_lst["api_defaults"]["port"], \
                                              self.cld_attr_lst["api_defaults"]["protocol"], \
                                              conditional = True, \
                                              search_keywords = "cloud-api")

            if len(_api_pid) :
                if _api_pid[0].count("pnf") :
                    _x, _pid, _username = _api_pid[0].split('-') 
                    _msg = "Unable to start API service. Port "
                    _msg += self.cld_attr_lst["api_defaults"]["port"] + " is "
                    _msg += "already taken by process" + _pid + " (username "
                    _msg += _username + "). Please change "
                    _msg += "the port number in API_DEFAULTS and try again."
                    _status = 8181
                    raise ProcessManagement.ProcessManagementException(_status, _msg)
                else :
                    _api_pid = _api_pid[0]
                    _msg = "API Service daemon was successfully started. "
                    _msg += "The process id is " + str(_api_pid) + ". "
                    _msg += "Port " + str(self.cld_attr_lst["api_defaults"]["port"]) + '.\n'
                    sys.stdout.write(_msg)
            else :
                _msg = "Pid list for command line \"" + _cmd + "\" returned empty."
                _status = 7161
                raise ProcessManagement.ProcessManagementException(_status, _msg)

            print "Checking for a running GUI service daemon.....",
            _cmd = "screen -d -m -S cbgui" + self.cld_attr_lst["objectstore"]["username"] 
            _cmd += " bash -c '" + self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp()) 
            _cmd += " --msp=" + dic2str(self.msci.mscp()) 
            _cmd += " --operation=cloud-gui"
            _cmd += " --apiport=" + str(self.cld_attr_lst["api_defaults"]["port"])
            _cmd += " --apihost=" + self.cld_attr_lst["api_defaults"]["hostname"]
            _cmd += " --guiport=" + str(self.cld_attr_lst["gui_defaults"]["port"])
            _cmd += " --guihost=" + self.cld_attr_lst["gui_defaults"]["hostname"]
            _cmd += " --syslogp=" + self.cld_attr_lst["logstore"]["port"]
            _cmd += " --syslogf=" + self.cld_attr_lst["logstore"]["gui_facility"]
            _cmd += " --syslogh=" + self.cld_attr_lst["logstore"]["hostname"]
            _cmd += " --verbosity=" + self.cld_attr_lst["logstore"]["verbosity"]
            _cmd += "'"
            # DaemonContext Doesn't work with Twisted 
            # Someone else will have to figure it out.

            cbdebug(_cmd)

            _gui_pid = _proc_man.start_daemon(_cmd, \
                                              self.cld_attr_lst["gui_defaults"]["port"], \
                                              self.cld_attr_lst["gui_defaults"]["protocol"], \
                                              conditional = True, \
                                              search_keywords = "cloud-gui")

            if len(_gui_pid) :
                if _gui_pid[0].count("pnf") :
                    _x, _pid, _username = _api_pid[0].split('-') 
                    _msg = "Unable to start GUI service. Port "
                    _msg += self.cld_attr_lst["gui_defaults"]["port"] + " is "
                    _msg += "already taken by process" + _pid + " (username "
                    _msg += _username + "). Please change "
                    _msg += "the port number in GUI_DEFAULTS and try again."
                    _status = 8181
                    raise ProcessManagement.ProcessManagementException(_status, _msg)
                else :
                    _gui_pid = _gui_pid[0]
                    _msg = "GUI Service daemon was successfully started. "
                    _msg += "The process id is " + str(_gui_pid) + ". "
                    _msg += "Port " + str(self.cld_attr_lst["gui_defaults"]["port"]) + '.\n'
                    sys.stdout.write(_msg)  
            else :
                _msg = "Pid list for command line \"" + _cmd + "\" returned empty."
                _status = 7161
                raise ProcessManagement.ProcessManagementException(_status, _msg)

            _status = 0
            _msg = "All processes started successfully"

        except ProcessManagement.ProcessManagementException, obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to start API and/or GUI daemons: " + _fmsg
                cberr(_msg)         
                exit(_status)       
            else :
                cbdebug(_msg)

    @trace
    def emptyline(self):
        '''
        TBD
        '''
        return

    @trace
    def do_trace(self, f) :
        '''
        TBD
        '''

        f = f.strip()
        if f == "" or len(f) == 0:
            print("Please specify a filename to load commands...")
            return
            
        if f[0] != "/" :
            f = self.path + "/" + f
            print ("Loading trace file commands from: " + f)
            try :
                r = file(f)
            except IOError, msg :
                print ("Could not open file: " + str(msg))
                return
            
            while True :
                line = r.readline()
                if not line :
                    break
                self.onecmd(line)
            
    @trace
    def do_cldattach(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object  = self.active_operations.cldattach({}, \
                                                                   parameters, \
                                                                   None, \
                                                                   "cloud-attach", \
                                                                   self.cld_attr_lst)

        if not _status  :
            self.do_cldlist("", False)

        print(message_beautifier(_msg))

    @trace
    def do_expid(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.expid(self.cld_attr_lst, \
                                                               parameters, \
                                                               "expid-manage")

        print(message_beautifier(_msg))

    @trace
    def do_reset_refresh(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _result = self.passive_operations.reset_refresh(self.cld_attr_lst, \
                                                                       parameters, \
                                                                       "api-reset")
        print(message_beautifier(_msg))

    @trace
    def do_should_refresh(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _result = self.passive_operations.should_refresh(self.cld_attr_lst, \
                                                                        parameters, \
                                                                        "api-check")
        print(message_beautifier(_msg))

    @trace
    def do_monextract(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("all") :
    
            _status, _msg = self.passive_operations.monitoring_extractall(parameters, \
                                                                          "mon-extractall")
        else :
    
            _status, _msg = self.passive_operations.monitoring_extract(parameters, \
                                                                       "mon-extract")
        

        print(message_beautifier(_msg))

    @trace
    def do_monlist(self, parameters) :
        '''
        TBD
        '''

        _status, _msg = self.passive_operations.monitoring_list(parameters, \
                                                                "mon-list")
        print(message_beautifier(_msg))

    @trace
    def do_rolelist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " vm_templates+roles+VMs", \
                                                                    "global-list")
        print(message_beautifier(_msg))

    @trace
    def do_roleshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " vm_templates role", \
                                                                    "global-show")
        print(message_beautifier(_msg))

    @trace
    def do_typelist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " ai_templates+types+AIs", \
                                                                    "global-list")
        print(message_beautifier(_msg))

    @trace
    def do_typeshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " ai_templates type", \
                                                                    "global-show")
        print(message_beautifier(_msg))

    @trace
    def do_typealter(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalalter(_config_attr_list, \
                                                                     parameters + " ai_templates type", \
                                                                     "global-alter")
        print(message_beautifier(_msg))

    @trace
    def do_patternlist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " aidrs_templates+patterns+AIDRSs", \
                                                                    "global-list")
        print(message_beautifier(_msg))

    @trace
    def do_patternshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " aidrs_templates pattern ", \
                                                                    "global-show")
        print(message_beautifier(_msg))

    @trace
    def do_patternalter(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalalter(_config_attr_list, \
                                                                     parameters + " aidrs_templates pattern", \
                                                                     "global-alter")
        print(message_beautifier(_msg))

    @trace
    def do_poollist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " X+pools+VMCs", \
                                                                    "global-list")
        print(message_beautifier(_msg))

    @trace
    def do_viewlist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " query+criteria+VIEWs", \
                                                                    "global-list")
        print(message_beautifier(_msg))
        
    @trace
    def do_clddetach(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.active_operations.clddetach(self.cld_attr_lst, \
                                                                  parameters, \
                                                                  "cloud-detach")

        if not _status and BaseObjectOperations.default_cloud == parameters.strip():
            print("Disassociating default cloud: " + BaseObjectOperations.default_cloud)
            self.do_clddefault("none")
            self.do_cldlist("", False)
            
        print(message_beautifier(_msg))

    @trace
    def do_clddefault(self, parameters) :
        '''
        TBD
        '''        
        default_cloud = parameters.strip()
        if default_cloud == "" :
            _msg = "Current default cloud is \"" + str(BaseObjectOperations.default_cloud)
            _msg += "\". Need cloud name to be set as default cloud or 'none' to unset."
            print(message_beautifier(_msg))
        else :
            if default_cloud.lower() == "none" :
                BaseObjectOperations.default_cloud = None
                Cmd.prompt = "() "
            else :
                BaseObjectOperations.default_cloud = default_cloud 
                Cmd.prompt = '(' +  str(BaseObjectOperations.default_cloud) +  ") "

    @trace
    def do_cldlist(self, parameters, print_message = True) :
        '''
        TBD
        '''
        self.passive_operations = PassiveObjectOperations(self.osci, self.msci, [])

        _status, _msg, _object = self.passive_operations.list_objects(self.cld_attr_lst, \
                                                                      parameters, \
                                                                      "cloud-list")
        
        if len(_object["result"]) == 1 :
            self.do_clddefault(_object["result"][0]["name"])

        for _cloud_name_index in range(0, len(_object["result"])) :
            if _object["result"][_cloud_name_index]["name"] not in self.attached_clouds :
                self.attached_clouds.append(_object["result"][_cloud_name_index]["name"])

        self.passive_operations = PassiveObjectOperations(self.osci, \
                                                          self.msci, \
                                                          self.attached_clouds)


        self.active_operations = ActiveObjectOperations(self.osci, \
                                                self.msci, \
                                                self.attached_clouds)

        self.background_operations = BackgroundObjectOperations(self.osci, \
                                                                self.msci, \
                                                                self.attached_clouds)

        if print_message :
            print(message_beautifier(_msg))

    @trace
    def do_cldshow(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.show_object(self.cld_attr_lst, \
                                                                     parameters, \
                                                                     "cloud-show")
        print(message_beautifier(_msg))

    @trace
    def do_cldalter(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      parameters, \
                                                                      "cloud-alter")
        print(message_beautifier(_msg))

    @trace
    def do_vmccleanup(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.active_operations.vmccleanup(_vmc_attr_list, \
                                                                   parameters, \
                                                                   "vmc-cleanup")
        print(message_beautifier(_msg))

    @trace
    def do_vmcattach(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vmc-attachall")
            else :

                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vmc-attach")

        else :
            _vmc_attr_list = {}
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmcattachall(_vmc_attr_list, \
                                                                             parameters, \
                                                                             "vmc-attachall")
            else :
                _status, _msg, _object = self.active_operations.objattach(_vmc_attr_list, \
                                                                          parameters, \
                                                                          "vmc-attach")
        print(message_beautifier(_msg))

    @trace
    def do_vmcdetach(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            if parameters.count("all") :
                
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vmc-detachall")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vmc-detach")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.objdetachall(parameters, \
                                                                             "vmc-detachall")
            else :
                _vmc_attr_list = {}
                _status, _msg, _object = self.active_operations.objdetach(_vmc_attr_list, \
                                                                          parameters, \
                                                                          "vmc-detach")
        print(message_beautifier(_msg))

    @trace
    def do_vmclist(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}

        _status, _msg, _object = self.passive_operations.list_objects(_vmc_attr_list, \
                                                                      parameters, \
                                                                      "vmc-list")
        print(message_beautifier(_msg))

    @trace
    def do_vmcshow(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vmc_attr_list, \
                                                                     parameters, \
                                                                     "vmc-show")
        print(message_beautifier(_msg))

    @trace
    def do_vmcalter(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vmc_attr_list, \
                                                                      parameters, \
                                                                      "vmc-alter")
        print(message_beautifier(_msg))

    @trace
    def do_hostlist(self, parameters) :
        '''
        TBD
        '''        
        _host_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_host_attr_list, \
                                                                      parameters, \
                                                                      "host-list")
        print(message_beautifier(_msg))

    @trace
    def do_hostshow(self, parameters) :
        '''
        TBD
        '''        
        _host_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_host_attr_list, \
                                                                     parameters, \
                                                                     "host-show")
        print(message_beautifier(_msg))

    @trace
    def do_hostfail(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            _status, _msg = self.background_operations.background_execute(parameters, \
                                                                          "host-fail")
        else :
            _host_attr_list = {}
            _status, _msg, _object = self.active_operations.hostfail_repair(_host_attr_list, \
                                                                            parameters, \
                                                                            "host-fail")
        print(message_beautifier(_msg))

    @trace
    def do_hostrepair(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            _status, _msg = self.background_operations.background_execute(parameters, \
                                                                          "host-repair")
        else :
            _host_attr_list = {}
            _status, _msg, _object = self.active_operations.hostfail_repair(_host_attr_list, \
                                                                            parameters, \
                                                                            "host-repair")
        print(message_beautifier(_msg))

    @trace
    def do_vmattach(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "vm-attach")
            
        else :
            _vm_attr_list = {}
            _status, _msg, _object = self.active_operations.objattach(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-attach")
        print(message_beautifier(_msg))

    @trace
    def do_vmdetach(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vm-detachall")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "vm-detach")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.objdetachall(parameters, \
                                                                             "vm-detach")
            else :
                _vm_attr_list = {}
                _status, _msg, _object = self.active_operations.objdetach(_vm_attr_list, \
                                                                          parameters, \
                                                                          "vm-detach")
        print(message_beautifier(_msg))

    @trace
    def do_vmdebug(self, parameters) :
        '''
        TBD
        '''
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.debug_startup(_vm_attr_list, \
                                                                       parameters, \
                                                                       "vm-debug")
        print(message_beautifier(_msg))
            
    @trace
    def do_svmdebug(self, parameters) :
        '''
        TBD
        '''
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.debug_startup(_vm_attr_list, \
                                                                       parameters, \
                                                                       "svm-debug")
        print(message_beautifier(_msg))

    @trace
    def do_vmrunstate(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "vm-runstate")
        else :
            _vm_attr_list = {}
            _status, _msg, _object = self.active_operations.vmrunstate(_vm_attr_list, \
                                                                       parameters, \
                                                                       "vm-runstate")
        print(message_beautifier(_msg))

    @trace
    def do_vmsave(self, parameters) :
        '''
        TBD
        '''
        parameters += " save" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "save")
            else :
                _status, _msg = self.background_operations.background_execute(parameters, \
                                                                              "vm-runstate")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "save")
            else :
                _vm_attr_list = {}
                _status, _msg, _object = self.active_operations.vmrunstate(_vm_attr_list, \
                                                                           parameters, \
                                                                           "vm-runstate")

        print(message_beautifier(_msg))

    @trace
    def do_vmrestore(self, parameters) :
        '''
        TBD
        '''
        parameters += " attached" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "restore")
            else :
                _status, _msg = self.background_operations.background_execute(parameters, \
                                                                              "vm-runstate")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "restore")
            else :
                _vm_attr_list = {}
                _status, _msg, _object = self.active_operations.vmrunstate(_vm_attr_list, \
                                                                           parameters, \
                                                                           "vm-runstate")

        print(message_beautifier(_msg))
            
    @trace
    def do_vmfail(self, parameters) :
        '''
        TBD
        '''
        parameters += " fail" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "fail")
            else :
                _status, _msg = self.background_operations.background_execute(parameters, \
                                                                              "vm-runstate")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "fail")
            else :
                _vm_attr_list = {}
                _status, _msg, _object = self.active_operations.vmrunstate(_vm_attr_list, \
                                                                           parameters, \
                                                                           "vm-runstate")

        print(message_beautifier(_msg))

    @trace
    def do_vmrepair(self, parameters) :
        '''
        TBD
        '''
        parameters += " attached" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "repair")
            else :
                _status, _msg = self.background_operations.background_execute(parameters, \
                                                                              "vm-runstate")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.vmrunstateall(parameters, \
                                                                              "repair")
            else :
                _vm_attr_list = {}
                _status, _msg, _object = self.active_operations.vmrunstate(_vm_attr_list, \
                                                                           parameters, \
                                                                           "vm-runstate")

        print(message_beautifier(_msg))
            
    @trace
    def do_svmattach(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_svm_attr_list, \
                                                                  parameters, \
                                                                  "svm-attach")
        print(message_beautifier(_msg))

    @trace
    def do_svmdetach(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.objdetach(_svm_attr_list, \
                                                                  parameters, \
                                                                  "svm-detach")
        print(message_beautifier(_msg))
            
    @trace
    def do_svmstat(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.svmstat(_svm_attr_list, \
                                                                parameters, \
                                                                "svm-stat")
        print(message_beautifier(_msg))
            
    @trace
    def do_svmfail(self, parameters) :
        '''
            This command is identical to 'svmdetach vm_X fail'
            This is because 'detaching' the SVM object needs to go through
            the proper procedures regardless whether or not we are actually failing over
            the primary VM or simply deactivating FT replication for the primary VM.
            In either case, significant changes happen in the datastore.
        '''
        parameters += " fail"
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.objdetach(_svm_attr_list, \
                                                                  parameters, \
                                                                  "svm-detach")
        print(message_beautifier(_msg))
            
    @trace
    def do_vmcapture(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "vm-capture")
        else :
            _vm_attr_list = {}
            _status, _msg, _object = self.active_operations.vmcapture(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-capture")
        print(message_beautifier(_msg))

    @trace
    def do_vmresize(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "vm-resize")
        else :
            _vm_attr_list = {}
            _status, _msg, _object = self.active_operations.vmresize(_vm_attr_list, \
                                                                     parameters, \
                                                                     "vm-resize")
        print(message_beautifier(_msg))

    @trace
    def do_vmlist(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-list")
        print(message_beautifier(_msg))
            
    @trace
    def do_svmlist(self, parameters) :
        '''
        TBD
        '''        
        _svm_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_svm_attr_list, \
                                                                      parameters, \
                                                                      "svm-list")
        print(message_beautifier(_msg))

    @trace
    def do_vmshow(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vm_attr_list, \
                                                                     parameters, \
                                                                     "vm-show")
        print(message_beautifier(_msg))
            
    @trace
    def do_svmshow(self, parameters) :
        '''
        TBD
        '''        
        _svm_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_svm_attr_list, \
                                                                     parameters, \
                                                                     "svm-show")
        print(message_beautifier(_msg))

    @trace
    def do_vmalter(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-alter")
        print(message_beautifier(_msg))

    @trace
    def do_aiattach(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "ai-attach")
        else :
            _ai_attr_list = {}

            _status, _msg, _object = self.active_operations.objattach(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-attach")
        print(message_beautifier(_msg))

    @trace
    def do_aidetach(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-detachall")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-detach")
        else :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.objdetachall(parameters, \
                                                                             "ai-detach")
            else :
                _ai_attr_list = {}
                _status, _msg, _object = self.active_operations.objdetach(_ai_attr_list, \
                                                                          parameters, \
                                                                          "ai-detach")
        print(message_beautifier(_msg))

    @trace
    def do_aicapture(self, parameters) :
        '''
        TBD
        '''        
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "ai-capture")
        else :
            _ai_attr_list = {}
            _status, _msg, _object = self.active_operations.aicapture(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-capture")
        print(message_beautifier(_msg))

    @trace
    def do_airestore(self, parameters) :
        '''
        TBD
        '''
        parameters += " attached" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.airunstate(parameters, \
                                                                           "fail")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-runstate")
        else :
            if parameters.count("all") :
                True
                #_status, _msg, _object = _vm_command.vmrunstateall(parameters, "repair")
            else :
                _ai_attr_list = {}
                _status, _msg, _object = self.active_operations.airunstate(_ai_attr_list, \
                                                                           parameters, \
                                                                           "ai-runstate")
        print(message_beautifier(_msg))

    @trace
    def do_aisave(self, parameters) :
        '''
        TBD
        '''
        parameters += " save" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.airunstate(parameters, \
                                                                           "fail")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-runstate")
        else :
            if parameters.count("all") :
                True
                #_status, _msg, _object = _vm_command.vmrunstateall(parameters, "repair")
            else :
                _ai_attr_list = {}
                _status, _msg, _object = self.active_operations.airunstate(_ai_attr_list, \
                                                                           parameters, \
                                                                           "ai-runstate")
        print(message_beautifier(_msg))
            
    @trace
    def do_aifail(self, parameters) :
        '''
        TBD
        '''
        parameters += " fail" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.airunstate(parameters, \
                                                                           "fail")
            else :
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-runstate")
        else :
            if parameters.count("all") :
                True
                #_status, _msg, _object = _vm_command.vmrunstateall(parameters, "repair")
            else :
                _ai_attr_list = {}
                _status, _msg, _object = self.active_operations.airunstate(_ai_attr_list, \
                                                                           parameters, \
                                                                           "ai-runstate")
        print(message_beautifier(_msg))

    @trace
    def do_airepair(self, parameters) :
        '''
        TBD
        '''
        parameters += " attached" 
        if parameters.count("async") :
            if parameters.count("all") :
                _status, _msg, _object = self.active_operations.airunstate(parameters, \
                                                                           "repair")
            else :                
                _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                       "ai-runstate")
        else :
            if parameters.count("all") :
                True
                #_status, _msg, _object = _vm_command.vmrunstateall(parameters, "repair")
            else :
                _ai_attr_list = {}
                _status, _msg, _object = self.active_operations.airunstate(_ai_attr_list, \
                                                                           parameters, \
                                                                           "ai-runstate")
        print(message_beautifier(_msg))

    @trace
    def do_airesize(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("async") :
            _status, _msg, _object = self.background_operations.background_execute(parameters, \
                                                                                   "ai-resize")
        else :
            _ai_attr_list = {}
            _status, _msg, _object = self.active_operations.airesize(_ai_attr_list, \
                                                                     parameters, \
                                                                     "ai-resize")
        print(message_beautifier(_msg))

    @trace
    def do_ailist(self, parameters) :
        '''
        TBD
        '''        
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-list")
        print(message_beautifier(_msg))

    @trace
    def do_aishow(self, parameters) :
        '''
        TBD
        '''        
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_ai_attr_list, \
                                                                     parameters, \
                                                                     "ai-show")
        print(message_beautifier(_msg))

    @trace
    def do_aialter(self, parameters) :
        '''
        TBD
        '''
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-alter")
        print(message_beautifier(_msg))

    @trace
    def do_aidrsattach(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_aidrs_attr_list, \
                                                                  parameters, \
                                                                  "aidrs-attach")
        print(message_beautifier(_msg))

    @trace
    def do_aidrsdetach(self, parameters) :
        '''
        TBD
        ''' 
        if parameters.count("all") :
            _status, _msg, _object = self.active_operations.objdetachall(parameters, \
                                                                         "aidrs-detachall")
        else :
            _aidrs_attr_list = {}
            _status, _msg, _object = self.active_operations.objdetach(_aidrs_attr_list, \
                                                                      parameters, \
                                                                      "aidrs-detach")
        print(message_beautifier(_msg))

    @trace
    def do_aidrslist(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_aidrs_attr_list, \
                                                                      parameters, \
                                                                      "aidrs-list")
        print(message_beautifier(_msg))

    @trace
    def do_aidrsshow(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_aidrs_attr_list, \
                                                                     parameters, \
                                                                     "aidrs-show")
        print(message_beautifier(_msg))

    @trace
    def do_aidrsalter(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_aidrs_attr_list, \
                                                                      parameters, \
                                                                      "aidrs-alter")
        print(message_beautifier(_msg))

    @trace
    def do_vmcrsattach(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_vmcrs_attr_list, \
                                                                  parameters, \
                                                                  "vmcrs-attach")
        print(message_beautifier(_msg))

    @trace
    def do_vmcrsdetach(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objdetach(_vmcrs_attr_list, \
                                                                  parameters, \
                                                                  "vmcrs-detach")
        print(message_beautifier(_msg))

    @trace
    def do_vmcrslist(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_vmcrs_attr_list, \
                                                                      parameters, \
                                                                      "vmcrs-list")
        
        print(message_beautifier(_msg))

    @trace
    def do_vmcrsshow(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vmcrs_attr_list, \
                                                                     parameters, \
                                                                     "vmcrs-show")
        print(message_beautifier(_msg))

    @trace
    def do_vmcrsalter(self, parameters) :
        '''
        TBD
        '''
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vmcrs_attr_list, \
                                                                      parameters, \
                                                                      "vmcrs-alter")
        print(message_beautifier(_msg))

    @trace
    def do_viewshow(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.show_view(self.cld_attr_lst, \
                                                                   parameters, \
                                                                   "view-show")
        print(message_beautifier(_msg))

    @trace
    def do_stats(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.stats(self.cld_attr_lst, \
                                                               parameters, \
                                                               "stats-get")
        print(message_beautifier(_msg))

    @trace
    def do_stateshow(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.show_state(self.cld_attr_lst, \
                                                                    parameters, \
                                                                    "state-show")
        print(message_beautifier(_msg))

    @trace
    def do_statealter(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.alter_state(self.cld_attr_lst, \
                                                                     parameters, \
                                                                     "state-alter")
        print(message_beautifier(_msg))

    @trace
    def do_waitfor(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.wait_for(self.cld_attr_lst, \
                                                                  parameters, \
                                                                  "wait-for")
        print(message_beautifier(_msg))

    @trace
    def do_waituntil(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_until(self.cld_attr_lst, \
                                                                    parameters, \
                                                                    "wait-until")
        print(message_beautifier(_msg))

    @trace
    def do_waiton(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_on(self.cld_attr_lst, \
                                                                 parameters, \
                                                                 "wait-on")
        print(message_beautifier(_msg))

    @trace
    def do_msgpub(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.msgpub(self.cld_attr_lst, \
                                                                parameters, \
                                                                "msg-pub")
        print(message_beautifier(_msg))

    @trace
    def do_shell(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.execute_shell(parameters, \
                                                                       "shell-execute")  

        print(message_beautifier(_msg))

    @trace
    def do_echo(self, line):
        '''
        TBD
        '''
        print(line)

    @trace
    def do_quit(self, line) :
        '''
        TBD
        '''
        if self.console is not None :
            self.console.send_top("Use CTRL-D or CTRL-] to exit.", True)
        return True

    @trace
    def do_exit(self, line) :
        '''
        TBD
        '''
        if self.console is not None :
            self.console.send_top("Use CTRL-D or CTRL-] to exit.", True)
        return True

    @trace
    def do_help(self, args):
        if not help(args) :
            Cmd.do_help(self, args)

    @trace
    def do_EOF(self, line) :
        '''
        TBD
        '''
        if self.console is not None :
            self.console.send_top("Use CTRL-D or CTRL-] to exit.", True)
        return True

def help(args):
    path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../"
    '''
    Get help on commands
       'help' or '?' with no arguments prints a list of commands for which help is available
       'help <command>' or '? <command>' gives help on <command>
    '''
    if len(args) :
        if os.access(path + "docs/help/" + args + ".txt", os.F_OK) :
            _fd = open(path + "docs/help/" + args + ".txt", 'r')
            _fc = _fd.readlines()
            _fd.close()
            for _line in _fc :
                print _line,
        else :
            "No help available for " + args
        print ''
        return True
    else :
        return False
