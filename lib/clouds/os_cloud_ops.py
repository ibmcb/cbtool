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
    Created on Jan 30, 2018
    OpenStack Object Operations Library
    @author: Marcio Silva, Michael R. Galaxy
'''

from time import time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number
from .libcloud_common import LibcloudCmds

from .shared_functions import CldOpsException

#from libcloud.compute.drivers.azure import ConfigurationSet,ConfigurationSetInputEndpoint

class OsCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              provider = "OPENSTACK", \
                              num_credentials = 1, \
                              use_ssh_keys = True, \
                              use_volumes = True, \
                              use_networks = True, \
                              use_security_groups = True, \
                              use_public_ips = False, \
                              use_get_image = True, \
                              verify_ssl = False, \
                              tldomain = "openstack.org" \
                             )

    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, access_token) :
        '''
        TBD
        '''
        
        _access_url = "auto"
        _auth_version = '3.x_password'
        _endpoint_type = "publicURL"
        _region = "auto"
        _username = "auto"
        _password = "auto"
        _tenant = "auto"
        _project_name = None
        _cacert = None
        _insecure = False
        _user_domain_id = "default"
        _project_domain_id = "default"
        _domain_name = "Default"

        if not self.connauth_pamap :
            self.connauth_pamap = self.parse_cloud_connection_file(access_token)

        if "OS_AUTH_URL" in self.connauth_pamap :
            _access_url = self.connauth_pamap["OS_AUTH_URL"]

        if "OS_ENDPOINT_TYPE" in self.connauth_pamap :
            _endpoint_type = self.connauth_pamap["OS_ENDPOINT_TYPE"]

        if "OS_REGION_NAME" in self.connauth_pamap :
            _region = self.connauth_pamap["OS_REGION_NAME"]

        if "OS_USERNAME" in self.connauth_pamap :
            _username = self.connauth_pamap["OS_USERNAME"]

        if "OS_PASSWORD" in self.connauth_pamap :
            _password = self.connauth_pamap["OS_PASSWORD"]

        if "OS_TENANT_NAME" in self.connauth_pamap :
            _tenant = self.connauth_pamap["OS_TENANT_NAME"]

        if "OS_PROJECT_NAME" in self.connauth_pamap :
            _project_name = self.connauth_pamap["OS_PROJECT_NAME"]

        if "OS_CACERT" in self.connauth_pamap :
            _cacert = self.connauth_pamap["OS_CACERT"]

        if "OS_INSECURE" in self.connauth_pamap :
            if self.connauth_pamap["OS_INSECURE"] == "1" :
                _insecure = True

        if "OS_PROJECT_DOMAIN_ID" in self.connauth_pamap :
            _project_domain_id = self.connauth_pamap["OS_PROJECT_DOMAIN_ID"]

        if "OS_DOMAIN_NAME" in self.connauth_pamap :
            _domain_name = self.connauth_pamap["OS_DOMAIN_NAME"]

        if "OS_USER_DOMAIN_ID" in self.connauth_pamap :
            _user_domain_id = self.connauth_pamap["OS_USER_DOMAIN_ID"]

        if "OS_USER_DOMAIN_NAME" in self.connauth_pamap :
            _user_domain_name = self.connauth_pamap["OS_USER_DOMAIN_NAME"]

        _access_url = _access_url.replace("/v2.0/",'').replace("/v3/",'').replace("/identity",'')

        self.access = _access_url + '-' + _endpoint_type

        if not _project_name :
            _project_name = _username

        driver = libcloud_driver(_username, \
                                 _password, \
                                 ex_force_auth_version = _auth_version, \
                                 ex_force_auth_url = _access_url, \
                                 ex_force_service_type='compute', \
                                 ex_force_service_region = _region, \
                                 ex_tenant_name = _tenant, \
                                 ex_project_name = _project_name, \
                                 ex_project_domain_id =  _project_domain_id, \
                                 ex_user_domain_id = _user_domain_id, \
                                 ex_domain_name = _domain_name)

        _msg = "Libcloud connection code is \"python -c 'from libcloud.compute."
        _msg += "providers import get_driver; from libcloud.compute.types import"
        _msg += " Provider; cls = get_driver(Provider.OPENSTACK); con = "
        _msg += "cls(\"" + _username + "\", " + "\"REPLACE_PASSWORD\"" + ", "
        _msg += "ex_force_auth_version = \"" + _auth_version + "\", "
        _msg += "ex_force_auth_url = \"" + _access_url + "\", "
        _msg += "ex_force_service_type = \"" + "compute" + "\", "
        _msg += "ex_force_service_region = \"" + _region + "\", "
        _msg += "ex_tenant_name = \"" + _tenant + "\", "
        _msg += "ex_project_name = \"" + _project_name + "\", "
        _msg += "ex_project_domain_id = \"" + _project_domain_id + "\", "
        _msg += "ex_user_domain_id = \"" + _user_domain_id + "\")'"
        cbdebug(_msg, True)

        return driver

    @trace
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, connection) :
        '''
        TBD
        '''
        if "OS_TENANT_NAME" in self.connauth_pamap :
            vm_defaults["tenant_from_rc"] = self.connauth_pamap["OS_TENANT_NAME"]

        vm_defaults["access"] = self.access

        vmc_defaults["access"] = self.access

        if not LibcloudCmds.floating_ip_pools :
            cbdebug(" Caching " + self.get_description()  + " Floating IP pools...", True)
            LibcloudCmds.floating_ip_pools = connection.ex_list_floating_ip_pools()
        
        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        if len(imageid) == 36 and imageid.count('-') == 4 :
            return True

        return False

    @trace            
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        connection.import_key_pair_from_string(key_name, key_type + ' ' + key_contents + " cbtool@orchestrator")        
        return True
    
    @trace
    def pre_vmcreate_process(self, obj_attr_list, connection, keys) :
        '''
        TBD
        '''
        
        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        if len(LibcloudCmds.locations) == 1 :
            obj_attr_list["libcloud_location_inst"] = LibcloudCmds.locations[0]
        else :
            for _location in LibcloudCmds.locations :
                if _location.id == obj_attr_list["region"] :
                    obj_attr_list["libcloud_location_inst"] = _location
                    break

        _mark_a = time()
        _security_groups = []

        for _secgrp in LibcloudCmds.security_groups :
            for _security_group in obj_attr_list["security_groups"].split(',') :
                if _secgrp.name == obj_attr_list["security_groups"] :
                    _security_groups.append(_secgrp)
        self.annotate_time_breakdown(obj_attr_list, "get_secgrp_time", _mark_a)

        _mark_a = time()
        _networks = []
        for _network in LibcloudCmds.networks :
            if _network.name == obj_attr_list["run_netname"] :
                if _network not in _networks :
                    _networks.append(_network)

            if _network.name == obj_attr_list["prov_netname"] :
                if _network not in _networks :
                    _networks.append(_network)
        self.annotate_time_breakdown(obj_attr_list, "get_net_time", _mark_a)

        obj_attr_list["availability_zone"] = "none"

        obj_attr_list["libcloud_call_type"] = "create_node_with_keyword_arguments_only"

        self.vmcreate_kwargs["name"] = obj_attr_list["cloud_vm_name"]
        self.vmcreate_kwargs["size"] = obj_attr_list["libcloud_size_inst"]
        self.vmcreate_kwargs["image"] =  obj_attr_list["libcloud_image_inst"]        
        self.vmcreate_kwargs["ex_security_groups"] = _security_groups
        self.vmcreate_kwargs["ex_userdata"] = obj_attr_list["userdata"]
        self.vmcreate_kwargs["ex_config_drive"] = obj_attr_list["config_drive"]        
        self.vmcreate_kwargs["ex_keyname"] = keys[0]
        self.vmcreate_kwargs["networks"] = _networks       
        self.vmcreate_kwargs["ex_metadata"] =  {}

        obj_attr_list["cloud_floating_ip_uuid"] = "NA"
        obj_attr_list["cloud_floating_ip"] = "NA"
        if obj_attr_list["use_floating_ip"].lower() == "true" :

            for _floating_pool in LibcloudCmds.floating_ip_pools :
                if _floating_pool.name == obj_attr_list["floating_pool"] :
                    break

            _mark_a = time()
            _fip = connection.ex_create_floating_ip(ip_pool = _floating_pool.name)
            self.annotate_time_breakdown(obj_attr_list, "create_fip_time", _mark_a)
            obj_attr_list["cloud_floating_ip_uuid"] = _fip.id
            obj_attr_list["cloud_floating_ip"] = _fip.ip_address
            self.vmcreate_kwargs["ex_metadata"]["cloud_floating_ip_uuid"] = obj_attr_list["cloud_floating_ip_uuid"]
            self.vmcreate_kwargs["ex_metadata"]["cloud_floating_ip"] = obj_attr_list["cloud_floating_ip"]

    @trace
    def post_vmcreate_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        if obj_attr_list["cloud_floating_ip_uuid"] != "NA" :
            _mark_a = time()
            _fip = self.get_adapter(_credentials_list).ex_attach_floating_ip_to_node(self.get_instances(obj_attr_list), obj_attr_list["cloud_floating_ip"])
            self.annotate_time_breakdown(obj_attr_list, "attach_fip_time", _mark_a)

    @trace    
    def post_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''    
        if "cloud_floating_ip" in obj_attr_list :
            if obj_attr_list["cloud_floating_ip"] != "NA" :
                connection.ex_delete_floating_ip(self.get_adapter(_credentials_list).ex_get_floating_ip(obj_attr_list["cloud_floating_ip"]))
        return True

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack"
