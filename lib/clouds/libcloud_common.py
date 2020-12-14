#!/usr/bin/env python3

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
    @author: Michael R. Galaxy, Darrin Eden
'''
from time import time, sleep
from random import randint
from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import Nethashget

from .shared_functions import CldOpsException, CommonCloudFunctions

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState
from libcloud.common.types import MalformedResponseError
from libcloud.common.exceptions import BaseHTTPError

from copy import deepcopy

from io import StringIO

import threading
import traceback
import os
import http.client

from http.client import HTTPConnection
from http.client import HTTPSConnection

import libcloud.security
import logging
import contextlib

'''
We need the ability to log HTTP headers to debug what happens
with libcloud.

For the response HTTP headers, that's not problem => We get that
from the libcloud library itself.

For the request headers, libcloud doesn't make that easy, so we have to
bypass it.

What we're trying to do here is solve a conundrum. Under the covers,
libcloud uses /usr/lib/python2.7/httplib.py as it's primary HTTP
transport library.

httplib, has the ability to debug itself, but instead of using the logging
library like a "good" python library should, it just prints to stdout.
In a separate patch (via Dockerfile) we fix httplib to work correctly
and use a logger. We can't really monkey patch this, and sending a python
patch upstream would take too long

That being said, after it uses the logging library correctly, we still
have to capture the log output the headers ONLY when something bad happens.
We don't want to spew a bunch of header logs to the logging system
for the 99% of the time when things are working fine.

To solve that problem, we trap the (newly fixed) http header log messages
from the httplib library into a StringIO buffer. Then, if we happen
to hit a python exception in libcloud, we dump those headers to the log
if and only if there is an exception.

That's what all the mess below is for.

So, below, if we don't carry the patch to httplib, we only log the response
headers (which are usually what matters). If we carry the httplib patch
(sold separately), then we will also log the request headers.
'''

stream = False

# Tell the httplib patch (if available, sold separately) to debug and use the logging module
# for logging the request headers.
if hasattr(http.client, "httplib_log") :
    HTTPConnection.debuglevel = 3
    HTTPSConnection.debuglevel = 3
    httplib_log = logging.getLogger("httplib")
    httplib_log.setLevel(logging.DEBUG)
    httplib_log.propagate = False

    # Capture those messages to StringIO
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    for handler in httplib_log.handlers:
        httplib_log.removeHandler(handler)
    httplib_log.addHandler(handler)

class LibcloudCmds(CommonCloudFunctions) :
    catalogs = threading.local()
    locations = False
    services = False
    sizes = False
    imagelist = []
    networks = False
    security_groups = False
    floating_ip_pools = False
    global_images = False
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
                 FOO_CREDENTIALS = user1:bar;user2:baz
             Example 2)
                1. Cloud is named "HAPPY"
                2. There are three tenants named "not", "so", and "lucky"
                3. Each tenant has the same access_key and access_token, two (2) credentials each as "foo" and "bar"
                4. The configuration file would look like this:
                 [USER-DEFINED : CLOUDOPTION_HAPPY ]
                 HAPPY_CREDENTIALS = not:foo:bar;so:foo:bar;lucky:foo:bar
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
    @use_volumes: (Optional, Default False)
            Leave this as false if you're not interested in block storage / volume support, or you're cloud doesn't support it.
    @use_sizes: (Optional, Default True)
            Use the VM image sizes as listed by your cloud.
    @use_locations: (Optional, Default True)
            Use the Regions as listed by your cloud.
    @use_services: (Optional, Default False)
            Use the Services as listed by your cloud.
    @use_networks: (Optional, Default False)
            Use the Networks (in case of multi-network clouds) as listed by your cloud.
    @use_security_groups: (Optional, Default False)
            Use the Security Groups as listed by your cloud.
    @use_public_ips: (Optional, Default True)
            Does your cloud provide public/private IP pair
    @use_get_image: (Optional, Default True)
            Should be set to false only if the get_image() method is not implemented for the libcloud backend.
    @verify_ssl: (Optional, Default True)
            Whether or not to have libcloud verify SSL certificates when communicating with the cloud
    @tldomain: (Optional, Default False)
            The FQDN of your cloud. None if false.
    @target_location: (Optional, Default False)
            If true, pass a location object to list_sizes and list_images
    @extra: (Optional, Default empty)
            Extra fixed parameters to be used by libcloud that we don't know about, which get passed at instance creation time.
    '''

    @trace
    def __init__ (self, pid, osci, expid = None, provider = "OverrideMe", \
                  num_credentials = 2, use_ssh_keys = False, use_volumes = False, \
                  use_locations = True, use_services = False, use_networks = False, \
                  use_security_groups = False, use_public_ips = True, use_sizes = True, \
                  use_get_image = True, tldomain = False, verify_ssl = True, \
                  target_location = False, extra = {}) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci, expid)
        self.ft_supported = False
        self.current_token = 0
        self.cache_mutex = threading.Lock()
        self.token_mutex = threading.Lock()
        self.provider = provider
        self.num_credentials = num_credentials
        self.use_ssh_keys = use_ssh_keys
        self.use_volumes = use_volumes
        self.use_locations = use_locations
        self.use_services = use_services
        self.use_networks = use_networks
        self.use_security_groups = use_security_groups
        self.use_public_ips = use_public_ips
        self.use_sizes = use_sizes
        self.use_get_image = use_get_image
        self.target_location = target_location
        self.tldomain = tldomain
        self.additional_rc_contents = ''
        self.imglist_kwargs = {}
        self.vmcreate_kwargs = {}
        self.vvcreate_kwargs = {}
        self.vmdestroy_kwargs = {}
        self.vmlist_args = []
        self.connauth_pamap = {}
        self.access = False

        libcloud.security.VERIFY_SSL_CERT = verify_ssl

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "LibCloud Base"

    @trace
    def dump_reset(self, location) :
        if stream :
            stream.truncate(0)
            stream.seek(0)

    @trace
    def get_adapter(self, credentials_list) :
        '''
        The next step to debugging libcloud headers is to make sure that we
        reset the StringIO stream before and after each request to libcloud.
        That way, when there is a python exception, we only get the header logs
        for the last request and not for requests that are irrelevant.
        '''
        self.dump_reset("get_adapter")
        return LibcloudCmds.catalogs.cbtool[credentials_list]

    @trace
    def dump_httplib_headers(self, credentials_list) :
        '''
        Finally, dump the httplib header logs (if any) and re-truncate the stream
        for the next error.
        '''
        if credentials_list == False :
            cbwarn("Cannot dump headers. Credentials list is False.")
        else :
            try :
                # Log the request headers, if available.
                if stream :
                    send_headers = stream.getvalue().strip().replace("\n\n", "\n").split("\n")
                    for header in send_headers :
                        if header.count("Bearer") :
                            cberr("send ==> Bearer: xxxxxxxxxxxxxxx")
                        else :
                            cberr("send ==> " + header.strip())

                # Grab the response headers from libcloud itself and log those.
                headers = LibcloudCmds.catalogs.cbtool[credentials_list].connection.connection.getheaders()
                for hkey in list(headers.keys()) :
                    cberr("recv ==> " + str(hkey) + ": " + headers[hkey])
            except Exception as e :
                for line in traceback.format_exc().splitlines() :
                    cberr(line, True)

        self.dump_reset("maindump")

    @trace
    def connect(self, credentials_list, vmc_name = False, obj_attr_list = False) :

