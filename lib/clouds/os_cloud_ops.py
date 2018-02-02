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
    Created on Jan 30, 2018
    OpenStack Object Operations Library
    @author: Marcio Silva, Michael R. Hines, Darrin Eden
'''

from time import time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number
from libcloud_common import LibcloudCmds

from shared_functions import CldOpsException

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
                              use_floating_ips = True, \
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

        if "OS_USER_DOMAIN_ID" in self.connauth_pamap :
            _user_domain_id = self.connauth_pamap["OS_USER_DOMAIN_ID"]

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
                                 ex_user_domain_id = _user_domain_id)

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
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, _local_conn) :
        '''
        TBD
        '''
        if "OS_TENANT_NAME" in self.connauth_pamap :
            vm_defaults["tenant_from_rc"] = self.connauth_pamap["OS_TENANT_NAME"]

        vm_defaults["access"] = self.access

        vmc_defaults["access"] = self.access
        
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
        if len(imageid) == 36 and imageid.count('-') == 4 :
            return True

        return False

    @trace            
    def create_ssh_key(self, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        connection.import_key_pair_from_string(key_name, key_type + ' ' + key_contents + " cbtool@orchestrator")        
        return True

    @trace
    def get_region_from_vmc_name(self, obj_attr_list) :
        '''
        TBD
        '''
        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        for _location in LibcloudCmds.locations :
            if _location.id == obj_attr_list["region"] :
                return _location

        return False
    
    @trace
    def get_cloud_specific_parameters(self, obj_attr_list, extra, credentials_list, status) :
        '''
        TBD
        '''
        _mark_a = time()        
        keyname = False
        
        for dontcare in range(0, 2) :
            for key in LibcloudCmds.keys[credentials_list] :
                if key.name == obj_attr_list["key_name"] :
                    keyname = key.name

            if keyname :
                break

            cbdebug("Could not find " + obj_attr_list["key_name"] + " keys. Refreshing key list...", True)
            LibcloudCmds.keys[credentials_list] = LibcloudCmds.catalogs.cbtool[credentials_list].list_key_pairs()

        if not keyname :
            raise CldOpsException("Not all SSH keys exist. Check your configuration: " + obj_attr_list["key_name"], status, True)        
        self.annotate_time_breakdown(obj_attr_list, "get_sshkey_time", _mark_a)

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

        obj_attr_list["libcloud_call_type"] = 2

        self.vmcreate_kwargs["name"] = obj_attr_list["cloud_vm_name"]
        self.vmcreate_kwargs["size"] = obj_attr_list["libcloud_size_inst"]
        self.vmcreate_kwargs["image"] =  obj_attr_list["libcloud_image_inst"]        
        self.vmcreate_kwargs["ex_security_groups"] = _security_groups
        self.vmcreate_kwargs["ex_userdata"] = obj_attr_list["userdata"]
        self.vmcreate_kwargs["ex_config_drive"] = obj_attr_list["config_drive"]        
        self.vmcreate_kwargs["ex_keyname"] = keyname
        self.vmcreate_kwargs["networks"] = _networks       
        self.vmcreate_kwargs["ex_metadata"] =  {}
        
        if "cloud_floating_ip_uuid" in obj_attr_list :
            self.vmcreate_kwargs["ex_metadata"]["cloud_floating_ip_uuid"] = obj_attr_list["cloud_floating_ip_uuid"]
        if "cloud_floating_ip" in obj_attr_list :            
            self.vmcreate_kwargs["ex_metadata"]["cloud_floating_ip"] = obj_attr_list["cloud_floating_ip"]

                
        return True

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack"
