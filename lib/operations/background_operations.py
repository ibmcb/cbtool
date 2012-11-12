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
    Created on Nov 28, 2011

    Background Object Operations Library

    @author: Marcio A. Silva
'''

from uuid import uuid5, NAMESPACE_DNS
from random import randint
from subprocess import Popen, PIPE
from time import sleep

from ..auxiliary.code_instrumentation import trace, cblog, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from ..auxiliary.data_ops import dic2str, DataOpsException
from base_operations import BaseObjectOperations
from lib.auxiliary.data_ops import str2dic, dic2str

class BackgroundObjectOperations(BaseObjectOperations) :
    '''
    TBD
    '''

    @trace    
    def background_execute(self, parameters, command) :
        '''
        TBD
        '''
        try :
            _result = {}
            _status = 100
            _smsg = ''
            _fmsg = "unknown error"
            _obj_type, _operation = command.split('-')
            _obj_type = _obj_type.upper()

            # Some small pre-processing is in order. We just need to remove the
            # word "async" from the parameter list
 
            _p_parameters = parameters.split()
            _parameters = ''
            _parallel_operations = 1
            _inter_spawn_time = False
            for _parameter in _p_parameters :
                if not _parameter.count("async") :
                    _parameters += _parameter + ' '
                else :
                    if _parameter.count('=') :
                        _x, _parallel_operations = _parameter.split('=')
                        if _parameter.count(":") :
                            _parallel_operations, _inter_spawn_time = _parallel_operations.split(':')

                        _msg = "Going to start " + _parallel_operations + " \""
                        _msg += command.replace('-','') + "\" operations in parallel. "

                        if _inter_spawn_time :
                            _msg += "Wait time between each operation is " + _inter_spawn_time + " seconds."
                        print _msg

            _obj_attr_list = {}

            # The parse_cli method is used just to get the cloud name and
            # object name.
            _status, _fmsg = self.parse_cli(_obj_attr_list, _parameters, command)

            if BaseObjectOperations.default_cloud is not None and _parameters.split()[0] != BaseObjectOperations.default_cloud :
                _parameters = BaseObjectOperations.default_cloud + ' ' + _parameters
                _status = 0


            if not _status :
                self.conn_check()

                _cloud_parameters = self.get_cloud_parameters(_obj_attr_list["cloud_name"])

                #if not command.count("detachall") :
                #    _parallel_operations = 1
 
                for _op in range(0,int(_parallel_operations)) :

                    if command.count("attach") or command.count("capture") :
                        
                        _obj_uuid = str(uuid5(NAMESPACE_DNS, str(randint(0, \
                                                                             1000000000000000000)))).upper()
                        _obj_attr_list["uuid"] = _obj_uuid
        
                        _cmd = self.path + "/cbact"
                        _cmd += " --procid=" + self.pid
                        _cmd += " --osp=" + dic2str(self.oscp)
                        _cmd += " --oop=" + ','.join(_parameters.split())
                        _cmd += " --operation=" + command
                        _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                        _cmd += " --uuid=" + _obj_uuid
                        _cmd += " --daemon"
                        #_cmd += "  --debug_host=localhost"
                        
                    elif command.count("detach") and not command.count("detachall") :
                        
                        self.pre_select_object(_obj_attr_list, _obj_type, _cloud_parameters["username"])    
                        
                        _obj_uuid = self.osci.object_exists(_obj_type, \
                                                            _obj_attr_list["name"], \
                                                            True)
    
                        if not _obj_uuid :
                            _fmsg = "Object is not instantiated on the object store."
                            _fmsg += "There is no need for explicitly detach it from "
                            _fmsg += "this experiment."
                            _status = 37
    
                        else :
                            _cmd = self.path + "/cbact"
                            _cmd += " --procid=" + self.pid
                            _cmd += " --osp=" + dic2str(self.oscp)
                            _cmd += " --oop=" + ','.join(_parameters.split())
                            _cmd += " --operation=" + command
                            _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                            _cmd += " --uuid=" + _obj_uuid
                            _cmd += " --daemon"
                            #_cmd += "  --debug_host=localhost"
    
                    elif command.count("runstate") or \
                    command.count("fail") or command.count("repair") or \
                    command.count("save") or command.count("restore") or \
                    command.count("resize") or command.count("detachall") :
    
                        if _obj_type != "HOST" :
                            _obj_uuid = self.osci.object_exists(_obj_type, \
                                                                _obj_attr_list["name"], \
                                                                True)
                        else : 
                            _obj_uuid = _obj_attr_list["name"]
    
                        if not _obj_uuid :
                            _fmsg = "Object is not instantiated on the object store."
                            _fmsg += "It cannot be captured on this experiment."
                            _status = 37
    
                        else :
                            _cmd = self.path + "/cbact"
                            _cmd += " --procid=" + self.pid
                            _cmd += " --osp=" + dic2str(self.oscp)
                            _cmd += " --oop=" + ','.join(_parameters.split())
                            _cmd += " --operation=" + command
                            _cmd += " --cn=" + _obj_attr_list["cloud_name"]
                            _cmd += " --uuid=" + _obj_uuid
                            _cmd += " --daemon"
                            #_cmd += "  --debug_host=localhost"
                    else :
                        _msg = "Unknown Operation" + command
                        _status = 100
    
                    if not _status :
                        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
        
                        if _proc_h.pid :
                                _obj_id = _obj_uuid + '-' + _operation
                                self.update_process_list(self.cn, _obj_type, \
                                                         _obj_id, \
                                                         str(_proc_h.pid), "add")
                                _smsg += "Operation \"" + command + "\" will be processed "
                                _smsg += "asynchronously, through the command \""
                                _smsg += _cmd + "\". The process id is "
                                _smsg += str(_proc_h.pid) + ".\n"
                                _status = 0
        
                        else :
                            _status = 9
                            _fmsg = "Unable to spawn a new process with the command line \""
                            _fmsg += _cmd + "\". No PID was obtained."

                    if _inter_spawn_time :
                        _msg = command.replace('-','') + ' ' + str(_op + 1) + " dispatched..."
                        cbdebug(_msg, True)
                        if _op < (int(_parallel_operations) - 1) :
                            sleep(int(_inter_spawn_time))               
                            
                    _result = _obj_attr_list
                    
        except self.oscc.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Background operation execution failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Background operation execution success. " + _smsg
                cbdebug(_msg)
            return self.package(_status, _msg, _result)
        
    @trace
    def vminit(self, cloud_name, role, vmc_pool = "auto", size = "default"):
        try :
            vm = {}
            self.conn_check()
            sub_channel = self.osci.subscribe("VM", "pause_on_attach")
            info = "unknown error"
            vm = self.background_execute(cloud_name + " " + role + " " + vmc_pool + " " + size + " pause async", "vm-attach")[2]
            if not int(vm["status"]) :
                for message in sub_channel.listen() :
                    uuid, status, info = message["data"].split(";")
                    if vm["result"]["uuid"] == uuid :
                        if status == "vmready" :
                            vm["status"] = 0
                            vm["msg"] = "Successful VM initialization." 
                            vm["result"] = str2dic(info)
                            break
                        if status == "error" :
                            vm["status"] = 343 
                            vm["msg"] = "Failure in Object Storage PubSub: " + info 
                            vm["result"] = None
                            break
                            
            sub_channel.unsubscribe()
        except self.oscc.ObjectStoreMgdConnException, obj :
            vm["status"] = obj.status
            vm["info"] = str(obj)
            vm["result"] = None
        
        return vm
    
    @trace
    def vmrun(self, started_uuid):
        try :
            status = 342
            vm = {}
            self.conn_check()
            info = "unknown error"
            sub_channel = self.osci.subscribe("VM", "pause_on_attach")
            self.osci.publish_message("VM", "pause_on_attach", started_uuid + ";continue;success", 1, 3600)
            for message in sub_channel.listen() :
                uuid, status, info = message["data"].split(";")
                if started_uuid == uuid :
                    if status == "vmfinished" :
                        attrs = self.osci.get_object("VM", False, uuid, False)
                        vm = {"status" : 0, "msg" : "success", "result": attrs}
                        break
                    if status == "error" :
                        vm = {"status" : 432, "msg" : info, "result" : None}
                        break
                    
            sub_channel.unsubscribe()
        except self.oscc.ObjectStoreMgdConnException, obj :
            vm["msg"] = "Failed to run initialized VM: " + str(obj)
            vm["status"] = obj.status
            vm["result"] = None
        
        return vm

    @trace
    def appinit(self, cloud_name, type, load_level = "default", load_duration = "default", lifetime = "none", aidrs = "none"):
        try :
            app = {}
            self.conn_check()
            sub_channel = self.osci.subscribe("VM", "pause_on_attach")
            info = "unknown error"
            total = 0
            count = 0
            app = self.background_execute(cloud_name + " " + type + " " + load_level + " " + load_duration + " " + lifetime + " " + aidrs + " pause async", "ai-attach")[2]
            app["vms"] = {}
            if not int(app["status"]) :
                for message in sub_channel.listen() :
                    uuid, status, info = message["data"].split(";")
                    if app["result"]["uuid"] == uuid :
                        if status == "vmready" :
                            vm = str2dic(info)
                            if vm["uuid"] not in app["vms"] :
                                app["vms"][vm["uuid"]] = vm
                                count += 1
                            if total > 0 and count == total :
                                app["status"] = 0
                                app["msg"] = "Successful app initialization." 
                                app["result"]["vms"] = app["vms"]
                                break
                        elif status == "vmcount" :
                            total = int(info)
                        elif status == "error" :
                            app["status"] = 343 
                            app["msg"] = "Failure in Object Storage PubSub: " + info 
                            app["result"] = None
                            break
                            
            sub_channel.unsubscribe()
        except self.oscc.ObjectStoreMgdConnException, obj :
            app["status"] = obj.status
            app["info"] = str(obj)
            app["result"] = None
        
        return app 

    @trace
    def apprun(self, started_uuid):
        try :
            status = 342
            app = {}
            self.conn_check()
            info = "unknown error"
            sub_channel = self.osci.subscribe("VM", "pause_on_attach")
            self.osci.publish_message("VM", "pause_on_attach", started_uuid + ";continue;success", 1, 3600)
            for message in sub_channel.listen() :
                uuid, status, info = message["data"].split(";")
                if started_uuid == uuid :
                    if status == "appfinished" :
                        attrs = self.osci.get_object("AI", False, uuid, False)
                        app = {"status" : 0, "msg" : "success", "result": attrs}
                        break
                    if status == "error" :
                        app = {"status" : 432, "msg" : info, "result" : None}
                        break
                    
            sub_channel.unsubscribe()
        except self.oscc.ObjectStoreMgdConnException, obj :
            app["msg"] = "Failed to run initialized Application: " + str(obj)
            app["status"] = obj.status
            app["result"] = None
        
        return app 
