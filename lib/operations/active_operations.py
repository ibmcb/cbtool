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
    Created on Nov 27, 2011

    Active Object Operations Library

    @author: Marcio A. Silva, Michael R. Galaxy
'''
from os import chmod, access, F_OK
from random import choice, randint
from time import time, sleep
from subprocess import Popen, PIPE
from re import sub
from uuid import uuid5, NAMESPACE_DNS

from lib.remote.process_management import ProcessManagement
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, dic2str, get_bootstrap_command, selectively_print_message, DataOpsException
from lib.auxiliary.value_generation import ValueGeneration
from lib.stores.stores_initial_setup import StoreSetupException
from lib.auxiliary.thread_pool import ThreadPool
from lib.auxiliary.data_ops import selective_dict_update, natural_keys
from lib.auxiliary.config import parse_cld_defs_file, load_store_functions, get_available_clouds, rewrite_cloudconfig, rewrite_cloudoptions
from lib.clouds.shared_functions import CldOpsException
from lib.remote.network_functions import Nethashget
from lib.remote.network_functions import Nethashget, hostname2ip, NetworkException
from .base_operations import BaseObjectOperations

import copy
import threading
import os
import sys
import socket
import telnetlib
import traceback

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
                
                _idmsg = "\nThe " + cld_attr_lst["model"].upper() + " cloud named \""
                _idmsg += cld_attr_lst["name"] + "\""
                _smsg = _idmsg + " was already attached to this experiment."
                _fmsg = _idmsg + " could not be attached to this experiment: "

                if not self.expid :                
                    _time_attr_list = self.osci.get_object(cld_attr_lst["name"], "GLOBAL", False, "time", False)
                    self.expid = _time_attr_list["experiment_id"]

                _expid = self.expid
                    
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

                _idmsg = "\nThe " + cld_attr_lst["model"].upper() + " cloud named \""
                _idmsg += cld_attr_lst["cloud_name"] + "\""
                _smsg = _idmsg + " was successfully attached to this "
                _smsg += "experiment."
                _fmsg = _idmsg + " could not be attached to this experiment: "

                _cld_ops = __import__("lib.clouds." + cld_attr_lst["model"] \
                                      + "_cloud_ops", fromlist = \
                                      [cld_attr_lst["model"].capitalize() + "Cmds"])
    
                _cld_ops_class = getattr(_cld_ops, \
                                         cld_attr_lst["model"].capitalize() + "Cmds")

                if "ssh_key_name" in cld_attr_lst["space"] :
                    ssh_filename = cld_attr_lst["space"]["credentials_dir"] + '/' + cld_attr_lst["space"]["ssh_key_name"]
                else :
                    raise Exception("\n   The parameter " + cld_attr_lst["model"].upper() + "_SSH_KEY_NAME is not configured:\n")

                if not os.path.isfile(ssh_filename) :
                    if not os.path.isfile(cld_attr_lst["space"]["ssh_key_name"]) :
                        _cmd = "mkdir -p " + cld_attr_lst["space"]["credentials_dir"] + "; ssh-keygen -q -t rsa -N '' -f " + ssh_filename
                        _proc_man =  ProcessManagement()
                        _status, out, err =_proc_man.run_os_command(_cmd)                        
                        if _status :
                            _fmsg = "Error: "
                            raise Exception("\n   Your " + cld_attr_lst["model"].upper() + "_SSH_KEY_NAME parameter is wrong:\n" + \
                                            "\n   Neither files exists: " + cld_attr_lst["space"]["ssh_key_name"] + " nor " + ssh_filename + \
                                            "\n   Please update your configuration and try again.\n")
                        else :
                            cld_attr_lst["space"]["ssh_key_name"] = ssh_filename 
                else :
                    cld_attr_lst["space"]["ssh_key_name"] = ssh_filename 

                _proc_man =  ProcessManagement(username = cld_attr_lst["time"]["username"], cloud_name = cld_attr_lst["cloud_name"])
                self.start_vpnserver(cld_attr_lst)

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

                if str(cld_attr_lst["vm_defaults"]["use_jumphost"]).lower() != "false" and \
                str(cld_attr_lst["vm_defaults"]["create_jumphost"]).lower() == "false" :

                    _msg = " The attribute \"USE_JUMPHOST\" in Global Object "
                    _msg += "[VM_DEFAULTS] is set to \"True\". "                    
                    _msg += "Will set the attribute \"CREATE_JUMPHOST\" in the" 
                    _msg += " same Global Object ([VM_DEFAULTS]) also to \"True\"."
                    cbdebug(_msg, True)
                    cld_attr_lst["vm_defaults"]["create_jumphost"] = "true"

                if str(cld_attr_lst["vm_defaults"]["use_vpn_ip"]).lower() == "true" and \
                str(cld_attr_lst["vm_defaults"]["userdata"]).lower() == "false" :

                    _msg = " The attribute \"USE_VPN_IP\" in Global Object "
                    _msg += "[VM_DEFAULTS] is set to \"True\". "                    
                    _msg += "Will set the attribute \"USERDATA\" in the" 
                    _msg += " same Global Object ([VM_DEFAULTS]) also to \"True\"."
                    cbdebug(_msg, True)
                    cld_attr_lst["vm_defaults"]["userdata"] = "true"

                _msg = "Attempting to connect to all VMCs described in the cloud "
                _msg += "defaults file, in order to check the access parameters "
                _msg += "and security credentials"
                cbdebug(_msg)

                # Just create an openSSL certificates to be used later (multiple uses)

                if not os.path.exists(cld_attr_lst["space"]["generated_configurations_dir"]) :
                    os.mkdir(cld_attr_lst["space"]["generated_configurations_dir"])

                _ssl_key = cld_attr_lst["space"]["generated_configurations_dir"] + "/cb.key"
                _ssl_csr = cld_attr_lst["space"]["generated_configurations_dir"] + "/cb.csr"
                _ssl_crt = cld_attr_lst["space"]["generated_configurations_dir"] + "/cb.crt"  
                if not os.path.isfile(_ssl_key) :
                    _cmd = 'openssl req -newkey rsa:2048 -nodes -keyout ' 
                    _cmd += _ssl_key + ' -out ' + _ssl_csr 
                    _cmd += ' -subj "/C=US/ST=NewYork/L=NewYork/O=CB/CN=www.example.com" '
                    _cmd += '&& openssl x509 -signkey ' + _ssl_key + ' -in '
                    _cmd += _ssl_csr + ' -req -days 365 -out ' + _ssl_crt
                    _proc_man =  ProcessManagement()
                    _status, out, err =_proc_man.run_os_command(_cmd)

                cld_attr_lst["vm_defaults"]["ssl_cert"] = _ssl_crt
                cld_attr_lst["vm_defaults"]["ssl_key"] = _ssl_key
                cld_attr_lst["vmc_defaults"]["ssl_cert"] = _ssl_crt
                cld_attr_lst["vmc_defaults"]["ssl_key"] = _ssl_key

                if "walkthrough" not in cld_attr_lst :                    
                    cld_attr_lst["walkthrough"] = "false"

                self.create_image_build_map(cld_attr_lst)
                    
                for _vmc_entry in _initial_vmcs :
                    _cld_conn = _cld_ops_class(self.pid, None, None)
                    _x_status, _x_msg = _cld_conn.test_vmc_connection(cld_attr_lst["cloud_name"], \
                                                                      _vmc_entry.split(':')[0], \
                                                                      cld_attr_lst["vmc_defaults"]["access"], \
                                                                      cld_attr_lst["vmc_defaults"]["credentials"], \
                                                                      cld_attr_lst["vmc_defaults"]["key_name"], \
                                                                      cld_attr_lst["vmc_defaults"]["security_groups"], \
                                                                      cld_attr_lst["vm_templates"], \
                                                                      cld_attr_lst["vm_defaults"], \
                                                                      cld_attr_lst["vmc_defaults"])

                    if _x_status or str(cld_attr_lst["vmc_defaults"]["force_walkthrough"]).lower() == "true" :
                        cld_attr_lst["walkthrough"] = "true"
                
                cld_attr_lst["vmc_defaults"]["walkthrough"] = cld_attr_lst["walkthrough"]
                cld_attr_lst["vm_defaults"]["walkthrough"] = cld_attr_lst["walkthrough"]
                cld_attr_lst["ai_defaults"]["walkthrough"] = cld_attr_lst["walkthrough"]
                
                # This needs to be better coded later. Right now, it is just a fix to avoid
                # the problems caused by the fact that git keeps resetting RSA's private key
                # back to 644 (which are too open).
                chmod(cld_attr_lst["space"]["ssh_key_name"], 0o600)
                
                if str(cld_attr_lst["vm_defaults"]["create_jumphost"]).lower() != "false" :

                    if str(cld_attr_lst["vm_defaults"]["jumphost_ip"]).count('.') == 3 :
                        _msg = "The attribute \"CREATE_JUMPHOST\" in the Global Object" 
                        _msg += " VM_DEFAULTS is set to \"True\"."
                        cbdebug(_msg, True)                        

                        _msg = "         Will attempt to connect (ssh) to the host \"" 
                        _msg += str(cld_attr_lst["vm_defaults"]["jumphost_ip"]) + "\""
                        _msg += " to confirm that this host can be used as a \""
                        _msg += "jump box\"..."
                        #cbdebug(_msg, True)
                        print(_msg, end=' ')

                        _jump_box_host_fn = cld_attr_lst["space"]["generated_configurations_dir"] 
                        _jump_box_host_fn += "/" + cld_attr_lst["name"]
                        _jump_box_host_fn += "_jump_box.conf"

                        # Just re-using the already existing ProcessManagement
                        # instance. That is why all ssh parameters are being 
                        # specified here instead of there.

                        _command = "ssh -i " +  cld_attr_lst["space"]["credentials_dir"]
                        _command += '/' + cld_attr_lst["vm_defaults"]["ssh_key_name"] 
                        _command += " -o StrictHostKeyChecking=no"
                        _command += " -o UserKnownHostsFile=/dev/null"
                        _command += " -o BatchMode=yes "                                                  
                        _command += ' ' + cld_attr_lst["vm_defaults"]["jumphost_login"] 
                        _command += '@' + cld_attr_lst["vm_defaults"]["jumphost_ip"]
                        _command += " \"which nc\""

                        _status, _result_stdout, _result_stderr = \
                        _proc_man.retriable_run_os_command(_command, \
                                                           total_attempts = int(cld_attr_lst["vm_defaults"]["update_attempts"]),\
                                                           retry_interval = int(cld_attr_lst["vm_defaults"]["update_frequency"]), \
                                                           raise_exception_on_error = False)

                        if not _status :
                            _jump_box_host_contents = "Host *\n"
                            _jump_box_host_contents += "  ProxyCommand "
                            _jump_box_host_contents += _command.replace('"', '').replace("which",'').replace(" nc", "nc -w 2 %h 22")

                            _jump_box_host_fd = open(_jump_box_host_fn, 'w')

                            _jump_box_host_fd.write(_jump_box_host_contents)
                            _jump_box_host_fd.close()

                            cld_attr_lst["vm_defaults"]["ssh_config_file"] = _jump_box_host_fn

                            print("done\n")
                    else :
                        _msg = "The attribute \"CREATE_JUMPHOST\" in Global Object "
                        _msg += " VM_DEFAULTS is set to \"True\", but the actual "
                        _msg += " IP address of the jump_host VM could not be determined."
                        _msg += " Please try to re-run the tool."
                        cberr(_msg, True)
                        exit(1)                
                
                _all_global_objects = list(cld_attr_lst.keys())
                cld_attr_lst["client_should_refresh"] = str(0.0)

                _remove_from_global_objects = [ "name", "model", "user-defined", \
                                               "dependencies", "cloud_filename", \
                                               "cloud_name", "objectstore", \
                                               "command_originated", "state", \
                                               "tracking", "channel", "sorting", \
                                               "ai_arrived", "ai_departed", \
                                               "ai_failed", "ai_reservations", "walkthrough" ]
    
                for _object in _remove_from_global_objects :
                    if _object in _all_global_objects :
                        _all_global_objects.remove(_object)
    
                cld_attr_lst["all"] = ','.join(_all_global_objects)
                cld_attr_lst["all_vmcs_attached"] = "false"
                
                if "regression" in cld_attr_lst["space"] :
                    cld_attr_lst["regression"] = str(cld_attr_lst["space"]["regression"]).strip().lower()
                else :
                    cld_attr_lst["regression"] = "false"

                cld_attr_lst["description"] = _cld_conn.get_description()
                cld_attr_lst["username"] = cld_attr_lst["time"]["username"]
                cld_attr_lst["start_time"] = str(int(time()))
                cld_attr_lst["client_should_refresh"] = str(0) 
                cld_attr_lst["time"]["hard_reset"] = uni_attr_lst["time"]["hard_reset"] if "hard_reset" in uni_attr_lst["time"] else False
                cld_attr_lst["space"]["tracefile"] = uni_attr_lst["space"]["tracefile"] if "tracefile" in uni_attr_lst["space"] else "none"

                # While setting up the Object Store, check for free ports for the 
                # API, GUI, and Gmetad (Host OS performance data collection)
                # daemons, using their indicated ports as the base port
                cld_attr_lst["mon_defaults"]["collector_host_multicast_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_multicast_port"], protocol = "tcp")
                cld_attr_lst["mon_defaults"]["collector_host_aggregator_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_aggregator_port"], protocol = "tcp")
                cld_attr_lst["mon_defaults"]["collector_host_summarizer_port"] = _proc_man.get_free_port(cld_attr_lst["mon_defaults"]["collector_host_summarizer_port"], protocol = "tcp")
    
                os_func, ms_func, unused, unused = load_store_functions(cld_attr_lst)

                os_func(cld_attr_lst, "initialize", cloud_name = cld_attr_lst["name"])
                ms_func(cld_attr_lst, "initialize")

                _status = 0

                _expid = cld_attr_lst["time"]["experiment_id"]
                _cld_name = cld_attr_lst["name"]
         
            _msg = _smsg + "\nThe experiment identifier is " + _expid + "\n"
            cld_attr_lst["cloud_name"] = _cld_name
                
        except ImportError as msg :
            _status = 8
            _msg = _fmsg + str(msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        except OSError as msg :
            _status = 8
            _msg = _fmsg + str(msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        except AttributeError as msg :
            _status = 8
            _msg = _fmsg + str(msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        except DataOpsException as obj :
            _status = 8
            _msg = _fmsg + str(msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        # Chicken and the egg problem:
        # Can't catch this exception if the import fails
        # inside of the try/catch ... find another solution
        #except _cld_ops_class.CldOpsException, obj :
        #    _status = str(obj.msg)
        #    _msg = _fmsg + str(obj.msg)

        except StoreSetupException as obj :
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        except ProcessManagement.ProcessManagementException as obj :
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        except socket.gaierror as e :
            _status = 24
            _msg = _fmsg + " vmc: " + cld_attr_lst["vmc_defaults"]["access"] + str(e)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
        except Exception as e :
            _status = 23
            _msg = _fmsg + str(e)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
        
        finally :
            if _status :
                cberr(_msg)
            else :                
                cbdebug(_msg)
            return self.package(_status, _msg, cld_attr_lst)
        
    @trace
    def start_vpnserver(self, cld_attr_lst) :
        '''
        TBD
        '''

        if cld_attr_lst["model"].lower() == "sim" :
            cbdebug("No need for a VPN server on simcloud.")
            return
            
        _type = cld_attr_lst["vpn"]["kind"]
        _vpn_server_config = cld_attr_lst["space"]["generated_configurations_dir"] 
        _vpn_server_config += '/' + cld_attr_lst["cloud_name"] + "_server-cb-openvpn.conf"
        _vpn_server_address = cld_attr_lst["vpn"]["server_ip"]
        _vpn_server_port = cld_attr_lst["vpn"]["server_port"]

        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not os.path.isfile(_vpn_server_config) :
                _proc_man =  ProcessManagement()
                script = self.path + "/util/openvpn/make_keys.sh"
                _vpn_network = cld_attr_lst["vpn"]["network"]
                _vpn_netmask = cld_attr_lst["vpn"]["netmask"]
                _cmd = script + ' ' + _vpn_network + ' ' + _vpn_netmask + ' ' 
                _cmd += cld_attr_lst["cloud_name"] + ' ' + _vpn_server_address + ' ' + _vpn_server_port
                cbinfo("Creating \"" + _type + "\" VPN server unified CB configuration: " + _cmd + ", please wait ...", True)
                _status, out, err =_proc_man.run_os_command(_cmd)
    
                if not _status :
                    cbdebug("VPN configuration success: (" + _vpn_network + ' ' + _vpn_netmask + ")", True)
                else :
                    raise Exception("VPN configuration failed: " + out + err)
            else :

                cbinfo("VPN configuration for this cloud already generated: " + _vpn_server_config, True)

            vpn_client_config = cld_attr_lst["space"]["generated_configurations_dir"] 
            vpn_client_config += '/' + cld_attr_lst["cloud_name"] + "_client-cb-openvpn.conf"
            cld_attr_lst["vm_defaults"]["vpn_config_file"] = vpn_client_config

#            if cld_attr_lst["vm_defaults"]["use_vpn_ip"] and not cld_attr_lst["vpn"]["start_server"] :
#                _msg = " The attribute \"USE_VPN_IP\" in Global Object "
#                _msg += "[VM_DEFAULTS] is set to \"True\". Will set the"
#                _msg += "attribute \"START_SERVER\" in the Global Object "
#                _msg += "[VPN] also to \"True\"."
#                cbdebug(_msg, True)
#                cld_attr_lst["vpn"]["start_server"] = True

            if str(cld_attr_lst["vm_defaults"]["use_vpn_ip"]).lower() == "false" :
                _status = 0
                _msg = "VPN is disabled for this cloud."
                return True

            if str(cld_attr_lst["vpn"]["start_server"]).lower() == "false" :

                _msg = "Bypassing the startup of a \"" + _type + "\" VPN server..."

                # Occasionally (on laptops) the VPN ip address of the orchestrator
                # has reset and is no longer the same as what is located in the
                # configuration file. In that case, update the runtime configuration
                # and notify the user.
                client_not_found = True
                try :
                    tmp = Nethashget(cld_attr_lst["vpn"]["management_ip"])
                    tmp.nmap(int(cld_attr_lst["vpn"]["management_port"]), "TCP")
                    tn = telnetlib.Telnet(cld_attr_lst["vpn"]["management_ip"], int(cld_attr_lst["vpn"]["management_port"]), 1)
                    tn.write(b"log all\r\n")
                    tn.write(b"exit\n")
                    lines = []
                    while True :
                        try :
                            lines.append(tn.read_until(b"\n", 1).decode("utf-8"))
                        except Exception as e :
                            break
                    tn.close
                    lines.reverse()
                    for line in lines :
                        if line.count("route " + cld_attr_lst["vpn"]["network"]) :
                            bip = line.split(" ")[10]
                            client_not_found = False
                            if bip != cld_attr_lst["vpn"]["server_bootstrap"] :
                                cbwarn("VPN Bootstrap changed to: " + bip, True)
                                cld_attr_lst["vpn"]["server_bootstrap"] = bip
                            break
                except TypeError as e:
                    for line in traceback.format_exc().splitlines() :
                        cbwarn(line, True)
                except Exception as e: 
                    pass

                if client_not_found :
                    cbdebug("Local VPN client not online. VMs may not be reachable.", True)
                _status = 0
            else :
                _vpn_pid = False
                
                print("Checking for a running VPN daemon.....", end=' ')
                
                _proc_man = ProcessManagement(username = "root")
                _base_cmd = "openvpn --config " + _vpn_server_config
                _cmd = _base_cmd + " --daemon"

                _vpn_pid = _proc_man.get_pid_from_cmdline(_cmd)     

                if not _vpn_pid :
                    
                    _vpn_pid = _proc_man.start_daemon("sudo " + _cmd, \
                                                      protocol = "tcp", \
                                                      conditional = True, \
                                                      port = _vpn_server_port, \
                                                      search_keywords = _vpn_server_config)
                            
                    if len(_vpn_pid) :
                        if _vpn_pid[0].count("pnf") :
                            _x, _p, _username = _vpn_pid[0].split('-') 
                            _msg = "Unable to start VPN service. Port 1194"
                            _msg += " is already taken by process" + _p + "."
                            _status = 8181
        
                            raise ProcessManagement.ProcessManagementException(_status, _msg)
                        else :
                            _p = _vpn_pid[0]
                            _msg = "VPN daemon was successfully started. "
                            _msg += "The process id is " + str(_p) + ".\n"
                            sys.stdout.write(_msg)
                    else :
                        _msg = "\nVPN failed to start. To discover why, please "
                        _msg += "run:\n\n" + _base_cmd + "\n\n ... and report the bug."
                        cberr(_msg, True)
                        _status = 7161
                        raise ProcessManagement.ProcessManagementException(_status, _msg)

                else :
                    _p = _vpn_pid
                    _msg = "A VPN daemon of the kind \"" + _type + "\" "
                    _msg += "on node " + _vpn_server_address + ", TCP "
                    _msg += "port " + str(_vpn_server_port) + " seems to be "
                    _msg += "running.\n"
                    sys.stdout.write(_msg)

            _status = 0
    
        except ProcessManagement.ProcessManagementException as obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to start VPN server: " + _fmsg
                cberr(_msg)         
                exit(_status)       
            else :
                print('')
                cbdebug(_msg)
                return True

    @trace    
    def clddetach(self, cld_attr_list, parameters, command, api = False) :
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
                            if "name" not in _obj_attr_list :
                                continue
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except ProcessManagement.ProcessManagementException as obj :
            _status = str(obj.status)
            _msg = _fmsg + str(obj.msg)

        except Exception as e :
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

                _fault_situations_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                                  "GLOBAL", \
                                                                  False, \
                                                                  "fi_templates", \
                                                                  False)

                if obj_attr_list["situation"] != "auto" and not \
                obj_attr_list["situation"] + "_fault" in _fault_situations_attr_list :
                    _fmsg = "Fault Injection situation \"" + obj_attr_list["situation"]
                    _fmsg += "\" is not defined."
                    _status = 102
                else :
                    _status = 0

                if not _status :
                    _status = 103

                    _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                           "HOST", \
                                                           True, \
                                                           obj_attr_list["name"], \
                                                           False)

                    if obj_attr_list["situation"] == "auto" :
                        obj_attr_list["situation"] = _host_attr_list["fault"]
                        
                    _cmd_fault = _fault_situations_attr_list[obj_attr_list["situation"] + "_fault"]
                    _cmd_repair = _fault_situations_attr_list[obj_attr_list["situation"] + "_repair"]                    
     
                    _proc_man = ProcessManagement(username = _host_attr_list["login"], \
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

                                _cmd = ''
                                for _sub_cmd in _cmd_repair.split(';') :                                    
                                    _cmd += "sudo " + _sub_cmd + "; "
   
                                _msg = "Repairing a fault on host " + obj_attr_list["name"]
                                _msg += " by executing the command \"" + _cmd + "\""
                                _msg += " as user " + _host_attr_list["login"]
                                cbdebug(_msg, True)
    
                                _host_repaired = True
    
                                if ("simulated" in _host_attr_list and \
                                _host_attr_list["simulated"].lower() == "true") or\
                                 len(_cmd) <= 5 :
                                    _status = 0
                                else :
                                    _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)
                                    
                                if not _status :
                                    self.osci.remove_from_list(obj_attr_list["cloud_name"], \
                                                               "HOST", \
                                                               "FAILED_HOSTS", \
                                                               obj_attr_list["name"], \
                                                               True)

                                    self.osci.remove_object_attribute(obj_attr_list["cloud_name"], \
                                                                      "HOST", \
                                                                      _host_attr_list["uuid"], \
                                                                      False, \
                                                                      "fault")                                    
                                    
                            break
    
                    if _target_state.lower() == "fail" and not _host_already_failed :
    
                        _cmd = ''
                        for _sub_cmd in _cmd_fault.split(';') :                                    
                            _cmd += "sudo " + _sub_cmd + "; "
        
                        _msg = "Injecting a fault on host " + obj_attr_list["name"]
                        _msg += " by executing the command \"" + _cmd + "\""
                        cbdebug(_msg, True)
    
                        if ("simulated" in _host_attr_list and \
                            _host_attr_list["simulated"].lower() == "true") or \
                            len(_cmd) <= 5 :
                            _status = 0
                        else :
                            _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)
    
                        if not _status :
                            self.osci.add_to_list(obj_attr_list["cloud_name"], \
                                                  "HOST", "FAILED_HOSTS", \
                                                  obj_attr_list["name"], int(time())) 

                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                              "HOST", \
                                                              _host_attr_list["uuid"], \
                                                              False, \
                                                              "fault", \
                                                              obj_attr_list["situation"])
        
                    if _target_state.lower() == "repair" and \
                    not _host_already_failed and not _host_repaired :
                        _msg = "Host \"" + obj_attr_list["name"] + "\" is "
                        _msg += "not at the \"failed\" state. No need for repair."
                        cbdebug(_msg, True)
                        _host_already_failed = True                            
                        _status = 0
        
                    _result = obj_attr_list

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
                    self.set_cloud_operations_instance(obj_attr_list["model"])       
                    _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]
    
                    _status, _fmsg = _cld_conn.vmccleanup(obj_attr_list)
                    _result = obj_attr_list

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
                _msg += "successfully cleaned up on this experiment." 
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

            obj_attr_list["walkthrough"] = _vmc_defaults["walkthrough"]

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
                                
                _obj_attr_list["walkthrough"] = _vmc_defaults["walkthrough"]

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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally:
            
            if _status :
                _msg = "Failure while attaching all VMCs to this "
                _msg += "experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "\nAll VMCs successfully attached to this experiment." + self.walkthrough_messages("VMCALL", "attach", obj_attr_list)
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

        except IndexError as msg :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 40
            _fmsg = str(msg)

        except self.ObjectOperationException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
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
        '''
        TBD
        '''

        _status = 100
        _pool_selected = False
        _fmsg = "An error has occurred, but no error message was captured"
        _vm_location = obj_attr_list["pool"]
        _cn = obj_attr_list["cloud_name"]
        _vmc_lock = False
        _colocate_lock = False
        
        del obj_attr_list["pool"]

        try :
            _vm_id = obj_attr_list["name"] + " (" + obj_attr_list["uuid"] + ")"
            if obj_attr_list["ai_name"].lower() != "none" :
                _vm_id += ", part of " + obj_attr_list["ai_name"]
                _vm_id += " (" + obj_attr_list["ai"] + ")"

            obj_attr_list["log_string"] = _vm_id
            
            _msg = "Starting the attachment of " + _vm_id + "..."                                       
            cbdebug(_msg)

            _vmc_pools = list(self.osci.get_list(_cn, "GLOBAL", "vmc_pools"))
            _hosts = list(self.osci.get_list(_cn, "GLOBAL", "host_names"))
            
            '''
            Blacklists are for Anti-Colocation. Please don't break them. =) 
            FT depends on anti-colocation. Others might also in the future.
            '''
            if "vmc_pool_blacklist" in list(obj_attr_list.keys()) :
                _blacklist = obj_attr_list["vmc_pool_blacklist"].split(",")
                for _bad_pool in _blacklist :
                    for _idx in range(0, len(_vmc_pools)) :
                        if _bad_pool.upper() == _vmc_pools[_idx] :
                            del _vmc_pools[_idx]
                            break

            elif "host_name_blacklist" in list(obj_attr_list.keys()) :
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
                for _key in list(obj_attr_list.keys()) :
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

                    # We want round-robin support to be as deterministic as possible
                    # We want to iterate through the VMC lists by name so that they
                    # are always visited in the same order, so do a basic lexicographical sort.
                    if len(_vmc_uuid_list) > 1 :
                        _vmc_uuid_names = {}
                        for _vitem in _vmc_uuid_list :
                            _vmc_uuid_names[_vitem.split("|")[1]] = _vitem

                        _vitem_names = list(_vmc_uuid_names.keys())
                        _vitem_names.sort(key=natural_keys)
                        _vmc_uuid_list = []

                        for _vitem in _vitem_names :
                            _vmc_uuid_list.append(_vmc_uuid_names[_vitem])

                        cbdebug("Naturally sorted VMC uuid list by name: " + str(_vmc_uuid_list))
    
                    _vmc_defaults = self.osci.get_object(_cn, "GLOBAL", False, "vmc_defaults", False)
                    if str(_vmc_defaults["placement_method"]).lower().strip().count("roundrobin") : # use round-robin
                        # Intra-Pool Round-robin support.

                        if obj_attr_list["ai_name"].lower() != "none" :
                            # Force serializing of the placement decision (but not the attachment)
                            # so that we can deterministically round-robin VMs to the same places
                            # during baseline tests.
                            while True :
                                _vmc_lock = self.osci.acquire_lock(_cn, "VMC", "vmc_placement", "vmc_placement", 1)
                                assert(_vmc_lock)
                                cbdebug("Waiting: " + str(obj_attr_list["placement_order"]) + " for AI " + str(obj_attr_list["ai"]))
                                placement_leader = self.osci.pending_object_get(_cn, "AI", obj_attr_list["ai"], "placement_leader", failcheck = False)

                                if isinstance(placement_leader, bool) and not placement_leader :
                                    cbdebug("Initializing placement leader: 0")
                                    self.osci.pending_object_set(_cn, "AI", obj_attr_list["ai"], "placement_leader", 0)
                                    placement_leader = 0
                                else :
                                    cbdebug("Got leader: " + str(placement_leader))

                                if int(placement_leader) == int(obj_attr_list["placement_order"]) :
                                    cbdebug("It's my turn! " + obj_attr_list["name"])
                                    self.osci.pending_object_set(_cn, "AI", obj_attr_list["ai"], "placement_leader", int(placement_leader) + 1)
                                    break
                                else :
                                    cbdebug("Placement leader: " + str(placement_leader))

                                self.osci.release_lock(_cn, "VMC", "vmc_placement", _vmc_lock)
                                sleep(1)
                        else :
                            _vmc_lock = self.osci.acquire_lock(_cn, "VMC", "vmc_placement", "vmc_placement", 1)

                        assert(_vmc_lock)

                        # First, let's make it a counter and then populate this list based on the highest counter.

                        _highest_vmcount = 0
                        _highest_vmcs = []
                        for _vmc_uuid_entry in _vmc_uuid_list :
                            _vmc_attr_list = self.osci.get_object(_cn, "VMC", False, _vmc_uuid_entry.split('|')[0], False)

                            if "scheduled_vms" not in _vmc_attr_list :
                                self.osci.update_object_attribute(_cn, "VMC", _vmc_uuid_entry.split('|')[0], False, "scheduled_vms", 0)
                                continue

                            _vmcount = int(_vmc_attr_list["scheduled_vms"])

                            if len(_highest_vmcs) == 0 or _vmcount >= _highest_vmcount :
                                _highest_vmcount = _vmcount
                                _highest_vmcs.append(_vmc_uuid_entry)
                            else :
                                cbdebug("Skipping VMC " + _vmc_uuid_entry + " as candidate, current count: " + str(_vmcount))

                        # Remove the VMCs with the highest vmcount from the candidate list
                        _highest_vmcs.reverse()
                        for _highest_vmc in _highest_vmcs :
                            if len(_vmc_uuid_list) > 1 :
                                for _vmc_uuid_entry_idx in range(0, len(_vmc_uuid_list)) :
                                    _vmc_uuid_entry = _vmc_uuid_list[_vmc_uuid_entry_idx]
                                    if _vmc_uuid_entry == _highest_vmc :
                                        cbdebug("Removing from candidate list: " + _highest_vmc)
                                        del _vmc_uuid_list[_vmc_uuid_entry_idx]
                                        break
                        cbdebug("Scheduling for VM " + obj_attr_list["name"] + " excluding highest VM count " + str(_highest_vmcount) + " VMC " + str(_highest_vmcs))
                    assert(len(_vmc_uuid_list))

                    if str(_vmc_defaults["placement_method"]).lower().strip().count("roundrobin") :
                        obj_attr_list["vmc"] = _vmc_uuid_list[0].split('|')[0]
                        cbdebug("Round-robin selected: " + str(_vmc_uuid_list[0]))
                    else :
                        obj_attr_list["vmc"] = choice(_vmc_uuid_list).split('|')[0]

                    if str(_vmc_defaults["placement_method"]).lower().strip().count("colocate") :
                        _colocate_lock = self.osci.acquire_lock(_cn, "VMC", "vmc_colocate", "vmc_placement", 1)
                        assert(_colocate_lock)

                        first_vmc = self.osci.pending_object_get(obj_attr_list["cloud_name"], \
                             "AI", obj_attr_list["ai"], "first_vmc", failcheck = False)

                        if first_vmc :
                            obj_attr_list["vmc"] = first_vmc
                        else :
                            first_vmc = obj_attr_list["vmc"]
                            self.osci.pending_object_set(obj_attr_list["cloud_name"], \
                                 "AI", obj_attr_list["ai"], "first_vmc", first_vmc )

                        cbdebug("VM " + obj_attr_list["name"] + " will share VMC: " + first_vmc)
                            
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

            if "prov_netname" not in obj_attr_list :
                obj_attr_list["prov_netname"] = obj_attr_list["netname"]

            if "run_netname" not in obj_attr_list :
                obj_attr_list["run_netname"] = obj_attr_list["netname"]

            if not _status :
                if "qemu_debug_port_base" in obj_attr_list :
                    _status, _fmsg = self.auto_allocate_port("qemu_debug", obj_attr_list, "VMC", obj_attr_list["vmc"], obj_attr_list["vmc_cloud_ip"])

            if obj_attr_list["nest_containers_enabled"].strip().lower() == "true" :
                # Once the base image boots up (the generic one the user has configured to host
                # a nested container), we pull the actual container's base image from the [CONTAINER_TEMPLATES]
                # section. Thus, the user should define a new section, one entry for each role that was originally
                # defined in the [VM_TEMPLATES] section. This allows the user to seemlessly toggle between
                # nested containers and regular VMs using their existing snapshots.
                _container_templates = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                 "GLOBAL", \
                                                 False, \
                                                 "container_templates", False)


                if obj_attr_list["role"] not in _container_templates :
                    _fmsg = "To use nested containers, you need to define a section named [CONTAINER_TEMPLATES] which instructs "
                    _fmsg += "CloudBench which container images to use using the role \"" + obj_attr_list["role"] + "\". "
                    _fmsg += "See the templates for an example and try again."
                    _status = 5335
                    raise CldOpsException(_fmsg, _status)

                obj_attr_list["container_role"] = str2dic(_container_templates[obj_attr_list["role"]])["imageid1"]

                _vm_templates = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                     "GLOBAL", \
                                                     False, \
                                                     "vm_templates", False)
                if "nest_containers_base_image" not in _vm_templates :
                    _fmsg = "To use nested containers, you need to define NEST_CONTAINERS_BASE_IMAGE = xxxx in the [VM_TEMPLATES] section of your configuration files. This tells CloudBench which base image to use before pulling a container within the instance. See the templates for an example and try again."
                    _status = 5334
                    raise CldOpsException(_fmsg, _status)

                replacement = str2dic(_vm_templates["nest_containers_base_image"])

                if replacement["imageid1"] != obj_attr_list["imageid1"] :
                    # We want to make the use of nested containers transparent.
                    # So, we will not require that the user change their [VM_TEMPLATES] definitions.
                    # Instead, if they have enabled nested containers, we will dynamically override
                    # the imageid they originall provided with the one they have specified
                    # using the NEST_CONTAINERS_BASE_IMAGE key. We then overrite all VM base image roles
                    # used at VM attachment time with this image.

                    old_string = str2dic(_vm_templates[obj_attr_list["role"]])
                    old_string["imageid1"] = replacement["imageid1"]
                    obj_attr_list["imageid1"] = old_string["imageid1"]
                    if "cloudinit_packages" in replacement :
                        old_string["cloudinit_packages"] = replacement["cloudinit_packages"]
                        obj_attr_list["cloudinit_packages"] = replacement["cloudinit_packages"]

                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "GLOBAL", "vm_templates", False, obj_attr_list["role"], dic2str(old_string))

            obj_attr_list["imageid1"] = obj_attr_list["image_prefix"].strip() + obj_attr_list["imageid1"] + obj_attr_list["image_suffix"].strip()

            self.admission_control("VM", obj_attr_list, "schedule")

            _status = 0
                
        except KeyError as msg :
            _status = 40
            _fmsg = "Unknown VM role: " + str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = 40
            _fmsg = str(obj.msg)

        except DataOpsException as obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        finally :
            if _vmc_lock :
                self.osci.release_lock(_cn, "VMC", "vmc_placement", _vmc_lock)
            if _colocate_lock :
                self.osci.release_lock(_cn, "VMC", "vmc_colocate", _colocate_lock)
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


            _ai_id = obj_attr_list["name"] + " (" + obj_attr_list["uuid"] + ")"                
            if obj_attr_list["aidrs_name"].lower() != "none" :
                _ai_id += ", submitted by " + obj_attr_list["aidrs_name"]
                _ai_id += " (" + obj_attr_list["aidrs"] + ")"

            obj_attr_list["log_string"] = _ai_id

            _msg = "Starting the attachment of " + _ai_id + "..."                                       
            cbdebug(_msg)   

            _vmc_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC")
            if not _vmc_list :
                _msg = "No VMC attached to this experiment. Please "
                _msg += "attach at least one VMC, or the VM creations triggered "
                _msg += "by this AI attachment operation will fail."
                raise self.osci.ObjectStoreMgdConnException(_msg, _status)
                                        
            _ai_templates = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                 "ai_templates", False)
            _ai_template_attr_list = {}
            _app_type = obj_attr_list["type"]
            for _attrib, _val in _ai_templates.items() :
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
            # only "driver_hadoop_setup1"
            _x = len(_app_type) + 1

            for _key, _value in _ai_template_attr_list.items() :
                if _key.count(_app_type) :
                    if _key[_x:] in obj_attr_list : 
                        if obj_attr_list[_key[_x:]] == "default" :
                            obj_attr_list[_key[_x:]] = _value
                    else :
                        obj_attr_list[_key[_x:]] = _value

            if "description" in obj_attr_list :
                del(obj_attr_list["description"])

            if "lifetime" in obj_attr_list and obj_attr_list["lifetime"] != "none" :
                _value_generation = ValueGeneration(self.pid)
                obj_attr_list["lifetime"] = int(_value_generation.get_value(obj_attr_list["lifetime"]))

            if not "base_type" in obj_attr_list :
                obj_attr_list["base_type"] = obj_attr_list["type"]

            _fmsg = "About to create VM list for AI"
            self.create_vm_list_for_ai(obj_attr_list)

            _fmsg = "About to execute speculative admission control"
            self.speculative_admission_control(obj_attr_list)

            _post_speculative_admission_control = True

            self.osci.pending_object_set(obj_attr_list["cloud_name"], \
                 "AI", obj_attr_list["uuid"], "status", "Creating VMs: Switch tabs for tracking..." )

            if obj_attr_list["vm_creation"].lower() == "explicit" : 
                _fmsg = "About to create VMs for AI"                
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

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = 41
            _fmsg = str(obj.msg)

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ValueGeneration.ValueGenerationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except DataOpsException as obj :
            _status = 43
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
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

            _aidrs_id = obj_attr_list["name"] + " (" + obj_attr_list["uuid"] + ")"                
            obj_attr_list["log_string"] = _aidrs_id
            
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
            
                for _key, _value in _aidrs_templates.items() :
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

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
            
                for _key, _value in _vmcrs_templates.items() :
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

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
            
                for _key, _value in _firs_templates.items() :
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

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = 40
            _fmsg = str(obj.msg)

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
        _post_attach = False
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
                        _staging_parameters += " nosync"
                                              
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
                        _staging_parameters += " nosync"
                                                      
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

                    for pkey in list(obj_attr_list.keys()) :
                        self.osci.pending_object_set(_cloud_name, _obj_type, \
                            obj_attr_list["uuid"], pkey, obj_attr_list[pkey])

                    self.osci.pending_object_set(_cloud_name, _obj_type, \
                        obj_attr_list["uuid"], "status", "Initializing...")
                    
                    _created_pending = True

                    self.set_cloud_operations_instance(obj_attr_list["model"])            
                    _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]
    
                    if _obj_type == "VMC" :
                        self.pre_attach_vmc(obj_attr_list)

                    elif _obj_type == "VM" :
                        self.pre_attach_vm(obj_attr_list)
    
                    elif _obj_type == "AI" :
                        _status, _fmsg = _cld_conn.aidefine(obj_attr_list, "provision_originated")
                        self.pre_attach_ai(obj_attr_list)

                    elif _obj_type == "AIDRS" :
                        self.pre_attach_aidrs(obj_attr_list)
                        
                    elif _obj_type == "VMCRS" :
                        self.pre_attach_vmcrs(obj_attr_list)

                    elif _obj_type == "FIRS" :
                        self.pre_attach_firs(obj_attr_list)
    
                    else :
                        _msg = "Unknown object: " + _obj_type
                        raise self.ObjectOperationException(_msg, 28)
                    
                    _pre_attach = True
                    _admission_control = self.admission_control(_obj_type, \
                                                            obj_attr_list, \
                                                            "attach")
    
                    if _obj_type == "VMC" :
                        _status, _fmsg = _cld_conn.vmcregister(obj_attr_list)
                        if "initial_hosts" in obj_attr_list :
                            if not isinstance(obj_attr_list, str) :
                                obj_attr_list["initial_hosts"] = ','.join(obj_attr_list["initial_hosts"])

                        _vmcregister = True
    
                    elif _obj_type == "VM" :
                        self.osci.pending_object_set(_cloud_name, _obj_type, \
                                            obj_attr_list["uuid"], "status", "Sending create request to cloud ...")
                        _status, _fmsg = _cld_conn.vmcreate(obj_attr_list)
                        _vmcreate = True

                    elif _obj_type == "AI" :
                        _status, _fmsg = _cld_conn.aidefine(obj_attr_list, "all_vms_booted")
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

                        if "userdata" in obj_attr_list :
                            obj_attr_list["userdata"] = "/var/lib/cloud/" + obj_attr_list["cloud_vm_uuid"] + "/user-data.txt"

                        if "host_list" in obj_attr_list :
                            _host_list_attrs = copy.deepcopy(obj_attr_list["host_list"])
                            del obj_attr_list["host_list"]
                        else :
                            _host_list_attrs = {}

                        for _key,_value in obj_attr_list.items() :
                            if not isinstance(_value, str) and not isinstance(_value, int) and not isinstance(_value, float):
                                print(_key + " : " + str(_value) + " ("  + str(type(_value)) + ")")

                        self.osci.create_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                obj_attr_list, False, True)

                        _created_object = True

                        if _obj_type == "VMC" :
                            self.post_attach_vmc(obj_attr_list, _host_list_attrs)
    
                        elif _obj_type == "VM" :

                            _max_recreate_tries = int(obj_attr_list["recreate_attempts"])
                            _finished_object = False

                            while not _finished_object and _max_recreate_tries > 0 :
                                _status, _msg = self.post_attach_vm(obj_attr_list, _staging)
                                self.pending_decide_abortion(obj_attr_list, "VM", "instance creation")
                                if not _status :
                                    break

                                self.osci.pending_object_set(_cloud_name, _obj_type, \
                                                    obj_attr_list["uuid"], "status", "Recreating ...")

                                cbdebug("Recreating VM " + obj_attr_list["name"] + "...", True)
                                self.osci.destroy_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                         obj_attr_list, False)
                                _status, _fmsg = _cld_conn.vmdestroy_repeat(obj_attr_list)
                                _created_object = False
                                _status, _fmsg = _cld_conn.vmcreate(obj_attr_list)
                                self.osci.create_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                            obj_attr_list, False, True)
                                _created_object = True
                                _max_recreate_tries -= 1
                                obj_attr_list["recreate_attempts_left"] = _max_recreate_tries
                                cbdebug("Attempts left #" + str(_max_recreate_tries))

                            self.pending_decide_abortion(obj_attr_list, "VM", "instance creation")
                            
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

                        _post_attach = True

        except self.ObjectOperationException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 23
            _fmsg = str(e)

        finally:
            unique_state_key = "-attach-" + str(time())
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
                        _cld_conn.vmdestroy_repeat(obj_attr_list)
                        if "qemu_debug_port_base" in obj_attr_list :
                            self.auto_free_port("qemu_debug", obj_attr_list, "VMC", obj_attr_list["vmc"], obj_attr_list["vmc_cloud_ip"])

                    if _pre_attach and _obj_type == "VM" :
                        self.admission_control(_obj_type, obj_attr_list, "deschedule")
                        
                    if _aidefine :
                        _cld_conn.aiundefine(obj_attr_list,"deprovision_finished")

                    if _created_object :
                        self.osci.destroy_object(_cloud_name, _obj_type, obj_attr_list["uuid"], \
                                                obj_attr_list, False)

                    if not _post_attach :
                        self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                       _obj_type, obj_attr_list, "attach")
                    
                    obj_attr_list["tracking"] = str(_fmsg)
                    if "uuid" in obj_attr_list and "cloud_name" in obj_attr_list :
                        self.osci.create_object(_cloud_name, "FAILEDTRACKING" + _obj_type, obj_attr_list["uuid"] + unique_state_key, \
                                                obj_attr_list, False, True, 3600)
                    _xmsg = "Done "
                    cberr(_xmsg)

            else :

                _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully "
                _msg += "attached to this experiment."                

                if "prepare_" + str(_staging) + "_complete" in obj_attr_list :
                    _msg += _staging + "d."
                    obj_attr_list["tracking"] = _staging + ": success." 
                else :
                    _result = copy.deepcopy(obj_attr_list)
                    self.osci.update_counter(_cloud_name, _obj_type, "ARRIVED", "increment")

                    if not "submitter" in obj_attr_list :
                        if _obj_type == "VM" :
                            if obj_attr_list["prov_cloud_ip"] == obj_attr_list["run_cloud_ip"] :
                                _ip = "IP address " + obj_attr_list["cloud_ip"] + " (port " + str(obj_attr_list["prov_cloud_port"]) + ")"
                            else :
                                _ip = "IP addresses " + obj_attr_list["prov_cloud_ip"] + " (port " + str(obj_attr_list["prov_cloud_port"]) + ")"+ " and " + obj_attr_list["run_cloud_ip"] 
                        else :
                            _ip = "IP address " + obj_attr_list["cloud_ip"]

                        if _ip.count('-') :
                            _ip = _ip.split('-')[0]
                        
                        _msg += " It is ssh-accessible at the " + _ip
                        _msg += " (hostname is " + obj_attr_list["cloud_hostname"] + ")."
                                                
                    obj_attr_list["tracking"] = "Attach: success." 

                self.osci.create_object(_cloud_name, \
                                        "FINISHEDTRACKING" + _obj_type, \
                                        obj_attr_list["uuid"] + unique_state_key, \
                                        obj_attr_list, \
                                        False, \
                                        True, \
                                        3600)

                _msg += self.walkthrough_messages(_obj_type, "attach", obj_attr_list)
                cbdebug(_msg)

            if _created_pending :
                self.osci.pending_object_remove(_cloud_name, _obj_type, obj_attr_list["uuid"], "status")
                self.osci.pending_object_remove(_cloud_name, _obj_type, obj_attr_list["uuid"], "abort")                
                self.osci.remove_from_list(_cloud_name, _obj_type, "PENDING",obj_attr_list["uuid"] + "|" + obj_attr_list["name"], True)

            return self.package(_status, _msg, _result)

    @trace
    def post_attach_vmc(self, obj_attr_list, host_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        try :
            if "hosts" in obj_attr_list and len(obj_attr_list["hosts"]) and obj_attr_list["discover_hosts"].lower() == "true":

                for _host_uuid in obj_attr_list["hosts"].split(',') :
        
                    self.osci.create_object(obj_attr_list["cloud_name"], "HOST", _host_uuid, \
                                            host_attr_list[_host_uuid], False, True)

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

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        except self.osci.ObjectStoreMgdConnException as obj :
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
            _msg = "VM creation previously failed (no Cloud-assigned IP address). Will not send files"
            _status = 452
            raise self.ObjectOperationException(_msg, _status)
        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _retry_interval = int(obj_attr_list["update_frequency"])

        if str(obj_attr_list["use_jumphost"]).lower() == "true" :
            if "ssh_config_file" in obj_attr_list :
                _config_file = obj_attr_list["ssh_config_file"]
            else :
                _config_file = None
        else :
            _config_file = None            
            
        _proc_man = ProcessManagement(username = obj_attr_list["login"], \
                                      cloud_name = obj_attr_list["cloud_name"], \
                                      priv_key = obj_attr_list["identity"], \
                                      config_file = _config_file,
                                      connection_timeout = 120)

        try :
            
            if "nosync" not in obj_attr_list or obj_attr_list["nosync"].lower() == "false" :
                if threading.current_thread().abort :
                    _msg = "VM creation aborted during transfer file step..."
                    _status = 12345
                    raise self.ObjectOperationException(_msg, _status)

            _abort, _fmsg, _remaining_time = self.pending_decide_abortion(obj_attr_list, "VM", "checking SSH accessibility")

            if _remaining_time != 100000 :
                _actual_tries = _remaining_time/int(obj_attr_list["update_frequency"])
            else :
                _actual_tries = int(obj_attr_list["update_attempts"])

            _ssh_cmd_log = "ssh -p " + str(obj_attr_list["prov_cloud_port"]) + " -i " + obj_attr_list["identity"]
            _ssh_cmd_log += ' ' + obj_attr_list["login"] + "@" + obj_attr_list["prov_cloud_ip"]
            
            if obj_attr_list["role"] == "check" :
                _cmd_list = [ "/bin/true", "sudo /bin/true" ]
            else :
                _cmd_list = [ "/bin/true" ]

            for _cmd in _cmd_list :
                _msg = "Checking ssh accessibility on " + obj_attr_list["log_string"]
                _msg += ": " + _ssh_cmd_log + " \"" + _cmd + "\"..."
                cbdebug(_msg, selectively_print_message("check_ssh", obj_attr_list))
                _proc_man.retriable_run_os_command(_cmd, \
                                                   obj_attr_list["uuid"], \
                                                   _actual_tries, \
                                                   _retry_interval, \
                                                   obj_attr_list["check_ssh"], \
                                                   obj_attr_list["debug_remote_commands"], \
                                                   True,
                                                   tell_me_if_stderr_contains = False, \
                                                   port = obj_attr_list["prov_cloud_port"], \
                                                   osci = self.osci, \
                                                   get_hostname_using_key = "prov_cloud_ip" \
                                                   )

            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                                              False, "last_known_state", \
                                              "checked SSH accessibility")
            obj_attr_list["last_known_state"] = "checked SSH accessibility"
            
            _msg = "Checked ssh accessibility on " + obj_attr_list["log_string"]
            cbdebug(_msg)
            
            _msg = "Bootstrapping " + obj_attr_list["log_string"]  + ": creating file"
            _msg += " cb_os_parameters.txt in \"" + obj_attr_list["login"] 
            _msg += "\" user's home dir on IP address " 
            _msg += obj_attr_list["prov_cloud_ip"] + "..."

            if str(obj_attr_list["cloud_init_bootstrap"]).lower() == "true" :
                _msg += " done by cloud-init!"
                cbdebug(_msg, selectively_print_message("transfer_files", obj_attr_list))
            else :
                cbdebug(_msg, selectively_print_message("transfer_files", obj_attr_list))

                _abort, _fmsg, _remaining_time = self.pending_decide_abortion(obj_attr_list, "VM", "boostrapping")
    
                if _remaining_time != 100000 :
                    _actual_tries = _remaining_time/int(obj_attr_list["update_frequency"])
                else :
                    _actual_tries = int(obj_attr_list["update_attempts"])                
                
                _bcmd = get_bootstrap_command(obj_attr_list, cloud_init = False)
                
                _msg = "BOOTSTRAP: " + _bcmd
                cbdebug(_msg)

                _proc_man.retriable_run_os_command(_bcmd, \
                                                   obj_attr_list["uuid"], \
                                                   _actual_tries, \
                                                   _retry_interval, \
                                                   obj_attr_list["transfer_files"], \
                                                   obj_attr_list["debug_remote_commands"], \
                                                   True, \
                                                   tell_me_if_stderr_contains = "Connection reset by peer", \
                                                   port = obj_attr_list["prov_cloud_port"], \
                                                   osci = self.osci, \
                                                   get_hostname_using_key = "prov_cloud_ip")

            _msg = "Bootstrapped " + obj_attr_list["log_string"]
            cbdebug(_msg)

            _msg = "Sending a copy of the code tree to " +  obj_attr_list["log_string"]  + ", on IP "
            _msg += "address " + obj_attr_list["prov_cloud_ip"] + "..."
            
            if str(obj_attr_list["cloud_init_rsync"]).lower() == "true" :
                _msg += " done by cloud-init!"
                cbdebug(_msg, selectively_print_message("transfer_files", obj_attr_list))

            else :
                cbdebug(_msg, selectively_print_message("transfer_files", obj_attr_list))

                _abort, _fmsg, _remaining_time = self.pending_decide_abortion(obj_attr_list, "VM", "transfer files")
    
                if _remaining_time != 100000 :
                    _actual_tries = _remaining_time/int(obj_attr_list["update_frequency"])
                else :
                    _actual_tries = int(obj_attr_list["update_attempts"])    
                
                _rcmd = "rsync -e \"" + _proc_man.rsync_conn + "\""
                _rcmd += " --exclude-from "
                _rcmd += "'" +  obj_attr_list["exclude_list"] + "' -az "
                _rcmd += "--delete --no-o --no-g --inplace --rsync-path='sudo rsync' -O " 
                _rcmd += obj_attr_list["base_dir"] + "/* " 
                _rcmd += obj_attr_list["prov_cloud_ip"] + ":~/" 
                _rcmd += obj_attr_list["remote_dir_name"] + '/'
    
                _msg = "RSYNC: " + _rcmd
                cbdebug(_msg)

                _proc_man.retriable_run_os_command(_rcmd, \
                                                   "127.0.0.1", \
                                                   _actual_tries, \
                                                   _retry_interval, \
                                                   obj_attr_list["transfer_files"], \
                                                   obj_attr_list["debug_remote_commands"], \
                                                   True, \
                                                   tell_me_if_stderr_contains = "Connection reset by peer", \
                                                   port = obj_attr_list["prov_cloud_port"])                

                self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                                                  False, "last_known_state", \
                                                  "sent copy of code tree")
                obj_attr_list["last_known_state"] = "sent copy of code tree"

            _time_mark_ift = int(time())

            if "time_mark_aux" in obj_attr_list :
                _delay = _time_mark_ift - obj_attr_list["time_mark_aux"]
            else :
                _delay = -1

            self.osci.pending_object_set(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], "status", "Files transferred...")
            obj_attr_list["mgt_005_file_transfer"] = _delay
            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                                              False, "mgt_005_file_transfer", \
                                              _delay)
            obj_attr_list["time_mark_aux"] = _time_mark_ift
             
            _msg = "Sent a copy of the code tree to " +  obj_attr_list["log_string"]  + ", on IP "
            _msg += "address " + obj_attr_list["prov_cloud_ip"] + "..."
            cbdebug(_msg)
            
            if selectively_print_message("run_generic_scripts", obj_attr_list) \
            and "ai" in obj_attr_list and obj_attr_list["ai"] == "none" :

                if not access(obj_attr_list["identity"], F_OK) :
                    obj_attr_list["identity"] = obj_attr_list["identity"].replace(obj_attr_list["username"], \
                                                                                  obj_attr_list["login"])


                if str(obj_attr_list["prepare_workload_names"]).lower() != "none" \
                and str(obj_attr_list["prepare_image_name"]).lower() != "none" :
                    _msg = "Performing workload (" + obj_attr_list["prepare_workload_names"] 
                    _msg += ") image build operation on " + obj_attr_list["log_string"]
                    _msg += ", on IP address "+ obj_attr_list["prov_cloud_ip"] + "..."     
                else :
                    _msg = "Performing generic instance post_boot configuration on " + obj_attr_list["log_string"] 
                    _msg += ", on IP address "+ obj_attr_list["prov_cloud_ip"] + "..."     
                cbdebug(_msg, selectively_print_message("run_generic_scripts", obj_attr_list))

                _cmd = "~/" + obj_attr_list["remote_dir_name"] + "/scripts/common/cb_post_boot.sh"

                _status, _result_stdout, _result_stderr = \
                        _proc_man.retriable_run_os_command(obj_attr_list["generic_post_boot_command"], obj_attr_list["uuid"], \
                                                           really_execute = obj_attr_list["run_generic_scripts"], \
                                                           debug_cmd = obj_attr_list["debug_remote_commands"], \
                                                           total_attempts = int(obj_attr_list["update_attempts"]),\
                                                           retry_interval = int(obj_attr_list["update_frequency"]), \
                                                           raise_exception_on_error = True, \
                                                           tell_me_if_stderr_contains = "Connection reset by peer", \
                                                           port = obj_attr_list["prov_cloud_port"], \
                                                           osci = self.osci, \
                                                           get_hostname_using_key = "prov_cloud_ip"  \
                                                           )                   

                _time_mark_ipbc = int(time())
                if "time_mark_aux" in obj_attr_list :
                    _delay = _time_mark_ipbc - obj_attr_list["time_mark_aux"]
                else :
                    _delay = -1

                if _status :
                    _fmsg = "Failure while executing generic VM "
                    _fmsg += "post_boot configuration on "
                    _fmsg += obj_attr_list["name"] + '.\n'
                else :

                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                              False, "mgt_006_instance_preparation", \
                              _delay)

                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", obj_attr_list["uuid"], \
                                                      False, "last_known_state", \
                                                      "generic post-boot script executed")                    
                    obj_attr_list["last_known_state"] = "generic post-boot script executed"

                if str(obj_attr_list["prepare_workload_names"]).lower() != "none" \
                and str(obj_attr_list["prepare_image_name"]).lower() != "none" :
                    _msg = "Performed workload image build operation on " + obj_attr_list["log_string"]
                    _msg += ", on IP address "+ obj_attr_list["prov_cloud_ip"] + "."
                    _msg += "You can now capture this image with \"vmcapture youngest "
                    
                    if obj_attr_list["prepare_image_name"][0:len(obj_attr_list["image_prefix"])] != obj_attr_list["image_prefix"] :
                        obj_attr_list["prepare_image_name"] = obj_attr_list["image_prefix"].strip() + obj_attr_list["prepare_image_name"]
                                        
                    if obj_attr_list["prepare_image_name"][-len(obj_attr_list["image_suffix"]):] != obj_attr_list["image_suffix"] :
                        obj_attr_list["prepare_image_name"] += obj_attr_list["image_suffix"].strip()                   
                    
                    _msg += obj_attr_list["prepare_image_name"] + "\" on the CLI\n"
                    cbdebug(_msg)
                    print('\n' + _msg)

                else :
                    _msg = "Performed generic VM post_boot configuration on " + obj_attr_list["log_string"] 
                    _msg += ", on IP address "+ obj_attr_list["prov_cloud_ip"] + "..."     
                    cbdebug(_msg)
                     
            else :                
                _status = 0

            if "ai" in obj_attr_list and obj_attr_list["ai"] == "none" :
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ProcessManagement.ProcessManagementException as obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)
            _status = 23
            _fmsg = str(e)

        finally :

            if _status :
                if _status == "90001" :
                    _msg = "VM creation succeeded, but authentication has failed,"
                    _msg += " likely due to cloud-init or similar bootstrapping"
                    _msg += " not completing correctly. Will re-create the VM and try again."
                    cbdebug(_msg, True)
                    return _status, _msg

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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
            _cmd = "screen -d -m bash -c '" + self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=aidr-submit"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += "'"
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
            _cmd = "screen -d -m bash -c '" + self.path + "/cbact"
            _cmd += " --procid=" + self.pid
            _cmd += " --osp=" + dic2str(self.osci.oscp())
            _cmd += " --uuid=" + obj_attr_list["uuid"] 
            _cmd += " --operation=aidr-remove"
            _cmd += " --cn=" + obj_attr_list["cloud_name"]
            _cmd += "'"
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

        except Exception as e :
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

        except Exception as e :
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

        except Exception as e :
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

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            
        except Exception as e :
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
                if self.osci.object_exists(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], False) :
                    _status = 46
                    _fmsg = "This VM is part of the AI " + obj_attr_list["ai"] + '.'
                    _fmsg += "Please detach this AI instead."
                else :
                    _status = 0
                
        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            
        except Exception as e :
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

        except Exception as e :
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

        except Exception as e :
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

        except Exception as e :
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

                self.set_cloud_operations_instance(obj_attr_list["model"])            
                _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]

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
                    _status, _msg = _cld_conn.vmdestroy_repeat(obj_attr_list)

                elif _obj_type == "AI" :
                    self.pre_detach_ai(obj_attr_list)
                    _cld_conn.aiundefine(obj_attr_list,"deprovision_finished")
                    
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
                _msg += "successfully detached from this experiment."
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

            if "hosts" in obj_attr_list and obj_attr_list["discover_hosts"].lower() == "true" :
                for _host_uuid in obj_attr_list["hosts"].split(',') :
                    _host_attr_list =  self.osci.get_object(obj_attr_list["cloud_name"], "HOST", False, _host_uuid, False)
                    self.osci.destroy_object(obj_attr_list["cloud_name"], "HOST", _host_uuid, _host_attr_list, False)
                    self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                   "HOST", _host_attr_list, \
                                                   "detach")

            self.record_management_metrics(obj_attr_list["cloud_name"], "VMC", \
                                           obj_attr_list, "detach")
            
            _status = 0

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
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

            self.admission_control("VM", obj_attr_list, "deschedule")

            if str(obj_attr_list["current_state"]).lower() != "attached" :

                if "post_capture" in obj_attr_list and obj_attr_list["post_capture"] == "true" :
                    _scores = True
                else :
                    _scores = False

                self.osci.remove_from_list(obj_attr_list["cloud_name"], "VM", "VMS_UNDERGOING_" + str(obj_attr_list["current_state"]).upper(), obj_attr_list["uuid"], _scores)


            self.record_management_metrics(obj_attr_list["cloud_name"], "VM", \
                                           obj_attr_list, "detach")

            _status = 0

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg =  str(obj.msg)

        except Exception as e :
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

            self.record_management_metrics(obj_attr_list["cloud_name"], \
                                           "AI", obj_attr_list, "detach")


            _status = 0

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
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

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
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

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
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

        except IndexError as msg :
            _status = 40
            _fmsg = str(msg)

        except Exception as e :
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except Exception as e :
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
                    
        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
        '''
        TBD
        '''
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

                    self.set_cloud_operations_instance(obj_attr_list["model"])            
                    _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]                                        

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
    

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
                    self.set_cloud_operations_instance(obj_attr_list["model"])            
                    _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]                                        

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

                        if "mgt_102_capture_request_sent" in obj_attr_list :
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
                            if "mgt_999_provisioning_request_failed" not in obj_attr_list :
                                obj_attr_list["mgt_999_provisioning_request_failed"] = \
                                    int(time()) - int(obj_attr_list["mgt_001_provisioning_request_originated"])

                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], "VM", \
                                                              obj_attr_list["uuid"], \
                                                              False, \
                                                              "mgt_999_capture_request_failed", \
                                                              obj_attr_list["mgt_999_capture_request_failed"])
    
                        obj_attr_list["post_capture"] = "true"
    
                        if obj_attr_list["walkthrough"] == "true" :
                                _vm_templates = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                                     "GLOBAL", \
                                                                     False, \
                                                                     "vm_templates", False)
    
                                _vm_t = str2dic(_vm_templates["tinyvm"])
                                _vm_t["imageid1"] = obj_attr_list["captured_image_name"]
                                _vm_t = dic2str(_vm_t)

                                self.osci.update_object_attribute(obj_attr_list["cloud_name"], \
                                                                  "GLOBAL", \
                                                                  "vm_templates", \
                                                                  False, \
                                                                  "tinyvm", \
                                                                  _vm_t)
                                    
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally:        
            if _status :
                _msg = _obj_type + " object " + obj_attr_list["uuid"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "captured on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = self.walkthrough_messages(_obj_type, "capture", obj_attr_list)
                if len(_msg) < 3 :
                    _msg = _obj_type + " object " + obj_attr_list["uuid"] 
                    _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully captured "
                    _msg += "on this experiment."
                cbdebug(_msg)

            return self.package(_status, _msg, _result)

    @trace    
    def imgdelete(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _result = None
            _fmsg = "An error has occurred, but no error message was captured"
            
            obj_attr_list["name"] = "undefined"
            obj_attr_list["imageid1"] = "NA"
            obj_attr_list["boot_volume_imageid1"] = "NA"
                
            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                
                if not _status :                            
                    self.set_cloud_operations_instance(obj_attr_list["model"])         
                    _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]                
    
    #                if "ai" in obj_attr_list and obj_attr_list["ai"].lower() != "none" :
    #                    _ai_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "AI", False, obj_attr_list["ai"], False)
                        
    #                    _current_state = self.osci.get_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"])
                    
                    _status, _fmsg = _cld_conn.imgdelete(obj_attr_list)
                    _result = obj_attr_list
                    _status = 0

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally:
            
            if _status :
                _msg = "IMAGE object " + obj_attr_list["boot_volume_imageid1"] + " ("
                _msg += "named \"" + obj_attr_list["name"] + "\") could not be "
                _msg += "deleted on this experiment: " + _fmsg
                cberr(_msg)
            else :
                _msg = "IMAGE object " + obj_attr_list["boot_volume_imageid1"] 
                _msg += " (named \"" + obj_attr_list["name"] +  "\") successfully "
                _msg += "deleted on this experiment."
                cbdebug(_msg)

            return self.package(_status, _msg, _result)

    @trace    
    def vmresize(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _result = None
            _fmsg = "An error has occurred, but no error message was captured"
            
            obj_attr_list["uuid"] = "undefined"            
            obj_attr_list["name"] = "undefined"

            _resizable_vm = True
            _obj_type = command.split('-')[0].upper()
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
                
            if not _status :
                self.set_cloud_operations_instance(obj_attr_list["model"])         
                _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]                

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

                    _result = obj_attr_list
                    
                    _status = 0

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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

            return self.package(_status, _msg, _result)

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
                                self.set_cloud_operations_instance(obj_attr_list["model"])            
                                _cld_conn = self.coi[obj_attr_list["model"]][self.pid + '-' + obj_attr_list["experiment_id"]]
                                         
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
        
                                    if "mgt_201_runstate_request_originated" in obj_attr_list :
                                        self.osci.update_object_attribute(_cloud_name, "VM", \
                                                                      obj_attr_list["uuid"], \
                                                                      False, \
                                                                      "mgt_201_runstate_request_originated", \
                                                                      obj_attr_list["mgt_201_runstate_request_originated"])
                                    if "mgt_202_runstate_request_sent" in obj_attr_list :
                                        self.osci.update_object_attribute(_cloud_name, "VM", \
                                                                      obj_attr_list["uuid"], \
                                                                      False, \
                                                                      "mgt_202_runstate_request_sent", \
                                                                      obj_attr_list["mgt_202_runstate_request_sent"])
                                    
                                    if "mgt_203_runstate_request_completed" in obj_attr_list :
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
            
        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except ImportError as msg :
            _status = 8
            _fmsg = str(msg)

        except AttributeError as msg :
            _status = 8
            _fmsg = str(msg)

        except Exception as e :
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

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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

                            _pool, _meta_tag, _size, _extra_parms = \
                            self.propagate_ai_attributes_to_vm(_vm_role, _cloud_ips, obj_attr_list)

                            if _vm_role in _cloud_ips :
                                if _extra_parms != '' :
                                    _cloud_ip = ','
                                else :
                                    _cloud_ip = ''
                                _cloud_ip += "cloud_ip=" + _cloud_ips[_vm_role].pop()
                            else :
                                _cloud_ip = ''

                            obj_attr_list["parallel_operations"][_vm_counter] = {} 
                            _pobj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0,10000000000000000) + _vm_counter)))
                            _pobj_uuid = _pobj_uuid.upper()

                            obj_attr_list["temp_vms"] += _pobj_uuid + ','
                            obj_attr_list["parallel_operations"][_vm_counter]["uuid"] = _pobj_uuid
                            obj_attr_list["parallel_operations"][_vm_counter]["ai"] = obj_attr_list["uuid"]                            
                            obj_attr_list["parallel_operations"][_vm_counter]["ai_name"] = obj_attr_list["name"]
                            obj_attr_list["parallel_operations"][_vm_counter]["aidrs"] = obj_attr_list["aidrs"]
                            obj_attr_list["parallel_operations"][_vm_counter]["aidrs_name"] = obj_attr_list["aidrs_name"]
                            obj_attr_list["parallel_operations"][_vm_counter]["pattern"] = obj_attr_list["pattern"]
                            obj_attr_list["parallel_operations"][_vm_counter]["type"] = obj_attr_list["type"]
                            obj_attr_list["parallel_operations"][_vm_counter]["base_type"] = obj_attr_list["base_type"]
                            obj_attr_list["parallel_operations"][_vm_counter]["mode"] = obj_attr_list["mode"]
                            obj_attr_list["parallel_operations"][_vm_counter]["placement_order"] = _vm_counter                            
                            obj_attr_list["parallel_operations"][_vm_counter]["parameters"] = obj_attr_list["cloud_name"] +\
                             ' ' + _vm_role + ' ' + _pool + ' ' + _meta_tag + ' ' +\
                              _size + ' ' + _attach_action + ' ' + _extra_parms + _cloud_ip
                            obj_attr_list["parallel_operations"][_vm_counter]["operation"] = "vm-attach"
                            _vm_command_list += obj_attr_list["cloud_name"] + ' ' +\
                             _vm_role + ", " + _pool + ", " + _meta_tag + ", " +\
                              _size + ", " + _attach_action + ", " + _extra_parms + _cloud_ip + "; "
                            _vm_counter += 1

                        obj_attr_list["temp_vms"] = obj_attr_list["temp_vms"][:-1]

                        _msg = "VM attach command list is: " + _vm_command_list
                        cbdebug(_msg)

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

                    _status, _fmsg  = self.parallel_vm_config_for_ai(obj_attr_list["cloud_name"], \
                                                                     obj_attr_list["uuid"], \
                                                                     "resize")
                    
                    if not _status :

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
                        
                        self.osci.update_object_attribute(obj_attr_list["cloud_name"],\
                                                           "AI", \
                                                           obj_attr_list["uuid"],\
                                                            False,\
                                                             "sut",\
                                                              obj_attr_list["sut"])

                        for _vm in obj_attr_list["vms"].split(',') :
                            _vm_uuid, _vm_role, _vm_name = _vm.split('|')
                            
                            _vm_obj_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                                     "VM", \
                                                                     False, \
                                                                     _vm_uuid, \
                                                                     False)

                            self.record_management_metrics(obj_attr_list["cloud_name"], \
                                                           "VM", \
                                                           _vm_obj_attr_list, \
                                                           "attach")   
                            
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"],\
                                                               "VM",\
                                                                _vm_uuid,\
                                                                 False,\
                                                                  "sut",\
                                                                   obj_attr_list["sut"])

                        _status = 0
                        _result = obj_attr_list

                else :

                    _fmsg = "AI object named \"" + obj_attr_list["name"] + "\" could "
                    _fmsg += "not be resized because it is on the "
                    _fmsg += "\"" + _current_state + "\" state."
                    _status = 817

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally:        
    
            self.osci.remove_from_list(obj_attr_list["cloud_name"], "AI", "AIS_UNDERGOING_RESIZE", obj_attr_list["name"])
            self.osci.set_object_state(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], "attached")

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
                        if "nosync" in obj_attr_list and obj_attr_list["nosync"] == "true" :
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, obj_attr_list["cloud_name"] + ' ' + _vm_name, "vm-capture")
                        elif not BaseObjectOperations.default_cloud :
                            _cloud_name = parameters.split()[0]
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, _cloud_name + ' ' + _vm_name, "vm-capture")
                        else :
                            _status, _fmsg, _object = self.vmcapture(_capture_vm_attr_list, _vm_name, "vm-capture")
                        break
                _result = obj_attr_list

        except self.ObjectOperationException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
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
                
            for _object in list(obj_attr_list["parallel_operations"].keys()) :
                
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
                for _object in list(obj_attr_list["parallel_operations"].keys()) :
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
            
        except self.ObjectOperationException as obj :
            _status = 45
            _fmsg = str(obj.msg)
            if _thread_pool :
                _thread_pool.abort()
                
        except self.osci.ObjectStoreMgdConnException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            if _thread_pool :
                _thread_pool.abort()
                
        except Exception as e :
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
        first_stop = False
        _ai_state = True
        _prev_load_level = 0
        _prev_load_duration = 0
        _prev_load_id =  0

        _initial_ai_attr_list = self.osci.get_object(cloud_name, "AI", False, object_uuid, False)
        
        _check_frequency = float(_initial_ai_attr_list["update_frequency"])

        while _ai_state :

            # We should always be talking to from redis, regardless
            # whether or not we have a scalable mode or controllable mode.
            # Without it, we cannot accurately update large scale tests when
            # running on multiple clouds at the same time.

            _ai_state = self.osci.get_object_state(cloud_name, "AI", object_uuid)
            _ai_attr_list = self.osci.get_object(cloud_name, "AI", False, object_uuid, False)
            _check_frequency = float(_ai_attr_list["update_frequency"])

            _sla_runtime_targets = ''
            for _key in _ai_attr_list :
                if _key.count("sla_runtime_target") :
                    _sla_runtime_targets += _key + ':' + _ai_attr_list[_key] + ','

            if _sla_runtime_targets != '':
                _sla_runtime_targets = _sla_runtime_targets[:-1]

            if _ai_state and _ai_state == "attached" :
                if not first_stop and str(_ai_attr_list["pause_after_attached"]).lower() == "true" :
                    self.osci.set_object_state(cloud_name, "AI", object_uuid, "stopped")
                    sleep(_check_frequency)
                    first_stop = True
                    cbdebug("Attach complete. Pausing myself")
                    continue

                _load = self.get_load(cloud_name, _ai_attr_list, False, \
                                      _prev_load_level, _prev_load_duration, \
                                      _prev_load_id)

                if _load :
                    _prev_load_level = _ai_attr_list["current_load_level"]
                    _prev_load_duration = _ai_attr_list["current_load_duration"]
                    _prev_load_id = _ai_attr_list["current_load_id"]

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

                self.update_object_attribute(cloud_name, \
                                             object_type.upper(), \
                                             object_uuid, \
                                             "current_reset_status", \
                                             _reset_status) 
    
                # The change we're making here is that we now kick off the workload over
                # SSH to support multiple load generators running simultaneously.
                if not _reset_status :
                    _cmd_params = ''
                    _cmd_params += str(_ai_attr_list["current_load_profile"]) + ' '                    
                    _cmd_params += str(_ai_attr_list["current_load_level"]) + ' '
                    _cmd_params += str(_ai_attr_list["current_load_duration"]) + ' '
                    _cmd_params += str(_ai_attr_list["current_load_id"]) + ' '
                    _cmd_params += str(_sla_runtime_targets)

                    # We still preserve the original behavior for the vast majority of cases
                    # by simply opening a local fork/exec to run the workload when SSH
                    # is not needed.
                    if _ai_attr_list["load_generator_ip"] == _ai_attr_list["load_manager_ip"] and int(str(_ai_attr_list["load_generator_sources"])) == 1 :
                        _script_key = _ai_attr_list["load_manager_role"].lower() + "_start1"
                        _cmd = "~/" + _ai_attr_list[_script_key] + ' ' + _cmd_params
        
                        _proc_h = Popen(_cmd, shell=True)
        
                        if _proc_h.pid :
                            _msg = "Local load generating command \"" + _cmd + "\" "
                            _msg += " was successfully started."
                            _msg += "The process id is " + str(_proc_h.pid) + "."
                            cbdebug(_msg)
                        
                            _msg = "Waiting for the load generating process to "
                            _msg += "terminate."
                            cbdebug(_msg)

                            _proc_h.wait()
                    else :
                        # Otherwise, if multiple load generator roles are defined, then
                        # we need to start those over SSH
                        _start_status, _fmsg = self.parallel_vm_config_for_ai(cloud_name, \
                                                                    object_uuid, \
                                                                    "start", cmd_params = _cmd_params)
                        if not _start_status :
                            cbdebug("Remote load generator completed.")
                        else : 
                            cberr("Remote load generator start failed: " + _fmsg)

                    if str(_ai_attr_list["pause_after_run"]).lower() == "true" :
                        cbdebug("Run complete. Pausing myself")
                        self.osci.set_object_state(cloud_name, "AI", object_uuid, "stopped")
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
                sleep(_check_frequency)
        
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
                        _msg += "was successfully started by " + _aidrs_attr_list["log_string"] + '.'
                        #_msg += "The process id is " + str(_aid_pid) + "."
                        cbdebug(_msg)

                        _obj_id = _ai_uuid + '-' + "attach"
                        self.update_process_list(cloud_name, "AI", \
                                                 _obj_id, \
                                                 str(_aid_pid), \
                                                 "add",
                                                 " (" + _aidrs_attr_list["log_string"] + ") ")
                    else :
                        _msg = "AI attachment command \"" + _cmd + "\" "
                        _msg += "could not be successfully started by " + _aidrs_attr_list["log_string"] + '.'
                        cberr(_msg)
                else :
                    _msg = "Unable to get state, or state is \"stopped\"."
                    _msg += "Will stop creating new AIs until the state of "
                    _msg += _aidrs_attr_list["log_string"] + " changes."
                    cbdebug(_msg)
            else :
                _msg = _aidrs_attr_list["log_string"] + " is overloaded because " + _msg
                _msg += ". Will keep checking its state and "
                _msg += " destroying overdue AIs, but will not create new ones"
                _msg += " until the number of AIs/Daemons drops below the limit."
                cbdebug(_msg)

                if _curr_iait < _check_frequency :
                    _check_frequency = _curr_iait / 2

            _aidrs_state = self.osci.get_object_state(cloud_name, "AIDRS", object_uuid)

            if not _aidrs_state  :
                _msg = _aidrs_attr_list["log_string"] + " state could not be "
                _msg += "obtained. This process will exit, leaving all the AIs behind."
                cbdebug(_msg)
                break

            elif _aidrs_state == "stopped" :
                _msg = _aidrs_attr_list["log_string"] + " state was set to \"stopped\"."
                cbdebug(_msg)
            else :
                True

            _inter_arrival_time = int(time()) - _inter_arrival_time_start

            while _inter_arrival_time < _curr_iait :

                _inter_arrival_time = int(time()) - _inter_arrival_time_start
                
                if abs(_inter_arrival_time - _curr_iait) < _check_frequency :
                    sleep(_check_frequency/10)
                else :
                    sleep(_check_frequency)

        _msg = "This AIDRS daemon has detected that the " + _aidrs_attr_list["log_string"] 
        _msg += " associated to it was detached. Proceeding to remove its pid from"
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

                _msg = "Some AIs issued by " + _aidrs_attr_list["log_string"] + " have reached the end of their "
                _msg += "lifetimes, and will now be removed."
                _msg += "Overdue AI list is : " + ','.join(_my_overdue_ais)
                cbdebug(_msg)

                for _ai in _my_overdue_ais :
                    _ai_uuid, _ai_name = _ai.split('|')
                    
                    _current_state = self.osci.get_object_state(cloud_name, "AI", _ai_uuid)

                    if _current_state and _current_state == "attached" :                    
                        _cmd = base_dir + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.osci.oscp())
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
                            _msg += " was successfully started by " + _aidrs_attr_list["log_string"] + '.'
                            #_msg += "The process id is " + str(_aid_pid) + "."
                            cbdebug(_msg)

                            _obj_id = _ai_uuid + '-' + "detach"
                            self.update_process_list(cloud_name, "AI", \
                                                     _obj_id, \
                                                     str(_aid_pid), \
                                                     "add", 
                                                     " (" + _aidrs_attr_list["log_string"] + ") ")
                    else :
                        _msg = "AI \"" + _ai_uuid + "\" is on the \""
                        _msg += _current_state + "\" and therefore cannot "
                        _msg += "detached."
                        cbdebug(_msg)
            else :
                _msg = "No AIs issued by " + _aidrs_attr_list["log_string"] + " have reached the end of their lifetimes."
                cbdebug(_msg)

            _aidrs_state = self.osci.get_object_state(cloud_name, "AIDRS", object_uuid)

            if not _aidrs_state  :
                _msg = _aidrs_attr_list["log_string"] + " state could not be "
                _msg += "obtained. This process will exit, leaving all the AIs behind."
                cbdebug(_msg)
                break

            elif _aidrs_state == "stopped" :
                _msg = _aidrs_attr_list["log_string"] + " state was set to \"stopped\"."
                cbdebug(_msg)
            else :
                True

            sleep(int(_aidrs_attr_list["update_frequency"]))

        _msg = "This AIDRS daemon has detected that the " + _aidrs_attr_list["log_string"] 
        _msg += " associated to it was detached. Proceeding to remove its pid from"
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
        except self.osci.ObjectStoreMgdConnException as obj :
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

        except self.osci.ObjectStoreMgdConnException as obj :
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

        except self.osci.ObjectStoreMgdConnException as obj :
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
        except self.osci.ObjectStoreMgdConnException as obj :
            app["msg"] = "Failed to run initialized Application: " + str(obj)
            app["status"] = obj.status
            app["result"] = None
        
        return app
