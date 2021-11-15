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
    Created on Aug 22, 2011

    Experiment Command Processor Command Line Interface

    @author: Marcio Silva, Michael R. Galaxy
'''

import os
import sys
import readline
import re
import xmlrpc.client
import socket
import traceback

from cmd import Cmd
from pwd import getpwuid
from sys import stdout, path
from subprocess import Popen, PIPE
from optparse import OptionParser
from re import sub, compile
from time import time

from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO
from logging.handlers import logging, SysLogHandler, RotatingFileHandler
from lib.auxiliary.code_instrumentation import VerbosityFilter, MsgFilter, AntiMsgFilter, STATUS, ReconnectingNewlineSysLogHandler
from lib.stores.stores_initial_setup import StoreSetupException
from lib.auxiliary.data_ops import message_beautifier, dic2str, is_valid_temp_attr_list, create_restart_script
from lib.remote.process_management import ProcessManagement
from lib.operations.active_operations import ActiveObjectOperations
from lib.operations.passive_operations import PassiveObjectOperations
from lib.operations.base_operations import BaseObjectOperations
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.stores.stores_initial_setup import load_metricstore_adapter
from lib.stores.redis_datastore_adapter import RedisMgdConn
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions, get_available_clouds
from lib.api.api_service_client import *
from lib.api.api_service import API

class CBCLI(Cmd) :
    @trace
    def __init__ (self, definitions = None) :
        '''
        TBD
        '''
        self.stdout = sys.stdout
        self.path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../"
        self.cld_attr_lst = {"logstore" : {}, "user-defined" : {}, "api_defaults" : {}} # will be overriden later, used for setup_default_options()
        self.username = getpwuid(os.getuid())[0]
        self.pid = "TEST_" + self.username 
        history = os.path.expanduser("~") + "/.cb_history"
        
        self.console = None
        self.active_operations = None
        self.passive_operations = None
        self.attached_clouds = []
        
        _status = 100
        _msg = "An error has occurred, but no error message was captured"

        # See if the '-f' option exists
        self.setup_default_options()
        
        if self.options.debug_host is not None :
            import debug
            print(str(path))
            import pydevd
            pydevd.settrace(host=self.options.debug_host)

        try :

            self.cld_attr_lst = {}
            _msg = "Parsing \"cloud definitions\" file....."
            print(str(_msg), end=' ')

            '''
             We have to store the resulting definitions themselves in
             addition to the attributes because the user may have used
             the '-c' option, in which case the user-specified definitions
             have to be passed to the cldattach() command manually.
            '''

            get_options_from_env(self.options)

            self.cld_attr_lst, self.definitions = parse_cld_defs_file(None, True, self.options.config)
            
            if self.options.hard_reset :
                self.cld_attr_lst["time"]["hard_reset"] = True
            else :
                self.cld_attr_lst["time"]["hard_reset"] = False

            self.cld_attr_lst["space"]["tracefile"] = self.options.tracefile

            '''
            Using the new multi-cloud configuration is mandatory, now.

            This is because the github.com configuration format
            is expected to "just work" out of the box. This is done
            by offering a functional "default" simulated cloud in the
            public configuration file in addition to per-cloud
            example configurations for the user to try out.

            This cannot be done without a proper multi-cloud configuration.
            '''
            if not self.options.oldconfig :
                clouds = get_available_clouds(self.cld_attr_lst, return_all_options = True) 

                if len(clouds) == 0 :
                    _msg = "Configuration Error: Your configuration is deprecated."
                    _msg += "Please refer to configs/cloud_definitions.txt for "
                    _msg += "examples on the new configuration format.\n "
                    _msg += "If you want to revert to use the deprecated format,"
                    _msg += " specify --oldconfig on the command-line."
                    raise Exception(_msg)

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

            self.os_func, self.ms_func, self.ls_func, self.fs_func = \
            load_store_functions(self.cld_attr_lst)
    
            print("\nChecking \"Object Store\".....", end=' ')        
            _status, _msg = self.os_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')
    
            print("Checking \"Log Store\".....", end=' ')     
            _status, _msg = self.ls_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')
    
            print("Checking \"Metric Store\".....", end=' ') 
            _status, _msg = self.ms_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n')

            print("Checking \"File Store\".....", end=' ') 
            _status, _msg = self.fs_func(self.cld_attr_lst, "check")
            sys.stdout.write(_msg + '\n\n')
            
            oscp = self.cld_attr_lst["objectstore"].copy()
            del oscp["config_string"]
            del oscp["usage"]

            self.osci = RedisMgdConn(oscp)
            self.api_service_url = "http://" + self.cld_attr_lst["api_defaults"]["hostname"]
            self.api_service_url += ":" + self.cld_attr_lst["api_defaults"]["port"]
            
            self.api = APIClient(self.api_service_url)

            '''
             All thanks to python. This works, again, by using decorators:
             
             The Cmd class looks up the corresponding function as it usually
             does 'do_function', but instead it finds a decorator which accepts
             the same "parameters" argument. The decorator "unpack_arguments_for_api"
             then builds a list of python named arguments and passes it to the
             corresponding API function. In order to figure out which API function
             to use, the API exposes a function to list those functions, which
             in turn allows us to setup the appropriate function pointer.
            '''
             
            self.signatures = {}
            self.usage = {}

            for methodtuple in inspect.getmembers(API, predicate=inspect.isfunction) :
                
                # Record the function signatures required to be provided by the CLI
                name = methodtuple[0]
                
                if name in ["__init__", "success", "error", "get_functions", \
                            "get_signature", "should_refresh", "reset_refresh", \
                            "vminit", "appinit", "cldparse" ] :
                    # vminit and appinit are exposed to the command-line
                    # as regular attach commands using a separate parameter
                    continue
                
                # Do not install the function if it's already implemented
                # by the CBCLI class
                try :
                    getattr(self, "do_" + name)
                    continue
                except AttributeError as msg :
                    pass
                
                func = getattr(API, name)
                
                argspec = inspect.getargspec(func) 
                spec = argspec[0]
                defaults = [] if argspec[3] is None else argspec[3]
                num_spec = len(spec)
                num_defaults = len(defaults)
                diff = num_spec - num_defaults
                named = diff - 1 
                self.signatures[name] = {"args" : spec[1:], "named" : named }
                
                # Now, we can build the Usage strings automatically
                # by inspecting the functions themselves
                _msg = "Usage: vmattach <cloud name> <role> [vmc pool] [size] [action after attach] [mode]"
                doc = "Usage: " + self.convert_app_to_ai(name) + " "
                for x in range(1, diff) :
                    doc += "<" + spec[x] + "> "
                for x in range(diff, num_spec) :
                    if spec[x].lower() == "nosync" :
                        doc += "[mode] "
                        continue
                    doc += "[" + spec[x] + " = " + str(defaults[x - diff]) + "] "
                self.usage[name] = doc
            
            self.install_functions()
                
            self.api.print_message = True 
                
            Cmd.prompt = "() "
            Cmd.emptyline = self.emptyline()
            Cmd.__init__(self)

        except StoreSetupException as obj :
            for line in traceback.format_exc().splitlines() :
                print(line)
            _status = str(obj.status)
            _msg = str(obj.msg)

        except IOError as msg :
            print(("IOError: " + str(msg)))
            pass
        
        except OSError as msg :
            print(("OSError: " + str(msg)))
            pass

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                print(line)
            _status = 23
            _msg = str(e)

        finally :
            if _status :
                print(_msg)
                exit(_status)
                
    def convert_app_to_ai(self, name):
        if len(name) >= 4 and name[:3] == "app" :
            name = "ai" + name[3:]
        return name
           
    def install_functions(self):
        for name in self.signatures :
            # Install the API functions into the command-line
            new_function = self.convert_app_to_ai(name)
            setattr(self, "do_" + new_function, self.unpack_arguments_for_api(getattr(self.api, name)))
            setattr(CBCLI, "do_" + new_function, self.unpack_arguments_for_api(getattr(self.api, name)))
            setattr(self, "help_" + new_function, help)
            setattr(CBCLI, "help_" + new_function, help)
                
    def unpack_arguments_for_api(self, func) :
        '''
        TBD
        '''
        def wrapped(*args, **kwargs):
            name = func.__name__ if not self.options.remote else func._Method__name
            
            '''
            This function is called by Cmd class.
            The first parameter contains the parameter list which
            we relay over to the API.
            '''
            temp_parameters = args[0]
            temp_parameters = self.cleanup_comments(temp_parameters).strip().split()

            if len(temp_parameters) == 0 :
                temp_parameters = []
            if len(args) > 1 :
                temp_parameters = temp_parameters + list(args)[1:]
                
            '''
            The 'nosync' and other '=' keywords/options are special, because we 
            are allowing them to liberally float around the command line without
            being properly positioned by the user.
            
            The API requires that 'nosync' and tkv be a keyword arguments,
            and requires the components of the '=' sign to be splitup.
            '''

            parameters = []
            for param in temp_parameters :
                if param.count("nosync") or param.count("async") :
                    kwargs["nosync"] = param
                    continue

                if name.count("attach") :
                    if is_valid_temp_attr_list(param) :
                        kwargs["temp_attr_list"] = param
                        continue

                if param.count("=") and name.count("alter") :
                    pieces = param.split("=", 1)
                    parameters.append(pieces[0])
                    parameters.append(pieces[1])
                    continue
                parameters.append(param)
            
            '''
            All API functions, like the CLI require the name of the cloud
            to be specified.
            '''
            if BaseObjectOperations.default_cloud :
                if len(parameters) > 0 :
                        _possible_cloud_name = parameters[0]
                        if _possible_cloud_name == BaseObjectOperations.default_cloud :
                            True
                        elif _possible_cloud_name in self.attached_clouds :
                            True 
                        else :
                            parameters = [BaseObjectOperations.default_cloud] + parameters
                else :
                    parameters = [BaseObjectOperations.default_cloud] + parameters

            num_parms = len(parameters)
                
            if len(name) >= 3 and name[:2] == "ai" :
                name = "app" + name[2:]
            required =  int(self.signatures[name]["named"])
            
            '''
            Now that we know the required number of arguments,
            we can yell at the user if they typed the wrong number
            of parameters based on the exact signature of
            the actual function.
            '''
            if num_parms < required :
                print(self.usage[name])
                return

            if num_parms > len(self.signatures[name]["args"]) :
                print(self.usage[name])
                return

            # Now, actually send to the API
            try :
                response = func(*parameters, **kwargs)
                if not self.options.remote :
                    print((message_beautifier(response["msg"])))

            except APIException as obj :
                print(obj)

            except Exception as e :
                _status = 23
                _msg = str(e)

        return wrapped
    
    @trace
    def setup_default_options(self) :
        '''
        Do command line parsing
        '''

        _path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0)
            
        usage = '''usage: %prog [options] [command]
        '''
        self.parser = OptionParser(usage)
        
        self.parser.add_option("--oldconfig", dest = "oldconfig", action = "store_true", \
                      default = False, \
                        help = "Use the deprecated configuration format.")

        '''
         This options controls whether or not the API is used *in memory*
         or over the network as a service.
        '''
        
        self.parser.add_option("-r", "--remote", dest = "remote", action = "store_true", \
                      default = False if "remote" not in self.cld_attr_lst["api_defaults"] \
                        else self.cld_attr_lst["api_defaults"]["remote"], \
                        help = "Use a remote API instance instead of local in-memory API.")
        
        self.parser.add_option("-d", "--debug_host", dest = "debug_host", metavar = "<ip address>", \
                      default = None, \
                      help = "Point CloudBench to a remote debugger")
        
        # Tracefile options
        self.parser.add_option("-t", "--trace", dest = "tracefile", metavar = "TRACE", \
                          default = None if "trace" not in self.cld_attr_lst["user-defined"] \
                            else self.cld_attr_lst["user-defined"]["trace"], \
                          help = "Points to a trace file to be loaded at the " + \
                          "beginning of execution")

        self.parser.add_option("--tpdir", \
                           dest="tpdir", \
                           default= _path + "/3rd_party", \
                           help="Name of the third-party directory")
    
        self.parser.add_option("--defdir", \
                           dest="defdir", \
                           default=_path + "/configs/templates/", \
                           help="Dependencies configuration file defaults dir")
    
        self.parser.add_option("--cusdir", \
                           dest="cusdir", \
                           default=_path + "/configs/", \
                           help="Dependencies configuration file customizations dir")
    
        self.parser.add_option("--wksdir", \
                           dest = "wksdir", \
                           default = _path + "/scripts/", \
                           help = "Workload dependencies configuration file dir")
    
        self.parser.add_option("-w","--wks", \
                           dest = "wks", \
                           default = "", \
                           help = "Comma-separated workload list")
    
        self.parser.add_option("--custom", \
                           dest = "custom", \
                           default = "", \
                           help = "Dependencies customization file name")
        
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
        self.parser.add_option("-x", "--hard_reset", dest = "hard_reset", action = "store_true", \
                          help = "Hard reset (flushes Object Store, Log Store and Metric Store before starting a new experiment).")
        # Soft Reset
        '''
        Hard resets delete data from Mongo, which is bad.
        Soft reset should be the default for regular usage,
        so data is not lost.
        ''' 
        self.parser.add_option("-f", "--soft_reset", action = "store_true", dest = "soft_reset", \
                          help = "Soft reset (flushes Object Store but leaves experiment data intact)")

        self.parser.add_option("-i", "--soft_reset_cloud", default = "startup_cloud", dest = "soft_reset_cloud", \
                          help = "Soft reset only a specific cloud type, default: 'startup_cloud'")
    
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
            if self.cld_attr_lst["logstore"]["protocol"] == "TCP" :
                hdlr = ReconnectingNewlineSysLogHandler(address = (options.syslogn, int(options.syslogp)), \
                                     facility=_syslog_selector[str(options.syslogf)],
                                     socktype = socket.SOCK_STREAM)
            else :
                hdlr = SysLogHandler(address = (options.syslogn, int(options.syslogp)), \
                                     facility=_syslog_selector[str(options.syslogf)],
                                     socktype = socket.SOCK_DGRAM)
        else :
            hdlr = RotatingFileHandler(options.logdest, maxBytes=20971520, \
                                       backupCount=20)
            
        # Need to make this rfc3164-compliant by including the 'hostname' and the 'program name'
        formatter = Formatter(socket.getfqdn() + " cloudbench [%(levelname)s] %(message)s")

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
            if int(options.verbosity) >= 8 :
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 7 :
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 6 :
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("data_ops"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 5 :
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("get_object_count"))
                hdlr.addFilter(VerbosityFilter("get_counters"))
                hdlr.addFilter(VerbosityFilter("get_process_object"))
                hdlr.addFilter(VerbosityFilter("data_ops"))             
                hdlr.addFilter(VerbosityFilter("datastore"))                
                logger.setLevel(DEBUG)                
            elif int(options.verbosity) >= 4 :
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("get_object_count"))
                hdlr.addFilter(VerbosityFilter("get_counters"))
                hdlr.addFilter(VerbosityFilter("get_process_object"))
                hdlr.addFilter(VerbosityFilter("data_ops"))              
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 3 :
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("get_object_count"))
                hdlr.addFilter(VerbosityFilter("get_counters"))
                hdlr.addFilter(VerbosityFilter("get_process_object"))
                hdlr.addFilter(VerbosityFilter("data_ops"))                
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from all modules in the
                # "stores" subdirectory.
                hdlr.addFilter(VerbosityFilter("stores"))
                hdlr.addFilter(VerbosityFilter("datastore"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 2 :
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("get_object_count"))
                hdlr.addFilter(VerbosityFilter("get_counters"))
                hdlr.addFilter(VerbosityFilter("get_process_object"))
                hdlr.addFilter(VerbosityFilter("data_ops"))                
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
                hdlr.addFilter(VerbosityFilter("PassiveObjectOperations"))
                hdlr.addFilter(VerbosityFilter("get_object_count"))
                hdlr.addFilter(VerbosityFilter("get_counters"))
                hdlr.addFilter(VerbosityFilter("get_process_object"))
                hdlr.addFilter(VerbosityFilter("data_ops"))
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

            print("Checking for a running API service daemon.....", end=' ') 

            _proc_man = ProcessManagement(username = self.cld_attr_lst["objectstore"]["username"])

            _base_cmd = "\"" +  self.path + "/cbact\""
            _base_cmd += " --procid=" + self.pid
            _base_cmd += " --osp=" + dic2str(self.osci.oscp()) 
            _base_cmd += " --operation=cloud-api"

            # Ensure backwards-compatibility
            _bind_port = self.cld_attr_lst["api_defaults"]["bind_port"]
            if str(self.cld_attr_lst["api_defaults"]["bind_port"]).lower() == "false" :
                _bind_port = self.cld_attr_lst["api_defaults"]["port"]

            _base_cmd += " --apiport=" + _bind_port

            _bind_hostname = self.cld_attr_lst["api_defaults"]["bind_hostname"]
            if str(self.cld_attr_lst["api_defaults"]["bind_hostname"]).lower() == "false" :
                _bind_hostname = self.cld_attr_lst["api_defaults"]["hostname"]

            _base_cmd += " --apihost=" + _bind_hostname
            _base_cmd += " --syslogp=" + self.cld_attr_lst["logstore"]["port"]
            _base_cmd += " --syslogf=" + self.cld_attr_lst["logstore"]["api_facility"]
            _base_cmd += " --syslogh=" + self.cld_attr_lst["logstore"]["hostname"]
            _base_cmd += " --syslogr=" + self.cld_attr_lst["logstore"]["protocol"]
            _base_cmd += " --verbosity=" + self.cld_attr_lst["logstore"]["verbosity"]
            #_base_cmd += " --debug_host=localhost"
            _cmd = "screen -d -m bash -c '" + _base_cmd + "'"
            cbdebug(_cmd)
            
            _api_pid = _proc_man.start_daemon(_cmd, \
                                              self.cld_attr_lst["api_defaults"]["port"], \
                                              self.cld_attr_lst["api_defaults"]["protocol"], \
                                              conditional = True, \
                                              search_keywords = "cloud-api")

            if len(_api_pid) :
                if _api_pid[0].count("pnf") :
                    if len(_api_pid[0].split('-')) == 3 :
                        _x, _pid, _username = _api_pid[0].split('-') 
                    else :
                        _pid = str(_api_pid[0])
                        _username = "NA"
                    _msg = "Unable to start API service. Port "
                    _msg += self.cld_attr_lst["api_defaults"]["port"] + " is "
                    _msg += "already taken by process" + _pid + " (username "
                    _msg += _username + "). Please change "
                    _msg += "the port number in the section [API_DEFAULTS] of "
                    _msg += "cloud configuration file and try again."
                    _status = 8181

                    raise ProcessManagement.ProcessManagementException(_msg, _status)
                else :
                    _api_conn_string = "http://" + str(self.cld_attr_lst["api_defaults"]["hostname"])
                    _api_conn_string += ":" + str(self.cld_attr_lst["api_defaults"]["port"]) 
                    _api_pid = _api_pid[0]
                    _msg = "API Service daemon was successfully started. "
                    _msg += "The process id is " + str(_api_pid) + " (" + _api_conn_string + ").\n"
                    sys.stdout.write(_msg)

                    create_restart_script("restart_cb_api", _cmd, self.cld_attr_lst["logstore"]["username"], "cloud-api")
                    
                    try :
                        self.cld_attr_lst["api_defaults"]["file_identifier"] = self.cld_attr_lst["api_defaults"]["file_identifier"].strip()
                        _fn = "/tmp/cb_api_" + self.cld_attr_lst["api_defaults"]["username"] + self.cld_attr_lst["api_defaults"]["file_identifier"]
                        _fd = open(_fn, 'w')
                        _fd.write(_api_conn_string)
                        _fd.close()

                    except Exception as e :
                        _msg = "    Error writing file \"" + _fn  + "\":" + str(e)
                        print(_msg)
                        exit(4)
                    
            else :
                _msg = "\nAPI failed to start. To discover why, please run:\n\n"
                _msg += _base_cmd + " --logdest=console\n\n ... and report the bug."
                _status = 7161
                raise ProcessManagement.ProcessManagementException(_msg, _status)

            use_ssl = False
            cert = self.cld_attr_lst["gui_defaults"]["sslcert"]
            key = self.cld_attr_lst["gui_defaults"]["sslkey"]

            if cert and key :
                use_ssl = True

            print("Checking for a running GUI service daemon.....", end=' ')
            _base_cmd = "\"" + self.path + "/cbact\""
            _base_cmd += " --procid=" + self.pid
            _base_cmd += " --osp=" + dic2str(self.osci.oscp()) 
            _base_cmd += " --operation=cloud-gui"
            _base_cmd += " --apiport=" + str(self.cld_attr_lst["api_defaults"]["port"])
            _base_cmd += " --apihost=" + self.cld_attr_lst["api_defaults"]["hostname"]
            _base_cmd += " --guiport=" + str(self.cld_attr_lst["gui_defaults"]["port"])
            _base_cmd += " --guihost=" + self.cld_attr_lst["gui_defaults"]["hostname"]
            _base_cmd += " --guibranding=" + self.cld_attr_lst["gui_defaults"]["branding"]

            if use_ssl :
                _base_cmd += " --guisslcert=" + cert 
                _base_cmd += " --guisslkey=" + key 

            _base_cmd += " --syslogp=" + self.cld_attr_lst["logstore"]["port"]
            _base_cmd += " --syslogf=" + self.cld_attr_lst["logstore"]["gui_facility"]
            _base_cmd += " --syslogh=" + self.cld_attr_lst["logstore"]["hostname"]
            _base_cmd += " --syslogr=" + self.cld_attr_lst["logstore"]["protocol"]
            _base_cmd += " --verbosity=" + self.cld_attr_lst["logstore"]["verbosity"]

            # DaemonContext Doesn't work with Twisted 
            # Someone else will have to figure it out.
            _cmd = "screen -d -m -S cbgui" + self.cld_attr_lst["objectstore"]["username"] 
            _cmd += " bash -c '" + _base_cmd + "'"

            create_restart_script("restart_cb_gui", _base_cmd, self.cld_attr_lst["logstore"]["username"], "cloud-gui", vtycmd = True)

            cbdebug(_cmd)

            _gui_pid = _proc_man.start_daemon(_cmd, \
                                              self.cld_attr_lst["gui_defaults"]["port"], \
                                              self.cld_attr_lst["gui_defaults"]["protocol"], \
                                              conditional = True, \
                                              search_keywords = "cloud-gui")

            if len(_gui_pid) :
                if _gui_pid[0].count("pnf") :
                    _x, _pid, _username = _gui_pid[0].split('-') 
                    _msg = "Unable to start GUI service. Port "
                    _msg += self.cld_attr_lst["gui_defaults"]["port"] + " is "
                    _msg += "already taken by process" + _pid + " (username "
                    _msg += _username + "). Please change "
                    _msg += "the port number in [GUI_DEFAULTS] and try again."
                    _status = 8181
                    raise ProcessManagement.ProcessManagementException(_msg, _status)
                else :
                    _gui_pid = _gui_pid[0]
                    _msg = "GUI Service daemon was successfully started. "
                    url = "http"
                    if use_ssl :
                        url += "s"
                    url += "://" + self.cld_attr_lst["api_defaults"]["hostname"]
                    url += ":" + str(self.cld_attr_lst["gui_defaults"]["port"])
                    _msg += "The process id is " + str(_gui_pid) + ", "
                    _msg += "listening on port " + str(self.cld_attr_lst["gui_defaults"]["port"]) + '.'
                    _msg += " Full url is \"" + url + "\".\n\n"
                    sys.stdout.write(_msg)  
            else :
                _msg = "\nGUI failed to start. To discover why, please run:\n\n" + _base_cmd + " --logdest=console\n\n ... and report the bug."
                _msg += "\n\nAlternatively, if the problem is with 'screen', which"
                _msg += " daemonizes the above command, try this:\n\n"
                _msg += _cmd + "\n\n ... and report the bug."
                _status = 7161
                raise ProcessManagement.ProcessManagementException(_msg, _status)

            _status = 0
            _msg = "All processes started successfully"

        except ProcessManagement.ProcessManagementException as obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to start API and/or GUI daemons: " + _fmsg
                cberr(_msg, True)         
                exit(_status)       
            else :
                cbdebug(_msg)

    @trace
    def emptyline(self):
        '''
        TBD
        '''
        return

    def cleanup_comments(self, parameters) :
        ''' 
        TBD
        '''
        if parameters.count('#') :
            _processed_parameters = ''
            _parameters = parameters.split()

            for _parameter in _parameters :
                if not _parameter.count('#') :
                    _processed_parameters += _parameter + ' '
                else :
                    break
            parameters = _processed_parameters

        return parameters

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
            print(("Loading trace file commands from: " + f))
            try :
                r = file(f)
            except IOError as msg :
                print(("Could not open file: " + str(msg)))
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
                                       self.definitions, \
                                       "cloud-attach", \
                                       self.cld_attr_lst)

        if not _status  :
            self.do_cldlist("", False)

        print((message_beautifier(_msg)))

    @trace
    def do_monextract(self, parameters) :
        '''
        TBD
        '''
        if parameters.count("all") :
    
            _status, _msg, _object = self.passive_operations.monitoring_extractall(parameters, \
                                                                                   "mon-extractall")
        else :
    
            _status, _msg, _object = self.passive_operations.monitoring_extract(parameters, \
                                                                                "mon-extract")
        

        print((message_beautifier(_msg)))

    @trace
    def do_clddetach(self, parameters) :
        '''
        TBD
        '''        
        _status, _msg, _object = self.active_operations.clddetach(self.cld_attr_lst, \
                                                                  parameters, \
                                                                  "cloud-detach")

        if not _status and BaseObjectOperations.default_cloud == self.cld_attr_lst["name"] :
            self.do_cldlist("", False)
            
        print((message_beautifier(_msg)))

    @trace
    def do_clddefault(self, parameters) :
        '''
        TBD
        '''
        parameters = self.cleanup_comments(parameters)
        
        parameters = parameters.strip().split()

        default_cloud = ''
        walkthrough = ''
        
        if len(parameters) >= 1 :
            default_cloud = parameters[0]

        if len(parameters) >= 2 :
            walkthrough = ' ' + parameters[1]
        
        if default_cloud == '' :
            _msg = "Current default cloud is \"" + str(BaseObjectOperations.default_cloud)
            _msg += "\". Need cloud name to be set as default cloud or 'none' to unset."
            print((message_beautifier(_msg)))
        else :
            if default_cloud.lower() == "none" :
                BaseObjectOperations.default_cloud = None
                Cmd.prompt = "() "
            else :                
                BaseObjectOperations.default_cloud = default_cloud 
                Cmd.prompt = '(' +  str(BaseObjectOperations.default_cloud) + walkthrough + ") "

    @trace
    def do_cldlist(self, parameters, print_message = True) :
        '''
        TBD
        '''
        self.passive_operations = PassiveObjectOperations(self.osci, [])

        _status, _msg, _object = self.passive_operations.list_objects(self.cld_attr_lst, \
                                                                      parameters, \
                                                                      "cloud-list")
                        
        if len(_object["result"]) == 1 :
            _w = ''
            if "walkthrough" in _object["result"][0] :
                if _object["result"][0]["walkthrough"] == "true" :
                    _w = " WALKTHROUGH"
                
            self.do_clddefault(_object["result"][0]["name"] + _w)

        for _cloud_name_index in range(0, len(_object["result"])) :
            if _object["result"][_cloud_name_index]["name"] not in self.attached_clouds :
                self.attached_clouds.append(_object["result"][_cloud_name_index]["name"])

        self.passive_operations = PassiveObjectOperations(self.osci, self.attached_clouds)


        self.active_operations = ActiveObjectOperations(self.osci, \
                                                self.attached_clouds)

        if not self.options.remote :
            # Use a local copy of the API so that we can do local debugging
            self.api = API(self.pid, self.passive_operations, self.active_operations, None, False)
            self.install_functions()
                
        if print_message :
            print((message_beautifier(_msg)))

    @trace
    def do_waituntil(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_until(self.cld_attr_lst, \
                                                                    parameters, \
                                                                    "wait-until")
        print((message_beautifier(_msg)))

    @trace
    def do_waiton(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.wait_on(self.cld_attr_lst, \
                                                                 parameters, \
                                                                 "wait-on")
        print((message_beautifier(_msg)))

    @trace
    def do_msgpub(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.msgpub(self.cld_attr_lst, \
                                                                parameters, \
                                                                "msg-pub")
        print((message_beautifier(_msg)))

    @trace
    def do_shell(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.execute_shell(parameters, \
                                                                       "shell-execute")  

        print((message_beautifier(_msg)))

    @trace
    def do_appdev(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "ai_defaults run_application_scripts=false,debug_remote_commands=true", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_appundev(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "ai_defaults run_application_scripts=true,debug_remote_commands=false", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_vmdev(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "vm_defaults check_boot_complete=wait_for_0,transfer_files=false,run_generic_scripts=false,debug_remote_commands=true,check_ssh=false", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_vmundev(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "vm_defaults check_boot_complete=tcp_on_22,transfer_files=true,run_generic_scripts=true,debug_remote_commands=false,check_ssh=true", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_appnoload(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "ai_defaults dont_start_load_manager=true", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_appload(self, parameters) :
        '''
        TBD
        '''
        _status, _msg, _object = self.passive_operations.alter_object(self.cld_attr_lst, \
                                                                      "ai_defaults dont_start_load_manager=false", \
                                                                      "cloud-alter")

        print((message_beautifier(_msg)))

    @trace
    def do_echo(self, line):
        '''
        TBD
        '''
        print(line)

    @trace
    def do_quit(self, line) :
        return True

    @trace
    def do_exit(self, line) :
        return True

    @trace
    def do_help(self, args):
        if not help(args) :
            Cmd.do_help(self, args)

    @trace
    def do_pause(self, args):
        input("CLI was paused.Press any key to continue....")

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
                print(_line, end=' ')
        else :
            "No help available for " + args
            return False
        print('')
        return True
    else :
        return False


def get_options_from_env(options) :
    '''
    TBD
    '''
    if not options.config :
        _key = "CB_CONFIGURATION_FILE"
        if _key in os.environ :
            print("\n##########################################################################################")
            _msg = "CLI option \" --config=" + str(os.environ[_key]) + " set on the"
            _msg += " environment (" + str(_key) + ")."
            cbdebug(_msg, True)            
            print("##########################################################################################\n")
            options.config = os.environ[_key]

    return True
