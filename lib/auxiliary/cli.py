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
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions

class CBCLI(Cmd) :

    @trace
    def __init__ (self, do_nothing = False) :
        '''
        TBD
        '''
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../"
        self.instance = False
        self.cld_attr_lst = None
        self.username = getpwuid(os.getuid())[0]
        self.pid = "TEST_" + self.username 
        history = self.path + "/.cb_history"
        self.console = None
        self.active_operations = None
        self.passive_operations = None
        self.background_operations = None
        self.attached_clouds = []

        if do_nothing :
            return 
        
        Cmd.__init__(self)
        Cmd.prompt = "() "
        Cmd.emptyline = self.emptyline()

        _status = 100
        _msg = "An error has occurred, but no error message was captured"

        try :

            _msg = "Parsing \"cloud definitions\" file....."
            self.write(_msg, True)
            self.cld_attr_lst = parse_cld_defs_file(self.pid, None, True)

            self.os_conn_parms = self.cld_attr_lst["objectstore"].copy()
            del self.os_conn_parms["config_string"]
            del self.os_conn_parms["usage"]

            self.ms_conn_parms = self.cld_attr_lst["metricstore"].copy()
            del self.ms_conn_parms["config_string"]
            del self.ms_conn_parms["usage"]

            if not os.path.exists(history) :
                _file = open(history, 'w')
                _file.write('')
                _file.close()

            readline.set_history_length(10000)
            readline.read_history_file(history) 

            self.os_func, self.ms_func, self.ls_func = load_store_functions(self.cld_attr_lst)
    
            self.write("Checking \"Object Store\".....", True)        
            _status, _msg = self.os_func("cliexec", None, self.cld_attr_lst, "check")
            self.write(_msg)
    
            self.write("Checking \"Log Store\".....", True)        
            _status, _msg = self.ls_func("cliexec", None, self.cld_attr_lst, "check")
            self.write(_msg)
    
            self.write("Checking \"Metric Store\".....", True)        
            _status, _msg = self.ms_func("cliexec", None, self.cld_attr_lst, "check")
            self.write(_msg)
            
            '''
            fix me
            '''
            self.os_conn_parms = self.cld_attr_lst["objectstore"].copy()
            del self.os_conn_parms["config_string"]
            del self.os_conn_parms["usage"]

        except StoreSetupException, obj :
            _status = str(obj.status)
            _msg = str(obj.msg)

        except IOError :
            pass
        
        except OSError, msg :
            self.write("OSError: " + str(msg))
            pass

        except Exception, e :
            _status = 23
            _msg = str(e)

        finally :
            if _status :
                self.write(_msg)
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

            self.write("Checking for a running API service daemon.....", True)

            _proc_man = ProcessManagement(username = self.cld_attr_lst["objectstore"]["username"])

            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.os_conn_parms) 
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
                    _msg += "Port " + str(self.cld_attr_lst["api_defaults"]["port"]) + '.'
                    self.write(_msg)
            else :
                _msg = "Pid list for command line \"" + _cmd + "\" returned empty."
                _status = 7161
                raise ProcessManagement.ProcessManagementException(_status, _msg)

            self.write("Checking for a running GUI service daemon.....", True)
            _cmd = "screen -d -m -S cbgui" + self.cld_attr_lst["objectstore"]["username"] 
            _cmd += " bash -c '" + self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.os_conn_parms) 
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
                    _msg += "Port " + str(self.cld_attr_lst["gui_defaults"]["port"]) + '.'
                    self.write(_msg)  
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
    def write(self, message, no_newline = False) :
        '''
        TBD
        '''
        if no_newline :
            print message,
        else :
            print message

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
            self.write("Please specify a filename to load commands...")
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
            self.os_conn_parms["cloud_name"] = _object["result"]["cloud_name"]
            self.do_cldlist("", False)

        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_expid(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.expid(self.cld_attr_lst, \
                                                               parameters, \
                                                               "expid-manage")

        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_reset_refresh(self, parameters) :
        '''
        TBD
        '''
        if self.os_conn_parms :
            _status, _msg, _result = self.passive_operations.reset_refresh(self.cld_attr_lst, \
                                                                           parameters, \
                                                                           "api-reset")
            self.write(message_beautifier(self.pid, _msg))
        else :
            self.write("Please attach at least one cloud first.")

    @trace
    def do_should_refresh(self, parameters) :
        '''
        TBD
        '''
        if self.os_conn_parms : 
            _status, _msg, _result = self.passive_operations.should_refresh(self.cld_attr_lst, \
                                                                            parameters, \
                                                                            "api-check")
            self.write(message_beautifier(self.pid, _msg))
        else :
            self.write("Please attach at least one cloud first.")

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
        

        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_monlist(self, parameters) :
        '''
        TBD
        '''

        _status, _msg = self.passive_operations.monitoring_list(parameters, \
                                                                "mon-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_rolelist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " vm_templates+roles+VMs", \
                                                                    "global-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_roleshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " vm_templates role", \
                                                                    "global-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_typelist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " ai_templates+types+AIs", \
                                                                    "global-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_typeshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " ai_templates type", \
                                                                    "global-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_typealter(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalalter(_config_attr_list, \
                                                                     parameters + " ai_templates type", \
                                                                     "global-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_patternlist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " aidrs_templates+patterns+AIDRSs", \
                                                                    "global-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_patternshow(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalshow(_config_attr_list, \
                                                                    parameters + " aidrs_templates pattern ", \
                                                                    "global-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_patternalter(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globalalter(_config_attr_list, \
                                                                     parameters + " aidrs_templates pattern", \
                                                                     "global-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_poollist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " X+pools+VMCs", \
                                                                    "global-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_viewlist(self, parameters) :
        '''
        TBD
        '''
        _config_attr_list = {}
        _status, _msg, _object = self.passive_operations.globallist(_config_attr_list, \
                                                                    parameters + " query+criteria+VIEWs", \
                                                                    "global-list")
        self.write(message_beautifier(self.pid, _msg))
        
    @trace
    def do_clddetach(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.active_operations.clddetach(self.cld_attr_lst, \
                                                                  parameters, \
                                                                  "cloud-detach")

        if not _status and BaseObjectOperations.default_cloud == parameters.strip():
            self.write("Disassociating default cloud: " + BaseObjectOperations.default_cloud)
            self.do_clddefault("none")

            self.do_cldlist("", False)
            
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_clddefault(self, parameters) :
        '''
        TBD
        '''        
        default_cloud = parameters.strip()
        if default_cloud == "" :
            _msg = "Current default cloud is \"" + str(BaseObjectOperations.default_cloud)
            _msg += "\". Need cloud name to be set as default cloud or 'none' to unset."
            self.write(_msg)
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
        self.passive_operations = PassiveObjectOperations(self.pid, \
                                                          self.os_conn_parms, \
                                                          self.ms_conn_parms, \
                                                          [])

        _status, _msg, _object = self.passive_operations.list_objects(self.cld_attr_lst, \
                                                                      parameters, \
                                                                      "cloud-list")
        
        if len(_object["result"]) == 1 :
            self.do_clddefault(_object["result"][0]["name"])

        for _cloud_name_index in range(0, len(_object["result"])) :
            if _object["result"][_cloud_name_index]["name"] not in self.attached_clouds :
                self.attached_clouds.append(_object["result"][_cloud_name_index]["name"])

        self.passive_operations = PassiveObjectOperations(self.pid, \
                                                          self.os_conn_parms, \
                                                          self.ms_conn_parms, \
                                                          self.attached_clouds)


        self.active_operations = ActiveObjectOperations(self.pid, \
                                                self.os_conn_parms, \
                                                self.ms_conn_parms, \
                                                self.attached_clouds)

        self.background_operations = BackgroundObjectOperations(self.pid, \
                                                                self.os_conn_parms, \
                                                                self.ms_conn_parms, \
                                                                self.attached_clouds)

        if print_message :
            self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_cldshow(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.show_object(self.cld_attr_lst, \
                                                                     parameters, \
                                                                     "cloud-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_cldalter(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      parameters, \
                                                                      "cloud-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmccleanup(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.active_operations.vmccleanup(_vmc_attr_list, \
                                                                   parameters, \
                                                                   "vmc-cleanup")
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmclist(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}

        _status, _msg, _object = self.passive_operations.list_objects(_vmc_attr_list, \
                                                                      parameters, \
                                                                      "vmc-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcshow(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vmc_attr_list, \
                                                                     parameters, \
                                                                     "vmc-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcalter(self, parameters) :
        '''
        TBD
        '''        
        _vmc_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vmc_attr_list, \
                                                                      parameters, \
                                                                      "vmc-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_hostlist(self, parameters) :
        '''
        TBD
        '''        
        _host_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_host_attr_list, \
                                                                      parameters, \
                                                                      "host-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_hostshow(self, parameters) :
        '''
        TBD
        '''        
        _host_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_host_attr_list, \
                                                                     parameters, \
                                                                     "host-show")
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmdebug(self, parameters) :
        '''
        TBD
        '''
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.debug_startup(_vm_attr_list, \
                                                                       parameters, \
                                                                       "vm-debug")
        self.write(message_beautifier(self.pid, _msg))
            
    @trace
    def do_svmdebug(self, parameters) :
        '''
        TBD
        '''
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.debug_startup(_vm_attr_list, \
                                                                       parameters, \
                                                                       "svm-debug")
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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

        self.write(message_beautifier(self.pid, _msg))

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

        self.write(message_beautifier(self.pid, _msg))
            
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

        self.write(message_beautifier(self.pid, _msg))

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

        self.write(message_beautifier(self.pid, _msg))
            
    @trace
    def do_svmattach(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_svm_attr_list, \
                                                                  parameters, \
                                                                  "svm-attach")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_svmdetach(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.objdetach(_svm_attr_list, \
                                                                  parameters, \
                                                                  "svm-detach")
        self.write(message_beautifier(self.pid, _msg))
            
    @trace
    def do_svmstat(self, parameters) :
        '''
        TBD
        '''
        _svm_attr_list = {}
        _status, _msg, _object = self.active_operations.svmstat(_svm_attr_list, \
                                                                parameters, \
                                                                "svm-stat")
        self.write(message_beautifier(self.pid, _msg))
            
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
        self.write(message_beautifier(self.pid, _msg))
            
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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmlist(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-list")
        self.write(message_beautifier(self.pid, _msg))
            
    @trace
    def do_svmlist(self, parameters) :
        '''
        TBD
        '''        
        _svm_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_svm_attr_list, \
                                                                      parameters, \
                                                                      "svm-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmshow(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vm_attr_list, \
                                                                     parameters, \
                                                                     "vm-show")
        self.write(message_beautifier(self.pid, _msg))
            
    @trace
    def do_svmshow(self, parameters) :
        '''
        TBD
        '''        
        _svm_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_svm_attr_list, \
                                                                     parameters, \
                                                                     "svm-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmalter(self, parameters) :
        '''
        TBD
        '''        
        _vm_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vm_attr_list, \
                                                                      parameters, \
                                                                      "vm-alter")
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))
            
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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_ailist(self, parameters) :
        '''
        TBD
        '''        
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aishow(self, parameters) :
        '''
        TBD
        '''        
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_ai_attr_list, \
                                                                     parameters, \
                                                                     "ai-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aialter(self, parameters) :
        '''
        TBD
        '''
        _ai_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_ai_attr_list, \
                                                                      parameters, \
                                                                      "ai-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aidrsattach(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_aidrs_attr_list, \
                                                                  parameters, \
                                                                  "aidrs-attach")
        self.write(message_beautifier(self.pid, _msg))

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
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aidrslist(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_aidrs_attr_list, \
                                                                      parameters, \
                                                                      "aidrs-list")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aidrsshow(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_aidrs_attr_list, \
                                                                     parameters, \
                                                                     "aidrs-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_aidrsalter(self, parameters) :
        '''
        TBD
        '''        
        _aidrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_aidrs_attr_list, \
                                                                      parameters, \
                                                                      "aidrs-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcrsattach(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objattach(_vmcrs_attr_list, \
                                                                  parameters, \
                                                                  "vmcrs-attach")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcrsdetach(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.active_operations.objdetach(_vmcrs_attr_list, \
                                                                  parameters, \
                                                                  "vmcrs-detach")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcrslist(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.list_objects(_vmcrs_attr_list, \
                                                                      parameters, \
                                                                      "vmcrs-list")
        
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcrsshow(self, parameters) :
        '''
        TBD
        '''        
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.show_object(_vmcrs_attr_list, \
                                                                     parameters, \
                                                                     "vmcrs-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_vmcrsalter(self, parameters) :
        '''
        TBD
        '''
        _vmcrs_attr_list = {}
        _status, _msg, _object = self.passive_operations.alter_object(_vmcrs_attr_list, \
                                                                      parameters, \
                                                                      "vmcrs-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_viewshow(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.show_view(self.cld_attr_lst, \
                                                                   parameters, \
                                                                   "view-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_stats(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.stats(self.cld_attr_lst, \
                                                               parameters, \
                                                               "stats-get")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_stateshow(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.show_state(self.cld_attr_lst, \
                                                                    parameters, \
                                                                    "state-show")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_statealter(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.alter_state(self.cld_attr_lst, \
                                                                     parameters, \
                                                                     "state-alter")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_waitfor(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.passive_operations.wait_for(self.cld_attr_lst, \
                                                                  parameters, \
                                                                  "wait-for")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_waituntil(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_until(self.cld_attr_lst, \
                                                                    parameters, \
                                                                    "wait-until")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_waiton(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_on(self.cld_attr_lst, \
                                                                 parameters, \
                                                                 "wait-on")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_msgpub(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.msgpub(self.cld_attr_lst, \
                                                                parameters, \
                                                                "msg-pub")
        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_shell(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.execute_shell(parameters, \
                                                                       "shell-execute")  

        self.write(message_beautifier(self.pid, _msg))

    @trace
    def do_echo(self, line):
        '''
        TBD
        '''
        self.write(line)

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
        '''
        Get help on commands
           'help' or '?' with no arguments prints a list of commands for which help is available
           'help <command>' or '? <command>' gives help on <command>
        '''
        if len(args) :
            if os.access(self.path + "docs/help/" + args + ".txt", os.F_OK) :
                _fd = open(self.path + "docs/help/" + args + ".txt", 'r')
                _fc = _fd.readlines()
                _fd.close()
                for _line in _fc :
                    print _line,
            else :
                "No help available for " + args
            print ''
        else :
            Cmd.do_help(self, args)

    @trace
    def do_EOF(self, line) :
        '''
        TBD
        '''
        if self.console is not None :
            self.console.send_top("Use CTRL-D or CTRL-] to exit.", True)
        return True
