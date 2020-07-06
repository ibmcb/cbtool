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
    Created on Fev 3, 2012

    OpenStack Object Operations Library

    @author: Marcio A. Silva
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

from keystoneauth1.identity import v3
from keystoneauth1 import session

from novaclient import client as novac
from glanceclient import client as glancec

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic
from lib.remote.network_functions import hostname2ip
from .shared_functions import CldOpsException, CommonCloudFunctions 

class OskCmds(CommonCloudFunctions) :
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
        self.oskconncompute = {}
        self.oskconnstorage = {}
        self.oskconnnetwork = {}
        self.oskconnimage = {} 
        self.expid = expid
        self.ft_supported = False
        self.lvirt_conn = {}
        self.networks_attr_list = { "tenant_network_list":[] }
        self.host_map = {}
        self.api_error_counter = {}
        self.additional_rc_contents = ''
        self.connauth_pamap = {}
        self.max_api_errors = 10
        
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack Cloud"
        
    @trace
    def connect(self, access_url, authentication_data, region, extra_parms = {}, diag = False, generate_rc = False, client_conn_id = None) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _dmsg = ''

            _version = '2'
            
            _auth = None
            _credentials = None
            _data_auth_parse = False
            _nova_client = False

            if not self.connauth_pamap :
                self.connauth_pamap = self.parse_cloud_connection_file(access_url)
            
            access_url, _endpoint_type, region = self.parse_connection_data(access_url, region, extra_parms)

            _username, _password, _tenant, _project_name, _cacert, _verify, _user_domain_id, _project_domain_id = self.parse_authentication_data(authentication_data)
            _data_auth_parse = True

            _client_conn_id = "common"
            if client_conn_id :
                _client_conn_id = client_conn_id

            if not _username :
                _fmsg = _password
            else :

                access_url = access_url.replace('v2.0/','v3')

                _auth = v3.Password(auth_url = access_url, \
                                    username = _username, \
                                    password = _password, \
                                    project_name = _project_name, \
                                    user_domain_id = _user_domain_id, \
                                    project_domain_id = _project_domain_id)
                
                _session = session.Session(auth = _auth, verify = _verify, cert = _cacert)

                _msg = self.get_description() + " connection parameters: username=" + _username
                _msg += ", password=<omitted>, tenant=" + _tenant + ", "
                _msg += "cacert=" + str(_cacert) + ", verify=" + str(_verify)
                _msg += ", region_name=" + region + ", access_url=" + access_url
                _msg += ", endpoint_type=" + str(_endpoint_type)
                cbdebug(_msg, diag)
    
                _fmsg = "About to attempt a connection to " + self.get_description()

                if _client_conn_id not in self.oskconncompute :
                    self.oskconncompute[_client_conn_id] = novac.Client("2.1", session = _session)
                    self.oskconnimage[_client_conn_id] = glancec.Client("2", session = _session) 

                    self.oskconncompute[_client_conn_id].flavors.list()

                _nova_client = True
                if "use_cinderclient" in extra_parms :
                    self.use_cinderclient = str(extra_parms["use_cinderclient"]).lower()
                else :
                    self.use_cinderclient = "false"

                _cinder_client = True                    
                if self.use_cinderclient == "true" :
                    _cinder_client = False
                    if _client_conn_id not in self.oskconnstorage :                    
                        from cinderclient import client as cinderc 

                        self.oskconnstorage[_client_conn_id] = cinderc.Client("2.1", session = _session)                    

                        self.oskconnstorage[_client_conn_id].volumes.list()
                    
                    _cinder_client = True                                    

                self.use_neutronclient = "true"
                _neutron_client = True
                if self.use_neutronclient == "true" :
                    _neutron_client = False

                    if _client_conn_id not in self.oskconnnetwork :
                        from neutronclient.v2_0 import client as neutronc                           

                        self.oskconnnetwork[_client_conn_id] = neutronc.Client(session = _session)
        
                        self.oskconnnetwork[_client_conn_id].list_networks()

                    _neutron_client = True
                else :
                    self.oskconnnetwork = False

                _region = region
                _msg = "Selected region is " + str(region)
                cbdebug(_msg)

                if generate_rc :
                    self.additional_rc_contents = "export OS_TENANT_NAME=" + _tenant + "\n"
                    self.additional_rc_contents += "export OS_USERNAME=" + _username + "\n"
                    self.additional_rc_contents += "export OS_PASSWORD=" + _password + "\n"
                    self.additional_rc_contents += "export OS_AUTH_URL=\"" + access_url + "\"\n"
                    self.additional_rc_contents += "export OS_NO_CACHE=1\n"
#                    self.additional_rc_contents += "export OS_INTERFACE=" + _endpoint_type.replace("URL",'') +  "\n"
                    self.additional_rc_contents += "export OS_INTERFACE=admin\n"
                    if _cacert :
                        self.additional_rc_contents += "export OS_CACERT=" + _cacert + "\n"
                    self.additional_rc_contents += "export OS_REGION_NAME=" + region + "\n"
                                    
                _status = 0

        except novaclient.exceptions as obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)
                if _data_auth_parse :

                    if not _nova_client :
                        _dmsg = "Please attempt to execute the following : \"python -c \""
                        _dmsg += "from keystoneauth1.identity import v3; "
                        _dmsg += "from keystoneauth1 import session; "
                        _dmsg += "from novaclient import client as novac; "
                        _dmsg += "_auth = v3.Password(username = '" + str(_username) 
                        _dmsg += "', password = 'REPLACE_PASSWORD', project_name = '"
                        _dmsg += str(_tenant) + "', auth_url = '" + str(access_url) 
                        _dmsg += "', user_domain_id = '" + str(_user_domain_id) + "', "
                        _dmsg += "project_domain_id = '" + str(_project_domain_id) + "'); "
                        _dmsg += "_session = session.Session(auth = _auth, verify = " + str(_verify) + ", cert = " + str(_cacert) + "); "
                        _dmsg += "ct = novac.Client(\"2.1\", session = _session); print ct.flavors.list()\"\""
                    
                    elif not _cinder_client :
                        _dmsg = "Please attempt to execute the following : \"python -c \""
                        _dmsg += "from keystoneauth1.identity import v3; "
                        _dmsg += "from keystoneauth1 import session; "
                        _dmsg += "from cinderclient import client as cinderc; "
                        _dmsg += "_auth = v3.Password(username = '" + str(_username) 
                        _dmsg += "', password = 'REPLACE_PASSWORD', project_name = '"
                        _dmsg += str(_tenant) + "', auth_url = '" + str(access_url) 
                        _dmsg += "', user_domain_id = '" + str(_user_domain_id) + "', "
                        _dmsg += "project_domain_id = '" + str(_project_domain_id) + "'); "
                        _dmsg += "_session = session.Session(auth = _auth, verify = " + str(_verify) + ", cert = " + str(_cacert) + "); "
                        _dmsg += "ct = cinderc.Client(\"2.1\", session = _session); print ct.volumes.list()\"\""                                                        
                    
                    elif not _neutron_client :
                        _dmsg = "Please attempt to execute the following : \"python -c \""
                        _dmsg += "from keystoneauth1.identity import v3; "
                        _dmsg += "from keystoneauth1 import session; "
                        _dmsg += "from neutronclient.v2_0 import client as neutronc; "
                        _dmsg += "_auth = v3.Password(username = '" + str(_username) 
                        _dmsg += "', password = 'REPLACE_PASSWORD', project_name = '"
                        _dmsg += str(_tenant) + "', auth_url = '" + str(access_url) 
                        _dmsg += "', user_domain_id = '" + str(_user_domain_id) + "', "
                        _dmsg += "project_domain_id = '" + str(_project_domain_id) + "'); "
                        _dmsg += "_session = session.Session(auth = _auth, verify = " + str(_verify) + ", cert = " + str(_cacert) + "); "
                        _dmsg += "ct = neutronc.Client(session = _session); print ct.list_networks()\"\""                            
                    print(_dmsg)
                    
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

            self.connect(access, credentials, vmc_name, vm_defaults, True, True, vmc_name)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults, False, vmc_name)

            _security_group_found = self.check_security_group(vmc_name, security_group_name)

            _floating_pool_found = self.check_floating_pool(vmc_name, vm_defaults)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)

            _detected_imageids = self.check_images(vmc_name, vm_defaults, vm_templates)

            _check_jumphost = self.check_jumphost(vmc_name, vm_defaults, vm_templates, _detected_imageids)
            
            if not (_run_netname_found and _prov_netname_found and \
                    _key_pair_found and _security_group_found and _check_jumphost) :
                _msg = "Check the previous errors, fix it (using OpenStack's web"
                _msg += " GUI (horizon) or nova CLI"
                _status = 1178
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
            self.disconnect()
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

        self.get_network_list(vmc_name, vm_defaults)
                        
        _prov_netname_found = False
        _run_netname_found = False

        if _prov_netname in self.networks_attr_list :
            _net_model = self.networks_attr_list[_prov_netname]["model"]
            _net_type = self.networks_attr_list[_prov_netname]["model"]
            
            if _net_model != "external" :
                _prov_netname_found = True
                if _net_type == _net_model :
                    _net_str = _net_type
                else :
                    _net_str = _net_type + ' ' + _net_model
                _msg = "done. This " + _net_str + " will be used as the default for provisioning."
                cbdebug(_msg)
            else: 
                _msg = "\nERROR! The default provisioning network (" 
                _msg += _prov_netname + ") cannot be an external network"
                cberr(_msg, True)

        if _run_netname in self.networks_attr_list :
            _net_model = self.networks_attr_list[_run_netname]["model"]
            _net_type = self.networks_attr_list[_run_netname]["model"]
            
            if _net_model != "external" :
                _run_netname_found = True
                if _net_type == _net_model :
                    _net_str = _net_type
                else :
                    _net_str = _net_type + ' ' + _net_model                
                _msg = "a " + _net_type + ' ' + _net_model + " will be used as the default for running."
                cbdebug(_msg)
            else: 
                _msg = "ERROR! The default running network (" 
                _msg += _run_netname + ") cannot be an external network"
                cberr(_msg, True)
                                               
        if not (_run_netname_found and _prov_netname_found) :
            _msg = "ERROR! Please make sure that the " + _net_str + " can be found"
            _msg += " VMC " + vmc_name
            _fmsg = _msg 
            cberr(_msg, True)

        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_defaults, vm_templates) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _map_name_to_id = {}
        _map_id_to_name = {}

