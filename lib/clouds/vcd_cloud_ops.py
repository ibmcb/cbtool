#!/usr/bin/env python3

#/*******************************************************************************
# Copyright (c) 2012 Gartner, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on Jan 7, 2013
    vCloud Director Object Operations Library
    @author: Daniel R. Bowers
'''

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from .libcloud_common import LibcloudCmds

class VcdCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              provider = "VCLOUD", \
                              num_credentials = 1, \
                              use_sizes = False, \
                              use_locations = False, \
                              verify_ssl = False, \
                             )

    # num_credentials = 1: '1' is for the password. The username is assumed to be the first parameter and is included by default as 'tenant' below.

    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, password) :
        return libcloud_driver(tenant, password, self.access, api_version = '1.5')

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "VMware VCloud"

    @trace
    def pre_vmcreate_process(self, obj_attr_list, keys) :
        self.vmcreate_kwargs["ex_create_attr"] = {}
        self.vmcreate_kwargs["ex_force_customization"] = False
        self.vmcreate_kwargs["ex_clone_timeout"] = int(obj_attr_list["clone_timeout"])
        self.vmcreate_kwargs["ex_vm_names"] = ["vm" + obj_attr_list["name"].split("_")[1]]

        _image_id_name = "https://" + obj_attr_list["access"] + "/api/vAppTemplate/vappTemplate-" + obj_attr_list["imageid1"]
        # The common code has already done a search against all image names.
        # If that failed: 
        #    Allow for image name to be the VCD UUID rather than text name
        #    This permits cbtool to work when there are spaces in image names
        #
        # Otherwise, try to clone another image.
        #
        # This is all very hacky. Please get rid of it as soon as you can and stick to
        # libcloud as close as possible. If someone doesn't have the appropriate access
        # to vCloud to perform a properly scaled benchmark, then it's really not worth supporting.

        if not obj_attr_list["image"] :
            _alternate_name = "https://" + obj_attr_list["access"] + "/api/vAppTemplate/vappTemplate-" + obj_attr_list["imageid1"]
            _force_recustomization = False

            for attempt in range(0, 2) :
                for x in self.get_images() :
                    if x.name == _alternate_name or x.id == _alternate_name :
                        obj_attr_list["image"] = x
                        break

                if obj_attr_list["image"] :
                    break

                cbdebug("Image is missing. Refreshing image list...", True)
                self.repopulate_images(obj_attr_list)

            if not obj_attr_list["image"] :
                cbdebug("Cannot find a matching vApp in VCD catalog. Searching for instantiated vApp...", True)

                image = self.get_my_driver(obj_attr_list).ex_find_node(node_name = obj_attr_list["imageid1"])

                if image is not None :
                    obj_attr_list["image"] = image
                    self.vmcreate_kwargs["ex_force_customization"] = True
                    _msg = "Found an instantiated vApp named "
                    _msg += obj_attr_list["imageid1"]
                    _msg += " Will attempt to clone this vApp."
                    cbdebug (_msg, True)

