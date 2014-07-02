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
    SCP v2 (HSLT) Object Operations Library

    @author: Michael R. Hines, Marcio A. Silva 
'''
from time import time, sleep
from random import random
from subprocess import Popen, PIPE
from uuid import uuid5, NAMESPACE_DNS
from sys import path
from random import choice
import xmlrpclib

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

class ScpCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci, expid = None) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.scpconn = False
        self.access_url = False
        self.ft_supported = False
        self.lock = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Smart Cloud Provisioning"

    @trace
    def connect(self, access_urls, authentication_data, rack) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _access_url, _endpoint_url = access_urls.split('-')
            self.scpconn = xmlrpclib.Server("http://" + _access_url)
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Smart Cloud Provisioning connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Smart Cloud Provisioning connection successful."
                cbdebug(_msg)
                return _status, _msg, rack

    @trace
    def query(self, query_type, obj_attr_list, lock = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if obj_attr_list :
                if not self.scpconn.__str__().count("ServerProxy") :
                    self.connect(obj_attr_list["access"], \
                                 obj_attr_list["credentials"], \
                                 obj_attr_list["name"])

#            if lock :
#                _lock = self.lock("VMC", obj_attr_list["vmc"], "operation")

            if query_type == "describe_service_region" :
                _response = self.scpconn.proxy.describe_serviceregion()            
            elif query_type == "describe_hyper_nodes" :
                _response = self.scpconn.proxy.describe_hyper_nodes()
            elif query_type == "describe_storage_nodes" :
                _response = self.scpconn.proxy.describe_storage_nodes()
            elif query_type == "describe_images" :
                _response = self.scpconn.proxy.describe_images([])
            elif query_type == "run_instance" :
                _response = self.scpconn.proxy.run_instances(obj_attr_list["cloud_imageid"], obj_attr_list["size"], obj_attr_list["cloud_vm_name"])
            elif query_type == "describe_specific_instance" :
                _response = self.scpconn.proxy.describe_instances(obj_attr_list["cloud_vm_name"])
            elif query_type == "describe_all_instances" :
                _response = self.scpconn.proxy.describe_instances()
            elif query_type == "terminate_instances" :
                _response = self.scpconn.proxy.terminate_instances(obj_attr_list["cloud_vm_uuid"])
            elif query_type == "capture_image" :
                _response = self.scpconn.proxy.capture_image(obj_attr_list["cloud_vm_uuid2"], obj_attr_list["captured_image_name"])
            elif query_type == "describe_image" :
                _response = self.scpconn.proxy.describe_images(obj_attr_list["captured_image_name"])
            else :
                _response = []
                _response.append("X")

#            if lock :
#                if self.unlock("VMC", obj_attr_list["vmc"], _lock) :
#                    True

            if _response is None or _response is False:
                _status = 131
                _fmsg = "Failure: empty response"

            elif len(_response) == 1 : 
                if "error" in _response[0] :
                    _status = 141
                    _fmsg = "Failure: " + _response[0]["error"]
                elif "X" in _response[0] :
                    _status = 151
                    _fmsg = "Unknown query type: " + query_type
                else :
                    _status = 0
            else :
                #_msg = "Response for query \"" + query_type + "\" was: " + _response
                _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Smart Cloud Provisioning query failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Smart Cloud Provisioning query successful."
                cbdebug(_msg)
                return _response

    @trace
    def test_vmc_common(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _access_url, _iaas_endpoint = access.split('-')            
        _target, _port_number = _access_url.split(':')
        _deploy_python_proxy_script = self.path + "/scripts/common/scp_python_proxy.sh"
        _python_proxy_script = "scp2_python_proxy.rb"
        _iaas_access_id, _iaas_private_key, _iaas_service_public_key = credentials.split('-')

        _cmd = _deploy_python_proxy_script + ' ' + _target + ' ' + _port_number
        _cmd += ' ' + _python_proxy_script + ' ' + _iaas_access_id
        _cmd += ' http://' + _iaas_endpoint + ' ' + _iaas_private_key
        _cmd += ' ' + _iaas_service_public_key

        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)

        if _proc_h.pid :
            _msg = "Python proxy daemon deployment on service VM "
            _msg += "\"" + _target + "\" started successfully with the "
            _msg += "command \"" + _cmd + "\"."
            cbdebug(_msg)
        else :
            _msg = "Error while deploying python proxy daemon on the "
            _msg += "service VM \"" + _target + "\" with the command "
            _msg += "\"" + _cmd + "\""
            cberr(_msg)
            raise CldOpsException(_msg, 98)

        _proc_h.communicate()

        if not _proc_h.returncode :
            _msg = "Python proxy deployed successfully on service VM "
            _msg += "\"" + _target + "\"."
            cbdebug(_msg, True)
            # This is very important! Give the script a couple of seconds
            # to start.
            sleep (2)
        else :
            _msg = "Python proxy failed to deploy on service VM "
            _msg += "\"" + _target + "\"."
            cberr(_msg, True)
            raise CldOpsException(_msg, 98)

    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            self.test_vmc_common(vmc_name, access, credentials, 2)
            self.connect(access, credentials, vmc_name)
            self.query("describe_service_region", None, False)

            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _registered_image_list = self.query("describe_images", None, True)
            _registered_imageid_list = []

            for _registered_image in _registered_image_list :
                _registered_imageid_list.append(_registered_image["image_id"])

            _required_imageid_list = {}

            for _vm_role in vm_templates.keys() :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]                
                if _imageid not in _required_imageid_list :
                    _required_imageid_list[_imageid] = []
                _required_imageid_list[_imageid].append(_vm_role)

            _msg = 'y'

            _detected_imageids = {}
            _undetected_imageids = {}

            for _imageid in _required_imageid_list.keys() :
                
                # Unfortunately we have to check image names one by one,
                # because they might be appended by a generic suffix for
                # image randomization (i.e., deploying the same image multiple
                # times as if it were different images.
                _image_detected = False
                for _registered_imageid in _registered_imageid_list :
                    if str(_registered_imageid).count(_imageid) :
                        _image_detected = True
                        _detected_imageids[_imageid] = "detected"
                    else :
                        _undetected_imageids[_imageid] = "undetected"

                if _image_detected :
                    True
#                    _msg += "xImage id for VM roles \"" + ','.join(_required_imageid_list[_imageid]) + "\" is \""
#                    _msg += _imageid + "\" and it is already registered.\n"
                else :
                    _msg = "xWARNING Image id for VM roles \""
                    _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                    _msg += _imageid + "\" is NOT registered "
                    _msg += "(attaching VMs with any of these roles will result in error).\n"
            
            if not len(_detected_imageids) :
                _msg = "None of the image ids used by any VM \"role\" were detected"
                _msg += " in this SCP cloud. Please register at least one "
                _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
                cberr(_msg, True)
            else :
                _msg = _msg.replace("yx",'')
                _msg = _msg.replace('x',"         ")
                _msg = _msg[:-2]
                if len(_msg) :
                    cbdebug(_msg, True)

            _status = 0

        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC \"" + vmc_name + "\" did not pass the connection test."
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC \"" + vmc_name + "\" was successfully tested."
                cbdebug(_msg, True)
                return _status, _msg

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        try :

            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
    
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            _msg = "Executing host discovery commands on VMC \"" + obj_attr_list["name"] + "\"....."
            cbdebug(_msg, True)
    
            _hyper_node_list = self.query("describe_hyper_nodes", obj_attr_list)
    
            _storage_node_list = self.query("describe_storage_nodes", obj_attr_list)
            
            _host_list = _hyper_node_list + _storage_node_list

            _msg = "Host discovery commands executed successfully on VMC \"" + obj_attr_list["name"] + "\"."
            cbdebug(_msg)

            obj_attr_list["host_count"] = len(_host_list)

            for _host in _host_list :
                _host_uuid = str(uuid5(NAMESPACE_DNS,str(_host["ipaddress"]))).upper()
                obj_attr_list["hosts"] += _host_uuid + ','
                obj_attr_list["host_list"][_host_uuid] = {}
                obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
                obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
                if _host["jid"].count("storage") :
                    obj_attr_list["host_list"][_host_uuid]["function"] = "storage"
                    obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = _host["jid"].replace("storage.", '')
                else :
                    obj_attr_list["host_list"][_host_uuid]["function"] = "hyper"
                    obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = _host["jid"].replace(obj_attr_list["name"] + '.', '')
                obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = _host["ipaddress"]        
                obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
                obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
                obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
                obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
                obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
                obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
                obj_attr_list["host_list"][_host_uuid]["simulated"] = "False"
                obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]
                if "login" in obj_attr_list :
                    obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["login"]
                else :
                    obj_attr_list["host_list"][_host_uuid]["login"] = "root"                
                obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
                obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
                _time_mark_prc = int(time())
                obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start
    
            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

            self.additional_host_discovery (obj_attr_list)
            self.populate_interface(obj_attr_list)

            return True

        except CldOpsException, obj :
            _status = obj.status
            _msg = "Error while discovering hosts for VMC \"" + obj_attr_list["name"]
            _msg += "\": " + str(obj.msg)
            cberr(_msg)
            raise CldOpsException(_msg, _status)

        except Exception, e :
            _status = 23
            _msg = "Error while discovering hosts for VMC \"" + obj_attr_list["name"]
            _msg += "\": " + str(e)
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            # check for old instances and destroy
            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"])

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            _running_instances = True
            _status = 0
            while _running_instances and not _status and _curr_tries < _max_tries :
                _running_instances = False                
                _instance_list = self.query("describe_all_instances", obj_attr_list)

                for _instance in _instance_list :
                    if _instance["instance_tag"].count("cb-" + obj_attr_list["username"]) :
                        _running_instances = True
                        if _instance["state"] == "running" :
                            _msg = "Terminating instance \""
                            _msg += _instance["instance_id"] + "\"" 
                            _msg += " (" + _instance["instance_tag"] + ")"
                            cbdebug(_msg, True)
                            _instance["cloud_vm_uuid"] = _instance["gid"]
                            self.query("terminate_instances", _instance, False)

                        if _instance["state"] == "starting" :
                            _msg = "Will wait for instance "
                            _msg += _instance["instance_id"] + "\"" 
                            _msg += " (" + _instance["instance_tag"] + ") to"
                            _msg += "start and then destroy it."
                            cbdebug(_msg, True)

                    _msg = "Some instances are still starting on VMC \"" + obj_attr_list["name"] 
                    _msg += "\". Will wait for " + str(_wait) + " seconds and check again."
                    sleep(_wait)
                    _curr_tries += 1

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "Some instances on VMC \"" + obj_attr_list["name"] + "\""
                _fmsg += " could not be removed because they never became active"
                _fmsg += ". They will have to be removed manually."
                cberr(_msg, True)

                sleep(int(obj_attr_list["update_frequency"]))

        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _msg = "Removing all VMs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VMs names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            _access_url, _iaas_endpoint = obj_attr_list["access"].split('-')
            _name, _discard = _access_url.split(':')
            
            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(_name)
            
            obj_attr_list["arrival"] = int(time())

            if obj_attr_list["discover_hosts"].lower() == "true" :
                _msg = "Discovering hosts on VMC \"" + obj_attr_list["name"] + "\"....."
                cbdebug(_msg, True)
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
                    
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
           
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg, True)
                return _status, _msg

    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = self.query("describe_images", obj_attr_list, True)

            _fmsg += "Please check if the defined image name is present on this "
            _fmsg += "Smart Cloud Provisioning"

            _imageid = False

            _candidate_images = []

            for _idx in range(0,len(_image_list)) :
                if obj_attr_list["randomize_image_name"].lower() == "false" and \
                _image_list[_idx]["image_id"] == obj_attr_list["imageid1"] :
                    _imageid = _image_list[_idx]["image_id"]
                    break
                elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                _image_list[_idx]["image_id"].count(obj_attr_list["imageid1"]) :
                    _candidate_images.append(_image_list[_idx])
                else :                     
                    True

            if  obj_attr_list["randomize_image_name"].lower() == "true" :
                _imageid = choice(_candidate_images)

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _imageid

    @trace
    def vmcunregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
            _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])
            
            if "cleanup_on_detach" in obj_attr_list and obj_attr_list["cleanup_on_detach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            _time_mark_prc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_prc - _time_mark_drs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''        
        if "private_ip" in instance and len(instance["private_ip"]) :
            obj_attr_list["vmc_name"], obj_attr_list["host_name"], _x, _y =  instance["instance_id"].split('.')
            obj_attr_list["cloud_hostname"] = _x + '.' + _y
            obj_attr_list["cloud_ip"] = instance["private_ip"]
            obj_attr_list["cloud_ip"] = instance["private_pip"]            
            obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]
            
            return True
        else :
            return False

    @trace
    def get_vm_instance(self, obj_attr_list) :
        '''
        TBD
        '''
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        sleep(_wait)
        
        while _curr_tries < _max_tries :
            _fmsg = "No error message"
            _status = 0
            try :
    
                _instances = self.query("describe_specific_instance", obj_attr_list, True)
                
                if len(_instances) :
                    return _instances[0]
                else :
                    return False
    
            except CldOpsException, obj :
                _status = obj.status
                _fmsg = str(obj.msg)
                _msg = "An exception was raised while trying to get information "
                _msg += "about the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")."
                _msg += " Will wait for " + str(_wait) + " seconds and try again."
                sleep(_wait)
                _curr_tries += 1
    
            except Exception, e :
                _status = 23
                _fmsg = str(e)
                _msg = "An exception was raised while trying to get information "
                _msg += "about the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")."
                _msg += " Will wait for " + str(_wait) + " seconds and try again."
                sleep(_wait)
                _curr_tries += 1

        if _status :
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_running(self, obj_attr_list) :
        '''
        TBD
        '''
        _instance = self.get_vm_instance(obj_attr_list)

        if _instance :
            if "state" in _instance and _instance["state"] == "running" :
                return _instance
            else :
                return False
        else :
            return False

    @trace
    def is_vm_ready(self, obj_attr_list,) :
        '''
        TBD
        '''
        _instance = self.is_vm_running(obj_attr_list)
        
        if _instance :
            
            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")
            
            if self.get_ip_address(obj_attr_list, _instance) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
            return False
    
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            obj_attr_list["cloud_vm_uuid"] = "NA"

            _instance = False

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] + '-' + "vm" + obj_attr_list["name"].split("_")[1] + '-' + obj_attr_list["role"]

            obj_attr_list["last_known_state"] = "about to connect to webservice VM"

            if self.get_vm_instance(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            obj_attr_list["last_known_state"] = "about to get and image list"

            obj_attr_list["cloud_imageid"] = self.get_images(obj_attr_list) 

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Starting an instance on Smart Cloud Provisioning, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" (" + str(obj_attr_list["cloud_imageid"]) + ") and "
            _msg += "size \"" + obj_attr_list["size"] + "\""
            _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
            cbdebug(_msg, True)

            _instance = self.query("run_instance", obj_attr_list, True)[0]

            if _instance :
                obj_attr_list["cloud_vm_uuid"] = _instance["gid"]
                obj_attr_list["cloud_vm_uuid2"] = _instance["instance_id"]

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
                            
                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
    
                _status = 0

            else :
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :

            if _status :               
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += str(_fmsg) + " (The VM creation will be rolled back)"
                cberr(_msg, True)

                _instance = self.get_vm_instance(obj_attr_list)
                if _instance :
                    self.query("terminate_instances", obj_attr_list)

                raise CldOpsException(_msg, _status)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _time_mark_drs = int(time())

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            _wait = int(obj_attr_list["update_frequency"])
            
            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                if "cloud_vm_uuid" in obj_attr_list and obj_attr_list["cloud_vm_uuid"] != "NA" :
                    _instance_id = obj_attr_list["cloud_vm_uuid"]
                else :
                    _instance_id = _instance["gid"]

                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                _instance = self.query("terminate_instances", obj_attr_list, True)

                sleep(_wait)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
            else :
                True

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmcapture(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                
                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

#                obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"].split('_')[1] + '_'
                # Temporary fix... stupid bug in SCP
                obj_attr_list["captured_image_name"] = obj_attr_list["name"].split('_')[1] + '_'
                obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent. "
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _instance = self.query("capture_image", obj_attr_list, True)

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _vm_image = self.query("describe_image", obj_attr_list, True)

                    if len(_vm_image) and "status" in _vm_image[0] :
                        if _vm_image[0]["status"] == "available" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    if "mgt_103_capture_request_completed" not in obj_attr_list :
                        obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs

                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing. "
                    _msg += "Will wait " + obj_attr_list["update_frequency"]
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    sleep(int(obj_attr_list["update_frequency"]))             
                    _curr_tries += 1

            else :
                _fmsg = "This instance does not exist"
                _status = 1098

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "" + obj_attr_list["name"] + ""
                _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _fmsg +=  "could not be captured after " + str(_max_tries * _wait) + " seconds.... "
                cberr(_msg)
            else :
                _status = 0
            
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, "all_vms_booted")
            
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on Smart Cloud Provisioning \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