#        if not self.access and obj_attr_list and "access" in obj_attr_list :
#            self.access = obj_attr_list["access"]

        credentials = credentials_list.split(":")
        if len(credentials) != (self.num_credentials + 1) :
            _status = 8499
            _fmsg = self.get_description() + " needs at least "
            _fmsg += str(self.num_credentials) + " credentials, including an "
            _fmsg += "arbitrary tag representing the tenant. Refer to the templates for examples."
            raise CldOpsException(_fmsg, _status)

        tenant = credentials[0]

        # libcloud is totally not thread-safe. bastards.
        cbdebug("Checking libcloud connection...")
        try :
            getattr(LibcloudCmds.catalogs, "cbtool")
        except AttributeError as e :
            cbdebug("Initializing thread local connection: ")

            LibcloudCmds.catalogs.cbtool = {}

        self.cache_mutex.acquire()
        _hostname = "NA"
        try :
            _status = 100

            if credentials_list not in LibcloudCmds.catalogs.cbtool :
                cbdebug("Connecting to " + self.get_description() + "...")
                _status = 110
                driver = self.get_real_driver(self.provider)
                LibcloudCmds.catalogs.cbtool[credentials_list] = self.get_libcloud_driver(driver, tenant, *credentials[1:])
            else :
                cbdebug(self.get_description()  + " Already connected.")

            cbdebug(" Caching " + self.get_description() + " locations. If stale, then restart...")

            if obj_attr_list and "name" in obj_attr_list :
                _hostname = obj_attr_list["name"]

            if self.use_locations :
                if not LibcloudCmds.locations :
                    cbdebug(" Caching " + self.get_description()  + " Locations...", True)
                    LibcloudCmds.locations = self.get_adapter(credentials_list).list_locations()

                assert(LibcloudCmds.locations)

                if self.target_location :
                    for _location in LibcloudCmds.locations :
                        LibcloudCmds.target_location = _location
                        if _location.id == vmc_name :
                            LibcloudCmds.target_location = _location
                            break

            if self.use_sizes :
                if not LibcloudCmds.sizes :
                    if self.target_location :
                        _msg = " Caching " + self.get_description() + " Sizes (location \"" + LibcloudCmds.target_location.id + "\")..."
                        cbdebug(_msg, True)
                        LibcloudCmds.sizes = self.get_adapter(credentials_list).list_sizes(location = LibcloudCmds.target_location)
                    else :
                        _msg = " Caching " + self.get_description() + " Sizes..."
                        cbdebug(_msg, True)
                        LibcloudCmds.sizes = self.get_adapter(credentials_list).list_sizes()
                    assert(LibcloudCmds.sizes)

            if self.use_ssh_keys :
                if credentials_list not in LibcloudCmds.keys :
                    cbdebug(" Caching " + self.get_description() + " keys (" + tenant + ")", True)
                    LibcloudCmds.keys[credentials_list] = self.get_adapter(credentials_list).list_key_pairs()
                    assert(credentials_list in LibcloudCmds.keys)

            if self.use_services :
                if not LibcloudCmds.services :
                    cbdebug(" Caching " + self.get_description()  + " Services...", True)
                    LibcloudCmds.services = self.get_adapter(credentials_list).ex_list_cloud_services()

            if self.use_networks :
                if not LibcloudCmds.networks :
                    cbdebug(" Caching " + self.get_description()  + " Networks...", True)
                    LibcloudCmds.networks = self.get_adapter(credentials_list).ex_list_networks()

            if self.use_security_groups :
                if not LibcloudCmds.security_groups :
                    cbdebug(" Caching " + self.get_description()  + " Security Groups...", True)
                    LibcloudCmds.security_groups = self.get_adapter(credentials_list).ex_list_security_groups()

            cbdebug("Done caching.")

            _status = 0

        except Exception as e:
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
            _msg = "Error connecting " + self.get_description() + ": " + str(e)
            cbdebug(_msg, True)
            _status = 23

        finally :
            self.cache_mutex.release()
            if _status :
                _msg = self.get_description() + " connection failure. Failed to use your credentials for account: " + tenant
                cbdebug(_msg, True)
                cberr(_msg)
                if credentials_list in LibcloudCmds.catalogs.cbtool :
                    del LibcloudCmds.catalogs.cbtool[credentials_list]
                raise CldOpsException(_msg, _status)
            else :
                _msg = self.get_description() + " connection successful."
                cbdebug(_msg)
                return _status, _msg, LibcloudCmds.catalogs.cbtool[credentials_list], _hostname

    @trace
    def test_vmc_connection(self, cloud_name, vmc_name, access, credentials, key_name, \
                            security_group_name, vm_templates, vm_defaults, vmc_defaults) :
        '''
        TBD
        '''
        credentials_list = False
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            vmc_name = vmc_name.replace("____",' ')

            if "global_images" in vmc_defaults and str(vmc_defaults["global_images"]).lower().strip() == "true" :
                LibcloudCmds.global_images = True

            _key_pair_found = False
            for credentials_list in credentials.split(";"):
                _status, _msg, _local_conn, _hostname = self.connect(credentials_list, vmc_name, vmc_defaults)
                _key_pair_found = self.check_ssh_key(vmc_name, self.determine_key_name(vm_defaults), vm_defaults, False, _local_conn, self.use_ssh_keys)

            self.generate_rc(cloud_name, vmc_defaults, self.additional_rc_contents)

            _prov_netname_found, _run_netname_found = self.check_networks(vmc_name, vm_defaults)

            _extra_vmc_setup_complete = self.extra_vmc_setup(vmc_name, vmc_defaults, vm_defaults, vm_templates, _local_conn)

            _detected_imageids = self.check_images(vmc_name, vm_templates, credentials_list, vm_defaults)

            _extra_vmc_setup_complete = self.extra_vmc_setup(vmc_name, vmc_defaults, vm_defaults, vm_templates, _local_conn)

            if not (_run_netname_found and _prov_netname_found and _key_pair_found and _extra_vmc_setup_complete) :
                _msg = "Check the previous errors, fix it (using " + self.get_description()
                _msg += "'s CLI or (Web) GUI"
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
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
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
        if "prov_netname" in vm_defaults :
            _prov_netname = vm_defaults["prov_netname"]
        else :
            _prov_netname = vm_defaults["netname"]

        if "run_netname" in vm_defaults :
            _prov_netname = vm_defaults["run_netname"]
        else :
            _run_netname = vm_defaults["netname"]

        _prov_netname_found = False
        _run_netname_found = False

        if LibcloudCmds.networks :
            for _network in LibcloudCmds.networks :
                if _network.name == _prov_netname :
                    _prov_netname_found = True

                if _network.name == _run_netname :
                    _run_netname_found = True
        else :
            _prov_netname_found = True
            _run_netname_found = True

        return _prov_netname_found, _run_netname_found

    @trace
    def check_images(self, vmc_name, vm_templates, credentials_list, vm_defaults) :
        '''
        TBD
        '''
        self.common_messages("IMG", { "name": vmc_name }, "checking", 0, '')

        _registered_image_list = self.repopulate_images({"credentials_list" : credentials_list})

        _registered_imageid_list = []

        _map_name_to_id = {}
        _map_id_to_name = {}

        for _registered_image in _registered_image_list :

            _registered_imageid_list.append(_registered_image.id)
            _map_name_to_id[str(_registered_image.name.strip())] = str(_registered_image.id)
            _map_name_to_id[str(_registered_image.id.strip())] = str(_registered_image.id)

        for _vm_role in list(vm_templates.keys()) :
            _imageid = str2dic(vm_templates[_vm_role])["imageid1"]
            _replacement_id = _imageid
            if _imageid != "to_replace" :
                # Need to support spaces within image names.
                # If we can't find the original name, try the same thing with spaces instead of
                # underscores.
                if _imageid in _map_name_to_id or _imageid.replace("_", " ") in _map_name_to_id:
                    if _imageid not in _map_name_to_id :
                        _replacement_id = _imageid.replace("_", " ")

                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_replacement_id])
                else :
                    _map_name_to_id[_imageid] = _imageid
                    vm_templates[_vm_role] = vm_templates[_vm_role].replace(_imageid, _map_name_to_id[_imageid])

                _map_id_to_name[_map_name_to_id[_replacement_id]] = _replacement_id

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
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def extra_vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        return True

    @trace
    def post_vmcreate_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def pre_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def post_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def extra_vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        return True

    @trace
    def pre_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def post_vmdelete_process(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        return True

    @trace
    def get_list_node_args(self, obj_attr_list) :
        '''
        TBD
        '''

        return [ ]

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''
        credentials_list = False
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _search = "cb-" + obj_attr_list["username"] + "-" + obj_attr_list["cloud_name"]

            for credentials_list in obj_attr_list["credentials"].split(";"):
                _status, _msg, _local_conn, _hostname = self.connect(credentials_list)

            _wait = int(obj_attr_list["update_frequency"])
            _existing_instances = True
            while _existing_instances :
                _existing_instances = False
                for credentials_list in obj_attr_list["credentials"].split(";"):
                    credentials = credentials_list.split(":")
                    tenant = credentials[0]
                    obj_attr_list["tenant"] = tenant
                    self.common_messages("VMC", obj_attr_list, "cleaning up vms", 0, '')

                    _reservations = self.get_adapter(credentials_list).list_nodes(*self.get_list_node_args(obj_attr_list))

                    for _reservation in _reservations :
                        _match = "-".join(_reservation.name.split("-")[:3])
                    
                        if _match == _search :
                            if _reservation.state in [ NodeState.PENDING, NodeState.STOPPED ] :
                                cbdebug("Instance " + _reservation.name + " still has a pending event. waiting to destroy...")
                                if _reservation.state == NodeState.STOPPED :
                                    cbdebug("Instance is stopped: " + _reservation.name + " . CB will not destroy stopped instances, but we have sent a start request to the cloud. If it does not resume, please investigate why it is stopped.", True)
                                    self.get_adapter(credentials_list).ex_power_on_node(_reservation)

                                _existing_instances = True
                                continue

                            try :
                                cbdebug("Killing: " + _reservation.name + " (" + tenant + ")", True)
                                _reservation.destroy()
                            except BaseHTTPError as e :
                                if e.code == 404 :
                                    cbwarn("404: Not trusting instance " + _reservation.name + " error status... Will try again.", True)
                                self.dump_httplib_headers(credentials_list)
                            except MalformedResponseError as e :
                                self.dump_httplib_headers(credentials_list)
                                cbdebug("The Cloud's API is misbehaving...", True)
                            except Exception as e :
                                for line in traceback.format_exc().splitlines() :
                                    cbwarn(line, True)
                                self.dump_httplib_headers(credentials_list)
                            _existing_instances = True
                        else :
                            _msg = "Cleaning up " + self.get_description() + ".  Ignoring instance: " + _reservation.name
                            cbdebug(_msg)

                if _existing_instances :
                    _wait = self.backoff(obj_attr_list, _wait)

            if self.use_volumes :
                _wait = int(obj_attr_list["update_frequency"])
                _running_volumes = True
                while _running_volumes :
                    _running_volumes = False
                    for credentials_list in obj_attr_list["credentials"].split(";"):
                        credentials = credentials_list.split(":")
                        tenant = credentials[0]
                        self.common_messages("VMC", obj_attr_list, "cleaning up vvs", 0, '')
                        obj_attr_list["tenant"] = tenant

                        _volumes = self.get_adapter(credentials_list).list_volumes()
                        for _volume in _volumes :
                            _match = "-".join(_volume.name.split("-")[:3])
                        
                            if _match == _search :
                                try :
                                    cbdebug("Destroying: " + _volume.name + " (" + tenant + ")", True)
                                    _volume.destroy()
                                except MalformedResponseError as e :
                                    self.dump_httplib_headers(credentials_list)
                                    raise CldOpsException("The Cloud's API is misbehaving", 1483)
                                except Exception as e :
                                    for line in traceback.format_exc().splitlines() :
                                        cbwarn(line, True)
                                    self.dump_httplib_headers(credentials_list)
                                _running_volumes = True
                            else :
                                _msg = "Cleaning up " + self.get_description() + ". Ignoring volume: " + _volume.name
                                cbdebug(_msg)

                        if _running_volumes :
                            _wait = self.backoff(obj_attr_list, _wait)

            self.extra_vmccleanup(obj_attr_list)

            _status = 0

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            cberr(_msg)
            _status = 2

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
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
        credentials_list = False
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            obj_attr_list["name"] = obj_attr_list["name"].replace("____",' ')

            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _status, _fmsg = self.vmccleanup(obj_attr_list)
            else :
                _status = 0

            for credentials_list in obj_attr_list["credentials"].split(";"):
                _x, _y, _z, _hostname = self.connect(credentials_list, obj_attr_list)

            obj_attr_list["cloud_hostname"] = _hostname + "_" + obj_attr_list["name"]

            # Public clouds don't really have "hostnames" - they have a single endpoint for all
            # regions and VMCs.
            obj_attr_list["cloud_ip"] = _hostname + "." + gethostbyname(self.tldomain) + "_" + obj_attr_list["name"]
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

        except CldOpsException as obj :
            _fmsg = str(obj.msg)
            _status = 2

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
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

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
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
        credentials_list = False
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _nr_instances = 0

            for _vmc_uuid in self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC") :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], \
                                                      "VMC", False, _vmc_uuid, \
                                                      False)

                for credentials_list in _vmc_attr_list["credentials"].split(";"):
                    _status, _msg, _local_conn, _hostname = self.connect(credentials_list)

                    _instance_list = _local_conn.list_nodes(*self.get_list_node_args(obj_attr_list))

                    if _instance_list :
                        for _instance in _instance_list :
                            if _instance.name.count("cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"]) :
                                _nr_instances += 1

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
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

        _registered_key_pair_objects = {}
        for _key_pair in connection.list_key_pairs() :
            registered_key_pairs[_key_pair.name] = str(_key_pair.fingerprint) + '-'
            if "id" in _key_pair.extra :
                registered_key_pairs[_key_pair.name] += str(_key_pair.extra["id"])
            else :
                registered_key_pairs[_key_pair.name] += "NA"
            _registered_key_pair_objects[_key_pair.name] = _key_pair
            #connection.delete_key_pair(_registered_key_pair_objects[key_name])

        return True

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            node = self.get_instances(obj_attr_list)

            obj_attr_list["run_cloud_ip"] = "NA"
            obj_attr_list["prov_cloud_ip"] = "NA"            
                    
            if len(node.private_ips) > 0 :
                if obj_attr_list["run_netname"].lower() != "public" :
                    obj_attr_list["run_cloud_ip"] = node.private_ips[0]
                elif len(node.public_ips) > 0 :
                    obj_attr_list["run_cloud_ip"] = node.public_ips[0]

                if not self.use_public_ips :
                    obj_attr_list["run_cloud_ip"] = node.private_ips[0]
            else :
                if len(node.public_ips) > 0 :
                    obj_attr_list["run_cloud_ip"] = node.public_ips[0]
                else :
                    cbdebug(obj_attr_list["log_string"] + " Instance Public address not yet available.")
                    return False

            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]

            if obj_attr_list["hostname_key"] == "cloud_vm_name" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_vm_name"]
            elif obj_attr_list["hostname_key"] == "cloud_ip" :
                obj_attr_list["cloud_hostname"] = obj_attr_list["cloud_ip"].replace('.','-')

            _msg = obj_attr_list["log_string"] + " Public IP = " + str(node.public_ips)
            _msg += " Private IP = " + str(node.private_ips)
            cbdebug(_msg)

            if len(node.public_ips) > 0 :
                obj_attr_list["public_cloud_ip"] = node.public_ips[0]

            if len(node.private_ips) > 0 :
                if obj_attr_list["prov_netname"].lower() != "public" :
                    obj_attr_list["prov_cloud_ip"] = node.private_ips[0]
                else :
                    if len(node.public_ips) > 0 :
                        obj_attr_list["prov_cloud_ip"] = node.public_ips[0]

                if not self.use_public_ips :
                    if obj_attr_list["use_floating_ip"].lower() == "true" :
                        if len(node.public_ips) > 0 :
                            obj_attr_list["prov_cloud_ip"] = node.public_ips[0]
                    else :
                        if len(node.private_ips) > 0 :
                            obj_attr_list["prov_cloud_ip"] = node.private_ips[0]
                else :
                    if obj_attr_list["prov_netname"].lower() != "public" :
                        if len(node.private_ips) > 0 :
                            obj_attr_list["prov_cloud_ip"] = node.private_ips[0]

            else :
                if len(node.public_ips) > 0 :
                    obj_attr_list["prov_cloud_ip"] = node.public_ips[0]

            # Some clouds do not provide an IP per instance, but a (SSH) port per instance instead
            if "ssh_port" in node.extra :
                obj_attr_list["prov_cloud_port"] = node.extra["ssh_port"]

                if obj_attr_list["check_boot_complete"] == "tcp_on_22":
                    obj_attr_list["check_boot_complete"] = "tcp_on_" + str(obj_attr_list["prov_cloud_port"])

            _status = 0
            return True

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _msg = "Could not retrieve IP addresses for object " + obj_attr_list["uuid"]
            _msg += " from " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + ": " + str(e)
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def get_instances(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _msg = "cloud_vm_name " + obj_attr_list["log_string"]
            _msg += " from " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\""
            cbdebug(_msg)
            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0

            # This call (list nodes) is a very high-frequency call and fails often. It causes
            # vmcreate()'s to fail unnecessarily, because it can be called dozens of times before
            # a create has actually completed, so let's include a retry.
            # However, we don't want to extend the overall timeouts any further than what has been configured.
            # So, let's retry only every 1-second until we hit the maximum.
            while True :
                try :
                    node_list = self.get_adapter(obj_attr_list["credentials_list"]).list_nodes(*self.get_list_node_args(obj_attr_list))
                    break
                except Exception as e:
                    _curr_tries += 1
                    if _curr_tries > _wait :
                        raise e
                    cbwarn("Problem querying for instance (" + str(_curr_tries) + "): " + obj_attr_list["log_string"] + ": " + str(e) + ", retrying...")
                    sleep(1)

            node = False
            if node_list :
                for x in node_list :
                    if x.name == obj_attr_list["cloud_vm_name"] :
                        node = x
                        break
            _status = 0

            return node

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def get_images(self, obj_attr_list, fail = True) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _candidate_images = False

            if self.is_cloud_image_uuid(obj_attr_list["imageid1"]) :
                if self.use_get_image :
                    try :
                        _candidate_images = self.get_adapter(obj_attr_list["credentials_list"]).get_image(obj_attr_list["imageid1"])
                    except BaseHTTPError as e :
                        if e.code == 404 :
                            cbdebug("Instead looking for: " + obj_attr_list["imageid1"].replace("_", " "), True)
                            if self.target_location :
                                _candidate_images = self.get_adapter(obj_attr_list["credentials_list"]).get_image(obj_attr_list["imageid1"], location = obj_attr_list["libcloud_location_inst"])
                            else :
                                _candidate_images = self.get_adapter(obj_attr_list["credentials_list"]).get_image(obj_attr_list["imageid1"].replace("_", " "))
                else :
                    for _image in self.repopulate_images(obj_attr_list) :
                        if _image.id == obj_attr_list["imageid1"] :
                            _candidate_images = _image
                            break
            else :
                for _image in self.repopulate_images(obj_attr_list) :
                    if _image.name == obj_attr_list["imageid1"] or _image.id == obj_attr_list["imageid1"] :
                        _candidate_images = _image
                        break

            _fmsg = "Please check if the defined image name is present on this "
            _fmsg += self.get_description()

            if _candidate_images :
                obj_attr_list["imageid1"] = _candidate_images.name
                obj_attr_list["boot_volume_imageid1"] = _candidate_images.id
                _status = 0

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                if fail :
                    _msg = "Image Name (" +  obj_attr_list["imageid1"] + ") not found: " + _fmsg
                    cberr(_msg)
                    raise CldOpsException(_msg, _status)
                else :
                    return False
            else :
                return _candidate_images

    @trace
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            node = self.get_instances(obj_attr_list)
            return node and node.state == NodeState.RUNNING

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def is_vm_ready(self, obj_attr_list) :
        '''
        TBD
        '''
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
    def vm_placement(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _status = 0

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
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
    def vvcreate(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            obj_attr_list["cloud_vv_instance"] = None

            if "cloud_vv_type" not in obj_attr_list :

                if self.use_volumes :
                    if "cloud_vv_type" not in obj_attr_list :
                        obj_attr_list["cloud_vv_type"] = "LCV"
                else :
                    obj_attr_list["cloud_vv_type"] = "NOT SUPPORTED"

            if self.use_volumes and "cloud_vv" in obj_attr_list and str(obj_attr_list["cloud_vv"]).lower() != "false" :

                obj_attr_list["region"] = _region = obj_attr_list["vmc_name"]
                obj_attr_list["cloud_vv_name"] = obj_attr_list["cloud_vv_name"].lower().replace("_", "-")

                obj_attr_list["last_known_state"] = "about to send volume create request"
                self.common_messages("VV", obj_attr_list, "creating", _status, _fmsg)

                if self.use_volumes :
                    _mark_a = int(time())

                    for _location in LibcloudCmds.locations :
                        if _location.id == obj_attr_list["region"] :
                            self.vvcreate_kwargs["location"] = _location

                    if not self.vvcreate_kwargs :
                        self.vvcreate_kwargs["location"] = obj_attr_list["availability_zone"]
                        self.vvcreate_kwargs["ex_volume_type"] = obj_attr_list["cloud_vv_type"]

                    _volume = connection.create_volume(int(obj_attr_list["cloud_vv"]),
                                                      obj_attr_list["cloud_vv_name"],
                                                      **self.vvcreate_kwargs)

                    self.annotate_time_breakdown(obj_attr_list, "create_volume_time", _mark_a)

                    sleep(int(obj_attr_list["update_frequency"]))

                    obj_attr_list["cloud_vv_uuid"] = _volume.id
                    obj_attr_list["cloud_vv_instance"] = _volume

                else :
                    obj_attr_list["cloud_vv_uuid"] = "NOT SUPPORTED"

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)

        finally :
            _status, _msg = self.common_messages("VV", obj_attr_list, "created", _status, _fmsg)
            return _status, _msg

    @trace
    def vvdestroy(self, obj_attr_list, connection) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            if str(obj_attr_list["cloud_vv_uuid"]).lower() != "not supported" and str(obj_attr_list["cloud_vv_uuid"]).lower() != "none" :
                _volumes = connection.list_volumes()
                if len(_volumes) :
                    self.common_messages("VV", obj_attr_list, "destroying", 0, '')
                for _volume in _volumes :
                    if _volume.name == obj_attr_list["cloud_vv_name"] :
                        try :
                            _volume.destroy()
                            break
                        except MalformedResponseError as e :
                            self.dump_httplib_headers(credentials_list)
                            raise CldOpsException("The Cloud's API is misbehaving", 1483)
                        except Exception as e :
                            for line in traceback.format_exc().splitlines() :
                                cbwarn(line, True)
                            self.dump_httplib_headers(credentials_list)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
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
            _fmsg = "An error has occurred when creating new VM, but no error message was captured"
            _instance = False
            _reservation = False
            volume = False

            # This is just to pass regression tests.
            test_map = dict(platinum64 = "64gb", rhodium64 = "48gb", \
                            gold64 = "32gb", silver64 = "16gb", bronze64 = "8gb",\
                             copper64 = "4gb", gold32 = "4gb", silver32 = "4gb",\
                              iron64 = "2gb", iron32 = "2gb", bronze32 = "2gb",\
                               copper32 = "2gb", micro32 = "1gb", nano32 = "1gb",\
                                pico32 = "512mb")

            _requested_size = obj_attr_list["size"]

            if _requested_size in test_map :
                _requested_size = test_map[_requested_size]

            self.determine_instance_name(obj_attr_list)
            self.determine_key_name(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to connect to " + self.get_description() + " manager"

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if obj_attr_list["ai"] != "none" :
                _credentials_list = self.osci.pending_object_get(obj_attr_list["cloud_name"], "AI", obj_attr_list["ai"], "credentials_list")
            else :
                _credentials_list = self.rotate_token(obj_attr_list["cloud_name"])

            if "tenant_from_rc" in obj_attr_list :
                obj_attr_list["tenant"] = obj_attr_list["tenant_from_rc"]
            else :
                obj_attr_list["tenant"] = _credentials_list.split(":")[0]

            obj_attr_list["credential"] = _credentials_list.split(":")[1]
            obj_attr_list["credentials_list"] = _credentials_list

            _mark_a = time()
            _status, _msg, _local_conn, _hostname = self.connect(_credentials_list, obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "authenticate_time", _mark_a)

            _mark_a = time()
            if self.is_vm_running(obj_attr_list) :
                _msg = "An instance named \"" + obj_attr_list["cloud_vm_name"]
                _msg += "\" is already running. It needs to be destroyed first."
                _status = 187
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            self.annotate_time_breakdown(obj_attr_list, "check_existing_instance_time", _mark_a)

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])

            self.vm_placement(obj_attr_list)

            obj_attr_list["last_known_state"] = "about to send create request"

            _mark_a = time()
            obj_attr_list["libcloud_image_inst"] = self.get_images(obj_attr_list)
            self.annotate_time_breakdown(obj_attr_list, "get_imageid_time", _mark_a)

            obj_attr_list["config_drive"] = False

            obj_attr_list["userdata"] = self.populate_cloudconfig(obj_attr_list)
            if obj_attr_list["userdata"] :
                obj_attr_list["config_drive"] = True
            else :
                obj_attr_list["config_drive"] = False

            self.common_messages("VM", obj_attr_list, "creating", 0, '')

            obj_attr_list["libcloud_size_inst"] = False

            if self.use_ssh_keys :
                _mark_a = time()

                _tmp_keys = obj_attr_list["key_name"].split(",")
                for dontcare in range(0, 2) :
                    _keys = []
                    for _tmp_key in _tmp_keys :
                        for _key in LibcloudCmds.keys[_credentials_list] :
                            if "id" in _key.extra :
                                _key_id = _key.extra["id"]
                                if _tmp_key in [_key.name, _key_id] and _key_id not in _keys and _key.name not in _keys :
                                    _keys.append(_key_id)
                            else :
                                if _key.name in _tmp_keys :
                                    _keys.append(_key.name)

                    if len(_keys) >= len(_tmp_keys) :
                        break

                    cbdebug("Only found " + str(len(_keys)) + " keys. Refreshing key list...", True)
                    LibcloudCmds.keys[_credentials_list] = self.get_adapter(_credentials_list).list_key_pairs()

                if len(_keys) < len(_tmp_keys) :
                    raise CldOpsException("Not all SSH keys exist. Check your configuration: " + obj_attr_list["key_name"] + " _keys: " + str(_keys) + " _tmp_keys: " + str(_tmp_keys), _status)
                self.annotate_time_breakdown(obj_attr_list, "get_sshkey_time", _mark_a)
            else :
                _keys = []

            self.pre_vmcreate_process(obj_attr_list, _local_conn, _keys)

            if self.use_sizes :
                _mark_a = time()
                for _sz in LibcloudCmds.sizes :
                    if _sz.id == _requested_size :
                        obj_attr_list["libcloud_size_inst"] = _sz
                        break

                    if _sz.name == _requested_size :
                        obj_attr_list["libcloud_size_inst"] = _sz
                        break
                self.annotate_time_breakdown(obj_attr_list, "get_size_time", _mark_a)

            _status, _fmsg = self.vvcreate(obj_attr_list, _local_conn)

            if "libcloud_location_inst" not in obj_attr_list :
                raise CldOpsException("Region " + obj_attr_list["region"] + " has become unavailable. Check your configuration and try again.", 917)

            _mark_a = time()

            # Libcloud is not threadsafe.
            # It clobbers this dictionary if you don't protect it.
            _args_clone = deepcopy(self.vmcreate_kwargs)

            if obj_attr_list["libcloud_call_type"] == "create_node_with_mixed_arguments" :
                _reservation = self.get_adapter(_credentials_list).create_node(
                    obj_attr_list["cloud_vm_name"],
                    obj_attr_list["libcloud_size_inst"],
                    obj_attr_list["libcloud_image_inst"],
                    obj_attr_list["libcloud_location_inst"],
                    **_args_clone
                    )

            if obj_attr_list["libcloud_call_type"] == "create_node_with_keyword_arguments_only" :
                _reservation = self.get_adapter(_credentials_list).create_node(
                    **self.vmcreate_kwargs
                    )

            obj_attr_list["last_known_state"] = "sent create request"

            if _reservation :
                self.annotate_time_breakdown(obj_attr_list, "instance_creation_time", _mark_a)

                cbdebug(" Reservation ID for " + obj_attr_list["log_string"] + " is: " + str(_reservation.id), True)
                obj_attr_list["last_known_state"] = "vm created"
                sleep(int(obj_attr_list["update_frequency"]))

                obj_attr_list["cloud_vm_uuid"] = _reservation.uuid

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                if obj_attr_list["cloud_vv_instance"] :

                    _mark_a = time()
                    if not obj_attr_list["cloud_vv_instance"].attach(_reservation) :
                        _fmsg = "Volume attach failed. Aborting VM creation..."
                        obj_attr_list["cloud_vv_instance"].destroy()
                        raise CldOpsException(_fmsg, _status)
                    else :
                        self.annotate_time_breakdown(obj_attr_list, "attach_volume_time", _mark_a)
 
                self.post_vmcreate_process(obj_attr_list, _local_conn)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)

                obj_attr_list["host_name"] = _reservation.name
                obj_attr_list["canonical_id"] = _reservation.id

                _status = 0

                if obj_attr_list["force_failure"].lower() == "true" :
                    _fmsg = "Forced failure (option FORCE_FAILURE set \"true\")"
                    _status = 916

            else :
                obj_attr_list["host_name"] = "unknown"
                obj_attr_list["last_known_state"] = "vm creation failed"
                _fmsg = "Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException as obj :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = obj.status
            _fmsg = str(obj.msg)
            cbwarn("Error during reservation creation: " + _fmsg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)
            cbwarn("Error reaching " + self.get_description() + ":" + _fmsg)

        finally :
            if "mgt_003_provisioning_request_completed" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_active_time", obj_attr_list["mgt_003_provisioning_request_completed"], False)

            if "mgt_004_network_acessible" in obj_attr_list :
                self.annotate_time_breakdown(obj_attr_list, "instance_reachable_time", obj_attr_list["mgt_004_network_acessible"], False)

            if not _status :
                True
            else :
                if _reservation :
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

            cbdebug("Last known state: " + str(obj_attr_list["last_known_state"]))

            _wait = int(obj_attr_list["update_frequency"])
            _curr_tries = 0
            _max_tries = int(obj_attr_list["update_attempts"])

            _credentials_list = obj_attr_list["credentials_list"]
            _status, _msg, _local_conn, _hostname = self.connect(_credentials_list)

            self.pre_vmdelete_process(obj_attr_list, _local_conn)

            if "instance_obj" in obj_attr_list :
                if obj_attr_list["instance_obj"] :

                    self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                    _time_mark_drs = int(time())

                    if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                        obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

                    obj_attr_list["instance_obj"].destroy()

                    sleep(_wait)
                    del obj_attr_list["instance_obj"]

                if obj_attr_list["cloud_vv_instance"] :
                    obj_attr_list["cloud_vv_instance"].destroy()
                    del obj_attr_list["cloud_vv_instance"]

                obj_attr_list["mgt_902_deprovisioning_request_sent"] = int(time()) - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

            else :

                self.common_messages("VM", obj_attr_list, "destroying", 0, '')

                firsttime = True
                _time_mark_drs = int(time())
                _instance = self.get_instances(obj_attr_list)
                while _instance :
                    if _curr_tries >= _max_tries :
                        self.dump_httplib_headers(_credentials_list)
                        raise CldOpsException("The Cloud's API is misbehaving", 1485)
                    _errmsg = "get_instances"

                    _instance = self.get_instances(obj_attr_list)
                    if not _instance :
                        if firsttime :
                            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                        break

                    if _instance.state in [ NodeState.PENDING, NodeState.STOPPED ] :
                        if _instance.state == NodeState.STOPPED :
                            cbdebug("Instance " + obj_attr_list["name"] + " (" + _instance.name + ") is stopped. CB will not destroy stopped instances, but we have sent a power on request. If it is still not online, please investigate why it is stopped.", True)
                            self.get_adapter(_credentials_list).ex_power_on_node(_instance)
                        else :
                            cbdebug("Instance " + obj_attr_list["name"] + " (" + _instance.name + ") still has a pending event. Waiting to destroy...", True)
                        _wait = self.backoff(obj_attr_list, _wait)
                        _curr_tries += 1
                        continue

                    try :
                        if firsttime :
                            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs

                        self.get_adapter(_credentials_list).destroy_node(_instance)

                        if firsttime :
                            obj_attr_list["mgt_902_deprovisioning_request_sent"] = int(time()) - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])

                        firsttime = False
                    except BaseHTTPError as e :
                        if e.code == 404 :
                            cbwarn("404: Not trusting instance " + obj_attr_list["name"] + " error status... Will try again.", True)
                        self.dump_httplib_headers(_credentials_list)
                        raise CldOpsException("The Cloud's API is misbehaving, code: " + str(e.code), 1484)
                    except MalformedResponseError as e :
                        self.dump_httplib_headers(_credentials_list)
                        raise CldOpsException("The Cloud's API is misbehaving", 1483)
                    except Exception as e :
                        for line in traceback.format_exc().splitlines() :
                            cbwarn(line, True)
                        self.dump_httplib_headers(_credentials_list)

                    _msg = "Inside destroy. " + _errmsg
                    _msg += " after " + str(_curr_tries) + " attempts. Will retry in " + str(_wait) + " seconds."
                    cbdebug(_msg)
                    _wait = self.backoff(obj_attr_list, _wait)
                    _curr_tries += 1
                    cbdebug("Next try...")

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = _time_mark_drc - _time_mark_drs

            _status, _fmsg = self.vvdestroy(obj_attr_list, self.get_adapter(_credentials_list))

            obj_attr_list["last_known_state"] = "vm destoyed"

            self.post_vmdelete_process(obj_attr_list, _local_conn)

            self.take_action_if_requested("VM", obj_attr_list, "deprovision_finished")

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as msg :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
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

            _credentials_list = obj_attr_list["credentials_list"]
            self.connect(_credentials_list)

            _instance = self.get_instances(obj_attr_list)

            if _instance :

                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["image"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                self.common_messages("VM", obj_attr_list, "capturing", 0, '')

                self.get_adapter(_credentials_list).create_image(_instance, obj_attr_list["captured_image_name"])

                _capture_image_id = None
                _vm_image_created = False
                _image_instance = False

                while not _vm_image_created and _curr_tries < _max_tries :

                    if not _capture_image_id :
                        for _image in self.repopulate_images(obj_attr_list) :
                            if _image.name == obj_attr_list["captured_image_name"] :
                                _image_instance = _image
                                _capture_image_id = _image.id
                                break
                    else :
                        _image_instance = self.get_adapter(_credentials_list).get_image(_capture_image_id)

                    if _image_instance  :
                        _vm_image_created = True
                        _time_mark_crc = int(time())
                        obj_attr_list["mgt_103_capture_request_completed"] = _time_mark_crc - _time_mark_crs
                        break

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
            else :
                _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)

        finally :
            _status, _msg = self.common_messages("VM", obj_attr_list, "captured", _status, _fmsg)
            return _status, _msg

    def vmrunstate_do(self, instance, credentials_list, obj_attr_list) :
        '''
        TBD
        '''
        _ts = obj_attr_list["target_state"]
        _cs = obj_attr_list["current_state"]

        if instance :
            if _ts == "fail" :
                self.get_adapter(credentials_list).ex_shutdown_node(instance)
            elif _ts == "save" :
                self.get_adapter(credentials_list).ex_shutdown_node(instance)
            elif (_ts == "attached" or _ts == "resume") and _cs == "fail" :
                self.get_adapter(credentials_list).ex_power_on_node(instance)
            elif (_ts == "attached" or _ts == "restore") and _cs == "save" :
                self.get_adapter(credentials_list).ex_power_on_node(instance)

    def vmrunstate(self, obj_attr_list) :
        '''
        TBD
        '''
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        try :
            _ts = obj_attr_list["target_state"]
            _cs = obj_attr_list["current_state"]

            _credentials_list = obj_attr_list["credentials_list"]
            self.connect(_credentials_list)

            _curr_tries = 0
            _wait = int(obj_attr_list["update_frequency"])
            self.common_messages("VM", obj_attr_list, "runstate altering", 0, '')

            firsttime = True
            _time_mark_rrs = int(time())
            _instance = False
            while True :
                _errmsg = "get_instances"
                cbdebug("Getting instance...")
                _instance = self.get_instances(obj_attr_list)

                _curr_tries += 1
                _msg = "Inside runstate: " + _errmsg
                _msg += " after " + str(_curr_tries) + " attempts. Will retry in " + str(_wait) + " seconds."
                cbdebug(_msg)

                if (_ts in ["fail", "save"] and _instance.state != NodeState.STOPPED) or (_ts in ["attached", "resume", "restore"] and _instance.state != NodeState.RUNNING) :
                    try :
                        if firsttime :
                            if "mgt_201_runstate_request_originated" not in obj_attr_list :
                                obj_attr_list["mgt_201_runstate_request_originated"] = _time_mark_rrs
                        self.vmrunstate_do(_instance, _credentials_list, obj_attr_list)
                        if firsttime :
                            obj_attr_list["mgt_202_runstate_request_sent"] = int(time()) - int(obj_attr_list["mgt_201_runstate_request_originated"])
                        firsttime = False
                    except Exception as e :
                        for line in traceback.format_exc().splitlines() :
                            cbwarn(line, True)
                        self.dump_httplib_headers(obj_attr_list["credentials_list"])

                    cbdebug(self.get_description() + " request still not complete. Will try again momentarily...", True)
                    sleep(_wait)
                    continue

                break

            if "mgt_201_runstate_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_201_runstate_request_originated"] = _time_mark_rrs

            if "mgt_202_runstate_request_sent" not in obj_attr_list :
                obj_attr_list["mgt_202_runstate_request_sent"] = int(time()) - int(obj_attr_list["mgt_201_runstate_request_originated"])

            _time_mark_rrc = int(time())
            obj_attr_list["mgt_203_runstate_request_completed"] = _time_mark_rrc - _time_mark_rrs

            _msg = "VM " + obj_attr_list["name"] + " runstate request completed."
            cbdebug(_msg)

            _status = 0

        except CldOpsException as obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(obj_attr_list["credentials_list"])
            _status = 23
            _fmsg = str(e)

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
        _credentials_list = False
        try :
            _status = 100
            _image_instance = False

            _fmsg = "An error has occurred, but no error message was captured"

            self.common_messages("IMG", obj_attr_list, "deleting", 0, '')

            _credentials_list = self.rotate_token(obj_attr_list["cloud_name"])

            obj_attr_list["credentials_list"] = _credentials_list

            self.connect(_credentials_list, obj_attr_list)

            _image_instance = self.get_images(obj_attr_list)

            if _image_instance :

                _x = obj_attr_list["imageid1"]
                obj_attr_list["imageid1"] = _image_instance.id

                self.get_adapter(_credentials_list).delete_image(_image_instance)

                _wait = int(obj_attr_list["update_frequency"])
                _curr_tries = 0
                _max_tries = int(obj_attr_list["update_attempts"])

                _image_deleted = False

                while not _image_deleted and _curr_tries < _max_tries :

                    _image_instance = self.get_images(obj_attr_list, False)

                    if not _image_instance :
                        _image_deleted = True
                    else :
                        sleep(_wait)
                        _curr_tries += 1

                obj_attr_list["imageid1"] = _x

            _status = 0

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(_credentials_list)
            _status = 23
            _fmsg = str(e)

        finally :
            _status, _msg = self.common_messages("IMG", obj_attr_list, "deleted", _status, _fmsg)
            return _status, _msg

    @trace
    def aidefine(self, obj_attr_list, current_step) :
        '''
        TBD
        '''
        lock = False
        credentials_list = False
        try :
            if current_step == "provision_originated" :
                credentials_list = self.rotate_token(obj_attr_list["cloud_name"])
                tenant = credentials_list.split(":")[0]
                obj_attr_list["tenant"] = tenant
                obj_attr_list["credentials_list"] = credentials_list
                self.osci.pending_object_set(obj_attr_list["cloud_name"], "AI", \
                    obj_attr_list["uuid"], "credentials_list", credentials_list)

                # Cache libcloud objects for this daemon / process before the VMs are attached
                self.connect(credentials_list, obj_attr_list)

            _fmsg = "An error has occurred, but no error message was captured"

            self.take_action_if_requested("AI", obj_attr_list, current_step)

            _status = 0

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            self.dump_httplib_headers(credentials_list)
            _status = 23
            _fmsg = str(e)

        finally :
            if lock :
                self.unlock(obj_attr_list["cloud_name"], "AI", obj_attr_list["uuid"], lock)
            if _status :
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on " + self.get_description() + " \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on " + self.get_description() + " \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

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
    def get_real_driver(self, who) :
        return get_driver(getattr(Provider, who))

    @trace
    def get_my_driver(self, obj_attr_list) :
        return self.get_adapter(obj_attr_list["credentials_list"])

    @trace
    def repopulate_images(self, obj_attr_list) :
        if not LibcloudCmds.global_images :
            LibcloudCmds.imagelist = []

        if not len(LibcloudCmds.imagelist) :
            if self.target_location :
                LibcloudCmds.imagelist = self.get_my_driver(obj_attr_list).list_images(**self.imglist_kwargs)
            else :
                LibcloudCmds.imagelist = self.get_my_driver(obj_attr_list).list_images()

        return LibcloudCmds.imagelist

    @trace
    def repopulate_keys(self, obj_attr_list) :
        LibcloudCmds.keys[obj_attr_list["credentials_list"]] = self.get_my_driver(obj_attr_list).list_key_pairs()

    @trace
    def rotate_token(self, cloud_name) :
        '''
        TBD
        '''
        vmc_defaults = self.osci.get_object(cloud_name, "GLOBAL", False, "vmc_defaults", False)
        _credentials_lists = vmc_defaults["credentials"].split(";")
        lock = self.lock(cloud_name, "VMC", "shared_access_token_counter", "credentials_list")

        assert(lock)

        current_token = 0 if "current_token" not in vmc_defaults else int(vmc_defaults["current_token"])
        new_token = current_token

        if len(_credentials_lists) > 1 :
            new_token += 1
            if new_token == len(_credentials_lists) :
                new_token = 0

        self.osci.update_object_attribute(cloud_name, "GLOBAL", "vmc_defaults", False, "current_token", str(new_token))
        self.unlock(cloud_name, "VMC", "shared_access_token_counter", lock)

        return _credentials_lists[current_token]
