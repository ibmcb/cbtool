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
    Created on Oct 20, 2015

    GCE Object Operations Library

    @author: Marcio A. Silva
'''
import httplib2
import httplib2shim
import traceback

from time import time, sleep
from random import randint
from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, is_number, DataOpsException
from lib.remote.ssh_ops import get_ssh_key

from .shared_functions import CldOpsException, CommonCloudFunctions 

from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GCEExceptionHttpError

class GceCmds(CommonCloudFunctions) :
    # GCE uses the same image IDs for all regions and all zones.
    # Attempting to discover them more than once invalidates the
    # last attempt at discovering them by inadvertenly rewriting the image IDs
    # with random numbers, so let's make sure we only do it once.
    base_images_checked = False

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
        self.gceconn = False
        self.instances_project= None
        self.images_project = None
        self.instance_info = None
        self.expid = expid
        self.additional_rc_contents = ''
        self.http_conn = {}

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Google Compute Engine"

    @trace
    def connect(self, project, secret_key, zone = "us-east1-b", http_conn_id = None) :
        '''
        TBD
        '''
        try :
            _status = 100
            if not self.instances_project :
                project = project.split(',')
                if len(project) == 2 :
                    self.images_project, self.instances_project = project
                else :
                    self.instances_project = project[0]
                    self.images_project = self.instances_project

            _credentials = GoogleCredentials.get_application_default()

            if _credentials.create_scoped_required():
                _credentials = _credentials.create_scoped('https://www.googleapis.com/auth/compute')

            _http_conn_id = "common"
            if http_conn_id :
                _http_conn_id = http_conn_id

            if _http_conn_id not in self.http_conn :
                self.http_conn[_http_conn_id] = _credentials.authorize(http = httplib2shim.Http())

            self.gceconn = build('compute', 'v1', http = self.http_conn[http_conn_id])
            _zone_list = self.gceconn.zones().list(project=self.instances_project).execute(http = self.http_conn[http_conn_id])["items"]

            _zone_info = False
            for _idx in range(0,len(_zone_list)) :
                if _zone_list[_idx]["description"] == zone :
                    _zone_info = _zone_list[_idx]
                    _zone_hostname = _zone_info["region"]
                    _msg = "Selected zone is " + str(_zone_info["description"])
                    cbdebug(_msg)
                    break

            if _zone_info :
                _status = 0
            else :
                _fmsg = "Unknown " + self.get_description() + " zone (" + zone + ")"
                
        except GCEExceptionHttpError as obj:
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _fmsg = str(msg)
            _status = 23

        finally :
            if _status :
                _msg =  self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :

                _msg =  self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, _zone_hostname

    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.connect(access, credentials, vmc_name, vmc_name)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults, False, vmc_name)
            
            if not GceCmds.base_images_checked :
                _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_name, vm_defaults)

                if not (_run_netname_found and _prov_netname_found and _key_pair_found) :
                    _msg = "Check the previous errors, fix it (using GCE's web"
                    _msg += " GUI (Google Developer's Console) or gcloud CLI utility"
                    _status = 1178
                    raise CldOpsException(_msg, _status)

                GceCmds.base_images_checked = True

                if len(_detected_imageids) :
                    _status = 0
                else :
                    _status = 1
            else :
                _status = 0

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
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
    def check_images(self, vmc_name, vm_templates, http_conn_id, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _map_name_to_id = {}
        _map_id_to_name = {}

        _registered_image_list = []
        _registered_images = self.gceconn.images().list(project=self.images_project).execute(http = self.http_conn[http_conn_id])
        if "items" in _registered_images :
            _registered_image_list = _registered_images["items"]
        
        _registered_imageid_list = []

        for _registered_image in _registered_image_list :
            _registered_imageid_list.append(_registered_image["id"])
            _map_name_to_id[_registered_image["name"]] = _registered_image["id"]

        for _vm_role in list(vm_templates.keys()) :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]

            if _imageid != "to_replace" :
                if _imageid in _map_name_to_id and _map_name_to_id[_imageid] != _imageid :
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                else :
                    _map_name_to_id[_imageid] = "00000" + ''.join(["%s" % randint(0, 9) for num in range(0, 14)])
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])

                _map_id_to_name[_map_name_to_id[_imageid]] = _imageid

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_id_to_name, vm_defaults)

        return _detected_imageids

    @trace
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

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"], obj_attr_list["name"])

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')
            _pre_existing_instances = False

            _running_instances = True

            while _running_instances :
                _running_instances = False

                _instance_list = self.get_instances(obj_attr_list, "vm", "all")
                
                for _instance in _instance_list :

                    if _instance["name"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower()) and _instance["status"] == 'RUNNING' :
                        self.gceconn.instances().delete(project = self.instances_project, \
                                                        zone = obj_attr_list["name"], \
                                                        instance = _instance["name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                        _running_instances = True

                sleep(int(obj_attr_list["update_frequency"]))

            sleep(int(obj_attr_list["update_frequency"])*5)

            self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')
            
            _volume_list = self.get_instances(obj_attr_list, "vv", "all")

            if len(_volume_list) :
                for _volume in _volume_list :
                    if _volume["name"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower()) :
                        if not "users" in _volume :
                            self.gceconn.disks().delete(project = self.instances_project, \
                                                        zone = obj_attr_list["name"], \
                                                        disk = _volume["name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                            _msg = _volume["id"] + " detached "
                            _msg += "... was deleted"
                            cbdebug(_msg)
                        else:
                            _msg = _volume["id"] + ' '
                            _msg += "... still attached and could not be deleted"
                            cbdebug(_msg)
            else :
                _msg = "No volumes to remove"
                cbdebug(_msg)

            _status = 0

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)
            
        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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

            _x, _y, _hostname = self.connect(obj_attr_list["access"], obj_attr_list["credentials"], obj_attr_list["name"], obj_attr_list["name"])

            obj_attr_list["cloud_hostname"] = _hostname + "-" + obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = gethostbyname(_hostname.split('/')[2])
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

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)
            
        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23

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

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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

                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], _vmc_attr_list["name"], _vmc_attr_list["name"])

                _instance_list = self.get_instances(_vmc_attr_list, "vm", "all")                

                for _instance in _instance_list :

                    if _instance["name"].count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower()) :
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

        self.temp_key_metadata = {}
        self.project_metadata = self.gceconn.projects().get(project=self.instances_project).execute(http = self.http_conn[connection])

        if "items" in self.project_metadata["commonInstanceMetadata"] :
            for _element in self.project_metadata["commonInstanceMetadata"]["items"] :
                if _element["key"] == "sshKeys" :
                    for _component in _element["value"].split('\n') :
                        if len(_component.split(' ')) == 3 :
                            _r_key_tag, _r_key_contents, _r_key_user = _component.split(' ')
                            _r_key_name, _r_key_type = _r_key_tag.split(':')
                            self.temp_key_metadata[_r_key_name] = _r_key_tag + ' ' + _r_key_contents + ' ' + _r_key_user
                            _r_key_type, _r_key_contents, _r_key_fingerprint = \
                            get_ssh_key(_r_key_type + ' ' + _r_key_contents + ' ' + _r_key_user, self.get_description(), False)

                            registered_key_pairs[_r_key_name] = _r_key_fingerprint + "-NA"
                            #_temp_key_metadata[key_name] = key_name + ':' + _key_type + ' ' + _key_contents + ' ' + vm_defaults["login"] + "@orchestrator"
            
        return True

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :

            _private_ip_address = self.instance_info["networkInterfaces"][0]["networkIP"]
            _public_ip_address = self.instance_info["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

            cbdebug("Got IPs for " + obj_attr_list["name"] + ": " + str(_private_ip_address) + ", " + str(_public_ip_address))
                       
            _public_hostname = obj_attr_list["cloud_vm_name"] + '.' + obj_attr_list["vmc_name"]
            _private_hostname = obj_attr_list["cloud_vm_name"] + '.' + obj_attr_list["vmc_name"]
            obj_attr_list["public_cloud_ip"] = _public_ip_address
                        
            if obj_attr_list["run_netname"] == "private" :
                obj_attr_list["cloud_hostname"] = _private_hostname
                obj_attr_list["run_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["cloud_hostname"] = _public_hostname
                obj_attr_list["run_cloud_ip"] = _public_ip_address

            if obj_attr_list["prov_netname"] == "private" :
                obj_attr_list["prov_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["prov_cloud_ip"]  = _public_ip_address

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            if obj_attr_list["prov_netname"].lower() == "private" :
                obj_attr_list["prov_cloud_ip"] = _private_ip_address
            else :
                obj_attr_list["prov_cloud_ip"] = _public_ip_address

            return True

        except Exception as e:
            cbdebug("Failed to retrieve IP for: " + obj_attr_list["name"] + ": " + str(e))
            return False

    @trace
    def get_instances(self, obj_attr_list, obj_type = "vm", identifier = "all") :
        '''
        TBD
        '''

        try :
            _instances = []
            _fmsg = "Error while getting instances"

            if "vmc_name" in obj_attr_list :
                _actual_zone = obj_attr_list["vmc_name"]
            else :
                _actual_zone = obj_attr_list["name"]

            if obj_type == "vm" :
                if identifier == "all" :
                    _instance_list = self.gceconn.instances().list(project = self.instances_project, \
                                                                   zone =  _actual_zone).execute(http = self.http_conn[obj_attr_list["name"]])
                else :
                    _instance_list = self.gceconn.instances().get(project = self.instances_project, \
                                                                    zone =  _actual_zone, instance = identifier).execute(http = self.http_conn[obj_attr_list["name"]])
            else :
                if identifier == "all" :
                    _instance_list = self.gceconn.disks().list(project = self.instances_project, \
                                                                   zone =  _actual_zone).execute(http = self.http_conn[obj_attr_list["name"]])
                else :
                    _instance_list = self.gceconn.disks().get(project = self.instances_project, \
                                                                   zone =  _actual_zone, \
                                                                   disk = identifier).execute(http = self.http_conn[obj_attr_list["name"]])
                    
            if "items" in _instance_list :
                _instances = _instance_list["items"]

            elif "status" in _instance_list :
                _instances = _instance_list
                
            return _instances
        
        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            if _status == 404 :
                return []
            else :
                _fmsg = str(obj)
                raise CldOpsException(_fmsg, _status)
        
        except Exception as _fmsg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            return []

    @trace
    def get_images(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _candidate_images = None
            
            _fmsg = "An error has occurred, but no error message was captured"

            if "role" in obj_attr_list and obj_attr_list["role"] == "check" :
                if obj_attr_list["imageid1"].count("ubuntu") :
                    obj_attr_list["images_project"] = "ubuntu-os-cloud"
                elif obj_attr_list["imageid1"].count("rhel") :                    
                    obj_attr_list["images_project"] = "rhel-cloud"            
                elif obj_attr_list["imageid1"].count("centos") :                    
                    obj_attr_list["images_project"] = "centos-cloud"
                else :
                    obj_attr_list["images_project"] = self.images_project                                
            else :
                obj_attr_list["images_project"] = self.images_project

            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                _filter = "id eq " + obj_attr_list["imageid1"]

            else :
                _filter = "name eq " + obj_attr_list["imageid1"]

            _candidate_images = self.gceconn.images().list(project = obj_attr_list["images_project"], \
                                                           filter = _filter).execute(http = self.http_conn[obj_attr_list["name"]])
            
            _fmsg = "Please check if the defined image name is present on this "
            _fmsg +=  self.get_description()

            if "items" in _candidate_images :
                obj_attr_list["imageid1"] = _candidate_images["items"][0]["name"]
                obj_attr_list["boot_volume_imageid1"] = _candidate_images["items"][0]["id"]
                _status = 0

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)
            raise CldOpsException(_fmsg, _status)
        
        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            if _status :
                _msg = "Image Name (" +  obj_attr_list["imageid1"] + ") not found: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                return _candidate_images

    @trace
    def get_networks(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

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
                return True

    @trace            
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        for _kn in [ key_name + "  cbtool", vm_defaults["login"] + "  " + vm_defaults["login"]] :

            _actual_key_name, _actual_user_name = _kn.split("  ")

            self.temp_key_metadata[_actual_key_name] = _actual_key_name + ':' + key_type + ' ' + key_contents + ' ' + _actual_user_name + "@orchestrator"

        _key_list_str = ''

        for _key in list(self.temp_key_metadata.keys()) :
            _key_list_str += self.temp_key_metadata[_key] + '\n'

        _key_list_str = _key_list_str[0:-1]

        if "items" in self.project_metadata["commonInstanceMetadata"] :
            for _element in self.project_metadata['commonInstanceMetadata']['items'] :
                if _element["key"] == "sshKeys" :
                    _element["value"] += _key_list_str
        else :
            self.project_metadata['commonInstanceMetadata']["items"] = []
            self.project_metadata['commonInstanceMetadata']['items'].append({"key": "sshKeys", "value" : _key_list_str})

        self.gceconn.projects().setCommonInstanceMetadata(project=self.instances_project, body=self.project_metadata["commonInstanceMetadata"]).execute(http = self.http_conn[connection])

        return True

    @trace
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        # Checks for len() == 18/19 no longer valid. Images of length 16 were found.
        if is_number(imageid) :
            return True
        
        return False

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :
                _instance_state = _instance["status"]
            else :
                _instance_state = "non-existent"
                        
            if _instance_state == "RUNNING" :
                self.instance_info = _instance
                
                if "disks" in _instance :
                    for _disk in _instance["disks"] :
                        if _disk["index"] == 0 :
                            obj_attr_list["boot_link_imageid1"] = _disk["source"]
                            break
                return True
            else :
                return False

        except GCEExceptionHttpError as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = int(obj.resp.status)
            _fmsg = str(obj)
            raise CldOpsException(_fmsg, _status)
        
        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _fmsg = str(msg)
            cberr(_fmsg)
            _status = 23
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''        
        cbdebug("Waiting for " + obj_attr_list["name"] + " to be running...")
        if self.is_vm_running(obj_attr_list) :

            cbdebug("Getting IP for " + obj_attr_list["name"])
            if self.get_ip_address(obj_attr_list) :
                cbdebug("IP found for " + obj_attr_list["name"])
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                cbdebug("IP not found for " + obj_attr_list["name"])
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            cbdebug("VM still not running yet: " + obj_attr_list["name"])
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

        except Exception as e :
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

            obj_attr_list["cloud_vv_instance"] = False

            if "cloud_vv_type" not in obj_attr_list :
                '''
                GCE types as of 2018:
                pd-standard
                local-ssd
                pd-ssd
                '''
                obj_attr_list["cloud_vv_type"] = "pd-standard"
             
            _disk_type = "zones/" + obj_attr_list["vmc_name"] + "/diskTypes/" + obj_attr_list["cloud_vv_type"]

            if "cloud_vv" in obj_attr_list and str(obj_attr_list["cloud_vv"]).lower() != "false":

                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)
    
                obj_attr_list["last_known_state"] = "about to send volume create request"

                _config = {
                    'name': obj_attr_list["cloud_vv_name"], 
                    'description' : "used by " + obj_attr_list["cloud_vm_name"],
                    'sizeGb' : obj_attr_list["cloud_vv"],
                    'type' : _disk_type,
                }


                _operation = self.gceconn.disks().insert(project = self.instances_project, \
                                                         zone =  obj_attr_list["vmc_name"], \
                                                         body = _config).execute(http = self.http_conn[obj_attr_list["name"]])

                if self.wait_until_operation(obj_attr_list, _operation) :
                    _instance =  self.get_instances(obj_attr_list, "vv", obj_attr_list["cloud_vv_name"])
                    
                    obj_attr_list["cloud_vv_uuid"] = _instance["id"]
                    obj_attr_list["cloud_vv_source"] = _instance["selfLink"]
                    
            _status = 0

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEExceptionHttpError as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except KeyboardInterrupt :
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = 23
            _fmsg = str(e)
    
        finally :
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace
    def vvdestroy(self, obj_attr_list, identifier) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if "cloud_vv" in obj_attr_list and str(obj_attr_list["cloud_vv"]).lower() != "false":
                _instance = self.get_instances(obj_attr_list, "vv", obj_attr_list[identifier])

                if _instance :
                    self.common_messages("VV", obj_attr_list, "destroying", 0, '')

                    _operation = self.gceconn.disks().delete(project = self.instances_project, \
                                                             zone =  obj_attr_list["vmc_name"], \
                                                             disk = obj_attr_list[identifier]).execute(http = self.http_conn[obj_attr_list["name"]])

                    self.wait_until_operation(obj_attr_list, _operation)

            _status = 0
                    
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as e :
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
            _operation = False
            
            self.determine_instance_name(obj_attr_list)
            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].lower()
            obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].lower().replace("_", "-")
            self.determine_key_name(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["name"])

            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += " is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"
            
            self.get_images(obj_attr_list)
            self.get_networks(obj_attr_list)

            obj_attr_list["config_drive"] = False

            _status, _fmsg = self.vvcreate(obj_attr_list)
            
            # "Security groups" must be a list
            _security_groups = []
            _security_groups.append(obj_attr_list["security_groups"])
                                            
            _source_disk_image = "projects/" + obj_attr_list["images_project"] + "/global/images/" + obj_attr_list["imageid1"]
            _machine_type = "zones/" + obj_attr_list["vmc_name"] + "/machineTypes/" + obj_attr_list["size"]

            if "cloud_rv_type" not in obj_attr_list :
                obj_attr_list["cloud_rv_type"] = "pd-standard"
            _root_type = "zones/" + obj_attr_list["vmc_name"] + "/diskTypes/" + obj_attr_list["cloud_rv_type"]

            if "cloud_rv" in obj_attr_list and obj_attr_list["cloud_rv"] != "0":
                _rv_size = obj_attr_list["cloud_rv"]
            else:
                _rv_size = None

            _config = {
                'name': obj_attr_list["cloud_vm_name"],
                'machineType': _machine_type,
        
                # Specify the boot disk and the image to use as a source.
                'disks': [
                    {
                        'boot': True,
                        'autoDelete': True,
                        'initializeParams': {
                            'sourceImage': _source_disk_image,
                            'diskType' : _root_type,
                            'diskSizeGb': _rv_size,
                        }
                    }
                ],
        
                # Specify a network interface with NAT to access the public
                # internet.
                'networkInterfaces': [{
                    'network': 'global/networks/default',
                    'accessConfigs': [
                        {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                    ]
                }],
        
                # Allow the instance to access cloud storage and logging.
                'serviceAccounts': [{
                    'email': 'default',
                    'scopes': [
                        'https://www.googleapis.com/auth/devstorage.read_write',
                        'https://www.googleapis.com/auth/logging.write'
                    ]
                }],
        
                # Metadata is readable from the instance and allows you to
                # pass configuration from deployment scripts to instances.
                'metadata': {
                    'items': [{
                        'key': 'expid',
                        'value': obj_attr_list["experiment_id"]
                    }, {
                        'key': 'use',
                        'value': "cloudbench"
#                    }, {
#                        'key': 'sshKeys',
#                        'value': obj_attr_list["login"] + ':' + \
#                        obj_attr_list["ssh_key_type"] + ' ' + \
#                        obj_attr_list["ssh_key_contents"].strip('\n') + ' ' + \
#                        obj_attr_list["ssh_key_name"].strip('\n') + "@orchestrator"
                    }]            
                }
            }

            if "preemptible" in obj_attr_list and str(obj_attr_list["preemptible"]).lower() == "true" :
                cbdebug("Will create a pre-emptible instance.", True)
                _config["scheduling"] = { "preemptible" : True }

            user_data = self.populate_cloudconfig(obj_attr_list)

            if user_data :
                _config["metadata"]["items"].append({"key" : "user-data", "value" : user_data})
                cbdebug("Appended userdata...", True)

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "none":
                self.common_messages("VV", obj_attr_list, "attaching", _status, _fmsg)
            
                _config["disks"].append({'boot': False, \
                                         "autoDelete" : True, \
                                         "source" : obj_attr_list["cloud_vv_source"]})

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            sleep(float(obj_attr_list["name"].replace("vm_",'')) + 1.0)

            self.pre_vmcreate_process(obj_attr_list)

            _operation = self.gceconn.instances().insert(project = self.instances_project, \
                                                         zone = obj_attr_list["vmc_name"], \
                                                         body = _config).execute(http = self.http_conn[obj_attr_list["name"]])
            
            if self.wait_until_operation(obj_attr_list, _operation) :

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = "unknown"

                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"                    
                    _status = 916

            else :
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                _status = 100

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line)
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEExceptionHttpError as obj :
            for line in traceback.format_exc().splitlines() :
                cberr(line)
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cberr(line)
            _fmsg = str(msg)
            _status = 23

        finally :

            if _status and _operation is not False :
                cbdebug("Error after VM creation. Cleanup...", True)
                self.vmdestroy_repeat(obj_attr_list)

            self.post_vmboot_process(obj_attr_list)
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
                
            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])
            
            if _instance :
                self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                _operation = self.gceconn.instances().delete(project = self.instances_project, \
                                                             zone = obj_attr_list["vmc_name"], \
                                                             instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)

                while self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries :
                    sleep(_wait)
                    _curr_tries += 1
                    
            else :
                True

            _status, _fmsg = self.vvdestroy(obj_attr_list, "cloud_vm_name")
                        
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs            
             
            _status, _fmsg = self.vvdestroy(obj_attr_list, "cloud_vv_name")

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")
            
        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEExceptionHttpError as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line)
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cberr(line)
            _fmsg = str(msg)
            _status = 23
    
        finally :
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

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            if not self.gceconn :
                self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                             obj_attr_list["vmc_name"], obj_attr_list["name"])

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

                obj_attr_list["captured_image_name"] = obj_attr_list["captured_image_name"].replace('_','-')

                _operation = self.gceconn.instances().delete(project = self.instances_project, \
                                                             zone = obj_attr_list["vmc_name"], \
                                                             instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)

                _config = {
                    "name": obj_attr_list["captured_image_name"], 
                    "sourceDisk" : obj_attr_list["boot_link_imageid1"]
                }

                _operation = self.gceconn.images().insert(project = self.images_project, \
                                                         body = _config).execute(http = self.http_conn[obj_attr_list["name"]])


                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _filter = "name eq " + obj_attr_list["captured_image_name"]
    
                    _image_instances = self.gceconn.images().list(project = self.images_project, \
                                                                  filter = _filter).execute(http = self.http_conn[obj_attr_list["name"]])
                                
                    if "items" in _image_instances :
                        if _image_instances["items"][0]["status"] == "READY" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    sleep(_wait)             
                    _curr_tries += 1

                if _curr_tries > _max_tries  :
                    _status = 1077
                    _fmsg = "" + obj_attr_list["name"] + ""
                    _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _fmsg +=  "could not be captured after " + str(_max_tries * _wait) + " seconds.... "
                else :
                    _status = 0

            else :
                _fmsg = "This instance does not exist"
                _status = 1098
            
        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
            return _status, _msg

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

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            _instance = self.get_instances(obj_attr_list, "vm", obj_attr_list["cloud_vm_name"])

            if _instance :
                if _ts == "fail" :
                    _operation = self.gceconn.instances().stop(project = self.instances_project, \
                                                               zone =  obj_attr_list["vmc_name"], \
                                                               instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                elif _ts == "save" :
                    _operation = self.gceconn.instances().stop(project = self.instances_project, \
                                                               zone =  obj_attr_list["vmc_name"], \
                                                               instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                                                               
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _operation = self.gceconn.instances().start(project = self.instances_project, \
                                                               zone =  obj_attr_list["vmc_name"], \
                                                                instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])
                                                                
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _operation = self.gceconn.instances().start(project = self.instances_project, \
                                                                zone =  obj_attr_list["vmc_name"], \
                                                                instance = obj_attr_list["cloud_vm_name"]).execute(http = self.http_conn[obj_attr_list["name"]])

                self.wait_until_operation(obj_attr_list, _operation)
 
            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs
                        
            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as msg :
            _fmsg = str(msg)
            _status = 23
    
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
        try :
            _status = 100
            
            _fmsg = "An error has occurred, but no error message was captured"
            
            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')
                                   
            self.connect(obj_attr_list["access"], obj_attr_list["credentials"], \
                         obj_attr_list["vmc_name"], obj_attr_list["vmc_name"])
            
            _filter = "name eq " + obj_attr_list["imageid1"]

            _image_instances = self.gceconn.images().list(project = self.images_project, \
                                                           filter = _filter).execute(http = self.http_conn[obj_attr_list["vmc_name"]])

            if "items" in _image_instances :
                obj_attr_list["imageid1"] = _image_instances["items"][0]["name"]
                obj_attr_list["boot_volume_imageid1"] = _image_instances["items"][0]["id"]
                
                _operation = self.gceconn.images().delete(project = self.images_project, \
                                                          image = obj_attr_list["imageid1"]).execute(http = self.http_conn[obj_attr_list["vmc_name"]])

                _wait = int(obj_attr_list["update_frequency"])
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])

                _image_deleted = False                
                while not _image_deleted and _curr_tries < _max_tries :

                    _filter = "name eq " + obj_attr_list["imageid1"]
        
                    _image_instances = self.gceconn.images().list(project = self.images_project, \
                                                                   filter = _filter).execute(http = self.http_conn[obj_attr_list["vmc_name"]])                    

                    if "items" not in _image_instances :
                        _image_deleted = True
                    else :
                        sleep(_wait)
                        _curr_tries += 1
                        
            _status = 0

        except GCEExceptionHttpError as obj :
            _status = int(obj.resp.status)
            _fmsg = str(obj)

        except Exception as e :
            _status = 23
            _fmsg = str(e)
            
        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg
        
    @trace
    def wait_until_operation(self, obj_attr_list, opid) :
        '''
        TBD
        '''

        _msg = "Waiting for " + obj_attr_list["name"] + " operation to finish..."
        cbdebug(_msg)
    
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        _wait = int(obj_attr_list["update_frequency"])
        sleep(_wait)
        
        while _curr_tries < _max_tries :
            _start_pooling = int(time())

            _op = self.gceconn.zoneOperations().get(project = self.instances_project, \
                                                           zone =  obj_attr_list["vmc_name"], \
                                                           operation = opid["name"]).execute(http = self.http_conn[obj_attr_list["name"]])
            
            if _op['status'] == 'DONE':
                if 'error' in _op :
                    raise CldOpsException(_op["error"], 2001)

                if str(obj_attr_list["cloud_vm_uuid"]).lower() == "none" :
                    obj_attr_list["cloud_vm_uuid"] = _op["id"]

                return True
            else:
                sleep(_wait)
                _curr_tries += 1
                
        _fmsg = obj_attr_list["name"] + " operation did not finish after "
        _fmsg += str(_max_tries * _wait) + " seconds... "
        _fmsg += "Giving up."
        
        raise CldOpsException(_op["error"], 2001)
