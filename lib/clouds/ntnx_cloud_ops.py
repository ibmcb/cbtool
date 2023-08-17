#!/usr/bin/env python3
#/*******************************************************************************
# Copyright (c) 2023 Telecommunications Technology Association (TTA)

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
    Created on Jun 23, 2023

    Nutanix Object Operations Library

    @author: Hyo-Sil Kim
'''
from time import time, sleep
from uuid import uuid5, UUID
from random import choice
from os import access, F_OK
from os.path import expanduser

import socket
import copy
import iso8601

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

from ntnx_api import prism
from ntnx_api.client import PrismApi

import traceback

class NtnxCmds(CommonCloudFunctions) :
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
        self.ntnxclusters = {} # prism.Cluster
        self.ntnxconnvm = {} # prism.VMs
        self.ntnxconnimage = {} # prism.Images
        self.ntnxconnnetwork = {} # prism.Networks
        self.expid = expid
        self.ft_supported = False
        self.lvirt_conn = {}
        self.networks_attr_list = { "tenant_network_list":[] }
        self.host_map = {}
        self.api_error_counter = {}
        self.additional_rc_contents = ''
        self.max_api_errors = 10
        
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Nutanix Cloud"
        
    @trace
    def connect(self, access_url, authentication_data, region = "RegionOne") :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _dmsg = ''

            
            _separator = '-'
            _username = "default"
            _password = "default"
            _tenant = "default"

    
            if len(authentication_data.split(_separator)) != 3 :
                _msg = "ERROR: Insufficient number of parameters in NTNX_CREDENTIALS."
                _msg += "Please make sure that at least username, password and tenant"
                _msg += " are present."
                _status = -1
            else :
                _username, _password, _tenant = authentication_data.split(_separator)
 
            if not _username :
                _fmsg = _password
            else :
                _ntnx_api = PrismApi(
                        ip_address=access_url,
                        username=_username,
                        password=_password)

                # connect to Nutanix Cluster 
                self.ntnxclusters = prism.Cluster(api_client=_ntnx_api)
                _msg = self.get_description() + " connection parameters: username=" + str(_username)
                _msg += ", password=<omitted>, tenant=" + str(_tenant) + ", "
                _msg += ", region_name=" + str(region) + ", access_url=" + str(access_url)
                cbdebug(_msg, True)
    
                _fmsg = "About to attempt a connection to " + self.get_description()

                # connect to Nutanix Network manger
                self.ntnxconnnetwork = prism.Network(api_client=_ntnx_api)

                # connect to Nutanix Image manager
                self.ntnxconnimage = prism.Images(api_client=_ntnx_api)
 
                # connect to Nutanix VM manager
                self.ntnxconnvm = prism.Vms(api_client=_ntnx_api)

                
                _region = region
                _msg = "Selected region is " + str(region)
                #cbdebug(_msg)
                cbdebug(_msg)
                _status = 0


        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " connection failure: " + _fmsg + "url:" + str(access_url) + "username:" + str(_username) + "password:" + str(_password)
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, _region

    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults, False, vmc_name)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _detected_imageids = self.check_images(vmc_name, vm_templates, vm_defaults)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                _msg = "Check the previous errors, fix it"
                _status = 1178
                cberr(_msg)
                raise CldOpsException(_msg, _status) 

            if len(_detected_imageids) :
                _status = 0               
            else :
                _status = 1

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
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

        _net_str = "network \"" + _prov_netname + "\""
        _msg = "Checking if the " + _net_str + " can be found on VMC " + vmc_name + "..."
        cbdebug(_msg, True)
                        
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
        _map_uuid_to_name = {}
        _map_id_to_name = {}
        
        _registered_image_list = self.ntnxconnimage.get(self.ntnxclusters.get_all_uuids()[0])
        _registered_imageid_list = []
            
        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image['uuid'])
            _map_name_to_id[_registered_image['name']] = _registered_image['uuid']
                
        for _vm_role in list(vm_templates.keys()) :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]                
            if _imageid != "to_replace" :
                if _imageid in _map_name_to_id and _map_name_to_id[_imageid] != _imageid :
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                else :
                    _map_name_to_id[_imageid] = _imageid
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])   

                _map_id_to_name[_map_name_to_id[_imageid]] = _imageid

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_id_to_name, vm_defaults)
        
        return _detected_imageids


    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''

        _host_uuid = obj_attr_list["cloud_vm_uuid"]

        obj_attr_list["host_list"] = {}
        obj_attr_list["hosts"] = ''

        obj_attr_list["initial_hosts"] = ''.split(',')
        obj_attr_list["host_count"] = len(obj_attr_list["initial_hosts"])
    
        return True

        
    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"])

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _running_instances = True
            
            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False
                
                _vmc_name = obj_attr_list["name"]
                _instances = self.ntnxconnvm.get(self.ntnxclusters.get_all_uuids()[0])
                
                for _instance in _instances :
                    if _instance['name'].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) \
                    and not _instance['name'].count("jumphost") :
                                                                        
                        _running_instances = True
                        if  _instance['power_state'] == "on" :
                            _msg = "Terminating instance: " 
                            _msg += _instance['uuid'] + " (" + _instance['name'] + ")"
                            cbdebug(_msg, True)

                            self.retriable_instance_delete(obj_attr_list, _instance) 

                        else :
                            _msg = "Will wait for instance "
                            _msg += _instance['uuid'] + "\"" 
                            _msg += " (" + _instance['name'] + ") to "
                            _msg += "start and then destroy it."
                            cbdebug(_msg, True)
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


        except CldOpsException as obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)

        except Exception as e :
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
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])
            
            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            if not _status :
                _x, _y, _hostname = self.connect(obj_attr_list["access"], \
                                                 obj_attr_list["credentials"], \
                                                 obj_attr_list["name"])

                obj_attr_list["cloud_hostname"] = _hostname

                _x, obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list['access'], True)
                obj_attr_list["arrival"] = int(time())

                if str(obj_attr_list["discover_hosts"]).lower() == "true" :                   
                    self.discover_hosts(obj_attr_list, _time_mark_prs)
                else :
                    obj_attr_list["hosts"] = ''
                    obj_attr_list["host_list"] = {}
                    obj_attr_list["host_count"] = "NA"

                _time_mark_prc = int(time())

                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
                _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
                        
        except Exception as e :
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

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VMC", obj_attr_list, "unregistered", _status, _fmsg)
            return _status, _msg
 
    @trace
    def vmcount(self, obj_attr_list):
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
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"],_vmc_attr_list["name"])

                _instances = self.ntnxconnvm.get(self.ntnxclusters.get_all_uuids()[0])
                
                for _instance in _instances :                    
                    if _instance['name'].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) \
                    and not _instance['name'].count("jumphost") :
                        if _instance['power_state'] == "on" :
                            _nr_instances += 1

        except Exception as e :
            _status = 23
            _nr_instances = "NA"
            _fmsg = "(While counting instance(s) through API call \"list\") " + str(e)

        finally :
            return _nr_instances


    @trace
    def get_ssh_keys(self, vmc_name, key_name, key_contents, key_fingerprint, registered_key_pairs, internal, connection) :
        '''
        TBD
        '''

        registered_key_pairs[key_name] = key_fingerprint + "-NA"

        return True



    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        _networks = dict(instance['vm_nics'][0])

        if len(_networks) :
            obj_attr_list['run_cloud_ip'] = '{0}'.format(_networks['ip_address'])
            if "run_cloud_ip" in obj_attr_list : 
                _msg = "Network \"" + obj_attr_list["run_cloud_ip"] + "\" found."
                cbdebug(_msg)
                obj_attr_list['cloud_ip'] = '{0}'.format(_networks['ip_address'])
            else :
                return False
   
            if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
            elif obj_attr_list["hostname_key"] == "cloud_ip" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')
    
            if obj_attr_list["prov_netname"] == obj_attr_list["run_netname"] :
                obj_attr_list["prov_cloud_ip"] = obj_attr_list["run_cloud_ip"]
                return True

        else :
            _status = 1181
            _msg = "IP address list for network " + str(_networks) + " is empty."
            cberr(_msg)
            raise CldOpsException(_msg, _status)                
            return False



    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all", force_list = False) :
        '''
        TBD
        '''
        try :
            _call = "NA"
            
        #    self.connect(obj_attr_list["access"], \
        #                obj_attr_list["credentials"], \
        #                obj_attr_list["vmc_name"])
            if obj_type == "vm" :
                                
                if "cloud_vm_uuid" in obj_attr_list and len(obj_attr_list["cloud_vm_uuid"]) >= 36 and not force_list :
                    _call = "get"
                    _instance = self.ntnxconnvm.search_name(identifier, \
                            clusteruuid = self.ntnxclusters.get_all_uuids()[0])
                    return _instance

                else :
                    _call = "list"
                    _instances = self.ntnxconnvm.get(self.ntnxclusters.get_all_uuids()[0])
                    if len(_instances) > 0 :

                        if identifier == "all" :   
                            return _instances
                    else :
                        return False
            else :
                return False

        except Exception as e :
            _status = 23
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(e) + ", identifer=" + str(identifier) + ", obj_attr_list[\"name\"]=" + obj_attr_list["name"]
            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                cbwarn(_fmsg)
                return False

    
    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _vmc_name = obj_attr_list["name"]
            _image_list = self.ntnxconnimage.get(self.ntnxclusters.get_all_uuids()[0])

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += self.get_description()

            _imageid = False

            _candidate_images = []
            
            for _image in _image_list :
                if _image['uuid'] == obj_attr_list["imageid1"] :
                    _candidate_images.append(_image)

            if len(_candidate_images) :
                if  str(obj_attr_list["randomize_image_name"]).lower() == "true" :
                    _imageid = choice(_candidate_images)
                else :
                    _imageid = _candidate_images[0]

                if _imageid :
                    obj_attr_list["boot_volume_imageid1"] = _imageid['uuid']
                    obj_attr_list["imageid1"] = _imageid['name']
                    obj_attr_list["boot_volume_imageid1_instance"] = _imageid
                
                _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ' ' + _hyper + ") not found: " + _fmsg
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
            _fmsg = "An error has occurred, but no error message was captured"

            _netids = []
            _netnames = []
            
            _netlist = obj_attr_list["prov_netname"].split(',') + obj_attr_list["run_netname"].split(',')
                                    
            for _netname in _netlist :  

                if "HA network tenant" in _netname :
                    continue
 
                if not _netname in self.networks_attr_list :
                    _status = 168
                    _fmsg = "Please check if the defined network is present on this "
                    _fmsg += self.get_description()
                    
                    if "name" in obj_attr_list :
                        _conn_id = obj_attr_list["name"]
                    else :
                        _conn_id = "common"
                        
                    self.get_network_list(_conn_id, obj_attr_list)
                
                if _netname in self.networks_attr_list :
                    _networkid = self.networks_attr_list[_netname]["uuid"]
                    
                    _net_info = {"net-id" : _networkid}
                    if not _net_info in _netids :
                        _netids.append(_net_info)
                        _netnames.append(_netname)
                                                
                    _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Network (" +  obj_attr_list["prov_netname"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _netnames = ','.join(_netnames)                
                return _netnames, _netids

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''        
        if len(imageid) == 36 and imageid.count('-') == 4 :
            return True
        
        return False
    
    @trace
    def is_vm_running(self, obj_attr_list, fail = True):
        '''
        TBD
        '''
        try :
            
            _cloud_vm_name = obj_attr_list["cloud_vm_name"]
            
            _instance = self.get_instances(obj_attr_list, "vm", \
                                           _cloud_vm_name)
            if _instance :
                if _instance['power_state'] == "on" : # on
                    return _instance

                else : # off, suspended or else
                    return False
            else :
                return False

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

        
    @trace    
    def is_vm_ready(self, obj_attr_list) :

        _instance = self.is_vm_running(obj_attr_list)


        if _instance: # on state

            obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"

            if self.get_ip_address(obj_attr_list, _instance) :
                obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
            return True

        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            return False


       
    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        
        try :                        
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _instance = False

            self.determine_instance_name(obj_attr_list)            
            self.determine_key_name(obj_attr_list)
            
            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"
            
            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            # KEEP IT HERE TOO, NEEDS TO BE DUPLICATED, DO NOT REMOVE                    
            self.determine_key_name(obj_attr_list)

            if obj_attr_list["tenant"] != "default" :
                if "ssh_key_injected" not in obj_attr_list :
                    self.check_ssh_key(obj_attr_list["vmc_name"], \
                                       obj_attr_list["key_name"], \
                                       obj_attr_list, True)

                if "user" not in obj_attr_list :
                    obj_attr_list["user"] = obj_attr_list["tenant"] 

                obj_attr_list["admin_credentials"] = obj_attr_list["credentials"]                  
                obj_attr_list["credentials"] = obj_attr_list["credentials"]
                #if obj_attr_list["name"] in self.ntnxconnvm :
                #    del self.ntnxconnvm[obj_attr_list["name"]]

            _mark_a = time()
            if not self.ntnxclusters:
                self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"])
            
            self.annotate_time_breakdown(obj_attr_list, "authenticate_time", _mark_a)

            _mark_a = time()
            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            self.annotate_time_breakdown(obj_attr_list, "check_existing_instance_time", _mark_a)
                    
            obj_attr_list["last_known_state"] = "about to get flavor and image list"

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            _mark_a = time()
            self.get_images(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_imageid_time", _mark_a)

            obj_attr_list["userdata"] = self.populate_cloudconfig(obj_attr_list)
            if obj_attr_list["userdata"] :
                obj_attr_list["config_drive"] = True                
            else :
                obj_attr_list["config_drive"] = None

            _mark_a = time()
            _netnames, _netids = self.get_networks(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_netid_time", _mark_a)

            _meta = {}
            if "meta_tags" in obj_attr_list :
                if obj_attr_list["meta_tags"] != "empty" and \
                obj_attr_list["meta_tags"].count(':') and \
                obj_attr_list["meta_tags"].count(',') :
                    _meta = str2dic(obj_attr_list["meta_tags"])

            _meta["experiment_id"] = obj_attr_list["experiment_id"]

            _time_mark_prs = int(time())
            
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])


            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            self.pre_vmcreate_process(obj_attr_list)

            _mark_a = time()
            _flag = False
            _flag = self.ntnxconnvm.create( name = obj_attr_list["cloud_vm_name"], \
                                                            cores = 4,\
                                                            memory_gb = 4, \
                                                            storage_container_uuid = "443ef86d-48ac-487d-95bb-1df952995efd", \
                                                            disks = [ \
                                                                {'bus': 'scsi', 'size_gb': 40, 'image_name' : obj_attr_list["imageid1"],},], \
                                                           # timezone="KST", \
                                                            nics = [{'network_name': _netnames, 'ipam': True,},],  \
                                                            clusteruuid = self.ntnxclusters.get_all_uuids()[0], \
                                                            )  
            if _flag:

                self.annotate_time_breakdown(obj_attr_list, "instance_creation_time", _mark_a)
                                
                sleep(int(obj_attr_list["update_frequency"]))

                _instance_list = self.ntnxconnvm.get(self.ntnxclusters.get_all_uuids()[0])
                _instance = False
                for _c_instance in _instance_list :
                    if _c_instance['name'] == obj_attr_list["cloud_vm_name"] :
                        _instance = _c_instance

                if _instance : 
                    obj_attr_list["cloud_vm_uuid"] = _instance['uuid']
                    
                    self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                    _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
                
                    _mark_a = time()
                    self.annotate_time_breakdown(obj_attr_list, "instance_scheduling_time", _mark_a)
                    _mark_a = time()
                    self.annotate_time_breakdown(obj_attr_list, "port_creation_time", _mark_a)

                    _status = 0
                    
                    self.get_mac_address(obj_attr_list, _instance)

                    self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                    self.get_host_and_instance_name(obj_attr_list)
    
                    #if obj_attr_list["tenant"] != "default" :
                    #    del self.ntnxconnvm[obj_attr_list["name"]]

                    if "resource_limits" in obj_attr_list :
                        _status, _fmsg = self.set_cgroup(obj_attr_list)
                    else :
                        _status = 0

                    if str(obj_attr_list["force_failure"]).lower() == "true" :
                        _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                        _status = 916
                else :
                    _fmsg = "there is no such instance!"
                    _status = 1024

            else :
                _fmsg = "Failed to obtain instance's (cloud assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason." + str(obj_attr_list["cloud_vm_name"])
                cberr(_fmsg)
                _status = 100
                
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :           
            if "mgt_003_provisioning_request_completed" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_active_time", obj_attr_list["mgt_003_provisioning_request_completed"], False)
            
            if "mgt_004_network_acessible" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_reachable_time", obj_attr_list["mgt_004_network_acessible"], False)

            if "flavor_instance" in obj_attr_list :
                del obj_attr_list["flavor_instance"]

            if "boot_volume_imageid1_instance" in obj_attr_list :                
                del obj_attr_list["boot_volume_imageid1_instance"]

            if "availability_zone" in obj_attr_list :            
                obj_attr_list["availability_zone"] = str(obj_attr_list["availability_zone"])

            if "block_device_mapping" in obj_attr_list :            
                obj_attr_list["block_device_mapping"] = str(obj_attr_list["block_device_mapping"])

            if "cloud_vv_type" in obj_attr_list :            
                obj_attr_list["cloud_vv_type"] = str(obj_attr_list["cloud_vv_type"])

            _status, _msg = self.common_messages("VM", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg
 
    @trace
    def get_host_and_instance_name(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try : 
            _instance = self.is_vm_running(obj_attr_list, fail = fail)

            if _instance:
                obj_attr_list["instance_name"] = _instance["name"]
                obj_attr_list["host_name"] = _instance["host_uuid"]
            else :
                obj_attr_list["instance_name"] = "unknown"
                obj_attr_list["host_name"] = "unknown"
            _status = 0
        except :
            _status = 2000
            _msg = str(obj_attr_list)
            cberr(_msg)
            raise CldOpsException(_msg, _status)
        finally :
            if not _status:
                return True
            else :
                return False

            return True




    @trace        
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :

            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if int(obj_attr_list["instance_creation_status"]) :
                _status, _fmsg = self.instance_cleanup_on_failure(obj_attr_list)
            else :
                                
                _time_mark_drs = int(time())
                if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                    obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                    
                obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                    _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])
   
                if not self.ntnxclusters:
                    self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

                _wait = int(obj_attr_list["update_frequency"])
                _max_tries = int(obj_attr_list["update_attempts"])
                _curr_tries = 0

                _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"]) 
    
                if _instance :
    
                    self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                    self.retriable_instance_delete(obj_attr_list, _instance)
                    sleep(_wait)
    
                    while _instance and _curr_tries < _max_tries :
                        _instance = self.get_instances(obj_attr_list, "vm", \
                                               obj_attr_list["cloud_vm_name"])
                        if _instance :                            
                            if _instance['power_state'] != "on" :
                                break
                            
                        sleep(_wait)
                        _curr_tries += 1
                                                                    
                else :
                    True

                _status = 0
    
                _time_mark_drc = int(time())
                obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                    _time_mark_drc - _time_mark_drs

                    
                self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")
                        
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace
    def retriable_instance_delete(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        _identifier = ""
        _flag = False
        try :
            if "cloud_vm_name" in obj_attr_list :
                _identifier = obj_attr_list["cloud_vm_name"]
            else :
                _identifier = instance['name']

            _flag = self.ntnxconnvm.delete_name(name=_identifier, \
                    clusteruuid=self.ntnxclusters.get_all_uuids()[0])
            return _flag

        except Exception as e :
            _status = 23
            _fmsg = "(While removing instance(s) through API call \"delete\") "  + str(_identifier) + " in " + str(obj_attr_list["name"])  + str(_flag)
            if _identifier not in self.api_error_counter :
                self.api_error_counter[_identifier] = 0
            
            self.api_error_counter[_identifier] += 1
            
            if self.api_error_counter[_identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                return False

    @trace
    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        ''' 
        return 0, "NOT SUPPORTED"
       
    @trace        
    def vmcapture(self, obj_attr_list) :
        '''
        TBD
        '''
        return 0, "NOT SUPPORTED"

    @trace        
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''        
        return 0, "NOT SUPPORTED"
      

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
        try:
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            if not self.ntnxclusters:
               self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"])

            _image_list = self.ntnxconnimage.get(self.ntnxclusters.get_all_uuids()[0])
                
            for _image in _image_list :
                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                    if _image['uuid'] == obj_attr_list["imageid1"] :
                        self.ntnxconnimage.delete_uuid(obj_attr_list['imageid1'], self.ntnxclusters.get_all_uuids()[0])
                        break
                else : 
                    if _image['name'] == obj_attr_list["imageid1"] :
                        self.ntnxconnimage.delete_name(obj_attr_list['imageid1'], self.ntnxclusters.get_all_uuids()[0])
                        break

            obj_attr_list["boot_volume_imageid1"] = _image['uuid']
            obj_attr_list["imageid1"] = _image['name']

            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg

 
    @trace
    def get_network_attr(self, obj_attr_list, network_attr_list) :
        '''
        TBD
        '''
        _name = network_attr_list["name"]
        if "provider:network_type" in network_attr_list :
            _type = network_attr_list["provider:network_type"]
        else :
            _type = "NA"
        _uuid = network_attr_list["uuid"]
        
        if _type == "flat":
            _model = "flat"
        else :
            if "router:external" in network_attr_list :
                if network_attr_list["router:external"] :
                    _model = "external"
                else :
                    _model = "tenant"
            else :
                _model = "NA"

        self.networks_attr_list[_name] = {"uuid" : _uuid, "model" : _model, \
                                           "type" : _type }
        
        if _model == "tenant" :
            if _name not in self.networks_attr_list["tenant_network_list"] :
                self.networks_attr_list["tenant_network_list"].append(_name)
                        
        return True


    @trace    
    def get_network_list(self, vmc_name, obj_attr_list) :
        '''
        TBD
        '''
        _network_list = self.ntnxconnnetwork.get(self.ntnxclusters.get_all_uuids()[0])

        for _network_attr_list in _network_list :
            self.get_network_attr(obj_attr_list, _network_attr_list)

        return _network_list    


    @trace
    def instance_cleanup_on_failure(self, obj_attr_list) :
        '''
        TBD
        '''

        _vminstance = self.get_instances(obj_attr_list, "vm", \
                                                       obj_attr_list["cloud_vm_name"])

        if _vminstance :
            # Not the best way to solve this problem. Will improve later.
            
            if not self.is_vm_running(obj_attr_list) :
                if "fault" in dir(_vminstance) :
                    if "message" in _vminstance.fault : 
                        obj_attr_list["instance_creation_failure_message"] += "\nINSTANCE ERROR MESSAGE:" + str(_vminstance.fault["message"]) + ".\n"

            # Try and make a last attempt effort to get the hostname,
            # even if the VM creation failed.

            self.get_host_and_instance_name(obj_attr_list, fail = False)

            if "host_name" in obj_attr_list :
                obj_attr_list["instance_creation_failure_message"] += " (Host \"" + obj_attr_list["host_name"] + "\")"

            #_vminstance.delete()
            self.ntnxconnvm.delete_name(name=_vminstance["name"], clusteruuid=self.ntnxclusters.get_all_uuids()[0])
            #del self.ntnxconnvm[obj_attr_list["name"]]
            sleep(20)

        
        if obj_attr_list["volume_creation_status"] :
            obj_attr_list["instance_creation_failure_message"] += "VOLUME ERROR MESSAGE:" + obj_attr_list["volume_creation_failure_message"] + ".\n"

        return 0, obj_attr_list["instance_creation_failure_message"]

    @trace
    def add_host(self, obj_attr_list, host, start) :
        '''
        TBD
        '''
        try :

            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _function = ''
            for _service in self.host_map[host]["services"] :
                if _service.count("scheduler") or _service.count("api") or \
                _service.count("server") or _service.count("dhcp") :
                    _function = "controller,"
                    break
                
            #if "nova-compute" in self.host_map[host]["services"] :
            #    _function = "compute,"

            _function = _function[0:-1]
            
            # Host UUID is artificially generated
            _host_uuid = str(uuid5(UUID('4f3f2898-69e3-5a0d-820a-c4e87987dbce'), \
                                   obj_attr_list["cloud_name"] + str(host)))
            obj_attr_list["host_list"][_host_uuid] = {}
            obj_attr_list["hosts"] += _host_uuid + ','

            _actual_host_name = host
             
            if "modify_host_names" in obj_attr_list and \
            str(obj_attr_list["modify_host_names"]).lower() != "false" :
                _queried_host_name = _actual_host_name.split(".")[0] + '.' + obj_attr_list["modify_host_names"]
            else :
                _queried_host_name = _actual_host_name

            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], \
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_queried_host_name, True)

            obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = \
            _actual_host_name

            obj_attr_list["host_list"][_host_uuid].update(self.host_map[host])
            obj_attr_list["host_list"][_host_uuid]["function"] = _function
            obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
            
            obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
            obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                                
            if str(obj_attr_list["host_user_root"]).lower() == "true" :
                obj_attr_list["host_list"][_host_uuid]["login"] = "root"                        
            else :
                obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["host_list"][_host_uuid]["username"]
                
            obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
            obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
            obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
            obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
            obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
            obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
            obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
            obj_attr_list["host_list"][_host_uuid]["simulated"] = False
            obj_attr_list["host_list"][_host_uuid]["identity"] = obj_attr_list["identity"]
            if "login" in obj_attr_list :
                obj_attr_list["host_list"][_host_uuid]["login"] = obj_attr_list["login"]
            else :
                obj_attr_list["host_list"][_host_uuid]["login"] = "root"                
            obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
            obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
            _time_mark_prc = int(time())
            obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start

            _status = 0
            
        except CldOpsException as obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)
                    
        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("HOST", obj_attr_list, "discovered", _status, _fmsg)
            return _status, _msg        



    @trace
    def get_mac_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''

        try :
            obj_attr_list["cloud_mac"] = instance['vm_nics'][0]['mac_address']
            _status = 0
        except :
            _status = 2000
            obj_attr_list["cloud_mac"] = "ERROR"
            _msg = str(instance['vm_nics'][0]['mac_address'])
            cberr(_msg)
            raise CldOpsException(_msg, _status)
        finally :
            if not _status:
                return True
            else :
                return False

