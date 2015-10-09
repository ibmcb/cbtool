#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2015 DigitalOcean, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on Oct 31, 2015

    DigitalOcean Object Operations Library

    @author: Darrin Eden
'''
from time import time, sleep

from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import Nethashget

from shared_functions import CldOpsException, CommonCloudFunctions

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState

class DoCmds(CommonCloudFunctions) :
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
        self.digitalocean = None
        self.access_url = False
        self.ft_supported = False
        self.lock = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "DigitalOcean"

    @trace
    def connect(self, access_token) :
        '''
        TBD
        '''
        try :

            _status = 100

            _msg = "Connecting to DigitalOcean host with access token " + access_token
            cbdebug(_msg)

            driver = get_driver(Provider.DIGITAL_OCEAN)
            _status = 110

            self.digitalocean = driver(access_token, api_version='v2')
            _status = 120

            # Attempt to a connection using those login credentials
            print self.digitalocean.list_nodes()

            _status = 0

        except :
            _msg = "Error connecting DigitalOcean.  Status = " + str(_status)
            cbdebug(_msg, True)
            cberr(_msg)

            _status = 23

        finally :
            if _status :
                _msg = "DigitalOcean connection failure. Failed to connect with token " + access_token
                cbdebug(_msg, True)
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "DigitalOcean connection successful."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def test_vmc_connection(self, access_token) :
        '''
        TBD
        '''
        try :
            self.connect(access_token)

        except CldOpsException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            _status = 2
            raise CldOpsException(_msg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100

            if not self.digitalocean :
                _msg = "Cleaning DigitalOcean"
                cbdebug(_msg)
                self.connect(obj_attr_list["access_token"])

            _pre_existing_instances = False

            _msg = "Cleaning up DigitalOcean"
            cbdebug(_msg)
            _reservations = self.digitalocean.list_nodes()

            _running_instances = True
            while _running_instances :
                _msg = "Cleaning up running instances. Checking to see if they were instantiated by CB..."
                cbdebug(_msg)
                _running_instances = False
                for _reservation in _reservations :
                    if _reservation.name.count("cb-" + obj_attr_list["username"]) :
                        _msg = "Cleaning up DigitalOcean.  Destroying CB instantiated node: " + _reservation.name
                        cbdebug(_msg)
                        _reservation.destroy_node(_reservation)
                        _running_instances = True
                    else :
                        _msg = "Cleaning up DigitalOcean.  Ignoring instance: " + _reservation.name
                        cbdebug(_msg)

                sleep(int(obj_attr_list["update_frequency"]))

            _msg = "All running instances on DigitalOcean " + obj_attr_list["name"]
            _msg += " were terminated"
            cbdebug(_msg)

            sleep(int(obj_attr_list["update_frequency"])*5)

            _status = 0

        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "DigitalOcean " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "DigitalOcean " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _msg = "Attempting to attach a new VMC..."
            cbdebug(_msg)

            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _msg = "Cleaning up VMC before attaching it."
                cbdebug(_msg)
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            obj_attr_list["cloud_hostname"] = "257.0.0.0"

            obj_attr_list["cloud_ip"] = "257.0.0.0"

            obj_attr_list["arrival"] = int(time())

            _time_mark_prc = int(time())

            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except :
            _status = 23
            _fmsg = sys.exc_info()[0]
            raise

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on DigitalOcean \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on DigitalOcean \"" + obj_attr_list["cloud_name"]
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

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on DigitalOcean \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on DigitalOcean \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            node = self.get_vm_instance(obj_attr_list)

            obj_attr_list["prov_cloud_ip"] = node.public_ips[0]
            obj_attr_list["run_cloud_ip"] =  node.public_ips[0]
            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            _msg = "Public IP = " + obj_attr_list["cloud_hostname"]
            _msg += " Private IP = " + obj_attr_list["cloud_ip"]
            cbdebug(_msg)
            _status = 0
            return True

        except :
            _msg = "Could not retrieve IP addresses for object " + obj_attr_list["uuid"]
            _msg += "from DigitalOcean \"" + obj_attr_list["cloud_name"]
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def get_vm_instance(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _msg = "cloud_vm_name " + obj_attr_list["cloud_vm_name"]
            _msg += "from DigitalOcean \"" + obj_attr_list["cloud_name"]
            cberr(_msg)

            node_list = [x for x in self.digitalocean.list_nodes() if x.name == obj_attr_list["cloud_vm_name"]]

            _msg = str(node_list)
            cberr(_msg)

            return node_list[0]

        except Exception, e :
            _status = 23
            _fmsg = str(e)
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
            node = self.get_vm_instance(obj_attr_list)
            return node.state == NodeState.RUNNING

        except Exception, e :
            _status = 23
            _fmsg = str(e)
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
            _fmsg = "An error has occurred when creating new Droplet, but no error message was captured"

            obj_attr_list["cloud_vm_uuid"] = "NA"
            _instance = False

            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
            obj_attr_list["cloud_vm_name"] += '-' + "vm" + obj_attr_list["name"].split("_")[1]
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

            if obj_attr_list["ai"] != "none" :
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to DigitalOcean"

            access_token = obj_attr_list["access_token"]

            if not self.digitalocean :
                _msg = "Connecting to VCD with credentials " + access_token
                cbdebug(_msg)

                self.connect(access_token)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Attempting to create a Droplet "
            _msg += obj_attr_list["image"]
            _msg += " on DigitalOcean, creating a vm named "
            _msg += obj_attr_list["cloud_vm_name"]
            cbdebug(_msg, True)

            _msg = "...Looking for an existing image named "
            _msg += obj_attr_list["image"]
            cbdebug(_msg, True)

            size = [x for x in self.digitalocean.list_sizes() if x.id == "1gb"][0]
            image = [x for x in self.digitalocean.list_images() if x.id == obj_attr_list["image"]][0]
            location = [x for x in self.digitalocean.list_locations() if x.id == obj_attr_list["location"]][0]

            vm_computername = "vm" + obj_attr_list["name"].split("_")[1]
            _msg = "...Launching new Droplet with hostname " + vm_computername
            cbdebug(_msg,True)

            _timeout = obj_attr_list["clone_timeout"]
            _msg = "...libcloud clone_timeout is " + _timeout
            cbdebug(_msg)

            _reservation = self.digitalocean.create_node(name=obj_attr_list["cloud_vm_name"],
                                                         image=image,
                                                         size=size,
                                                         location=location)

            obj_attr_list["last_known_state"] = "sent create request to DigitalOcean, parsing response"

            _msg = "...Sent command to create node, waiting for creation..."
            cbdebug(_msg)

            if _reservation :

                obj_attr_list["last_known_state"] = "vm created"
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _reservation.uuid

                _msg = "...Success. New instance UUID is " + _reservation.uuid
                cbdebug(_msg,True)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                obj_attr_list["host_name"] = "unknown"

                if "instance_obj" in obj_attr_list :
                    del obj_attr_list["instance_obj"]

                _status = 0

            else :
                obj_attr_list["last_known_state"] = "vm creation failed"
                _fmsg = "...Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if "instance_obj" in obj_attr_list :
                del obj_attr_list["instance_obj"]

            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be created "
                _msg += "on DigitalOcean \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)

                if "cloud_vm_uuid" in obj_attr_list :
                    obj_attr_list["mgt_deprovisioning_request_originated"] = int(time())
                    self.vmdestroy(obj_attr_list)
                else :
                    if _instance :
                        _instance.destroy()
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on DigitalOcean \"" + obj_attr_list["cloud_name"]
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

            _time_mark_drs = int(time())
            _wait = int(obj_attr_list["update_frequency"])

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            if ( obj_attr_list["last_known_state"] == "running with ip assigned" or \
                 obj_attr_list["last_known_state"] == "running with ip unassigned" or \
                 obj_attr_list["last_known_state"] == "vm created" ) :

                _msg = "Droplet " + obj_attr_list["name"] + " was in created or running state. Will attempt to terminate."
                cbdebug(_msg)

                credential_name = obj_attr_list["credentials"]

                _wait = int(obj_attr_list["update_frequency"])
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])

                while _curr_tries < _max_tries :
                    try :
                        _errmsg = "self.digitalocean"
                        _errmsg = "self.connect"
                        self.connect(credential_name, obj_attr_list["access"], \
                                     obj_attr_list["password"], obj_attr_list["version"])

                        _errmsg = "get_vm_instance"
                        _instance = self.get_vm_instance(obj_attr_list)

                        break
                    except :
                        _curr_tries += 1
                        _msg = "Inside destroy. " + _errmsg + " failed"
                        _msg += " after " + str(_curr_tries) + " attempts. Will retry in " + str(_wait) + " seconds."
                        cbdebug(_msg, True)
                        sleep(_wait)

                if _instance :

                    _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                    _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                    _msg += "...."
                    cbdebug(_msg, True)

                    #_instance.destroy()
                    #sleep(_wait)

                    # Code to check if vm running isn't working yet, so won't wait for VM to be marked as not running
                    #while self.is_vm_running(obj_attr_list) :
                    #    sleep(_wait)

                    # Multiple simultaneous API calls to destroy a VM on my VCD often fail, so adding retries
                    _destroy_curr_tries = 0
                    while _destroy_curr_tries < _max_tries :

                        try :
                            # Force re-connect, in case timeout occured
                            self.connect(credential_name, obj_attr_list["access"], \
                                         obj_attr_list["password"], obj_attr_list["version"])
                            _status = _instance.destroy()
                            obj_attr_list["last_known_state"] = "vm destoyed"
                            sleep(_wait)
                            break

                        except :
                            _destroy_curr_tries = _destroy_curr_tries + 1

                            if _destroy_curr_tries >= _destroy_max_tries :
                                _msg = "Aborting VM destroy call for "  + obj_attr_list["name"]
                                _msg += " after " + str(_destroy_curr_tries) + " attempts."
                                _status = 1
                                #                                cberr(_msg)
                                #                                raise self.ObjectOperationException(_msg, _status)
                            else :
                                _msg = "VM destroy call to DigitalOcean has failed for "  + obj_attr_list["name"]
                                _msg += " Will try again."
                                cbdebug(_msg, True)
                                sleep(_wait)

                else :
                    True
            else :
                # instance never really existed
                obj_attr_list["last_known_state"] = "vm destoyed"
                _msg = "Droplet " + obj_attr_list["name"] + " had not been successfully created; no need to issue destory command."
                cbdebug(_msg)


            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_drc - _time_mark_drs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on DigitalOcean cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                # cberr(_msg)
                # raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on DigitalOcean cloud \"" + obj_attr_list["cloud_name"]
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

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            credential_name = obj_attr_list["credentials"]
            if not self.digitalocean :
                self.connect(credential_name, obj_attr_list["access"], \
                             obj_attr_list["password"], obj_attr_list["version"])

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                obj_attr_list["captured_image_name"] = obj_attr_list["image"] + "_captured_at_"
                obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent. "
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."
                cbdebug(_msg)

                _captured_imageid = self.digitalocean.create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = self.digitalocean.get_all_images(_captured_imageid)

                    if len(_image_instance)  :
                        if _image_instance[0].state == "pending" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

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

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be captured "
                _msg += " on DigitalOcean cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on DigitalOcean cloud \"" + obj_attr_list["cloud_name"]
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

            credential_name = obj_attr_list["credentials"]
            if not self.digitalocean :
                self.connect(credential_name, obj_attr_list["access"], \
                             obj_attr_list["password"], obj_attr_list["version"])

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]

            _msg = "Sending a runstate change request (" + _ts + " for " + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                if _ts == "fail" :
                    _instance.stop()
                elif _ts == "save" :
                    _instance.stop()
                elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                    _instance.start()
                elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                    _instance.start()

            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except AWSException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on Elastic Compute Cloud \""
                _msg += obj_attr_list["cloud_name"] + "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on Elastic Compute Cloud \""
                _msg += obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def aidefine(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, "all_vms_booted")

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on DigitalOcean \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on DigitalOcean \"" + obj_attr_list["cloud_name"]
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
                _msg += " on DigitalOcean \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on DigitalOcean \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
