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

    @author: Michael R. Hines, Darrin Eden
'''
from time import time, sleep

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import Nethashget

from shared_functions import CldOpsException, CommonCloudFunctions

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState

import threading

catalogs = threading.local()

class DoCmds(CommonCloudFunctions) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.access_url = False
        self.ft_supported = False
        self.expid = expid
        self.locations = False
        self.sizes = False
        self.images = False
        self.keys = {}
        self.cache_mutex = threading.Lock()
        self.token_mutex = threading.Lock()
        self.current_token = 0

    @trace
    def get_description(self) :
        return "DigitalOcean"

    @trace
    def connect(self, credential_pair) :
        credentials = credential_pair.split(":")
        if len(credentials) != 2 :
            raise CldOpsException("DigitalOcean credentials should be in the form of tag:bearer_token, where tag is arbitrary.", 8499)
        tenant = credentials[0]
        access_token = credentials[1]

        # libcloud is totally not thread-safe. bastards.
        cbdebug("Checking libcloud connection...")
        try :
            getattr(catalogs, "digitalocean")
        except AttributeError, e :
            cbdebug("Initializing thread local connection: ")

            catalogs.digitalocean = {}

        self.cache_mutex.acquire()
        try :
            _status = 100

            if credential_pair not in catalogs.digitalocean :
                cbdebug("Connecting to DigitalOcean...")
                _status = 110
                catalogs.digitalocean[credential_pair] = get_driver(Provider.DIGITAL_OCEAN)(access_token, api_version='v2')
            else :
                cbdebug("DigitalOcean Already connected.")

            cbdebug("Caching DigitalOcean locations, sizes, and images. If stale, then restart...")
            if not self.locations :
                cbdebug("Caching DigitalOcean Locations...", True)
                self.locations = catalogs.digitalocean[credential_pair].list_locations()
            if not self.sizes :
                cbdebug("Caching DigitalOcean Sizes...", True)
                self.sizes = catalogs.digitalocean[credential_pair].list_sizes()

            if credential_pair not in self.keys :
                cbdebug("Caching DigitalOcean keys (" + tenant + ")", True)
                self.keys[credential_pair] = catalogs.digitalocean[credential_pair].list_key_pairs()

            if not self.images :
                cbdebug("Caching DigitalOcean Images (can take a minute or so)...", True)
                self.images = catalogs.digitalocean[credential_pair].list_images()

            assert(credential_pair in self.keys)
            assert(self.images)
            assert(self.sizes)
            assert(self.locations)
            cbdebug("Done caching.")

            _status = 0

        except Exception, e:
            _msg = "Error connecting DigitalOcean: " + str(e)
            cbdebug(_msg, True)
            _status = 23
        finally :
            self.cache_mutex.release()
            if _status :
                _msg = "DigitalOcean connection failure. Failed to use your access token for account: " + tenant
                cbdebug(_msg, True)
                cberr(_msg)
                if credential_pair in catalogs.digitalocean :
                    del catalogs.digitalocean[credential_pair]
                raise CldOpsException(_msg, _status)
            else :
                _msg = "DigitalOcean connection successful."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        try :
            # Attempt to a connection using those login credentials
            for credential_pair in credentials.split(","):
                self.connect(credential_pair)

        except CldOpsException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            _status = 2
            raise CldOpsException(_msg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        try :
            _status = 100

            for credential_pair in obj_attr_list["credentials"].split(","):
                self.connect(credential_pair)

            _msg = "Cleaning up DigitalOcean"
            cbdebug(_msg)

            _running_instances = True
            while _running_instances :
                _running_instances = False
                for credential_pair in obj_attr_list["credentials"].split(","):
                    credentials = credential_pair.split(":")
                    tenant = credentials[0]

                    _reservations = catalogs.digitalocean[credential_pair].list_nodes()
                    for _reservation in _reservations :
                        if _reservation.name.count("cb-" + obj_attr_list["username"]) :
                            if _reservation.state == NodeState.PENDING :
                                cbdebug("Instance still has a pending event. waiting to destroy...")
                                sleep(10)
                                _msg = "Cleaning up DigitalOcean.  Destroying CB instantiated node: " + _reservation.name
                                cbdebug(_msg)
                                continue

                            try :
                                cbdebug("Killing: " + _reservation.name + " (" + tenant + ")", True)
                                _reservation.destroy()
                            except :
                                pass
                            _running_instances = True
                        else :
                            _msg = "Cleaning up DigitalOcean.  Ignoring instance: " + _reservation.name
                            cbdebug(_msg)

                    if _running_instances :
                        sleep(int(obj_attr_list["update_frequency"]))

                _msg = "All running instances on DigitalOcean " + obj_attr_list["name"]
                _msg += " were terminated"
                cbdebug(_msg)

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
        _fmsg = "none"
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

            obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
            obj_attr_list["cloud_ip"] = obj_attr_list["name"] + ".digitalocean.com"

            obj_attr_list["arrival"] = int(time())

            _time_mark_prc = int(time())

            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cberr(str(obj))

        except Exception, e:
            _status = 23
            _fmsg = sys.exc_info()[0]
            cberr(str(e))
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
        try :
            _status = 100
            node = self.get_vm_instance(obj_attr_list)

            if len(node.private_ips) > 0 and obj_attr_list["run_netname"].lower() == "private" :
                obj_attr_list["run_cloud_ip"] = node.private_ips[0]
            else :
                obj_attr_list["run_cloud_ip"] = node.public_ips[0]
            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
            elif obj_attr_list["hostname_key"] == "cloud_ip" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')

            _msg = "Public IP = " + node.public_ips[0]
            _msg += " Private IP = " + obj_attr_list["cloud_ip"]
            cbdebug(_msg)

            if str(obj_attr_list["use_vpn_ip"]).lower() == "true" and str(obj_attr_list["vpn_only"]).lower() == "true" :
                assert(self.get_attr_from_pending(obj_attr_list))

                if "cloud_init_vpn" not in obj_attr_list :
                    cbdebug("Droplet VPN address not yet available.")
                    return False
                cbdebug("Found VPN IP: " + obj_attr_list["cloud_init_vpn"])
                obj_attr_list["prov_cloud_ip"] = obj_attr_list["cloud_init_vpn"]
            else :
                if len(node.private_ips) > 0 and obj_attr_list["prov_netname"].lower() == "private" :
                    obj_attr_list["prov_cloud_ip"] = node.private_ips[0]
                else :
                    obj_attr_list["prov_cloud_ip"] = node.public_ips[0]

            _status = 0
            return True

        except Exception, e :
            _msg = "Could not retrieve IP addresses for object " + obj_attr_list["uuid"]
            _msg += " from DigitalOcean \"" + obj_attr_list["cloud_name"] + ": " + str(e)
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def get_vm_instance(self, obj_attr_list) :
        try :
            _status = 100
            _msg = "cloud_vm_name " + obj_attr_list["cloud_vm_name"]
            _msg += " from DigitalOcean \"" + obj_attr_list["cloud_name"]
            cbdebug(_msg)

            node_list = catalogs.digitalocean[obj_attr_list["credential_pair"]].list_nodes()

            node = False
            if node_list :
                for x in node_list :
                    if x.name == obj_attr_list["cloud_vm_name"] :
                        node = x
                        break
            _status = 0

            return node

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def vmcount(self, obj_attr_list):
        return "NA"

    def is_vm_running(self, obj_attr_list):
        try :
            node = self.get_vm_instance(obj_attr_list)
            return node and node.state == NodeState.RUNNING

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        if self.is_vm_running(obj_attr_list) :

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

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if obj_attr_list["ai"] != "none" :
                credential_pair = self.osci.pending_object_get(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "credential_pair")
            else :
                credential_pair = self.rotate_token(obj_attr_list["cloud_name"])

            obj_attr_list["tenant"] = credential_pair.split(":")[0]
            obj_attr_list["credential"] = credential_pair.split(":")[1]
            obj_attr_list["credential_pair"] = credential_pair

            cbdebug("Connecting to DigitalOcean...")
            self.connect(credential_pair)

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Attempting to create a Droplet "
            _msg += obj_attr_list["imageid1"]
            _msg += " on DigitalOcean, creating a vm named "
            _msg += obj_attr_list["cloud_vm_name"] + " (" + obj_attr_list["tenant"] + ")"
            cbdebug(_msg, True)

            _msg = "Looking for an existing image named "
            _msg += obj_attr_list["imageid1"]
            cbdebug(_msg, True)

            keys = []

            image = False
            tmp_keys = obj_attr_list["key_name"].split(",")
            for dontcare in range(0, 2) :
                for tmp_key in tmp_keys :
                    for key in self.keys[credential_pair] :
                        if tmp_key in [key.name, key.extra["id"]] and key.extra["id"] not in keys :
                            keys.append(key.extra["id"])

                if len(keys) == len(tmp_keys) :
                    break

                cbdebug("Only found " + str(len(keys)) + " keys. Refreshing key list...", True)
                self.keys[credential_pair] = catalogs.digitalocean[credential_pair].list_key_pairs()

            if len(keys) != len(tmp_keys) :
                raise CldOpsException("Not all SSH keys exist. Check your configuration: " + obj_attr_list["key_name"], _status)

            for dontcare in range(0, 2) :
                for x in self.images :
                    if x.name == obj_attr_list["imageid1"] or x.id == obj_attr_list["imageid1"] :
                        image = x
                        break

                if image :
                    break
                cbdebug("Image is missing. Refreshing image list...", True)
                self.images = catalogs.digitalocean[credential_pair].list_images()

            if not image :
                raise CldOpsException("Image doesn't exist at DigitalOcean. Check your configuration: " + obj_attr_list["imageid1"], _status)

            cbdebug("Launching new Droplet with hostname " + obj_attr_list["cloud_vm_name"], True)

            _reservation = catalogs.digitalocean[credential_pair].create_node(
                image = image,
                name = obj_attr_list["cloud_vm_name"],
                size = [x for x in self.sizes if x.id == obj_attr_list["size"]][0],
                location = [x for x in self.locations if x.id == obj_attr_list["vmc_name"]][0],
                ex_user_data = self.populate_cloudconfig(obj_attr_list),
                ex_create_attr={ "ssh_keys": keys, "private_networking" : True }
            )

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])


            obj_attr_list["last_known_state"] = "sent create request"

            cbdebug("Sent command to create node, waiting for creation...", True)

            if _reservation :

                obj_attr_list["last_known_state"] = "vm created"
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _reservation.uuid

                cbdebug("Success. New instance UUID is " + _reservation.uuid, True)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                obj_attr_list["host_name"] = "unknown"

                if "instance_obj" in obj_attr_list :
                    del obj_attr_list["instance_obj"]

                _status = 0

            else :
                obj_attr_list["last_known_state"] = "vm creation failed"
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cbwarn("Error during reservation creation: " + _fmsg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            cbwarn("Error reaching digitalocean: " + _fmsg)

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
                    if _reservation :
                        _reservation.destroy()
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on DigitalOcean \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmdestroy(self, obj_attr_list) :
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())
            _wait = int(obj_attr_list["update_frequency"])

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

            obj_attr_list["mgt_902_deprovisioning_request_sent"] = _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            cbdebug("Last known state: " + str(obj_attr_list["last_known_state"]))

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])
            credential_pair = obj_attr_list["credential_pair"]
            self.connect(credential_pair)

            _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            while True :
                _errmsg = "get_vm_instance"
                cbdebug("Getting instance...")
                _instance = self.get_vm_instance(obj_attr_list)
                if not _instance :
                    cbdebug("Breaking...")
                    break

                if _instance.state == NodeState.PENDING :
                    try :
                        _instance.destroy()
                    except :
                        pass
                    cbdebug("DigitalOcean still has a pending event. Waiting to destroy...", True)
                    sleep(30)
                    continue

                try :
                    result = _instance.destroy()
                except :
                    pass

                _curr_tries += 1
                _msg = "Inside destroy. " + _errmsg
                _msg += " after " + str(_curr_tries) + " attempts. Will retry in " + str(_wait) + " seconds."
                cbdebug(_msg)
                sleep(_wait)
                cbdebug("Next try...")

            obj_attr_list["last_known_state"] = "vm destoyed"
            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")            
            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_drc - _time_mark_drs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cberr("CldOpsException: " + str(obj), True)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
            cberr("Exception: " + str(e), True)

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

            credential_pair = obj_attr_list["credential_pair"]
            self.connect(credential_pair)

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

                _captured_imageid = catalogs.digitalocean[credential_pair].create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = catalogs.digitalocean[credential_pair].get_all_images(_captured_imageid)

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

            credential_pair = obj_attr_list["credential_pair"]
            self.connect(credential_pair)

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
    def rotate_token(self, cloud_name) :
        vmc_defaults = self.osci.get_object(cloud_name, "GLOBAL", False, "vmc_defaults", False)
        credential_pairs = vmc_defaults["credentials"].split(",")
        lock = self.lock(cloud_name, "VMC", "shared_access_token_counter", "credential_pair")

        assert(lock)

        current_token = 0 if "current_token" not in vmc_defaults else int(vmc_defaults["current_token"])
        new_token = current_token

        if len(credential_pairs) > 1 :
            new_token += 1
            if new_token == len(credential_pairs) :
                new_token = 0

        self.osci.update_object_attribute(cloud_name, "GLOBAL", "vmc_defaults", False, "current_token", str(new_token))
        self.unlock(cloud_name, "VMC", "shared_access_token_counter", lock)

        return credential_pairs[current_token]

    @trace
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        lock = False
        try :
            if current_step == "provision_originated" :
                credentials_pair = self.rotate_token(obj_attr_list["cloud_name"])
                tenant = credentials_pair.split(":")[0]
                obj_attr_list["tenant"] = tenant
                obj_attr_list["credentials_pair"] = credentials_pair
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", \
                    obj_attr_list["uuid"], "credential_pair", credentials_pair)

            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, current_step)            

            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if lock :
                self.unlock(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], lock)
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
    def aiundefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        try :
            _fmsg = "An error has occurred, but no error message was captured"
            self.take_action_if_requested("AI", obj_attr_list, current_step)            
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
