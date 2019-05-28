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

from time import time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number
from libcloud_common import LibcloudCmds

from shared_functions import CldOpsException

class DoCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              provider = "DIGITAL_OCEAN", \
                              num_credentials = 1, \
                              use_ssh_keys = True, \
                              use_volumes = True, \
                              tldomain = "digitalocean.com", \
                             )
    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, access_token) :
        '''
        TBD
        '''
        
        driver = libcloud_driver(access_token, api_version = 'v2')

        return driver

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
        '''
        TBD
        '''
        connection.create_key_pair(key_name, key_type + ' ' + key_contents + " cbtool@orchestrator")        
        return True
    
    @trace
    def pre_vmcreate_process(self, obj_attr_list, keys) :
        '''
        TBD
        '''

        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        for _location in LibcloudCmds.locations :
            if _location.id == obj_attr_list["region"] :
                obj_attr_list["libcloud_location_inst"] = _location
                break

        if obj_attr_list["netname"] == "private" :
            self.vmcreate_kwargs["ex_create_attr"]["private_networking"] = True

        obj_attr_list["libcloud_call_type"] = "create_node_with_mixed_arguments"

        self.vmcreate_kwargs["ex_create_attr"]["ssh_keys"] = keys
        self.vmcreate_kwargs["ex_user_data"] = obj_attr_list["userdata"]

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "DigitalOcean Cloud"
