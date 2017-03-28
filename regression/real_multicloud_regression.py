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
from time import sleep,time
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
        print "./" + argv[0] + " <multi cloud config dir> [comma-separated value cloud model list] [minimal|low|medium|high|complete|pause]"
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
    
    if len(argv) > 3 :
        if argv[3] == "minimal" :
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
    
        if argv[3] == "pause" :        
            _options.pause = True
            
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

def check_cloud_attach(apiconn, cloud_model) :
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

    except APIException, obj :
        _error = True
        _fmsg = "API Problem (" + str(obj.status) + "): " + obj.msg
    
    except Exception, msg :
        _error = True
        _fmsg = "Problem during experiment: " + str(msg)
    
    finally :
        if _cloud_attached :
            print _msg
            _result = "PASS"
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
        _model_to_imguuid["osk"] = "xenial0"
        _model_to_imguuid["ec2"] = "ami-a9d276c9"
        _model_to_imguuid["gce"] = "ubuntu-1604-xenial-v20161221"
        _model_to_imguuid["do"] = "21669205"        
        _model_to_imguuid["slr"] = "1373563"        
        _model_to_imguuid["kub"] = "ibmcb/cbtoolbt-ubuntu"

        _model_to_login = {}
        _model_to_login["sim"] = "ubuntu"
        _model_to_login["pcm"] = "ubuntu" 
        _model_to_login["pdm"] = "cbuser"
        _model_to_login["nop"] = "ubuntu"
        _model_to_login["osk"] = "ubuntu"
        _model_to_login["ec2"] = "ubuntu"
        _model_to_login["gce"] = "ubuntu"
        _model_to_login["do"] = "root"        
        _model_to_login["slr"] = "root"
        _model_to_login["kub"] = "cbuser"

        _vm_location = "auto"
        _meta_tags = "empty"
        _size = "default"
        _pause_step = "none"
        _nop_cloud_ip = "172.16.0.254"
        _temp_attr_list = "empty=empty"
        
        if test_case.count("pubkey") :
            _img_name = _model_to_imguuid[cloud_model]
        else :
            _img_name = "regressiontest"
        _login = _model_to_login[cloud_model]

        #if test_case == "no pubkey injection, no volume" :
        _vm_role = "check:" + _img_name

        if test_case == "pubkey injection, no volume" :
            _vm_role = "check:" + _img_name + ':' + _login    

        if test_case.count(", volume") :
            if cloud_model == "osk" :            
                _temp_attr_list = "cloud_vv=1"
            else :
                _temp_attr_list = "cloud_vv=10"
                                
        if test_case.count("force failure") :
            _temp_attr_list = "force_failure=true"
            
        if test_case == "newly captured image" :
            _vm_role = "check:regressiontest:" + _login

        if test_case == "non-existent image failure" :
            _vm_role = "check:regressiontest:" + _login

        if cloud_model == "nop" :
            _temp_attr_list += ",cloud_ip=" + _nop_cloud_ip

        _vms_failed = int(apiconn.stats(cloud_name, "all", "noprint", "true")["experiment_counters"]["VM"]["failed"])
            
        print "## Testing VM Attach (" + test_case + ") using \"" + _vm_role +  "\" (" + _temp_attr_list + ")..."
        _vm = apiconn.vmattach(cloud_name, _vm_role, _vm_location, _meta_tags, _size, _pause_step, _temp_attr_list)

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
                if test_case.count("no volume") :
                    if "cloud_vv_uuid" in _vm and str(_vm["cloud_vv_uuid"]).lower() == "none" :
                        _result = "PASS"
                    else :
                        _attach_error = True
                        _result = "FAIL"                        
                else :
                    print "######## VV UUID: " + str(_vm["cloud_vv_uuid"]).lower()
                    if str(_vm["cloud_vv_uuid"]).lower() == "not supported" :
                        _result = "NA"
                    elif str(_vm["cloud_vv_uuid"]).lower() != "none" :
                        _result = "PASS"
                    else :
                        _attach_error = True
                        _result = "FAIL"
            else :
                _attach_error = True
                _result = "FAIL"                
        else :
            if int(_vm_counters["reservations"]) == 0 and int(_vm_counters["failed"]) - _vms_failed != 0 and int(_vm_counters["reported"]) == 0 :
                _result = "PASS"
                _attach_error = False
            else :
                _result = "FAIL"
                _attach_error = True

        if not test_case.count("failure") and not test_case.count(", volume") and "uuid" in _vm :    
            print "#### Testing VM Detach (" + test_case + ")..."
            try :
                apiconn.vmdetach(cloud_name, _vm["uuid"])

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
        _vm = apiconn.vmcapture(cloud_name, "youngest", "regressiontest", "none", False)

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
            return "PASS"

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
        _img = apiconn.imgdelete(cloud_name, "regressiontest", _vmc, True)

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
            return "PASS"

