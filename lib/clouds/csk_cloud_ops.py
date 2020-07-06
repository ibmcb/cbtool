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
    Created on Apr 28, 2012

    CloudPlatform/CloudStack Object Operations Library

    @author: YongHun Jeon, JaeHoon Jung
'''
from os import makedirs, access, F_OK
from time import time, sleep
from random import choice

from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import hostname2ip

from .shared_functions import CldOpsException, CommonCloudFunctions 

from lib.remote.process_management import ProcessManagement

import CloudStack 

class CskCmds(CommonCloudFunctions) :
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
        self.cskconn = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "CloudPlatform"

    @trace
    def connect(self, access, api_key, secret_key) :
        '''
        TBD
        '''
        try :
            _status = 100

            _fmsg = "An error has occurred, but no error message was captured"


            self.cskconn = CloudStack.Client(access, \
                                            api_key, \
                                            secret_key)

            _status = 0

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = "CloudPlatform connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "CloudPlatform connection successful."
                cbdebug(_msg)
                return _status, _msg
    
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            _apikey, _secretkey = credentials.split('|')

            self.connect(access, _apikey, _secretkey)
            
            _zoneid = self.get_zone(vmc_name)

            _msg = "Checking if the ssh key pair \"" + key_name + "\" is created"
            _msg += " on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _key_pair_found = False
            for _key_pair in self.cskconn.listSSHKeyPairs() :
                if _key_pair['name'] == key_name :
                    _key_pair_found = True

            if not _key_pair_found :
                _msg = "ERROR! Please create the ssh key pair \"" + key_name + "\" in "
                _msg += "CloudPlatform before proceeding."
                _fmsg = _msg
                cberr(_msg, True)

            _msg = "Checking if the security group \"" + security_group_name
            _msg += "\" is created on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _security_group_found = False
            for security_group in self.cskconn.listSecurityGroups() :
                if security_group['name'] == security_group_name :
                    _security_group_found = True

            if not _security_group_found :
                _msg = "ERROR! Please create the security group \"" + security_group_name + "\" in "
                _msg += "CloudPlatform before proceeding."
                _fmsg = _msg
                cberr(_msg, True)
            
            _msg = "Checking if the imageids associated to each \"VM role\" are"
            _msg += " registered on VMC " + vmc_name + "...."
            cbdebug(_msg, True)

            _registered_image_list = self.cskconn.listTemplates({'zoneid' : _zoneid, 'templatefilter' : 'executable'})
            _registered_imageid_list = []

            for _registered_image in _registered_image_list :
                _registered_imageid_list.append(_registered_image['name'].replace(" ", ""))

            _required_imageid_list = {}


            for _vm_role in list(vm_templates.keys()) :
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]                
                if _imageid not in _required_imageid_list :
                    _required_imageid_list[_imageid] = []
                _required_imageid_list[_imageid].append(_vm_role)

            _msg = 'y'

            _detected_imageids = {}
            _undetected_imageids = {}

            for _imageid in list(_required_imageid_list.keys()) :
                
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
                else :
                    _msg = "xWARNING Image id for VM roles \""
                    _msg += ','.join(_required_imageid_list[_imageid]) + "\": \""
                    _msg += _imageid + "\" is NOT registered "
                    _msg += "(attaching VMs with any of these roles will result in error).\n"
            
            if not len(_detected_imageids) :
                _msg = "ERROR! None of the image ids used by any VM \"role\" were detected"
                _msg += " in this cloudPlatform. Please register at least one "
                _msg += "of the following images: " + ','.join(list(_undetected_imageids.keys()))
                _fmsg = _msg 
                cberr(_msg, True)
            else :
                _msg = _msg.replace("yx",'')
                _msg = _msg.replace('x',"         ")
                _msg = _msg[:-2]
                if len(_msg) :
                    cbdebug(_msg, True)

            if not (_key_pair_found and _security_group_found and len(_detected_imageids)) :
                _msg = "Check the previous errors, fix it (using CloudStack's web"
                _msg += " GUI (horizon) or nova CLI"
                _status = 1178
                raise CldOpsException(_msg, _status) 

            _status = 0

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

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

            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                          obj_attr_list["secret_key"])
                          
            _zoneid = self.get_zone(obj_attr_list["name"])
                
            obj_attr_list["hosts"] = ''
            obj_attr_list["host_list"] = {}
            _host_list = self.cskconn.listHosts({'zoneid' : _zoneid})

            _host_count = 0

            _service_ids_found = {}
            for _host in _host_list :
                # Sometimes, the same hypervisor is reported more than once,
                # with slightly different names. We need to remove (in fact,
                # avoid the insertion of) duplicates.
                if not _host['id'] in _service_ids_found and _host['type'] == 'Routing' :
                    # Host UUID is artificially generated
                    _host_uuid = _host['id']
                    obj_attr_list["host_list"][_host_uuid] = {}
                    obj_attr_list["hosts"] += _host_uuid + ','
                    obj_attr_list["host_list"][_host_uuid]["cloud_hostname"] = _host['name']
                    obj_attr_list["host_list"][_host_uuid]["cloud_ip"] = _host['ipaddress']
                    obj_attr_list["host_list"][_host_uuid]["function"] = "compute"
                    obj_attr_list["host_list"][_host_uuid]["name"] = "host_" + obj_attr_list["host_list"][_host_uuid]["cloud_hostname"]
                    obj_attr_list["host_list"][_host_uuid]["memory_size"] = _host['memorytotal']
                    obj_attr_list["host_list"][_host_uuid]["cores"] = _host['cpunumber']
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
                    _service_ids_found[ _host['id']] = "1"
                    _host_count = _host_count + 1

            obj_attr_list["hosts"] = obj_attr_list["hosts"][:-1]

            obj_attr_list["host_count"] = _host_count

            self.additional_host_discovery (obj_attr_list)
            
            _status = 0
            
        except CldOpsException as obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception as e :
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

            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                                         obj_attr_list["secret_key"])
                                         
            _zoneid = self.get_zone(obj_attr_list["name"])

            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            _wait = int(obj_attr_list["update_frequency"])
            sleep(_wait)

            _running_instances = True
          
            _instance_name = "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"];
            _instance_name = _instance_name.lower()

            while _running_instances and _curr_tries < _max_tries :
                _running_instances = False

                _instances = self.cskconn.listVirtualMachines({'zoneid': _zoneid})

                for _instance in _instances :

                    if _instance['name'].count(_instance_name) :
                        _running_instances = True
                        if _instance['state'] == 'Running' or _instance['state'] == 'Stopped' :
                            _msg = "Terminating instance: " 
                            _msg += _instance['id'] + " (" + _instance['name'] + ")"
                            cbdebug(_msg, True)
                            self.cskconn.destroyVirtualMachine({'id': _instance['id']})

                        if _instance['state'] == 'Starting' or _instance['state'] == 'Creating' :
                            _msg = "Will wait for instance "
                            _msg += _instance['id'] + "\"" 
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
                _msg = "All running instances on the VMC " + obj_attr_list["name"]
                _msg += " were terminated"
                cbdebug(_msg)

#            sleep(int(obj_attr_list["update_frequency"])*5)

            _msg = "Now all volumes belonging to the just terminated "
            _msg += "instances on the VMC " + obj_attr_list["name"] + " will "
            _msg += "also be removed."
            cbdebug(_msg)

            _volumes = self.cskconn.listVolumes({'zoneid': _zoneid})

            if _volumes and len(_volumes) :
                for unattachedvol in _volumes :
                    if unattachedvol['state'] == 'Allocated' :
                        _msg = unattachedvol['id'] + ' ' + unattachedvol['state'] 
                        _msg += "... was deleted"
                        cbdebug(_msg)
                        self.cskconn.deleteVolume({'id':unattachedvol['id']})
                    else:
                        _msg = unattachedvol['id'] + ' ' + unattachedvol['state']
                        _msg += "... still attached and could not be deleted"
                        cbdebug(_msg)
            else :
                _msg = "No volumes to remove"
                cbdebug(_msg)

            _status = 0

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :

            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\""
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
            else :
                _status = 0

            if not _status :
                _x, _y = self.connect(obj_attr_list["access"], obj_attr_list["api_key"], obj_attr_list["secret_key"])
            
                _zoneid = self.get_zone(obj_attr_list["name"])

                obj_attr_list["cloud_hostname"] = obj_attr_list["name"];
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

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
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

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_zone(self, zonename) :
        '''
        TBD
        '''
        try :
            _status = 100
            _zoneid = False
            _zones = self.cskconn.listZones()
            for _zone in _zones : 
                if _zone['name'] == zonename : 
                    _zoneid = _zone['id']
                    break;
            
            if _zoneid :
                _status = 0
            else :
                _fmsg = "Unknown CloudPlatform zone (" + zonename + ")"

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg = _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "zone id : " + _zoneid
                cbdebug(_msg)
                return _zoneid

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _instance = obj_attr_list["instance_obj"]
            obj_attr_list["cloud_hostname"] = _instance['name']
            if len(_instance['nic']) : 
                for _nic in _instance['nic'] :
                    if _nic['isdefault'] == True :
                        obj_attr_list["run_cloud_ip"] = _nic['ipaddress']
                        # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
                        obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"] 
                        obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_ip"]

                        return True
        except :
            return False

    def get_sizes(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            
            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], obj_attr_list["secret_key"])
            
            
            _size_list = self.cskconn.listServiceOfferings()

            _status = 168
            _fmsg = "Please check if the defined flavor is present on this "
            _fmsg += "CloudPlatform"

            _sizeid = False
            for _size in _size_list :
                if _size['name'] == obj_attr_list["size"] :
                    _sizeid = _size['id']
                    _status = 0
                    break

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Flavor (" +  obj_attr_list["size"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                return _sizeid

    def get_images(self, zoneid, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured."
            
            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], obj_attr_list["secret_key"])

            _searchOps={'templatefilter' : 'executable'}
 
            if zoneid :
                _searchOps['zoneid'] = zoneid

            _image_list = self.cskconn.listTemplates(_searchOps)

            _fmsg += " Please check if the defined image name is present on this "
            _fmsg += "CloudPlatform"

            _imageid = False

            _candidate_images = []

            for _image in _image_list :
                _image_name = _image['name'].replace(" ", "")
                if obj_attr_list["randomize_image_name"].lower() == "false" and \
                _image_name == obj_attr_list["imageid1"] :
                    _imageid = _image['id']
                    break
                elif obj_attr_list["randomize_image_name"].lower() == "true" and \
                _image_name == obj_attr_list["imageid1"] :
                    _candidate_images.append(_image['id'])
                else :                     
                    True

            if  obj_attr_list["randomize_image_name"].lower() == "true" :
                _imageid = choice(_candidate_images)

            _status = 0

        except Exception as e :
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
    def get_vm_instance(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
        
            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], obj_attr_list["secret_key"])
        
            if "cloud_uuid" in obj_attr_list and obj_attr_list["cloud_uuid"] != "NA" :
                _instances = self.cskconn.listVirtualMachines({'id': obj_attr_list["cloud_uuid"]})
                if _instances :
                    obj_attr_list["instance_obj"] = _instances[0]
                    return _instances[0]
                else :
                    return False
            else :
                _instances = self.cskconn.listVirtualMachines()
                for _instance in _instances :
                    if _instance['name'] == obj_attr_list["cloud_vm_name"] :
                        obj_attr_list["instance_obj"] = _instance
                        return _instance
                return False
        except Exception as msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
            raise CldOpsException(_fmsg, _status)

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"

    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                if _instance['state'] == 'Running' :
                    return _instance
                elif _instance['state'] == 'Error' :
                    _msg = "Instance \"" + obj_attr_list["cloud_vm_name"] + "\"" 
                    _msg += " reported an error (from CloudPlatform)"
                    _status = 1870
                    cberr(_msg)
                    raise CldOpsException(_msg, _status)                    
                else :
                    return False
            else :
                return False
        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
            cberr(_fmsg)
            raise CldOpsException(_fmsg, _status)

    def is_vm_stopped(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                if _instance['state'] == 'Stopped' :
                    return _instance
                else :
                    return False
            else :
                return False
        except Exception as msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''        
        if self.is_vm_running(obj_attr_list) :

            self.take_action_if_requested("VM", obj_attr_list, "provision_complete")

            if self.get_ip_address(obj_attr_list) :
                obj_attr_list["last_known_state"] = "running with ip assigned"
                self.take_action_if_requested("VM", obj_attr_list, "provision_complete")
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
            
            obj_attr_list["cloud_uuid"] = "NA"
            _instance = False

            _instance_name = "cb-" + obj_attr_list["username"]
            _instance_name += '-' + obj_attr_list["cloud_name"]
            _instance_name += '-' + "vm"
            _instance_name += obj_attr_list["name"].split("_")[1]
            _instance_name += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :            
                _instance_name += '-' + obj_attr_list["ai_name"]            
            
            obj_attr_list["cloud_vm_name"] = _instance_name.replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to cloud platform manager"

            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                             obj_attr_list["secret_key"])

            _zoneid = self.get_zone(obj_attr_list["vmc_name"])
            
            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            _sizeid = self.get_sizes(obj_attr_list)
            _imageid = self.get_images(_zoneid, obj_attr_list)

            _msg = "Starting an instance on CloudPlatform vm name : " + obj_attr_list["cloud_vm_name"] + ", using the imageid \""
            _msg += obj_attr_list["imageid1"] + "\"(" + _imageid + ") and size \""
            _msg += obj_attr_list["size"] + "\"(" + _sizeid + ") on VMC \""
            _msg += obj_attr_list["vmc_name"] + "\""

            cbdebug(_msg, True)

            _instance = self.cskconn.deployVirtualMachine({'name':obj_attr_list["cloud_vm_name"], \
                                                      'serviceofferingid':_sizeid, \
                                                      'templateid':_imageid, \
                                                      'keypair':obj_attr_list["key_name"], \
                                                      'securitygroupnames' : obj_attr_list["security_groups"], \
                                                      'zoneid':_zoneid})
 
            if _instance :
                sleep(int(obj_attr_list["update_frequency"]))
                
                obj_attr_list["cloud_uuid"] = '{0}'.format(_instance['id'])

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = "unknown"

                if "instance_obj" in obj_attr_list : 
                    del obj_attr_list["instance_obj"]                    
                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916
                
            else :
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if "instance_obj" in obj_attr_list :
                del obj_attr_list["instance_obj"]

            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be created "
                _msg += "on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)
                if "cloud_uuid" in obj_attr_list :
                    obj_attr_list["mgt_deprovisioning_request_originated"] = int(time())
                    self.vmdestroy(obj_attr_list)
                else :
                    if _instance :
                        self.cskconn.destroyVirtualMachine({'id': _instance['id']})
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
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

            if "prov_cloud_ip" in obj_attr_list :
                try :
                    _space_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "space", False) 

                    _data_dir = _space_attr_list["data_working_dir"] + "/" + obj_attr_list["experiment_id"]

                    if not access(_data_dir, F_OK) :
                        makedirs(_data_dir)

                    _cmd = "scp -i " 
                    _cmd += _space_attr_list["ssh_key_name"]
                    _cmd += " " + obj_attr_list["login"] + "@" + obj_attr_list["prov_cloud_ip"]
                    _cmd += ":/home/" + obj_attr_list["login"] + "/nmon/nmon.csv "
                    _cmd += _data_dir + "/nmon_" + obj_attr_list["cloud_vm_name"] + ".csv"

                    print(_cmd)

                    _proc_man = ProcessManagement()
                    _proc_man.run_os_command(_cmd)
                except Exception as msg :
                    cbdebug(str(msg), True)

            _time_mark_drs = int(time())
            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                
            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                             obj_attr_list["secret_key"])

            _zoneid = self.get_zone(obj_attr_list["vmc_name"])
            
            _wait = int(obj_attr_list["update_frequency"])

            _instance = self.get_vm_instance(obj_attr_list)

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])
        
            if _instance :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (instance id " + _instance['id'] + ")"
                _msg += "...."
                cbdebug(_msg, True)
                
                self.cskconn.destroyVirtualMachine({'id': _instance['id']})

                sleep(_wait)

                while self.is_vm_running(obj_attr_list) :
                    sleep(_wait)
                    
                _time_mark_drc = int(time())
                obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                    _time_mark_drc - _time_mark_drs
                    
            else :
                True

            # This needs to be changed later. I could not find an easy way to
            # find the actual volume id of a given instance
             
            _volumes = self.cskconn.listVolumes({'zoneid': _zoneid})

            if _volumes and len(_volumes) :
                for unattachedvol in _volumes :
                    if unattachedvol['state'] == 'Allocated' :
                        _msg = unattachedvol['id'] + ' ' + unattachedvol['state'] 
                        _msg += "... was deleted"
                        cbdebug(_msg)
                        self.cskconn.deleteVolume({'id':unattachedvol['id']})
                    else:
                        _msg = unattachedvol['id'] + ' ' + unattachedvol['state'] 
                        _msg += "... still attached and could not be deleted"
                        cbdebug(_msg)
            else :
                _msg = "No volumes to remove"
                cbdebug(_msg)
           
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on CloudPlatform \"" + obj_attr_list["cloud_name"]
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

            if not self.cskconn :
                self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                             obj_attr_list["secret_key"])

            _zoneid = self.get_zone(obj_attr_list["vmc_name"])

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"]) * 10

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                self.cskconn.stopVirtualMachine({'id': _instance['id']})
                while not self.is_vm_stopped(obj_attr_list) :
                    sleep(_wait)

                _osTypes = self.cskconn.listOsTypes();
                _osTypeId = False
                for _osType in _osTypes : 
                    if _osType['description'] == 'Ubuntu 12.04 (64-bit)' :
                        _osTypeId = _osType['id']
                        break;

                if not _osTypeId : 
                    _status  = 311
                    _msg = "Can't get osTypeId"
                    cberr(_msg)
                    raise CldOpsException(_status, _msg)

                _volumeId = False
                _volumes = self.cskconn.listVolumes({'virtualmachineid':_instance['id']})
                if _volumes and len(_volumes) :
                    _volume = _volumes[0]
                    _volumeId = _volume['id']
 
                if not _volumeId : 
                    _status  = 312
                    _msg = "Can't get volumeId"
                    cberr(_msg)
                    raise CldOpsException(_status, _msg)
                
                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent. "
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                _msg += " from " + _instance['name'] + "(" + _volumeId + ")" 
                cbdebug(_msg, True)

                _captured_image = self.cskconn.createTemplate({'volumeid':_volumeId , 'name':obj_attr_list["captured_image_name"], 'displaytext':obj_attr_list["captured_image_name"], 'ostypeid':_osTypeId})
                _captured_imageid = _captured_image['id']

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"] + "\""
                _msg += ", imageid  \"" + _captured_imageid
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :
                    _image_instance = self.cskconn.listTemplates({'zoneid':_zoneid, 'templatefilter':'executable','id':_captured_imageid})
                    if len(_image_instance)  :
                        if _image_instance[0]['status'] == "Download Complete" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

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
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be captured "
                _msg += " on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += " status \"" + str(_status) + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
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
    
            self.connect(obj_attr_list["access"], obj_attr_list["api_key"], \
                         obj_attr_list["secret_key"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                if _ts == "fail" :
                    self.cskconn.stopVirtualMachine({'id': _instance['id']})
                elif _ts == "save" :
                    self.cskconn.stopVirtualMachine({'id': _instance['id']})
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    self.cskconn.startVirtualMachine({'id': _instance['id']})
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    self.cskconn.startVirtualMachine({'id': _instance['id']})
            
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)
                        
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on CloudPlatform \"" 
                _msg += obj_attr_list["cloud_name"] + "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on CloudPlatform \"" 
                _msg += obj_attr_list["cloud_name"] + "\"."
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
            _status = 0

        except Exception as msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace        
    def aiundefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            self.take_action_if_requested("AI", obj_attr_list, current_step)                        
            _status = 0

        except Exception as msg :
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
    
        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be undefined "
                _msg += " on CloudPlatform \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on CloudPlatform \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

