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
from subprocess import Popen, PIPE
from uuid import uuid5, UUID
from random import choice

from novaclient.v1_1 import client
from novaclient import exceptions as novaexceptions

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import hostname2ip
from shared_functions import CldOpsException, CommonCloudFunctions 

class OskCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.oskconn = False
        self.ft_supported = False 

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "OpenStack Compute Cloud"

    @trace
    def connect(self, access_url, authentication_data, region) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _username, _password, _tenant = authentication_data.split('-')
            self.oskconn = client.Client(_username, _password, _tenant, access_url, region_name=region, service_type="compute")
            self.oskconn.flavors.list()
            _region = region
            _msg = "Selected region is " + str(region)
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
                raise CldOpsException(_msg, _status)
            else :
                _msg = "OpenStack connection successful."
                cbdebug(_msg)
                return _status, _msg, _region
    
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, extra_info) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            self.connect(access, credentials, vmc_name)
            _status = 0

        except CldOpsException, obj :
            _fmsg = str(obj.msg)
            cberr(_fmsg)
            _status = 2
            raise CldOpsException(_fmsg, _status)

        finally :
            if _status :
                _msg = "VMC \"" + vmc_name + "\" could not be tested."
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

            if not self.oskconn :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])
                
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
    
            _host_list = self.oskconn.hypervisors.list()
       
            obj_attr_list["host_count"] = len(_host_list)
    
            for _host in _host_list :
    
                # Host UUID is artificially generated
                _host_uuid = str(uuid5(UUID('4f3f2898-69e3-5a0d-820a-c4e87987dbce'), obj_attr_list["cloud_name"] + str(_host.service["id"])))
                obj_attr_list["host_list"][_host_uuid] = {}
                obj_attr_list["hosts"] += _host_uuid + ','
                obj_attr_list["host_list"][_host_uuid]["cloud_hostname"], obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = hostname2ip(_host.hypervisor_hostname)

                if obj_attr_list["host_list"][_host_uuid]["cloud_ip"] == obj_attr_list["cloud_ip"] :
                    obj_attr_list["host_list"][_host_uuid]["function"] = "controller"
                else :
                    obj_attr_list["host_list"][_host_uuid]["function"] = "compute"
                obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                obj_attr_list["host_list"][_host_uuid]["memory_size"] = _host.memory_mb
                obj_attr_list["host_list"][_host_uuid]["cores"] = _host.vcpus
                obj_attr_list["host_list"][_host_uuid]["pool"] = obj_attr_list["pool"]
                obj_attr_list["host_list"][_host_uuid]["username"] = obj_attr_list["username"]
                obj_attr_list["host_list"][_host_uuid]["notification"] = "False"
                obj_attr_list["host_list"][_host_uuid]["model"] = obj_attr_list["model"]
                obj_attr_list["host_list"][_host_uuid]["vmc_name"] = obj_attr_list["name"]
                obj_attr_list["host_list"][_host_uuid]["vmc"] = obj_attr_list["uuid"]
                obj_attr_list["host_list"][_host_uuid]["uuid"] = _host_uuid
                obj_attr_list["host_list"][_host_uuid]["arrival"] = int(time())
                obj_attr_list["host_list"][_host_uuid]["counter"] = obj_attr_list["counter"]
                obj_attr_list["host_list"][_host_uuid]["mgt_001_provisioning_request_originated"] = obj_attr_list["mgt_001_provisioning_request_originated"]
                obj_attr_list["host_list"][_host_uuid]["mgt_002_provisioning_request_sent"] = obj_attr_list["mgt_002_provisioning_request_sent"]
                _time_mark_prc = int(time())
                obj_attr_list["host_list"][_host_uuid]["mgt_003_provisioning_request_completed"] = _time_mark_prc - start
    
            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]
            
            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
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

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconn :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["name"])

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            _running_instances = True
            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False
                _instances = self.oskconn.servers.list()
                for _instance in _instances :
                    if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                        _running_instances = True
                        if  _instance.status == "ACTIVE" :
                            _msg = "Terminating instance: " 
                            _msg += _instance.id + " (" + _instance.name + ")"
                            cbdebug(_msg, True)
                            _instance.delete()

                        if _instance.status == "BUILD" :
                            _msg = "Will wait for instance "
                            _msg += _instance.id + "\"" 
                            _msg += " (" + _instance.name + ") to "
                            _msg += "start and then destroy it."
                            cbdebug(_msg, True)
                            
                    _msg = "Some instances are still starting on VMC \"" + obj_attr_list["name"] 
                    _msg += "\". Will wait for " + str(_wait) + " seconds and check again."
                    sleep(_wait)
                    _curr_tries += 1
                                
                sleep(int(obj_attr_list["update_frequency"]))

            if _curr_tries > _max_tries  :
                _status = 1077
                _fmsg = "Some instances on VMC \"" + obj_attr_list["name"] + "\""
                _fmsg += " could not be removed because they never became active"
                _fmsg += ". They will have to be removed manually."
                cberr(_msg, True)
            else :
                _status = 0
            
            sleep(int(obj_attr_list["update_frequency"]))

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)
            
        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
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
                _msg = "Removing all VMs previously created on VMC \""
                _msg += obj_attr_list["name"] + "\" (only VMs names starting with"
                _msg += " \"" + "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]
                _msg += "\")....."
                cbdebug(_msg, True)
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            if not _status :
                _x, _y, _hostname = self.connect(obj_attr_list["access"], \
                                                 obj_attr_list["credentials"], \
                                                 obj_attr_list["name"])
    
                obj_attr_list["cloud_hostname"] = _hostname
                _x, obj_attr_list["cloud_ip"] = hostname2ip(obj_attr_list["access"].split(':')[1].replace('//',''))
                obj_attr_list["arrival"] = int(time())
    
                if obj_attr_list["discover_hosts"].lower() == "true" :
                    _msg = "Discovering hosts on VMC \"" + obj_attr_list["name"] + "\"....."
                    cbdebug(_msg, True)
                    _status, _fmsg = self.discover_hosts(obj_attr_list, _time_mark_prs)
                else :
                    obj_attr_list["hosts"] = ''
                    obj_attr_list["host_list"] = {}
                    obj_attr_list["host_count"] = "NA"
                    
                _time_mark_prc = int(time())
                obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

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
            
            _flavor_list = self.oskconn.flavors.list()

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
            _fmsg = "An error has occurred, but no error message was captured"

            _image_list = self.oskconn.images.list()

            _fmsg += "Please check if the defined image name is present on this "
            _fmsg += "OpenStack Cloud"

            _imageid = False

            _candidate_images = []

            for _idx in range(0,len(_image_list)) :
                if obj_attr_list["randomize_image_name"].lower() == "false" and \
                _image_list[_idx].name == obj_attr_list["imageid1"] :
                    _imageid = _image_list[_idx]
                    break
                elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                _image_list[_idx].name.count(obj_attr_list["imageid1"]) :
                    _candidate_images.append(_image_list[_idx])
                else :                     
                    True

            if  obj_attr_list["randomize_image_name"].lower() == "true" :
                _imageid = choice(_candidate_images)

            _status = 0

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

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
        if "private" in instance.addresses :
            _ip_address_key = "private"
        elif "brnet" in instance.addresses :
            _ip_address_key = "brnet"
        else :
            _ip_address_key = False
                
        if _ip_address_key :
            obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
            obj_attr_list["cloud_ip"] = '{0}'.format(instance.addresses[_ip_address_key][0]["addr"])      
            return True
        else :
            return False

    @trace
    def get_mac_address(self, obj_attr_list, instance) :
        '''
        TBD
        '''
        if "cloud_mac" in obj_attr_list : 
            if obj_attr_list["cloud_mac"] == "True" :
                _virtual_interfaces = self.oskconn.virtual_interfaces.list(obj_attr_list["cloud_uuid"])
                if _virtual_interfaces and len(_virtual_interfaces) :
                    obj_attr_list["cloud_mac"] = _virtual_interfaces[0].mac_address
            else :
                obj_attr_list["cloud_mac"] = "NA"
        return True

    @trace
    def get_vm_instances(self, obj_attr_list, vmidentifier = "all") :
        '''
        TBD
        '''
        try :
            _search_opts = {}

            if vmidentifier != "all" :
                _search_opts["name"] = vmidentifier

            if not self.oskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _instances = self.oskconn.servers.list(search_opts = _search_opts)
    
            if len(_instances) : 
                if vmidentifier != "all" :   
                    return _instances[0]
                else :
                    return _instances
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
    def is_vm_running(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _instance = self.get_vm_instances(obj_attr_list, \
                                           obj_attr_list["cloud_vm_name"])

            if _instance :
                if _instance.status == "ACTIVE" :
                    return _instance
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

            self.pause_after_provision_if_requested(obj_attr_list)

            if self.get_ip_address(obj_attr_list, _instance) :
                obj_attr_list["last_known_state"] = "ACTIVE with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "ACTIVE with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not ACTIVE"
            return False

    @trace
    def get_hostname(self, obj_attr_list) :
        '''
        TBD
        '''
        
        # There is a lot of extra information that can be obtained through
        # the "_info" attribute. However, a new connection has to be 
        # established to access the most up-to-date data on this attribute
        # Not sure how stable it will be with newer versions of the API. 
        _instance = self.is_vm_running(obj_attr_list)
        
        if _instance :
            if "OS-EXT-SRV-ATTR:host" in _instance._info :
                obj_attr_list["host_name"] = _instance._info['OS-EXT-SRV-ATTR:host']
            else :
                obj_attr_list["host_name"] = "unknown"
        else :
            obj_attr_list["host_name"] = "unknown"
        return True

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            obj_attr_list["cloud_uuid"] = "NA"
            _instance = False
            
            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"] + '-' + "vm" + obj_attr_list["name"].split("_")[1] + '-' + obj_attr_list["role"]

            obj_attr_list["last_known_state"] = "about to connect to openstack manager"

            if not self.oskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            obj_attr_list["last_known_state"] = "about to get flavor and image list"

            # "Security groups" must be a list
            _security_groups = []
            _security_groups.append(obj_attr_list["security_groups"])

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _flavor = self.get_flavors(obj_attr_list)            
            _imageid = self.get_images(obj_attr_list)
            
            _msg = "Starting an instance on OpenStack, using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\" (" + str(_imageid) + ") and "
            _msg += "size \"" + obj_attr_list["size"] + "\" (" + str(_flavor) + ")"
            _msg += " on VMC \"" + obj_attr_list["vmc_name"] + "\""
            cbdebug(_msg, True)
    
            _instance = self.oskconn.servers.create(name = obj_attr_list["cloud_vm_name"], \
                                                    image = _imageid, \
                                                    flavor = _flavor, \
                                                    security_groups = _security_groups, \
                                                    key_name = obj_attr_list["key_name"])

            if _instance :
                
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_uuid"] = '{0}'.format(_instance.id)

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
                            
                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                self.get_hostname(obj_attr_list)

                _status = 0
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
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)
                
                _instance = self.get_vm_instances(obj_attr_list, \
                                               obj_attr_list["cloud_vm_name"])

                if _instance :
                    # Try to make a last attempt effort to get the hostname,
                    # even if the VM creation failed.
                    self.get_hostname(obj_attr_list)

                    _instance.delete()
                raise CldOpsException(_msg, _status)

            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "was successfully created"
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
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

            if not self.oskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_vm_instances(obj_attr_list, \
                                           obj_attr_list["cloud_vm_name"])
            
            if _instance :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)
            
                _instance.delete()
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

        except novaexceptions, obj:
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be destroyed "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
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
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if not self.oskconn :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _instance = self.get_vm_instances(obj_attr_list, \
                                           obj_attr_list["cloud_vm_name"])

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
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries : 
                    _vm_images = self.oskconn.images.list()
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
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
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
                _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
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
            if _status :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "could not be captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "" + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "was successfully captured "
                _msg += " on OpenStack Cloud \"" + obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg)
                return _status, _msg

    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100

            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]
    
            if not self.oskconn :
                self.connect(obj_attr_list["access"], \
                             obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            _instance = self.get_vm_instances(obj_attr_list, \
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
    def aidefine(self, obj_attr_list) :
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