#        _registered_image_list = self.oskconncompute[vmc_name].glance.list()
        _registered_image_list = self.oskconnimage[vmc_name].images.list()
        _registered_imageid_list = []
            
        for _registered_image in _registered_image_list :
            if "hypervisor_type" in vm_defaults :
                if str(vm_defaults["hypervisor_type"]).lower() != "fake" :
                    if "hypervisor_type" in _registered_image._info :
                        if _registered_image._info["hypervisor_type"] == vm_defaults["hypervisor_type"] :                        
                            _registered_imageid_list.append(_registered_image.id)
                            _map_name_to_id[_registered_image.name] = _registered_image.id
                else :
                    _registered_imageid_list.append(_registered_image.id)
                    _map_name_to_id[_registered_image.name] = _registered_image.id                    
            else : 
                _registered_imageid_list.append(_registered_image.id)
                _map_name_to_id[_registered_image.name] = _registered_image.id
                
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

    @trace
    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["name"],
                         {},
                         False,
                         False,
                         obj_attr_list["name"])

            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            self.build_host_map(obj_attr_list["name"])
            _host_list = list(self.host_map.keys())

            obj_attr_list["host_count"] = len(_host_list)

            for _host in _host_list :
                self.add_host(obj_attr_list, _host, start)

            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]
                        
            self.additional_host_discovery (obj_attr_list)
            self.populate_interface(obj_attr_list)
            
            _status = 0
            
        except CldOpsException as obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)
                    
        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()    
            _status, _msg = self.common_messages("HOST", obj_attr_list, "discovered", _status, _fmsg)
            return _status, _msg

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
                         obj_attr_list["name"],
                        {"use_cinderclient" : str(obj_attr_list["use_cinderclient"])}, \
                        False, \
                        False, \
                        obj_attr_list["name"])

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _running_instances = True
            
            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False
                
                _criteria = {}                              
                _criteria["all_tenants"] = int(obj_attr_list["all_tenants"])
                _vmc_name = obj_attr_list["name"]
                _instances = self.oskconncompute[_vmc_name].servers.list(search_opts = _criteria)
                
                for _instance in _instances :
                    if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) \
                    and not _instance.name.count("jumphost") :

                        _instance_metadata = _instance.metadata
                        if "cloud_floating_ip_uuid" in _instance_metadata :
                            _msg = "    Deleting floating IP " + _instance_metadata["cloud_floating_ip_uuid"]
                            _msg += ", associated with instance "
                            _msg += _instance.id + " (" + _instance.name + ")"
                            cbdebug(_msg, True)
                            self.oskconnnetwork[_vmc_name].delete_floatingip(_instance_metadata["cloud_floating_ip_uuid"])                             
