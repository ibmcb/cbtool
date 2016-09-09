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
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from libcloud_common import LibcloudCmds

class DoCmds(LibcloudCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        LibcloudCmds.__init__(self, pid, osci, expid = expid, \
                              description = "DIGITAL_OCEAN", \
                              num_credentials = 1, \
                              use_ssh_keys = True, \
                              use_cloud_init = True, \
                              use_volumes = True, \
                              tldomain = "digitalocean.com", \
                              extra = {"private_networking" : True} \
                             )
    # All clouds based on libcloud should define this function.
    # It performs the initial libcloud setup.
    @trace
    def get_libcloud_driver(self, libcloud_driver, tenant, access_token) :
        driver = libcloud_driver(access_token, api_version = 'v2')
        driver.EX_CREATE_ATTRIBUTES.append("server")
        driver.EX_CREATE_ATTRIBUTES.append("management_networking")

        return driver
