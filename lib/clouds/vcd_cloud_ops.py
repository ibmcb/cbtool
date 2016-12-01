#!/usr/bin/env python

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
from time import time, sleep

from socket import gethostbyname

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import str2dic, DataOpsException
from lib.remote.network_functions import Nethashget

from shared_functions import CldOpsException, CommonCloudFunctions 

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState

import libcloud.security

class VcdCmds(CommonCloudFunctions) :
    '''
    TBD
    '''
    @trace
    def __init__ (self, pid, osci, expid = None) :
        '''
        TBD
        '''
        CommonCloudFunctions.__init__(self, pid, osci)
        self.pid = pid
        self.osci = osci
        self.vcdconn = False
        self.access_url = False
        self.ft_supported = False
        self.lock = False
        self.expid = expid

    @trace
    def get_description(self) :
        '''
        TBD
        '''
        return "VMware vCloud Director"

    @trace
    def connect(self, name, host, password, version) :
        '''
        TBD
        '''
        try :

            _status = 100

            libcloud.security.VERIFY_SSL_CERT = False

            _msg = "Connecting to vcloud director host " + host + " using username " + name
            _msg += " password = " + password
            _msg += " api version = " + version
            cbdebug(_msg)

            vcloud = get_driver(Provider.VCLOUD)
            _status = 110    
    
            # Assign login credentials and host information to libcloud handler
            self.vcdconn = vcloud(name, password, host=host, api_version = '1.5')
            _status = 120

            # Attempt to a connection using those login credentials
            # nodes = self.vcdconn.list_nodes()
          
            _status = 0
             
        except :
            _msg = "Error connecting to vCloud Director.  Status = " + str(_status) 
            cbdebug(_msg, True)
            cberr(_msg)

            _status = 23

        finally :
            if _status :
                _msg = "vCloud Director connection failure.  Failed to connect to host " + host + " using credentials " + name + password + " with API version " + version
                cbdebug(_msg, True)
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "vCloud Director connection successful."
                cbdebug(_msg)
                return _status, _msg
    
    @trace
    def test_vmc_connection(self, vmc_name, access, credentials, extra_info, dummy1, dummy2, dummy3) :
        '''
        TBD
        '''
        try :
            self.connect(credentials.split(";")[0], access, credentials.split(";")[1], '1.5')
                        
        except CldOpsException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            _status = 2
            raise CldOpsException(_msg, _status)

    @trace
    def vmccleanup(self, obj_attr_list) :
        '''
        TBD
        '''

        try :
            _status = 100

            if not self.vcdconn :
                _msg = "Cleaning up VMC. Making connection to vCloud Director host..."
                cbdebug(_msg)
                self.connect(obj_attr_list["credentials"].split(";")[0], obj_attr_list["access"], \
                             obj_attr_list["credentials"].split(";")[1], '1.5')

            _pre_existing_instances = False

            _msg = "Cleaning up VMC.  Looking up all running instances..."
            cbdebug(_msg)
            _reservations = self.vcdconn.list_nodes()

            _running_instances = True
            while _running_instances :
                _msg = "Cleaning up VMC.  Found running instances.  Checking to see if they were instantiated by CB..."
                cbdebug(_msg)
                _running_instances = False
                for _reservation in _reservations :
                    if _reservation.name.count("cb-" + obj_attr_list["username"]) :
                        _msg = "Cleaning up VMC.  Destroying CB instantiated node: " + _reservation.name
                        cbdebug(_msg)
                        _reservation.destroy_node(_reservation)
                        _running_instances = True
                    else :
                        _msg = "Cleaning up VMC.  Ignoring instance: " + _reservation.name
                        cbdebug(_msg)
                sleep(int(obj_attr_list["update_frequency"]))

            _msg = "All running instances on the VMC " + obj_attr_list["name"]
            _msg += " were terminated"
            cbdebug(_msg)

            sleep(int(obj_attr_list["update_frequency"])*5)

            _status = 0

        except CldOpsException, obj :
            _status = int(obj.error_code)
            _fmsg = str(obj.error_message)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["name"] + " could not be cleaned "
                _msg += "on vCloud Director Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\" : " + _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["name"] + " was successfully cleaned "
                _msg += "on vCloud Director Cloud \"" + obj_attr_list["cloud_name"] + "\""
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmcregister(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _msg = "Attempting to attach a new Virtual Machine Container..."
            cbdebug(_msg)

            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])
            
            if "cleanup_on_attach" in obj_attr_list and obj_attr_list["cleanup_on_attach"] == "True" :
                _msg = "Cleaning up container before attaching it."
                cbdebug(_msg)
                _status, _fmsg = self.vmccleanup(obj_attr_list)

            # vCloud Director doesn't reveal hostname of hypervisor host
            obj_attr_list["cloud_hostname"] = obj_attr_list["access"]
            obj_attr_list["cloud_ip"] = obj_attr_list["access"]
            
            obj_attr_list["arrival"] = int(time())

            if obj_attr_list["discover_hosts"].lower() == "true" :
                _msg = "Host discovery for VMC \"" + obj_attr_list["name"]
                _msg += "\" request, but vCloud Director does not allow it. Ignoring for now....."
                cbdebug(_msg, True)
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"
            else :
                obj_attr_list["hosts"] = ''
                obj_attr_list["host_list"] = {}
                obj_attr_list["host_count"] = "NA"

            _time_mark_prc = int(time())

            obj_attr_list["mgt_003_provisioning_request_completed"] = _time_mark_prc - _time_mark_prs

            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be registered "
                _msg += "on vCloud Director \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "registered on vCloud Director \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
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

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VMC " + obj_attr_list["uuid"] + " could not be unregistered "
                _msg += "on vCloud Director Cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VMC " + obj_attr_list["uuid"] + " was successfully "
                _msg += "unregistered on vCloud Director Cloud \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def get_ip_address(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            obj_attr_list["cloud_hostname"] = "vm" + obj_attr_list["name"].split("_")[1]
            
            obj_attr_list["prov_cloud_ip"] = obj_attr_list["instance_obj"].private_ips[0]
            obj_attr_list["run_cloud_ip"] =  obj_attr_list["instance_obj"].private_ips[0]
            # NOTE: "cloud_ip" is always equal to "run_cloud_ip"
            obj_attr_list["cloud_ip"] = obj_attr_list["run_cloud_ip"]            
            
            _msg = "Public IP = " + obj_attr_list["cloud_hostname"]
            _msg += " Private IP = " + obj_attr_list["cloud_ip"]
            cbdebug(_msg)
            _status = 0
            return True
        
        except :
            _msg = "Could not retrieve IP addresses for object " + obj_attr_list["uuid"]
            _msg += "from vCloud Director \"" + obj_attr_list["cloud_name"]
            cberr(_msg)
            raise CldOpsException(_msg, _status)

    @trace
    def get_vm_instance(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _msg = "Looking for node named " + obj_attr_list["cloud_vm_name"]
            cbdebug(_msg)

            _nodes = self.vcdconn.list_nodes()
            for _node in _nodes :
                if _node.name == obj_attr_list["cloud_vm_name"] :
                    _msg = "Found one!"
                    cbdebug(_msg)
                    obj_attr_list["instance_obj"] = _node
                    return _node
            _msg = "Did not find one."
            cbdebug(_msg)
            return False
                
        except Exception, e :
            _status = 23
            _fmsg = str(e)
            raise CldOpsException(_fmsg, _status)

    @trace
    def vmcount(self, obj_attr_list):
        '''
        TBD
        '''
        return "NA"
    
    def is_vm_running(self, obj_attr_list):
        '''
        TBD
        '''
        try :
            node = self.get_vm_instance(obj_attr_list)
            return node and node.state == NodeState.RUNNING

        except Exception, e :
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
    def vmcreate(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred when creating new vApp, but no error message was captured"
            
            obj_attr_list["cloud_vm_uuid"] = "NA"
            _instance = False
            
            obj_attr_list["cloud_vm_name"] = "cb-" + obj_attr_list["username"] 
            obj_attr_list["cloud_vm_name"] += '-' + "vm" + obj_attr_list["name"].split("_")[1]
            obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["role"]
            
            if obj_attr_list["ai"] != "none" :            
                obj_attr_list["cloud_vm_name"] += '-' + obj_attr_list["ai_name"] 

            obj_attr_list["cloud_vm_name"] = obj_attr_list["cloud_vm_name"].replace("_", "-")
            obj_attr_list["last_known_state"] = "about to connect to vCloud Director manager"
         
            credential_name = obj_attr_list["credentials"].split(";")[0]

            self.take_action_if_requested("VM", obj_attr_list, "provision_originated")

            if not self.vcdconn :
                _msg = "Connecting to VCD with username " + credential_name + " at address " + obj_attr_list["access"]
                cbdebug(_msg)

                self.connect(credential_name, obj_attr_list["access"], \
                             obj_attr_list["credentials"].split(";")[1], '1.5')

            _time_mark_prs = int(time())
            obj_attr_list["mgt_002_provisioning_request_sent"] = _time_mark_prs - int(obj_attr_list["mgt_001_provisioning_request_originated"])
            obj_attr_list["last_known_state"] = "about to send create request"

            _msg = "Attempting to create an instance of vApp "
            _msg += obj_attr_list["imageid1"]
            _msg += " on vCloud Director, creating a vm named "
            _msg += obj_attr_list["cloud_vm_name"]
            cbdebug(_msg, True)

            # Create new VCD vApp
            _msg = "...Looking for vApp in VCD Catalog named "
            _msg += obj_attr_list["imageid1"]
            cbdebug(_msg, True)

            vcd_vapp_images = self.vcdconn.list_images()
            image_to_launch = None
            _force_recustomization = False

            for t in vcd_vapp_images :
                if t.name == obj_attr_list["imageid1"] :
                    image_to_launch = t
                    _msg = "...Found vApp in VCD catalog named "
                    _msg += obj_attr_list["imageid1"]
                    cbdebug(_msg, True)

                # Allow for image name to be the VCD UUID rather than text name
                # This permits cbtool to work when there are spaces in image names
                _image_id_name = "https://" + obj_attr_list["access"] + "/api/vAppTemplate/vappTemplate-" + obj_attr_list["imageid1"]
                if t.id == _image_id_name :
                    image_to_launch = t
                    _msg = "...Found vApp in VCD catalog with name "
                    _msg += t.name
                    _msg += " with an ID corresponding to "
                    _msg += obj_attr_list["imageid1"]
                    cbdebug(_msg, True)

            if image_to_launch == None :
                # Test whether an instantiated vApp exists with the request image name.  If so, clone this Vapp.
                # This allows users who cannot add images to the VCD catalog to create and use custom images
                _msg = "Cannot find a matching vApp in VCD catalog. Searching for instantiated vApp..."
                cbdebug(_msg, True)

                image_to_launch = self.vcdconn.ex_find_node(node_name = obj_attr_list["imageid1"])

                if image_to_launch == None :
                    _msg = "Cannot find an instantiated vApp named "
                    _msg += obj_attr_list["imageid1"]
                    cbdebug (_msg, True)
                else:
                    _force_recustomization = True
                    _msg = "Found an instantiated vApp named "
                    _msg += obj_attr_list["imageid1"]
                    _msg += " Will attempt to clone this vApp."
                    cbdebug (_msg, True)

            if image_to_launch == None :
               _msg = "Error : Cannot find a vApp named "
               _msg += obj_attr_list["imageid1"]
               _msg += " in vCloud Director catalog.  Aborting."
               cberr(_msg)
               raise CldOpsException(_msg, _status)

            vm_computername = "vm" + obj_attr_list["name"].split("_")[1]
            _msg = "...Launching new vApp containing VM with hostname " + vm_computername
            cbdebug(_msg,True)
            _timeout = obj_attr_list["clone_timeout"]
            _msg = "...libcloud clone_timeout is " + _timeout
            cbdebug(_msg)

            _reservation = self.vcdconn.create_node(name = obj_attr_list["cloud_vm_name"], image = image_to_launch, ex_vm_names = [vm_computername], ex_clone_timeout = int(obj_attr_list["clone_timeout"]), ex_force_customization=_force_recustomization)

            obj_attr_list["last_known_state"] = "sent create request to vCloud Director, parsing response"

            _msg = "...Sent command to create node, waiting for creation..."
            cbdebug(_msg)

            if _reservation :

                obj_attr_list["last_known_state"] = "vm created"
                sleep(int(obj_attr_list["update_frequency"]))
                
                obj_attr_list["cloud_vm_uuid"] = _reservation.uuid
                obj_attr_list["instance_obj"] = _reservation

                _msg = "...Success. New instance UUID is " + _reservation.uuid
                cbdebug(_msg,True)

                self.take_action_if_requested("VM", obj_attr_list, "provision_started")

                _time_mark_prc = self.wait_for_instance_ready(obj_attr_list, _time_mark_prs)

                self.wait_for_instance_boot(obj_attr_list, _time_mark_prc)
                obj_attr_list["host_name"] = "unknown"

                if "instance_obj" in obj_attr_list : 
                    del obj_attr_list["instance_obj"]
                _status = 0

            else :
                obj_attr_list["last_known_state"] = "vm creation failed"
                _fmsg = "...Failed to obtain instance's (cloud-assigned) uuid. The "
                _fmsg += "instance creation failed for some unknown reason."
                cberr(_fmsg)
                _status = 100

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if "instance_obj" in obj_attr_list :
                del obj_attr_list["instance_obj"]
                
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be created "
                _msg += "on vCloud Director \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg + " (The VM creation will be rolled back)"
                cberr(_msg)
 

                if "cloud_vm_uuid" in obj_attr_list :
                    obj_attr_list["mgt_deprovisioning_request_originated"] = int(time())
                    self.vmdestroy(obj_attr_list)
                else :
                    if _instance :
                        _instance.destroy()
                raise CldOpsException(_msg, _status)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "created on vCloud Director \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def vmdestroy(self, obj_attr_list) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _time_mark_drs = int(time())
            _wait = int(obj_attr_list["update_frequency"])

            if "mgt_901_deprovisioning_request_originated" not in obj_attr_list :
                obj_attr_list["mgt_901_deprovisioning_request_originated"] = _time_mark_drs
                
            obj_attr_list["mgt_902_deprovisioning_request_sent"] = \
                _time_mark_drs - int(obj_attr_list["mgt_901_deprovisioning_request_originated"])


            credential_name = obj_attr_list["credentials"].split(";")[0]
            self.connect(credential_name, obj_attr_list["access"], \
                        obj_attr_list["credentials"].split(";")[1], '1.5')

    	    _instance = self.get_vm_instance(obj_attr_list)
            if _instance :
                _msg = "Sending a termination request for "  + obj_attr_list["name"] + ""
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ")"
                _msg += "...."
                cbdebug(_msg, True)

                _status = _instance.destroy()
                obj_attr_list["last_known_state"] = "vm destoyed"
       	        sleep(_wait)

                # Code to check if vm running isn't working yet, so won't wait for VM to be marked as not running
                #while self.is_vm_running(obj_attr_list) :
                #    sleep(_wait)

            else :
                True

            _time_mark_drc = int(time())
            obj_attr_list["mgt_903_deprovisioning_request_completed"] = \
                _time_mark_drc - _time_mark_drs
            
            _status = 0

        except CldOpsException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)
    
        finally :
            if _status :
                _msg = "VM " + obj_attr_list["uuid"] + " could not be destroyed "
                _msg += " on vCloud Director cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "destroyed on vCloud Director cloud \"" + obj_attr_list["cloud_name"]
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

            credential_name = obj_attr_list["credentials"].split(";")[0]
            if not self.vcdconn :
                self.connect(credential_name, obj_attr_list["access"], \
                             obj_attr_list["credentials"].split(";")[1], '1.5')

            _instance = self.get_vm_instance(obj_attr_list)

            if _instance :
                
                _time_mark_crs = int(time())

                # Just in case the instance does not exist, make crc = crs
                _time_mark_crc = _time_mark_crs

                obj_attr_list["mgt_102_capture_request_sent"] = _time_mark_crs - obj_attr_list["mgt_101_capture_request_originated"]

                if obj_attr_list["captured_image_name"] == "auto" :
                    obj_attr_list["captured_image_name"] = obj_attr_list["imageid1"] + "_captured_at_"
                    obj_attr_list["captured_image_name"] += str(obj_attr_list["mgt_101_capture_request_originated"])

                _msg = obj_attr_list["name"] + " capture request sent. "
                _msg += "Will capture with image name \"" + obj_attr_list["captured_image_name"] + "\"."                 
                cbdebug(_msg)

                _captured_imageid = self.vcdconn.create_image(obj_attr_list["cloud_vm_uuid"] , obj_attr_list["captured_image_name"])

                _msg = "Waiting for " + obj_attr_list["name"]
                _msg += " (cloud-assigned uuid " + obj_attr_list["cloud_vm_uuid"] + ") "
                _msg += "to be captured with image name \"" + obj_attr_list["captured_image_name"]
                _msg += "\"..."
                cbdebug(_msg, True)

                _vm_image_created = False
                while not _vm_image_created and _curr_tries < _max_tries :

                    _image_instance = self.vcdconn.get_all_images(_captured_imageid)

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
                _msg += " on vCloud Director cloud \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "VM " + obj_attr_list["uuid"] + " was successfully "
                _msg += "captured on vCloud Director cloud \"" + obj_attr_list["cloud_name"]
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
    
            credential_name = obj_attr_list["credentials"].split(";")[0]
            if not self.vcdconn :
                self.connect(credential_name, obj_attr_list["access"], \
                             obj_attr_list["credentials"].split(";")[1], '1.5')

            if "mgt_201_runstate_request_originated" in obj_attr_list :
                _time_mark_rrs = int(time())
                obj_attr_list["mgt_202_runstate_request_sent"] = \
                    _time_mark_rrs - obj_attr_list["mgt_201_runstate_request_originated"]
    
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
    def aidefine(self, obj_attr_list, current_step) :
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
                _msg = "AI " + obj_attr_list["name"] + " could not be defined "
                _msg += " on vCloud Director \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "defined on vCloud Director \"" + obj_attr_list["cloud_name"]
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
                _msg += " on vCloud Director \"" + obj_attr_list["cloud_name"] + "\" : "
                _msg += _fmsg
                cberr(_msg)
                raise CldOpsException(_status, _msg)
            else :
                _msg = "AI " + obj_attr_list["uuid"] + " was successfully "
                _msg += "undefined on vCloud Director \"" + obj_attr_list["cloud_name"]
                _msg += "\"."
                cbdebug(_msg)
                return _status, _msg
