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

from novaclient import client as novac

#try :
#    from novaclient.v2 import client as novac
#except :
#    from novaclient.v1_1 import client as novac

from novaclient import exceptions as novaexceptions

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, value_suffix
from lib.remote.network_functions import hostname2ip, validIPv4
from lib.remote.process_management import ProcessManagement
from lib.remote.ssh_ops import get_ssh_key
from shared_functions import CldOpsException, CommonCloudFunctions 

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
        self.oskconncompute = False
        self.oskconnstorage = False
        self.expid = expid
        self.ft_supported = False
        self.lvirt_conn = {}
        self.networks_attr_list = { "tenant_network_list":[] }
        self.host_map = {}
        self.api_error_counter = {}
        self.max_api_errors = 10
        
    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack Compute Cloud"

    def parse_authentication_data(self, authentication_data, tenant = "default", username = "default", single = False):
        '''
        TBD
        '''
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
                return False, _msg, False, False, False

        if len(authentication_data.split(_separator)) == 3 :
            _username, _password, _tenant = authentication_data.split(_separator)
            _cacert = None
            _insecure = False
            
        elif len(authentication_data.split(_separator)) == 4 :
            _username, _password, _tenant, _cacert = authentication_data.split(_separator)
            _insecure = False
            
        elif len(authentication_data.split(_separator)) == 5 :
            _username, _password, _tenant, _cacert, _insecure = authentication_data.split(_separator)
            _insecure = True

        elif len(authentication_data.split(_separator)) > 5 and _separator == '-' :            
            _msg = "ERROR: Please make sure that the none of the parameters in"
            _msg += "OSK_CREDENTIALS have any dashes (i.e., \"-\") on it. If"
            _msg += "a dash is required, please use the string \"_dash\", and"
            _msg += "it will be automatically replaced."
            if single :
                return _msg
            else :
                return False, _msg, False, False, False
            
        else :
            _username = ''
            _password = ''
            _tenant = ''

        if tenant != "default" :
            _tenant = tenant
        
        if username != "default" :
            _username = username

        if single :
            _str = str(_username) + ':' + str(_password) + ':' + str(_tenant)

            if _cacert :
                _str += ':' + str(_cacert) 
            if _insecure :
                _str += ':' +  str(_insecure)

            return _str
        else :
            return _username, _password, _tenant, _cacert, _insecure
        
    @trace
    def connect(self, access_url, authentication_data, region, extra_parms = {}, diag = False, generate_rc = False) :
        '''
        TBD
        '''        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if len(access_url.split('-')) == 1 :
                _endpoint_type = "publicURL"
            if len(access_url.split('-')) == 2 :
                access_url, _endpoint_type = access_url.split('-')                               
            else :
                access_url = access_url.split('-')[0]
                _endpoint_type = "publicURL"
            access_url = access_url.replace("_dash_",'-')
            
            _data_auth_parse = False
            _username, _password, _tenant, _cacert, _insecure = \
            self.parse_authentication_data(authentication_data)
            _data_auth_parse = True
            
            if not _username :
                _fmsg = _password
            else :
                _username = _username.replace("_dash_",'-')
                _password = _password.replace("_dash_",'-')
                _tenant = _tenant.replace("_dash_",'-')

                if _cacert :
                    _cacert = _cacert.replace("_dash_",'-')
    
                _msg = "OpenStack connection parameters: username=" + _username
                _msg += ", password=<omitted>, tenant=" + _tenant + ", "
                _msg += "cacert=" + str(_cacert) + ", insecure=" + str(_insecure)
                _msg += ", region_name=" + region + ", access_url=" + access_url
                _msg += ", endpoint_type=" + str(_endpoint_type)
                cbdebug(_msg, diag)
    
                _fmsg = "About to attempt a connection to OpenStack"
    
                self.oskconncompute = novac.Client(2, _username, _password, _tenant, \
                                             access_url, region_name = region, \
                                             service_type="compute", \
                                             endpoint_type = _endpoint_type, \
                                             cacert = _cacert, \
                                             insecure = _insecure)
    
                self.oskconncompute.flavors.list()
    
                if "use_cinderclient" in extra_parms :
                    self.use_cinderclient = str(extra_parms["use_cinderclient"]).lower()
                else :
                    self.use_cinderclient = "false"
    
                if self.use_cinderclient == "true" :
                    # At the moment, we're still making cinder call from nova.                
                    self.oskconnstorage = novac.Client(2, _username, _password, _tenant, \
                                                 access_url, region_name=region, \
                                                 service_type="volume", \
                                                 endpoint_type = _endpoint_type, \
                                                 cacert = _cacert, \
                                                 insecure = _insecure)
        
                    self.oskconnstorage.volumes.list()                
                
                if "use_neutronclient" in extra_parms :
                    self.use_neutronclient = str(extra_parms["use_neutronclient"]).lower()
                else :
                    self.use_neutronclient = "false"
                
                if self.use_neutronclient == "true" :
    
                    from neutronclient.v2_0 import client as neutronc                           
                    
                    self.oskconnnetwork = neutronc.Client(username = _username, \
                                                          password = _password, \
                                                          tenant_name = _tenant, \
                                                          auth_url = access_url, \
                                                          region_name = region, \
                                                          service_type="network", \
                                                          endpoint_type = _endpoint_type, \
                                                          cacert = _cacert, \
                                                          insecure = _insecure)
        
                    self.oskconnnetwork.list_networks()
                else :
                    self.oskconnnetwork = False
                
                _region = region
                _msg = "Selected region is " + str(region)
                cbdebug(_msg)

                if generate_rc :
                    if "cloud_name" in extra_parms :
                        _file = expanduser("~") + "/cbrc-" + extra_parms["cloud_name"].lower()
                    else :
                        _file = expanduser("~") + "/cbrc"
                        
                    _file_fd = open(_file, 'w')

                    _file_fd.write("export OS_TENANT_NAME=" + _tenant + "\n")
                    _file_fd.write("export OS_USERNAME=" + _username + "\n")
                    _file_fd.write("export OS_PASSWORD=" + _password + "\n")                    
                    _file_fd.write("export OS_AUTH_URL=\"" + access_url + "\"\n")
                    _file_fd.write("export OS_NO_CACHE=1\n")
