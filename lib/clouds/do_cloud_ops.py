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
                              extra = {} \
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
    def extra_vmc_setup(self, vmc_name, vmc_defaults, vm_defaults, vm_templates, connection) :
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
    def is_cloud_image_uuid(self, imageid) :
        '''
        TBD
        '''
        if len(imageid) == 8 and is_number(imageid) :
            return True

        return False

    @trace            
    def create_ssh_key(self, vmc_name, key_name, key_type, key_contents, key_fingerprint, vm_defaults, connection) :
        '''
        TBD
        '''
        connection.create_key_pair(key_name, key_type + ' ' + key_contents + " cbtool@orchestrator")        
        return True
    
    @trace
    def get_region_from_vmc_name(self, obj_attr_list) :
        '''
        TBD
        '''
        obj_attr_list["region"] = obj_attr_list["vmc_name"]

        for _location in LibcloudCmds.locations :
            if _location.id == obj_attr_list["region"] :
                return _location

        return False
    
    @trace
    def get_cloud_specific_parameters(self, obj_attr_list, extra, credentials_list, status) :
        '''
        TBD
        '''
        _mark_a = time()
        keys = []

        tmp_keys = obj_attr_list["key_name"].split(",")
        for dontcare in range(0, 2) :
            for tmp_key in tmp_keys :
                for key in LibcloudCmds.keys[credentials_list] :
                    if tmp_key in [key.name, key.extra["id"]] and key.extra["id"] not in keys and key.name not in keys :
                        keys.append(key.extra["id"])

            if len(keys) >= len(tmp_keys) :
                break

            cbdebug("Only found " + str(len(keys)) + " keys. Refreshing key list...", True)
            LibcloudCmds.keys[credentials_list] = LibcloudCmds.catalogs.cbtool[credentials_list].list_key_pairs()

        if len(keys) != len(tmp_keys) :
            raise CldOpsException("Not all SSH keys exist. Check your configuration: " + obj_attr_list["key_name"], status, True)
        self.annotate_time_breakdown(obj_attr_list, "get_sshkey_time", _mark_a)
                
        extra["ssh_keys"] = keys
        
        if obj_attr_list["netname"] == "private" :
            extra["private_networking"] = True

        obj_attr_list["libcloud_call_type"] = 1

        self.vmcreate_kwargs["ex_create_attr"] = extra        
        self.vmcreate_kwargs["ex_user_data"] = obj_attr_list["userdata"]

        return True

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "DigitalOcean Cloud"
