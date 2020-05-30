#!/usr/bin/env python

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
                              use_volumes = False, \
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
        
        driver = libcloud_driver(subscription_id = _subscription_id, tenant_id = _tenant_id, key = _application_id, secret = _secret)

        return driver

    @trace
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, _local_conn) :
        '''
        TBD
        '''
        
#        _cloud_service_found = False
                
#        vm_defaults["cloud_service_name"] = vm_defaults["cloud_service_prefix"] + vmc_name.replace(' ','')
        
        vm_defaults["run_netname"] = "private"
        
#        vmc_defaults["cloud_service_name"] = vm_defaults["cloud_service_name"]
        
#        _cloud_service_name_list = _local_conn.ex_list_cloud_services()
        
#        for _cloud_service in _cloud_service_name_list :
#            if _cloud_service.service_name == vm_defaults["cloud_service_name"] :
#                _cloud_service_found = True

#        if not _cloud_service_found :
#            _local_conn.ex_create_cloud_service(vm_defaults["cloud_service_name"], vmc_name)
#            LibcloudCmds.services = False
#            _cloud_service_found = True

        hash_object = hashlib.sha1(str(time()).encode("utf-8"))
        hex_dig = hash_object.hexdigest()
        vm_defaults["vm_name_suffix"] = str(hex_dig[0:10])

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
        if imageid.count("__") == 1 :
            if is_number(imageid.split("__")[0], True) :
                return True

        return False
    
    @trace
    def pre_vmcreate_process(self, obj_attr_list, keys) :
        '''
        TBD
        '''
        print("AQUI")
        for _location in LibcloudCmds.locations :
            print(obj_attr_list["region"])
            if _location.id == obj_attr_list["region"] :
                obj_attr_list["libcloud_location_inst"] = _location
                break
                    
        self.vmcreate_kwargs["ex_custom_data"] = obj_attr_list["userdata"]
        self.vmcreate_kwargs["ex_admin_user_id"] = obj_attr_list["login"]
        obj_attr_list["libcloud_call_type"] = "create_node_with_mixed_arguments"

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Azure Resource Manager"