#                    _file_fd.write("export OS_INTERFACE=" + _endpoint_type.replace("URL",'') +  "\n")
                    _file_fd.write("export OS_INTERFACE=admin\n")                        
                    if _cacert :
                        _file_fd.write("export OS_CACERT=" + _cacert + "\n")
                    _file_fd.write("export OS_REGION_NAME=" + region + "\n")

                    if "cloud_name" in extra_parms :                        
                        _file_fd.write("export CB_CLOUD_NAME=" + extra_parms["cloud_name"] + "\n")
                        _file_fd.write("export CB_USERNAME=" + extra_parms["username"] + "\n")
                    _file_fd.close()
                
                _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "OpenStack connection failure: " + _fmsg
                cberr(_msg)
                if _data_auth_parse :
                    _dmsg = "Please attempt to execute the following : \"python -c \""
                    _dmsg += "from novaclient import client as novac;"
                    _dmsg += "ct = novac.Client(2, '" + str(_username) + "', '"
                    _dmsg += "REPLACE_PASSWORD', '" + str(_tenant) + "', '" + str(access_url)
                    _dmsg += "', region_name='" + str(region) + "', service_type='compute', "
                    _dmsg += "endpoint_type='" + str(_endpoint_type) + "', cacert='" + str(_cacert)
                    _dmsg += "', insecure='" + str(_insecure) + "'); ct.flavors.list()\""
                    print _dmsg
                    
                raise CldOpsException(_msg, _status)
            else :
                _msg = "OpenStack connection successful."
                cbdebug(_msg)
                return _status, _msg, _region

    @trace
    def disconnect(self) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if self.oskconncompute :
                self.oskconncompute.novaclient.http.close()


            if self.oskconnstorage and self.use_cinderclient == "true":
                self.oskconnstorage.novaclient.http.close()


            if self.oskconnnetwork :
                self.oskconnnetwork.neutronclient.http.close()

            _status = 0

        except novaexceptions, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except AttributeError :
            # If the "close" method does not exist, proceed normally.
            _msg = "The \"close\" method does not exist or is not callable" 
            cbwarn(_msg)
            _status = 0
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "OpenStack disconnection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "OpenStack disconnection successful."
                cbdebug(_msg)
                return _status, _msg, ''
    
    def check_ssh_key(self, vmc_name, key_name, vm_defaults, internal = False) :
        '''
        TBD
        '''

        _key_pair_found = False      
        
        if not key_name :
            _key_pair_found = True
        else :
            _msg = "\n OpenStack status: Checking if the ssh key pair \"" + key_name + "\" is created"
            _msg += " on VMC " + vmc_name + "...."            
            if not internal :
                print _msg,
            else :
                cbdebug(_msg)            
            
            _key_pair_found = False

            _pub_key_fn = vm_defaults["credentials_dir"] + '/'
            _pub_key_fn += vm_defaults["ssh_key_name"] + ".pub"

            _pub_key_fn = vm_defaults["credentials_dir"] + '/'
            _pub_key_fn += vm_defaults["ssh_key_name"] + ".pub"

            _key_type, _key_contents, _key_fingerprint = get_ssh_key(_pub_key_fn)
            
            if not _key_contents :
                _fmsg = _key_type 
                cberr(_fmsg, True)
                return False
            
            _key_pair_found = False

            for _key_pair in self.oskconncompute.keypairs.list() :

                if _key_pair.name == key_name :
                    _msg = "A key named \"" + key_name + "\" was found "
                    _msg += "on VMC " + vmc_name + ". Checking if the key"
                    _msg += " contents are correct."
                    cbdebug(_msg)
                    
                    _key2 = _key_pair.public_key.split()[1]
                    
                    if len(_key_contents) > 1 and len(_key2) > 1 :
                        if _key_contents == _key2 :
                            _msg = "The contents of the key \"" + key_name
                            _msg += "\" on the VMC " + vmc_name + " and the"
                            _msg += " one present on directory \"" 
                            _msg += vm_defaults["credentials_dir"] + "\" ("
                            _msg += vm_defaults["ssh_key_name"] + ") are the same."
                            cbdebug(_msg)
                            _key_pair_found = True
                            break
                        
                        else :
                            _msg = "The contents of the key \"" + key_name
                            _msg += "\" on the VMC " + vmc_name + " and the"
                            _msg += " one present on directory \"" 
                            _msg += vm_defaults["credentials_dir"] + "\" ("
                            _msg += vm_defaults["ssh_key_name"] + ") differ."
                            _msg += "Will delete the key on OpenStack"
                            _msg += " and re-created it"
                            cbdebug(_msg)
                            self.oskconncompute.keypairs.delete(_key_pair)
                            break

            if not _key_pair_found :

                _msg = "\n Openstack status: Creating the ssh key pair \"" + key_name + "\""
                _msg += " on VMC " + vmc_name + ", using the public key \""
                _msg += _pub_key_fn + "\"..."
                if not internal :
                    print _msg,
                else :
                    cbdebug(_msg)

                self.oskconncompute.keypairs.create(key_name, \
                                                    public_key = _key_type + ' ' + _key_contents)

                _key_pair_found = True
            else :
                _msg = "done\n"
                if not internal :
                    print _msg,
                
            return _key_pair_found

    def check_security_group(self,vmc_name, security_group_name) :
        '''
        TBD
        '''

        _security_group_name = False
        
        if security_group_name :

            _msg = " OpenStack status: Checking if the security group \"" + security_group_name
            _msg += "\" is created on VMC " + vmc_name + "...."
            #cbdebug(_msg)
            print _msg,
            
            _security_group_found = False
            for security_group in self.oskconncompute.security_groups.list() :
                if security_group.name == security_group_name :
                    _security_group_found = True
                    _msg = "done\n"
                    print _msg
            
            if not _security_group_found :
                _msg = "ERROR! Please create the security group \"" 
                _msg += security_group_name + "\" in "
                _msg += "OpenStack before proceeding."
                _fmsg = _msg 
                cberr(_msg, True)
        else :
            _security_group_found = True

        return _security_group_found

    def check_floating_pool(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        _floating_pool_found = True

        _floating_pool_list = self.oskconncompute.floating_ip_pools.list()

        if len(vm_defaults["floating_pool"]) < 2 :
            if len(_floating_pool_list) == 1 :
                vm_defaults["floating_pool"] = _floating_pool_list[0].name
                
                _msg = "A single floating IP pool (\"" 
                _msg += vm_defaults["floating_pool"] + "\") was found on this"
                _msg += " VMC. Will use this as the floating pool."
                cbdebug(_msg)

        _msg = " OpenStack status: Checking if the floating pool \""
        _msg += vm_defaults["floating_pool"] + "\" can be found on VMC "
        _msg += vmc_name + "..."
        #cbdebug(_msg)
        print _msg,
        
        _floating_pool_found = False

        for _floating_pool in _floating_pool_list :
            if _floating_pool.name == vm_defaults["floating_pool"] :
                _floating_pool_found = True
                        
        if not (_floating_pool_found) :
            _msg = "ERROR! Please make sure that the floating IP pool "
            _msg += vm_defaults["floating_pool"] + "\" can be found"
            _msg += " VMC " + vmc_name
            _fmsg = _msg 
            cberr(_msg, True)
        else :
            _msg = "done"
            print _msg            

        return _floating_pool_found

    def get_network_attr(self, obj_attr_list, network_attr_list) :
        '''
        TBD
        '''

        if "use_neutronclient" in obj_attr_list :
            _use_neutronclient = str(obj_attr_list["use_neutronclient"]).lower()
                            
        if _use_neutronclient == "true" :
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
        else :
            _name = network_attr_list.label
            _uuid = network_attr_list.id 
            if _name.count("ext") :
                _model = "external"
            else :
                _model = "tenant"
            _type = "NA"

        self.networks_attr_list[_name] = {"uuid" : _uuid, "model" : _model, \
                                           "type" : _type }
        
        if _model == "tenant" :
            if _name not in self.networks_attr_list["tenant_network_list"] :
                self.networks_attr_list["tenant_network_list"].append(_name)
                        
        return True
    
    def get_network_list(self, obj_attr_list) :
        '''
        TBD
        '''
        if "use_neutronclient" in obj_attr_list :
            _use_neutronclient = str(obj_attr_list["use_neutronclient"]).lower()
            
        if _use_neutronclient == "false" :
            _network_list = self.oskconncompute.networks.list()
        else :
            _network_list = self.oskconnnetwork.list_networks()["networks"]
        
        for _network_attr_list in _network_list :
            self.get_network_attr(obj_attr_list, _network_attr_list)

        return _network_list
    
    def check_networks(self, vmc_name, vm_defaults) :
        '''
        TBD
        '''
        _prov_netname = vm_defaults["netname"]
        _run_netname = vm_defaults["netname"]

        _net_str = "network \"" + _prov_netname + "\""
        
        _msg = " OpenStack status: Checking if the " + _net_str + " can be found on VMC " + vmc_name + "..."
        #cbdebug(_msg)        
        print _msg, 

        self.get_network_list(vm_defaults)
                        
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
                _msg = "done. This " + _net_str + " network will be used as the default for provisioning."
                cbdebug(_msg)
                print _msg
            else: 
                _msg = "\nERROR! The default provisioning network (" 
                _msg += _prov_netname + ") cannot be an external network"
                cbdebug(_msg)
                print _msg

        if _run_netname in self.networks_attr_list :
            _net_model = self.networks_attr_list[_run_netname]["model"]
            _net_type = self.networks_attr_list[_run_netname]["model"]
            
            if _net_model != "external" :
                _run_netname_found = True
                if _net_type == _net_model :
                    _net_str = _net_type
                else :
                    _net_str = _net_type + ' ' + _net_model                
                _msg = "a " + _net_type + ' ' + _net_model + " network will be used as the default for running."
                cbdebug(_msg)
            else: 
                _msg = "ERROR! The default running network (" 
                _msg += _run_netname + ") cannot be an external network"
                cbdebug(_msg)
                print _msg
                                               
        if not (_run_netname_found and _prov_netname_found) :
            _msg = "ERROR! Please make sure that the " + _net_str + " can be found"
            _msg += " VMC " + vmc_name
            _fmsg = _msg 
            cberr(_msg, True)

        return _prov_netname_found, _run_netname_found

    def check_images(self, vmc_name, vm_templates) :
        '''
        TBD
        '''
        _msg = " OpenStack status: Checking if the imageids associated to each \"VM role\" are"
        _msg += " registered on VMC " + vmc_name + "...."
        #cbdebug(_msg)
        print _msg,

        _registered_image_list = self.oskconncompute.images.list()
        _registered_imageid_list = []

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image.name)

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
                _msg += "zWARNING Image id for VM roles \""
                _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                _msg += _imageid + "\" is NOT registered "
                _msg += "(attaching VMs with any of these roles will result in error).\n"

        if not len(_detected_imageids) :
            _msg = "ERROR! None of the image ids used by any VM \"role\" were detected"
            _msg += " in this OpenStack cloud. Please register at least one "
            _msg += "of the following images: " + ','.join(_undetected_imageids.keys())
            cberr(_msg, True)
        else :
            _cmsg = "done"
            print _cmsg
            
            _msg = _msg.replace("yz",'')
            _msg = _msg.replace('z',"         ")
            _msg = _msg[:-2]
            if len(_msg) :
                cbdebug(_msg, True)        

        return _detected_imageids

    def check_jumphost(self, vmc_name, vm_defaults, vm_templates, detected_imageids) :
        '''
        TBD
        '''
        _can_create_jumphost = False

        if vm_defaults["jumphost_login"] == "auto" :
            vm_defaults["jumphost_login"] = vm_defaults["login"]

        vm_defaults["jumphost_name"] = vm_defaults["username"] + '-' + vm_defaults["jumphost_base_name"]

        if "floating_pool" in vm_defaults and "cb_nullworkload" in detected_imageids :
            _can_create_jumphost = True

        try :
            _cjh = str(vm_defaults["create_jumphost"]).lower()
            _jhn = vm_defaults["jumphost_name"]
                       
            if _cjh == "true" :
                vm_defaults["jumphost_ip"] = "to be created"
                                
                _msg = " OpenStack status: Checking if a \"Jump Host\" (" + _jhn + ") VM is already" 
                _msg += " present on VMC " + vmc_name + "...."
                #cbdebug(_msg)
                print _msg

                _obj_attr_list = copy.deepcopy(vm_defaults)

                _obj_attr_list.update(str2dic(vm_templates["tinyvm"]))
                _obj_attr_list["cloud_vm_name"] = _jhn
                _obj_attr_list["cloud_name"] = ""
                _obj_attr_list["role"] = "nullworkload"                        
                _obj_attr_list["name"] = "vm_0"
                _obj_attr_list["size"] = "m1.tiny"                                         
                _obj_attr_list["use_floating_ip"] = "true"
                _obj_attr_list["randomize_image_name"] = "false"
                _obj_attr_list["experiment_id"] = ""
                _obj_attr_list["mgt_001_provisioning_request_originated"] = int(time())
                _obj_attr_list["vmc_name"] = vmc_name
                _obj_attr_list["ai"] = "none"
                _obj_attr_list["is_jumphost"] = True
                _obj_attr_list["use_jumphost"] = False                
                _obj_attr_list["check_boot_complete"] = "tcp_on_22"
                _obj_attr_list["userdata"] = None

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
                        print _msg
                        
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
                print _msg
                
                vm_defaults["jumphost_ip"] = _obj_attr_list["prov_cloud_ip"]

            else :
                return True
            
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cberr(_fmsg, True)    
            return False
        
        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            cberr(_fmsg, True)    
            return False
                            
        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)
            return False
            
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            cberr(_fmsg, True)    
            return False
            
        return True
    
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vm_defaults, True, True)

            _key_pair_found = self.check_ssh_key(vmc_name, \
                                                 vm_defaults["username"] + '_' + vm_defaults["tenant"] + '_' + key_name, vm_defaults)

            _security_group_found = self.check_security_group(vmc_name, security_group_name)

            if str(vm_defaults["create_jumphost"]).lower() != "false" or str(vm_defaults["use_floating_ip"]).lower() != "false" :
                _floating_pool_found = self.check_floating_pool(vmc_name, vm_defaults)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)

            _detected_imageids = self.check_images(vmc_name, vm_templates)

            _check_jumphost = self.check_jumphost(vmc_name, vm_defaults, vm_templates, _detected_imageids)
            
            if not (_run_netname_found and _prov_netname_found and \
                    _key_pair_found and _security_group_found and \
                    len(_detected_imageids) and _check_jumphost) :
                _msg = "Check the previous errors, fix it (using OpenStack's web"
                _msg += " GUI (horizon) or nova CLI"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            _status = 0

        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            self.disconnect()
            if _status :
                _msg = "VMC \"" + vmc_name + "\" did not pass the connection test."
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC \"" + vmc_name + "\" was successfully tested.\n"
                cbdebug(_msg, True)
                return _status, _msg

    def discover_hosts(self, obj_attr_list, start) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            self.build_host_map()
            _host_list = self.host_map.keys()

            obj_attr_list["host_count"] = len(_host_list)

            for _host in _host_list :
                self.add_host(obj_attr_list, _host, start)

            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]
                        
            self.additional_host_discovery (obj_attr_list)
            self.populate_interface(obj_attr_list)
            
            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)
                    
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :

            self.disconnect()    
            if _status :
                _msg = "HOSTS belonging to VMC " + obj_attr_list["name"] + " could not be "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = str(obj_attr_list["host_count"]) + "HOSTS belonging to "
                _msg += "VMC " + obj_attr_list["name"] + " were successfully "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                cbdebug(_msg)
                return _status, _msg

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
            obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_queried_host_name)

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

            _status = 0
            
        except CldOpsException, obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)

        except socket.gaierror, e :
            _status = 453
            _fmsg = "While adding hosts, CB needs to resolve one of the "
            _fmsg += "OpenStack host names: " + _queried_host_name + ". "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."
                    
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "HOSTS belonging to VMC " + obj_attr_list["name"] + " could not be "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = str(obj_attr_list["host_count"]) + "HOSTS belonging to "
                _msg += "VMC " + obj_attr_list["name"] + " were successfully "
                _msg += "discovered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                cbdebug(_msg)
                return _status, _msg        

    def get_service_list(self, project) :
        '''
        TBD
        '''
        if project == "compute" :
            return self.oskconncompute.services.list()
        elif project == "volume" and self.use_cinderclient == "true" :
            return self.oskconnstorage.services.list()
        elif project == "network" :
            return self.oskconnnetwork.list_agents()["agents"]        
        else :
            return []

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
        
        except socket.gaierror:
            _status = 1200
            _fmsg = "The Hostname \"" + _service_host + "\" - used by the OpenSTack"
            _fmsg += " Controller - is not mapped to an IP. "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."
            cberr(_fmsg, True)
            raise CldOpsException(_fmsg, _status)

    def get_service_binary(self, service, project) :
        '''
        TBD
        '''
        if project == "compute" or project == "volume" :
            return service.binary
        else :
            return service["binary"]

    def build_host_map(self) :
        '''
        TBD
        '''

        try :        
            for _project in ["compute", "volume", "network"] :
    
                for _service in self.get_service_list(_project) :
    
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
    
            for _entry in self.oskconncompute.hypervisors.list() :
                _host = _entry.hypervisor_hostname.split('.')[0]
                if _host not in self.host_map :
                    self.host_map[_host] = {}
                    self.host_map[_host]["services"] = []
                                    
                self.host_map[_host]["extended_info"] = _entry._info
                self.host_map[_host]["memory_size"] = _entry.memory_mb
                self.host_map[_host]["cores"] = _entry.vcpus
                self.host_map[_host]["hypervisor_type"] = _entry.hypervisor_type             
    
            return True

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"], 
                             {"use_neutronclient" : str(obj_attr_list["use_neutronclient"]), \
                              "use_cinderclient" : str(obj_attr_list["use_cinderclient"])})

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            _msg = "Removing all VMs previously created on VMC \""
            _msg += obj_attr_list["name"] + "\" (only VM names starting with"
            _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
            _msg += "\")....."
            cbdebug(_msg, True)
            _running_instances = True
            
            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False
                
                _criteria = {}                              
                _criteria['all_tenants'] = 1                
                _instances = self.oskconncompute.servers.list(search_opts = _criteria)
                
                for _instance in _instances :
                    if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) \
                    and not _instance.name.count("jumphost") :

                        _running_instances = True
                        if  _instance.status == "ACTIVE" :
                            _msg = "Terminating instance: " 
                            _msg += _instance.id + " (" + _instance.name + ")"
                            cbdebug(_msg, True)
                            
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
                _msg = "Removing all VVs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VV names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)
                _volumes = self.oskconnstorage.volumes.list()
    
                for _volume in _volumes :
                    if "display_name" in dir(_volume) :
                        _volume_name = _volume.display_name
                    else :
                        _volume_name = _volume.name
                        
                    if _volume_name :
                        if _volume_name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                            _volume.delete()

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.status)
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
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
                                                 True)
    
                obj_attr_list["cloud_hostname"] = _hostname

                _resolve = obj_attr_list["access"].split(':')[1].replace('//','')
                _resolve = _resolve.split('/')[0]
                _resolve = _resolve.replace("_dash_","-")

                _x, obj_attr_list["cloud_ip"] = hostname2ip(_resolve)
                obj_attr_list["arrival"] = int(time())
    
                if str(obj_attr_list["discover_hosts"]).lower() == "true" :                   
                    _msg = "Discovering hosts on VMC \"" + obj_attr_list["name"] + "\"....."
                    cbdebug(_msg, True)
                    _status, _fmsg = self.discover_hosts(obj_attr_list, _time_mark_prs)
                else :
                    obj_attr_list["hosts"] = ''
                    obj_attr_list["host_list"] = {}
                    obj_attr_list["host_count"] = "NA"

                self.get_network_list(obj_attr_list)

                _networks = {}
                for _net in self.networks_attr_list.keys() :
                    if "type" in self.networks_attr_list[_net] :
                        _type = self.networks_attr_list[_net]["type"]

                        obj_attr_list["network_" + _net] = _type
                        
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except socket.herror:
            _status = 1200
            _fmsg = "The IP address \"" + _resolve + "\" - used by the OpenSTack"
            _fmsg += " Controller - is not mapped to a Hostname. "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."

        except socket.gaierror:
            _status = 1200
            _fmsg = "The Hostname \"" + _resolve + "\" - used by the OpenSTack"
            _fmsg += " Controller - is not mapped to an IP. "
            _fmsg += "Please make sure this name is resolvable either in /etc/hosts or DNS."
                        
        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def get_flavors(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _flavor_list = self.oskconncompute.flavors.list()

            _status = 168
            _fmsg = "Please check if the defined flavor is present on this "
            _fmsg += "OpenStack Cloud"

            _flavor = False
            for _idx in range(0,len(_flavor_list)) :
                if _flavor_list[_idx].name.count(obj_attr_list["size"]) :
                    _flavor = _flavor_list[_idx]
                    _status = 0
                    break

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Flavor (" +  obj_attr_list["size"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _flavor

    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _hyper = ''
            
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = self.oskconncompute.images.list()

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += "OpenStack Cloud"

            _imageid = False

            _candidate_images = []

            for _idx in range(0,len(_image_list)) :
                if _image_list[_idx].name.count(obj_attr_list["imageid1"]) :
                    _candidate_images.append(_image_list[_idx])
                else :                     
                    True

            if "hypervisor_type" in obj_attr_list :
                _hyper = obj_attr_list["hypervisor_type"]                
                for _image in list(_candidate_images) :
                    if "hypervisor_type" in _image.metadata :
                        if _image.metadata["hypervisor_type"] != obj_attr_list["hypervisor_type"] :
                            _candidate_images.remove(_image)
                        else :
                            _hyper = _image.metadata["hypervisor_type"]
                            
            if len(_candidate_images) :
                if  obj_attr_list["randomize_image_name"].lower() == "true" :
                    _imageid = choice(_candidate_images)
                else :
                    _imageid = _candidate_images[0]

                _status = 0
            
        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ' ' + _hyper + ") not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _imageid, _hyper

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
                
                if not _netname in self.networks_attr_list :
                    _status = 168
                    _fmsg = "Please check if the defined network is present on this "
                    _fmsg += "OpenStack Cloud"
                    self.get_network_list(obj_attr_list)
                
                if _netname in self.networks_attr_list :
                    _networkid = self.networks_attr_list[_netname]["uuid"]
                    
                    _net_info = {"net-id" : _networkid}
                    if not _net_info in _netids :
                        _netids.append(_net_info)
                        _netnames.append(_netname)
                                                
                    _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
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

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on OpenStack \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on OpenStack \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        
        _networks = instance.addresses.keys()

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
    def get_mac_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''

        if "cloud_mac" in obj_attr_list : 
            if obj_attr_list["cloud_mac"] == "True" :
                #If the MAC retrieval fails, just ignore it.
                #Nested 'try' is fine for now.
                try :
                    _virtual_interfaces = self.oskconncompute.virtual_interfaces.list(instance.id)
                    if _virtual_interfaces and len(_virtual_interfaces) :
                        obj_attr_list["cloud_mac"] = _virtual_interfaces[0].mac_address
                except :
                    obj_attr_list["cloud_mac"] = "N/A"
            else :
                obj_attr_list["cloud_mac"] = "N/A"
        return True

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all", force_list = False) :
        '''
        TBD
        '''
        try :
            _search_opts = {}
            _call = "NAi"
            _search_opts['all_tenants'] = 1
            
            if identifier != "all" :
                if obj_type == "vm" :
                    _search_opts["name"] = identifier
                else :
                    _search_opts["display_name"] = identifier

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if obj_type == "vm" :
                                
                if "cloud_vm_uuid" in obj_attr_list and len(obj_attr_list["cloud_vm_uuid"]) >= 36 and not force_list :
                    _call = "get"
                    _instances = [ self.oskconncompute.servers.get(obj_attr_list["cloud_vm_uuid"]) ]

                else :
                    _call = "list"
                    _instances = self.oskconncompute.servers.list(search_opts = _search_opts)
            else :
                if "cloud_vv_uuid" in obj_attr_list and len(obj_attr_list["cloud_vv_uuid"]) >= 36 :
                    _call = "get"
                    _instances = [ self.oskconnstorage.volumes.get(obj_attr_list["cloud_vv_uuid"]) ]
                else :
                    _call = "list"
                    _instances = self.oskconnstorage.volumes.list(search_opts = _search_opts)
            
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

        except novaexceptions, obj:
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

        except Exception, e :
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
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        try :

            _nr_instances = 0
            for _vmc_uuid in self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC") :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                      "VMC", False, _vmc_uuid, \
                                                      False)

                if not self.oskconncompute :
                    self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                                 _vmc_attr_list["name"])

                _nr_instances += len(self.oskconncompute.servers.list())

            return _nr_instances

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = "(While counting instance(s) through API call \"list\") " + str(obj.error_message)
            cberr(_fmsg, True)
            return "ERR"
        
        except Exception, e :
            _status = 23
            _fmsg = "(While counting instance(s) through API call \"list\") " + str(e)
            cberr(_fmsg, True)
            return "ERR"

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

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            raise CldOpsException(_fmsg, _status)

        except Exception, e :
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

            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")

            if self.get_ip_address(obj_attr_list, _instance) :
                obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                return True
        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            
        return False

    @trace
    def is_vm_alive(self, obj_attr_list) :
        '''
        TBD
        '''
        _vm_alive = False
        
        _vm_alive = self.oskconncompute.fping.get(obj_attr_list["cloud_vm_uuid"]).alive

        if _vm_alive :
            # Since ssh will take some extra time to start after the VM is
            # pingable, we wait one period before returning
            sleep(int(obj_attr_list["update_frequency"]))
            
        return _vm_alive

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
            
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _fip = False

            if str(obj_attr_list["always_create_floating_ip"]).lower() == "false" :
                
                _call = "floating ip list"
                fips = self.oskconncompute.floating_ips.list()
                
                for _fip in fips :
                    if _fip.instance_id == None :
                        _fip = _fip.ip
                        break

            if not _fip :
                _call = "floating ip create"
                _mark1 = int(time())
                _fip_h = self.oskconncompute.floating_ips.create(obj_attr_list["floating_pool"])
                
                _fip = _fip_h.ip
                obj_attr_list["cloud_floating_ip_uuid"] = _fip_h.id
            
                _mark2 = int(time())
                obj_attr_list["osk_020_create_fip_time"] = _mark2 - _mark1    

            return _fip

        except novaexceptions, obj:
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

        except Exception, e :
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
            
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])


            if "cloud_floating_ip_uuid" in obj_attr_list :
                _call = "floating ip delete"
                self.oskconncompute.floating_ips.delete(obj_attr_list["cloud_floating_ip_uuid"])
                
            return True

        except novaexceptions, obj:
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

        except Exception, e :
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


    def floating_ip_attach(self, obj_attr_list, _instance) :
        '''
        TBD
        '''

        try :
            
            _call = "NAfpa"
            identifier = obj_attr_list["cloud_vm_name"]

            if str(obj_attr_list["use_floating_ip"]).lower() == "true" :
                _msg = "Attempting to add a floating IP to " + obj_attr_list["name"] + "..."
                cbdebug(_msg, True)

                obj_attr_list["last_known_state"] = "about to create floating IP"
                
                _fip = self.floating_ip_allocate(obj_attr_list)

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
                _mark1 = int(time())
                _instance.add_floating_ip(_fip)

                _mark2 = int(time())
                obj_attr_list["osk_021_attach_fip_time"] = _mark2 - _mark1    

            return True

        except novaexceptions, obj:
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

        except Exception, e :
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
    def vvcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        # Too many problems with neutronclient. Failures, API calls hanging, etc.
        obj_attr_list["use_neutronclient"] = "false"
        
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

            if "cloud_vv" in obj_attr_list :
    
                obj_attr_list["last_known_state"] = "about to send volume create request"
    
                obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["cloud_name"]
                obj_attr_list["cloud_vv_name"] += '-' + "vv"
                obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]            

                if "cloud_vv_type" in obj_attr_list :
                    _volume_type = obj_attr_list["cloud_vv_type"]
                else :
                    _volume_type = None

                if not _volume_type :                    
                    _msg = "Creating a volume, with size " 
                else :
                    _msg = "Creating a " + _volume_type + " volume, with size " 

                _msg += obj_attr_list["cloud_vv"] + " GB, on VMC \"" 
                _msg += obj_attr_list["vmc_name"] + "\""
                cbdebug(_msg, True)

                _imageid = None
                if "boot_volume" in obj_attr_list :
                    _imageid, _hyper = self.get_images(obj_attr_list).__getattr__("id")
                    _msg = "Creating boot volume with name \"" 
                    _msg += obj_attr_list['cloud_vv_name'] + "\", from image id"
                    _msg += " id \"" + _imageid + "\""
                    cbdebug(_msg, True)
    
                _mark1 = int(time())
                _instance = self.oskconnstorage.volumes.create(obj_attr_list["cloud_vv"], \
                                                               snapshot_id = None, \
                                                               display_name = obj_attr_list["cloud_vv_name"], \
                                                               display_description = None, \
                                                               volume_type = _volume_type, \
                                                               availability_zone = None, \
                                                               imageRef = _imageid)
                
                sleep(int(obj_attr_list["update_frequency"]))
        
                obj_attr_list["cloud_vv_uuid"] = '{0}'.format(_instance.id)

                _wait_for_volume = 180
                for i in range(1, _wait_for_volume) :
                    if self.oskconnstorage.volumes.get(_instance.id).status == "available" :
                        cbdebug("Volume took %s second(s) to become available" % i,True)
                        break
                    else :
                        sleep(1)

                _mark2 = int(time())
                obj_attr_list["osk_016_create_volume_time"] = _mark2 - _mark1

                if not _imageid :

                    _mark3 = int(time())
                    _msg = "Attaching the newly created Volume \""
                    _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                    _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                    _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                    _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                    cbdebug(_msg)

                    # There is weird bug on the python novaclient code. Don't change the
                    # following line, it is supposed to be "oskconncompute", even though
                    # is dealing with volumes. Will explain latter.
                    self.oskconncompute.volumes.create_server_volume(obj_attr_list["cloud_vm_uuid"], \
                                                                     obj_attr_list["cloud_vv_uuid"], \
                                                                     "/dev/vdd")

                    _mark2 = int(time())
                    obj_attr_list["osk_016_create_volume_time"] += (_mark3 - _mark3)

            else :
                obj_attr_list["cloud_vv_uuid"] = "none"

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            else :
                _msg = "Volume to be attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vvdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        # Too many problems with neutronclient. Failures, API calls hanging, etc.
        obj_attr_list["use_neutronclient"] = "false"

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])
        
            if "cloud_vv_uuid" in obj_attr_list and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :
                
                _instance = self.get_instances(obj_attr_list, "vv", obj_attr_list["cloud_vv_name"])
    
                if _instance :
    
                    _msg = "Sending a destruction request for the Volume" 
                    _msg += " previously attached to \"" 
                    _msg += obj_attr_list["name"] + "\""
                    _msg += " (cloud-assigned uuid " 
                    _msg += obj_attr_list["cloud_vv_uuid"] + ")...."
                    cbdebug(_msg, True)
    
                    if len(_instance.attachments) :
                        _server_id = _instance.attachments[0]["server_id"]
                        _attachment_id = _instance.attachments[0]["id"]
                        # There is weird bug on the python novaclient code. Don't change the
                        # following line, it is supposed to be "oskconncompute", even though
                        # is dealing with volumes. Will explain latter.
                        self.oskconncompute.volumes.delete_server_volume(_server_id, _attachment_id)
    
                    self.oskconnstorage.volumes.delete(_instance)
                    
            _status =  0
                    
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Volume previously attached to the " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vv_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def set_cgroup(self, obj_attr_list) :
        '''
        TBD
        '''

        _status = 189
        _fmsg = "About to import libvirt...."

        _state_code2value = {}
        _state_code2value["1"] = "running"
        _state_code2value["2"] = "blocked"
        _state_code2value["3"] = "paused"
        _state_code2value["4"] = "shutdown"
        # Temporarily renaming "shutoff" to "save"
        _state_code2value["5"] = "save"
        _state_code2value["6"] = "crashed"


        _cgroups_mapping = {}
        _cgroups_mapping["mem_hard_limit"] = "memory.limit_in_bytes"
        _cgroups_mapping["mem_soft_limit"] = "memory.soft_limit_in_bytes"
        
        try :        

            import libvirt

            _host_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                    "HOST", \
                                                    True, \
                                                    obj_attr_list["host_name"], \
                                                    False)

            _hypervisor_type = str(_host_attr_list["hypervisor_type"]).lower()

            if _hypervisor_type == "qemu" :
                _astr = "/system"
            else :
                _astr = ""

            _host_name = _host_attr_list["cloud_hostname"]

            _host_ip = _host_attr_list["cloud_ip"]


            obj_attr_list["resource_limits"] = str2dic(obj_attr_list["resource_limits"].replace(';',',').replace('-',':'))

            _proc_man = ProcessManagement(username = "root", \
                                          hostname = _host_ip, \
                                          cloud_name = obj_attr_list["cloud_name"])

            for _key in obj_attr_list["resource_limits"] :

                _base_dir = obj_attr_list["cgroups_base_dir"]
                if _key.count("mem") :
                    _subsystem = "memory"

                # The cgroups/libvirt interface is currently broken (for memory limit
                # control). Will have to ssh into the node and set cgroup limits 
                # manually.
                
                _value = str(value_suffix(obj_attr_list["resource_limits"][_key]))

                _cmd = "echo " + _value + " > " + _base_dir + _subsystem +"/machine/"
                _cmd += obj_attr_list["instance_name"] + ".libvirt-" + _hypervisor_type
                _cmd += "/" + _cgroups_mapping[_key]

                _msg = "Altering the \"" + _cgroups_mapping[_key] + "\" parameter"
                _msg += " on the \"" +_subsystem + "\" subsystem on cgroups for"
                _msg += " instance \"" + obj_attr_list["instance_name"] + "\" with "
                _msg += " the value \"" + _value + "\"..."
                cbdebug(_msg, True)

                _status, _result_stdout, _fmsg = _proc_man.run_os_command(_cmd)

            if not _status :
                
                if _host_name not in self.lvirt_conn or not self.lvirt_conn[_host_name] :        
                    _msg = "Attempting to connect to libvirt daemon running on "
                    _msg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\"...."
                    cbdebug(_msg)
    
                    self.lvirt_conn[_host_name] = libvirt.open( _hypervisor_type + "+tcp://" + _host_ip + _astr)
                    
                    _msg = "Connection to libvirt daemon running on hypervisor ("
                    _msg += _hypervisor_type + ") \"" + _host_ip + "\" successfully established."
                    cbdebug(_msg)
    
                    instance_data = self.lvirt_conn[_host_name].lookupByName(obj_attr_list["instance_name"])
    
                    obj_attr_list["lvirt_os_type"] = instance_data.OSType()
    
                    obj_attr_list["lvirt_scheduler_type"] = instance_data.schedulerType()[0]
        
                # All object uuids on state store are case-sensitive, so will
                # try to just capitalize the UUID reported by libvirt
    #                obj_attr_list["cloud_uuid"] = instance_data.UUIDString().upper()
    #                obj_attr_list["uuid"] = obj_attr_list["cloud_uuid"]
    #                obj_attr_list["cloud_lvid"] = instance_data.name()
    
                _gobj_attr_list = instance_data.info()
    
                obj_attr_list["lvirt_vmem"] = str(_gobj_attr_list[1])
                obj_attr_list["lvirt_vmem_current"] = str(_gobj_attr_list[2])
                obj_attr_list["lvirt_vcpus"] = str(_gobj_attr_list[3])
    
                _state_code = str(_gobj_attr_list[0])
                if _state_code in _state_code2value :
                    obj_attr_list["lvirt_state"] = _state_code2value[_state_code]
                else :
                    obj_attr_list["lvirt_state"] = "unknown"
    
                if _state_code == "1" :
    
                    _vcpu_info = instance_data.vcpus()
    
                    for _vcpu_nr in range(0, int(obj_attr_list["lvirt_vcpus"])) :
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_pcpu"] = str(_vcpu_info[0][_vcpu_nr][3])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_time"] =  str(_vcpu_info[0][_vcpu_nr][2])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_state"] =  str(_vcpu_info[0][_vcpu_nr][1])
                        obj_attr_list["lvirt_vcpu_" + str(_vcpu_nr) + "_map"] = str(_vcpu_info[1][_vcpu_nr])
    
                    _sched_info = instance_data.schedulerParameters()
    
                    obj_attr_list["lvirt_vcpus_soft_limit"] = str(_sched_info["cpu_shares"])
    
                    if "vcpu_period" in _sched_info :
                        obj_attr_list["lvirt_vcpus_period"] = str(float(_sched_info["vcpu_period"]))
                        obj_attr_list["lvirt_vcpus_quota"] = str(float(_sched_info["vcpu_quota"]))
                        obj_attr_list["lvirt_vcpus_hard_limit"] = str(float(obj_attr_list["lvirt_vcpus_quota"]) / float(obj_attr_list["lvirt_vcpus_period"]))
    
                    if "memoryParameters" in dir(instance_data) :    
                        _mem_info = instance_data.memoryParameters(0)
    
                        obj_attr_list["lvirt_mem_hard_limit"] = str(_mem_info["hard_limit"])
                        obj_attr_list["lvirt_mem_soft_limit"] = str(_mem_info["soft_limit"])
                        obj_attr_list["lvirt_mem_swap_hard_limit"] = str(_mem_info["swap_hard_limit"])
    
                    if "blkioParameters" in dir(instance_data) :
                        _diskio_info = instance_data.blkioParameters(0)
                        obj_attr_list["lvirt_diskio_soft_limit"] = "unknown"
                        if _diskio_info :
                            if "weight" in _diskio_info :
                                obj_attr_list["lvirt_diskio_soft_limit"] = str(_diskio_info["weight"])
    
    
                _status = 0

        except libvirt.libvirtError, msg :
            _fmsg = "Error while attempting to connect to libvirt daemon running on "
            _fmsg += "hypervisor (" + _hypervisor_type + ") \"" + _host_ip + "\":"
            _fmsg += msg
            cberr(_fmsg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while attempting to set resource limits for VM " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)

            else :
                _msg = "Successfully set resource limits for VM " + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "running on hypervisor \"" + _host_name + "\""
                _msg += " in OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)

            return _status, _msg

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        
        try :

            # Too many problems with neutronclient. Failures, API calls hanging, etc.
            obj_attr_list["use_neutronclient"] = "false"
                        
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _vvfmsg = ''
            _vvstatus = 0
            
            obj_attr_list["cloud_vm_uuid"] = "NA"
            _instance = False

            if "cloud_vm_name" not in obj_attr_list :
                obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["cloud_name"]
                obj_attr_list["cloud_vm_name"] += '-' + "vm"
                obj_attr_list["cloud_vm_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

                if obj_attr_list["ai"] != "none" :            
                    obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]  

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to openstack manager"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if "execute_provision_originated_stdout" in obj_attr_list :
                if obj_attr_list["execute_provision_originated_stdout"].count("tenant") :
                    _temp_dict = str2dic(obj_attr_list["execute_provision_originated_stdout"].replace('\n',''), False)
                    if _temp_dict :
                        obj_attr_list.update(_temp_dict)
                    
            obj_attr_list["key_name"] = obj_attr_list["username"] + '_' + obj_attr_list["tenant"] + '_' + obj_attr_list["key_name"]

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
                self.oskconncompute = False

            if not self.oskconncompute :
                _mark1 = int(time())
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})

                _mark2 = int(time())
                obj_attr_list["osk_011_authenticate_time"] = _mark2 - _mark1
            else :
                _mark2 = int(time())

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            _mark3 = int(time())
            obj_attr_list["osk_012_check_existing_instance_time"] = _mark3 - _mark2
                    
            obj_attr_list["last_known_state"] = "about to get flavor and image list"

            if str(obj_attr_list["security_groups"]).lower() == "false" :
                _security_groups = None
            else :
                # "Security groups" must be a list
                _security_groups = []
                _security_groups.append(obj_attr_list["security_groups"])

            if str(obj_attr_list["key_name"]).lower() == "false" :
                _key_name = None
            else :
                _key_name = obj_attr_list["key_name"]

            obj_attr_list["last_known_state"] = "about to send create request"

            _flavor = self.get_flavors(obj_attr_list)

            _mark4 = int(time())
            obj_attr_list["osk_013_get_flavors_time"] = _mark4 - _mark3            

            _imageid, _hyper = self.get_images(obj_attr_list)

            _mark5 = int(time())
            obj_attr_list["osk_014_get_imageid_time"] = _mark5 - _mark4

            _availability_zone = None            
            if len(obj_attr_list["availability_zone"]) > 1 :
                _availability_zone = obj_attr_list["availability_zone"]

            if "host_name" in obj_attr_list and _availability_zone :
