#!/usr/bin/env python3

#/*******************************************************************************
# Copyright (c) 2018 IBM Corp.

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

#/*******************************************************************************
# Copyright (c) 2015 DigitalOcean, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on Jan 26, 2018
    Azure Object Operations Library
    @author: Marcio Silva, Michael R. Galaxy
'''
from time import time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number
from .libcloud_common import LibcloudCmds

import hashlib

#from libcloud.compute.drivers.azure import ConfigurationSet,ConfigurationSetInputEndpoint

class AsCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              provider = "AZURE_ARM", \
                              num_credentials = 1, \
                              use_ssh_keys = False, \
                              use_sizes = True, \
                              use_services = False, \
                              use_get_image = False, \
                              use_locations = True, \
                              target_location = True, \
                              tldomain = "azure.com" \
                             )
    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, access_token) :
        '''
        TBD
        '''
        _subscription_id, _tenant_id, _application_id, _secret = access_token.split('+')
        
        self.subscription_id = _subscription_id
        driver = libcloud_driver(subscription_id = _subscription_id, tenant_id = _tenant_id, key = _application_id, secret = _secret)

        return driver

    @trace
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, connection) :
        '''
        TBD
        '''
        self.imglist_kwargs["location"] = LibcloudCmds.target_location
        if len(vm_defaults["publisher"]) > 3 :
            self.imglist_kwargs["ex_publisher"] = vm_defaults["publisher"]

        if len(vm_defaults["offer"]) > 3 :
            self.imglist_kwargs["ex_offer"] = vm_defaults["offer"]

        if vm_defaults["resource_group"] == "auto" :
            vm_defaults["resource_group"] = "cbtool" + vmc_name
        
        vmc_defaults["resource_group"] = vm_defaults["resource_group"]
        hash_object = hashlib.sha1(str(time()).encode("utf-8"))
        hex_dig = hash_object.hexdigest()
        vm_defaults["vm_name_suffix"] = str(hex_dig[0:10])

        return True

    @trace
    def extra_vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        _wait = int(obj_attr_list["update_frequency"])
        _existing_pips = True
        while _existing_pips :
            _existing_pips = False
            for credentials_list in obj_attr_list["credentials"].split(";"):
                credentials = credentials_list.split(":")
                tenant = credentials[0]
                self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')
                obj_attr_list["tenant"] = tenant

                _pips = self.get_adapter(credentials_list).ex_list_public_ips(obj_attr_list["resource_group"])
                for _pip in _pips :
                    if _pip.name.count("cb-" + obj_attr_list["username"] + "-" + obj_attr_list["cloud_name"]) :
                        try :
                            cbdebug("Destroying: " + _pip.name + " (" + tenant + ")", True)
                            self.get_adapter(credentials_list).ex_delete_public_ip(_pip)
                        except MalformedResponseError as e :
                            self.dump_httplib_headers(credentials_list)
                            raise CldOpsException("The Cloud's API is misbehaving", 1483)
                        except Exception as e :
                            for line in traceback.format_exc().splitlines() :
                                cbwarn(line, True)
                            self.dump_httplib_headers(credentials_list)
                        _existing_pips = True
                    else :
                        _msg = "Cleaning up " + self.get_description() + ". Ignoring Public IP: " + _pip.name
                        cbdebug(_msg)

                if _existing_pips :
                    _wait = self.backoff(obj_attr_list, _wait)
                    
        return True

    @trace
    def get_list_node_args(self, obj_attr_list) :
        '''
        TBD
        '''
        
        return [ ]

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        return False

    @trace
    def pre_vmcreate_process(self, obj_attr_list, connection, keys) :
        '''
        TBD
        '''
        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        if "libcloud_location_inst" not in obj_attr_list :
            for _location in LibcloudCmds.locations :
                if _location.id == obj_attr_list["region"] :
                    obj_attr_list["libcloud_location_inst"] = _location
                    break

        self.imglist_kwargs["location"] = LibcloudCmds.target_location
        if len(obj_attr_list["publisher"]) > 3 :
            self.imglist_kwargs["ex_publisher"] = obj_attr_list["publisher"]

        if len(obj_attr_list["offer"]) > 3 :
            self.imglist_kwargs["ex_offer"] = obj_attr_list["offer"]

        if obj_attr_list["storage_account"] == "auto" :
            obj_attr_list["storage_account"] = "cbtool" + obj_attr_list["region"]

        if obj_attr_list["netname"].count(',') :
            obj_attr_list["prov_netname"], obj_attr_list["run_netname"] = obj_attr_list["netname"].split(',')
            
        if obj_attr_list["netname"].count("auto") :
            obj_attr_list["netname"] = "cbtool" + obj_attr_list["region"]
            obj_attr_list["prov_netname"] = "public"
            obj_attr_list["run_netname"] = "private"
                        
        if "prov_netname" not in obj_attr_list :
            obj_attr_list["prov_netname"] = obj_attr_list["netname"]

        if "run_netname" not in obj_attr_list :
            obj_attr_list["run_netname"] = obj_attr_list["netname"]

        if "libcloud_public_ip_inst" not in obj_attr_list and obj_attr_list["prov_netname"] == "public" :

            _mark_a = time()
            obj_attr_list["cloud_pip_name"] = obj_attr_list["cloud_vm_name"].replace('-vm','-pip')
            _pip = connection.ex_create_public_ip(obj_attr_list["cloud_pip_name"], obj_attr_list["resource_group"], obj_attr_list["libcloud_location_inst"])
            self.annotate_time_breakdown(obj_attr_list, "create_pip_time", _mark_a)
            obj_attr_list["libcloud_public_ip_inst"] = _pip

            _mark_a = time()
            for _net in connection.ex_list_networks() :
                if _net.name == obj_attr_list["netname"] :
                    _net_inst = _net
                    break
                
            for _subnet in connection.ex_list_subnets(_net_inst) :
                if _subnet.name == "default" :
                    _snet_inst = _subnet

            obj_attr_list["cloud_vnic_name"] = obj_attr_list["cloud_vm_name"].replace('-vm','-vnic')
            _vnic = connection.ex_create_network_interface(obj_attr_list["cloud_vnic_name"], _snet_inst, obj_attr_list["resource_group"], location = obj_attr_list["libcloud_location_inst"], public_ip = obj_attr_list["libcloud_public_ip_inst"])
            self.annotate_time_breakdown(obj_attr_list, "create_vnic_time", _mark_a)
            obj_attr_list["libcloud_vnic_inst"] = _vnic

            self.vmcreate_kwargs["ex_nic"] = obj_attr_list["libcloud_vnic_inst"]
            self.vmcreate_kwargs["ex_network"] = None
        else  :
            self.vmcreate_kwargs["ex_network"] = obj_attr_list["netname"]     
        
        self.vmcreate_kwargs["location"] = obj_attr_list["libcloud_location_inst"]              
        self.vmcreate_kwargs["ex_resource_group"] = obj_attr_list["resource_group"]
        self.vmcreate_kwargs["ex_storage_account"] = obj_attr_list["storage_account"]
        self.vmcreate_kwargs["ex_customdata"] = obj_attr_list["userdata"].encode()
        self.vmcreate_kwargs["ex_user_name"] = obj_attr_list["login"]
        
        obj_attr_list["libcloud_call_type"] = "create_node_with_mixed_arguments"

        return True

    @trace
    def pre_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        self.vmdestroy_kwargs["ex_destroy_nic"] = True
        self.vmdestroy_kwargs["ex_destroy_vhd"] = True
        
        return True

    @trace
    def post_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        if "cloud_pip_name" in obj_attr_list :
            for _pip in connection.ex_list_public_ips(obj_attr_list["resource_group"]) :
                if _pip.name == obj_attr_list["cloud_pip_name"] :
                    _pip_inst = _pip
                    break

                try :
                    connection.ex_delete_public_ip(_pip_inst)
                except Exception as e :
                    cbwarn("While attempting to delete Public IP \""  + _pip_inst.name + "\": " + str(e))
        
        return True

    @trace
    def pre_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        
        self.vmdestroy_kwargs["ex_destroy_nic"] = True
        self.vmdestroy_kwargs["ex_destroy_vhd"] = True
        
    @trace
    def pre_vmcreate_process(self, obj_attr_list, connection, keys) :
        '''
        TBD
        '''
        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        if "libcloud_location_inst" not in obj_attr_list :
            for _location in LibcloudCmds.locations :
                if _location.id == obj_attr_list["region"] :
                    obj_attr_list["libcloud_location_inst"] = _location
                    break

        self.imglist_kwargs["location"] = LibcloudCmds.target_location
        if len(obj_attr_list["publisher"]) > 3 :
            self.imglist_kwargs["ex_publisher"] = obj_attr_list["publisher"]

        if len(obj_attr_list["offer"]) > 3 :
            self.imglist_kwargs["ex_offer"] = obj_attr_list["offer"]

        if obj_attr_list["storage_account"] == "auto" :
            obj_attr_list["storage_account"] = "cbtool" + obj_attr_list["region"]

        if obj_attr_list["netname"].count(',') :
            obj_attr_list["prov_netname"], obj_attr_list["run_netname"] = obj_attr_list["netname"].split(',')
            
        if obj_attr_list["netname"].count("auto") :
            obj_attr_list["netname"] = "cbtool" + obj_attr_list["region"]
            obj_attr_list["prov_netname"] = "public"
            obj_attr_list["run_netname"] = "private"
                        
        if "prov_netname" not in obj_attr_list :
            obj_attr_list["prov_netname"] = obj_attr_list["netname"]

        if "run_netname" not in obj_attr_list :
            obj_attr_list["run_netname"] = obj_attr_list["netname"]

        if "libcloud_public_ip_inst" not in obj_attr_list and obj_attr_list["prov_netname"] == "public" :

            _mark_a = time()
            obj_attr_list["cloud_pip_name"] = obj_attr_list["cloud_vm_name"].replace('-vm','-pip')
            _pip = connection.ex_create_public_ip(obj_attr_list["cloud_pip_name"], obj_attr_list["resource_group"], obj_attr_list["libcloud_location_inst"])
            self.annotate_time_breakdown(obj_attr_list, "create_pip_time", _mark_a)
            obj_attr_list["libcloud_public_ip_inst"] = _pip

            _mark_a = time()
            for _net in connection.ex_list_networks() :
                if _net.name == obj_attr_list["netname"] :
                    _net_inst = _net
                    break
                
            for _subnet in connection.ex_list_subnets(_net_inst) :
                if _subnet.name == "default" :
                    _snet_inst = _subnet

            obj_attr_list["cloud_vnic_name"] = obj_attr_list["cloud_vm_name"].replace('-vm','-vnic')
            _vnic = connection.ex_create_network_interface(obj_attr_list["cloud_vnic_name"], _snet_inst, obj_attr_list["resource_group"], location = obj_attr_list["libcloud_location_inst"], public_ip = obj_attr_list["libcloud_public_ip_inst"])
            self.annotate_time_breakdown(obj_attr_list, "create_vnic_time", _mark_a)
            obj_attr_list["libcloud_vnic_inst"] = _vnic

            self.vmcreate_kwargs["ex_nic"] = obj_attr_list["libcloud_vnic_inst"]
            self.vmcreate_kwargs["ex_network"] = None
        else  :
            self.vmcreate_kwargs["ex_network"] = obj_attr_list["netname"]     
        
        self.vmcreate_kwargs["location"] = obj_attr_list["libcloud_location_inst"]              
        self.vmcreate_kwargs["ex_resource_group"] = obj_attr_list["resource_group"]
        self.vmcreate_kwargs["ex_storage_account"] = obj_attr_list["storage_account"]
        self.vmcreate_kwargs["ex_customdata"] = obj_attr_list["userdata"].encode()
        self.vmcreate_kwargs["ex_user_name"] = obj_attr_list["login"]
        
        obj_attr_list["libcloud_call_type"] = "create_node_with_mixed_arguments"

        return True

    @trace
    def pre_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        self.vmdestroy_kwargs["ex_destroy_nic"] = True
        self.vmdestroy_kwargs["ex_destroy_vhd"] = True
        return True

    @trace
    def post_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        if "cloud_pip_name" in obj_attr_list :
            for _pip in connection.ex_list_public_ips(obj_attr_list["resource_group"]) :
                if _pip.name == obj_attr_list["cloud_pip_name"] :
                    _pip_inst = _pip
                    break

                try :
                    connection.ex_delete_public_ip(_pip_inst)
                except Exception as e :
                    cbwarn("While attempting to delete Public IP \""  + _pip_inst.name + "\": " + str(e))
        
        return True

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Azure Resource Manager"
