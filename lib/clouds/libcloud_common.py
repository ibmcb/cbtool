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
    Created on September 8th, 2016

    Libcloud Common Library: You want to inherit from this to make it easier to
    be compatible with CloudBench

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

from copy import deepcopy

import threading
import traceback

import libcloud.security

class LibcloudCmds(CommonCloudFunctions) :
    catalogs = threading.local()
    locations = False
    sizes = False
    images = False
    keys = {}

    '''
     README: Parameters:

     @description: (Required) This is the libcloud-specific identifier string for your cloud,
        as listed here under the "Provider Constant" column:
        http://libcloud.readthedocs.io/en/latest/supported_providers.html

     @num_credentials: (Required, Default 2)
             How many credentials does your cloud need to authenticate?

             For example, this might be '2' if you have both an access_token and access_key.
             For example, this might be '1' if you only have an access_token or bearer_token without a key.

             This class doesn't actually interpret your parameters, but it does use the string to interpret
             whether or not your configuration file has been setup correctly.

             Libcloud credentials must be in this format, and include a "tag" which is an arbitrary string
             that corresponds to the name of the tenant that owns the credentials.

             You can have as many credentials (tenants) as you want, but they need to be in the right format.

             Example 1)
                1. Cloud is named "FOO"
                2. There are two tenants "user1" and "user2"
                3. Each tenant only has one (1) credential for authentication: "bar" and "baz".
                4. The configuration file would look like this:

                 [USER-DEFINED : CLOUDOPTION_FOO ]
                 FOO_CREDENTIALS = user1:bar,user2:baz

             Example 2)
                1. Cloud is named "HAPPY"
                2. There are three tenants named "not", "so", and "lucky"
                3. Each tenant has the same access_key and access_token, two (2) credentials each as "foo" and "bar"
                4. The configuration file would look like this:

                 [USER-DEFINED : CLOUDOPTION_HAPPY ]
                 HAPPY_CREDENTIALS = not:foo:bar,so:foo:bar,lucky:foo:bar

            In Example 1), @num_credentials = 1
            In Example 2), @num_credentials = 2

            By, default we assume Oauth-driven clouds that have both an access token and an access key.

            If you have more or less than that, please set the value accordingly.

     @use_ssh_keys: (Optional for cloud-init-based clouds, Default false)
            A comma/colon-separated list of ssh key identifiers that can be looked up by libcloud and installed by cloud-init.

            For example:
                1. Cloud is named "FOO"
                2. two SSH keys, identified by "a" and "b"
                3. The configuration file would look like this:

                 [USER-DEFINED : CLOUDOPTION_FOO ]
                 FOO_KEY_NAME = a,b # identifiers used by cloud-init to install the public key
                 FOO_SSH_KEY_NAME = path/to/private/key/for/cbtool

            Using libcloud, we will then go and lookup those keys and use them at instance creation time.

            NOTE: FOO_SSH_KEY_NAME != FOO_SSH_KEY_NAME. The first one is the private key used by cbtool,
                  and the second one is the public key.

            NOTE: If your cloud doesn't support cloud-init, then you will need to make sure the VM image is prepared in advance
                  with the public key that corresponds to FOO_SSH_KEY_NAME

    @use_cloud_init: (Optional, Default False)
            NOTE: If your cloud doesn't support cloud-init, you will need to make sure your images have baked in the SSH public key on your own.

    @use_volumes: (Optional, Default False)

            Leave this as false if you're not interested in block storage / volume support, or you're cloud doesn't support it.

    @use_sizes: (Optional, Default True)
            Use the VM image sizes as listed by your cloud.

    @use_locations: (Optional, Default True)
            Use the Regions as listed by your cloud.

    @verify_ssl: (Optional, Default True)
            Whether or not to have libcloud verify SSL certificates when communicating with the cloud

    @tldomain: (Optional, Default False)
            The FQDN of your cloud. None if false.

    @extra: (Optional, Default empty)
            Extra fixed parameters to be used by libcloud that we don't know about, which get passed at instance creation time.

    '''

    @trace
    def __init__ (self, pid, osci, expid = None, description = "OverrideMe", num_credentials = 2, use_ssh_keys = False, use_cloud_init = False, use_volumes = False, use_locations = True, use_sizes = True, tldomain = False, verify_ssl = True, extra = {}) :
        CommonCloudFunctions.__init__(self, pid, osci, expid)
        self.access_url = False
        self.ft_supported = False
        self.current_token = 0
        self.cache_mutex = threading.Lock()
        self.token_mutex = threading.Lock()
        self.description = description
        self.num_credentials = num_credentials
        self.use_ssh_keys = use_ssh_keys
        self.use_cloud_init = use_cloud_init
        self.use_volumes = use_volumes
        self.use_locations = use_locations
        self.use_sizes = use_sizes
        self.tldomain = tldomain
        self.extra = extra
        self.extra["kwargs"] = {}

        libcloud.security.VERIFY_SSL_CERT = verify_ssl 

    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, *credentials) :
            raise CldOpsException("You must override this function, please.", 4920)

    '''
        You can override this function to modify the 'extra' parameter attributes as you see fit
        during instance creation time.

        If parameters are added that are common to all libcloud adapters, please submit a pull
        request and update this file directly.
    '''
    @trace
    def pre_vmcreate(self, obj_attr_list, extra) :
        return extra

    @trace
    def get_description(self) :
        return self.description

    @trace
    def get_real_driver(self, who) :
        return get_driver(getattr(Provider, who))

    @trace
    def get_my_driver(self, obj_attr_list) :
        return LibcloudCmds.catalogs.cbtool[obj_attr_list["credentials_list"]]

    @trace
    def repopulate_images(self, obj_attr_list) :
        LibcloudCmds.images = self.get_libcloud_driver(obj_attr_list).list_images()

    @trace
    def repopulate_keys(self, obj_attr_list) :
        LibcloudCmds.keys[obj_attr_list["credentials_list"]] = self.get_libcloud_driver(obj_attr_list).list_key_pairs()

    def get_images(self) :
        return LibcloudCmds.images

    @trace
    def connect(self, credentials_list) :
        credentials = credentials_list.split(":")
        if len(credentials) != (self.num_credentials + 1) :
            raise CldOpsException(self.description + " needs at least " + str(self.num_credentials) + " credentials, including an arbitrary tag representing the tenant. Refer to the templates for examples.", 8499)

        tenant = credentials[0]

        # libcloud is totally not thread-safe. bastards.
        cbdebug("Checking libcloud connection...")
        try :
            getattr(LibcloudCmds.catalogs, self.description)
        except AttributeError, e :
            cbdebug("Initializing thread local connection: ")

            LibcloudCmds.catalogs.cbtool = {}

        self.cache_mutex.acquire()
        try :
            _status = 100

            if credentials_list not in LibcloudCmds.catalogs.cbtool :
                cbdebug("Connecting to " + self.description + "...")
                _status = 110
                driver = self.get_real_driver(self.description)
                LibcloudCmds.catalogs.cbtool[credentials_list] = self.get_libcloud_driver(driver, tenant, *credentials[1:])
            else :
                cbdebug(self.description + " Already connected.")

            cbdebug("Caching " + self.description + " locations, sizes, and images. If stale, then restart...")

            if self.use_locations :
                if not LibcloudCmds.locations :
                    cbdebug("Caching " + self.description + " Locations...", True)
                    LibcloudCmds.locations = LibcloudCmds.catalogs.cbtool[credentials_list].list_locations()
                assert(LibcloudCmds.locations)

            if self.use_sizes :
                if not LibcloudCmds.sizes :
                    cbdebug("Caching " + self.description + " Sizes...", True)
                    LibcloudCmds.sizes = LibcloudCmds.catalogs.cbtool[credentials_list].list_sizes()
                assert(LibcloudCmds.sizes)

            if not LibcloudCmds.images :
                cbdebug("Caching " + self.description + " Images (can take a minute or so)...", True)
                LibcloudCmds.images = LibcloudCmds.catalogs.cbtool[credentials_list].list_images()

            assert(LibcloudCmds.images)

            if self.use_ssh_keys :
                if credentials_list not in LibcloudCmds.keys :
                    cbdebug("Caching " + self.description + " keys (" + tenant + ")", True)
                    LibcloudCmds.keys[credentials_list] = LibcloudCmds.catalogs.cbtool[credentials_list].list_key_pairs()
                assert(credentials_list in LibcloudCmds.keys)

            cbdebug("Done caching.")

            _status = 0

        except Exception, e:
            _msg = "Error connecting " + self.description + ": " + str(e)
            cbdebug(_msg, True)
            _status = 23
        finally :
            self.cache_mutex.release()
            if _status :
                _msg = self.description + " connection failure. Failed to use your credentials for account: " + tenant
                cbdebug(_msg, True)
                cberr(_msg)
                if credentials_list in LibcloudCmds.catalogs.cbtool :
                    del LibcloudCmds.catalogs.cbtool[credentials_list]
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.description + " connection successful."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults) :
        try :
            self.access = access
            self.security_group_name = security_group_name
            self.vm_templates = vm_templates
            self.vm_defaults = vm_defaults

            for credentials_list in credentials.split(","):
                self.connect(credentials_list)

        except CldOpsException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            _status = 2
            raise CldOpsException(_msg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        try :
            _status = 100

            for credentials_list in obj_attr_list["credentials"].split(","):
                self.connect(credentials_list)

            _msg = "Cleaning up " + self.description
            cbdebug(_msg)

            _running_instances = True
            while _running_instances :
                _running_instances = False
                for credentials_list in obj_attr_list["credentials"].split(","):
                    credentials = credentials_list.split(":")
                    tenant = credentials[0]

                    _reservations = LibcloudCmds.catalogs.cbtool[credentials_list].list_nodes()
                    for _reservation in _reservations :
                        if _reservation.name.count("cb-" + obj_attr_list["username"]) :
                            if _reservation.state == NodeState.PENDING :
                                cbdebug("Instance still has a pending event. waiting to destroy...")
                                sleep(10)
                                _msg = "Cleaning up " + self.description + ".  Destroying CB instantiated node: " + _reservation.name
                                cbdebug(_msg)
                                continue

                            try :
                                cbdebug("Killing: " + _reservation.name + " (" + tenant + ")", True)
                                _reservation.destroy()
                            except :
                                pass
                            _running_instances = True
                        else :
                            _msg = "Cleaning up " + self.description + ".  Ignoring instance: " + _reservation.name
                            cbdebug(_msg)

                    if _running_instances :
                        sleep(int(obj_attr_list["update_frequency"]))

                _msg = "All running instances on " + self.description + " " + obj_attr_list["name"]
                _msg += " were terminated"
                cbdebug(_msg)

            if self.use_volumes :
                _running_volumes = True
                while _running_volumes :
                    _running_volumes = False
                    for credentials_lists in obj_attr_list["credentials"].split(","):
                        credentials = credentials_list.split(":")
                        tenant = credentials[0]

                        _volumes = LibcloudCmds.catalogs.cbtool[credentials_list].list_volumes()
                        for _volume in _volumes :
                            if _volume.name.count("cb-" + obj_attr_list["username"]) :
                                try :
                                    cbdebug("Destroying: " + _volume.name + " (" + tenant + ")", True)
                                    _volume.destroy()
                                except :
                                    pass
                                _running_volumes = True
                            else :
                                _msg = "Cleaning up " + self.description + ". Ignoring volume: " + _volume.name
                                cbdebug(_msg)

                        if _running_volumes :
                            sleep(int(obj_attr_list["update_frequency"]))

                    _msg = "All volumes on " + self.description + " " + obj_attr_list["name"]
                    _msg += " were destroyed"
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
                _msg = self.description + " " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.description + " " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        _status = 100
        cbdebug("Attempting to attach a new VMC...")
        _fmsg = "An error has occurred, but no error message was captured"

        try :
            for credentials_list in obj_attr_list["credentials"].split(","):
                self.connect(credentials_list)

            location_found = False
            for location in LibcloudCmds.locations :
                if obj_attr_list["name"] == location.id :
                    location_found = location
                    break
            if not location_found :
                if len(obj_attr_list["name"]) <= 4 :
                    raise CldOpsException("No such region: " + obj_attr_list["name"], _status)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _msg = "Cleaning up VMC before attaching it."
                cbdebug(_msg)
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            if self.tldomain :
                obj_attr_list["cloud_hostname"] = obj_attr_list["name"]
                obj_attr_list["cloud_ip"] = obj_attr_list["name"] + ("." + self.tldomain)
            else :
                obj_attr_list["cloud_hostname"] = obj_attr_list["access"]
                obj_attr_list["cloud_ip"] = obj_attr_list["access"] 

            obj_attr_list["arrival"] = int(time())
            _time_mark_prc = int(time())
            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs
            _status = 0

        except CldOpsException, obj :
            cberr(str(obj))
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e:
            cberr(str(e))
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on " + self.description + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on " + self.description + " \"" + obj_attr_list["cloud_name"]
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
                _msg += "on " + self.description + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on " + self.description + " \"" + obj_attr_list["cloud_name"]
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
                if len(node.public_ips) > 0 :
                    obj_attr_list["run_cloud_ip"] = node.public_ips[0]
                else :
                    cbdebug("Instance Public address not yet available.")
                    return False

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
            elif obj_attr_list["hostname_key"] == "cloud_ip" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')

            _msg = "Public IP = " + str(node.public_ips)
            _msg += " Private IP = " + str(node.private_ips)
            cbdebug(_msg)

            if str(obj_attr_list["use_vpn_ip"]).lower() == "true" and str(obj_attr_list["vpn_only"]).lower() == "true" :
                assert(self.get_attr_from_pending(obj_attr_list))

                if "cloud_init_vpn" not in obj_attr_list :
                    cbdebug("Instance VPN address not yet available.")
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
            _msg += " from " + self.description + " \"" + obj_attr_list["cloud_name"] + ": " + str(e)
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def get_vm_instance(self, obj_attr_list) :
        try :
            _status = 100
            _msg = "cloud_vm_name " + obj_attr_list["cloud_vm_name"]
            _msg += " from " + self.description + " \"" + obj_attr_list["cloud_name"]
            cbdebug(_msg)

            node_list = LibcloudCmds.catalogs.cbtool[obj_attr_list["credentials_list"]].list_nodes()

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
        _status = 100
        _fmsg = "An error has occurred when creating new instance, but no error message was captured"
        obj_attr_list["cloud_vm_uuid"] = "NA"
        _instance = False
        volume = False

        # This is just to pass regression tests.
        test_map = dict(platinum64 = "64gb", rhodium64 = "48gb", gold64 = "32gb", silver64 = "16gb", bronze64 = "8gb", copper64 = "4gb", gold32 = "4gb", silver32 = "4gb", iron64 = "2gb", iron32 = "2gb", bronze32 = "2gb", copper32 = "2gb", micro32 = "1gb", nano32 = "1gb", pico32 = "512mb")

        requested_size = obj_attr_list["size"]

        if requested_size in test_map :
            requested_size = test_map[requested_size]

        _status = 100
        _fmsg = "An error has occurred when creating new instance, but no error message was captured"
        obj_attr_list["cloud_vm_uuid"] = "NA"
        _instance = False
        volume = False
        extra = deepcopy(self.extra)
        obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"]
        obj_attr_list["cloud_vm_name"] += '-' + "vm" + obj_attr_list["name"].split("_")[1]
        obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]

        try :

            obj_attr_list["host_name"] = obj_attr_list["vmc_name"]

            if obj_attr_list["ai"] != "none" :
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"]

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to " + self.description

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if obj_attr_list["ai"] != "none" :
                credentials_list = self.osci.pending_object_get(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "credentials_list")
            else :
                credentials_list = self.rotate_token(obj_attr_list["cloud_name"])

            obj_attr_list["tenant"] = credentials_list.split(":")[0]
            obj_attr_list["credential"] = ":".join(credentials_list.split(":")[1:])
            obj_attr_list["credentials_list"] = credentials_list

            cbdebug("Connecting to " + self.description + "...")
            self.connect(credentials_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Attempting to create a instance with image "
            _msg += obj_attr_list["imageid1"]
            _msg += " on " + self.description + ", named "
            _msg += obj_attr_list["cloud_vm_name"] + " (" + obj_attr_list["tenant"] + ")"
            cbdebug(_msg, True)

            if self.use_ssh_keys :
                keys = []
                tmp_keys = obj_attr_list["key_name"].split(",")
                for attempt in range(0, 2) :
                    for tmp_key in tmp_keys :
                        for key in LibcloudCmds.keys[credentials_list] :
                            if tmp_key in [key.name, key.extra["id"]] and key.extra["id"] not in keys :
                                keys.append(key.extra["id"])

                    if len(keys) == len(tmp_keys) :
                        break

                    cbdebug("Only found " + str(len(keys)) + " keys. Refreshing key list...", True)
                    LibcloudCmds.keys[credentials_list] = LibcloudCmds.catalogs.cbtool[credentials_list].list_key_pairs()

                extra["ssh_keys"] = keys

            obj_attr_list["image"] = False

            for attempt in range(0, 2) :
                for x in LibcloudCmds.images :
                    if x.name == obj_attr_list["imageid1"] or x.id == obj_attr_list["imageid1"] :
                        obj_attr_list["image"] = x
                        break

                if obj_attr_list["image"] :
                    break
                cbdebug("Image is missing. Refreshing image list...", True)
                LibcloudCmds.images = LibcloudCmds.catalogs.cbtool[credentials_list].list_images()

            # Currently, regions and VMCs are the same in libcloud based adapters
            obj_attr_list["region"] = region = obj_attr_list["vmc_name"]
            extra.update(self.pre_vmcreate(obj_attr_list, extra))

            if not obj_attr_list["image"] :
                raise CldOpsException("Image doesn't exist at " + self.description + ". Check your configuration: " + obj_attr_list["imageid1"], _status)

            if self.use_ssh_keys :
                if len(keys) != len(tmp_keys) :
                    raise CldOpsException("Not all SSH keys exist. Check your configuration: " + obj_attr_list["key_name"], _status)

            cbdebug("Launching new instance with hostname " + obj_attr_list["cloud_vm_name"] + " " + str(extra) + " vmc " + obj_attr_list["vmc_name"], True)

            if self.use_locations :
                 location = [x for x in LibcloudCmds.locations if x.id == obj_attr_list["region"]][0]
            else :
                 location = False 

            if self.use_sizes :
                size = [x for x in LibcloudCmds.sizes if x.id == requested_size][0]
            else :
                size = False

            kwargs = deepcopy(extra["kwargs"])
            del extra["kwargs"]

            _reservation = LibcloudCmds.catalogs.cbtool[credentials_list].create_node(
                image = obj_attr_list["image"],
                name = obj_attr_list["cloud_vm_name"],
                size = size, 
                location = location,
                ex_user_data = self.populate_cloudconfig(obj_attr_list) if self.use_cloud_init else False,
                ex_create_attr = extra,
                **kwargs
            )

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])


            obj_attr_list["last_known_state"] = "sent create request"

            if _reservation :

                obj_attr_list["last_known_state"] = "vm created"
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _reservation.uuid

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                obj_attr_list["host_name"] = "unknown"

                _status = 0
            else :
                obj_attr_list["last_known_state"] = "vm creation failed"
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100


            if self.use_volumes and "cloud_vv" in obj_attr_list :
                _status = 101

                obj_attr_list["last_known_state"] = "about to send volume create request"

                obj_attr_list["cloud_vv_name"] = "cb-" + obj_attr_list["username"]
                obj_attr_list["cloud_vv_name"] += '-' + "vv"
                obj_attr_list["cloud_vv_name"] += obj_attr_list["name"].split("_")[1]
                obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["role"]
                if obj_attr_list["ai"] != "none" :
                    obj_attr_list["cloud_vv_name"] += '-' + obj_attr_list["ai_name"]

                obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].replace("_", "-")

                _msg = "Creating a volume, with size "
                _msg += obj_attr_list["cloud_vv"] + " GB, on VMC \""
                _msg += obj_attr_list["vmc_name"] + "\" with name " + obj_attr_list["cloud_vv_name"] + "..."
                cbdebug(_msg, True)

                _mark1 = int(time())

                volume = LibcloudCmds.catalogs.cbtool[credentials_list].create_volume(int(obj_attr_list["cloud_vv"]),
                                                                              obj_attr_list["cloud_vv_name"],
                                                                              location = [x for x in LibcloudCmds.locations if x.id == obj_attr_list["vmc_name"]][0])

                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vv_uuid"] = volume.id

                _mark2 = int(time())
                obj_attr_list["libcloud_015_create_volume_time"] = _mark2 - _mark1

                if volume :
                    _mark3 = int(time())
                    _msg = "Attaching the newly created Volume \""
                    _msg += obj_attr_list["cloud_vv_name"] + "\" (cloud-assigned uuid \""
                    _msg += obj_attr_list["cloud_vv_uuid"] + "\") to instance \""
                    _msg += obj_attr_list["cloud_vm_name"] + "\" (cloud-assigned uuid \""
                    _msg += obj_attr_list["cloud_vm_uuid"] + "\")"
                    cbdebug(_msg)

                    if not volume.attach(_reservation) :
                        msg = "Volume attach failed. Aborting instance creation..."
                        cbdebug(msg, True)
                        volume.destroy()
                        raise CldOpsException(msg, _status)

                    cbdebug("Volume attach success.", True)
                    _mark4 = int(time())
                    obj_attr_list["libcloud_015_create_volume_time"] += (_mark4 - _mark3)
                    _status = 0
                else :
                    msg = "Volume creation failed. Aborting instance creation..."
                    cbdebug(msg, True)
                    raise CldOpsException(msg, _status)
            else :
                obj_attr_list["cloud_vv_uuid"] = "none"

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cbwarn("Error during reservation creation: " + _fmsg)

        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            _status = 23
            _fmsg = str(e)
            cbwarn("Error reaching cbtool: " + _fmsg)
            for line in traceback.format_exc().splitlines() :
                cberr(line, True)

        finally :
            if "image" in obj_attr_list :
                del obj_attr_list["image"]
            
            if _status :
                _msg = "Instance " + obj_attr_list["uuid"] + " could not be created "
                _msg += "on " + self.description + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The instance creation will be rolled back)"
                cberr(_msg)

                if "cloud_vm_uuid" in obj_attr_list :
                    obj_attr_list["mgt_901_deprovisioning_request_originated"] = int(time())
                    self.vmdestroy(obj_attr_list)
                else :
                    if _reservation :
                        _reservation.destroy()

                raise CldOpsException(_msg, _status)
            else :
                _msg = "Instance " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on " + self.description + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmdestroy(self, obj_attr_list) :
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        _wait = int(obj_attr_list["update_frequency"])
        cbdebug("Last known state: " + str(obj_attr_list["last_known_state"]))
        _curr_tries = 0
        _max_tries = int(obj_attr_list["update_attempts"])
        credentials_list = obj_attr_list["credentials_list"]

        try :
            self.connect(credentials_list)

            _msg = "Sending a termination request for "  + obj_attr_list["name"]
            _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
            _msg += "...."
            cbdebug(_msg, True)

            firsttime = True
            _time_mark_drs = int(time())
            while True :
                _errmsg = "get_vm_instance"
                cbdebug("Getting instance...")
                _instance = self.get_vm_instance(obj_attr_list)
                if not _instance :
                    cbdebug("Breaking...")
                    if firsttime :
                        if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                            obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                    break

                if _instance.state == NodeState.PENDING :
                    try :
                        _instance.destroy()
                    except :
                        pass
                    cbdebug(self.description + " still has a pending event. Waiting to destroy...", True)
                    sleep(_wait)
                    continue

                try :
                    if firsttime :
                        if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                            obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

                    result = _instance.destroy()

                    if firsttime :
                        obj_attr_list["mgt_902_deprovisioning_request_sent"] = int(time()) - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

                    firsttime = False
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

            if "cloud_vv_name" in obj_attr_list :
                tenant = credentials_list.split(":")[0]
                cbdebug("Checking for volumes from tenant: " + tenant)
                _volumes = LibcloudCmds.catalogs.cbtool[credentials_list].list_volumes()
                for _volume in _volumes :
                    if _volume.name == obj_attr_list["cloud_vv_name"] :
                        try :
                            cbdebug("Destroying: " + _volume.name + " (" + tenant + ")", True)
                            _volume.destroy()
                            break
                        except :
                            pass
                    else :
                        cbdebug("Ignoring volume: " + _volume.name)

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)
            cberr("CldOpsException: " + str(obj), True)

        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            _status = 23
            _fmsg = str(e)
            cberr("Exception: " + str(e), True)

        finally :
            if _status :
                _msg = "Instance " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on " + self.description + " cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "Instance " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on " + self.description + " cloud \"" + obj_attr_list["cloud_name"]
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

            credentials_list = obj_attr_list["credentials_list"]
            self.connect(credentials_list)

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

                _captured_imageid = LibcloudCmds.catalogs.cbtool[credentials_list].create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = LibcloudCmds.catalogs.cbtool[credentials_list].get_all_images(_captured_imageid)

                    if len(_image_instance)  :
                        if _image_instance[0].state == "pending" :
                            _vm_image_created = True
                            _time_mark_crc = int(time())
                            obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                            break

                    _msg = "" + obj_attr_list["name"]
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
                _fmsg = "" + obj_attr_list["name"]
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
                _msg = "Instance " + obj_attr_list["uuid"] + " could not be captured "
                _msg += " on " + self.description + " cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "Instance " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on " + self.description + " cloud \"" + obj_attr_list["cloud_name"]
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

            credentials_list = obj_attr_list["credentials_list"]
            self.connect(credentials_list)

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

            _msg = "Instance " + obj_attr_list["name"] + " runstate request completed."
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
                _msg = "Instance " + obj_attr_list["uuid"] + " could not have its "
                _msg += "run state changed on " + self.description + " \""
                _msg += obj_attr_list["cloud_name"] + "\" : " + _fmsg
                cberr(_msg, True)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "Instance " + obj_attr_list["uuid"] + " successfully had its "
                _msg += "run state changed on " + self.description + " \""
                _msg += obj_attr_list["cloud_name"] + "\"."
                cbdebug(_msg, True)
                return _status, _msg

    @trace
    def rotate_token(self, cloud_name) :
        vmc_defaults = self.osci.get_object(cloud_name, "GLOBAL", False, "vmc_defaults", False)
        credentials_lists = vmc_defaults["credentials"].split(",")
        lock = self.lock(cloud_name, "VMC", "shared_access_token_counter", "credentials_list")

        assert(lock)

        current_token = 0 if "current_token" not in vmc_defaults else int(vmc_defaults["current_token"])
        new_token = current_token

        if len(credentials_lists) > 1 :
            new_token += 1
            if new_token == len(credentials_lists) :
                new_token = 0

        self.osci.update_object_attribute(cloud_name, "GLOBAL", "vmc_defaults", False, "current_token", str(new_token))
        self.unlock(cloud_name, "VMC", "shared_access_token_counter", lock)

        return credentials_lists[current_token]

    @trace
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        lock = False
        try :
            if current_step == "provision_originated" :
                credentials_list = self.rotate_token(obj_attr_list["cloud_name"])
                tenant = credentials_list.split(":")[0]
                obj_attr_list["tenant"] = tenant
                obj_attr_list["credentials_list"] = credentials_list
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", \
                    obj_attr_list["uuid"], "credentials_list", credentials_list)

                # Cache libcloud objects for this daemon / process before the VMs are attached
                self.connect(credentials_list)

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
                _msg += " on " + self.description + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on " + self.description + " \"" + obj_attr_list["cloud_name"]
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
                _msg += " on " + self.description + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on " + self.description + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