#                _scheduler_hints = { "force_hosts" : obj_attr_list["host_name"] }

                for _host in self.oskconncompute.hypervisors.list() :
                    if _host.hypervisor_hostname.count(obj_attr_list["host_name"]) :
                        obj_attr_list["host_name"] = _host.hypervisor_hostname

                _availability_zone += ':' + obj_attr_list["availability_zone"]

            _scheduler_hints = None

            if "userdata" in obj_attr_list and obj_attr_list["userdata"] :
                _userdata = obj_attr_list["userdata"].replace("# INSERT OPENVPN COMMAND", \
                                                              "openvpn --config /etc/openvpn/" + obj_attr_list["cloud_name"].upper() + "_client-cb-openvpn.conf --daemon --client")
                _config_drive = True
            else :
                _config_drive = None
                _userdata = None

            _mark5 = int(time())
            _netnames, _netids = self.get_networks(obj_attr_list)

            _mark6 = int(time())
            obj_attr_list["osk_015_get_netid_time"] = _mark6 - _mark5
            
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

            _boot_volume_imageid = _imageid 
#
#           Create volume based image.
#
            _block_device_mapping = {}
            if "boot_volume" in obj_attr_list :
                _boot_volume = True
                _boot_volume_imageid = None                 
                obj_attr_list['cloud_vv'] = obj_attr_list['boot_volume_size'] 
                obj_attr_list['cloud_vv_type'] = None 
                self.vvcreate(obj_attr_list)
                _block_device_mapping = {'vda':'%s' % obj_attr_list["cloud_vv_uuid"]}

            _msg = "Starting an instance on OpenStack, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" (" + str(_imageid) + ' ' + _hyper + ") and "
            _msg += "size \"" + obj_attr_list["size"] + "\" (" + str(_flavor) + ")"

