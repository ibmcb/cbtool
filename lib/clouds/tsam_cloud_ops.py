#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

'''
    Created on Aug 27, 2011

    TSAM Object Operations Library

    @author: Michael R. Hines, Marcio A. Silva
'''
from time import sleep
from subprocess import Popen, PIPE
from re import search

from shared_functions import CldOpsException, CommonCloudFunctions 
from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from shared_functions import CldOpsException, CommonCloudFunctions 

class TsamCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, oscp, obj_inst) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, oscp)
        self.pid = pid
        self.oscp = oscp
        self.obj_inst = obj_inst
        self.oscc = False
        self.osci = False
        self.ft_supported = False 

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "Tivoli Service Automation Manager (TSAM) Cloud."
    
    @trace
    def invoke_rest(self, obj_attr_list, operation, extra="") :
        '''
        TBD
        '''
        cmd = "java -jar " + obj_attr_list["jars_dir"] + "/tsam_rest_adapter.jar "
        cmd += operation + "Instance " + obj_attr_list["tsam_dir"] + "/src/Ticketing.properties "
        cmd += obj_attr_list["tsam_dir"] + "/" + operation + "Instance.properties CloudEvent1"
        cmd += " " + extra
        
        _msg = "TSAM REST " + operation + ": " + cmd
        cbdebug(_msg)
        
        proc_h = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        
        output = []
        if not wait_on_process(self.pid, proc_h, output) :
            _msg = "ERROR trying to " + operation + " TSAM vm: " + str(output)
            cberr(_msg)
            return 10, _msg
        
        _msg = "SUCCESS from TSAM: " + str(output)
        cbdebug(_msg)
        return 0, str(output)

    @trace
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''        
        output = self.invoke_rest(obj_attr_list, "Create")
        if not output :
            return False

        result = search(".*KEY { ServiceInstanceID = ([0-9]+), " + \
                           "IP = ([0-9]+.[0-9]+.[0-9]+.[0-9]+), " + \
                           "HOSTNAME = ([^ ]+) }.*", output)
        if result is None :
            _msg = " Failed to parse VM description from TSAM output: " + output
            cberr(_msg)
            return 10, _msg

        obj_attr_list["tsid"] = result.group(1)
        obj_attr_list["ip_addr"] = result.group(2)

        obj_attr_list["hostname"] = result.group(3) 

        _msg = " - TSAM vm description: " + obj_attr_list["tsid"] + \
                      " " + obj_attr_list["ip_addr"] + " " + obj_attr_list["hostname"]
        cbdebug(_msg)

        _msg = "Waiting " + str(obj_attr_list["boot_time"]) + " seconds for "
        _msg += obj_attr_list["uuid"] + " (" + obj_attr_list["name"] + ") to "
        _msg += "boot..."
        cbdebug(_msg)        

        sleep(float(obj_attr_list["boot_time"]))
        wait_for_network_ready(obj_attr_list, None)
        _status = 0
        return 0, str(output)

    @trace
    def vmdestroy(self, obj_attr_list) :
        if not self.invoke_rest(obj_attr_list, "Delete") :
            return 10, " "   

        return 0, " "
