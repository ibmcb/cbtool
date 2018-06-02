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

from sys import path, argv
from time import sleep,time,strftime
from optparse import OptionParser

import fnmatch
import os
import pwd
import subprocess
import prettytable
import json

home = os.environ["HOME"]
username = pwd.getpwuid(os.getuid())[0]


_path_set = False
_cb_api_path = "NA"
_cb_cli_path = "NA"

def cli_postional_argument_parser() :
    '''
    TBD
    '''

    if len(argv) < 2 :
        print "./" + argv[0] + " <multi cloud config dir> [comma-separated value cloud model list] [minimal|low|medium|high|complete|pause] [noheader]"
        exit(1)

    _options, args = cli_named_option_parser()

    _options.cloud_config_dir = argv[1]
        
    _options.pause = False

    _options.cloud_models = [ "sim" ]    
    if len(argv) > 2 :
        _options.cloud_models = argv[2].split(',')
    
    _options.test_instances = True
    _options.test_ssh = True    
    _options.test_volumes = True    
    _options.test_capture = True
    _options.pause = False
    _options.private_results = False
    _options.noheader = False
    _options.headeronly = False
    
    if len(argv) > 3 :
        if argv[3] == "minimal" or argv[3] == "lowest" :
            _options.test_instances = False
            _options.test_ssh = False
            _options.test_capture = False
            _options.test_volumes = False
        
        if argv[3] == "low" :
            _options.test_instances = True
            _options.test_ssh = False            
            _options.test_volumes = False            
            _options.test_capture = False
            
        if argv[3] == "medium" :
            _options.test_instances = True
            _options.test_ssh = True 
            _options.test_volumes = False
            _options.test_capture = False

        if argv[3] == "high" :
            _options.test_instances = True
            _options.test_ssh = True 
            _options.test_volumes = True
            _options.test_capture = False

        if argv[3] == "complete" or argv[3] == "highest" :
            _options.test_instances = True
            _options.test_ssh = True 
            _options.test_volumes = True
            _options.test_capture = True
                
        if argv[3] == "pause" :        
            _options.pause = True

    if len(argv) > 4 :
        if argv[4] == "private" :
            _options.private_results = True

    if len(argv) > 5 :
        if argv[5] == "noheader" :
            _options.noheader = True

        if argv[5] == "headeronly" :
            _options.headeronly = True

    return _options

def cli_named_option_parser() :
    '''
    Reserved for future use
    '''
    usage = '''usage: %prog [options] [command]
    '''
    
    parser = OptionParser(usage)

    (options, args) = parser.parse_args()

    return options, args

for _path, _dirs, _files in os.walk(os.path.abspath(path[0] + "/../../")):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        if _path.count("/lib/auxiliary") :
            path.append(_path.replace("/lib/auxiliary",''))
            _path_set = True
            _cb_api_path = _path
            break
    if _path_set :
        break

for i in range(0, 10) :
    _cb_cli_path = os.path.abspath(path[0]) + "/../"*i + "cb"
    if os.access(_cb_cli_path, os.F_OK) :
        break

print "CBTOOL client API library found on \"" + _cb_api_path + "\""
print "CBTOOL executable CLI found on \"" + _cb_cli_path + "\""
    
from lib.api.api_service_client import *

def check_cloud_attach(apiconn, cloud_model, time_mark) :
    '''
    TBD
    '''
    try :
        print "## Checking if a Cloud Model \"" + cloud_model + "\" is attached to this experiment..."
        _error = False
        _fmsg = ''
        _cloud_name = "NA"
        
        _cloud_attached = False
        for _cloud in apiconn.cldlist() :
            if _cloud["model"] == cloud_model :
                _cloud_name = _cloud["name"]
                _cloud_attached = True
                break

        if not _cloud_attached :
            _msg = "## Unable to find a Cloud Model \"" + cloud_model + "\" attached to this experiment."
        else :
            _msg = "## Successfully confirmed that a Cloud Model \"" + cloud_model + "\" (\"" + _cloud_name + "\") was attached to this experiment."
            
            _msg += "Setting new expid" 
            apiconn.expid(_cloud_name, "NEWEXPID")

        _cloud_attach_time = int(time() - time_mark)
        
    except APIException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except Exception, msg :
        _error = True
        _fmsg = "Problem during experiment: " + str(msg)
    
    finally :
        if _cloud_attached :
            print _msg
            _result = "PASS (" + str(_cloud_attach_time).center(3,' ') + " )"
        else :
            if not _error :
                print _msg
                _result = "FAIL"
            else :
                print _fmsg
                _result = "FAIL"
                
        return _result, _cloud_name