def main() :
    '''
    TBD
    '''
    _options = cli_postional_argument_parser()
        
    _test_results_table = prettytable.PrettyTable(["Cloud Model", \
                                                   "Cloud Attach", \
                                                   "VM Attach (no pubkey injection, no volume)", \
                                                   "VM Attach (pubkey injection, no volume)", \
                                                   "VM Attach (pubkey injection, volume)", \
                                                   "VM Capture", \
                                                   "VM Attach (newly captured image, no volume)", \
                                                   "IMAGE Delete", \
                                                   "VM Attach (non-existent image failure)", \
                                                   "VM Attach (pubkey injection, force failure)"])
                                                  
    for _cloud_model in _options.cloud_models :
        _start = int(time())
        print ''
        _command = _cb_cli_path + " --hard_reset --config " + _options.cloud_config_dir + '/' + _cloud_model + ".txt exit"
        print "Attaching Cloud Model \"" + _cloud_model + "\" by running the command \"" + _command + "\"..."
        _proc_h = subprocess.Popen(_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _resul = _proc_h.communicate()
    
        _status = _proc_h.returncode
        if _status :
            print "ERROR while attempting to attach Cloud Model \"" + _cloud_model + "\""
            exit(_status)
    
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
        api = APIClient(_api_conn_info)

        _results_row = []
        _results_row.append(_cloud_model)

        if _options.pause :
            raw_input("Press Enter to continue...")
                        
        _cloud_result, _cloud_name = check_cloud_attach(api, _cloud_model)
        _results_row.append(_cloud_result)
        
        _test_cases = ["NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA" ]
        if _options.test_instances :
            _test_cases[0] = "no pubkey injection, no volume"
        
        if _options.test_ssh :
            _test_cases[1] = "pubkey injection, no volume"
            
        if _options.test_volumes :
            _test_cases[2] = "pubkey injection, volume"

        if _options.test_capture :
            _test_cases[3] = "vm capture"
            _test_cases[4] = "newly captured image, no volume"
            _test_cases[5] = "image delete"
            _test_cases[6] = "non-existent image failure"
            _test_cases[7] = "pubkey injection, force failure"

        if _cloud_model == "kub" :
            _test_cases[2] = "NA"            
            _test_cases[3] = "NA"
            _test_cases[4] = "NA"
            _test_cases[5] = "NA"            
            
        for _test_case in _test_cases :
            if _test_case.count("vm capture") :
                _results_row.append(check_vm_capture(api, _cloud_model, _cloud_name, _options))
            elif _test_case.count("image delete") :
                _results_row.append(check_img_delete(api, _cloud_model, _cloud_name, _options))
            elif _test_case == "NA":
                _results_row.append("NA")
            else :
                _results_row.append(check_vm_attach(api, _cloud_model, _cloud_name, _test_case, _options) )        

        _results_row[0] = _results_row[0] + " (" + str(int(time())-_start) + "s)"

        _test_results_table.add_row(_results_row)

        _fn = "/tmp/real_multicloud_regression_test.txt"
        _fh = open(_fn, "w")
        _fh.write(str(_test_results_table))
        _fh.close()

        print _test_results_table

        _error = False
             
        if _error :
            exit(1)
            
    exit(0)

main()