#                            self.oskconncompute.floating_ips.delete(_instance_metadata["cloud_floating_ip_uuid"])
                                                                        
                        _running_instances = True
                        if  _instance.status == "ACTIVE" :
                            _msg = "Terminating instance: " 
                            _msg += _instance.id + " (" + _instance.name + ")"
                            cbdebug(_msg, True)

                            _volume_attached = getattr(_instance, 'os-extended-volumes:volumes_attached')

                            self.retriable_instance_delete({}, _instance) 

                        if _instance.status == "BUILD" :
                            _msg = "Will wait for instance "
                            _msg += _instance.id + "\"" 
                            _msg += " (" + _instance.name + ") to "
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

            if self.oskconnstorage and self.use_cinderclient == "true" :
                self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')
                _volumes = self.oskconnstorage[_vmc_name].volumes.list()
    
                for _volume in _volumes :
                    if "display_name" in dir(_volume) :
                        _volume_name = str(_volume.display_name)
                    else :
                        _volume_name = str(_volume.name)
                    
                    if _volume_name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _volume.delete()

        except CldOpsException as obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
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
                                                 obj_attr_list["name"], 
                                                 obj_attr_list, \
                                                 False, \
                                                 True, \
                                                 obj_attr_list["name"])

                obj_attr_list["cloud_hostname"] = _hostname

                if "access_from_rc" in obj_attr_list :
                    _actual_access = obj_attr_list["access_from_rc"]
                else :
                    _actual_access = obj_attr_list["access"]
                                        
                _resolve = _actual_access.split(':')[1].replace('//','')

                _resolve = _resolve.split('/')[0]
                _resolve = _resolve.replace("_dash_","-")

                _x, obj_attr_list["cloud_ip"] = hostname2ip(_resolve, True)
                obj_attr_list["arrival"] = int(time())

                if str(obj_attr_list["discover_hosts"]).lower() == "true" :                   
                    _status, _fmsg = self.discover_hosts(obj_attr_list, _time_mark_prs)
                else :
                    obj_attr_list["hosts"] = ''
                    obj_attr_list["host_list"] = {}
                    obj_attr_list["host_count"] = "NA"
                    _status = 0

                if not _status :

                    self.get_network_list(obj_attr_list["name"], obj_attr_list)
    
                    _networks = {}
                    for _net in list(self.networks_attr_list.keys()) :
                        if "type" in self.networks_attr_list[_net] :
                            _type = self.networks_attr_list[_net]["type"]
    
                            obj_attr_list["network_" + _net] = _type
    
                    _time_mark_prc = int(time())
                    obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
                        
        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
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
            
            if "cleanup_on_detach" in obj_attr_list and str(obj_attr_list["cleanup_on_detach"]).lower() == "true" :
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

                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             _vmc_attr_list["name"], {}, False, False, _vmc_attr_list["name"])

                _instances = self.oskconncompute[_vmc_attr_list["name"]].servers.list()
                
                for _instance in _instances :                    
                    if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) \
                    and not _instance.name.count("jumphost") :
                        if _instance.status == "ACTIVE" :
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

        for _key_pair in self.oskconncompute[vmc_name].keypairs.list() :
            registered_key_pairs[_key_pair.name] = _key_pair.fingerprint + "-NA"

            #self.oskconncompute.keypairs.delete(_key_pair)
                                                
        return True

    @trace
    def get_security_groups(self, vmc_name, security_group_name, registered_security_groups) :
        '''
        TBD
        '''

        if vmc_name in self.oskconnnetwork :
            for _security_group in self.oskconnnetwork[vmc_name].list_security_groups()["security_groups"] :
                
                if _security_group["name"] not in registered_security_groups :
                    registered_security_groups.append(_security_group["name"])
        else :
            for _security_group in self.oskconncompute[vmc_name].security_groups.list() :
                registered_security_groups.append(_security_group.name)

        return True

    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        
        _networks = list(instance.addresses.keys())

        if len(_networks) :
            if _networks.count(obj_attr_list["run_netname"]) :
                _msg = "Network \"" + obj_attr_list["run_netname"] + "\" found."
                cbdebug(_msg)
                _run_network = _networks[_networks.index(obj_attr_list["run_netname"])]
            else :
                _msg = "Network \"" + obj_attr_list["run_netname"] + "\" found."
                _msg += "Using the first network (\"" + _networks[0] + "\") instead)."
                cbdebug(_msg)
                _run_network = _networks[0]

            _address_list = instance.addresses[_run_network]

            if len(_address_list) :
                
                for _address in _address_list :

                    if _address["OS-EXT-IPS:type"] == "fixed" :
                        obj_attr_list["run_cloud_ip"] = '{0}'.format(_address["addr"])

                # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
                if "run_cloud_ip" in obj_attr_list :
                    obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
                else :
                    return False

                if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                    obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
                elif obj_attr_list["hostname_key"] == "cloud_ip" :
                    obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')

                if str(obj_attr_list["use_floating_ip"]).lower() == "true" :

                    for _provnet in _networks :
                        _address_list = instance.addresses[_provnet]
            
                        if len(_address_list) :
            
                            for _address in _address_list :
            
                                if _address["OS-EXT-IPS:type"] == "floating" :
                                    obj_attr_list["prov_cloud_ip"] = '{0}'.format(_address["addr"])
                                    return True

                else :

                    if obj_attr_list["prov_netname"] == obj_attr_list["run_netname"] :
                        obj_attr_list["prov_cloud_ip"] = obj_attr_list["run_cloud_ip"]
                        return True
                    else :
                        if _networks.count(obj_attr_list["prov_netname"]) :
                            _msg = "Network \"" + obj_attr_list["prov_netname"] + "\" found."
                            cbdebug(_msg)
                            _prov_network = _networks[_networks.index(obj_attr_list["prov_netname"])]
                        else :
                            _msg = "Network \"" + obj_attr_list["prov_netname"] + "\" found."
                            _msg += "Using the first network (\"" + _networks[0] + "\") instead)."
                            cbdebug(_msg)
                            _prov_network = _networks[0]
        
                        _address_list = instance.addresses[_prov_network]
            
                        if len(_address_list) :
            
                            for _address in _address_list :
            
                                if _address["OS-EXT-IPS:type"] == "fixed" :
                                    obj_attr_list["prov_cloud_ip"] = '{0}'.format(_address["addr"])
                                    return True

            else :
                _status = 1181
                _msg = "IP address list for network " + str(_run_network) + " is empty."
                cberr(_msg)
                raise CldOpsException(_msg, _status)                
        else :
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all", force_list = False) :
        '''
        TBD
        '''
        try :
            _search_opts = {}
            _call = "NA"
            _search_opts["all_tenants"] = int(obj_attr_list["all_tenants"])
            
            if identifier != "all" :
                if obj_type == "vm" :
                    _search_opts["name"] = identifier
                else :
                    _search_opts["display_name"] = identifier

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list, False, False, identifier)

            if obj_type == "vm" :
                                
                if "cloud_vm_uuid" in obj_attr_list and len(obj_attr_list["cloud_vm_uuid"]) >= 36 and not force_list :
                    _call = "get"
                    _instances = [ self.oskconncompute[identifier].servers.get(obj_attr_list["cloud_vm_uuid"]) ]

                else :
                    _call = "list"
                    _instances = self.oskconncompute[identifier].servers.list(search_opts = _search_opts)
            else :

                if "cloud_vv_uuid" in obj_attr_list and len(obj_attr_list["cloud_vv_uuid"]) >= 36 :
                    _call = "get"
                    _instances = [ self.oskconnstorage[identifier].volumes.get(obj_attr_list["cloud_vv_uuid"]) ]

                else :
                    _call = "list"
                    _instances = self.oskconnstorage[identifier].volumes.list(search_opts = _search_opts)
            
            if len(_instances) > 0 :

                if identifier == "all" :   
                    return _instances
                else :

                    if obj_type == "vv" :
                        return _instances[0]

                    for _instance in _instances :

                        if str(obj_attr_list["is_jumphost"]).lower() == "true" :
                            return _instance
                        else :
                            _metadata = _instance.metadata
    
                            if "experiment_id" in _metadata :
                                if _metadata["experiment_id"] == self.expid :
                                    return _instance
                    return False
            else :
                return False

        except Exception as e :
            _status = 23
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(e)
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

#            _image_list = self.oskconncompute.glance.list()

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += self.get_description()

            _imageid = False

            _candidate_images = []