def check_vm_attach(apiconn, cloud_model, cloud_name, test_case, options) :
    '''
    TBD
    '''    
    try :

        _attach_error = False
        _delete_error = False
        
        _fmsg = ''
        _vm = {}
        _vms_failed = 0     
        
        print '' 
               
        if cloud_name == "NA" :
            raise ValueError('No cloud (' + cloud_model + ") attached!")

        _model_to_imguuid = {}
        _model_to_imguuid["sim"] = "baseimg"
        _model_to_imguuid["pcm"] = "xenial" 
        _model_to_imguuid["pdm"] = "ibmcb/cbtoolbt-ubuntu"
        _model_to_imguuid["nop"] = "baseimg"
        _model_to_imguuid["osk"] = "xenial3"
        _model_to_imguuid["os"] = "xenial3"        
        _model_to_imguuid["gen"] = "xenial3"
        _model_to_imguuid["plm"] = "xenial"        
        _model_to_imguuid["ec2"] = "ami-a9d276c9"
        _model_to_imguuid["gce"] = "ubuntu-1604-xenial-v20161221"
        _model_to_imguuid["do"] = "21669205"        
        _model_to_imguuid["slr"] = "1836627"        
        _model_to_imguuid["kub"] = "ibmcb/cbtoolbt-ubuntu"
        _model_to_imguuid["as"] = "b39f27a8b8c64d52b05eac6a62ebad85__Ubuntu-16_04-LTS-amd64-server-20180112-en-us-30GB"

        _model_to_login = {}
        _model_to_login["sim"] = "ubuntu"
        _model_to_login["pcm"] = "ubuntu" 
        _model_to_login["pdm"] = "cbuser"
        _model_to_login["plm"] = "ubuntu"        
        _model_to_login["nop"] = "ubuntu"
        _model_to_login["osk"] = "ubuntu"
        _model_to_login["os"] = "ubuntu"        
        _model_to_login["gen"] = "cbuser"
        _model_to_login["ec2"] = "ubuntu"
        _model_to_login["gce"] = "ubuntu"
        _model_to_login["do"] = "root"        
        _model_to_login["slr"] = "root"
        _model_to_login["kub"] = "cbuser"
        _model_to_login["as"] = "cbuser"
        
        _model_to_command = {}
        _model_to_command["sim"] = "echo 'volume_list'"
        _model_to_command["pcm"] = "echo NA"
        _model_to_command["pdm"] = "vm_name sudo mount | grep overlay | awk '{ print \$1 }' && sudo ls /mnt"
        _model_to_command["plm"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["nop"] = "echo NA"
        _model_to_command["osk"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["os"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | cut -d ' ' -f 2 | sed 's/://g'"        
        _model_to_command["gen"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["ec2"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | grep -v /dev/ram | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["gce"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | grep -v /dev/ram | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["do"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | grep -v /dev/ram | cut -d ' ' -f 2 | sed 's/://g'" 
        _model_to_command["slr"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | cut -d ' ' -f 2 | sed 's/://g'"
        _model_to_command["kub"] = "echo NA"
        _model_to_command["as"] = "vm_name sudo fdisk -l | grep Disk | grep bytes | grep -v /dev/ram | cut -d ' ' -f 2 | sed 's/://g'"

        
        _vm_location = "auto"
        _meta_tags = "empty"
        _size = "default"
        _pause_step = "none"
        _nop_cloud_ip = "self"
        _login = _model_to_login[cloud_model]
        _temp_attr_list = "login=" + _login
        
        if test_case.count("pubkey") :
            _img_name = _model_to_imguuid[cloud_model]
        else :
            _img_name = "regressiontest"


        #if test_case == "no pubkey injection, no volume" :
        _vm_role = "check:" + _img_name

        if test_case == "pubkey injection, no volume" :
            _vm_role = "check:" + _img_name + ':' + _login    

        if test_case.count(", volume") :
            _temp_attr_list += ",cloud_vv=5"

        if test_case.count(", vpn") :
            _temp_attr_list += ",use_vpn_ip=true"

        if test_case.count("force failure") :
            _temp_attr_list += ",force_failure=true"
            
        if test_case == "newly captured image" :
            _vm_role = "check:regressiontest:" + _login

        if test_case == "non-existent image failure" :
            _vm_role = "check:regressiontest:" + _login

        if cloud_model == "nop" :
            if _nop_cloud_ip == "self" :
                _command = "sudo ifconfig docker0 | grep inet[[:space:]] | awk '{ print $2 }'"
                _proc_h = subprocess.Popen(_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _resul = _proc_h.communicate()
                _nop_cloud_ip = _resul[0].replace('\n','')
            _temp_attr_list += ",cloud_ip=" + _nop_cloud_ip

        _vms_failed = int(apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]["failed"])
            
        print "## Testing VM Attach (" + test_case + ") using \"" + _vm_role +  "\" (" + _temp_attr_list + ")..."
        _mark_a = time()
        _vm = apiconn.vmattach(cloud_name, _vm_role, _vm_location, _meta_tags, _size, _pause_step, _temp_attr_list)
        _create_time = int(time() - _mark_a)

        if "volume_list" not in _vm :
            _vm["volume_list"] = ''
        
        if options.pause :
            print json.dumps(_vm, indent=4, sort_keys=True)
            raw_input("Press Enter to continue...")
                
        _msg = "#### Testing management performance metrics for VM \"" 
        _msg += _vm["name"] + "\" (" + _vm["cloud_vm_name"] + '/' 
        _msg += _vm["cloud_vm_uuid"] + ")"
        
        if str(_vm["cloud_vv_uuid"]).lower() != "none" :
            _msg += ", connected to volume \"" + _vm["cloud_vv_name"] + "\" ("
            _msg += _vm["cloud_vv_uuid"] + ")..."
        else :
            _msg += "..."

        print _msg            
        _mgt_metric = apiconn.get_latest_management_data(cloud_name, _vm["uuid"])
#        print _mgt_metric
    
    except APIException, obj :
        _attach_error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except APINoSuchMetricException, obj :
        _attach_error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except KeyboardInterrupt :
        print "Aborting this VM."
    
    except Exception, msg :
        _attach_error = True
        _fmsg = "Problem during experiment: " + str(msg)
    
    finally :

        _vm_counters = apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]

        print "###### Status after vmattach"
        print "###### VM RESERVATIONS: " + str(_vm_counters["reservations"])
        print "###### VM FAILED: " + str(_vm_counters["failed"])
        print "###### VM REPORTED: " + str(_vm_counters["reported"])
                       
        if not test_case.count("failure") :

            if int(_vm_counters["reservations"]) == 1 and int(_vm_counters["failed"]) - _vms_failed == 0 and int(_vm_counters["reported"]) == 1 :

                if test_case.count("no volume")  :

                    if "cloud_vv_uuid" in _vm and str(_vm["cloud_vv_uuid"]).lower() == "none" :

                        _result = "PASS" 
                        if not test_case.count("newly") and (test_case.count("no pubkey injection") or test_case.count(", vpn")) :
                            if _vm["prov_cloud_ip"] ==  _vm["run_cloud_ip"] :
                                _result += (" p=r=" + _vm["run_cloud_ip"]).center(35,' ')
                            else :
                                _result += (" p=" + _vm["prov_cloud_ip"] + ",r=" + _vm["run_cloud_ip"]).center(35, ' ')
                        else :
                            _result += (' ' + retriable_execute_command(options, apiconn, cloud_name, cloud_model, _vm, _model_to_command) + ' ').center(35,' ')
                            
                        _result += " (" + str(_create_time).center(3,' ')
                    else :

                        _attach_error = True
                        _result = "FAIL"
                else :

                    print "######## VV UUID: " + str(_vm["cloud_vv_uuid"]).lower()
                    if str(_vm["cloud_vv_uuid"]).lower() == "not supported" :
                        _result = "NA".center(49,' ')
                    elif str(_vm["cloud_vv_uuid"]).lower() != "none" :
                        _result = "PASS"
                        _result += (' ' + retriable_execute_command(options, apiconn, cloud_name, cloud_model, _vm, _model_to_command) + ' ').center(35,' ')
                        _result += " (" + str(_create_time).center(3,' ')                      
                    else :
                        _attach_error = True
                        _result = "FAIL"
            else :

                _attach_error = True
                _result = "FAIL".center(49, ' ')                
        else :
            if int(_vm_counters["reservations"]) == 0 and int(_vm_counters["failed"]) - _vms_failed != 0 and int(_vm_counters["reported"]) == 0 :
                _result = "PASS"
                _attach_error = False
            else :
                _result = "FAILW".center(30, ' ')
                _attach_error = True

        if not test_case.count("failure") and "uuid" in _vm :    
            print "#### Testing VM Detach (" + test_case + ")..."
            try :
                _mark_a = time()                
                apiconn.vmdetach(cloud_name, _vm["uuid"])
                _delete_time = int(time() - _mark_a)
        
            except APIException, obj :
                _delete_error = True
                _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg

            except APINoSuchMetricException, obj :
                _delete_error = True
                _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
                
            except KeyboardInterrupt :
                print "Aborting this VM."

            except Exception, msg :
                _delete_error = True
                _fmsg = "Problem during experiment: " + str(msg)
                
            if not _delete_error :    
                _vm_counters = apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]

                print "###### Status after vmdetach"
                print "###### VM RESERVATIONS: " + str(_vm_counters["reservations"])
                print "###### VM FAILED: " + str(_vm_counters["failed"])
                print "###### VM REPORTED: " + str(_vm_counters["reported"])
            
                if int(_vm_counters["reservations"]) > 0 or int(_vm_counters["reported"]) > 0:
                    _delete_error = True
                    print "#### ERROR while testing VM Detach (" + test_case + ")"
                    _fmsg = "VM reservations or reported is not equal zero"
                    _result = "FAIL"
                else :
                    print "#### Successfully tested VM Detach (" + test_case + ")"
                    if _result.count('(') :
                        _result += '/' + str(_delete_time).center(3,' ') + ')'
                    if _result.count("p=") :
                        _result = _result.center(41, ' ')                        
                    
        if test_case.count("failure") :
            print "######### " + _fmsg            
            _vm_counters = apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]

            print "###### Status after vmattach \"failure\""
            print "###### VM RESERVATIONS: " + str(_vm_counters["reservations"])
            print "###### VM FAILED: " + str(_vm_counters["failed"])
            print "###### VM REPORTED: " + str(_vm_counters["reported"])
        
            if int(_vm_counters["reservations"]) == 0 and int(_vm_counters["reported"]) == 0:
                _attach_error = False
                
        if not _attach_error and not _delete_error :
            _msg = "## Successfully tested VM Attach (" + test_case + ") using image \"" + _img_name +  "\""
            print _msg
        else :
            _fmsg = "## ERROR while testing VM Attach (" + test_case + ") using image \"" + _img_name +  "\": " + _fmsg
            print _fmsg
            
        return _result

def check_vm_capture(apiconn, cloud_model, cloud_name, options) :
    '''
    TBD
    '''
    try :

        print ''
        _error = False
        _fmsg = ''  
                
        if cloud_name == "NA" :
            raise ValueError('No cloud (' + cloud_model + ") attached!")
            
        print "## Testing VM Capture ..."
        _mark_a = time()        
        _vm = apiconn.vmcapture(cloud_name, "youngest", "regressiontest", "none", False)
        _capture_time = int(time() - _mark_a)

        if options.pause :
            print json.dumps(_vm, indent=4, sort_keys=True)
            raw_input("Press Enter to continue...")
            
        _vm_counters = apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]

        print "###### Status after vmcapture"
        print "###### VM RESERVATIONS: " + str(_vm_counters["reservations"])
        print "###### VM FAILED: " + str(_vm_counters["failed"])
        print "###### VM REPORTED: " + str(_vm_counters["reported"])
        
        if int(_vm_counters["reservations"]) > 0 or int(_vm_counters["reported"]) > 0:
            _error = True
            _fmsg = "## ERROR while testing VM Capture"
        else :
            _msg = "## Successfuly tested VM Capture."
    
    except APIException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except APINoSuchMetricException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except KeyboardInterrupt :
        print "Aborting this VM."
    
    except Exception, msg :
        _error = True
        _fmsg = "##Problem during experiment: " + str(msg)
    
    finally :
        if _error :
            print _fmsg
            return "FAIL"
        else :
            print _msg
            return "PASS (" + str(_capture_time).center(3,' ') + ')'

def check_img_delete(apiconn, cloud_model, cloud_name, options) :
    '''
    TBD
    '''
    try :

        print ''
        _error = False
        _fmsg = ''

        if cloud_name == "NA" :
            raise ValueError('No cloud (' + cloud_model + ") attached!")

        _vmc = apiconn.vmclist(cloud_name)[0]["name"]        
        print "## Testing IMAGE Delete ... (" + _vmc + ")"
        _mark_a = time()        
        _img = apiconn.imgdelete(cloud_name, "regressiontest", _vmc, True)
        _imgdelete_time = int(time() - _mark_a)

        if options.pause :
            print json.dumps(_img, indent=4, sort_keys=True)
            raw_input("Press Enter to continue...")
            
        _msg = "## Successfuly tested IMAGE Delete."
    
    except APIException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except APINoSuchMetricException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except KeyboardInterrupt :
        print "Aborting this IMG."
    
    except Exception, msg :
        _error = True
        _fmsg = "Problem during experiment: " + str(msg)
    
    finally :
        if _error :
            print _fmsg
            return "FAIL"
        else :
            print _msg
            return "PASS (" + str(_imgdelete_time).center(3,' ') + ')'

def retriable_cloud_connection(options, actual_cloud_model, command) :
    '''
    TBD
    '''
    
    _api = False
    _attempts = 3
    _attempt = 0
    
    while not _api and _attempt < _attempts :

        try : 
            print "Attaching Cloud Model \"" + actual_cloud_model + "\" by running the command \"" + command + "\"..."
            _proc_h = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _resul = _proc_h.communicate()
    
            _status = _proc_h.returncode

            if _status :
                print "ERROR while attempting to attach Cloud Model \"" + actual_cloud_model + "\""
                exit(_status)
    
            if options.private_results :
                api_file_name = "/tmp/cb_api_" + username + '_' + actual_cloud_model            
            else :
                api_file_name = "/tmp/cb_api_" + username

            if os.access(api_file_name, os.F_OK) :    
                try :
                    _fd = open(api_file_name, 'r')
                    _api_conn_info = _fd.read()
                    _fd.close()
                except :
                    _msg = "Unable to open file containing API connection information "
                    _msg += "(" + api_file_name + ")."
                    print _msg
                    exit(4)
            else :
                _msg = "Unable to locate file containing API connection information "
                _msg += "(" + api_file_name + ")."
                print _msg
                exit(4)
        
            _msg = "Connecting to API daemon (" + _api_conn_info + ")..."
            print _msg
            _api = APIClient(_api_conn_info)
            return _api

        except :
            _api = False
            _attempt += 1
            sleep(10)

def retriable_execute_command(options, apiconn, cloud_name, actual_cloud_model, vm_attr_list, command_to_model) :
    '''
    TBD
    '''
    _attempts = 60
    _attempt = 0

    _volume_list = "NA"    
    while _attempt < _attempts :    

        try :
            _volume_list = apiconn.shell(cloud_name, command_to_model[actual_cloud_model].replace("vm_name", vm_attr_list["name"]).replace("volume_list", vm_attr_list["volume_list"]))["stdout"]
            _volume_list = _volume_list.replace(' ','').replace("\n",',')[0:-1]
            return _volume_list
        
        except :
            _attempt += 1
            sleep(10)

    return _volume_list


def write_results(options, test_results_table, cloud_model) : 
    '''
    TBD
    '''
    if options.headeronly :
        test_results_table.add_row(["         ".center(22, ' '),\
                                    "     ", \
                                    "                                                 ", \
                                    "                                                 ", \
                                    "                                                 ", \
                                    "                                                 ", \
                                    "    ", \
                                    "    ", \
                                    "    ", \
                                    "    ", \
                                    "    "])
            
    _x_test_results_table = test_results_table.get_string().split('\n')
    if options.noheader :
        _x_test_results_table = '\n'.join(_x_test_results_table[7:-1])
    else :
        _x_test_results_table = test_results_table.get_string().split('\n')
        _aux = _x_test_results_table[2]
        _x_test_results_table[2] = _x_test_results_table[3]
        _x_test_results_table[3] = _x_test_results_table[4]
        _x_test_results_table[4] = _x_test_results_table[5]
        _x_test_results_table[5] = _x_test_results_table[6]
        _x_test_results_table[6] = _x_test_results_table[7]  
        _x_test_results_table[7] = _aux
        
        if options.headeronly :
            _x_test_results_table = _x_test_results_table[0:-2]
            
        _x_test_results_table = '\n'.join(_x_test_results_table)
    
    if options.private_results :
        _fn = "/tmp/" + cloud_model + "_real_multicloud_regression_test.txt"
    else :
        _fn = "/tmp/real_multicloud_regression_test.txt"

    _fh = open(_fn, "w")
    _fh.write(str(_x_test_results_table))
    
    if options.private_results :
        _fh.write('\n')

    _fh.close()
    
    if not options.headeronly :
        print _x_test_results_table
    
    return True
    
def main() :
    '''
    TBD
    '''
    _options = cli_postional_argument_parser()

    _first_header = ["Cloud Model", \
                     "Cloud Attach", \
                     "VM Attach", \
                     " VM Attach ", \
                     "  VM Attach ", \
                     "  VM Attach  ", \
                     "VM Capture", \
                     "VM Attach  ", \
                     "IMAGE Delete", \
                     "   VM Attach   ", \
                     "    VM Attach    "]


    _second_header = ['', \
                      '', \
                      "no pubkey injection", \
                      "pubkey injection", \
                      "pubkey injection", \
                      "pubkey injection", \
                      '', \
                      "pubkey injection" , \
                      '', \
                      "pubkey injection", \
                      "pubkey injection"]
    
    _third_header = [strftime("%Y-%m-%d"), \
                     strftime("%H:%M:%S"), \
                     "pre-existing image", \
                     "pre-existing image", \
                     "pre-existing image", \
                     "pre-existing image", \
                     '', \
                     "newly captured image" , \
                     '', \
                     "non-existent image", \
                     "pre-existing image"]
    
    _fourth_header = ['', \
                      '', \
                      "no volume", \
                      "no volume", \
                      "no volume", \
                      "volume", \
                      '', \
                      "no volume" , \
                      '', \
                      "no volume", \
                      "no volume"]
    
    _fifth_header = ['', \
                     '', \
                     "no failure", \
                     "no failure", \
                     "no failure", \
                     "no failure", \
                     '', \
                     "no failure" , \
                     '', \
                     "failure", \
                     "forced failure"]

    _sixth_header = ['', \
                     '', \
                     "no vpn", \
                     "no vpn", \
                     "vpn", \
                     "no vpn", \
                     '', \
                     "no vpn", \
                     '', \
                     "no vpn", \
                     "no vpn"]

    _test_results_table = prettytable.PrettyTable(_first_header)    
    _test_results_table.add_row(_second_header)
    _test_results_table.add_row(_third_header)    
    _test_results_table.add_row(_fourth_header)
    _test_results_table.add_row(_fifth_header)
    _test_results_table.add_row(_sixth_header)

    if _options.headeronly :
        write_results(_options, _test_results_table, _options.cloud_models[0])
        exit(0)

    _at_least_one_error = False
                                                      
    for _cloud_model in _options.cloud_models :
        _start = int(time())
        print ''
        
        if _options.private_results :
            _reset = " --soft_reset"            
        else :
            _reset = " --hard_reset"

        _command = _cb_cli_path + _reset + "  --config " + _options.cloud_config_dir + '/' + _cloud_model + ".txt exit"
        
        _actual_cloud_model = _cloud_model.replace("file",'').replace("fip",'')

        _display_cloud_model = _cloud_model.replace("file"," (file)").replace("fip", " (fip)")
        
        _mark_a = time()
        api = retriable_cloud_connection(_options, _actual_cloud_model, _command)

        _results_row = []
        _results_row.append(_display_cloud_model)

        if _options.pause :
            raw_input("Press Enter to continue...")
            
        _cloud_result, _cloud_name = check_cloud_attach(api, _actual_cloud_model, _mark_a)
        _results_row.append(_cloud_result)
        
        _test_cases = ["NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA" ]
        if _options.test_instances :
            _test_cases[0] = "no pubkey injection, no volume, no vpn"
        
        if _options.test_ssh :
            _test_cases[1] = "pubkey injection, no volume, no vpn"

        if _options.test_ssh :
            _test_cases[2] = "pubkey injection, no volume, vpn"
            
        if _options.test_volumes :
            _test_cases[3] = "pubkey injection, volume, no vpn"

        if _options.test_capture :
            _test_cases[4] = "vm capture"
            _test_cases[5] = "newly captured image, no volume"
            _test_cases[6] = "image delete"
            _test_cases[7] = "non-existent image failure, no vpn"
            _test_cases[8] = "pubkey injection, force failure, no vpn"

        if _actual_cloud_model == "sim" :
            _test_cases[2] = "NA"

        if _actual_cloud_model == "pdm" :
            _test_cases[2] = "NA"

        if _actual_cloud_model == "pcm" :
            _test_cases[2] = "NA"

        if _actual_cloud_model == "nop" :
            _test_cases[2] = "NA"

        if _actual_cloud_model == "kub" :
            _test_cases[2] = "NA"
            _test_cases[3] = "NA"
            _test_cases[4] = "NA"
            _test_cases[5] = "NA"
            _test_cases[6] = "NA"

        if _cloud_model.count("file") or _cloud_model.count("fip") :
            _test_cases[2] = "NA"
            _test_cases[3] = "NA"
            _test_cases[4] = "NA"
            _test_cases[5] = "NA"
            _test_cases[6] = "NA"
                        
        if _actual_cloud_model == "as" :
            _test_cases[2] = "NA"
            _test_cases[3] = "NA"
            _test_cases[4] = "NA"
            _test_cases[5] = "NA"
            _test_cases[6] = "NA"

        if _actual_cloud_model == "gen" :
            _test_cases[2] = "NA"            
            _test_cases[4] = "NA"
            _test_cases[5] = "NA"
            _test_cases[6] = "NA"

        if _actual_cloud_model == "slr" :
            _test_cases[2] = "NA"
            _test_cases[3] = "NA"
                                    
        for _test_case in _test_cases :
            if _test_case.count("vm capture") :
                _results_row.append(check_vm_capture(api, _actual_cloud_model, _cloud_name, _options))
            elif _test_case.count("image delete") :
                _results_row.append(check_img_delete(api, _actual_cloud_model, _cloud_name, _options))
            elif _test_case == "NA":
                _results_row.append("NA")
            else :
                _results_row.append(check_vm_attach(api, _actual_cloud_model, _cloud_name, _test_case, _options) )        

        _results_row[0] = _results_row[0] + " ( " + str(int(time())-_start) + "s )"
        _results_row[0] = _results_row[0].center(22, ' ')

        if _results_row[1] == "NA" :
            _results_row[1] = _results_row[1].center(52,' ')

        if _results_row[2] == "NA" :
            _results_row[2] = _results_row[2].center(51,' ')

        if _results_row[3] == "NA" :
            _results_row[3] = _results_row[3].center(49,' ')

        if _results_row[4] == "NA" :
            _results_row[4] = _results_row[4].center(49,' ')
        
        if _results_row[5] == "NA" :
            _results_row[5] = _results_row[5].center(49,' ')

        _test_results_table.add_row(_results_row)

        write_results(_options, _test_results_table, _cloud_model)

        _error = False

        _fn = "/tmp/" + _cloud_model + "_real_multicloud_regression_ecode.txt"
        _fh = open(_fn, "w")             
        if _error :
            _fh.write(str(1))
            _fh.close()            
            _at_least_one_error = True 
        else :
            _fh.write(str(0))
            _fh.close()            

    if _at_least_one_error :
        exit(1)
    else :
        exit(0)
        
main()
