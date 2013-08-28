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
    Created on Nov 27, 2011

    Active Object Operations Library

    @author: Marcio A. Silva, Michael R. Hines
'''
from os import chmod, access, F_OK
from random import choice, randint
from time import time, sleep
from subprocess import Popen, PIPE
from re import sub
from uuid import uuid5, NAMESPACE_DNS
from datetime import datetime

from lib.remote.process_management import ProcessManagement
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, dic2str, DataOpsException
from lib.auxiliary.value_generation import ValueGeneration
from lib.stores.stores_initial_setup import StoreSetupException
from lib.auxiliary.thread_pool import ThreadPool
from lib.auxiliary.data_ops import selective_dict_update
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions, get_available_clouds, rewrite_cloudconfig, rewrite_cloudoptions
from lib.clouds.shared_functions import CldOpsException
from base_operations import BaseObjectOperations

import copy
import threading
import os

class ActiveObjectOperations(BaseObjectOperations) :
    '''
    TBD
    '''
    @trace
    def cldattach(self, cld_attr_lst, params, definitions, cmd, \
                  uni_attr_lst = None) :
        '''
        TBD
        '''
        try :
            _fmsg = "unknown error: "
            _cld_name = None
            _status, _msg = self.parse_cli(cld_attr_lst, params, cmd)

            if _status :
                return self.package(_status, _msg, None)

            _attached_cloud_list = self.osci.get_object_list("ITSELF", "CLOUD")

            if _attached_cloud_list :
                _attached_cloud_list = list(_attached_cloud_list)
            else :
                _attached_cloud_list = []

            if cld_attr_lst["cloud_name"] in _attached_cloud_list :
                cld_attr_lst = self.get_cloud_parameters(cld_attr_lst["cloud_name"])
                
                _idmsg = "The \"" + cld_attr_lst["model"] + "\" cloud named \""
                _idmsg += cld_attr_lst["name"] + "\""
                _smsg = _idmsg + " was already attached to this experiment."
                _fmsg = _idmsg + " could not be attached to this experiment: "
                
                _time_attr_list = self.osci.get_object(cld_attr_lst["name"], "GLOBAL", False, "time", False)
                _expid = _time_attr_list["experiment_id"]
                _cld_name = cld_attr_lst["name"]
            else :
                '''
                 Three possibilities:
                 1. We parse a new cloud_definitions.txt from the CLI
                 2. We parse a new cloud_definitions from the API
                 3. We end-up re-parsing the default cloud_definitions.txt
                    - This one is equally important if you have multiple
                      clouds defined in a single definitions file
                      because all of the cloud templates are included by
                      default now - resulting in the unused ones being
                      thrown away below. So, it's necessary to re-parse
                      the file automatically and re-load them if a cloud
                      with a different model is attached in a single
                      configuration file.
                '''
                if cld_attr_lst["cloud_filename"] and not definitions :
                    fh = open(self.path + "/" + cld_attr_lst["cloud_filename"], 'r')
                    definitions = fh.read()
                    fh.close()
                    
                _attributes, _unused_definitions = parse_cld_defs_file(definitions)
                cld_attr_lst.update(_attributes)

                # Make a pass through config.py to verify that any available
                # CONFIGOPTION keywords are properly installed
                available_clouds = get_available_clouds(cld_attr_lst, return_all_options = True)

                rewrite_cloudoptions(cld_attr_lst, available_clouds, True)

                '''
                The ports for the Object Store, Log Store and Metric Store were
                already determined by the init method on CBCLI, since those are
                now part of the "universal" (i.e., "above the clouds") config. 
                These values, present on the universal configuration file, need 
                to be rewritten here.
                '''
                if uni_attr_lst :
                    cld_attr_lst["objectstore"].update(uni_attr_lst["objectstore"])
                    cld_attr_lst["logstore"].update(uni_attr_lst["logstore"])
                    cld_attr_lst["metricstore"].update(uni_attr_lst["metricstore"])

                rewrite_cloudconfig(cld_attr_lst)
                
                rewrite_cloudoptions(cld_attr_lst, available_clouds, False)
    
                ssh_filename = cld_attr_lst["space"]["credentials_dir"] + '/' + cld_attr_lst["space"]["ssh_key_name"]

                if not os.path.isfile(ssh_filename) :
                    if not os.path.isfile(cld_attr_lst["space"]["ssh_key_name"]) :
                        _fmsg = "Error: "
                        raise Exception("\n   Your " + cld_attr_lst["model"].upper() + "_SSH_KEY_NAME parameter is wrong:\n" + \
                                        "\n   Neither files exists: " + cld_attr_lst["space"]["ssh_key_name"] + " nor " + ssh_filename + \
                                        "\n   Please update your configuration and try again.\n");
                else :
                    cld_attr_lst["space"]["ssh_key_name"] = ssh_filename 

                _idmsg = "The \"" + cld_attr_lst["model"] + "\" cloud named \""
                _idmsg += cld_attr_lst["cloud_name"] + "\""
                _smsg = _idmsg + " was successfully attached to this "
                _smsg += "experiment."
                _fmsg = _idmsg + " could not be attached to this experiment: "

                _cld_ops = __import__("lib.clouds." + cld_attr_lst["model"] \
                                      + "_cloud_ops", fromlist = \
                                      [cld_attr_lst["model"].capitalize() + "Cmds"])
    
                _cld_ops_class = getattr(_cld_ops, \
                                         cld_attr_lst["model"].capitalize() + "Cmds")
    
                # User may have an empty VMC list. Need to be able to handle that.
                if cld_attr_lst["vmc_defaults"]["initial_vmcs"].strip() != "" :
                    _tmp_vmcs = cld_attr_lst["vmc_defaults"]["initial_vmcs"].split(",")

                    _vmcs = ""
                    for vmc in _tmp_vmcs :
                        _vmcs += vmc
                        if not vmc.count(":") :
                            _vmcs += ":sut"
                        _vmcs += ","

                    _vmcs = _vmcs[:-1]
                    cld_attr_lst["vmc_defaults"]["initial_vmcs"] = _vmcs
                    _initial_vmcs = str2dic(_vmcs)
                else :
                    _initial_vmcs = []
                    _cld_conn = _cld_ops_class(self.pid, None, None)
    
                _msg = "Attempting to connect to all VMCs described in the cloud "
                _msg += "defaults file, in order to check the access parameters "
                _msg += "and security credentials"
                cbdebug(_msg)
    
                for _vmc_entry in _initial_vmcs :
                    _cld_conn = _cld_ops_class(self.pid, None, None)
                    _cld_conn.test_vmc_connection(_vmc_entry.split(':')[0], \
                                                  cld_attr_lst["vmc_defaults"]["access"], \
                                                  cld_attr_lst["vmc_defaults"]["credentials"], \
                                                  cld_attr_lst["vmc_defaults"]["key_name"], \
                                                  cld_attr_lst["vmc_defaults"]["security_groups"], \
                                                  cld_attr_lst["vm_templates"],
                                                  cld_attr_lst["vm_defaults"])

    
                _all_global_objects = cld_attr_lst.keys()
                cld_attr_lst["client_should_refresh"] = str(0.0)
    
                _remove_from_global_objects = [ "name", "model", "user-defined", \
                                               "dependencies", "cloud_filename", \
                                               "cloud_name", "objectstore", \
                                               "command_originated", "state", \
                                               "tracking", "channel", "sorting", \
                                               "ai_arrived", "ai_departed", \
                                               "ai_failed", "ai_reservations" ]
    
                for _object in _remove_from_global_objects :
                    if _object in _all_global_objects :
                        _all_global_objects.remove(_object)
    
                cld_attr_lst["all"] = ','.join(_all_global_objects)
                cld_attr_lst["all_vmcs_attached"] = "false"
                cld_attr_lst["regression"] = str(cld_attr_lst["space"]["regression"]).strip().lower()
                cld_attr_lst["description"] = _cld_conn.get_description()
                cld_attr_lst["username"] = cld_attr_lst["time"]["username"]
                cld_attr_lst["start_time"] = str(int(time()))
                cld_attr_lst["client_should_refresh"] = str(0) 
                cld_attr_lst["time"]["hard_reset"] = uni_attr_lst["time"]["hard_reset"] if "hard_reset" in uni_attr_lst["time"] else False
                cld_attr_lst["space"]["tracefile"] = uni_attr_lst["space"]["tracefile"] if "tracefile" in uni_attr_lst["space"] else "none"

                # While setting up the Object Store, check for free ports for the 
                # API, GUI, and Gmetad (Host OS performance data collection)
                # daemons, using their indicated ports as the base port
                _proc_man =  ProcessManagement(username = cld_attr_lst["username"] , cloud_name = cld_attr_lst["cloud_name"])
                cld_attr_lst["mon_defaults"]["collector_host_multicast_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_multicast_port"], protocol = "tcp")
                cld_attr_lst["mon_defaults"]["collector_host_aggregator_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_aggregator_port"], protocol = "tcp")
                cld_attr_lst["mon_defaults"]["collector_host_summarizer_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_summarizer_port"], protocol = "tcp")
    
                os_func, ms_func, unused  = load_store_functions(cld_attr_lst)

                os_func(cld_attr_lst, "initialize", cloud_name = cld_attr_lst["name"])
                ms_func(cld_attr_lst, "initialize")
    
                # This needs to be better coded later. Right now, it is just a fix to avoid
                # the problems caused by the fact that git keeps resetting RSA's private key
                # back to 644 (which are too open).
                chmod(cld_attr_lst["space"]["ssh_key_name"], 0600)
    
                _expid = cld_attr_lst["time"]["experiment_id"]
                _cld_name = cld_attr_lst["name"]
    
            _status = 0
    
            _msg = _smsg + "\nThe experiment identifier is " + _expid + "\n"
            cld_attr_lst["cloud_name"] = _cld_name

        except ImportError, msg :
            _status = 8
            _msg = _fmsg + str(msg)

        except OSError, msg :
            _status = 8
            _msg = _fmsg + str(msg)

        except AttributeError, msg :
            _status = 8
            _msg = _fmsg + str(msg)

        except DataOpsException, obj :
            _status = 8
            _msg = _fmsg + str(msg)

        # Chicken and the egg problem:
        # Can't catch this exception if the import fails
        # inside of the try/catch ... find another solution
        #except _cld_ops_class.CldOpsException, obj :
        #    _status = str(obj.msg)
        #    _msg = _fmsg + str(obj.msg)

        except StoreSetupException, obj :
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)

        except ProcessManagement.ProcessManagementException, obj :
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)

        except Exception, e :
            _status = 23
            _msg = _fmsg + str(e)
        
        finally :
            if _status :
                cberr(_msg)
            else :
                cbdebug(_msg)
    
            return self.package(_status, _msg, cld_attr_lst)

    @trace    
    def clddetach(self, cld_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _update_frequency = 5
            _max_tries = 10
            _obj_type = command.split('-')[0].upper()

            _status, _fmsg = self.parse_cli(cld_attr_list, parameters, command)

            if not _status :
                _cld_attr_list = self.osci.get_object(cld_attr_list["name"], "CLOUD", False, cld_attr_list["name"], False)

                self.update_cloud_attribute(cld_attr_list["name"], "client_should_refresh", str(0))

                _msg = "Waiting for all active AIDRS daemons to finish gracefully...." 
                cbdebug(_msg, True)

                _curr_tries = 0
                _aidrs_list = self.osci.get_object_list(cld_attr_list["name"], "AIDRS")
                while _aidrs_list :
                    cbdebug("Still waiting.... ")
                    _aidrs_list = self.osci.get_object_list(cld_attr_list["name"], "AIDRS")

                    if _aidrs_list and _curr_tries < _max_tries :
                        for _aidrs_uuid in _aidrs_list :
                            _aidrs_attr_list = self.osci.get_object(cld_attr_list["name"], "AIDRS", \
                                                                 False, \
                                                                 _aidrs_uuid, \
                                                                 False)

                            _x_attr_list = {}
                            _parameters = cld_attr_list["name"] + ' ' + _aidrs_attr_list["name"] + " true"
                            self.objdetach(_x_attr_list, _parameters, "aidrs-detach")

                        sleep(_update_frequency)
                        _curr_tries += 1
                    else :
                        break
                
                if _curr_tries >= _max_tries :
                    _msg = "Some AIDRS (daemons) did not die after " 
                    _msg += str(_max_tries * _update_frequency) + " seconds."
                    _msg += "Please kill them manually after the end of the "
                    _msg += "cloud detachment process (a \"pkill -f aidrs-submit\""
                    _msg += " should suffice)."
                else :
                    _msg = "All AIDRS (daemons and objects were removed)." 
                cbdebug(_msg, True)
                sleep (_update_frequency) 

                _curr_tries = 0
                for _object_typ in [ "VMCRS", "FIRS", "AI", "VM", "VMC" ] :            
                    _msg = "Giving extra time for all " + _object_typ + "s to " 
                    _msg += "finish attachment/detachment gracefully......"
                    cbdebug(_msg)
                    
                    _active = int(self.get_object_count(cld_attr_list["name"], _object_typ, "ARRIVING"))
                    _active += int(self.get_object_count(cld_attr_list["name"], _object_typ, "DEPARTING"))

                    while _active :
                        cbdebug(str(_active) + ' ' + _object_typ + "s are still attaching/detaching....")
                    
                        _active = int(self.get_object_count(cld_attr_list["name"], _object_typ, "ARRIVING"))
                        _active += int(self.get_object_count(cld_attr_list["name"], _object_typ, "DEPARTING"))
    
                        if _active :
                            if _curr_tries < _max_tries :
                                sleep (_update_frequency)
                                _curr_tries += 1
                            else :
                                break
                
                    if _curr_tries >= _max_tries :
                        _msg = "Some " + _obj_type + " attach (daemons) did not die after " 
                        _msg += str(_max_tries * _update_frequency) + " seconds."
                        _msg += "Please kill them manually after the end of the "
                        _msg += "cloud detachment process (a \"pkill -f " + _obj_type.lower() + "-attach\""
                        _msg += " should suffice)."
                    else :
                        _msg = "Done"
                    cbdebug(_msg)

                    _msg = "Removing all " + _object_typ + " objects attached to"
                    _msg += " this experiment."
                    cbdebug(_msg, True)
                    
                    _obj_list = self.osci.get_object_list(cld_attr_list["name"], _object_typ)
                    if _obj_list :
                        for _obj_uuid in _obj_list :
                            _obj_attr_list = self.osci.get_object(cld_attr_list["name"], _object_typ, False, _obj_uuid, False)
                            _x_attr_list = {}
                            if BaseObjectOperations.default_cloud is not None :
                                _parameters = _obj_attr_list["name"] + " true"
                            else :
                                _parameters = cld_attr_list["name"] + ' ' + _obj_attr_list["name"] + " true"

                            self.objdetach(_x_attr_list, _parameters, _object_typ.lower() + "-detach")

                        cbdebug("Done", True)
                
                sleep (_update_frequency)

                _proc_man = ProcessManagement(username = _cld_attr_list["username"], cloud_name = cld_attr_list["name"])
                _gmetad_pid = _proc_man.get_pid_from_cmdline("gmetad.py")

                if len(_gmetad_pid) :
                    cbdebug("Killing the running Host OS performance monitor (gmetad.py)......", True)
                    _proc_man.kill_process("gmetad.py")

                _msg = "Removing all contents from Object Store (GLOBAL objects,"
                _msg += "VIEWS, etc.)"
                cbdebug(_msg, True)
                
                self.osci.clean_object_store(cld_attr_list["name"], _cld_attr_list)

                _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except ProcessManagement.ProcessManagementException, obj :
            print("AQUI")
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:
            if _status :
                _msg = "Cloud " + cld_attr_list["name"] + " could not be " 
                _msg += "detached from this experiment : " + _fmsg
                cberr(_msg)
            else :
                _msg = "Cloud " + cld_attr_list["name"] + " was successfully " 
                _msg += "detached from this experiment."
                cbdebug(_msg)

            return self.package(_status, _msg, False)

    def hostfail_repair(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None
            
            obj_attr_list["name"] = "undefined"
            obj_attr_list["target_state"] = "undefined"
            _host_already_failed = False
            _host_repaired = False
            _obj_type, _target_state = command.upper().split('-')
            
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status = 101

                _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                       "HOST", \
                                                       True, \
                                                       obj_attr_list["name"], \
                                                       False)
 
 
                _proc_man = ProcessManagement(username = _host_attr_list["username"], \
                                              cloud_name = obj_attr_list["cloud_name"], \
                                              hostname = _host_attr_list["cloud_ip"], \
                                              priv_key = _host_attr_list["identity"])

    #                _firs_defaults = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "firs_defaults", False)
    
                _failed_hosts = self.osci.get_list(obj_attr_list["cloud_name"], _obj_type, "FAILED_HOSTS", True)

                for _failed_host in _failed_hosts :

                    if _failed_host[0] == obj_attr_list["name"] :
                        if _target_state.lower() == "fail" :
                            _msg = "Host \"" + obj_attr_list["name"] + "\" is "
                            _msg += "already at the \"failed\" state."
                            cbdebug(_msg, True)
                            _host_already_failed = True                            
                            _status = 0
                        elif _target_state.lower() == "repair" :
                            _cmd = "service " + obj_attr_list["service"] +  " restart" 
            
                            _msg = "Repairing a fault on host " + obj_attr_list["name"]
                            _msg += " by executing the command \"" + _cmd + "\""
                            cbdebug(_msg, True)

                            _host_repaired = True

                            if "simulated" in _host_attr_list and _host_attr_list["simulated"].lower() != "true" :
                                _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)
                            else :
                                _status = 0
                                
                            if not _status :
                                self.osci.remove_from_list(obj_attr_list["cloud_name"], \
                                                           "HOST", \
                                                           "FAILED_HOSTS", \
                                                           obj_attr_list["name"], \
                                                           True)
                        break

                if _target_state.lower() == "fail" and not _host_already_failed :

                    _cmd = "pkill -f " + obj_attr_list["service"] 
    
                    _msg = "Injecting a fault on host " + obj_attr_list["name"]
                    _msg += " by executing the command \"" + _cmd + "\""
                    cbdebug(_msg, True)

                    if "simulated" in _host_attr_list and _host_attr_list["simulated"].lower() != "true" :
                        _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)
                    else :
                        _status = 0

                    if not _status :
                        self.osci.add_to_list(obj_attr_list["cloud_name"], \
                                              "HOST", "FAILED_HOSTS", \
                                              obj_attr_list["name"], int(time()))            
    
                if _target_state.lower() == "repair" and \
                not _host_already_failed and not _host_repaired :
                    _msg = "Host \"" + obj_attr_list["name"] + "\" is "
                    _msg += "not at the \"failed\" state. No need for repair."
                    cbdebug(_msg, True)
                    _host_already_failed = True                            
                    _status = 0
    
                _result = obj_attr_list

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "HOST \"" + obj_attr_list["name"] + "\" could"
                _msg += " not be " + _target_state.lower() + "ed on this "
                _msg += "experiment: " + _fmsg
                cberr(_msg)
            else :
                if _target_state.lower() == "repair" :
                    _target_state = "attached"
                else :
                    _target_state = "fail"
                self.osci.set_object_state(obj_attr_list["cloud_name"], "HOST", \
                                           _host_attr_list["uuid"], _target_state)                
                _msg = "HOST \"" + obj_attr_list["name"] + "\" was "
                _msg += "successfully " + _target_state.replace("ed",'') + "ed "
                _msg += "on this experiment." 
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace    
    def vmccleanup(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None
            obj_attr_list["name"] = "undefined"
            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :                    
                    _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])            
                    _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])
    
                    _status, _fmsg = _cld_conn.vmccleanup(obj_attr_list)
                    _result = obj_attr_list

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "VMC object named \"" + obj_attr_list["name"] + "\" could"
                _msg += " not be cleaned up on this experiment: "
                _msg += _fmsg
                cberr(_msg)
            else :
                _msg = "VMC object named \"" + obj_attr_list["name"] + "\" was "
                _msg += "sucessfully cleaned up on this experiment." 
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace    
    def vmcattachall(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _smsg = ''
            
            obj_attr_list["name"] = "undefined"
            
            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            _vmc_defaults = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                 "vmc_defaults", False)

            _cloud_parameters = self.get_cloud_parameters(obj_attr_list["cloud_name"])

            if _cloud_parameters["all_vmcs_attached"].lower() == "false" :
                _obj_type = command.split('-')[0].upper()
                _obj_attr_list = {}

                if BaseObjectOperations.default_cloud is not None:
                    _obj_attr_list["cloud_name"] = BaseObjectOperations.default_cloud
                else :
                    _obj_attr_list["cloud_name"] = parameters.split()[0]

                _obj_attr_list["command_originated"] = int(time())
                _obj_attr_list["command"] = "vmcattach " + obj_attr_list["cloud_name"] + " all"
                _obj_attr_list["name"] = "all"

                _temp_attr_list = obj_attr_list["temp_attr_list"]

                self.get_counters(_obj_attr_list["cloud_name"], _obj_attr_list)
                self.record_management_metrics(_obj_attr_list["cloud_name"], "VMC", _obj_attr_list, "trace")

                _obj_attr_list["parallel_operations"] = {}
                _vmc_counter = 0
                if _vmc_defaults["initial_vmcs"].strip() == "" :
                    _fmsg = "Your configuration template files are probably included in the wrong order."
                    _status = 12
                    raise self.ObjectOperationException(_fmsg, 12)

                else :
                    for _vmc_element in _vmc_defaults["initial_vmcs"].split(',') :
                        _vmc_vars = _vmc_element.split(":")
                        _vmc_cloud_name = _vmc_vars[0]
                        if len(_vmc_vars) == 2 :
                            _pools = _vmc_vars[1]
                        else :
                            _pools = "sut"
                        _obj_attr_list["parallel_operations"][_vmc_counter] = {}
                        _obj_attr_list["parallel_operations"][_vmc_counter]["uuid"] = str(uuid5(NAMESPACE_DNS, str(randint(0,10000000000000000)))).upper()
                        _obj_attr_list["parallel_operations"][_vmc_counter]["parameters"] = _obj_attr_list["cloud_name"]  + ' ' + _vmc_cloud_name + ' ' + _pools + ' ' + _temp_attr_list
                        _obj_attr_list["parallel_operations"][_vmc_counter]["operation"] = "vmc-attach"
                        _vmc_counter += 1

                    _obj_attr_list["attach_parallelism"] = _vmc_counter            
                    _obj_attr_list["cloud_name"] = obj_attr_list["cloud_name"]
                    _status, _fmsg = self.parallel_obj_operation("attach", _obj_attr_list)

                    if not _status :
                        self.update_cloud_attribute(_obj_attr_list["cloud_name"], "all_vmcs_attached", "true")

                        self.update_host_os_perfmon(_obj_attr_list)

                        _status = 0
            else :
                _smsg = " It looks like all VMCs were already attached." 
                #_smsg = " There is "
                #_smsg += "no need to re-attach them. Check it with the "
                #_smsg += "\"vmclist " + obj_attr_list["cloud_name"] + "\" command. If that is in "
                #_smsg += "error, please issue the command \" cldalter vmc_defaults"
                #_smsg += " all_vmcs_attached=false " + obj_attr_list["cloud_name"] + "\" and try again"
                _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "Failure while attaching all VMCs to this "
                _msg += "experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "All VMCs successfully attached to this experiment." + _smsg
                cbdebug(_msg)

            return self.package(_status, _msg, self.get_cloud_parameters(obj_attr_list["cloud_name"]))

    @trace
    def pre_attach_vmc(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100   
            _fmsg = "An error has occurred, but no error message was captured"
            _conf_vmc_list = {}

            _monitor_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                      "mon_defaults", False)

            obj_attr_list["collect_from_host"] = _monitor_attr_list["collect_from_host"]
            
            if "initial_vmcs" in obj_attr_list and obj_attr_list["initial_vmcs"].strip() != "":
                for _vmc_element in obj_attr_list["initial_vmcs"].split(',') :
                    _vmc_vars = _vmc_element.split(":")
                    _vmc_cloudname = _vmc_vars[0]
                    if len(_vmc_vars) == 2 :
                        _pools = _vmc_vars[1]
                    else :
                        _pools = "sut"
                    _conf_vmc_list[_vmc_cloudname] = sub(r';', ',', _pools)
    
                if obj_attr_list["name"] in _conf_vmc_list :
                    obj_attr_list["pool"] = _conf_vmc_list[obj_attr_list["name"]]
                else :
                    obj_attr_list["pool"] = "sut"

                del obj_attr_list["initial_vmcs"]

            else :
                obj_attr_list["pool"] = "none"
                
            obj_attr_list["nr_vms"] = 0
                
            self.initialize_metric_name_list(obj_attr_list)

            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC pre-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMC pre-attachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_attach_vm(self, obj_attr_list) :
        _status = 100
        _pool_selected = False
        _fmsg = "An error has occurred, but no error message was captured"
        _vm_location = obj_attr_list["pool"]
        _cn = obj_attr_list["cloud_name"]
        del obj_attr_list["pool"]

        try :
            _vmc_pools = list(self.osci.get_list(_cn, "GLOBAL", "vmc_pools"))
            _hosts = list(self.osci.get_list(_cn, "GLOBAL", "host_names"))
            
            '''
            Blacklists are for Anti-Colocation. Please don't break them. =) 
            FT depends on anti-colocation. Others might also in the future.
            '''
            if "vmc_pool_blacklist" in obj_attr_list.keys() :
                _blacklist = obj_attr_list["vmc_pool_blacklist"].split(",")
                for _bad_pool in _blacklist :
                    for _idx in range(0, len(_vmc_pools)) :
                        if _bad_pool.upper() == _vmc_pools[_idx] :
                            del _vmc_pools[_idx]
                            break
            elif "host_name_blacklist" in obj_attr_list.keys() :
                _blacklist = obj_attr_list["host_name_blacklist"].split(",")
                for _bad_host in _blacklist :
                    for _idx in range(0, len(_hosts)) :
                        if _bad_host.upper() == _hosts[_idx] :
                            del _hosts[_idx]
                            break

            if "vmc_pool" in obj_attr_list :
                _vm_location = obj_attr_list["vmc_pool"]

            if "host_name" in obj_attr_list :
                _vm_location = obj_attr_list["host_name"]

            if _vm_location.upper() != "AUTO"  :
                
                if _vm_location.upper() in _hosts :
                    _host_attr_list = self.osci.get_object(_cn, \
                                                           "HOST", \
                                                           True, \
                                                           "host_" + _vm_location.lower(), \
                                                           False)
                    
                    obj_attr_list["vmc_pool"] = _host_attr_list["pool"]
                    obj_attr_list["host_name"] = _vm_location.lower()
                    obj_attr_list["vmc"] = _host_attr_list["vmc"]
                    _pool_selected = True
                
                elif _vm_location.upper() in _vmc_pools :
                    obj_attr_list["vmc_pool"] = _vm_location.upper()
                    _pool_selected = True
                else :
                    obj_attr_list["vmc"] = _vm_location

            # Do NOT use "else" here. _vm_location can have its value changed
            # in the previous if statement
            if _vm_location.upper() == "AUTO"  :

                if not len(_vmc_pools) :
                    _status = 181
                    _fmsg = "No additional VMC pools available for VM creation"
                    raise self.osci.ObjectStoreMgdConnException(_fmsg, _status)

                # Will have to think about changing it later. It is quite 
                # inefficient, considering that there is a "pool" attribute
                # being loaded already
                for _key in obj_attr_list.keys() :
                    if _key.count("pref_pool") :
                        _pref_pool_role = _key.split("_pref_pool")[0]
                        _pref_pool_name = obj_attr_list[_key].upper()
                        if obj_attr_list["role"].count(_pref_pool_role) and _pref_pool_name in _vmc_pools :
                            obj_attr_list["vmc_pool"] = _pref_pool_name
                            _pool_selected = True
                            break
                        
                if not _pool_selected :
                    if "SUT" in _vmc_pools :
                        obj_attr_list["vmc_pool"] = "SUT"
                    else :
                        obj_attr_list["vmc_pool"] = choice(_vmc_pools)

            if not "vmc" in obj_attr_list and "vmc_pool" in obj_attr_list :
                _vmc_uuid_list = self.osci.query_by_view(_cn, "VMC", "BYPOOL", \
                                                         obj_attr_list["vmc_pool"])
    
                if len(_vmc_uuid_list) :
                    obj_attr_list["vmc"] = choice(_vmc_uuid_list).split('|')[0]
                    
                    if not obj_attr_list["vmc"] :
                        _fmsg = "No VMCs on pool \"" +  obj_attr_list["vmc_pool"] + "\""
                        _fmsg += " are available for VM creation."
                        _status = 181                    
                        raise self.osci.ObjectStoreMgdConnException(_fmsg, _status)

                else :
                    self.osci.remove_from_list(_cn, "GLOBAL", "vmc_pools", obj_attr_list["vmc_pool"])
                    _fmsg = "An empty VMC pool was selected. This pool was already "
                    _fmsg += "removed from the list of pools."
                    cbdebug(_fmsg)
                    _status = 1819
                    raise self.osci.ObjectStoreMgdConnException(_fmsg, _status)

            _object_exists_uuid = self.osci.object_exists(_cn, "VMC", obj_attr_list["vmc"], True)
            
            if _object_exists_uuid :
                _vmc_attr_list = self.osci.get_object(_cn, "VMC", False, _object_exists_uuid, False)
            else :
                if "vmc_pool" in obj_attr_list :
                    _fmsg = "The VMC pool (" + obj_attr_list["vmc_pool"] + \
                            ") you requested doesn't exist. Try again."
                else :
                    _fmsg = "The VMC name (" + obj_attr_list["vmc"] + \
                            ") you requested doesn't exist. Try again."
                _status = 5333
                raise self.osci.ObjectStoreMgdConnException(_fmsg, _status)

            obj_attr_list["vmc_max_vm_reservations"] = _vmc_attr_list["max_vm_reservations"]
            obj_attr_list["discover_hosts"] = _vmc_attr_list["discover_hosts"]
            obj_attr_list["vmc_name"] = _vmc_attr_list["name"]
            obj_attr_list["vmc_pool"] = _vmc_attr_list["pool"].upper()
            obj_attr_list["vmc"] = _vmc_attr_list["uuid"]
            obj_attr_list["vmc_cloud_ip"] = _vmc_attr_list["cloud_ip"]
            obj_attr_list["migrate_supported"] = _vmc_attr_list["migrate_supported"]
            obj_attr_list["protect_supported"] = _vmc_attr_list["protect_supported"]
            obj_attr_list["vmc_access"] = _vmc_attr_list["access"]

            _vm_templates = self.osci.get_object(_cn, "GLOBAL", False, "vm_templates", False)

            _vm_template_attr_list = str2dic(_vm_templates[obj_attr_list["role"]])
            
            if obj_attr_list["size"] == "load_balanced_default" :
                if "lb_size" in _vm_template_attr_list :
                    obj_attr_list["size"] = _vm_template_attr_list["lb_size"]
                else :
                    obj_attr_list["size"] = "default"
                
            selective_dict_update(obj_attr_list, _vm_template_attr_list)

            _status = 0

            if not _status :
                if "qemu_debug_port_base" in obj_attr_list :
                    _status, _fmsg = self.auto_allocate_port("qemu_debug", obj_attr_list, "VMC", obj_attr_list["vmc"], obj_attr_list["vmc_cloud_ip"])
                
        except KeyError, msg :
            _status = 40
            _fmsg = "Unknown VM role: " + str(msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except DataOpsException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM pre-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM pre-attachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_attach_ai(self, obj_attr_list) :
        '''
        TBD
        '''
        #Don't want exceptions to be caught here. Let them propagate to
        #upper-level handling code....
        
        if "save_on_attach" in obj_attr_list and obj_attr_list["save_on_attach"].lower() == "true" :
            cbdebug("Warning: the VMs of this VApp will be saved after attachment. " + \
                    "If this is not what you want, then CTRL-C and use cldalter command.", True)

        _status = 100
        _post_speculative_admission_control = False
        _fmsg = "An error has occurred, but no error message was captured"
            
        #Now start the exceptions...
        try :
                    
            _vmc_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC")
            if not _vmc_list :
                _msg = "No VMC attached to this experiment. Please "
                _msg += "attach at least one VMC, or the VM creations triggered "
                _msg += "by this AI attachment operation will fail."
                raise self.osci.ObjectStoreMgdConnException(_msg, _status)

            if "aidrs" in obj_attr_list and obj_attr_list["aidrs"].lower() != "none" :

                _object_exists = self.osci.object_exists(obj_attr_list["cloud_name"], "AIDRS", obj_attr_list["aidrs"], False)

                if _object_exists :
                    _aidrs_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "AIDRS", False, \
                                                          obj_attr_list["aidrs"], False)
        
                    obj_attr_list["max_ais"] = _aidrs_attr_list["max_ais"]
                    obj_attr_list["aidrs_name"] = _aidrs_attr_list["name"]
                    obj_attr_list["pattern"] = _aidrs_attr_list["pattern"]

                else :
                    obj_attr_list["max_ais"] = 1
                    obj_attr_list["aidrs_name"] = "orphan (" + obj_attr_list["aidrs"] + ")"
                    obj_attr_list["pattern"] = "unknown"
            else :
                    obj_attr_list["max_ais"] = 1
                    obj_attr_list["aidrs_name"] = "none"
                    obj_attr_list["pattern"] = "none"
                                        
            _ai_templates = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                 "ai_templates", False)
            _ai_template_attr_list = {}
            _app_type = obj_attr_list["type"]
            for _attrib, _val in _ai_templates.iteritems() :
                if _attrib.count(_app_type) :
                    _ai_template_attr_list[_attrib] = _val

            if not len(_ai_template_attr_list) :
                _status = 40
                _msg = "Unknown AI type: " + _app_type
                raise self.ObjectOperationException(_msg, _status)
            
            # This is just a trick to remove the application name from the
            # start of the AI attributes on the template. 
            # For instance, instead of adding the key  "hadoop_driver_hadoop_setup1"
            # to the list of attributes of the AI we want the key to be in fact 
            # only "hadoop_driver_hadoop_setup1"
            _x = len(_app_type) + 1

            for _key, _value in _ai_template_attr_list.iteritems() :
                if _key.count(_app_type) :
                    if _key[_x:] in obj_attr_list : 
                        if obj_attr_list[_key[_x:]] == "default" :
                            obj_attr_list[_key[_x:]] = _value
                    else :
                        obj_attr_list[_key[_x:]] = _value
                    
            if "lifetime" in obj_attr_list and obj_attr_list["lifetime"] != "none" :
                _value_generation = ValueGeneration(self.pid)
                obj_attr_list["lifetime"] = int(_value_generation.get_value(obj_attr_list["lifetime"]))

            if not "base_type" in obj_attr_list :
                obj_attr_list["base_type"] = obj_attr_list["type"]

            self.create_vm_list_for_ai(obj_attr_list)
     
            self.speculative_admission_control(obj_attr_list)

            _post_speculative_admission_control = True

            self.osci.pending_object_set(obj_attr_list["cloud_name"], \
                 "AI", obj_attr_list["uuid"], "status", "Creating VMs: Switch tabs for tracking..." )
            
            if obj_attr_list["vm_creation"].lower() == "explicit" : 
                _status, _fmsg = self.parallel_obj_operation("attach", obj_attr_list)
                
            if not _status :
                _vm_uuid_list = obj_attr_list["vms"].split(',')
                obj_attr_list["vms"] = ''

                for _vm_uuid in _vm_uuid_list :
                    _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                         "VM", \
                                                         False, \
                                                         _vm_uuid, \
                                                         False)

                    obj_attr_list["vms"] += _vm_uuid + '|' + _vm_attr_list["role"]
                    obj_attr_list["vms"] += '|' + _vm_attr_list["name"] + ','

                obj_attr_list["vms"] = obj_attr_list["vms"][:-1]
                    
                _status = 0

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM objects need to be aborted...", True)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 41
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ValueGeneration.ValueGenerationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except DataOpsException, obj :
            _status = 43
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AI pre-attachment operations failure: " + _fmsg
                cberr(_msg)

                if _post_speculative_admission_control :
                    self.admission_control("AI", obj_attr_list, "rollbackattach")
                
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AI pre-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def pre_attach_aidrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _fmsg = "An error has occurred, but no error message was captured"

            _vmc_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC")
            if not _vmc_list :
                _msg = "No VMC attached to this experiment. Please "
                _msg += "attach at least one VMC, or the VM creations triggered "
                _msg += "by the AIs instantiated by the AS attachment operation "
                _msg += "will fail."
                raise self.osci.ObjectStoreMgdConnException(_msg, _status)
                            
            _aidrs_templates = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                 "aidrs_templates", False)
            _aidrs_templates["patterns"] = []
            for _element in _aidrs_templates :
                if _element.count("iait") :
                    _aidrs_templates["patterns"].append(_element[0:-5])
            
            obj_attr_list["nr_ais"] = 0

            if obj_attr_list["pattern"] in _aidrs_templates["patterns"] :
                # This is just a trick to remove the application name from the
                # start of the AIDRS attributes on the template. 
                # For instance, instead of adding the key  "simpledt_max_ais"
                # to the list of attributes of the AS we want the key to be in fact 
                # only "max_ais"
                _x = len(obj_attr_list["pattern"]) + 1
            
                for _key, _value in _aidrs_templates.iteritems() :
                    if _key.count(obj_attr_list["pattern"]) :
                        if _key[_x:] in obj_attr_list : 
                            if obj_attr_list[_key[_x:]] == "default" :
                                obj_attr_list[_key[_x:]] = _value
                        else :
                            obj_attr_list[_key[_x:]] = _value

                obj_attr_list["arrival"] = int(time())

                _status = 0
            else :
                _fmsg = "Unknown pattern: " + obj_attr_list["pattern"] 

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AIDRS pre-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AIDRS pre-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def pre_attach_vmcrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :

            _status = 100

            _fmsg = "An error has occurred, but no error message was captured"
                            
            _vmcrs_templates = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                    "vmcrs_templates", False)

            _vmcrs_templates["patterns"] = []
            for _element in _vmcrs_templates :
                if _element.count("ivmcat") :
                    _vmcrs_templates["patterns"].append(_element[0:-7])

            obj_attr_list["nr_simultaneous_cap_reqs"] = 0
            obj_attr_list["nr_total_cap_reqs"] = 0

            if _vmcrs_templates["patterns"].count(obj_attr_list["pattern"]) :
                # This is just a trick to remove the application name from the
                # start of the AIDRS attributes on the template. 
                # For instance, instead of adding the key "simpledt_max_ais"
                # to the list of attributes of the AS we want the key to be in fact 
                # only "max_ais"
                _x = len(obj_attr_list["pattern"]) + 1
            
                for _key, _value in _vmcrs_templates.iteritems() :
                    if _key.count(obj_attr_list["pattern"]) :
                        if _key[_x:] in obj_attr_list : 
                            if obj_attr_list[_key[_x:]] == "default" :
                                obj_attr_list[_key[_x:]] = _value
                        else :
                            obj_attr_list[_key[_x:]] = _value

                obj_attr_list["arrival"] = int(time())

                _status = 0
            else :
                _fmsg = "Unknown pattern: " + obj_attr_list["pattern"] 

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMCRS pre-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMCRS pre-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    def pre_attach_firs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :

            _status = 100

            _fmsg = "An error has occurred, but no error message was captured"
                            
            _firs_templates = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                    "firs_templates", False)

            _firs_templates["patterns"] = []
            for _element in _firs_templates :
                if _element.count("ifat") :
                    _firs_templates["patterns"].append(_element[0:-4])

            obj_attr_list["nr_simultaneous_faults"] = 0
            obj_attr_list["nr_total_faults"] = 0

            if _firs_templates["patterns"].count(obj_attr_list["pattern"]) :
                # This is just a trick to remove the application name from the
                # start of the AIDRS attributes on the template. 
                # For instance, instead of adding the key "simpledt_max_ais"
                # to the list of attributes of the AS we want the key to be in fact 
                # only "max_ais"
                _x = len(obj_attr_list["pattern"]) + 1
            
                for _key, _value in _firs_templates.iteritems() :
                    if _key.count(obj_attr_list["pattern"]) :
                        if _key[_x:] in obj_attr_list : 
                            if obj_attr_list[_key[_x:]] == "default" :
                                obj_attr_list[_key[_x:]] = _value
                        else :
                            obj_attr_list[_key[_x:]] = _value

                obj_attr_list["arrival"] = int(time())

                _status = 0
            else :
                _fmsg = "Unknown pattern: " + obj_attr_list["pattern"] 

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "FIRS pre-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "FIRS pre-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace    
    def objattach(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        threading.current_thread().abort = False 
        threading.current_thread().aborted = False
            
        if "uuid" not in obj_attr_list :
            obj_attr_list["uuid"] = str(uuid5(NAMESPACE_DNS, \
                               str(randint(0,1000000000000000000)))).upper()
        
        if command == "vm-attach" :
            for key in ["ai", "ai_name", "aidrs", "aidrs_name", "pattern", "type"] :
                if key not in obj_attr_list :
                    obj_attr_list[key] = "none"
                    
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _obj_type = command.split('-')[0].upper()
        _result = {}

        _pre_attach = False
        _admission_control = False
        _vmcregister = False
        _vmcreate = False
        _aidefine = False
        _created_object = False
        _created_pending = False

        obj_attr_list["name"] = "undefined"
        obj_attr_list["cloud_ip"] = "undefined"
        obj_attr_list["cloud_hostname"] = "undefined"
            
        try :
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                _cloud_name = obj_attr_list["cloud_name"]

                _staging_from_gui = False
                
                if "staging" in obj_attr_list :
                    if obj_attr_list["staging"].count("prepare_") :
                        _staging_from_gui = True
                        #The "staging" string is prefixed with the word "prepare" by the UI.
                        _staging = obj_attr_list["staging"].replace("prepare_",'')
                    else :
                        _staging = obj_attr_list["staging"]
                else :
                    _staging = None

                '''
                This code path is really confusing, but highly necessary. 
                Basically, anything called from the UI requires 2 "objattach"
                invocations. The first one will just subscribe to a channel,
                while the second one will effectively perform the attachment.
                This has to be done this way mostly because the API cannot block
                waiting for the pub/sub cycle to complete, since it needs to 
                return to the UI. Again, keep in mind that this code path is used
                *only* by the UI.
                '''

                if _staging_from_gui :

                    _sub_channel = self.osci.subscribe(_cloud_name, "VM", "staging")
                    
                    if _obj_type == "VM" :
                        _staging_parameters = _cloud_name + ' '
                        _staging_parameters += obj_attr_list["role"] + ' '
                        _staging_parameters += obj_attr_list["pool"] + ' '
                        _staging_parameters += obj_attr_list["meta_tags"] + ' '
                        _staging_parameters += obj_attr_list["size"] + ' '
                        _staging_parameters += str(_staging) + ' ' 
                        _staging_parameters += obj_attr_list["temp_attr_list"] 
                        _staging_parameters += " async"
                                              
                        _tmp_result = self.pause_vm(obj_attr_list, \
                                                    _sub_channel, \
                                                    self.background_execute(_staging_parameters, "vm-attach")[2])
                        
                    elif _obj_type == "AI" :
                        _staging_parameters = _cloud_name + ' '
                        _staging_parameters += obj_attr_list["type"] + ' ' 
                        _staging_parameters += obj_attr_list["load_level"] + ' '
                        _staging_parameters += obj_attr_list["load_duration"] + ' '
                        _staging_parameters += obj_attr_list["lifetime"] + ' '
                        _staging_parameters += obj_attr_list["aidrs"] + ' '
                        _staging_parameters += str(_staging) + ' ' 
                        _staging_parameters += obj_attr_list["temp_attr_list"] 
                        _staging_parameters += " async"
                                                      
                        _tmp_result = self.pause_app(obj_attr_list, \
                                                     _sub_channel, \
                                                     self.background_execute(_staging_parameters, "ai-attach")[2])

                    _status = _tmp_result["status"]
                    _fmsg = _tmp_result["msg"]
                    _result = _tmp_result["result"]
                    obj_attr_list.update(_result)

                    obj_attr_list["prepare_" + str(_staging) + "_complete"] = int(time())
                    
                elif not _status :
                    self.osci.add_to_list(_cloud_name, _obj_type, "PENDING", \
                          obj_attr_list["uuid"] + "|" + obj_attr_list["name"], int(time()))

                    self.osci.pending_object_set(_cloud_name, _obj_type, \
                                        obj_attr_list["uuid"], "status", "Initializing...")
                    
                    _created_pending = True
    
                    _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                        
                    _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])
    
                    if _obj_type == "VMC" :
                        self.pre_attach_vmc(obj_attr_list)

                    elif _obj_type == "VM" :
                        self.pre_attach_vm(obj_attr_list)
    
                    elif _obj_type == "AI" :
                        self.pre_attach_ai(obj_attr_list)
    
                    elif _obj_type == "AIDRS" :
                        self.pre_attach_aidrs(obj_attr_list)
                        
                    elif _obj_type == "VMCRS" :
                        self.pre_attach_vmcrs(obj_attr_list)

                    elif _obj_type == "FIRS" :
                        self.pre_attach_firs(obj_attr_list)
    
                    else :
                        _msg = "Unknown object: " + _obj_type
                        raise self.ObjectOperationsException(_msg, 28)
                    
                    _pre_attach = True
                    _admission_control = self.admission_control(_obj_type, \
                                                            obj_attr_list, \
                                                            "attach")
    
                    if _obj_type == "VMC" :
                        _status, _fmsg = _cld_conn.vmcregister(obj_attr_list)
                        _vmcregister = True
    
                    elif _obj_type == "VM" :
                        self.osci.pending_object_set(_cloud_name, _obj_type, \
                                            obj_attr_list["uuid"], "status", "Sending create request to cloud ...")
                        _status, _fmsg = _cld_conn.vmcreate(obj_attr_list)
                        _vmcreate = True
                        
                    elif _obj_type == "AI" :
                        _status, _fmsg = _cld_conn.aidefine(obj_attr_list)
                        self.assign_roles(obj_attr_list)
                        _aidefine = True
    
                    elif _obj_type == "AIDRS" :
                        True
                    
                    elif _obj_type == "VMCRS" :
                        True

                    elif _obj_type == "FIRS" :
                        True
    
                    else :
                        False
    
                    if not _status :
    
                        if "lifetime" in obj_attr_list and not "submitter" in obj_attr_list :
                            if obj_attr_list["lifetime"] != "none" :
                                obj_attr_list["departure"] = obj_attr_list["lifetime"] +\
                                 obj_attr_list["arrival"]
                        
                        if _obj_type == "VM" and "host_name" in obj_attr_list and obj_attr_list["host_name"] != "unknown" :
                            if obj_attr_list["discover_hosts"].lower() == "true" :
                                _host_attr_list = self.osci.get_object(_cloud_name, "HOST", True, "host_" + obj_attr_list["host_name"], False)
                                obj_attr_list["host"] = _host_attr_list["uuid"]
                                obj_attr_list["host_cloud_ip"] = _host_attr_list["cloud_ip"]

                        self.osci.create_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                obj_attr_list, False, True)
                        _created_object = True
    
                        if _obj_type == "VMC" :
                            self.post_attach_vmc(obj_attr_list)
    
                        elif _obj_type == "VM" :
                            self.post_attach_vm(obj_attr_list, _staging)
    
                        elif _obj_type == "AI" :
                            self.post_attach_ai(obj_attr_list, _staging)
    
                        elif _obj_type == "AIDRS" :
                            self.post_attach_aidrs(obj_attr_list)
    
                        elif _obj_type == "VMCRS" :
                            self.post_attach_vmcrs(obj_attr_list)

                        elif _obj_type == "FIRS" :
                            self.post_attach_firs(obj_attr_list)

                        else :
                            True

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:
            unique_state_key = "-attach-" + str(time())
            
            if "userdata" in obj_attr_list :
                del obj_attr_list["userdata"]

            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "attached to this experiment: " + _fmsg
                cberr(_msg)

                if self.osci :
                    if "cloud_name" in obj_attr_list :
                        self.osci.update_counter(_cloud_name, _obj_type, "FAILED", "increment")
    
                    if _obj_type == "VM" :
                        if "mgt_001_provisioning_request_originated" in obj_attr_list :
                            obj_attr_list["mgt_999_provisioning_request_failed"] = \
                                int(time()) - int(obj_attr_list["mgt_001_provisioning_request_originated"])
                        
                    _xmsg = "Now all actions executed during the object's "
                    _xmsg += "attachment will be rolled back."
                    cberr(_xmsg)

                    if _obj_type == "AI" :
                        if "vms" in obj_attr_list :
                            self.destroy_vm_list_for_ai(obj_attr_list)
                            if obj_attr_list["vm_destruction"].lower() == "explicit" \
                            and obj_attr_list["destroy_vms"] != "0" :
                                self.parallel_obj_operation("detach", obj_attr_list)

                        '''
                        We publish a message in even if the object is a VApp, 
                        mostly because continue_app will need to know what happened.
                        We always use the "VM" channel, no matter the object.
                        '''
                                
                        if str(_staging) + "_complete" in obj_attr_list :
                            self.osci.publish_message(_cloud_name, \
                                                      "VM", \
                                                      "staging", \
                                                      obj_attr_list["uuid"] + ";error;" + _msg, \
                                                      1, \
                                                      3600)


                    if _obj_type == "VM" :
                        if "cloud_name" in obj_attr_list :
                            self.record_management_metrics(_cloud_name, \
                                                           "VM", obj_attr_list, "attach")

                        '''
                        Whenever the staging action (be it pause or execute) 
                        is completed (it is always completed inside the 
                        take_action_if_requested method, in the  shared_function
                        module on the cloud-specific code directory) each 
                        individual VM publishes a message back, in case a parent
                        AI is listening, and waiting for all VMs to reach the 
                        same barrier.
                        '''

                        if str(_staging) + "_complete" in obj_attr_list :
                            if obj_attr_list["ai"] != "none" :
                                _target_uuid = obj_attr_list["ai"]
                                _target_name = obj_attr_list["ai_name"]
                            else :
                                _target_uuid = obj_attr_list["uuid"]
                                _target_name = obj_attr_list["name"]                                

                            self.osci.publish_message(_cloud_name, \
                                                      "VM", \
                                                      "staging", \
                                                      _target_uuid + ";error;" + _msg, \
                                                      1, \
                                                      3600)

                    if _admission_control or ( _obj_type == "AI" and _pre_attach) :
                        self.admission_control(_obj_type, obj_attr_list, \
                                               "rollbackattach")
                    if _vmcregister :
                        _cld_conn.vmcunregister(obj_attr_list)
    
                    if _vmcreate :
                        _cld_conn.vmdestroy(obj_attr_list)
                        if "qemu_debug_port_base" in obj_attr_list :
                            self.auto_free_port("qemu_debug", obj_attr_list, "VMC", obj_attr_list["vmc"], obj_attr_list["vmc_cloud_ip"])
                        
                    if _aidefine :
                        _cld_conn.aiundefine(obj_attr_list)
    
                    if _created_object :
                        self.osci.destroy_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                obj_attr_list, False)
    
                    obj_attr_list["tracking"] = str(_fmsg)
                    if "uuid" in obj_attr_list and "cloud_name" in obj_attr_list :
                        self.osci.create_object(_cloud_name, "FAILEDTRACKING" + _obj_type, obj_attr_list["uuid"] + unique_state_key, \
                                                obj_attr_list, False, True, 3600)
                    _xmsg = "Done "
                    cberr(_xmsg)                

            else :
                
                _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") sucessfully "
                _msg += "attached to this experiment."                
                
                if "prepare_" + str(_staging) + "_complete" in obj_attr_list :
                    _msg += _staging + "d."
                    obj_attr_list["tracking"] = _staging + ": success." 
                else :
                    _result = copy.deepcopy(obj_attr_list)
                    self.osci.update_counter(_cloud_name, _obj_type, "ARRIVED", "increment")
    
                    if not "submitter" in obj_attr_list :
                        _msg += " It is ssh-accessible at the IP address " + obj_attr_list["cloud_ip"]
                        _msg += " (" + obj_attr_list["cloud_hostname"] + ")."
                    obj_attr_list["tracking"] = "Attach: success." 
                    
                self.osci.create_object(_cloud_name, \
                                        "FINISHEDTRACKING" + _obj_type, \
                                        obj_attr_list["uuid"] + unique_state_key, \
                                        obj_attr_list, \
                                        False, \
                                        True, \
                                        3600)
                        
                cbdebug(_msg)

            if _created_pending :
                self.osci.pending_object_remove(_cloud_name, _obj_type, obj_attr_list["uuid"], "status")
                self.osci.remove_from_list(_cloud_name, _obj_type, "PENDING",obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)
                
            return self.package(_status, _msg, _result)

    @trace
    def post_attach_vmc(self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        try :
            if "hosts" in obj_attr_list and len(obj_attr_list["hosts"]) :

                for _host_uuid in obj_attr_list["hosts"].split(',') :

                    self.osci.create_object(obj_attr_list["cloud_name"], "HOST", _host_uuid, \
                                            obj_attr_list["host_list"][_host_uuid], False, True)

                    self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                   "HOST", obj_attr_list["host_list"][_host_uuid], "attach")

                if not "attach_parallel" in obj_attr_list :
                    self.update_host_os_perfmon(obj_attr_list)
                elif obj_attr_list["attach_parallel"].lower() != "true" :
                    self.update_host_os_perfmon(obj_attr_list)
            else :
                _msg = "The host list for VMC \"" + obj_attr_list["name"] + "\" is empty"
                if obj_attr_list["discover_hosts"].lower() == "false" :
                    _msg += " (\"discover_hosts\" was set to \"false\")"
                _msg += '.'
                _msg += " Skipping Host OS performance monitor daemon startup"
                cbdebug(_msg, True)
                
            self.record_management_metrics(obj_attr_list["cloud_name"], "VMC", \
                                           obj_attr_list, "attach")

            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        finally :
            if _status :
                _msg = "VMC post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMC post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_attach_vm(self, obj_attr_list, staging = None) :
        '''
        TBD
        '''
        if obj_attr_list["cloud_ip"] == "undefined" :
            _msg = "VM creation previously failed. Will not send files"
            _status = 452
            raise self.ObjectOperationException(_msg, _status)
        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _curr_tries = 0
        _start = int(time())
        _max_tries = int(obj_attr_list["attempts"])

        _proc_man = ProcessManagement(username = obj_attr_list["login"], \
                                      cloud_name = obj_attr_list["cloud_name"], \
                                      priv_key = obj_attr_list["identity"])

        try :

            while _curr_tries < _max_tries :
                if "async" not in obj_attr_list or obj_attr_list["async"].lower() == "false" :
                    if threading.current_thread().abort :
                        _msg = "VM creation aborted during transfer file step..."
                        _status = 12345
                        raise self.ObjectOperationException(_msg, _status)

                _cmd = "ssh -i " + obj_attr_list["identity"]
                _cmd += " -o StrictHostKeyChecking=no"
                _cmd += " -o UserKnownHostsFile=/dev/null " 
                _cmd += obj_attr_list["login"] + "@"
                _cmd += obj_attr_list["prov_cloud_ip"] + " \"mkdir -p ~/" + obj_attr_list["remote_dir_name"] +  ';'
                _cmd += "echo '#OSKN-redis' > ~/cb_os_parameters.txt;"
                if "openvpn_server_address" in obj_attr_list :
                    _cmd += "echo '#OSHN-" + obj_attr_list["openvpn_server_address"] + "' >> ~/cb_os_parameters.txt;"
                else :
                    _cmd += "echo '#OSHN-" + self.osci.host + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSPN-" + str(self.osci.port) + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSDN-" + str(self.osci.dbid) + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSTO-" + str(self.osci.timout) + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSCN-" + obj_attr_list["cloud_name"] + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSMO-" + obj_attr_list["mode"] + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#OSOI-" + "TEST_" + obj_attr_list["username"] + ":" + obj_attr_list["cloud_name"] + "' >> ~/cb_os_parameters.txt;"
                _cmd += "echo '#VMUUID-" + obj_attr_list["uuid"] + "' >> ~/cb_os_parameters.txt;"
                _cmd += "sudo chown -R " +  obj_attr_list["login"] + " ~/" + obj_attr_list["remote_dir_name"] + "\";"
                _cmd += "rsync -e \"ssh -o StrictHostKeyChecking=no -l " + obj_attr_list["login"] + " -i " 
                _cmd += obj_attr_list["identity"] + "\" --exclude-from "
                _cmd += "'" +  obj_attr_list["exclude_list"] + "' -az --delete --no-o --no-g --inplace -O " + obj_attr_list["base_dir"] + "/* " 
                _cmd += obj_attr_list["prov_cloud_ip"] + ":~/" + obj_attr_list["remote_dir_name"] + '/'

                if obj_attr_list["transfer_files"].lower() != "false" :

                    _msg = "RSYNC: " + _cmd
                    cbdebug(_msg)

                    _msg = "Sending a copy of the code tree to "
                    _msg += obj_attr_list["name"] + " ("+ obj_attr_list["prov_cloud_ip"] + ")..."
                    cbdebug(_msg, True)

                else :
                    _msg = "Bypassing the sending of a copy of the code tree to "
                    _msg += obj_attr_list["name"] 
                    _msg += " ("+ obj_attr_list["prov_cloud_ip"] + ")..."
                    cbdebug(_msg, True)

                _status, _result_stdout, _result_stderr = \
                _proc_man.run_os_command(_cmd, "127.0.0.1", \
                                         obj_attr_list["transfer_files"], \
                                         obj_attr_list["debug_remote_commands"])

                if not _status :
                    break
                else :
                    _curr_tries = _curr_tries + 1
                    sleep(int(obj_attr_list["update_frequency"]))
                
            if _curr_tries >= _max_tries :
                _fmsg = "Unable to connect to VM after " + str(_max_tries)
                _fmsg += "tries. The VM seems unreachable."
            else :
                _delay = int(time()) - _start
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "status", "Files transferred...")
                obj_attr_list["mgt_005_file_transfer"] = _delay
                self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                                                  False, "mgt_005_file_transfer", \
                                                  _delay)

                if "ai" in obj_attr_list and obj_attr_list["ai"] == "none" :
                    if not access(obj_attr_list["identity"], F_OK) :
                        obj_attr_list["identity"] = obj_attr_list["identity"].replace(obj_attr_list["username"], \
                                                                                      obj_attr_list["login"])

                    if "run_generic_scripts" in obj_attr_list and obj_attr_list["run_generic_scripts"].lower() != "false" :
                        _msg = "Performing generic VM post_boot configuration on "
                        _msg += obj_attr_list["name"] + " ("+ obj_attr_list["prov_cloud_ip"] + ")..."     
                        cbdebug(_msg, True)

                    else :
                        _msg = "Bypassing generic VM post_boot configuration on "
                        _msg += obj_attr_list["name"] 
                        _msg += " ("+ obj_attr_list["prov_cloud_ip"] + ")..." 
                        cbdebug(_msg, True)

                    _cmd = "~/" + obj_attr_list["remote_dir_name"] + "/scripts/common/cb_post_boot.sh"
                    
                    _status, _xfmsg, _object = \
                    _proc_man.run_os_command(_cmd, obj_attr_list["prov_cloud_ip"], \
                                             obj_attr_list["run_generic_scripts"], \
                                             obj_attr_list["debug_remote_commands"])

                    if _status :
                        _fmsg = "Failure while executing generic VM "
                        _fmsg += "post_boot configuration on "
                        _fmsg += obj_attr_list["name"] + '.\n'
#                            _fmsg += _xfmsg

                    self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                   "VM", obj_attr_list, "attach")

            '''
            Whenever the staging action (be it pause or execute) is completed 
            (it is always completed inside the take_action_if_requested method,
            in the  shared_function module on the cloud-specific code directory)
            each individual VM publishes a message back, in case a parent AI is 
            listening, and waiting for all VMs to reach the same barrier.
            '''
            if str(staging) + "_complete" in obj_attr_list :
                if obj_attr_list["ai"] != "none" :
                    _target_uuid = obj_attr_list["ai"]
                    _target_name = obj_attr_list["ai_name"]
                else :
                    _target_uuid = obj_attr_list["uuid"]
                    _target_name = obj_attr_list["name"]                                

                self.osci.publish_message(obj_attr_list["cloud_name"], \
                                          "VM", \
                                          "staging", \
                                          _target_uuid + ";vmfinished;" + dic2str(obj_attr_list), \
                                          1, \
                                          3600)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_attach_ai(self, obj_attr_list, staging = None) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"


            self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "status", "Running VM Applications..." )
            _status, _fmsg  = self.parallel_vm_config_for_ai(obj_attr_list["cloud_name"], \
                                                             obj_attr_list["uuid"], "setup")

            if not _status :
                self.record_management_metrics(obj_attr_list["cloud_name"], \
                                               "AI", obj_attr_list, "attach")

                if "save_on_attach" in obj_attr_list and obj_attr_list["save_on_attach"].lower() == "true" :

                    secs = int(obj_attr_list["seconds_before_save"].strip())
                    _msg = "Going to save VMs for AI " + obj_attr_list["name"] + " now..."
                    cbdebug(_msg, True)
                    
                    if secs > 0 :
                        try :
                            _msg = "Will wait " + str(secs) + " seconds to reach steady state before saving..."
                            cbdebug(_msg, True)
                            self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "status", _msg)
                            sleep(secs)
                            _msg = "Saving " + obj_attr_list["name"] + " now...."
                            cbdebug(_msg)
                            self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "status", _msg)
                            
                        except KeyboardInterrupt :
                            _fmsg = "CTRL-C: Cancelled VM save..."
                            raise self.ObjectOperationException(_fmsg, 195)

                    obj_attr_list["target_state"] = "save"
                    _status = self.airunstate_actual(obj_attr_list)
                    self.runstate_list_for_ai(obj_attr_list, "save")
                    if obj_attr_list["state_changed_vms"] != "0" :
                        _status, _fmsg = self.parallel_obj_operation("runstate", obj_attr_list)

                else :
                    _status = 0

            '''
            We publish a message in even if the object is a VApp, 
            mostly because continue_app will need to know what happened.
            We always use the "VM" channel, no matter the object.
            '''                    
                    
            if str(staging) + "_complete" in obj_attr_list :
                self.osci.publish_message(obj_attr_list["cloud_name"], \
                                          "VM", \
                                          "staging", \
                                          obj_attr_list["uuid"] + ";appfinished;" + dic2str(obj_attr_list),\
                                           1, \
                                           3600)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if "target_state" in obj_attr_list :
                del obj_attr_list["target_state"]
            if _status :
                _msg = "AI post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AI post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_attach_aidrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            

            _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                          cloud_name = obj_attr_list["cloud_name"])

            # First, a Vapp Submmiter is instantiated
            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --msp=" + dic2str(self.msci.mscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=aidr-submit"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += " --daemon"
            #_cmd += "  --debug_host=127.0.0.1"

            _aidrs_pid = _proc_man.start_daemon(_cmd)

            if _aidrs_pid :

                _msg = "AIDRS attachment command \"" + _cmd + "\" "
                _msg += " was successfully started (submit)."
                _msg += "The process id is " + str(_aidrs_pid) + "."
                cbdebug(_msg)

                _obj_id = obj_attr_list["uuid"] + '-' + "submit"
                self.update_process_list(obj_attr_list["cloud_name"], "AIDRS", _obj_id, \
                                         str(_aidrs_pid), "add")
            else :
                _fmsg = "AIDRS attachment command \"" + _cmd + "\" "
                _fmsg += " failed while starting (submit)."

            # Second, a Vapp Remover is instantiated
            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --msp=" + dic2str(self.msci.mscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=aidr-remove"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += " --daemon"
            #_cmd += "  --debug_host=127.0.0.1"

            _aidrs_pid = _proc_man.start_daemon(_cmd)

            if _aidrs_pid :

                _msg = "AIDRS attachment command \"" + _cmd + "\" "
                _msg += " was successfully started (remove)."
                _msg += "The process id is " + str(_aidrs_pid) + "."
                cbdebug(_msg)

                _obj_id = obj_attr_list["uuid"] + '-' + "remove"
                self.update_process_list(obj_attr_list["cloud_name"], "AIDRS", _obj_id, \
                                         str(_aidrs_pid), "add")
            else :
                _fmsg = "AIDRS attachment command \"" + _cmd + "\" "
                _fmsg += " failed while starting (remove)."

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AIDRS post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AIDRS post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_attach_vmcrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            

            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --msp=" + dic2str(self.msci.mscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=vmcr-submit"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += " --daemon"

            _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                          cloud_name = obj_attr_list["cloud_name"])

            _vmcrs_pid = _proc_man.start_daemon(_cmd)

            if _vmcrs_pid :

                _msg = "VMCRS attachment command \"" + _cmd + "\" "
                _msg += " was successfully started."
                _msg += "The process id is " + str(_vmcrs_pid) + "."
                cbdebug(_msg)

                _obj_id = obj_attr_list["uuid"] + '-' + "submit"
                self.update_process_list(obj_attr_list["cloud_name"], "VMCRS", _obj_id, \
                                         str(_vmcrs_pid), "add")
            else :
                _fmsg = "VMCRS attachment command \"" + _cmd + "\" "
                _fmsg += " failed while starting."

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMCRS post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMCRS post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg

    def post_attach_firs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            

            _cmd = self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --msp=" + dic2str(self.msci.mscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=fir-submit"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += " --daemon"

            _proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                          cloud_name = obj_attr_list["cloud_name"])

            _firs_pid = _proc_man.start_daemon(_cmd)

            if _firs_pid :

                _msg = "FIRS attachment command \"" + _cmd + "\" "
                _msg += " was successfully started."
                _msg += "The process id is " + str(_firs_pid) + "."
                cbdebug(_msg)

                _obj_id = obj_attr_list["uuid"] + '-' + "submit"
                self.update_process_list(obj_attr_list["cloud_name"], "FIRS", _obj_id, \
                                         str(_firs_pid), "add")
            else :
                _fmsg = "FIRS attachment command \"" + _cmd + "\" "
                _fmsg += " failed while starting."

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "FIRS post-attachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "FIRS post-attachment operations success."
                cbdebug(_msg)
                return _status, _msg
        
    @trace
    def pre_detach_vmc(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _reservations_on_vmc = int(obj_attr_list["nr_vms"])
            
            if _reservations_on_vmc and obj_attr_list["force_detach"] == "false" :
                _status = 46
                _fmsg = "This VMC has " + str(_reservations_on_vmc) + " VM "
                _fmsg += "reservations. Please detach all VMs on this VMC before"
                _fmsg += " proceeding."
            else :
                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMC pre-detachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_detach_vm(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"            

            if obj_attr_list["ai"] == "none" or obj_attr_list["force_detach"].lower() != "false" :
                _status = 0
            else :
                _status = 46
                _fmsg = "This VM is part of the AI " + obj_attr_list["ai"] + '.'
                _fmsg += "Please detach this AI instead."
                
        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM pre-detachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_detach_ai(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["aidrs"] == "none" or\
             obj_attr_list["force_detach"].lower() != "false" or \
             not self.osci.object_exists(obj_attr_list["cloud_name"], "AIDRS", obj_attr_list["aidrs"], False) :

                _msg = "Removing AI from the \"BYAIDRS\" view"
                cbdebug(_msg)
                self.osci.remove_from_view(obj_attr_list["cloud_name"], "AI", obj_attr_list, "BYAIDRS")

                _msg = "Destroying all VMs belonging to this AI"
                cbdebug(_msg)
                self.destroy_vm_list_for_ai(obj_attr_list)

                if obj_attr_list["vm_destruction"].lower() == "explicit" and obj_attr_list["destroy_vms"] != "0" :
                    _status, _fmsg = self.parallel_obj_operation("detach", obj_attr_list)
                else :
                    _status = 0
            else :
                _status = 46
                _fmsg = "This AI is part of the AIDRS " + obj_attr_list["aidrs"] + '.'
                _fmsg += "Please detach this AS instead."

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AI pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AI pre-detachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_detach_aidrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _msg = " Changing AIDRS \"" + obj_attr_list["name"] + "\" to \""
            _msg += "stopped\"."
            self.osci.set_object_state(obj_attr_list["cloud_name"], "AIDRS", obj_attr_list["uuid"], "stopped")
            # For now, will just sleep for 20 seconds. Need to find a better
            # solution later
            sleep(20)
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AIDRS pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AIDRS pre-detachment operations success."
                cbdebug(_msg)
                return True

    @trace
    def pre_detach_vmcrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMCRS pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMCRS pre-detachment operations success."
                cbdebug(_msg)
                return True

    def pre_detach_firs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "FIRS pre-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "FIRS pre-detachment operations success."
                cbdebug(_msg)
                return True

    @trace    
    def objdetach(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        
        threading.current_thread().abort = False 
        threading.current_thread().aborted = False
        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _obj_type = command.split('-')[0].upper()
        _result = {}
         
        _admission_control = False
        _detach_pending = False

        obj_attr_list["uuid"] = "undefined"
        obj_attr_list["name"] = "undefined"
        
        try :
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            if _status == 912543 :
                if _obj_type in ["VMC", "AIDRS"] :
                    command += "all"
                _status, _fmsg, _result = self.objdetachall(parameters, command)
                
            elif not _status :
                self.osci.add_to_list(obj_attr_list["cloud_name"], _obj_type, "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], int(time()))
                self.osci.pending_object_set(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["uuid"], "status", "Detaching...")
                _detach_pending = True
                
                _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])

                obj_attr_list["current_state"] = \
                self.osci.get_object_state(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["uuid"])

                _admission_control = self.admission_control(_obj_type, \
                                                            obj_attr_list, \
                                                            "detach")

                if _obj_type == "VMC" :
                    self.pre_detach_vmc(obj_attr_list)
                    _status, _msg = _cld_conn.vmcunregister(obj_attr_list)

                elif _obj_type == "VM" :
                    self.pre_detach_vm(obj_attr_list)
                    _status, _msg = _cld_conn.vmdestroy(obj_attr_list)

                elif _obj_type == "AI" :
                    self.pre_detach_ai(obj_attr_list)

                elif _obj_type == "AIDRS" :
                    self.pre_detach_aidrs(obj_attr_list)

                elif _obj_type == "VMCRS" :
                    self.pre_detach_vmcrs(obj_attr_list)

                elif _obj_type == "FIRS" :
                    self.pre_detach_firs(obj_attr_list)

                else :
                    _msg = "Unknown object: " + _obj_type
                    raise self.ObjectOperationException(_msg, 28)

                if not _status :
                    self.osci.destroy_object(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["uuid"], \
                                             obj_attr_list, False)

                    _destroyed_object = True

                    if _obj_type == "VMC" :
                        self.post_detach_vmc(obj_attr_list)

                    elif _obj_type == "VM" :
                        self.post_detach_vm(obj_attr_list)

                    elif _obj_type == "AI" :
                        self.post_detach_ai(obj_attr_list)

                    elif _obj_type == "AIDRS" :
                        self.post_detach_aidrs(obj_attr_list)

                    elif _obj_type == "VMCRS" :
                        self.post_detach_vmcrs(obj_attr_list)

                    elif _obj_type == "FIRS" :
                        self.post_detach_firs(obj_attr_list)

                    else :
                        True

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:

            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "detached from this experiment: " + _fmsg
                cberr(_msg)

                if self.osci :
                    if "cloud_name" in obj_attr_list :
                        self.osci.update_counter(obj_attr_list["cloud_name"], _obj_type, "FAILED", "increment")
    
                    if _admission_control :
                        self.admission_control(_obj_type, obj_attr_list, \
                                               "rollbackdetach")
                        
                    obj_attr_list["tracking"] = _fmsg
            else :
                _result = copy.deepcopy(obj_attr_list)
                if obj_attr_list["name"] != "all" :
                    self.osci.update_counter(obj_attr_list["cloud_name"], _obj_type, "DEPARTED", "increment")
                
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") was "
                _msg += "sucessfully detached from this experiment."
                cbdebug(_msg)
                obj_attr_list["tracking"] = "Detach: success." 
                
            unique_state_key = "-detach-" + str(time())
            if self.osci and obj_attr_list["uuid"] != "undefined":
                tracking = "FINISHED" if not _status else "FAILED"
                self.osci.create_object(obj_attr_list["cloud_name"], tracking + "TRACKING" + _obj_type, obj_attr_list["uuid"] + unique_state_key, \
                                        obj_attr_list, False, True, 3600)
                if _detach_pending :
                    self.osci.pending_object_remove(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["uuid"], "status")
                    self.osci.remove_from_list(obj_attr_list["cloud_name"], _obj_type, "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)
            
            return self.package(_status, _msg, _result)

    @trace
    def post_detach_vmc(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "hosts" in obj_attr_list :
                for _host_uuid in obj_attr_list["hosts"].split(',') :
                    _host_attr_list =  self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, _host_uuid, False)
                    self.osci.destroy_object(obj_attr_list["cloud_name"], "HOST", _host_uuid, _host_attr_list, False)
                    self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                   "HOST", _host_attr_list, \
                                                   "detach")

            self.record_management_metrics(obj_attr_list["cloud_name"], "VMC", \
                                           obj_attr_list, "detach")
            
            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMC post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_detach_vm(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "qemu_debug_port_base" in obj_attr_list :
                self.auto_free_port("qemu_debug", obj_attr_list, "VMC", obj_attr_list["vmc"], obj_attr_list["vmc_cloud_ip"])

            if obj_attr_list["current_state"] != "attached" :

                if "post_capture" in obj_attr_list and obj_attr_list["post_capture"] == "true" :
                    _scores = True
                else :
                    _scores = False
                self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_" + obj_attr_list["current_state"].upper(), obj_attr_list["uuid"], _scores)

            self.record_management_metrics(obj_attr_list["cloud_name"], "VM", \
                                           obj_attr_list, "detach")

            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VM post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_detach_ai(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list["current_state"] != "attached" :
                if "pre_capture" in obj_attr_list and obj_attr_list["pre_capture"] == "true" :
                    _scores = True
                else :
                    _scores = False
                self.osci.remove_from_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_" + \
                                           obj_attr_list["current_state"].upper(), \
                                           obj_attr_list["uuid"], _scores)

            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AI post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AI post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_detach_aidrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AIDRS post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "AIDRS post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def post_detach_vmcrs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMCRS post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMCRS post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    def post_detach_firs(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _status = 0

        except IndexError, msg :
            _status = 40
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "FIRS post-detachment operations failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "VMCRS post-detachment operations success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def objdetachall(self, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _smsg = ''

            _obj_attr_list = {}

            _obj_type = command.split('-')[0].upper()

            if BaseObjectOperations.default_cloud is None :
                _obj_attr_list["cloud_name"] = parameters.split()[0]
            else :
                if len(parameters) > 0 and BaseObjectOperations.default_cloud == parameters.split()[0] :
                    True
                else :
                    parameters = BaseObjectOperations.default_cloud + ' ' + parameters
                _obj_attr_list["cloud_name"] = parameters.split()[0]           

            _obj_attr_list["command_originated"] = int(time())
            _obj_attr_list["command"] = _obj_type.lower() + "detach " + _obj_attr_list["cloud_name"] + " all"
            _obj_attr_list["name"] = "all"

            _obj_defaults = self.osci.get_object(_obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                 _obj_type.lower() + "_defaults", \
                                                 False)

            _obj_attr_list["detach_parallelism"] = _obj_defaults["detach_parallelism"] 

            self.get_counters(_obj_attr_list["cloud_name"], _obj_attr_list)
            self.record_management_metrics(_obj_attr_list["cloud_name"], _obj_type, _obj_attr_list, "trace")

            _obj_list = self.osci.get_object_list(_obj_attr_list["cloud_name"], _obj_type)

            if _obj_list :        
                _obj_counter = 0
                _obj_attr_list["parallel_operations"] = {}
                _obj_attr_list["parallel_operations"][_obj_counter] = {}
                for _obj in _obj_list :
                    _current_state = self.osci.get_object_state(_obj_attr_list["cloud_name"], _obj_type, _obj)
                    # The default behavior is to get rid of all VApps, irrespective
                    # of their states. If someone ever needs to "protect" VApps
                    # in the saved state from a "vappadetach all" just uncomment
                    # the following line. I am reluctant in making that another
                    # VApp parameter, because I don't know how much it will be 
                    # used.
#                    if _current_state == "attached" : 
                    _obj_name = self.osci.get_object(_obj_attr_list["cloud_name"], _obj_type, False, _obj, False)["name"]
                    _obj_attr_list["parallel_operations"][_obj_counter] = {}
                    _obj_attr_list["parallel_operations"][_obj_counter]["parameters"] = _obj_attr_list["cloud_name"]  + ' ' + _obj_name
                    _obj_attr_list["parallel_operations"][_obj_counter]["operation"] = _obj_type.lower() + "-detach"
                    _obj_attr_list["parallel_operations"][_obj_counter]["uuid"] = _obj
                    _obj_counter += 1

                _status, _fmsg = self.parallel_obj_operation("detach", _obj_attr_list)

            else :
                True

            if _obj_type == "VMC" :
                _cloud_parameters = self.get_cloud_parameters(_obj_attr_list["cloud_name"])
                _cloud_parameters["all_vmcs_attached"] = "false"
                self.update_cloud_attribute(_obj_attr_list["cloud_name"], "all_vmcs_attached", "false")

                _proc_man = ProcessManagement(username = _cloud_parameters["username"], cloud_name = _obj_attr_list["cloud_name"])
                _gmetad_pid = _proc_man.get_pid_from_cmdline("gmetad.py")

                if len(_gmetad_pid) :
                    cbdebug("Killing the running Host OS performance monitor (gmetad.py)......", True)
                    _proc_man.kill_process("gmetad.py")

            _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "All " + _obj_type + "s detachment failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "All " + _obj_type + "s successfully detached"
                cbdebug(_msg)
            return _status, _msg, None

    @trace
    def gtk(self, obj_attr_list, parameters, command):
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None
            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"
            _obj_type = command.split('-')[0].upper()
            operation = command.split('-')[1].lower()
            obj_attr_list["operation"] = operation
            name = "gtk_" + operation
            portname = name + "_port"
            
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    if portname not in obj_attr_list :
                        gui = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "gui_defaults", False)
                        gui["cloud_name"] = obj_attr_list["cloud_name"]
                        gui["uuid"] = obj_attr_list["uuid"]
                        _status, _fmsg = self.auto_allocate_port(name, gui, "GLOBAL", "gui_defaults", "localhost")
                        if not _status :
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              obj_attr_list["uuid"], False, \
                                                              portname, gui[portname])
                        obj_attr_list[portname] = gui[portname]
                        cbwarn("Port " + str(obj_attr_list[portname]) + " allocated.", True)
                    else :
                        cbwarn("Port " + str(obj_attr_list[portname]) + " already allocated.", True)
                        
                    port = obj_attr_list[portname]
                    
                    if operation == "display" :
                        uri = obj_attr_list["display_protocol"] + "://" + obj_attr_list["host_cloud_ip"] + ":" + obj_attr_list["display_port"]
                        cmd = "GDK_BACKEND=broadway BROADWAY_DISPLAY=" + str(port) + " remote-viewer " + uri
                    elif operation == "login" :
                        cmd = "GDK_BACKEND=broadway BROADWAY_DISPLAY=" + str(port) + " gnome-terminal --maximize -e \\\"bash -c 'ssh " + \
                                "-o StrictHostKeyChecking=no -i " + obj_attr_list["identity"] + " " + \
                                obj_attr_list["login"] + "@" + obj_attr_list["cloud_ip"] + "; echo connection closed; sleep 120d'\\\""
                                
                    cmd = "screen -d -m -S gtkCBUI_" + obj_attr_list["cloud_name"] + str(port) + " bash -c \"" + cmd + "\""
                    cbdebug("Will create GTK broadway backend with command: " + cmd)

                    proc_man = ProcessManagement(username = obj_attr_list["username"], \
                                                  cloud_name = obj_attr_list["cloud_name"])
                    
                    pid = proc_man.get_pid_from_cmdline("GDK_BACKEND=broadway")
    
                    if pid :
                        cbdebug("Killing old GTK process: " + str(pid), True)
                        if operation == "login" :
                            # GTK broadway segfaults with more than one gnome-terminal running at the same time
                            # So, we can only allow one to run at once until this gets fixed. 
                            proc_man.kill_process("GDK_BACKEND=broadway", kill_options = "gnome-terminal")
                        else :
                            # remote-viewer (spice/vnc), however has no problem running multiple broadway backends.
                            # So, only kill the old one and restart
                            proc_man.kill_process("", port = port)
                            
                        self.update_process_list(obj_attr_list["cloud_name"], "GLOBAL", "gui_defaults", str(pid), "remov")
    
                    proc_man.run_os_command(cmd)
                
                    sleep(2)
                    pid, username = proc_man.get_pid_from_port(port)
                    
                    if pid :
                        self.update_process_list(obj_attr_list["cloud_name"], "GLOBAL", "gui_defaults", str(pid), "add")
                        _result = obj_attr_list
                    else :
                        _status = 34095 
                        _fmsg = "GTK process creation failed."
                    
        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "GTK broadway (" + operation + ") could not be created for " \
                        + _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\"): " + _fmsg
                cberr(_msg)
            else :
                _msg = "GTK broadway (" + operation + ") successfully created for " \
                        + _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\"): "
                cbdebug(_msg)
            return self.package(_status, _msg, _result)
    @trace    
    def migrate(self, obj_attr_list, parameters, command) :
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None
            pending = False
            admission_control_requested = False
            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"
            _obj_type = command.split('-')[0].upper()
            operation = command.split('-')[1].lower()
            obj_attr_list["operation"] = operation
            
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                cn = obj_attr_list["cloud_name"]
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    self.osci.update_object_attribute(cn, "VM", obj_attr_list["uuid"], False, \
                                          operation + "_protocol_supported", obj_attr_list["choices"])
                    
                    _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                    _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])

                    _current_state = self.osci.get_object_state(cn, "VM", obj_attr_list["uuid"])
                    
                    if _current_state == "attached" :
                        pending = True
                        self.osci.add_to_list(cn, "VM", "VMS_UNDERGOING_" + operation.upper(), obj_attr_list["uuid"], int(time()))
                        self.osci.set_object_state(cn, "VM", obj_attr_list["uuid"], operation)
                        
                        self.osci.add_to_list(cn, _obj_type, "PENDING", \
                                  obj_attr_list["uuid"] + "|" + obj_attr_list["name"], int(time()))
    
                        self.osci.pending_object_set(cn, _obj_type, obj_attr_list["uuid"], "status", 
                                            ("migrat" if operation == "migrate" else operation) + "ing..." )
                        
                        admission_control_requested = self.admission_control(_obj_type, obj_attr_list, "migrate")
                        
                        ai = False
                        scrape_frequency = 0.5
                        if "ai" in obj_attr_list and obj_attr_list["ai"] != "none" and operation == "migrate":
                            ai = self.osci.get_object(cn, "AI", False, obj_attr_list["ai"], False)
                            if "dont_start_qemu_scraper" not in ai or ai["dont_start_qemu_scraper"].lower() != "true" :
                                self.osci.publish_message(cn, "AI", "migrate_" + ai["uuid"], \
                                        obj_attr_list["uuid"] + ";start;" + str(scrape_frequency), 1, 3600)
                                
                        _status, _fmsg = _cld_conn.vmmigrate(obj_attr_list)
                        
                        if ai :
                            self.osci.publish_message(cn, "AI", "migrate_" + ai["uuid"], \
                                    obj_attr_list["uuid"] + ";stop;none", 1, 3600)
     
                        if not _status :
                            self.admission_control(_obj_type, obj_attr_list, "migratefinish")
                            
                            self.osci.update_object_views(cn, "VM", \
                                                          obj_attr_list["uuid"], obj_attr_list, "remove", False)
                            for (src, dest) in [ 
                                                    ("host_name", "destination"),
                                                    ("host_cloud_ip", "destination_ip"),
                                                    ("host", "destination_uuid"),
                                                    ("vmc", "destination_vmc"),
                                                    ("vmc_name", "destination_vmc_name"),
                                                    ("vmc_cloud_ip", "destination_vmc_cloud_ip"),
                                                    ("vmc_pool", "destination_vmc_pool"),
                                                ] :
                                obj_attr_list[src] = obj_attr_list[dest]
                            
                                self.osci.update_object_attribute(cn, "VM", \
                                                                  obj_attr_list["uuid"], False, 
                                                                  src, obj_attr_list[src])
                            
                            self.osci.update_object_views(cn, "VM", \
                                                          obj_attr_list["uuid"], obj_attr_list, "add", False)
                            
                        for mgt in [  "mgt_501_" + operation + "_request_originated",
                                      "mgt_502_" + operation + "_request_sent", \
                                      "mgt_503_" + operation + "_request_completed", \
                                      "mgt_999_" + operation + "_request_failed" ] :
                            if mgt in obj_attr_list :
                                self.osci.update_object_attribute(cn, "VM", \
                                                          obj_attr_list["uuid"], False, mgt, obj_attr_list[mgt])
                            
                        if not _status :
                            _result = obj_attr_list
                    else :
                        _fmsg = "VM object named \"" + obj_attr_list["name"] + "\" could "
                        _fmsg += "not be " + operation + "ed because it is on the "
                        _fmsg += "\"" + _current_state + "\" state."
                        _status = 78
    

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            unique_state_key = "-" + operation + "-" + str(time())
            
            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += operation + "ed on this experiment: " + _fmsg
                cberr(_msg)
                obj_attr_list["tracking"] = operation + ": " + _fmsg 
                
                if admission_control_requested :
                    self.admission_control(_obj_type, obj_attr_list, "rollbackmigrate")
            else :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully " + operation + "ed "
                _msg += "on this experiment."
                cbdebug(_msg)
                obj_attr_list["tracking"] =  operation + ": success." 
                
            if pending :
                self.osci.remove_from_list(cn, "VM", "VMS_UNDERGOING_" + operation, obj_attr_list["uuid"], True)
                self.osci.set_object_state(cn, "VM", obj_attr_list["uuid"], "attached")
                
                self.osci.pending_object_remove(cn, _obj_type, obj_attr_list["uuid"], "status")
                self.osci.remove_from_list(cn, _obj_type, "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)
                
            tracking = "FINISHED" if not _status else "FAILED"
            self.osci.create_object(cn, \
                                    tracking + "TRACKING" + _obj_type, \
                                    obj_attr_list["uuid"] + unique_state_key, \
                                    obj_attr_list, False, True, 3600)

            return self.package(_status, _msg, _result)
        
    @trace    
    def vmcapture(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None

            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"
            _capturable_vm = True

            _obj_type = command.split('-')[0].upper()

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                    _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])

                    if "vmcrs" in obj_attr_list and obj_attr_list["vmcrs"] != "none" :
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMCRS", \
                                                          obj_attr_list["vmcrs"], \
                                                          False, "nr_simultaneous_cap_reqs", \
                                                          1, True)

                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMCRS", \
                                                          obj_attr_list["vmcrs"], \
                                                          False, "nr_total_cap_reqs", \
                                                          1, True)
    
                    if "ai" in obj_attr_list and obj_attr_list["ai"].lower() != "none" :
                        _ai_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "AI", False, obj_attr_list["ai"], False)
                        
                        _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"])
                        
                        if _current_state == "attached" :
    
                            self.osci.add_to_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_CAPTURE", obj_attr_list["ai"], int(time())) 
                            self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "capture")
                            
                            self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_CAPTURE", obj_attr_list["uuid"], int(time()))
                            self.osci.set_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "capture")
    
                            _ai_attr_list["exclude_vm"] = obj_attr_list["uuid"]
                            _ai_attr_list["pre_capture"] = "true"            
                            self.objdetach(_ai_attr_list, _ai_attr_list["cloud_name"] + \
                                           ' ' + _ai_attr_list["name"], "ai-detach")
                        else :
                            _fmsg = "VM object named \"" + obj_attr_list["name"] + "\" could "
                            _fmsg += "not be captured because the AI it belongs to is on the "
                            _fmsg += "\"" + _current_state + "\" state."
                            _status = 78
                            _capturable_vm = False
    
                    else :
                        
                        _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"])
                        
                        if _current_state == "attached" :
                            
                            self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_CAPTURE", obj_attr_list["uuid"], int(time()))
                            self.osci.set_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "capture")
    
                        else : 
                            _fmsg = "VM object named \"" + obj_attr_list["name"] + "\" could "
                            _fmsg += "not be captured because it is on the "
                            _fmsg += "\"" + _current_state + "\" state."
                            _status = 78
                            _capturable_vm = False
    
                    if _capturable_vm :
    
                        _status, _fmsg = _cld_conn.vmcapture(obj_attr_list)
     
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                          obj_attr_list["uuid"], \
                                                          False, \
                                                          "mgt_101_capture_request_originated", \
                                                          obj_attr_list["mgt_101_capture_request_originated"])
    
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                          obj_attr_list["uuid"], \
                                                          False, \
                                                          "mgt_102_capture_request_sent", \
                                                          obj_attr_list["mgt_102_capture_request_sent"])

                        if "mgt_103_capture_request_completed" in obj_attr_list :
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              obj_attr_list["uuid"], \
                                                              False, \
                                                              "mgt_103_capture_request_completed", \
                                                              obj_attr_list["mgt_103_capture_request_completed"])

                        else :
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              obj_attr_list["uuid"], \
                                                              False, \
                                                              "mgt_999_capture_request_failed", \
                                                              obj_attr_list["mgt_999_capture_request_failed"])
    
                        obj_attr_list["post_capture"] = "true"
    
                        self.objdetach(obj_attr_list, obj_attr_list["cloud_name"] + \
                                       ' ' + obj_attr_list["name"] + " true", \
                                       "vm-detach")
        
                        if "vmcrs" in obj_attr_list and obj_attr_list["vmcrs"] != "none" :
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VMCRS", \
                                                              obj_attr_list["vmcrs"], \
                                                              False, "nr_simultaneous_cap_reqs", \
                                                              -1, True)
                        
                    _status = 0
                    _result = obj_attr_list

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "captured on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully captured "
                _msg += "on this experiment."
                cbdebug(_msg)

            return self.package(_status, _msg, _result)

    @trace    
    def vmresize(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"

            _resizable_vm = True
            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                
            if not _status :
                _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])

                if "ai" in obj_attr_list and obj_attr_list["ai"].lower() != "none" :
                    _ai_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "AI", False, obj_attr_list["ai"], False)
                    
                    _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"])
                    
                    if _current_state == "attached" :

                        self.osci.add_to_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_RESIZE", obj_attr_list["ai"]) 
                        self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "resize")
                        
                        self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_RESIZE", obj_attr_list["uuid"])
                        self.osci.set_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "resize")

                    else :
                        _fmsg = "VM object named \"" + obj_attr_list["name"] + "\" could "
                        _fmsg += "not be resized because the AI it belongs to is on the "
                        _fmsg += "\"" + _current_state + "\" state."
                        _status = 78
                        _resizable_vm = False

                else :
                    
                    _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"])
                    
                    if _current_state == "attached" :
                        
                        self.osci.add_to_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_RESIZE", obj_attr_list["uuid"])
                        self.osci.set_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "resize")

                    else : 
                        _fmsg = "VM object named \"" + obj_attr_list["name"] + "\" could "
                        _fmsg += "not be resized because it is on the "
                        _fmsg += "\"" + _current_state + "\" state."
                        _status = 78
                        _resizable_vm = False

                if _resizable_vm :
                    obj_attr_list["resource_description"] = str2dic(obj_attr_list["resource_description"])
                    

                    _status, _fmsg = _cld_conn.vmresize(obj_attr_list)
                    
                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                      obj_attr_list["uuid"], \
                                                      False, \
                                                      "mgt_301_resize_request_originated", \
                                                      obj_attr_list["mgt_301_resize_request_originated"])

                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                      obj_attr_list["uuid"], \
                                                      False, \
                                                      "mgt_302_resize_request_sent", \
                                                      obj_attr_list["mgt_302_resize_request_sent"])
                    
                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                      obj_attr_list["uuid"], \
                                                      False, \
                                                      "mgt_303_resize_request_completed", \
                                                      obj_attr_list["mgt_303_resize_request_completed"])

                    self.osci.remove_from_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_RESIZE", obj_attr_list["ai"])
                    self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_RESIZE", obj_attr_list["uuid"])
                    self.osci.set_object_state(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "attached")
                    self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "attached")

                    _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "VM object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "resized on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "VM object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") resized "
                _msg += "on this experiment."
                cbdebug(_msg)

            return _status, _msg, None

    @trace    
    def vmrunstate(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = {}
            _runstate_pending = False
            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"
            obj_attr_list["target_state"] = "undefined"
                    
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                _cloud_name = obj_attr_list["cloud_name"]
                
                if _status in [0, 483920, 912543] :
                    if _status not in [483920] :
                        self.osci.add_to_list(_cloud_name, "VM", "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], int(time()))
                        self.osci.pending_object_set(_cloud_name, "VM", obj_attr_list["uuid"], "status", "Changing state to: " + obj_attr_list["target_state"] + "(" + obj_attr_list["suspected_command"] + ")")
                        _runstate_pending = True
                    
                    if _status == 483920 :
                        _tmp_result = self.continue_vm(obj_attr_list)
                        _status = _tmp_result["status"]
                        _fmsg = _tmp_result["msg"]
                        _result = _tmp_result["result"]
                        obj_attr_list.update(_result)
                        obj_attr_list["target_state"] = "attached"
                        obj_attr_list["suspected_command"] = "run"

                    elif _status == 912543 :
                        _status, _fmsg, _result = self.vmrunstateall(parameters, obj_attr_list["suspected_command"])

                    elif not _status :
                        _current_state = self.osci.get_object_state(_cloud_name, "VM", obj_attr_list["uuid"])
        
                        _target_state = obj_attr_list["target_state"].lower()
                        if _target_state == "resume" :
                            _target_state = "attached"
        
                        if _target_state == "restore" :
                            _target_state = "attached"

                        if  _target_state not in ["save", "suspend", "fail", "attached" ] :
                            _fmsg = "Unknown state: " + _target_state
                            _status = 101
        
                        if not _status :
                            if _target_state != _current_state :
                                obj_attr_list["current_state"] = _current_state
                                _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                                _cld_conn = _cld_ops_class(self.pid, self.osci, obj_attr_list["experiment_id"])
                                         
                                # TAC looks up libvirt function based on target state
                                # Do not remove this
                                if _target_state == "attached" :
                                    if _current_state == "save" :
                                        obj_attr_list["target_state"] = "restore"
                                    else :
                                        obj_attr_list["target_state"] = "resume"

                                elif _target_state in [ "fail", "suspend"] and _current_state != "attached" :
                                    _msg = "Unable to fail a VM that is not on the \""
                                    _msg += "attached\" state."
                                    _status = 871
                                    raise self.ObjectOperationException(_msg, _status)
                                
                                _status, _fmsg = _cld_conn.vmrunstate(obj_attr_list)
                                
                                if not _status :
                                    self.osci.set_object_state(_cloud_name, "VM", obj_attr_list["uuid"], _target_state)
                                    if _target_state != "attached" :
                                        self.osci.add_to_list(_cloud_name, "VM", "VMS_UNDERGOING_" + _target_state.upper(), obj_attr_list["uuid"])
                                    elif _target_state == "attached" :
                                        self.osci.remove_from_list(_cloud_name, "VM", "VMS_UNDERGOING_SAVE", obj_attr_list["uuid"])
                                        self.osci.remove_from_list(_cloud_name, "VM", "VMS_UNDERGOING_SUSPEND", obj_attr_list["uuid"]) 
                                        self.osci.remove_from_list(_cloud_name, "VM", "VMS_UNDERGOING_FAIL", obj_attr_list["uuid"]) 
        
                                    self.osci.update_object_attribute(_cloud_name, "VM", \
                                                                      obj_attr_list["uuid"], \
                                                                      False, \
                                                                      "mgt_201_runstate_request_originated", \
                                                                      obj_attr_list["mgt_201_runstate_request_originated"])
        
                                    self.osci.update_object_attribute(_cloud_name, "VM", \
                                                                      obj_attr_list["uuid"], \
                                                                      False, \
                                                                      "mgt_202_runstate_request_sent", \
                                                                      obj_attr_list["mgt_202_runstate_request_sent"])
                                    
                                    self.osci.update_object_attribute(_cloud_name, "VM", \
                                                                      obj_attr_list["uuid"], \
                                                                      False, \
                                                                      "mgt_203_runstate_request_completed", \
                                                                      obj_attr_list["mgt_203_runstate_request_completed"])
                                    
                                    self.record_management_metrics(_cloud_name, "VM", obj_attr_list, "runstate")
                                    _status = 0
                            else :
                                _result = obj_attr_list
                                _msg = "VM is already at the \"" + obj_attr_list["target_state"]
                                _msg += "\" state. There is no need to explicitly change it."
                                cbdebug(_msg)
                                _status = 0

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:

            unique_state_key = "-state-" + str(time())
            if _status :
                if _status != 9 :
                    _msg = "VM object " + obj_attr_list["uuid"] + " ("
                    _msg += "named \"" + obj_attr_list["name"] + "\") could "
                    _msg += " not have his run state changed to \""
                    _msg += obj_attr_list["target_state"] + "\" on this "
                    _msg += "experiment: " + _fmsg
                    cberr(_msg)
                    obj_attr_list["tracking"] = "Change state request: " + _fmsg
                    if "uuid" in obj_attr_list and "cloud_name" in obj_attr_list and self.osci :
                        self.osci.create_object(_cloud_name, "FAILEDTRACKINGVM", \
                                                obj_attr_list["uuid"] + \
                                                unique_state_key, \
                                                obj_attr_list, False, True, 3600)
                else :
                    _msg = _fmsg
            else :
                _msg = "VM object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") had "
                _msg += "its run state successfully changed to \""
                _msg += obj_attr_list["target_state"] + "\" on this "
                _msg += "experiment." 
                cbdebug(_msg)
                obj_attr_list["tracking"] = "Change state request: success." 
                self.osci.create_object(_cloud_name, "FINISHEDTRACKINGVM", obj_attr_list["uuid"] + unique_state_key, \
                                        obj_attr_list, False, True, 3600)
                
            if _runstate_pending :
                self.osci.pending_object_remove(_cloud_name, "VM", obj_attr_list["uuid"], "status")
                self.osci.remove_from_list(_cloud_name, "VM", "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)

            return self.package(_status, _msg, _result)

    @trace
    def vmrunstateall(self, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _smsg = ''
            _obj_attr_list = {}
            _target_state = "undefined"
 
            if BaseObjectOperations.default_cloud is None :
                _obj_attr_list["cloud_name"] = parameters.split()[0]
            else :
                if len(parameters) > 0 and BaseObjectOperations.default_cloud == parameters.split()[0] :
                    True
                else :
                    parameters = BaseObjectOperations.default_cloud + ' ' + parameters
                _obj_attr_list["cloud_name"] = parameters.split()[0]           
            
            parameters = parameters.split()

            if len(parameters) >= 3 :
                _all = parameters[1]
                _target_state= parameters[2]
                _status = 0

            if len(parameters) < 3:
                _status = 9
                _fmsg = "Usage: vmrunstate <cloud name> <vm name> <runstate> [mode]"

            if not _status :    
                _obj_attr_list["command_originated"] = int(time())
                _obj_attr_list["command"] = "vmrunstateall " + _obj_attr_list["cloud_name"] + " all"
                _obj_attr_list["name"] = "all"

                self.get_counters(_obj_attr_list["cloud_name"], _obj_attr_list)
                self.record_management_metrics(_obj_attr_list["cloud_name"], "VM", _obj_attr_list, "trace")

                _vm_list = False
                if _target_state == "attached" and (command == "repair" or command == "resume") :
                    _vm_list = self.osci.get_list(_obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_FAIL")

                elif _target_state == "attached" and command == "restore" :
                    _vm_list = self.osci.get_list(_obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_SAVE")

                else :
                    _vm_list = []
                    _vms = self.osci.get_object_list(_obj_attr_list["cloud_name"], "VM")
                    if _vms :
                        for _vm in  _vms :
                            _current_state = self.osci.get_object_state(_obj_attr_list["cloud_name"], "VM", _vm)
                            if _current_state and _current_state == "attached" :
                                _vm_list.append(_vm)

                if _vm_list :
                    _vm_counter = 0
                    _obj_attr_list["parallel_operations"] = {}
                    _obj_attr_list["parallel_operations"][_vm_counter] = {} 
                    for _vm in _vm_list :
                        if len(_vm) == 2 :
                            _vm_uuid = _vm[0]
                        else :
                            _vm_uuid = _vm
                        _vm_attr_list = self.osci.get_object(_obj_attr_list["cloud_name"], "VM", False, _vm_uuid, False)
                        _vm_name = _vm_attr_list["name"]
                        _obj_attr_list["runstate_parallelism"] = _vm_attr_list["runstate_parallelism"]
                        _obj_attr_list["parallel_operations"][_vm_counter] = {}
                        _obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _vm_attr_list["uuid"]
                        _obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = _obj_attr_list["cloud_name"]  + ' ' + _vm_name + ' ' + _target_state
                        _obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-runstate"
                        _vm_counter += 1
    
                    if _vm_counter > int(_obj_attr_list["runstate_parallelism"]) :
                        _obj_attr_list["runstate_parallelism"] = int(_obj_attr_list["runstate_parallelism"])
                    else :
                        _obj_attr_list["runstate_parallelism"] = _vm_counter
    
                        _status, _fmsg = self.parallel_obj_operation("runstate", _obj_attr_list)

                else :
                    _fmsg = " No VMs are in state suitable for the transition "
                    _fmsg += "specified (to the \"" + _target_state + "\" state)."
                    _status = 791
            
        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError, msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError, msg :
            _status = 8
            _fmsg = str(msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "Failure while changing all suitable VMs to the state \""
                _msg += _target_state + "\" on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "All suitable VMs were successfully changed to the state"
                _msg += "\"" + _target_state + "\" on this experiment"
                cbdebug(_msg)
            return _status, _msg, None
        
    @trace
    def airunstate_actual(self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 0
        _target_state = obj_attr_list["target_state"].lower()
        _msg = "Going to change the state of all VMs for AI "
        _msg += obj_attr_list["name"] + " to the \"" + _target_state
        _msg += "\" state."
        cbdebug(_msg, True)

        self.runstate_list_for_ai(obj_attr_list, obj_attr_list["target_state"])
        if obj_attr_list["state_changed_vms"] != "0" :
            _status, _fmsg = self.parallel_obj_operation("runstate", obj_attr_list)
            
            if not _status :
                self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], _target_state)

        return _status, _fmsg
    
    @trace
    def airunstate(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _result = []
            _runstate_pending = False
            _fmsg = "An error has occurred, but no error message was captured"
            _obj_type = command.split('-')[0].upper()
            obj_attr_list["name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                _cloud_name = obj_attr_list["cloud_name"]
                
                if _status in [0, 483920, 912543] :
                    if _status not in [483920] :
                        self.osci.add_to_list(_cloud_name, "AI", "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], int(time()))
                        self.osci.pending_object_set(_cloud_name, "AI", obj_attr_list["uuid"], "status", "Changing state to: " + obj_attr_list["target_state"] + "(" + obj_attr_list["suspected_command"] + ")")
                        _runstate_pending = True
                
                    if _status == 483920 :
                        _tmp_result = self.continue_app(obj_attr_list)
                        _status = _tmp_result["status"]
                        _fmsg = _tmp_result["msg"]
                        _result = _tmp_result["result"]
                        obj_attr_list.update(_result)
                        obj_attr_list["target_state"] = "attached"
                        obj_attr_list["suspected_command"] = "run"
                    elif _status == 912543 :
                        _status, _fmsg, _result = self.airunstateall(parameters, obj_attr_list["suspected_command"])
                    elif not _status :
                        _status, _fmsg = self.airunstate_actual(obj_attr_list)
                        _result = obj_attr_list

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            unique_state_key = "-state-" + str(time())

            if _status :
                if _status != 9 :
                    _msg = "Could not change all VMs state: " + _fmsg
                    cberr(_msg, True)
                    obj_attr_list["tracking"] = "Change state request: " + _fmsg
                else :
                    _msg = _fmsg

                if "uuid" in obj_attr_list and self.osci :
                    self.osci.create_object(_cloud_name, "FAILEDTRACKINGAI", \
                                            obj_attr_list["uuid"] + \
                                            unique_state_key, \
                                            obj_attr_list, False, True, 3600)
            else :
                _msg = "All VMs on the AI to changed to the \"" + obj_attr_list["target_state"]
                _msg += "\" state successfully."
                cbdebug(_msg, True)
                obj_attr_list["tracking"] = "Change state request: success."
                self.osci.create_object(_cloud_name, "FINISHEDTRACKINGAI", obj_attr_list["uuid"] + unique_state_key, \
                                        obj_attr_list, False, True, 3600)
                if _runstate_pending :
                    self.osci.pending_object_remove(_cloud_name, "AI", obj_attr_list["uuid"], "status")
                    self.osci.remove_from_list(_cloud_name, "AI", "PENDING", obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)
                
            return self.package(_status, _msg, _result)

    @trace    
    def airesize(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = None
            
            obj_attr_list["name"] = "undefined"
            obj_attr_list["uuid"] = "undefined"   
            obj_attr_list["mgt_401_resize_request_originated"] = int(time())
            _resizable_ai = True

            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            if not _status :

                obj_attr_list["parallel_operations"] = {}
                _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"])
               
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_402_resize_request_sent"] = _time_mark_rrs - obj_attr_list["mgt_401_resize_request_originated"]
                           
                if _current_state and _current_state == "attached" :

                    self.osci.add_to_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_RESIZE", obj_attr_list["uuid"]) 
                    self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "resize")
                    
                    _delta = obj_attr_list["quantity"][0]
                    _nr_vms = obj_attr_list["quantity"][1:]
                    _vm_role = obj_attr_list["role"]

                    obj_attr_list["temp_vms"] = ''
                    _vm_command_list = ''
                    _vm_counter = int(obj_attr_list["vms_nr"])
                    _vg = ValueGeneration(self.pid)
                    _nr_vms = int(_vg.get_value(_nr_vms, 0))

                    _attach_action = ''

                    if _delta == "+" :

                        _cloud_ips = {}

                        if _vm_role + "_cloud_ips" in obj_attr_list :
                            if not _vm_role in _cloud_ips :
                                _cloud_ips[_vm_role] = obj_attr_list[_vm_role + "_cloud_ips"].split(';')

                        for _idx in range(0, int(_nr_vms)) :

                            if _vm_role + "_pref_host" in obj_attr_list :
                                _pool = obj_attr_list[_vm_role + "_pref_host"]
                            else :
                                if _vm_role + "_pref_pool" in obj_attr_list :
                                    _pool = obj_attr_list[_vm_role + "_pref_pool"]
                                else :
                                    _pool = "auto"

                            if _vm_role + "_meta_tag" in obj_attr_list :
                                _meta_tag = obj_attr_list[_vm_role + "_meta_tag"]
                            else :
                                _meta_tag = "empty"
            
                            if _vm_role + "_size" in obj_attr_list :
                                _size = obj_attr_list[_vm_role + "_size"]
                            else :
                                _size = "default"

                            _extra_parms = "base_type=" + obj_attr_list["base_type"]

                            if _vm_role + "_netid" in obj_attr_list :
                                _extra_parms += ",netid=" + obj_attr_list[_vm_role + "_netid"]
            
                            if _vm_role + "_cloud_vv" in obj_attr_list :
                                _extra_parms += ",cloud_vv=" + obj_attr_list[_vm_role + "_cloud_vv"]

                            if _vm_role in _cloud_ips :
                                _cloud_ip = ",cloud_ip=" + _cloud_ips[_vm_role].pop()
                            else :
                                _cloud_ip = ''

                            obj_attr_list["parallel_operations"][_vm_counter] = {} 
                            _pobj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,10000000000000000) + _vm_counter)))
                            _pobj_uuid = _pobj_uuid.upper()

                            obj_attr_list["temp_vms"] += _pobj_uuid + ','
                            obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _pobj_uuid
                            obj_attr_list["parallel_operations"][_vm_counter]["ai"] = obj_attr_list["uuid"]
                            obj_attr_list["parallel_operations"][_vm_counter]["aidrs"] = obj_attr_list["aidrs"]
                            obj_attr_list["parallel_operations"][_vm_counter]["type"] = obj_attr_list["type"]
                            obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] +\
                             ' ' + _vm_role + ' ' + _pool + ' ' + _meta_tag + ' ' +\
                              _size + ' ' + _attach_action + ' ' + _extra_parms + _cloud_ip
                            obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-attach"
                            _vm_command_list += obj_attr_list["cloud_name"] + ' ' +\
                             _vm_role + ", " + _pool + ", " + _meta_tag + ", " +\
                              _size + ", " + _attach_action + ", " + _extra_parms + _cloud_ip + "; "
                            _vm_counter += 1

                        obj_attr_list["temp_vms"] = obj_attr_list["temp_vms"][:-1]

                        _status, _fmsg = self.parallel_obj_operation("attach", obj_attr_list)

                        if not _status :
                            _vm_uuid_list = obj_attr_list["temp_vms"].split(',')

                            for _vm_uuid in _vm_uuid_list :

                                _vm_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VM", False, _vm_uuid, False)
                                obj_attr_list["vms"] += ',' + _vm_uuid + '|' + _vm_attr_list["role"] + '|' + _vm_attr_list["name"]

                            del obj_attr_list["temp_vms"]

                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], False, "vms", obj_attr_list["vms"])
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], False, "vms_nr", _vm_counter)

                    elif _delta == "-" :

                        _vm_list = obj_attr_list["vms"].split(',')

                        obj_attr_list["vms"] = ''
                        _destroyed_vms = 0
                        
                        _filter = True
                        for _vm in _vm_list :

                            _curr_vm_uuid, _curr_vm_role, _curr_vm_name = _vm.split('|')

                            if _curr_vm_role == _vm_role and \
                            _curr_vm_uuid != obj_attr_list["load_generator_vm"] \
                            and _curr_vm_uuid != obj_attr_list["load_manager_vm"] \
                            and _curr_vm_uuid != obj_attr_list["metric_aggregator_vm"] \
                            and _filter:

                                obj_attr_list["parallel_operations"][_vm_counter] = {}
                                obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _curr_vm_uuid
                                obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] + ' ' + _curr_vm_name + " true"
                                obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-detach"
                                _vm_command_list += obj_attr_list["cloud_name"] + ' ' + _curr_vm_name + " true" + ', '
                                _vm_counter -= 1 
                                _destroyed_vms += 1
                                if _destroyed_vms >= _nr_vms :
                                    _filter = False
                            
                            else :
                                obj_attr_list["vms"] += _vm + ','

                        obj_attr_list["vms"] = obj_attr_list["vms"][:-1]
                        obj_attr_list["vms_nr"] = _vm_counter
                        _status, _fmsg = self.parallel_obj_operation("detach", obj_attr_list)

                        _destroyed_vm_list = obj_attr_list["temp_vms"]
                        
                        if not _status :                            
                        
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], False, "vms", obj_attr_list["vms"])
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], False, "vms_nr", _vm_counter)
                            
                            if _destroyed_vms < _nr_vms :
                                _msg = "The request to destroy " + str(_nr_vms)
                                _msg += " VMs with the role \"" + _vm_role + "\""
                                _msg += " could not be entirely fulfilled. Only"
                                _msg += str(_destroyed_vms) + " VMs could be "
                                _msg += "destroyed."
                                cbdebug(_msg)

                    if "run_application_scripts" in obj_attr_list and obj_attr_list["run_application_scripts"].lower() != "false" :
                        _status, _fmsg  = self.parallel_vm_config_for_ai(obj_attr_list["cloud_name"], \
                                                                         obj_attr_list["uuid"], \
                                                                         "resize")
                    else :
                        _msg = "Bypassing application-specific \"setup\" operations"
                        _fmsg = "none"
                        cbdebug(_msg, True)
                        _status = 0

                    if not _status :
                        self.osci.remove_from_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_RESIZE", obj_attr_list["name"])
                        self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "attached")

                        _aux_dict = {}
                        for _vm in obj_attr_list["vms"].split(',') :
                            _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                            
                            if _vm_role in _aux_dict :
                                _aux_dict[_vm_role] += 1
                            else :
                                _aux_dict[_vm_role] = 1

                            obj_attr_list["mgt_403_resize_request_completed"] = int(time()) - _time_mark_rrs
    
    
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              _vm_uuid, \
                                                              False, \
                                                              "mgt_401_resize_request_originated", \
                                                              obj_attr_list["mgt_401_resize_request_originated"])
        
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              _vm_uuid, \
                                                              False, \
                                                              "mgt_402_resize_request_sent", \
                                                              obj_attr_list["mgt_402_resize_request_sent"])
                            
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              _vm_uuid, \
                                                              False, \
                                                              "mgt_403_resize_request_completed", \
                                                              obj_attr_list["mgt_403_resize_request_completed"])

                        _tiers = obj_attr_list["sut"].split("->")
                        obj_attr_list["sut"] = ''

                        for _tier in _tiers :
                            _nr_vms, _vm_role = _tier.split("_x_")
                            obj_attr_list["sut"] += str(_aux_dict[_vm_role]) + "_x_" + _vm_role + "->"

                        obj_attr_list["sut"] = obj_attr_list["sut"][:-2]
                        
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], False, "sut", obj_attr_list["sut"])

                        _status = 0
                        _result = obj_attr_list

                else :

                    _fmsg = "AI object named \"" + obj_attr_list["name"] + "\" could "
                    _fmsg += "not be resized because it is on the "
                    _fmsg += "\"" + _current_state + "\" state."
                    _status = 817

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "resized on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully resized "
                _msg += "on this experiment."
                cbdebug(_msg)
            return self.package(_status, _msg, None)

    @trace    
    def aicapture(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _vm_name = "Unknown"
            _result = None
            obj_attr_list["name"] = "undefined"
            obj_attr_list["uuid"] = "undefined"

            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            if not _status :
                _capture_role = obj_attr_list["capture_role"]
                for _vm in obj_attr_list["vms"].split(',') :
                    _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                    if _vm_role == _capture_role :
                        _capture_vm_attr_list = {}
                        _msg = "About to call vmcapture method, from aicapture method"
                        cbdebug(_msg)
                        if "async" in obj_attr_list and obj_attr_list["async"] == "true" :
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, obj_attr_list["cloud_name"] + ' ' + _vm_name, "vm-capture")
                        elif not BaseObjectOperations.default_cloud :
                            _cloud_name = parameters.split()[0]
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, _cloud_name + ' ' + _vm_name, "vm-capture")
                        else :
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, _vm_name, "vm-capture")
                        break
                _result = obj_attr_list

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = "One of the VMs (\"" + _vm_name + "\") belonging to the "
                _msg += _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "captured on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "One of the VMs (\"" + _vm_name + "\") belonging to the "
                _msg += _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully captured "
                _msg += "on this experiment."
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace            
    def parallel_obj_operation(self, operation_type, obj_attr_list) :
        '''
        TBD
        '''
        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _rollback = False
        _thread_pool = None
        _rollback = False
        _child_failure = False 

        try :
                
            for _object in obj_attr_list["parallel_operations"].keys() :
                
                obj_attr_list["parallel_operations"][_object][operation_type + "_parallel"] = "true"
                _command = obj_attr_list["parallel_operations"][_object]["parameters"]
                _operation = obj_attr_list["parallel_operations"][_object]["operation"]
                _obj_type = _operation.split('-')[0]
                
                if not _thread_pool :
                    pool_key = operation_type
                    pool_key += '_' + _obj_type + "s_with_parallelism_"
                    pool_key += str(obj_attr_list[operation_type + "_parallelism"])

                    if pool_key not in self.thread_pools :
                        _thread_pool = ThreadPool(int(obj_attr_list[operation_type + "_parallelism"]))
                        self.thread_pools[pool_key] = _thread_pool
                    else :
                        _thread_pool = self.thread_pools[pool_key]
                        
                if operation_type == "attach" :       
                    _func = self.objattach
                elif operation_type == "detach" :
                    _func = self.objdetach
                elif operation_type == "capture" and _obj_type.lower() == "vm" :
                    _func = self.vmcapture
                elif operation_type == "runstate" and _obj_type.lower() == "vm" :
                    _func = self.vmrunstate
                elif operation_type == "resize" and _obj_type.lower() == "vm" :
                    _func = self.vmresize
                elif operation_type == "resize" and _obj_type.lower() == "ai" :
                    _func = self.airesize
                else :
                    _status = 1817
                    _msg = "Unknown operation/object type"
                    cberr(_msg)
                    raise self.ObjectOperationException(_msg, _status)                    

                serial_mode = False # only used for debugging

                _tmp_list = copy.deepcopy(obj_attr_list["parallel_operations"][_object])
                
                if serial_mode : 
                    _status, _fmsg, _object = _func(_tmp_list, _command, _operation)
                    if int(_status) :
                        _fmsg += " "
                        _child_failure = True
                        _rollback = True
                        break
                else :
                    _thread_pool.add_task(_func, _tmp_list, _command, _operation)

            if _thread_pool :
                _results = _thread_pool.wait_completion()
                for (_status, _fmsg, _object) in _results :
                    if int(_status) :
                        _fmsg += " "
                        _child_failure = True
                        _rollback = True
                        break
                
            # Make sure the operations succeeded
            if not _child_failure :
                for _object in obj_attr_list["parallel_operations"].keys() :
                    _obj_type = obj_attr_list["parallel_operations"][_object]["operation"].split('-')[0].upper()
                    _obj_uuid = obj_attr_list["parallel_operations"][_object]["uuid"]
                    _command = obj_attr_list["parallel_operations"][_object]["parameters"]
                    _exists = self.osci.object_exists(obj_attr_list["cloud_name"], _obj_type, _obj_uuid, False) 
                    if _exists and operation_type == "attach" :
                        True
                    elif operation_type == "detach" :
                        if _exists :
                            _status = 19
                            break
                    elif operation_type == "runstate" :
                        _state = self.osci.get_object_state(obj_attr_list["cloud_name"], "VM", _obj_uuid)
                        if _command.count("save") :
                            if _state != "save" :
                                _status = 20
                                _rollback = True
                                break
                        elif (_command.count("suspend") or _command.count("fail")) :
                            if _state not in [ "suspend", "fail" ] :
                                _status = 22
                                _rollback = True
                                break
                        elif _state != "attached" :
                            _status = 21
                            _rollback = True
                            _fmsg = "Objects are not in the right state. Runstate operation failed."
                            break
                    else :
                        _status = 18
                        _rollback = True
                        break
        
                    if operation_type == "attach" :
                        obj_attr_list["arrival"] = int(time())

            if _rollback :
                if not _child_failure :
                    _fmsg = ""
                _fmsg += "A rollback might be needed (only for VMs)."
            else :
                _status = 0

        except KeyboardInterrupt :
            _rollback = True
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("Signal children to abort...", True)
            if _thread_pool :
                _thread_pool.abort()
            
        except self.ObjectOperationException, obj :
            _status = 45
            _fmsg = str(obj.msg)
            if _thread_pool :
                _thread_pool.abort()
                
        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            if _thread_pool :
                _thread_pool.abort()
                
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            if _thread_pool :
                _thread_pool.abort()

        finally :
            if _status :
                _msg = "Parallel object operation failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                del obj_attr_list["parallel_operations"]
                _msg = "Parallel object operation success."
                cbdebug(_msg)
            return _status, _msg

    def aiexecute(self, cloud_name, object_type, object_uuid) :
        '''
        TBD
        '''
        _ai_state = True
        _prev_load_level = 0
        _prev_load_duration = 0
        _prev_load_id =  0

        _initial_ai_attr_list = self.osci.get_object(cloud_name, "AI", False, object_uuid, False)
        
        _mode = _initial_ai_attr_list["mode"]
        _check_frequency = float(_initial_ai_attr_list["update_frequency"])

        while _ai_state :

            if _mode == "controllable" :
                _ai_state = self.osci.get_object_state(cloud_name, "AI", object_uuid)
                _ai_attr_list = self.osci.get_object(cloud_name, "AI", False, object_uuid, False)
                _mode = _ai_attr_list["mode"]
                _check_frequency = float(_ai_attr_list["update_frequency"])
            else :
                _ai_state = "attached"
                _ai_attr_list = _initial_ai_attr_list
                
            if _ai_state and _ai_state == "attached" :
                _load = self.get_load(cloud_name, _ai_attr_list, False, \
                                      _prev_load_level, _prev_load_duration, \
                                      _prev_load_id)

                if _load :
                    _prev_load_level = _ai_attr_list["current_load_level"]
                    _prev_load_duration = _ai_attr_list["current_load_duration"]
                    _prev_load_id = _ai_attr_list["current_load_id"]

                if _mode == "controllable" :
                    self.update_object_attribute(cloud_name, \
                                                 object_type.upper(), \
                                                 object_uuid, \
                                                 "current_load_level", \
                                                 _ai_attr_list["current_load_level"]) 
                        
                    self.update_object_attribute(cloud_name, \
                                                 object_type.upper(), \
                                                 object_uuid, \
                                                 "current_load_duration", \
                                                 _ai_attr_list["current_load_duration"])
    
                    self.update_object_attribute(cloud_name, \
                                                 object_type.upper(), \
                                                 object_uuid, \
                                                 "current_load_id", \
                                                 _ai_attr_list["current_load_id"])
 
                _msg = "Preparing to execute AI reset"
                cbdebug(_msg)

                _reset_status, _fmsg = self.parallel_vm_config_for_ai(cloud_name, \
                                                                object_uuid, \
                                                                "reset")

                if not _reset_status :
                    _msg = "AI reset executed successfully."
                    cbdebug(_msg)
                else : 
                    _msg = "AI reset failed: " + _fmsg
                    cberr(_msg)
                    # If we fail, sleep a little and retry
                    sleep(_check_frequency * 2)

                if not _reset_status and _ai_attr_list["load_generator_ip"] == _ai_attr_list["load_manager_ip"] :
                    _cmd = "~/" + _ai_attr_list["start"] + ' '
                    _cmd += str(_ai_attr_list["current_load_profile"]) + ' '                    
                    _cmd += str(_ai_attr_list["current_load_level"]) + ' '
                    _cmd += str(_ai_attr_list["current_load_duration"]) + ' '
                    _cmd += str(_ai_attr_list["current_load_id"])
    
                    _load_level_time = 0
    
                    # You cannot Popen() with a PIPE unless you plan on emptying
                    # the pipe. The OS pipe has a limited buffer size and if you
                    # don't empty it, the process will block on write() to the PIPE.
                    _proc_h = Popen(_cmd, shell=True)
                    # _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
                    if _proc_h.pid :
                        _msg = "Load generating command \"" + _cmd + "\" "
                        _msg += " was successfully started."
                        _msg += "The process id is " + str(_proc_h.pid) + "."
                        cbdebug(_msg)
                    
                        _msg = "Waiting for the load generating process to "
                        _msg += "terminate."
                        cbdebug(_msg)
                        
                        #waitpid(-1, 0)
                        _proc_h.wait()
                else :
                    # Will have to create something here later, probably using
                    # pubsub
                    sleep(_check_frequency)

            else :
                # Only reset individual applications on the AI. Don't send
                # any load.
                _msg = object_type.upper() + " object " + object_uuid 
                _msg += " state was set to \"" + _ai_state + "\". No load will "
                _msg += "be applied until the state is changed. The "
                _msg += "current load will be allowed to finish its course."
                cbdebug(_msg)
                self.parallel_vm_config_for_ai(cloud_name, object_uuid, "reset")

        _msg = "AI \"state key\" was removed. The Load Manager will now end its execution"
        cbdebug(_msg)
        _status = 0
            
        return _status, _msg

    @trace
    def aidsubmit(self, cloud_name, base_dir, object_type, object_uuid) :
        '''
        TBD
        '''
        _aidrs_state = True

        while _aidrs_state :

            _inter_arrival_time = 0

            _inter_arrival_time_start = int(time())

            _aidrs_state = self.osci.get_object_state(cloud_name, "AIDRS", object_uuid)

            _aidrs_attr_list = self.osci.get_object(cloud_name, "AIDRS", False, object_uuid, False)

            _check_frequency = int(_aidrs_attr_list["update_frequency"])

            _aidrs_overload, _msg = self.get_aidrs_params(cloud_name, _aidrs_attr_list)

            _curr_iait = int(_aidrs_attr_list["current_inter_arrival_time"])

            if not _aidrs_overload :
                
                if _aidrs_state and _aidrs_state != "stopped" :

                    _ai_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0, \
                                                                    1000000000000000000)))).upper()

                    _cmd = base_dir + "/cbact"
                    _cmd += " --procid=" + self.pid
                    _cmd += " --osp=" + dic2str(self.osci.oscp())
                    _cmd += " --msp=" + dic2str(self.msci.mscp())

                    _cmd += " --oop=" + cloud_name + ',' + _aidrs_attr_list["type"] + ',' + _aidrs_attr_list["load_level"]
                    _cmd += ',' + _aidrs_attr_list["load_duration"] + ',' + _aidrs_attr_list["lifetime"]  + ',' + object_uuid

                    _cmd += " --operation=ai-attach"
                    _cmd += " --cn=" + cloud_name
                    _cmd += " --uuid=" + _ai_uuid
                    _cmd += " --daemon"
                    #_cmd += "  --debug_host=127.0.0.1"

                    _proc_man = ProcessManagement(username = _aidrs_attr_list["username"], \
                                                  cloud_name = _aidrs_attr_list["cloud_name"])

                    # Here, instead of using "start_daemon", "run_os_command" is
                    # used to save a few seconds. 
                    _aid_pid = _proc_man.run_os_command(_cmd)
            
                    if _aid_pid :

                        _msg = "AI attachment command \"" + _cmd + "\" "
                        _msg += "was successfully started."
                        #_msg += "The process id is " + str(_aid_pid) + "."
                        cbdebug(_msg)

                        _obj_id = _ai_uuid + '-' + "attach"
                        self.update_process_list(cloud_name, "AI", \
                                                 _obj_id, \
                                                 str(_aid_pid), \
                                                 "add")
                    else :
                        _msg = "AI attachment command \"" + _cmd + "\" "
                        _msg += "could not be successfully started."
                        cberr(_msg)
                else :
                    _msg = "Unable to get state, or state is \"stopped\"."
                    _msg += "Will stop creating new AIs until the AS state"
                    _msg += " changes."
                    cbdebug(_msg)
            else :
                _msg = "AIDRS is overloaded because " + _msg
                _msg += ". Will keep checking its state and "
                _msg += " destroying overdue AIs, but will not create new ones"
                _msg += " until the number of AIs/Daemons drops below the limit."
                cbdebug(_msg)

                if _curr_iait < _check_frequency :
                    _check_frequency = _curr_iait / 2

            _aidrs_state = self.osci.get_object_state(cloud_name, "AIDRS", object_uuid)

            if not _aidrs_state  :
                _msg = "AIDRS object " + object_uuid 
                _msg += " state could not be obtained. This process "
                _msg += " will exit, leaving all the AIs behind."
                cbdebug(_msg)
                break

            elif _aidrs_state == "stopped" :
                _msg ="AIDRS object " + object_uuid 
                _msg += " state was set to \"stopped\"."
                cbdebug(_msg)
            else :
                True

            _inter_arrival_time = int(time()) - _inter_arrival_time_start

            while _inter_arrival_time < _curr_iait :

                _inter_arrival_time = int(time()) - _inter_arrival_time_start
                
                if _inter_arrival_time - _curr_iait < _check_frequency :
                    sleep(_check_frequency/10)
                else :
                    sleep(_check_frequency)

        _msg = "This AIDRS daemon has detected that the AIDRS object associated to it was "
        _msg += "detached. Proceeding to remove its pid from"
        _msg += " the process list before finishing."
        cbdebug(_msg)
        _status = 0

        return _status, _msg

    @trace
    def aidremove(self, cloud_name, base_dir, object_type, object_uuid) :
        '''
        TBD
        '''
        _aidrs_state = True

        while _aidrs_state :

            _aidrs_attr_list = self.osci.get_object(cloud_name, "AIDRS", False, \
                                                    object_uuid, False)

            _my_overdue_ais = self.osci.query_by_view(cloud_name, "AI", "BYAIDRS", \
                                                      object_uuid, \
                                                      "departure", \
                                                      "overdue")

            if len(_my_overdue_ais) :

                _msg = "Some AIs have reached the end of their "
                _msg += "lifetimes, and will now be removed."
                _msg += "Overdue AI list is :" + ','.join(_my_overdue_ais)
                cbdebug(_msg)

                for _ai in _my_overdue_ais :
                    _ai_uuid, _ai_name = _ai.split('|')
                    
                    _current_state = self.osci.get_object_state(cloud_name, "AI", _ai_uuid)

                    if _current_state and _current_state == "attached" :                    
                        _cmd = base_dir + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.osci.oscp())
                        _cmd += " --msp=" + dic2str(self.msci.mscp())
                        _cmd += " --oop=" + cloud_name + ',' + _ai_name + ',true'
                        _cmd += " --operation=ai-detach"
                        _cmd += " --cn=" + cloud_name
                        _cmd += " --uuid=" + _ai_uuid                        
                        _cmd += " --daemon"
                        #_cmd += "  --debug_host=127.0.0.1"

                        _proc_man = ProcessManagement(username = _aidrs_attr_list["username"], \
                                                      cloud_name = _aidrs_attr_list["cloud_name"])

                        # Here, instead of using "start_daemon", "run_os_command" is
                        # used to save a few seconds.                 
                        _aid_pid = _proc_man.run_os_command(_cmd)

                        if _aid_pid :
                            _msg = "Overdue AI detachment command \"" + _cmd + "\" "
                            _msg += " was successfully started."
                            #_msg += "The process id is " + str(_aid_pid) + "."
                            cbdebug(_msg)

                            _obj_id = _ai_uuid + '-' + "detach"
                            self.update_process_list(cloud_name, "AI", \
                                                     _obj_id, \
                                                     str(_aid_pid), \
                                                     "add")
                    else :
                        _msg = "AI \"" + _ai_uuid + "\" is on the \""
                        _msg += _current_state + "\" and therefore cannot "
                        _msg += "detached."
                        cbdebug(_msg)
            else :
                _msg = "No AIs have reached the end of their lifetimes."
                cbdebug(_msg)

            _aidrs_state = self.osci.get_object_state(cloud_name, "AIDRS", object_uuid)

            if not _aidrs_state  :
                print "X"
                _msg = "AIDRS object " + object_uuid 
                _msg += " state could not be obtained. This process "
                _msg += " will exit, leaving all the AIs behind."
                cbdebug(_msg)
                break

            elif _aidrs_state == "stopped" :
                _msg ="AIDRS object " + object_uuid 
                _msg += " state was set to \"stopped\"."
                cbdebug(_msg)
            else :
                True

            sleep(int(_aidrs_attr_list["update_frequency"]))

        _msg = "This AIDRS daemon has detected that the AIDRS object associated to it was "
        _msg += "detached. Proceeding to remove its pid from"
        _msg += " the process list before finishing."
        cbdebug(_msg)
        _status = 0

        return _status, _msg

    @trace
    def vmcrsubmit(self, cloud_name, base_dir, object_type, object_uuid) :
        '''
        TBD
        '''
        _vmcrs_state = True

        while _vmcrs_state :

            _vmcrs_state = self.osci.get_object_state(cloud_name, "VMCRS", object_uuid)

            _vmcrs_attr_list = self.osci.get_object(cloud_name, "VMCRS", False, object_uuid, False)

            _type_list = self.osci.get_list(_vmcrs_attr_list["cloud_name"], "GLOBAL", "ai_types")

            _check_frequency = float(_vmcrs_attr_list["update_frequency"])

            _ivmcat_parms = _vmcrs_attr_list["ivmcat"]
            _vg = ValueGeneration(self.pid)
            _vmcr_inter_arrival_time = int(_vg.get_value(_ivmcat_parms, 0))

            if "nr_simultaneous_cap_reqs" in _vmcrs_attr_list and \
            int(_vmcrs_attr_list["nr_simultaneous_cap_reqs"]) >= int(_vmcrs_attr_list["max_simultaneous_cap_reqs"]) :
                _vmcrs_overload = True
            else :
                _vmcrs_overload = False

            if "nr_total_cap_reqs" in _vmcrs_attr_list and \
            int(_vmcrs_attr_list["nr_total_cap_reqs"]) >= int(_vmcrs_attr_list["max_total_cap_reqs"]) :
                _vmcrs_overload = True
            else :
                _vmcrs_overload = False

            _inter_arrival_time = 0

            if not _vmcrs_overload :

                _msg = "The selected inter-VM Capture Request arrival time was "
                _msg += str(_vmcr_inter_arrival_time) + " seconds."
                cbdebug(_msg)

                if _vmcrs_state and _vmcrs_state != "stopped" :

                    if _vmcrs_attr_list["scope"] in _type_list :
                        _view = "BYTYPE"
                    elif _vmcrs_attr_list["scope"] == _vmcrs_attr_list["username"] :
                        _view = "BYUSERNAME"
                    else :
                        _view = "BYAIDRS"

                    _capturable_ais = self.osci.query_by_view(cloud_name, \
                                                              "AI", \
                                                              _view, \
                                                              _vmcrs_attr_list["scope"],\
                                                               "arrival", \
                                                               "minage:" + _vmcrs_attr_list["min_cap_age"])

                    if len(_capturable_ais) :
                        _selected_ai = choice(_capturable_ais)
                        _ai_uuid, _ai_name = _selected_ai.split('|')
                        _ai_attr_list = self.osci.get_object(cloud_name, "AI", False, _ai_uuid, False)    
                        _vm_list = _ai_attr_list["vms"].split(',')
                        _vm_candidate_list = []

                        for _vm in _vm_list :
                            _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                        if _vm_role == _ai_attr_list["capture_role"] :
                            _vm_candidate_list.append(_vm)
                            _selected_vm = choice(_vm_candidate_list)

                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                        _cmd = base_dir + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.osci.oscp())
                        _cmd += " --msp=" + dic2str(self.msci.mscp())
                        _cmd += " --oop=" + cloud_name + ',' + _vm_name + ',' + object_uuid
                        _cmd += " --operation=vm-capture"
                        _cmd += " --cn=" + cloud_name
                        _cmd += " --uuid=" + _vm_uuid
                        _cmd += " --daemon"
                        #_cmd += "  --debug_host=127.0.0.1"

                        cbdebug(_cmd)
                        
                        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
                        if _proc_h.pid :
                            _msg = "VM capture command \"" + _cmd + "\" "
                            _msg += " was successfully started."
                            _msg += "The process id is " + str(_proc_h.pid) + "."
                            cbdebug(_msg)

                            _obj_id = _ai_uuid + '-' + "capture"
                            self.update_process_list(cloud_name, "AI", \
                                                     _obj_id, \
                                                     str(_proc_h.pid), \
                                                     "add")

                    else :
                        _msg = "No VMs are eligible for capture"
                        _inter_arrival_time = _check_frequency * 2
                        cbdebug(_msg)

                else :
                    _msg = "Unable to get state, or state is \"stopped\"."
                    _msg += "Will stop capturing new VMs until the VMCRS state"
                    _msg += " changes."
                    cbdebug(_msg)

            else :
                _msg = "VMCRS object reached maximum number of Capture Requests"
                _msg += " allowed. Will keep checking its state, but it will"
                _msg += " not capture any more VMs until the maximum number of"
                _msg += " capture requests is changed."
                cbdebug(_msg)
                _inter_arrival_time = _check_frequency * 2

            _inter_arrival_time_start = time()

            while _inter_arrival_time < _vmcr_inter_arrival_time :

                _vmcrs_state = self.osci.get_object_state(cloud_name, "VMCRS", object_uuid)
                
                if not _vmcrs_state  :
                    _msg = "VMCRS object " + object_uuid 
                    _msg += " state could not be obtained. This process "
                    _msg += " will exit, leaving all the AIs behind."
                    cbdebug(_msg)
                    break
                elif _vmcrs_state == "stopped" :
                    _msg ="VMCRS object " + object_uuid 
                    _msg += " state was set to \"stopped\"."
                    cbdebug(_msg)
                else :
                    True
                sleep(_check_frequency)
                _inter_arrival_time = time() - _inter_arrival_time_start

        _msg = "This VMCRS daemon has detected that the VMCRS object associated to it was "
        _msg += "detached. Proceeding to remove its pid from"
        _msg += " the process list before finishing."
        cbdebug(_msg)
        _status = 0
        
        return _status, _msg

    def firsubmit(self, cloud_name, base_dir, object_type, object_uuid) :
        '''
        TBD
        '''
        _firs_state = False

        while _firs_state :

            _firs_state = self.osci.get_object_state(cloud_name, "FIRS", object_uuid)

            _firs_attr_list = self.osci.get_object(cloud_name, "FIRS", False, object_uuid, False)

            _type_list = self.osci.get_list(_firs_attr_list["cloud_name"], "GLOBAL", "ai_types")

            _check_frequency = float(_firs_attr_list["update_frequency"])

            _ifat_parms = _firs_attr_list["ifat"]
            _vg = ValueGeneration(self.pid)
            _fault_inter_arrival_time = int(_vg.get_value(_ifat_parms, 0))

            _ftl_parms = _firs_attr_list["ftl"]
            _fault_time_length = int(_vg.get_value(_ftl_parms, 0))

            if "nr_simultaneous_faults" in _firs_attr_list and \
            int(_firs_attr_list["nr_simultaneous_faults"]) >= int(_firs_attr_list["max_simultaneous_faults"]) :
                _firs_overload = True
            else :
                _firs_overload = False

            if "nr_total_faults" in _firs_attr_list and \
            int(_firs_attr_list["nr_total_faults"]) >= int(_firs_attr_list["max_total_faults"]) :
                _firs_overload = True
            else :
                _firs_overload = False

            _inter_arrival_time = 0

            if not _firs_overload :

                _msg = "The selected inter-Fault Injection Request arrival time was "
                _msg += str(_fault_inter_arrival_time) + " seconds."
                cbdebug(_msg)

                if _firs_state and _firs_state != "stopped" :

                    if _firs_attr_list["scope"] in _type_list :
                        _view = "BYTYPE"
                    elif _firs_attr_list["scope"] == _firs_attr_list["username"] :
                        _view = "BYUSERNAME"
                    else :
                        _view = "BYAIDRS"

                    _capturable_ais = self.osci.query_by_view(cloud_name, \
                                                              "AI", \
                                                              _view, \
                                                              _firs_attr_list["scope"],\
                                                               "arrival", \
                                                               "minage:" + _firs_attr_list["min_cap_age"])

                    if len(_capturable_ais) :
                        _selected_ai = choice(_capturable_ais)
                        _ai_uuid, _ai_name = _selected_ai.split('|')
                        _ai_attr_list = self.osci.get_object(cloud_name, "AI", False, _ai_uuid, False)    
                        _vm_list = _ai_attr_list["vms"].split(',')
                        _vm_candidate_list = []

                        for _vm in _vm_list :
                            _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                        if _vm_role == _ai_attr_list["capture_role"] :
                            _vm_candidate_list.append(_vm)
                            _selected_vm = choice(_vm_candidate_list)

                        _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                        _cmd = base_dir + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.osci.oscp())
                        _cmd += " --msp=" + dic2str(self.msci.mscp())
                        _cmd += " --oop=" + cloud_name + ',' + _vm_name + ',' + object_uuid
                        _cmd += " --operation=vm-capture"
                        _cmd += " --cn=" + cloud_name
                        _cmd += " --uuid=" + _vm_uuid
                        _cmd += " --daemon"
                        #_cmd += "  --debug_host=127.0.0.1"

                        cbdebug(_cmd)
                        
                        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
                        if _proc_h.pid :
                            _msg = "VM capture command \"" + _cmd + "\" "
                            _msg += " was successfully started."
                            _msg += "The process id is " + str(_proc_h.pid) + "."
                            cbdebug(_msg)

                            _obj_id = _ai_uuid + '-' + "capture"
                            self.update_process_list(cloud_name, "AI", \
                                                     _obj_id, \
                                                     str(_proc_h.pid), \
                                                     "add")

                    else :
                        _msg = "No VMs are eligible for capture"
                        _inter_arrival_time = _check_frequency * 2
                        cbdebug(_msg)

                else :
                    _msg = "Unable to get state, or state is \"stopped\"."
                    _msg += "Will stop capturing new VMs until the VMCRS state"
                    _msg += " changes."
                    cbdebug(_msg)

            else :
                _msg = "VMCRS object reached maximum number of Capture Requests"
                _msg += " allowed. Will keep checking its state, but it will"
                _msg += " not capture any more VMs until the maximum number of"
                _msg += " capture requests is changed."
                cbdebug(_msg)
                _inter_arrival_time = _check_frequency * 2

            _inter_arrival_time_start = time()

            while _inter_arrival_time < _fault_inter_arrival_time :

                _firs_state = self.osci.get_object_state(cloud_name, "VMCRS", object_uuid)
                
                if not _firs_state  :
                    _msg = "FIRS object " + object_uuid 
                    _msg += " state could not be obtained. This process "
                    _msg += " will exit, leaving all the AIs behind."
                    cbdebug(_msg)
                    break
                elif _firs_state == "stopped" :
                    _msg ="FIRS object " + object_uuid 
                    _msg += " state was set to \"stopped\"."
                    cbdebug(_msg)
                else :
                    True
                sleep(_check_frequency)
                _inter_arrival_time = time() - _inter_arrival_time_start

        _msg = "This FIRS daemon has detected that the FIRS object associated to it was "
        _msg += "detached. Proceeding to remove its pid from"
        _msg += " the process list before finishing."
        cbdebug(_msg)
        _status = 0
        
        return _status, _msg
    
    @trace
    def continue_vm(self, obj_attr_list) :
        '''
        TBD
        '''
        status = 342
        cloud_name = obj_attr_list["cloud_name"]
        started_uuid = obj_attr_list["uuid"]
        vm = {}
        info = "unknown error"
        
        try :
            sub_channel = self.osci.subscribe(cloud_name, "VM", "staging")
            self.osci.publish_message(cloud_name, "VM", "staging", started_uuid + ";continue;success", 1, 3600)
            for message in sub_channel.listen() :
                args = str(message["data"]).split(";")
                if len(args) != 3 :
                    cbdebug("Message is not for me: " + str(args))
                    continue
                uuid, status, info = args
                if started_uuid == uuid :
                    if status == "vmfinished" :
                        attrs = self.osci.get_object(cloud_name, "VM", False, uuid, False)
                        vm = {"status" : 0, "msg" : "Successfully run VM after prior initialization", "result": attrs}
                        break
                    if status == "error" :
                        vm = {"status" : 432, "msg" : info, "result" : None}
                        break
                    
            sub_channel.unsubscribe()
        except self.osci.ObjectStoreMgdConnException, obj :
            vm["msg"] = "Failed to run initialized VM: " + str(obj)
            vm["status"] = obj.status
            vm["result"] = None 
        
        return vm

    @trace
    def pause_vm(self, obj_attr_list, sub_channel, vm) :
        '''
        TBD
        '''
        cloud_name = obj_attr_list["cloud_name"]
        info = "unknown error"
        
        try :
            if not int(vm["status"]) :
                for message in sub_channel.listen() :
                    args = str(message["data"]).split(";")
                    if len(args) != 3 :
                        cbdebug("Message is not for me: " + str(args))
                        continue
                    uuid, status, info = args
                    if vm["result"]["uuid"] == uuid :
                        if status == "vmready" :
                            vm["status"] = 0
                            vm["msg"] = "Successful VM initialization." 
                            vm["result"] = str2dic(info)
                            break
                        if status == "error" :
                            vm["status"] = 343 
                            vm["msg"] = "Failure in Object Storage PubSub: " + info 
                            vm["result"] = None
                            break
                            
            # If you change this message, change the GUI, because the GUI depends on it
            self.osci.pending_object_set(cloud_name, \
                                         "VM", \
                                         vm["result"]["uuid"], "status", \
                                         "Paused waiting for run command from user [" + vm["result"]["uuid"] + "]...")
            sub_channel.unsubscribe()

        except self.osci.ObjectStoreMgdConnException, obj :
            vm["status"] = obj.status
            vm["info"] = str(obj)
            vm["result"] = None
        
        return vm
    
    @trace
    def pause_app(self, obj_attr_list, sub_channel, app) :
        '''
        TBD
        '''
        info = "unknown error"
        total = 0
        count = 0
        cloud_name = obj_attr_list["cloud_name"]
        
        try :
            app["vms"] = {}
            if not int(app["status"]) :
                for message in sub_channel.listen() :
                    args = str(message["data"]).split(";")
                    if len(args) != 3 :
                        cbdebug("Message is not for me: " + str(args))
                        continue
                    uuid, status, info = args
                    if app["result"]["uuid"] == uuid :
                        if status == "vmready" :
                            vm = str2dic(info)
                            if vm["uuid"] not in app["vms"] :
                                app["vms"][vm["uuid"]] = vm
                                count += 1
                            if total > 0 and count == total :
                                app["status"] = 0
                                app["msg"] = "Successful app initialization." 
                                app["result"]["vms"] = app["vms"]
                                app["result"]["name"] = vm["ai_name"] 
                                break
                        elif status == "vmcount" :
                            total = int(info)
                        elif status == "error" :
                            app["status"] = 343 
                            app["msg"] = "Failure in Object Storage PubSub: " + info 
                            app["result"] = None
                            break
                            
            # If you change this message, change the GUI, because the GUI depends on it
            self.osci.pending_object_set(cloud_name, \
                                         "AI", \
                                         app["result"]["uuid"], "status", \
                                         "Paused waiting for run command from user [" + app["result"]["uuid"] + "]...")
            sub_channel.unsubscribe()

        except self.osci.ObjectStoreMgdConnException, obj :
            app["status"] = obj.status
            app["info"] = str(obj)
            app["result"] = None
        
        return app 

    @trace
    def continue_app(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            status = 342
            cloud_name = obj_attr_list["cloud_name"]
            started_uuid = obj_attr_list["uuid"]
            app = {}
            info = "unknown error"
            sub_channel = self.osci.subscribe(cloud_name, "VM", "staging")
            self.osci.publish_message(cloud_name, "VM", "staging", started_uuid + ";continue;success", 1, 3600)
            for message in sub_channel.listen() :
                args = str(message["data"]).split(";")
                if len(args) != 3 :
                    cbdebug("Message is not for me: " + str(args))
                    continue
                uuid, status, info = args
                if started_uuid == uuid :
                    if status == "appfinished" :
                        attrs = self.osci.get_object(cloud_name, "AI", False, uuid, False)
                        app = {"status" : 0, "msg" : "Successfully run application after prior initialization.", "result": attrs}
                        break
                    if status == "error" :
                        app = {"status" : 432, "msg" : info, "result" : None}
                        break
                    
            sub_channel.unsubscribe()
        except self.osci.ObjectStoreMgdConnException, obj :
            app["msg"] = "Failed to run initialized Application: " + str(obj)
            app["status"] = obj.status
            app["result"] = None
        
        return app