#            for _idx in range(0,len(_image_list)) :
#                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
#                    if _image_list[_idx].id == obj_attr_list["imageid1"] :
#                        _candidate_images.append(_image_list[_idx])
#                else :
#                    if _image_list[_idx].name.count(obj_attr_list["imageid1"]) :
#                        _candidate_images.append(_image_list[_idx])

            _vmc_name = obj_attr_list["name"]
            _candidate_images = [ self.oskconncompute[_vmc_name].glance.find_image(obj_attr_list["imageid1"]) ]

            if "hypervisor_type" in obj_attr_list :
                if str(obj_attr_list["hypervisor_type"]).lower() != "fake" :
                
                    _hyper = obj_attr_list["hypervisor_type"]
    
                    for _image in list(_candidate_images) :
                        if "hypervisor_type" in _image._info :
                            if _image._info["hypervisor_type"] != obj_attr_list["hypervisor_type"] :
                                _candidate_images.remove(_image)
                            else :
                                _hyper = _image._info["hypervisor_type"]
                else :
                    obj_attr_list["hypervisor_type"] = ''

            if len(_hyper) :
                obj_attr_list["hypervisor_type"] = _hyper
                            
            if len(_candidate_images) :
                if  str(obj_attr_list["randomize_image_name"]).lower() == "true" :
                    _imageid = choice(_candidate_images)
                else :
                    _imageid = _candidate_images[0]

                if _imageid :
                    obj_attr_list["boot_volume_imageid1"] = _imageid.id
                    obj_attr_list["imageid1"] = _imageid.name
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
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        self.oskconncompute[vmc_name].keypairs.create(key_name, \
                                            public_key = key_type + ' ' + key_contents)
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
    def is_vm_running(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try :
            
            _cloud_vm_name = obj_attr_list["cloud_vm_name"]
            
            _instance = self.get_instances(obj_attr_list, "vm", \
                                           _cloud_vm_name)
            if _instance :
                if _instance.status == "ACTIVE" :
                    return _instance

                elif _instance.status == "ERROR" :
                    obj_attr_list["last_known_state"] = "ERROR while checking for ACTIVE state"
                    return True

                else :
                    return False
            else :
                return False

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''
        _instance = self.is_vm_running(obj_attr_list)

        if _instance :

            if obj_attr_list["last_known_state"].count("ERROR") :
                return True            
            
            obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"

            if self.get_ip_address(obj_attr_list, _instance) :
                obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                return True
        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            
        return False

    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''
        _availability_zone = None            
        if len(obj_attr_list["availability_zone"]) > 1 :
            _availability_zone = obj_attr_list["availability_zone"]
                
        if "compute_node" in obj_attr_list and _availability_zone :
#                _scheduler_hints = { "force_hosts" : obj_attr_list["host_name"] }
            for _host in self.oskconncompute[obj_attr_list["name"]].hypervisors.list() :
                if _host.hypervisor_hostname.count(obj_attr_list["compute_node"]) :
                    obj_attr_list["host_name"] = _host.hypervisor_hostname
                    break

            if "host_name" in obj_attr_list :
                _availability_zone += ':' + obj_attr_list["host_name"]
            else :
                _msg = "Unable to find the compute_node \"" + obj_attr_list["compute_node"] 
                _msg += "\", indicated during the instance creation. Will let"
                _msg += " the scheduler pick a compute node"
                cbwarn(_msg)
                
        obj_attr_list["availability_zone"] = _availability_zone        
                        
        return True

    @trace
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["block_device_mapping"] = {}

            _vol_status = "NA"
            if "cloud_vv_type" not in obj_attr_list :
                obj_attr_list["cloud_vv_type"] = None
            if str(obj_attr_list["cloud_vv_type"]).lower() == "none" :
                obj_attr_list["cloud_vv_type"] = None
                
            if "cloud_vv" in obj_attr_list :

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

                _imageid = None
                if str(obj_attr_list["boot_from_volume"]).lower() == "true" :
                    _imageid = obj_attr_list["boot_volume_imageid1"]
                    obj_attr_list["cloud_vv_data_name"] = obj_attr_list["cloud_vv_name"]
                    obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].replace("-vv","-vbv")

                obj_attr_list["last_known_state"] = "about to send volume create request"
                _mark_a = time()
                if str(self.oskconnstorage[obj_attr_list["name"]].version) == '1' :
                    _instance = self.oskconnstorage[obj_attr_list["name"]].volumes.create(obj_attr_list["cloud_vv"], \
                                                                   snapshot_id = None, \
                                                                   display_name = obj_attr_list["cloud_vv_name"], \
                                                                   display_description = obj_attr_list["cloud_vv_name"], \
                                                                   volume_type = obj_attr_list["cloud_vv_type"], \
                                                                   availability_zone = None, \
                                                                   imageRef = _imageid)
                else :
                    _instance = self.oskconnstorage[obj_attr_list["name"]].volumes.create(obj_attr_list["cloud_vv"], \
                                                                   snapshot_id = None, \
                                                                   name = obj_attr_list["cloud_vv_name"], \
                                                                   description = obj_attr_list["cloud_vv_name"], \
                                                                   volume_type = obj_attr_list["cloud_vv_type"], \
                                                                   availability_zone = None, \
                                                                   imageRef = _imageid)

                self.annotate_time_breakdown(obj_attr_list, "create_volume_time", _mark_a)
                
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vv_uuid"] = '{0}'.format(_instance.id)

                _mark_a = time()
                _wait_for_volume = 180
                for i in range(1, _wait_for_volume) :
                    _vol_status = self.oskconnstorage[obj_attr_list["name"]].volumes.get(_instance.id).status
                    if _vol_status == "available" :
                        cbdebug("Volume " + obj_attr_list["cloud_vv_name"] + " took " + str(i) + " second(s) to become available",True)
                        break
                    elif _vol_status == "error" :
                        _fmsg = "Volume " + obj_attr_list["cloud_vv_name"] + " reported error after " + str(i) + " second(s)"
                        break
                    else :
                        sleep(1)
                self.annotate_time_breakdown(obj_attr_list, "volume_available_time", _mark_a)

                if str(obj_attr_list["boot_from_volume"]).lower() == "true" :
                    obj_attr_list["boot_volume_imageid1"] = None                 
                    obj_attr_list['cloud_vv'] = self.oskconnstorage[obj_attr_list["name"]].volumes.get(_instance.id).size 
                    obj_attr_list["block_device_mapping"] = {'vda':'%s' % obj_attr_list["cloud_vv_uuid"]}

            if _vol_status == "error" :
                _status = 17262
            else :
                _status = 0

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
            self.disconnect()
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
                        
            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :

                _instance = self.get_instances(obj_attr_list, "vv", obj_attr_list["cloud_vm_name"])

                if _instance :
    
                    self.common_messages("VV", obj_attr_list, "destroying", 0, '')

                    if len(_instance.attachments) :
                        _server_id = _instance.attachments[0]["server_id"]
                        _attachment_id = _instance.attachments[0]["id"]
                        # There is weird bug on the python novaclient code. Don't change the
                        # following line, it is supposed to be "oskconncompute", even though
                        # is dealing with volumes. Will explain latter.
                        self.oskconncompute[obj_attr_list["name"]].volumes.delete_server_volume(_server_id, _attachment_id)
    
                    self.oskconnstorage[obj_attr_list["name"]].volumes.delete(_instance)
                    
            _status =  0
                    
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
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
                obj_attr_list["credentials"] = self.parse_authentication_data(obj_attr_list["credentials"], \
                                                                              obj_attr_list["tenant"], \
                                                                              obj_attr_list["user"], \
                                                                              True)
                if obj_attr_list["name"] in self.oskconncompute :
                    del self.oskconncompute[obj_attr_list["name"]]

            _mark_a = time()
            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], \
                         {"use_cinderclient" : obj_attr_list["use_cinderclient"]}, \
                         False, \
                         False, \
                         obj_attr_list["name"])
            
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

            if str(obj_attr_list["security_groups"]).lower() == "false" :
                _security_groups = None
            else :
                # "Security groups" must be a list
                _security_groups = []
                _security_groups.append(obj_attr_list["security_groups"])

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            _mark_a = time()
            self.get_flavors(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_flavor_time", _mark_a)
            
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

            _fip = None
            if str(obj_attr_list["use_floating_ip"]).lower() == "true" :
                _msg = "    Attempting to create a floating IP to " + obj_attr_list["name"] + "..."
                cbdebug(_msg, True)

                obj_attr_list["last_known_state"] = "about to create floating IP"
                
                _fip = self.floating_ip_allocate(obj_attr_list)

            _meta["experiment_id"] = obj_attr_list["experiment_id"]

            if "cloud_floating_ip_uuid" in obj_attr_list :
                _meta["cloud_floating_ip_uuid"] = obj_attr_list["cloud_floating_ip_uuid"]

            _time_mark_prs = int(time())
            
            obj_attr_list["mgt_002_provisioning_request_sent"] = \
            _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vvcreate(obj_attr_list)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            self.pre_vmcreate_process(obj_attr_list)

            _mark_a = time()
            _instance = self.oskconncompute[obj_attr_list["name"]].servers.create(name = obj_attr_list["cloud_vm_name"], \
                                                           block_device_mapping = obj_attr_list["block_device_mapping"], \
                                                           image = obj_attr_list["boot_volume_imageid1_instance"], \
                                                           flavor = obj_attr_list["flavor_instance"], \
                                                           security_groups = _security_groups, \
                                                           key_name = obj_attr_list["key_name"], \
                                                           scheduler_hints = None, \
                                                           availability_zone = obj_attr_list["availability_zone"], \
                                                           meta = _meta, \
                                                           config_drive = obj_attr_list["config_drive"], \
                                                           userdata = obj_attr_list["userdata"], \
                                                           nics = _netids, \
                                                           disk_config = "AUTO")

            if _instance :
                self.annotate_time_breakdown(obj_attr_list, "instance_creation_time", _mark_a)
                                
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = '{0}'.format(_instance.id)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                while not self.floating_ip_attach(obj_attr_list, _instance) :
                    True

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
                
                _mark_a = time()
                self.annotate_time_breakdown(obj_attr_list, "instance_scheduling_time", _mark_a)
                _mark_a = time()
                self.annotate_time_breakdown(obj_attr_list, "port_creation_time", _mark_a)
                    
                if obj_attr_list["last_known_state"].count("ERROR") :
                    _fmsg = obj_attr_list["last_known_state"]
                    _status = 189
                else :

                    if not len(obj_attr_list["block_device_mapping"]) and \
                    str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :

                        self.common_messages("VV", obj_attr_list, "attaching", _status, _fmsg)

                        # There is a weird bug on the python novaclient code. Don't change the
                        # following line, it is supposed to be "oskconncompute", even though
                        # is dealing with volumes. Will explain later.
                        _mark_a = time()    
                        self.oskconncompute[obj_attr_list["name"]].volumes.create_server_volume(obj_attr_list["cloud_vm_uuid"], \
                                                                         obj_attr_list["cloud_vv_uuid"], \
                                                                         "/dev/vdd")
    
                        self.annotate_time_breakdown(obj_attr_list, "attach_volume_time", _mark_a)
                        
                        if obj_attr_list["volume_creation_status"] :
                            _status = obj_attr_list["volume_creation_status"]
                            
                    else :
                        _status = 0
 
                    if "admin_credentials" in obj_attr_list :
                        self.connect(obj_attr_list["access"], \
                                     obj_attr_list["admin_credentials"], \
                                     obj_attr_list["vmc_name"], \
                                     {}, 
                                     False, \
                                     False, \
                                     obj_attr_list["name"])

                    self.get_mac_address(obj_attr_list, _instance)

                    self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                    self.get_host_and_instance_name(obj_attr_list)
    
                    if obj_attr_list["tenant"] != "default" :
                        del self.oskconncompute[obj_attr_list["name"]]

                    if "resource_limits" in obj_attr_list :
                        _status, _fmsg = self.set_cgroup(obj_attr_list)
                    else :
                        _status = 0

                    if str(obj_attr_list["force_failure"]).lower() == "true" :
                        _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                        _status = 916

            else :
                _fmsg = "Failed to obtain instance's (cloud assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
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
            self.disconnect()
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
    
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], 
                             {}, \
                             False, \
                             False, \
                             obj_attr_list["name"])

                _wait = int(obj_attr_list["update_frequency"])
                _max_tries = int(obj_attr_list["update_attempts"])
                _curr_tries = 0
                
                _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
    
                if _instance :
    
                    self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                    self.floating_ip_delete(obj_attr_list)
        
                    self.retriable_instance_delete(obj_attr_list, _instance)
    
                    while _instance and _curr_tries < _max_tries :
                        _instance = self.get_instances(obj_attr_list, "vm", \
                                               obj_attr_list["cloud_vm_name"])
                        if _instance :                            
                            if _instance.status != "ACTIVE" :
                                break
                            
                        sleep(_wait)
                        _curr_tries += 1
                                                                    
                else :
                    True
    
                _status, _fmsg = self.vvdestroy(obj_attr_list)
    
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
            self.disconnect()
            _status, _msg = self.common_messages("VM", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace        
    def vmcapture(self, obj_attr_list) :
        '''
        TBD
        '''                
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], \
                         {}, \
                         False, \
                         False, \
                         obj_attr_list["name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')
                _instance.create_image(obj_attr_list["captured_image_name"], None)
                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :
#                    _vm_images = self.oskconncompute[obj_attr_list["name"]].glance.list()
                    _vm_images = self.oskconnimage[obj_attr_list["name"]].images.list()
                    for _vm_image in _vm_images :
                        if _vm_image.name == obj_attr_list["captured_image_name"] :
                            if _vm_image.status.lower() == "active" :
                                _vm_image_created = True
                                _time_mark_crc = int(time())
                                obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    if "mgt_103_capture_request_completed" not in obj_attr_list :
                        obj_attr_list["mgt_999_capture_request_failed"] = int(time()) - _time_mark_crs

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
                cberr(_fmsg)
            else :
                _status = 0
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()   
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
            return _status, _msg
            
    @trace
    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]
    
            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], \
                         {}, \
                         False, \
                         False, \
                         obj_attr_list["name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _instance = self.get_instances(obj_attr_list, "vm", \
                                              obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    _instance.pause()
                elif _ts == "save" :
                    _instance.suspend()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.unpause()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.resume()
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            _status, _msg = self.common_messages("VM", obj_attr_list, "runstate altered", _status, _fmsg)
            return _status, _msg

    @trace        
    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        self.connect(obj_attr_list["access"], \
                     obj_attr_list["credentials"], \
                     obj_attr_list["vmc_name"], \
                     {}, \
                     False, \
                     False, \
                     obj_attr_list["name"])

        operation = obj_attr_list["mtype"]

        _msg = "Sending a " + operation + " request for "  + obj_attr_list["name"]
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
        _msg += "...."
        cbdebug(_msg, True)
        
        # This is a migration, so we need to poll very frequently
        # If it is a micro-checkpointing operation, then poll normally
        _orig_freq = int(obj_attr_list["update_frequency"])
        _wait = 1 if operation == "migrate" else _orig_freq
        _wait = min(_wait, _orig_freq)
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        if _wait < _orig_freq :
            _max_tries = _max_tries * (_orig_freq / _wait) 
        
        _time_mark_crs = int(time())            
        try :
    
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _instance.live_migrate(obj_attr_list["destination_name"].replace("host_", ""))
                
                obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]
                
                while True and _curr_tries < _max_tries : 
                    sleep(_wait)             
                    _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
                    
                    if _instance.status not in ["ACTIVE", "MIGRATING"] :
                        _status = 4328
                        _msg = "Migration of instance failed, " + self.get_description() + " state is: " + _instance.status
                        raise CldOpsException(_msg, _status)
                    
                    if _instance.status == "ACTIVE" :
                        _time_mark_crc = int(time())
                        obj_attr_list["mgt_503_" + operation + "_request_completed"] = _time_mark_crc - _time_mark_crs
                        break

                    _msg = "" + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _msg += "still undergoing " + operation
                    _msg += ". Will wait " + str(_wait)
                    _msg += " seconds and try again."
                    cbdebug(_msg)

                    _curr_tries += 1
            else :
                _fmsg = "This instance does not exist"
                _status = 1098
            
            _status = 0

        except Exception as e :
            _status = 349201
            _fmsg = str(e)
            
        finally :
            self.disconnect()            
            if "mgt_503_" + operation + "_request_completed" not in obj_attr_list :
                obj_attr_list["mgt_999_" + operation + "_request_failed"] = int(time()) - _time_mark_crs

            _status, _msg = self.common_messages("VM", obj_attr_list, operation + "ed ", _status, _fmsg)
            return _status, _msg

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
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], \
                         obj_attr_list, \
                         False, \
                         False, \
                         None)

            _image_list = self.oskconnimage["common"].images.list()
                
            for _image in _image_list :
                if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                    if "hypervisor_type" in obj_attr_list :
                        if str(obj_attr_list["hypervisor_type"]).lower() != "fake" :
                            if "hypervisor_type" in _image._info :
                                if _image._info["hypervisor_type"] == obj_attr_list["hypervisor_type"] :                        
                                    if _image.id == obj_attr_list["imageid1"] :
                                        _image.delete()
                                        break
                        else :
                            if _image.id == obj_attr_list["imageid1"] :
                                _image.delete()
                                break
                    else :
                        if _image.id == obj_attr_list["imageid1"] :
                            _image.delete()
                            break
                else : 
                    if "hypervisor_type" in obj_attr_list :
                        if str(obj_attr_list["hypervisor_type"]).lower() != "fake" :
                            if "hypervisor_type" in _image._info :
                                if _image._info["hypervisor_type"] == obj_attr_list["hypervisor_type"] :
                                    if _image.name == obj_attr_list["imageid1"] :
                                        _image.delete()
                                        break
                        else :
                            if _image.name == obj_attr_list["imageid1"] :
                                _image.delete()
                                break
                    else :
                        if _image.name == obj_attr_list["imageid1"] :
                            _image.delete()
                            break

            obj_attr_list["boot_volume_imageid1"] = _image.id
            obj_attr_list["imageid1"] = _image.name

            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg

    @trace
    def parse_connection_data(self, connection_data, region, obj_attr_list) :
        '''
        TBD
        '''
        _access_url = None
        _endpoint_type = "publicURL"
        _region = region
        
        if not self.connauth_pamap :        
                
            if len(connection_data.split('-')) == 2 :
                _access_url, _endpoint_type = connection_data.split('-')                               
            else :
                _access_url = connection_data.split('-')[0]    
        else :
            if "OS_AUTH_URL" in self.connauth_pamap :
                _access_url = self.connauth_pamap["OS_AUTH_URL"]

            if "OS_ENDPOINT_TYPE" in self.connauth_pamap :
                _endpoint_type = self.connauth_pamap["OS_ENDPOINT_TYPE"]

            if "OS_REGION_NAME" in self.connauth_pamap :
                _region = self.connauth_pamap["OS_REGION_NAME"]

        obj_attr_list["access_from_rc"] = _access_url + '-' + _endpoint_type
        
        return _access_url, _endpoint_type, _region
        
    @trace
    def parse_authentication_data(self, authentication_data, tenant = "default", username = "default", single = False):
        '''
        TBD
        '''

        _username = ''
        _password = ''
        _tenant = ''
        _project_name = None
        # Insecure (don't verify CACERT: _verify = False and _cacert = None)
        # Verify CACERT (_verify = False and _cacert = <valid path to cert file>)
        _cacert = None
        _ckcert = None
        _verify = False
        _user_domain_id = "default"
        _project_domain_id = "default"
        
        if not self.connauth_pamap :
            if authentication_data.count(':') >= 2 :
                _separator = ':'
            else :
                _separator = '-'
    
            if len(authentication_data.split(_separator)) < 3 :
                _msg = "ERROR: Insufficient number of parameters in OSK_CREDENTIALS."
                _msg += "Please make sure that at least username, password and tenant"
                _msg += " are present."
                if single :
                    return _msg
                else :
                    return False, _msg, False, False, False, False, False, False
    
            if len(authentication_data.split(_separator)) == 3 :
                _username, _password, _tenant = authentication_data.split(_separator)
                
            elif len(authentication_data.split(_separator)) == 4 :
                _username, _password, _tenant, _cacert = authentication_data.split(_separator)
                _verify = True
    
            elif len(authentication_data.split(_separator)) == 5 :
                _username, _password, _tenant, _cacert, _ckcert = authentication_data.split(_separator)
                if ( str(_ckcert).lower() == "verify" ) :
                    _verify = True
                elif ( str(_ckcert).lower() == "insecure" ) :
                    _verify = False
                    _cacert = None
                else :
                    _verify = False
                    _cacert = None
    
            elif len(authentication_data.split(_separator)) > 5 and _separator == '-' :            
                _msg = "ERROR: Please make sure that the none of the parameters in"
                _msg += "OSK_CREDENTIALS have any dashes (i.e., \"-\") on it. If"
                _msg += "a dash is required, please use the string \"_dash\", and"
                _msg += "it will be automatically replaced."
                if single :
                    return _msg
                else :
                    return False, _msg, False, False, False, False, False, False
                
        else :

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
                if self.connauth_pamap["OS_INSECURE"] == "1" or str(self.connauth_pamap["OS_INSECURE"]).lower() == "insecure":
                    _verify = False
                    _cacert = None
                else :
                    _verify = True

            if "OS_PROJECT_DOMAIN_ID" in self.connauth_pamap :
                _project_domain_id = self.connauth_pamap["OS_PROJECT_DOMAIN_ID"]

            if "OS_USER_DOMAIN_ID" in self.connauth_pamap :
                _user_domain_id = self.connauth_pamap["OS_USER_DOMAIN_ID"]

        if tenant != "default" :
            _tenant = tenant
        
        if username != "default" :
            _username = username

        _username = _username.replace("_dash_",'-')
        _password = _password.replace("_dash_",'-')
        _tenant = _tenant.replace("_dash_",'-')

        if not _project_name :
            _project_name = _tenant

        if _cacert :
            _cacert = _cacert.replace("_dash_",'-')

        if single :
            _str = str(_username) + ':' + str(_password) + ':' + str(_tenant)

            if _cacert :
                _str += ':' + str(_cacert) 
            if _verify :
                _str += ':' +  str(_verify)

            return _str
        else :
            return _username, _password, _tenant, _project_name, _cacert, _verify, _user_domain_id, _project_domain_id

    @trace
    def disconnect(self) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