#            if _scheduler_hints :
#                _msg += ", with scheduler hints \"" + str(_scheduler_hints) + "\" "

            if _availability_zone :
                _msg += ", on the availability zone \"" + str(_availability_zone) + "\""

            if len(_block_device_mapping) :
                _msg += ", with \"block_device_mapping=" + str(_block_device_mapping) + "\""

            _msg += ", connected to networks \"" + _netnames + "\""
            _msg += ", on VMC \"" + obj_attr_list["vmc_name"] + "\", under tenant"
            _msg += " \"" + obj_attr_list["tenant"] + "\" (ssh key is \""
            _msg += str(_key_name) + "\" and userdata is "
            if _userdata :
                _msg += "\"auto\")"
            else :
                _msg += "\"none\")" 

            cbdebug(_msg, True)

            _instance = self.oskconncompute.servers.create(name = obj_attr_list["cloud_vm_name"], \
                                                           block_device_mapping = _block_device_mapping, \
                                                           image = _boot_volume_imageid, \
                                                           flavor = _flavor, \
                                                           security_groups = _security_groups, \
                                                           key_name = _key_name, \
                                                           scheduler_hints = _scheduler_hints, \
                                                           availability_zone = _availability_zone, \
                                                           meta = _meta, \
                                                           config_drive = _config_drive, \
                                                           userdata = _userdata, \
                                                           nics = _netids, \
                                                           disk_config = "AUTO")

            if _instance :
                
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = '{0}'.format(_instance.id)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                while not self.floating_ip_attach(obj_attr_list, _instance) :
                    True

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                if "osk_018_instance_creation_time" not in obj_attr_list :
                    obj_attr_list["osk_018_instance_scheduling_time"] = 0
                    obj_attr_list["osk_018_port_creation_time"] = 0
                    obj_attr_list["osk_019_instance_creation_time"] = obj_attr_list["mgt_003_provisioning_request_completed"]
                else :
                    obj_attr_list["osk_019_instance_creation_time"] = float(obj_attr_list["osk_019_instance_creation_time"]) - float(obj_attr_list["osk_018_port_creation_time"])
                    
                if obj_attr_list["last_known_state"].count("ERROR") :
                    _fmsg = obj_attr_list["last_known_state"]
                    _status = 189
                else :

                    if not len(_block_device_mapping) :
                        _vvstatus, _vvfmsg = self.vvcreate(obj_attr_list)

                        if _vvstatus :
                            _status = _vvstatus
                    else :
                        _status = 0
 
                    if "admin_credentials" in obj_attr_list :
                        self.connect(obj_attr_list["access"], obj_attr_list["admin_credentials"], \
                                     obj_attr_list["vmc_name"], \
                                     {"use_neutronclient" : obj_attr_list["use_neutronclient"]})                        

                    self.get_mac_address(obj_attr_list, _instance)

                    self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                    obj_attr_list["osk_022_instance_reachable"] = obj_attr_list["mgt_004_network_acessible"]   
                    
                    self.get_host_and_instance_name(obj_attr_list)
    
                    self.take_action_if_requested("VM", obj_attr_list, "provision_finished")

                    if "execute_provision_finished_stdout" in obj_attr_list :
                        if obj_attr_list["execute_provision_finished_stdout"].count("tenant") :
                            _temp_dict = str2dic(obj_attr_list["execute_provision_finished_stdout"].replace('\n',''), False)
                            if _temp_dict :
                                obj_attr_list.update(_temp_dict)

                    if obj_attr_list["tenant"] != "default" :
                        self.oskconncompute = False

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
                
        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :

            self.disconnect()

            if _status :

                self.instance_cleanup_on_failure(obj_attr_list, _status, _fmsg, _vvstatus, _vvfmsg)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    def instance_cleanup_on_failure(self, obj_attr_list, _status, _fmsg, _vvstatus, _vvfmsg) :
        '''
        TBD
        '''

        _oskfmsg = ''
        _liof_msg = ''
        _vminstance = self.get_instances(obj_attr_list, "vm", \
                                                       obj_attr_list["cloud_vm_name"])
            
        _msg = "" + obj_attr_list["name"] + ""
        _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
        _msg += "could not be created"
        _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\""

        if _vminstance :
            # Not the best way to solve this problem. Will improve later.
            
            if not self.is_vm_running(obj_attr_list) :
                if "fault" in dir(_vminstance) :
                    if "message" in _vminstance.fault : 
                        _oskfmsg = "\nINSTANCE ERROR MESSAGE:" + str(_vminstance.fault["message"]) + ".\n"

            # Try and make a last attempt effort to get the hostname,
            # even if the VM creation failed.

            self.get_host_and_instance_name(obj_attr_list, fail = False)

            if "host_name" in obj_attr_list :
                _msg += " (Host \"" + obj_attr_list["host_name"] + "\")"

            if str(obj_attr_list["leave_instance_on_failure"]).lower() == "true" :
                _liof_msg = " (Will leave the VM running due to experimenter's request)"
            else :
                _liof_msg = " (The VM creation will be rolled back)"
                _vminstance.delete()

                if "cloud_vv" in obj_attr_list :
                    self.vvdestroy(obj_attr_list)

            _msg += ": " 

        _msg += _fmsg + ".\n"
        
        if _vvstatus :
            _msg += "VOLUME ERROR MESSAGE:" + _vvfmsg + ".\n"

        if len(_oskfmsg) :
            _msg += _oskfmsg

        _msg += _liof_msg
        cberr(_msg)
        
        raise CldOpsException(_msg, _status)

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
        
        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = "(While removing instance(s) through API call \"delete\") " + str(obj.error_message)

            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                return False

        except Exception, e :
            _status = 23
            _fmsg = "(While removing instance(s) through API call \"delete\") " + str(obj.error_message)
            if identifier not in self.api_error_counter :
                self.api_error_counter[identifier] = 0
            
            self.api_error_counter[identifier] += 1
            
            if self.api_error_counter[identifier] > self.max_api_errors :            
                raise CldOpsException(_fmsg, _status)
            else :
                return False
                
    @trace
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            
            # Too many problems with neutronclient. Failures, API calls hanging, etc.
            obj_attr_list["use_neutronclient"] = "false"
                        
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())
            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                
            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                self.floating_ip_delete(obj_attr_list)

                _msg = "Sending a termination request for Instance \""  + obj_attr_list["name"] + "\""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                self.retriable_instance_delete(obj_attr_list, _instance)

                while _instance :
                    _instance = self.get_instances(obj_attr_list, "vm", \
                                           obj_attr_list["cloud_vm_name"], True)
                    if _instance :
                        if _instance.status != "ACTIVE" :
                            break
                    sleep(_wait)
            else :
                True

            _status, _fmsg = self.vvdestroy(obj_attr_list)

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
                
            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

            if "execute_deprovision_finished_stdout" in obj_attr_list :
                if obj_attr_list["execute_deprovision_finished_stdout"].count("tenant") :
                    _temp_dict = str2dic(obj_attr_list["execute_deprovision_finished_stdout"].replace('\n',''), False)
                    if _temp_dict :
                        obj_attr_list.update(_temp_dict)
                    
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully destroyed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmcapture(self, obj_attr_list) :
        '''
        TBD
        '''
        # Too many problems with neutronclient. Failures, API calls hanging, etc.
        obj_attr_list["use_neutronclient"] = "false"
                
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs  

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent."
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _instance.create_image(obj_attr_list["captured_image_name"], None)
                sleep(_wait)

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries : 
                    _vm_images = self.oskconncompute.images.list()
                    for _vm_image in _vm_images :
                        if _vm_image.name == obj_attr_list["captured_image_name"] :
                            if _vm_image.status == "ACTIVE" :
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

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()   
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def vmmigrate(self, obj_attr_list) :
        '''
        TBD
        '''
        # Too many problems with neutronclient. Failures, API calls hanging, etc.
        obj_attr_list["use_neutronclient"] = "false"        
        
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})

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
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})
    
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _instance.live_migrate(obj_attr_list["destination_name"].replace("host_", ""))
                
                obj_attr_list["mgt_502_" + operation + "_request_sent"] = _time_mark_crs - obj_attr_list["mgt_501_" + operation + "_request_originated"]
                
                while True and _curr_tries < _max_tries : 
                    sleep(_wait)             
                    _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
                    
                    if _instance.status not in ["ACTIVE", "MIGRATING"] :
                        _status = 4328
                        _msg = "Migration of instance failed, OpenStack state is: " + _instance.status
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
    
        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
        
        except Exception, e :
            _status = 349201
            _fmsg = str(e)
            
        finally :
            self.disconnect()            
            if "mgt_503_" + operation + "_request_completed" not in obj_attr_list :
                obj_attr_list["mgt_999_" + operation + "_request_failed"] = int(time()) - _time_mark_crs
                        
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "could not be " + operation + "ed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "was successfully " + operation + "ed "
                _msg += "on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        # Too many problems with neutronclient. Failures, API calls hanging, etc.
        obj_attr_list["use_neutronclient"] = "false"

        try :
            _status = 100

            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]
    
            if not self.oskconncompute :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], \
                             {"use_neutronclient" : obj_attr_list["use_neutronclient"]})

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

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

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            self.disconnect()            
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on OpenStack Cloud"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\" :" + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on OpenStack Cloud"
                _msg += " \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace        
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :

            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, current_step)

            if "execute_provision_originated_stdout" in obj_attr_list and current_step == "provision_originated" :
                if obj_attr_list["execute_provision_originated_stdout"].count("tenant") :
                    _temp_dict = str2dic(obj_attr_list["execute_provision_originated_stdout"].replace('\n',''), False)

                    if _temp_dict :
                        obj_attr_list["vm_extra_parms"] = ''                    
                        for _key in _temp_dict.keys() :
                            if not _key.count("staging") :
                                obj_attr_list["vm_extra_parms"] += _key + '=' + _temp_dict[_key] + ','
                            else :
                                obj_attr_list["vm_attach_action"] = _temp_dict["vm_staging"]
                                
                        obj_attr_list["vm_extra_parms"] = obj_attr_list["vm_extra_parms"][0:-1]
                        obj_attr_list.update(_temp_dict)
                    
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            self.take_action_if_requested("AI", obj_attr_list, current_step)            
            _fmsg = "An error has occurred, but no error message was captured"
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on OpenStack Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
