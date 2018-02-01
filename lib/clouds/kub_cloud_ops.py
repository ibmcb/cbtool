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

    PDM Cloud Object Operations Library

    @author: Marcio A. Silva
'''

from time import time, sleep, mktime, strptime
from random import randint
from os.path import expanduser

import operator
import pykube

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, is_number, DataOpsException
from lib.remote.network_functions import hostname2ip, check_url
from shared_functions import CldOpsException, CommonCloudFunctions 

class KubCmds(CommonCloudFunctions) :
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
        self.ft_supported = False
        self.kubeconn = False        
        self.expid = expid
        self.api_error_counter = {}
        self.additional_rc_contents = ''        
        self.max_api_errors = 10
        
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Kubernetes Cloud"

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}, diag = False, generate_rc = False) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _endpoint_ip = "NA"            
            _fmsg = "An error has occurred, but no error message was captured"

            self.kubeconn = pykube.HTTPClient(pykube.KubeConfig.from_file(access))

            for _x in pykube.Endpoint.objects(self.kubeconn) :
                True

            self.additional_rc_contents = "export KUBECONFIG=" + access + "\n"
            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " connection to endpoint \"" + _endpoint_ip + "\" failed: " + _fmsg
                cberr(_msg)                    
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, ''
    
    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True, True)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it (using Docker CLI)"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            if len(_detected_imageids) :
                _status = 0               
            else :
                _status = 1

        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            _status, _msg = self.common_messages("VMC", {"name" : vmc_name }, "connected", _status, _fmsg)
            return _status, _msg

    @trace
    def check_networks(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        _prov_netname = vm_defaults["netname"]
        _run_netname = vm_defaults["netname"]

        _prov_netname_found = True
        _run_netname_found = True
            
        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''

        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _map_name_to_id = {}
        _map_id_to_name = {}

        _registered_image_list = []
        _registered_imageid_list = []

        for _vm_role in vm_templates.keys() :            
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            if _imageid != "to_replace" :
                if _imageid in _map_name_to_id :                     
#                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                    True
                else :
                    if vm_defaults["docker_repo"] == "https://hub.docker.com/r/" and _imageid == "ibmcb/ubuntu_cb_nullworkload" :
                        if _imageid not in _registered_imageid_list :
                            _registered_imageid_list.append(_imageid)                        
#                    if check_url(vm_defaults["docker_repo"] + '/' + _imageid) :                    
#                        _map_name_to_id[_imageid] = "aaaa0" + ''.join(["%s" % randint(0, 9) for num in range(0, 59)])
#                        vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
#                        _registered_imageid_list.append(_map_name_to_id[_imageid])

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_id_to_name)

        if not _detected_imageids :
            return _detected_imageids

        return _detected_imageids

    @trace
    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        for _host in pykube.Node.objects(self.kubeconn) :

            _host_info = _host.metadata
    
            _host_uuid = self.generate_random_uuid(_host_info["uid"])
    
            obj_attr_list["hosts"] += _host_uuid + ','            
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"].upper()
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            
            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], \
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_host_info["name"], True)
                
            obj_attr_list["host_list"][_host_uuid]["name"] = "host_"  + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["cloud_vm_uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
            obj_attr_list["host_list"][_host_uuid]["function"] = "hypervisor"
            obj_attr_list["host_list"][_host_uuid]["cores"] = "NA"
            obj_attr_list["host_list"][_host_uuid]["memory"] = "NA"
            obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
            obj_attr_list["host_list"][_host_uuid]["simulated"] = False
            obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]
    
            obj_attr_list["host_list"][_host_uuid]["hypervisor_type"] = "docker"
                                                
            if "login" in obj_attr_list :
                obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["login"]
            else :
                obj_attr_list["host_list"][_host_uuid]["login"] = "root"
                
            obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
            obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
            obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
            _time_mark_prc = int(time())
            obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start
                
        obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

        self.additional_host_discovery (obj_attr_list)

        return True

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            
            for _abstraction_type in [ "service", "deployment", "replicaset", "pod" ] :
                for _item in pykube.objects.Namespace.objects(self.kubeconn) :
                    _namespace = _item.name
                    _running_instances = True
        
                    while _running_instances and _curr_tries < _max_tries :
                        _running_instances = False
    
                        if _abstraction_type == "service" :
                            _object_list = pykube.objects.Service.objects(self.kubeconn).filter(namespace = _namespace)
    
                        if _abstraction_type == "deployment" :
                            _object_list = pykube.objects.Deployment.objects(self.kubeconn).filter(namespace = _namespace)
    
                        if _abstraction_type == "replicaset" :                        
                            _object_list = pykube.objects.ReplicaSet.objects(self.kubeconn).filter(namespace = _namespace)
    
                        if _abstraction_type == "pod" :                        
                            _object_list = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = _namespace)
                            
                        for _object in _object_list :
        
                            _object_name = str(_object.name)
                            
                            if _object_name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower()) :
        
                                _running_instances = True
                                _object_id = _object.obj["metadata"]["uid"]
                                _msg = "Terminating " + _abstraction_type + " : " 
                                _msg += _object_id + " (" + str(_object_name) + ")"
                                cbdebug(_msg, True)
                                
                                _object.delete()
                                    
                        sleep(_wait)
        
                        _curr_tries += 1

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "Some instances on VMC \"" + obj_attr_list["name"] + "\""
                _fmsg += " could not be removed because they never became active"
                _fmsg += ". They will have to be removed manually."
                cberr(_msg, True)
            else :
                _status = 0

            self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')

            _msg = "Ok"
            _status = 0
                        
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "cleaned up", _status, _fmsg)
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
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])            

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]

            obj_attr_list["cloud_hostname"], obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["name"], False)

            obj_attr_list["cloud_vm_uuid"] = self.generate_random_uuid(obj_attr_list["name"])

            obj_attr_list["arrival"] = int(time())
            
            if str(obj_attr_list["discover_hosts"]).lower() == "true" :
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            obj_attr_list["network_detected"] = "flannel"
            _container_list = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = "kube-system")
            for _container in _container_list :
                if _container.name.count("calico") :
                    obj_attr_list["network_detected"] = "calico"
            
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = \
            _time_mark_prc - _time_mark_prs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "registered", _status, _fmsg)
            return _status, _msg

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

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])    
        
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
            _status, _msg = self.common_messages("VMC", obj_attr_list, "unregistered", _status, _fmsg)
            return _status, _msg

    @trace 
    def vmcount(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"                        
            _nr_instances = 0

            for _vmc_uuid in self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC") :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                      "VMC", False, _vmc_uuid, \
                                                      False)
                
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             _vmc_attr_list["name"], obj_attr_list)

                _container_list = pykube.objects.Pod.objects(self.kubeconn).filter()
                for _container in _container_list :
                    if _container.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower()) :
                        _nr_instances += 1

        except Exception, e :
            _status = 23
            _nr_instances = "NA"
            _fmsg = str(e)

        finally :
            return _nr_instances

    @trace
    def get_ssh_keys(self, key_name, key_contents, key_fingerprint, registered_key_pairs, internal, connection) :
        '''
        TBD
        '''

        registered_key_pairs[key_name] = key_fingerprint + "-NA"

        return True

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''             
        _networks = [  obj_attr_list["netname"] ]
                
        if len(_networks) :

            if "podIP" in self.instance_info["status"] :
                _address = self.instance_info["status"]["podIP"]

                obj_attr_list["run_cloud_ip"] = _address

                if str(obj_attr_list["ports_base"]).lower() != "false" :
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["host_cloud_ip"]
                else :
                    obj_attr_list["prov_cloud_ip"] = obj_attr_list["run_cloud_ip"]

                # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
                obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
                
                obj_attr_list["cloud_mac"] = "NA"
                
                return True
            else :
                return False
        else :
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "pod", identifier = "all") :
        '''
        TBD
        '''

        _instances = False
        _fmsg = "Error while getting instances"
        _call = "NA"

        try :

            if obj_type == "pod" :
                _call = "containers()"
                if identifier == "all" :
                    _instances = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"])
                                                                   
                else :
                    
                    if "cloud_vm_exact_match_name" in obj_attr_list :
                        identifier = obj_attr_list["cloud_vm_exact_match_name"]
                        _instances = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"metadata.name": identifier})

                    elif "selector" in obj_attr_list :
                        _selector = str2dic(obj_attr_list["selector"])
                        _instances = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                          selector= _selector)

                    else :
                        _instances = pykube.objects.Pod.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"metadata.name": identifier})


            elif obj_type == "replicaset" :
                if identifier == "all" :
                    _instances = pykube.objects.ReplicaSet.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"])
                else :
                    if "cloud_rs_exact_match_name" in obj_attr_list  :
                        identifier = obj_attr_list["cloud_rs_exact_match_name"]
                        _instances = pykube.objects.ReplicaSet.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"metadata.name": identifier})
                                                
                    elif "selector" in obj_attr_list :
                        _selector = str2dic(obj_attr_list["selector"])
                        _instances = pykube.objects.ReplicaSet.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                             selector= _selector)

                    else :
                        _instances = pykube.objects.ReplicaSet.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"metadata.name": identifier})
                        
            elif obj_type == "deployment" :
                if identifier == "all" :
                    _instances = pykube.objects.Deployment.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"])
                else :
                    if "selector" in obj_attr_list :
                        _selector = str2dic(obj_attr_list["selector"])
                        _instances = pykube.objects.Deployment.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      selector= _selector)
            
            elif obj_type == "service" :
                if identifier == "all" :
                    _instances = pykube.Service.objects(self.kubeconn).filter(namespace=obj_attr_list["namespace"])
                else :
                    _instances = pykube.Service.objects(self.kubeconn).filter(namespace=obj_attr_list["namespace"], \
                                                                              field_selector={"metadata.name": identifier})                    
            else :
                _call = "volumes()"                    
                if identifier == "all" :
                    True 
                else :
                    True
                        
            if _instances :
                for _x in _instances :
                    _instances = _x

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _xfmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _xfmsg = str(e)
            
        finally :
            if _status :
                _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + _xfmsg
                if identifier not in self.api_error_counter :
                    self.api_error_counter[identifier] = 0
                
                self.api_error_counter[identifier] += 1
                
                if self.api_error_counter[identifier] > self.max_api_errors :            
                    raise CldOpsException(_fmsg, _status)
                else :
                    cbwarn(_fmsg)
                    return []
            else :
                return _instances

    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = [ obj_attr_list["imageid1"] ]

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg +=  self.get_description()

            _candidate_images = []

            for _image in _image_list :
                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
#                    if _image["Id"].split(':')[1] == obj_attr_list["imageid1"] :
                    _candidate_images.append(obj_attr_list["imageid1"])
                else :
                    if _image.count(obj_attr_list["imageid1"]) :
                        _candidate_images.append(obj_attr_list["imageid1"])                        

            if len(_candidate_images) :
                obj_attr_list["boot_volume_imageid1"] = "TBD" 
                _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ") not found: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace
    def get_networks(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Network (" +  obj_attr_list["prov_netname"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace            
    def create_ssh_key(self, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''

        return True
    
        if len(imageid) == 64 and is_number(imageid, True) :
            return True
        
        return False

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :

            _instance = self.get_instances(obj_attr_list, "pod", obj_attr_list["cloud_vm_name"])

            _instance_status = False
            if _instance :
                if "status" in _instance.obj :
                    if "containerStatuses" in _instance.obj["status"] :
                        if "state" in _instance.obj["status"]["containerStatuses"][0] : 
                            _instance_status = _instance.obj["status"]["containerStatuses"][0]["state"].keys()[0]
            
            if str(_instance_status) == "running" :
                self.instance_info = _instance.obj
                obj_attr_list["cloud_vm_exact_match_name"] = _instance.name
                obj_attr_list["cloud_vm_name"] = _instance.name
                obj_attr_list["cloud_hostname"] = _instance.name
                
                if "hostIP" in self.instance_info["status"] :
                    _host_ip = self.instance_info["status"]["hostIP"]
                    obj_attr_list["host_name"], obj_attr_list["host_cloud_ip"] = hostname2ip(_host_ip, True)     

                if obj_attr_list["abstraction"] == "replicaset" or obj_attr_list["abstraction"] == "deployment" :
                    if "cloud_rs_exact_match_name" not in obj_attr_list :
                        _x_instance = self.get_instances(obj_attr_list, "replicaset", obj_attr_list["cloud_rs_name"])
                        if _x_instance :
                            obj_attr_list["cloud_rs_exact_match_name"] = _x_instance.name
                            obj_attr_list["cloud_rs_name"] = _x_instance.name

                            if "metadata" in _x_instance.obj :
                                if "uid" in _x_instance.obj["metadata"] :                        
                                    obj_attr_list["cloud_rs_uuid"] = _x_instance.obj["metadata"]["uid"]
                                                 
                if obj_attr_list["abstraction"] == "deployment" :
                    if "cloud_d_exact_match_name" not in obj_attr_list :
                        _x_instance = self.get_instances(obj_attr_list, "deployment", obj_attr_list["cloud_d_name"])
                        if _x_instance :                        
                            obj_attr_list["cloud_d_exact_match_name"] = _x_instance.name
                            obj_attr_list["cloud_d_name"] = _x_instance.name

                            if "metadata" in _x_instance.obj :
                                if "uid" in _x_instance.obj["metadata"] :           
                                    obj_attr_list["cloud_d_uuid"] = _x_instance.obj["metadata"]["uid"]
                            
                return True
            else :
                return False
        
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace    
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''        
        if self.is_vm_running(obj_attr_list) :

            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                                                            
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
            return False

    @trace        
    def vm_placement(self, obj_attr_list) :
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
                _msg = "VM placement failed: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return True

    @trace
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if "cloud_vv_type" not in obj_attr_list :
                obj_attr_list["cloud_vv_type"] = "NOT SUPPORTED"

            if "cloud_vv" in obj_attr_list :

                obj_attr_list["last_known_state"] = "about to send volume create request"
    
                obj_attr_list["cloud_vv_uuid"] = "NOT SUPPORTED"

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace        
    def vvdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "not supported" and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :    
                self.common_messages("VV", obj_attr_list, "destroying", 0, '')
                                
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :                
            _status, _msg = self.common_messages("VV", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg
    
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.determine_instance_name(obj_attr_list)
            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].lower()
            obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].lower()
            obj_attr_list["cloud_rs_name"] = obj_attr_list["cloud_vm_name"]
            obj_attr_list["cloud_d_name"] = obj_attr_list["cloud_vm_name"]
            obj_attr_list["cloud_rs_uuid"] = "NA"
            obj_attr_list["cloud_d_uuid"] = "NA"
                                                
            self.determine_key_name(obj_attr_list)

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            _mark_a = time()
            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])
            self.annotate_time_breakdown(obj_attr_list, "authenticate_time", _mark_a)

            _mark_a = time()
            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)    
            self.annotate_time_breakdown(obj_attr_list, "check_existing_instance_time", _mark_a)
                        
            _env = [  
                       { "name": "CB_SSH_PUB_KEY", \
                         "value" : obj_attr_list["pubkey_contents"]
                       },\
                       { "name": "CB_LOGIN", \
                         "value" : obj_attr_list["login"]
                       } 
                   ]

            if str(obj_attr_list["ports_base"]).lower() != "false" :
                obj_attr_list["prov_cloud_port"] = int(obj_attr_list["ports_base"]) + int(obj_attr_list["name"].replace("vm_",''))

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])

            _annotations = { "creator" : "cbtool" }
            if len(obj_attr_list["annotations"]) > 2 :
                _annotations = str2dic(obj_attr_list["annotations"])

                if "override_imageid1" in _annotations :
                    obj_attr_list["imageid1"] = _annotations["override_imageid1"]
            
            if obj_attr_list["abstraction"] == "pod" :
                _obj = { "apiVersion": "v1", \
                         "kind": "Pod", \
                         "id":  obj_attr_list["cloud_vm_name"], \
                         "metadata": { "name":  obj_attr_list["cloud_vm_name"], \
                                       "namespace": obj_attr_list["namespace"] , \
                                       "labels" : { "creator" : "cbtool", \
                                                    "app" :  obj_attr_list["cloud_vm_name"] 
                                                  }, \
                                        "annotations" : _annotations
                                      }, \
                         "spec": { "containers":
                                     [ 
                                        { "env": _env, \
                                           "name": obj_attr_list["cloud_vm_name"], \
                                           "image": obj_attr_list["imageid1"]
                                        }
                                     ]
                                 }
                       }

            if obj_attr_list["abstraction"] == "replicaset" :
                _obj = { "apiVersion": "extensions/v1beta1", \
                         "kind": "ReplicaSet", \
                         "id": obj_attr_list["cloud_rs_name"], \
                         "metadata": { "name": obj_attr_list["cloud_rs_name"], \
                                       "namespace": obj_attr_list["namespace"] 
                                     }, \
                         "spec": { "replicas": int(obj_attr_list["replicas"]), \
                                   "template": {
                                                "metadata": { "labels": { "app": obj_attr_list["cloud_vm_name"], \
                                                                          "role": "master", \
                                                                          "tier": "backend", \
                                                                          "creator" : "cbtool" 
                                                                        } 
                                                             },\
                                                "spec": { "containers":
                                                            [ 
                                                               { "env": _env, \
                                                                 "name": obj_attr_list["cloud_vm_name"], \
                                                                 "image": obj_attr_list["imageid1"] 
                                                               } 
                                                            ] 
                                                        }
                                               }
                                  } 
    
                        }
                obj_attr_list["selector"] = "app:" + obj_attr_list["cloud_rs_name"] + ',' + "role:master,tier:backend" 

            if obj_attr_list["abstraction"] == "deployment" :
                _obj = { "apiVersion": "extensions/v1beta1", \
                         "kind": "Deployment", \
                         "id": obj_attr_list["cloud_d_name"], \
                         "metadata": { "name": obj_attr_list["cloud_d_name"], \
                                       "namespace": obj_attr_list["namespace"]
                                     }, \
                         "spec": { "replicas": int(obj_attr_list["replicas"]), \
                                   "template": {
                                                "metadata": { "labels": { "app": obj_attr_list["cloud_vm_name"], \
                                                                          "role": "master", \
                                                                          "tier": "backend", \
                                                                          "creator":  "cbtool"
                                                                        } 
                                                             },\
                                                "spec": { "containers": \
                                                            [ 
                                                               { "env": _env, \
                                                                 "name": obj_attr_list["cloud_vm_name"], \
                                                                 "image": obj_attr_list["imageid1"] 
                                                               } 
                                                            ] 
                                                        }
                                               }
                                  } 
    
                        }

                obj_attr_list["selector"] = "app:" + obj_attr_list["cloud_d_name"] + ',' + "role:master,tier:backend" 
                        
            self.vm_placement(obj_attr_list)

            _cpu, _memory = obj_attr_list["size"].split('-')

            if "userdata" not in obj_attr_list :
                obj_attr_list["userdata"] = "auto"
                
            if obj_attr_list["userdata"] != "none" :
                obj_attr_list["config_drive"] = True
            else :
                obj_attr_list["config_drive"] = False
                        
            _time_mark_prs = int(time())            
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)
            self.pre_vmcreate_process(obj_attr_list)            
            self.vvcreate(obj_attr_list)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')
            
            _mark_a = time()
            if obj_attr_list["abstraction"] == "pod" :
                pykube.Pod(self.kubeconn, _obj).create()
            if obj_attr_list["abstraction"] == "replicaset" :
                pykube.ReplicaSet(self.kubeconn, _obj).create()
            if obj_attr_list["abstraction"] == "deployment" :
                pykube.Deployment(self.kubeconn, _obj).create()
                                                
            self.annotate_time_breakdown(obj_attr_list, "instance_scheduling_time", _mark_a)
                                    
            self.take_action_if_requested("VM", obj_attr_list, "provision_started")

            _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

            if str(obj_attr_list["ports_base"]).lower() != "false" and str(obj_attr_list["check_boot_complete"]).lower() != "wait_for_0" :

                if obj_attr_list["abstraction"] == "pod" :
                    _actual_app_name = obj_attr_list["cloud_vm_name"]

                if obj_attr_list["abstraction"] == "replicaset" :
                    _actual_app_name = obj_attr_list["cloud_rs_name"]

                if obj_attr_list["abstraction"] == "deployment" :
                    _actual_app_name = obj_attr_list["cloud_d_name"]
                
                _obj = { "kind": "Service", \
                                 "apiVersion": "v1", \
                                 "metadata": { "name":  obj_attr_list["cloud_vm_name"] }, \
                                 "spec": { 
                                          "selector": { "creator" : "cbtool", "app" : _actual_app_name }, \
                                          "ports": [ { "name": "ssh", "protocol": "TCP", "port": obj_attr_list["prov_cloud_port"], "targetPort": int(obj_attr_list["run_cloud_port"]) } ], \
                                          "externalIPs": [ obj_attr_list["prov_cloud_ip"] ]
                                          }
                                }
        
                pykube.Service(self.kubeconn, _obj).create()

            self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
            
            obj_attr_list["arrival"] = int(time())

            _status = 0

            if obj_attr_list["force_failure"].lower() == "true" :
                _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                _status = 916

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
            self.get_extended_info(obj_attr_list)
            
            if "mgt_004_network_acessible" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_reachable_time", obj_attr_list["mgt_004_network_acessible"], False)
                   
            _status, _msg = self.common_messages("VM", obj_attr_list, "created", _status, _fmsg)
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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])
            
            _wait = int(obj_attr_list["update_frequency"])
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0
                
            _p_instance = self.get_instances(obj_attr_list, "pod", obj_attr_list["cloud_vm_name"])
                
            if _p_instance :
                self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                _s_instance = self.get_instances(obj_attr_list, "service", obj_attr_list["cloud_vm_name"])

                if _s_instance :
                    _s_instance.delete()

                _d_instance = self.get_instances(obj_attr_list, "deployment", obj_attr_list["cloud_vm_name"])
    
                if _d_instance :
                    _d_instance.delete()
    
                _r_instance = self.get_instances(obj_attr_list, "replicaset", obj_attr_list["cloud_vm_name"])
    
                if _r_instance :
                    _r_instance.delete()
                                    
                _p_instance.delete()

            while _p_instance and _curr_tries < _max_tries :
                _p_instance = self.get_instances(obj_attr_list, "pod", obj_attr_list["cloud_vm_name"])                
                sleep(_wait)
                _curr_tries += 1                

            if "cloud_vv" in obj_attr_list :
                self.vvdestroy(obj_attr_list)
                
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace        
    def vmcapture(self, obj_attr_list) :            
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"

    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]
    
            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _instance = self.get_instances(obj_attr_list, "pod", obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    True
#                    self.dockconn[_host_ip].pause(obj_attr_list["cloud_vm_uuid"])
                elif _ts == "save" :
                    True
#                    self.dockconn[_host_ip].stop(obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    True
#                    self.dockconn[_host_ip].unpause(obj_attr_list["cloud_vm_uuid"])
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    True
#                    self.dockconn[_host_ip].start(obj_attr_list["cloud_vm_uuid"])
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs
                        
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "runstate altered", _status, _fmsg)
            return _status, _msg
        
    @trace
    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"

    @trace
    def vmresize(self, obj_attr_list) :
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"
        
    @trace
    def imgdelete(self, obj_attr_list) :
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"

    @trace
    def get_extended_info(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _pattern = "%Y-%m-%dT%H:%M:%SZ"

            if self.instance_info :
                                            
                if "metadata" in self.instance_info :
                    if "resourceVersion" in self.instance_info["metadata"] :
                        obj_attr_list["cloud_resource_version"] = self.instance_info["metadata"]["resourceVersion"]

                    if "uid" in self.instance_info["metadata"] :                        
                        obj_attr_list["cloud_vm_uuid"] = self.instance_info["metadata"]["uid"]
                                
                    if "creationTimestamp" in self.instance_info["metadata"] and "cloud_vm_creation_timestamp" not in obj_attr_list :
                        obj_attr_list["cloud_vm_creation_timestamp"] = int(mktime(strptime(self.instance_info["metadata"]["creationTimestamp"], _pattern)))                       

                _mark_a = int(obj_attr_list["cloud_vm_creation_timestamp"])

                if obj_attr_list["abstraction"] == "deployment" :
                    for _event in pykube.objects.Event.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"involvedObject.name": obj_attr_list["cloud_d_name"]}) :
                        _event_info = _event.obj

                        #if _epoch > obj_attr_list["mgt_001_provisioning_request_originated"] :
                                                
                        if _event_info["involvedObject"]["uid"] == obj_attr_list["cloud_d_uuid"] :

                            _epoch = int(mktime(strptime(_event_info["firstTimestamp"], _pattern)))
                            
                            if _epoch < _mark_a :
                                _mark_a = _epoch
                                obj_attr_list["cloud_vm_creation_timestamp"] = _epoch
                                                        
                            self.annotate_time_breakdown(obj_attr_list, "instance_" + _event_info["reason"].lower() + "_time", _epoch - _mark_a, False)
                            _mark_a = _epoch

                if obj_attr_list["abstraction"] == "replicaset" or obj_attr_list["abstraction"] == "deployment" :
                    for _event in pykube.objects.Event.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"involvedObject.name": obj_attr_list["cloud_rs_name"]}) :
                        _event_info = _event.obj
                        
                        #if _epoch > obj_attr_list["mgt_001_provisioning_request_originated"] :
                        
                        if _event_info["involvedObject"]["uid"] == obj_attr_list["cloud_rs_uuid"] :

                            _epoch = int(mktime(strptime(_event_info["firstTimestamp"], _pattern)))
                            
                            if _epoch < _mark_a :
                                _mark_a = _epoch
                                obj_attr_list["cloud_vm_creation_timestamp"] = _epoch
                                                        
                            self.annotate_time_breakdown(obj_attr_list, "instance_" + _event_info["reason"].lower() + "_time", _epoch - _mark_a, False)
                            _mark_a = _epoch

                for _event in pykube.objects.Event.objects(self.kubeconn).filter(namespace = obj_attr_list["namespace"], \
                                                                                      field_selector={"involvedObject.name": obj_attr_list["cloud_vm_name"]}) :
                    _event_info = _event.obj
                    
                    if _event_info["involvedObject"]["uid"] == obj_attr_list["cloud_vm_uuid"] :
                                                
                        _epoch = int(mktime(strptime(_event_info["firstTimestamp"], _pattern)))
                        self.annotate_time_breakdown(obj_attr_list, "instance_" + _event_info["reason"].lower() + "_time", _epoch - _mark_a, False)
                        _mark_a = _epoch
                
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            return True