#            if self.oskconncompute :
#                self.oskconncompute.novaclientlient.http.close()

#            if self.oskconnstorage and self.use_cinderclient == "true":
#                self.oskconnstorage.novaclientlient.http.close()

#            if self.oskconnnetwork :
#                self.oskconnnetwork.neutronclient.http.close()

            _status = 0

        except AttributeError :
            # If the "close" method does not exist, proceed normally.
            _msg = "The \"close\" method does not exist or is not callable" 
            cbwarn(_msg)
            _status = 0
            
        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = self.get_description() + " disconnection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " disconnection successful."
                cbdebug(_msg)
                return _status, _msg, ''

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
        _uuid = network_attr_list["id"]
        
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
        
        _network_list = self.oskconnnetwork[vmc_name].list_networks()["networks"]

        for _network_attr_list in _network_list :
            self.get_network_attr(obj_attr_list, _network_attr_list)

        return _network_list    
        
    @trace
    def check_floating_pool(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        _floating_pool_found = True

        if str(vm_defaults["create_jumphost"]).lower() != "false" or \
        str(vm_defaults["use_floating_ip"]).lower() != "false" :

            _floating_pool_dict = {}
            for _network in self.oskconnnetwork[vmc_name].list_networks()["networks"] :
                if _network["router:external"] :
                    if _network["name"] not in _floating_pool_dict :
                        _floating_pool_dict[_network["name"]] = _network["id"]
                        
#            _floating_pool_list = self.oskconncompute.floating_ip_pools.list()

            if len(vm_defaults["floating_pool"]) < 2 :
                if len(_floating_pool_dict) == 1 :
                    vm_defaults["floating_pool"] = list(_floating_pool_dict.keys())[0]
#                    vm_defaults["floating_pool"] = _floating_pool_list[0].name
 
                    _msg = "A single floating IP pool (\"" 
                    _msg += vm_defaults["floating_pool"] + "\") was found on this"
                    _msg += " VMC. Will use this as the floating pool."
                    cbdebug(_msg)
    
            _msg = "Checking if the floating pool \""
            _msg += vm_defaults["floating_pool"] + "\" can be found on VMC "
            _msg += vmc_name + "..."
            cbdebug(_msg, True)
            
            _floating_pool_found = False
    
            for _floating_pool in list(_floating_pool_dict.keys()) :
                if _floating_pool == vm_defaults["floating_pool"] :
                    vm_defaults["floating_pool_id"] = _floating_pool_dict[_floating_pool]
                    _floating_pool_found = True                        

#                    if _floating_pool.name == vm_defaults["floating_pool"] :
#                        _floating_pool_found = True
                            
            if not (_floating_pool_found) :
                _msg = "ERROR! Please make sure that the floating IP pool "
                _msg += vm_defaults["floating_pool"] + "\" can be found"
                _msg += " VMC " + vmc_name
                _fmsg = _msg 
                cberr(_msg, True)

        return _floating_pool_found

    @trace
    def check_jumphost(self, vmc_name, vm_defaults, vm_templates, detected_imageids) :
        '''
        TBD
        '''
        _can_create_jumphost = False

        if vm_defaults["jumphost_login"] == "auto" :
            vm_defaults["jumphost_login"] = vm_defaults["login"]

        vm_defaults["jumphost_name"] = vm_defaults["username"] + '-' + vm_defaults["jumphost_base_name"]

        try :
            
            _cjh = str(vm_defaults["create_jumphost"]).lower()
            _jhn = vm_defaults["jumphost_name"]
                       
            if _cjh == "true" :
                vm_defaults["jumphost_ip"] = "to be created"
                                
                _msg = "Checking if a \"Jump Host\" (" + _jhn + ") VM is already" 
                _msg += " present on VMC " + vmc_name + "...."
                cbdebug(_msg, True)

                _obj_attr_list = copy.deepcopy(vm_defaults)

                _obj_attr_list.update(str2dic(vm_templates[vm_defaults["jumphost_role"]]))

                if "floating_pool" in vm_defaults and _obj_attr_list["imageid1"] in detected_imageids :
                    _can_create_jumphost = True

                _obj_attr_list["cloud_vm_name"] = _jhn
                _obj_attr_list["cloud_name"] = ""
                _obj_attr_list["role"] = vm_defaults["jumphost_role"]      
                _obj_attr_list["name"] = "vm_0"
                _obj_attr_list["model"] = "osk"                
                _obj_attr_list["size"] = vm_defaults["jumphost_size"]                        
                _obj_attr_list["use_floating_ip"] = "true"
                _obj_attr_list["randomize_image_name"] = "false"
                _obj_attr_list["experiment_id"] = ""
                _obj_attr_list["mgt_001_provisioning_request_originated"] = int(time())
                _obj_attr_list["vmc_name"] = vmc_name
                _obj_attr_list["ai"] = "none"
                _obj_attr_list["is_jumphost"] = True
                _obj_attr_list["use_jumphost"] = False                
                _obj_attr_list["check_boot_complete"] = "tcp_on_22"
                _obj_attr_list["userdata"] = False
                _obj_attr_list["uuid"] = "00000000-0000-0000-0000-000000000000"
                _obj_attr_list["log_string"] = _obj_attr_list["name"] + " (" + _obj_attr_list["uuid"] + ")"

                _netname = _obj_attr_list["jumphost_netnames"]
                if _netname == "all" :
                    _netname = ','.join(self.networks_attr_list["tenant_network_list"])

                _obj_attr_list["prov_netname"] = _netname
                _obj_attr_list["run_netname"] = _netname
                        
                if not self.is_vm_running(_obj_attr_list) :
                    if _can_create_jumphost :
                        _msg = "                   Creating a \"Jump Host\" (" + _jhn + ") VM on "
                        _msg += " VMC " + vmc_name + ", connected to the networks \"" 
                        _msg += _netname + "\", and attaching a floating IP from pool \""
                        _msg += vm_defaults["floating_pool"] + "\"."
                        #cbdebug(_msg)
                        print(_msg)
                        
                        if "jumphost_ip" in _obj_attr_list :
                            del _obj_attr_list["jumphost_ip"]

                        self.vmcreate(_obj_attr_list)
                        
                    else :
                        _msg = "The jump_host address was set to \"$True\", meaning"
                        _msg += " that a \"cb_jumphost\" VM should be automatically"
                        _msg += " created. However, the \"cb_nullworkload\" is not"
                        _msg += " present on this cloud, and thus the \"cb_jumphost\""
                        _msg += " cannot be created."
                        cberr(_msg, True)
                        return False
                    
                _instance = self.get_instances(_obj_attr_list, "vm", _jhn)
                self.get_ip_address(_obj_attr_list, _instance)

                _msg = "                   A \"Jump Host\" (" + _jhn + ") VM was found, with the floating IP"
                _msg += " address \"" + _obj_attr_list["prov_cloud_ip"] + "\""
                _msg += " already assigned to it"
                #cbdebug(_msg)
                print(_msg)
                
                vm_defaults["jumphost_ip"] = _obj_attr_list["prov_cloud_ip"]

            else :
                return True

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cberr(_fmsg, True)    
            return False
                            
        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)
            return False
            
        except Exception as e :
            _status = 23
            _fmsg = str(e)
            cberr(_fmsg, True)    
            return False
            
        return True
    
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
                
            if "nova-compute" in self.host_map[host]["services"] :
                _function = "compute,"

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
    def get_service_list(self, vmc_name, project) :
        '''
        TBD
        '''
        if project == "compute" :
            return self.oskconncompute[vmc_name].services.list()
        elif project == "volume" and self.use_cinderclient == "true" :
            return self.oskconnstorage[vmc_name].services.list()
        elif project == "network" :
            return self.oskconnnetwork[vmc_name].list_agents()["agents"]
        else :
            return []

    @trace
    def get_service_host(self, service, project) :
        '''
        TBD
        '''
        if project == "compute" or project == "volume" :            
            _service_host = service.host.split('@')[0]
        else :
            _service_host = service["host"]

        try :
            _host, _ip = hostname2ip(_service_host)
            return _host.split('.')[0]

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def get_service_binary(self, service, project) :
        '''
        TBD
        '''
        if project == "compute" or project == "volume" :
            return service.binary
        else :
            return service["binary"]

    @trace
    def build_host_map(self, vmc_name) :
        '''
        TBD
        '''

        try :        
            for _project in ["compute", "volume", "network"] :
    
                for _service in self.get_service_list(vmc_name, _project) :
    
                    _host = self.get_service_host(_service, _project)
                    
                    if _host not in self.host_map :
                        self.host_map[_host] = {}
                        self.host_map[_host]["services"] = []
                        self.host_map[_host]["extended_info"] = False
                        self.host_map[_host]["memory_size"] = "NA"
                        self.host_map[_host]["cores"] = "NA"
                        self.host_map[_host]["hypervisor_type"] = "NA"    
    
                    _name = self.get_service_binary(_service, _project)
    
                    if _name not in self.host_map[_host]["services"] :
                        self.host_map[_host]["services"].append(_name)
    
            for _entry in self.oskconncompute[vmc_name].hypervisors.list() :
                _host = _entry.hypervisor_hostname.split('.')[0]
                if _host not in self.host_map :
                    self.host_map[_host] = {}
                    self.host_map[_host]["services"] = []
                                    
                self.host_map[_host]["extended_info"] = _entry._info
                self.host_map[_host]["memory_size"] = _entry.memory_mb
                self.host_map[_host]["cores"] = _entry.vcpus
                self.host_map[_host]["hypervisor_type"] = _entry.hypervisor_type             
    
            return True

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)
        
    @trace
    def get_flavors(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _flavor_list = self.oskconncompute[obj_attr_list["name"]].flavors.list()

            _status = 168
            _fmsg = "Please check if the defined flavor is present on this "
            _fmsg += self.get_description()

            _flavor = False

            for _idx in range(0,len(_flavor_list)) :
                if _flavor_list[_idx].name == obj_attr_list["size"] :
                    _flavor = _flavor_list[_idx]
                    _status = 0
                    break            

            obj_attr_list["flavor_instance"] = _flavor
            obj_attr_list["flavor"] = _flavor.id

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Flavor (" +  obj_attr_list["size"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return True
            
    @trace
    def get_mac_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''

        try :
            _virtual_interfaces = self.oskconncompute[obj_attr_list["name"]].virtual_interfaces.list(instance.id)
            if _virtual_interfaces and len(_virtual_interfaces) :
                obj_attr_list["cloud_mac"] = _virtual_interfaces[0].mac_address
        except :
            obj_attr_list["cloud_mac"] = "ERROR"

        return True

    @trace
    def get_host_and_instance_name(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        
        # There is a lot of extra information that can be obtained through
        # the "_info" attribute. However, a new connection has to be 
        # established to access the most up-to-date data on this attribute
        # Not sure how stable it will be with newer versions of the API. 
        _instance = self.is_vm_running(obj_attr_list, fail = fail)

        if _instance :


            obj_attr_list["instance_name"] = "unknown" 
            obj_attr_list["host_name"] = "unknown"

            try :                   
                obj_attr_list["instance_name"] = getattr(_instance, 'OS-EXT-SRV-ATTR:instance_name')                        
                obj_attr_list["host_name"] = getattr(_instance, 'OS-EXT-SRV-ATTR:host')
            except :
                pass
            
#            if "_info" in dir(_instance) :

#                if "OS-EXT-SRV-ATTR:host" in _instance._info :
#                    obj_attr_list["host_name"] = _instance._info['OS-EXT-SRV-ATTR:host'].split('.')[0]
#                else :
#                    obj_attr_list["host_name"] = "unknown"
                
#                if "OS-EXT-SRV-ATTR:instance_name" in _instance._info :
#                    obj_attr_list["instance_name"] = _instance._info['OS-EXT-SRV-ATTR:instance_name']
#                else :
#                    obj_attr_list["instance_name"] = "unknown"
#            else :
#                obj_attr_list["instance_name"] = "unknown"            
#                obj_attr_list["host_name"] = "unknown"                    
        else :
            obj_attr_list["instance_name"] = "unknown"            
            obj_attr_list["host_name"] = "unknown"
        return True

    @trace
    def get_instance_deployment_time(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        _instance = self.is_vm_running(obj_attr_list, fail)

        _created = False
        _launched = False
              
        if _instance :
            if "_info" in dir(_instance) :
                if "created" in _instance._info :
                    _created = iso8601.parse_date(_instance._info["created"])
                    
                if "S-SRV-USG:launched_at" in _instance._info :
                    _launched = iso8601.parse_date(_instance._info["OS-SRV-USG:launched_at"])

            if _created and _launched :

                _mgt_003 = (_launched - _created).total_seconds()
            
                obj_attr_list["comments"] += " Actual time spent waiting for instance"
                obj_attr_list["comments"] += " to become active was "
                obj_attr_list["comments"] += str(obj_attr_list["mgt_003_provisioning_request_completed"])
                obj_attr_list["comments"] += ". "
                obj_attr_list["mgt_003_provisioning_request_completed"] = int(_mgt_003)
            
        return True

    @trace
    def floating_ip_allocate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _call = "NAfpc"
            identifier = obj_attr_list["cloud_vm_name"]
            
            if not self.oskconnnetwork :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {}, \
                             False, \
                             False, \
                             obj_attr_list["name"])

            _fip = False

            if not _fip :
                _call = "floating ip create"
                _mark_a = time()
                _fip_h = self.oskconnnetwork[obj_attr_list["name"]].create_floatingip({"floatingip": {"floating_network_id": obj_attr_list["floating_pool_id"]}}) 
#                _fip_h = self.oskconncompute.floating_ips.create(obj_attr_list["floating_pool"])
                self.annotate_time_breakdown(obj_attr_list, "create_fip_time", _mark_a)
                obj_attr_list["cloud_floating_ip_address"] = _fip_h["floatingip"]["floating_ip_address"]
                obj_attr_list["cloud_floating_ip_uuid"] = _fip_h["floatingip"]["id"]

                _fip = obj_attr_list["cloud_floating_ip_address"]
                
            return _fip

        except Exception as e :
            _status = 23
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(e)

            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > 3 :            
                raise CldOpsException(_fmsg, _status)
            else :
                cbwarn(_fmsg)
                return False

    @trace
    def floating_ip_delete(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _call = "NAfpd"
            identifier = obj_attr_list["cloud_vm_name"]
            
            self.connect(obj_attr_list["access"], \
                         obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], \
                         {}, \
                         False, \
                         False, \
                         obj_attr_list["name"])

            if "cloud_floating_ip_uuid" in obj_attr_list :
                _call = "floating ip delete"
                self.oskconnnetwork[obj_attr_list["name"]].delete_floatingip(obj_attr_list["cloud_floating_ip_uuid"])                
            return True

        except Exception as e :
            _status = 23
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(e)

            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > 3 :            
                raise CldOpsException(_fmsg, _status)
            else :
                cbwarn(_fmsg)
                return False
    
    @trace
    def floating_ip_attach(self, obj_attr_list, _instance) :
        '''
        TBD
        '''

        try :
            
            _call = "NAfpa"
            identifier = obj_attr_list["cloud_vm_name"]

            if str(obj_attr_list["use_floating_ip"]).lower() == "true" :
                _msg = "    Attempting to attach a floating IP to " + obj_attr_list["name"] + "..."
                cbdebug(_msg, True)
                                
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])
                _wait = int(obj_attr_list["update_frequency"])

                obj_attr_list["last_known_state"] = "about to attach floating IP"

                _vm_ready = False
                while _curr_tries < _max_tries :
                    _vm_ready = self.is_vm_running(obj_attr_list)

                    if _vm_ready :
                        break
                    else :
                        _curr_tries += 1
                        sleep(_wait)

                _call = "floating ip attach"
                _mark_a = time()                
                if "hypervisor_type" in obj_attr_list and obj_attr_list["hypervisor_type"].lower() == "fake" :
                    True
                else :
                    
                    try :
                        update_info = {"port_id":_instance.interface_list()[0].id}
                        self.oskconnnetwork.update_floatingip(obj_attr_list["cloud_floating_ip_uuid"], {"floatingip": update_info})
                    except :
                        _instance.add_floating_ip(obj_attr_list["cloud_floating_ip_address"])
                    
                    self.annotate_time_breakdown(obj_attr_list, "attach_fip_time", _mark_a)

            return True

        except novaclient.exceptions as obj:
            _status = int(obj.error_code)
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(obj.error_message)

            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                cbwarn(_fmsg)
                return False

        except Exception as e :
            _status = 23
            _fmsg = "(While getting instance(s) through API call \"" + _call + "\") " + str(e)

            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > 3 :            
                raise CldOpsException(_fmsg, _status)
            else :
                cbwarn(_fmsg)
                return False
            
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

            _vminstance.delete()
            sleep(20)

            if "cloud_vv" in obj_attr_list :
                self.vvdestroy(obj_attr_list)
        
        if obj_attr_list["volume_creation_status"] :
            obj_attr_list["instance_creation_failure_message"] += "VOLUME ERROR MESSAGE:" + obj_attr_list["volume_creation_failure_message"] + ".\n"

        return 0, obj_attr_list["instance_creation_failure_message"]

    @trace
    def retriable_instance_delete(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        try :
            if "cloud_vm_name" in obj_attr_list :
                identifier = obj_attr_list["cloud_vm_name"]
            else :
                identifier = instance.name
            instance.delete()
            return True

        except Exception as e :
            _status = 23
            _fmsg = "(While removing instance(s) through API call \"delete\") " + str(obj.error_message)
            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                return False
