#!/usr/bin/env python3

#/*******************************************************************************
# Copyright (c) 2023 Akamai, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on June, 20, 2023
    Linode Object Operations Library
    @author: Michael R. Galaxy
'''

from time import time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number
from .libcloud_common import LibcloudCmds

from .shared_functions import CldOpsException
import random, string, base64

class LinCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              provider = "LINODE", \
                              num_credentials = 1, \
                              use_ssh_keys = True, \
                              use_volumes = True, \
                              tldomain = "linode.com", \
                             )
    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, access_token) :
        return libcloud_driver(access_token, api_version = '4.0')

    @trace
    def is_cloud_image_uuid(self, imageid) :
        # DigitalOcean image IDs are just integers, and can be of
        # arbitrary length. At best we can detect whether or not they
        # are integers, but the number of digits is never a guarantee.

        # DigitalOcean also supports regularly-named images.
        # Just return true unconditionally.
        return True

    @trace
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        connection.create_key_pair(key_name, key_type + ' ' + key_contents + " cbtool@orchestrator")
        return True

    @trace
    def pre_vmcreate_process(self, obj_attr_list, libcloud_connection, keys) :

        # This needs to be empty on each creation.
        # It changes from create to create, depending
        # on which tenant is used and what the userdata
        # will be.

        obj_attr_list["config_drive"] = False

        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        if "libcloud_location_inst" not in obj_attr_list :
            for _location in LibcloudCmds.locations :
                if _location.id == obj_attr_list["region"] :
                    obj_attr_list["libcloud_location_inst"] = _location
                    break

        if obj_attr_list["netname"] == "private" :
            self.vmcreate_kwargs["ex_private_ip"] = True

        obj_attr_list["libcloud_call_type"] = "create_node_with_mixed_arguments"

        if keys :
            # Most cloud providers provide for a 1-to-1 mapping at VM create time
            # between the name of the uploaded SSH key and the contents of the key.
            # Linode does not do that in their API.
            # You only get to choose from:
            # 1) Specifying the username of the Linode account, which will dump *all* SSH keys into
            #    the guest VM.
            # 2) Specifying the raw contents of the SSH key to the API, which kind
            #    of defeats the purpose of uploading your SSH keys, but oh well.
            #
            # This means to only specify *one* key, we have to re-retrieve the key
            # we are looking for.

            public_keys = []
            for keypair in LibcloudCmds.keys[obj_attr_list["credentials_list"]] :
                for key in keys :
                    if key == keypair.extra["id"] :
                        public_keys.append(keypair.public_key)
                        break

            self.vmcreate_kwargs["ex_authorized_keys"] = public_keys

            if obj_attr_list["userdata"] not in (False, None) :
                self.vmcreate_kwargs["ex_userdata"] = obj_attr_list["userdata"]

        # The linode API really, really wants a root password,
        # so just give them a random one.
        random_password = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
        random_password += ''.join(random.choice(string.ascii_uppercase) for i in range(6))
        cbdebug("Random Linode password: " + random_password, True)
        self.vmcreate_kwargs["root_pass"] = random_password

    @trace
    def get_description(self) :
        return "Linode Cloud"
