#!/usr/bin/env python
#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express orz implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

'''
    Created on Dec 15, 2020

    ZSTACK Object Operations Library

    @author: tao.wu
'''
from time import time, sleep
import os
import sys
from random import randint
from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, dic2str, DataOpsException, create_restart_script, weighted_choice

from shared_functions import CldOpsException, CommonCloudFunctions

# import apibinding.api_actions as api_actions
# from apibinding import api
# import apibinding.inventory as inventory
import requests
import json
import traceback


class ZskCmds(CommonCloudFunctions):
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
        self.expid = expid
        self.additional_rc_contents = ''

    def zsk_login_by_account(self, access, name='admin', password='password'):
        import hashlib
        action = "accounts/login"
        action_url = access + action
        body = {
            "logInByAccount" : {
                "accountName": name,
                "password": hashlib.sha512(password).hexdigest(),
            }
        }
        headers = {
            'Content-Type': 'application/json', 'charset': 'UTF-8'
        }
        _r = requests.post(action_url, data=json.dumps(body), headers=headers)
        return _r.json()['inventory']['uuid']

    def zsk_logout(self, access, session_uuid):
        action = "accounts/sessions/"
        action_url = access + action + session_uuid
        headers = {
            'Content-Type': 'application/json', 'charset': 'UTF-8'
        }
        _r = requests.delete(action_url, data=None, headers=headers)

    def zsk_execute_action_with_session(self, access, action_url, action_type='post', body_dict={}):
        '''
        Execute action via RESTfull API
        ZStack API allows you to perform operations on resources by using the following four HTTP verbs, action_type as follows.
        get, Obtains resource information.
        post, Creates a resource
        put, Updates a resource
        delete, Deletes a resource.
        for post,delete, put, it's an asynchronous API, will receive a 202 status code  and a round-robin address,
        need periodically request the round-robin address to obtain API operation results.
        '''
        try:
            _respond = {}
            _session_uuid = self.zsk_login_by_account(access)
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Authorization': 'OAuth ' + _session_uuid,
            }
            if action_type == 'post':
                _res = requests.post(action_url, headers=headers, data=json.dumps(body_dict))
                result_url = _res.json()['location']
                for i in range(300):
                    _r = requests.get(result_url, headers=headers, params={})
                    if _r.json().get('inventory') is not None:
                        _respond = _r.json()
                        break
                    elif _r.json().get('error') is not None:
                        _respond = _r.json()
                        raise Exception('Failed to post ' + action_url + ', error: ' + _r.json()['error']['details'])
                    sleep(1)
            elif action_type == 'delete':
                _r = requests.delete(action_url, headers=headers, params=body_dict, timeout=300)
                result_url = _r.json()['location']
                _r = requests.get(result_url, headers=headers, params={})
                for i in range(300):
                    _r = requests.get(result_url, headers=headers, params={})
                    if _r.status_code == 200:
                        _respond = _r.json()
                        break
                    elif _r.json().get('error') is not None:
                        _respond = _r.json()
                        raise Exception('Failed to delete ' + action_url + ' , ERROR: ' + _r.json()['error']['details'])
                    sleep(1)
            elif action_type == 'get':
                _r = requests.get(action_url, headers=headers, params=body_dict)
                if _r.status_code == 200:
                    _respond = _r.json()
                else:
                    raise Exception('Failed to get ' + action_url + ', code:' + str(_r.status_code))
            elif action_type == 'put':
                _r = requests.put(action_url, headers=headers, data=json.dumps(body_dict))
                result_url = _r.json()['location']
                for i in range(300):
                    _r = requests.get(result_url, headers=headers, params={})
                    if _r.json().get('inventory') is not None:
                        _respond = _r.json()
                        break
                    elif _r.json().get('error') is not None:
                        _respond = _r.json()
                        raise Exception('Failed to post ' + action_url + ' , ERROR: ' + _r.json()['error']['details'])
                    sleep(1)
        except Exception as e:
            cberr(traceback.print_exc(file=sys.stdout))
        finally:
            self.zsk_logout(access, _session_uuid)
            return _respond


    def zsk_update_mn_global(self, access, category, name, value):
        '''
        update zstack global settings via RESTfull API.
        '''
        action = 'global-configurations/' + category + '/' + name + '/actions'
        action_url = access + action
        body = {
            "updateGlobalConfig": {
                "value": value}
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_configure_mn(self, access):
        self.zsk_update_mn_global(access, 'vm', 'deletionPolicy', 'Direct')
        self.zsk_update_mn_global(access, 'volume', 'deletionPolicy', 'Direct')
        self.zsk_update_mn_global(access, 'identity ', 'session.maxConcurrent', '1000')

    def zsk_gen_query_conditions(self, name, op, value):
        '''
        Get general query condition, the value of name is 'name' 'uuid'
        '''
        return name + op + value

    def zsk_query_resource(self, access, resource, condition):
        '''
        execute zstack api via reset full api, if get the resource success ,inventories contained in body
        and the resources results will in inventories.
        '''
        if resource == 'images':
            _url = access + 'images'
        elif resource == 'disk-offerings':
            _url = access + 'disk-offerings'
        elif resource == 'instance-offerings':
            _url = access + 'instance-offerings'
        elif resource == 'l3-networks':
            _url = access + 'l3-networks'
        elif resource == 'vm-instances':
            _url = access + 'vm-instances'
        elif resource == 'volumes':
            _url = access + 'volumes'
        else:
            raise Exception('Cannot find the resource: ' + str(resource))
        params = {
            'q': condition,
        }
        return self.zsk_execute_action_with_session(access, _url, 'get', params)

    def zsk_get_image_bootmode(self, access, image_uuid):
        '''
        get the image boot mode
        '''
        action = 'system-tags'
        action_url = access + action
        params = {
            'q': 'resourceUuid=' + image_uuid,
        }
        return self.zsk_execute_action_with_session(access, action_url, 'get', params)['inventories'][0]['tag']

    def zsk_create_vm(self, access, name, ins_offering_uuid, image_uuid, l3_uuid, disk_offering_uuid):
        '''
        Create vm via restful API
        '''

        try:
            _res = {}
            action = "vm-instances"
            action_url = access + action
            body = {
                "params": {
                    "name": name,
                    "instanceOfferingUuid": ins_offering_uuid,
                    "imageUuid": image_uuid,
                    "l3NetworkUuids": [l3_uuid],
                    "defaultL3NetworkUuid": l3_uuid,
                    "dataDiskOfferingUuids": [disk_offering_uuid],
                    "disk_tag": "virtio::diskOffering::" + disk_offering_uuid + "::num::1",
                    "systemTags": []
                }
            }
            try:
                if self.zsk_get_image_bootmode(access, image_uuid) == 'bootMode::UEFI':
                    body["params"]["systemTags"].append("vmMachineType::q35")
            except:
                pass
            _respon = self.zsk_execute_action_with_session(access, action_url, 'post', body)
            if _respon.get('error'):
                raise Exception('create VM failed, ' + _respon['error']['details'])
        except Exception as e:
            cberr(traceback.print_exc(file=sys.stdout))
        finally:
            return _respon

    def zsk_stop_vm(self, access, vm_uuid):
        action = 'vm-instances/' + vm_uuid + '/actions'
        action_url = access + action
        body = {
            "stopVmInstance": {
                "type": "grace"
            },
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_start_vm(self, access, vm_uuid):
        action = 'vm-instances/' + vm_uuid + '/actions'
        action_url = access + action
        body = {
            "startVmInstance": {},
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_reboot_vm(self, access, vm_uuid):
        action = 'vm-instances/' + vm_uuid + '/actions'
        action_url = access + action
        body = {
            "rebootVmInstance": {},
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_resume_vm(self, access, vm_uuid):
        action = 'vm-instances/' + vm_uuid + '/actions'
        action_url = access + action
        body = {
            "resumeVmInstance": {},
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_pause_vm(self, access, vm_uuid):
        action = 'vm-instances/' + vm_uuid + '/actions'
        action_url = access + action
        body = {
            "pauseVmInstance": {},
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'put', body)

    def zsk_destroy_vm(self, access, vm_uuid):
        action = "vm-instances"
        params = {
            'deleteMode': 'Permissive'
        }
        action_url = access + action + '/' + vm_uuid
        return self.zsk_execute_action_with_session(access, action_url, 'delete', params)

    def zsk_destroy_volume(self, access, vv_uuid):
        action = "volumes"
        params = {
            'deleteMode': 'Permissive'
        }
        action_url = access + action + '/' + vv_uuid
        return self.zsk_execute_action_with_session(access, action_url, 'delete', params)

    def zsk_create_image(self, access, name, root_volume_uuid):
        action = 'images/root-volume-templates/from/volumes/' + root_volume_uuid
        action_url = access + action
        body = {
            "params": {
                "name": name,
                "backupStorageUuids": [
                    "e67b9791a8204b31842c3b36457ce56c"
                ],
                "platform": "Linux",
                "system": "false"
            },
            "systemTags": [],
            "userTags": []
        }
        return self.zsk_execute_action_with_session(access, action_url, 'post', body)

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "ZStack Elastic Compute Cloud"


    @trace
    def connect(self, access, name='', password='', timeout=60000):
        try:
            _status = 100
            self.zsk_login_by_account(access)
            _status = 0
        except Exception, msg:
            _fmsg = str(msg)
            _status = 23
        finally:
            if _status:
                _msg = self.get_description() + " connection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else:
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def disconnect(self):
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            # Nothing to do
            _status = 0
        except AttributeError:
            # If the "close" method does not exist, proceed normally.
            _msg = "The \"close\" method does not exist or is not callable"
            cbwarn(_msg)
            _status = 0

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            if _status:
                _msg = self.get_description() + " disconnection failure: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else:
                _msg = self.get_description() + " disconnection successful."
                cbdebug(_msg)
                return _status, _msg, ''

    @trace
    def vm_placement(self, obj_attr_list):
        '''
        TBD
        '''
        _availability_zone = None
        if len(obj_attr_list["availability_zone"]) > 1:
            _availability_zone = obj_attr_list["availability_zone"]

        if "compute_node" in obj_attr_list and _availability_zone:
            #                _scheduler_hints = { "force_hosts" : obj_attr_list["host_name"] }
            for _host in self.oskconncompute[obj_attr_list["name"]].hypervisors.list():
                if _host.hypervisor_hostname.count(obj_attr_list["compute_node"]):
                    obj_attr_list["host_name"] = _host.hypervisor_hostname
                    break

            if "host_name" in obj_attr_list:
                _availability_zone += ':' + obj_attr_list["host_name"]
            else:
                _msg = "Unable to find the compute_node \"" + obj_attr_list["compute_node"]
                _msg += "\", indicated during the instance creation. Will let"
                _msg += " the scheduler pick a compute node"
                cbwarn(_msg)

        obj_attr_list["availability_zone"] = _availability_zone

        return True

    @trace
    def vvcreate(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            #
            # if "cloud_vv_type" not in obj_attr_list:
            #     obj_attr_list["cloud_vv_type"] = "local"
            #
            # if "cloud_vv" in obj_attr_list:
            #     obj_attr_list["last_known_state"] = "about to send volume create request"
            #
            #     obj_attr_list["cloud_vv_uuid"] = self.generate_random_uuid()
            #
            #     self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)
            #
            #     obj_attr_list["volume_list"] += ",/dev/sdb"

            # no need
            _status = 0

        except CldOpsException, obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace
    def vvdestroy(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "none":
                self.common_messages("VV", obj_attr_list, "destroying", 0, '')

            _instance = self.get_instances(obj_attr_list, "vv", "vvuuid")
            if _instance:
                self.zsk_destroy_volume(obj_attr_list["access"], _instance["uuid"])
            _status = 0

        except CldOpsException, obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            _status, _msg = self.common_messages("VV", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcreate(self, obj_attr_list):
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _instance = False

            self.determine_instance_name(obj_attr_list)
            self.determine_key_name(obj_attr_list)
            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"

            obj_attr_list["userdata"] = self.populate_cloudconfig(obj_attr_list)
            if obj_attr_list["userdata"]:
                obj_attr_list["config_drive"] = True
            else:
                obj_attr_list["config_drive"] = None

            _mark_a = time()
            self.vm_placement(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "vm_placement_time", _mark_a)

            _meta = {}
            if "meta_tags" in obj_attr_list:
                if obj_attr_list["meta_tags"] != "empty" and \
                        obj_attr_list["meta_tags"].count(':') and \
                        obj_attr_list["meta_tags"].count(','):
                    _meta = str2dic(obj_attr_list["meta_tags"])

            _fip = None

            _meta["experiment_id"] = obj_attr_list["experiment_id"]

            if "cloud_floating_ip_uuid" in obj_attr_list:
                _meta["cloud_floating_ip_uuid"] = obj_attr_list["cloud_floating_ip_uuid"]

            _time_mark_prs = int(time())

            obj_attr_list["mgt_002_provisioning_request_sent"] = \
                _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vvcreate(obj_attr_list)

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            self.pre_vmcreate_process(obj_attr_list)

            # zstack create vm
            cond = self.zsk_gen_query_conditions('name', '=', obj_attr_list["size"])
            ins_offering_uuid = \
            self.zsk_query_resource(obj_attr_list["access"], 'instance-offerings', cond)['inventories'][0]['uuid']

            self.get_images(obj_attr_list)
            cond = self.zsk_gen_query_conditions('name', '=', obj_attr_list["imagename"])
            image_uuid = self.zsk_query_resource(obj_attr_list["access"], 'images', cond)['inventories'][0]['uuid']

            cond = self.zsk_gen_query_conditions('name', '=', obj_attr_list["netname"])
            net_uuid = self.zsk_query_resource(obj_attr_list["access"], 'l3-networks', cond)['inventories'][0]['uuid']

            cond = self.zsk_gen_query_conditions('name', '=', obj_attr_list["disk_size"])
            disk_uuid = \
            self.zsk_query_resource(obj_attr_list["access"], 'disk-offerings', cond)['inventories'][0]['uuid']

            _instance = self.zsk_create_vm(access=obj_attr_list['access'],
                                       name=obj_attr_list["cloud_vm_name"],
                                       ins_offering_uuid=ins_offering_uuid,
                                       image_uuid=image_uuid,
                                       l3_uuid=net_uuid,
                                       disk_offering_uuid=disk_uuid)
            if _instance.get('inventory'):
                obj_attr_list["cloud_vm_uuid"] = _instance['inventory']['uuid']
                obj_attr_list["cloud_vv_uuid"] = 'none'
                for volume in _instance["inventory"]["allVolumes"]:
                    if volume["type"] == "Data":
                        obj_attr_list["cloud_vv_uuid"] = volume['uuid']
                        break

                obj_attr_list["instance_obj"] = _instance["inventory"]
                obj_attr_list["arrival"] = int(time())

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)
                _status = 0

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                obj_attr_list["host_name"] = "unknown"

                _status = 0

                if str(obj_attr_list["force_failure"]).lower() == "true":
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                    _status = 916

                self.take_action_if_requested("VM", obj_attr_list, "provision_finished")

        except KeyboardInterrupt:
            _status = 42
            _fmsg = "CTRL-C interrupt"
            cbdebug("VM create keyboard interrupt...", True)

        except Exception, e:
            _status = 23
            _fmsg = str(e)
            cberr(traceback.format_exc())
        finally:
            self.disconnect()
            if "instance_obj" in obj_attr_list :
                del obj_attr_list["instance_obj"]
            if "mgt_003_provisioning_request_completed" in obj_attr_list:
                self.annotate_time_breakdown(obj_attr_list, "instance_active_time",
                                             obj_attr_list["mgt_003_provisioning_request_completed"], False)

            if "mgt_004_network_acessible" in obj_attr_list:
                self.annotate_time_breakdown(obj_attr_list, "instance_reachable_time",
                                             obj_attr_list["mgt_004_network_acessible"], False)

            _status, _msg = self.common_messages("VM", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace
    def vmdestroy(self, obj_attr_list):
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

            _wait = int(obj_attr_list["update_frequency"])
            _max_tries = int(obj_attr_list["update_attempts"])
            _curr_tries = 0

            instance = self.get_instances(obj_attr_list, "vm", "vmuuid")
            if instance:
                self.common_messages("VM", obj_attr_list, "destroying", 0, '')
                self.zsk_destroy_vm(obj_attr_list["access"], instance["uuid"])
                sleep(_wait)
                while self.is_vm_running(obj_attr_list) and _curr_tries < _max_tries :
                    sleep(_wait)
                    _curr_tries += 1
            else:
                True

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs

            _status, _fmsg = self.vvdestroy(obj_attr_list)

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, msg :
            _fmsg = str(msg)
            _status = 23
            cberr(traceback.format_exc())

        finally :
            self.disconnect()
            _status, _msg = self.common_messages("VM", obj_attr_list, "destroyed", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcapture(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])


            _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")

            if _instance:

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list[
                    "mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto":
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                _root_volume = None
                _volumes = _instance["allVolumes"]
                for volume in _volumes:
                    if volume["type"] == "Root":
                        _root_volume = volume
                        break

                _created_image = self.zsk_create_image(obj_attr_list["access"], obj_attr_list["captured_image_name"],
                                                       _root_volume["uuid"])

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries:

                    # _image_instance = self.ec2conn.get_all_images(image_ids=[_captured_imageid])

                    if len(_created_image):
                        _image_instance = _created_image[0]
                        if _image_instance.status.lower() == "ready":
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    sleep(_wait)
                    _curr_tries += 1

                if _curr_tries > _max_tries:
                    _status = 1077
                    _fmsg = "" + obj_attr_list["name"] + ""
                    _fmsg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                    _fmsg += "could not be captured after " + str(_max_tries * _wait) + " seconds.... "
                else:
                    _status = 0

            else:
                _fmsg = "This instance does not exist"
                _status = 1098

        except CldOpsException, obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, msg:
            _fmsg = str(msg)
            _status = 23

        finally:
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
            return _status, _msg


    def vmrunstate(self, obj_attr_list):
            '''
            TBD
            '''
            try:
                _status = 100

                _ts = obj_attr_list["target_state"]
                _cs = obj_attr_list["current_state"]

                if "mgt_201_runstate_request_originated" in obj_attr_list:
                    _time_mark_rrs = int(time())
                    obj_attr_list["mgt_202_runstate_request_sent"] = \
                        _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]

                self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

                _instance = self.get_instances(obj_attr_list, "vm", "vmuuid")

                if _instance:
                    if _ts == "fail":
                        _instance.pause()
                        self.zsk_pause_vm(obj_attr_list['access'], _instance["uuid"])
                    elif _ts == "save":
                        self.zsk_stop_vm(obj_attr_list['access'], _instance["uuid"])
                    elif (_ts == "attached" or _ts == "resume") and _cs == "fail":
                        self.zsk_resume_vm(obj_attr_list['access'], _instance["uuid"])
                    elif (_ts == "attached" or _ts == "restore") and _cs == "save":
                        self.zsk_start_vm(obj_attr_list['access'], _instance["uuid"])

                _time_mark_rrc = int(time())
                obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

                _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
                cbdebug(_msg)

                _status = 0

            except CldOpsException, obj:
                _status = obj.status
                _fmsg = str(obj.msg)

            except Exception, msg:
                _fmsg = str(msg)
                _status = 23

            finally:
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
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name,
                            security_group_name, vm_templates, vm_defaults, vmc_defaults):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            self.connect(access)
            self.zsk_configure_mn(access)
            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)
            _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults)
            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)
            _detected_imageids = self.check_images(vmc_name, vm_templates, vmc_defaults)
            if not (_run_netname_found and _prov_netname_found and _key_pair_found ):
                _msg = "Check the previous errors, fix it (using CBTOOL's web"
                _msg += " GUI or CLI"
                _status = 1178
                raise CldOpsException(_msg, _status)

            if len(_detected_imageids):
                _status = 0
            else:
                _status = 1
        except CldOpsException, obj:
            _fmsg = str(obj.msg)
            _status = 2
        except Exception, msg:
            _fmsg = str(msg)
            _status = 23
        finally:
            cberr(traceback.format_exc())
            self.disconnect()
            _status, _msg = self.common_messages("VMC", {"name": vmc_name}, "connected", _status, _fmsg)
            return _status, _msg

    @trace
    def check_networks(self, vmc_name, vm_defaults):
        '''
        TBD
        '''
        if "prov_netname" not in vm_defaults:
            _prov_netname = vm_defaults["netname"]
        else:
            _prov_netname = "public"

        if "run_netname" not in vm_defaults:
            _run_netname = vm_defaults["netname"]
        else:
            _run_netname = vm_defaults["run_netname"]

        if _run_netname == _prov_netname:
            _net_str = "network \"" + _prov_netname + "\""
        else:
            _net_str = "networks \"" + _prov_netname + "\" and \"" + _run_netname + "\""

        _msg = "Checking if the " + _net_str + " can be found on VMC " + vmc_name + "..."
        cbdebug(_msg, True)

        _prov_netname_found = True
        _run_netname_found = True

        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, vmc_defaults):
        '''
        TBD
        '''
        self.common_messages("IMG", {"name": vmc_name}, "checking", 0, '')

        _map_name_to_id = {}
        _map_uuid_to_name = {}
        _registered_imageid_list = []
        if True:
            for _vm_role in vm_templates.keys():
                _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
                if _imageid != "to_replace":
                    if not self.is_cloud_image_uuid(_imageid):
                        if _imageid in _map_name_to_id:
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])
                        else:
                            _map_name_to_id[_imageid] = self.generate_random_uuid(_imageid)
                            _map_uuid_to_name[_map_name_to_id[_imageid]] = _imageid
                            vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])

                        if _map_name_to_id[_imageid] not in _registered_imageid_list:
                            _registered_imageid_list.append(_map_name_to_id[_imageid])
                    else:
                        if _imageid not in _registered_imageid_list:
                            _registered_imageid_list.append(_imageid)

        _map_name_to_id["baseimg"] = self.generate_random_uuid("baseimg")
        _map_uuid_to_name[self.generate_random_uuid("baseimg")] = "baseimg"

        _detected_imageids = self.base_check_images(vmc_name, vm_templates, _registered_imageid_list, _map_uuid_to_name)

        if "images_uuid2name" not in vmc_defaults:
            vmc_defaults["images_uuid2name"] = dic2str(_map_uuid_to_name)

        if "images_name2uuid" not in vmc_defaults:
            vmc_defaults["images_name2uuid"] = dic2str(_map_name_to_id)

        return _detected_imageids

    @trace
    def discover_hosts(self, obj_attr_list, start):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _status = 0

        except CldOpsException, obj:
            _status = int(obj.status)
            _fmsg = str(obj.msg)

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            _status, _msg = self.common_messages("HOST", obj_attr_list, "discovered", _status, _fmsg)
            return _status, _msg

    @trace
    def vmccleanup(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')

            _msg = "Ok"
            _status = 0

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            _status, _msg = self.common_messages("VMC", obj_attr_list, "cleaned up", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(
                obj_attr_list["mgt_001_provisioning_request_originated"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True":
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else:
                _status = 0

            _x, _y = self.connect(obj_attr_list['access'])

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = self.generate_random_ip_address()
            obj_attr_list["arrival"] = int(time())

            if str(obj_attr_list["discover_hosts"]).lower() == "true":
                self.discover_hosts(obj_attr_list, _time_mark_prs)
            else:
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            _time_mark_prc = int(time())

            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

            _status = 0

        except CldOpsException, obj:
            _fmsg = str(obj.msg)
            _status = 2

        except Exception, msg:
            _fmsg = str(msg)
            _status = 23

        finally:
            self.disconnect()
            _status, _msg = self.common_messages("VMC", obj_attr_list, "registered", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcunregister(self, obj_attr_list):
        '''
          TBD
          '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list:
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(
                obj_attr_list["mgt_901_deprovisioning_request_originated"])

            if "cleanup_on_detach" in obj_attr_list and obj_attr_list["cleanup_on_detach"] == "True":
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            _time_mark_prc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_prc - _time_mark_drs

            _status = 0

        except CldOpsException, obj:
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, msg:
            _fmsg = str(msg)
            _status = 23

        finally:
            _status, _msg = self.common_messages("VMC", obj_attr_list, "unregistered", _status, _fmsg)
            return _status, _msg

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _nr_instances = "NA"
            _fmsg = "An error has occurred, but no error message was captured"
            _nr_instances = self.osci.count_object(obj_attr_list["cloud_name"], "VM", "RESERVATIONS")

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            return _nr_instances

    @trace
    def get_ssh_keys(self, vmc_name, key_name, key_contents, key_fingerprint, registered_key_pairs, internal,
                     connection):
        '''
        TBD
        '''

        registered_key_pairs[key_name] = key_fingerprint + "-NA"

        return True

    @trace
    def get_security_groups(self, vmc_name, security_group_name, registered_security_groups):
        '''
        TBD
        '''

        registered_security_groups.append(security_group_name)

        return True

    @trace
    def get_ip_address(self, obj_attr_list):
        '''
        TBD
        '''
        obj_attr_list["last_known_state"] = "running with ip assigned"
        if obj_attr_list["role"] != "predictablevm":
            obj_attr_list["run_cloud_ip"] = obj_attr_list["instance_obj"]["vmNics"][0]["ip"]
            obj_attr_list["prov_cloud_ip"] = obj_attr_list["instance_obj"]["vmNics"][0]["ip"]
        else:
            obj_attr_list["run_cloud_ip"] = "1.2.3.4"
            obj_attr_list["prov_cloud_ip"] = "1.2.3.4"

        # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
        obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]
        return True

    @trace
    def get_instances(self, obj_attr_list, obj_type="vm", identifier="all"):
        '''
        get vm or vm volume inventory.
        :param obj_attr_list: vm obj attr list.
        :param obj_type: vm for vm , vv for vm volume
        :param identifier:  vmuuid for vm , vvuuid for volume
        :return: json , inventory
        '''
        try:
            _search_opts = {}
            _call = "NA"
            _search_opts['all_tenants'] = 1

            if obj_type == "vm":
                if identifier == "vmname":
                    cond = self.zsk_gen_query_conditions('name', '=', obj_attr_list["cloud_vm_name"])
                    _vm_inv = \
                        self.zsk_query_resource(obj_attr_list["access"], "vm-instances", cond)
                    if _vm_inv["inventories"]:
                        _instance = _vm_inv["inventories"][0]
                        return _instance
                elif identifier == "vmuuid":
                    cond = self.zsk_gen_query_conditions('uuid', '=', obj_attr_list["cloud_vm_uuid"])
                    _vm_inv = \
                        self.zsk_query_resource(obj_attr_list["access"], "vm-instances", cond)
                    if _vm_inv["inventories"]:
                        _instance = _vm_inv["inventories"][0]
                        return _instance
                return False
            elif obj_type == "vv":
                if identifier == "vvuuid":
                    cond = self.zsk_gen_query_conditions('uuid', '=', obj_attr_list["cloud_vv_uuid"])
                    _volume_inv = \
                        self.zsk_query_resource(obj_attr_list["access"], "volumes", cond)
                    if _volume_inv["inventories"]:
                        _volume = _volume_inv["inventories"][0]
                        return _volume
                else:
                    return False
            else:
                return False

        except Exception, msg :
            _fmsg = str(msg)
            cberr(traceback.print_exc(file=sys.stdout))
            _status = 23
            raise CldOpsException(_fmsg, _status)


    @trace
    def get_images(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _hyper = ''
            _fmsg = "An error has occurred, but no error message was captured"
            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"],
                                                  False)
            _map_uuid_to_name = str2dic(_vmc_attr_list["images_uuid2name"])
            _map_name_to_uuid = str2dic(_vmc_attr_list["images_name2uuid"])
            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]):
                obj_attr_list["boot_volume_imageid1"] = obj_attr_list["imageid1"]
                obj_attr_list["imagename"] = _map_uuid_to_name[obj_attr_list["imageid1"]]
                if obj_attr_list["imageid1"] in _map_uuid_to_name:
                    obj_attr_list["imageid1"] = _map_uuid_to_name[obj_attr_list["imageid1"]]
                    _status = 0
                else:
                    _fmsg = "image does not exist"
                    _status = 1817
            else:
                if obj_attr_list["imageid1"] in _map_name_to_uuid:
                    obj_attr_list["boot_volume_imageid1"] = _map_name_to_uuid[obj_attr_list["imageid1"]]
                    _status = 0
                else:
                    _fmsg = "image does not exist"
                    _status = 1817
            if str(obj_attr_list["build"]).lower() == "true":
                obj_attr_list["boot_volume_imageid1"] = self.generate_random_uuid(obj_attr_list["imageid1"])
                _status = 0

        except Exception, e:
            _status = 23
            _fmsg = str(e)
        finally:
            if _status:
                _msg = "Image Name (" + obj_attr_list["imageid1"] + ") not found: " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else:
                return True

    @trace
    def get_networks(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _status = 0

        except Exception, e:
            _status = 23
            _fmsg = str(e)

        finally:
            if _status:
                _msg = "Network (" + obj_attr_list["prov_netname"] + " ) not found: " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else:
                return True

    @trace
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection):
        '''
        TBD
        '''
        return True

    @trace
    def is_cloud_image_uuid(self, imageid):
        '''
        TBD
        '''
        if len(imageid) == 36 and imageid.count('-') == 4:
            return True

        return False

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try:
            _cloud_vm_name = obj_attr_list["cloud_vm_name"]

            cond = self.zsk_gen_query_conditions('uuid', '=', obj_attr_list["cloud_vm_uuid"])
            _vm_ins = \
                self.zsk_query_resource(obj_attr_list["access"], 'vm-instances', cond)
            if _vm_ins["inventories"]:
                if _vm_ins["inventories"][0]["state"] == "Running":
                    return True
                else:
                    return False
            else:
                return False
        except Exception, e:
            _status = 23
            _fmsg = str(traceback.format_exc())
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''
        if self.is_vm_running(obj_attr_list):

            if self.get_ip_address(obj_attr_list):
                obj_attr_list["last_known_state"] = "running with ip assigned"
                return True
            else :
                obj_attr_list["last_known_state"] = "running with ip unassigned"
                return False
        else :
            obj_attr_list["last_known_state"] = "not running"
            return False
