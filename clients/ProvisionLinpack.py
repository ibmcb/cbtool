#!/usr/bin/env python
#/*******************************************************************************
# Copyright (c) 2012 Red Hat.
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
This script will launch X guests at Y rate, once all guests are launched 
this script will change a field, to start load on all the guests.

Please review the cbtool/scripts/linpack/cb_linpack.sh for an example
@author Joe Talerico
'''
from time import sleep
from sys import path
from time import strftime
import os
import logging
import fnmatch
import yaml
import threading
import sys

_home = "/opt/cbtool"

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from lib.api.api_service_client import *

_api_endpoint = "172.18.0.5"
_cloud_name = "MYOPENSTACK"
_workload = "linpack"
_launch_rate = 5
_write_file = "%s" % strftime("%m%d%Y-%H:%M:%S")
_launch_until = int(sys.argv[1])
_retrun_msg = ""
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#----------------------- theThread ---------------------------------------------
#
#
#
#-------------------------------------------------------------------------------
class theThread (threading.Thread):
    def __init__(self, api, ai):
        threading.Thread.__init__(self)
        self.api = api
        self.ai = ai
    def run(self):
        _sampling(self.api,self.ai)
#----------------------- end theThread -----------------------------------------

#----------------------- _sampling ---------------------------------------------
#
#
#
#-------------------------------------------------------------------------------
def _sampling(_api, _ai) :
    check_time = None
    
    #
    # Chagne to bool, switch to false when outside of QoS
    #
    _samples = 5
    file = open("%s-workload-data"%(_write_file), "a")
    while _samples > 0  :
        _data = _api.get_latest_app_data(_cloud_name,_ai)
        if _data != None :
            if _data['time'] != check_time :
                check_time = _data['time']
                file.write("%s, %s, %s, %s\n" % (_ai, _data['time'],
                   _data['app_throughput']['val'],
                   _data['app_throughput_max']['val']))
                _samples-=1
        else: 
            continue

    file.close()
    return True
#----------------------- End _sampling -----------------------------------------

#----------------------- CloudBench API ----------------------------------------
api = APIClient("http://" + _api_endpoint + ":7070")
_launched_ais = []
app = None
try :
    error = False
    vm = None
    _cloud_attached = False
    for _cloud in api.cldlist() :
        if _cloud["name"] == _cloud_name :
            _cloud_attached = True
            _cloud_model = _cloud["model"]
            break
    if not _cloud_attached :
        print("Cloud " + _cloud_name + " not attached")
        exit(1)
    ai_return_state=True
    print("Launching AI %s" % _workload)
    vms=[]
    _launch = None
    _ignore_ai = []
    _prev_failed = []
#----------------------- AIs to ignore... since this is a new run. -------------
    for ai in api.applist(_cloud_name) :
       _ignore_ai.append([val.split("|")[0] for val in ai["vms"].split(",")][0])
#----------------------- AIs failed before our run -----------------------------
    for ai in api.applist(_cloud_name,state="failed") :
       _prev_failed.append([val.split("|")[0] for val in ai["vms"].split(",")][0])

#
# Determine Baseline For YCSB And Kmeans.
#


    _ai_list = []
    _current_ai = []
    _file = open("%s-launch-data"%(_write_file), "w")
    while ai_return_state :
        
        # Rand function to determine when to launch the next AI set.
        
        _current_ai = []
        for ai in api.applist(_cloud_name) :
           if not [val.split("|")[0] for val in ai["vms"].split(",")][0] in _ignore_ai :
              _current_ai.append([val.split("|")[0] for val in ai["vms"].split(",")][0])
#----------------------- Create Apps over time ----------------------------------
        if _launch_rate > _launch_until :
           _launch = _launch_until
        else :
           _launch = _launch_rate
        logger.info("Launching : %s guests" % _launch)
        api.appattach(_cloud_name,_workload,nosync=_launch)
#----------------------- Wait for the AIs to be launched -----------------------
        while True :
            _ai_list = []
            for ai in api.applist(_cloud_name) :
               if not [val.split("|")[0] for val in ai["vms"].split(",")][0] in _ignore_ai :
                  if not [val.split("|")[0] for val in ai["vms"].split(",")][0] in _current_ai :
                     _ai_list.append([val.split("|")[0] for val in ai["vms"].split(",")][0])
            if len(_ai_list) != _launch :
               for ai in api.applist(_cloud_name,state="failed") :
                  if not [val.split("|")[0] for val in ai["vms"].split(",")][0] in _prev_failed :
#----------------------- Failed AI ---------------------------------------------
                      logger.info("Failed to launch a AI")
               sleep(20)
            else :
               break
#----------------------- Waiting for AIs to have management data. --------------
        for vm in _ai_list :
            while True :
                    _guest_data = api.get_latest_management_data(_cloud_name,vm)
                    if _guest_data == None :
                        sleep(5)
                        continue
                    else:
                        break
#----------------------- Build a list of Guest UUIDs ---------------------------
        for vm in _ai_list :
            _guest_data = api.get_latest_management_data(_cloud_name,vm)
            if _guest_data["cloud_hostname"].find(_workload) != -1 :
                _data_uuid = _guest_data["uuid"]
            _file.write("%s ,%s, %s, %s" % (_guest_data["cloud_hostname"],
                            _guest_data["mgt_003_provisioning_request_completed"],
                            _guest_data["mgt_004_network_acessible"],
                            _guest_data["last_known_state"]))

        _launch_until = _launch_until - _launch_rate
        if _launch_until > 0 :
            sleep(20)
            ai_return_state = True
        else :
            _ai_list = _current_ai + _ai_list
            ai_return_state = False

    for app in api.applist(_cloud_name):
        if not [val.split("|")[0] for val in ai["vms"].split(",")][0] in _ignore_ai :
            api.appalter(_cloud_name, app['uuid'], 'wait_for', 1)

#----------------------- Sampling will being the workload, and begin sampling th
    threads = []
    _file.close()
    for ai in _ai_list :
        threads.append( theThread(api,ai) )
    [x.start() for x in threads]
    [x.join() for x in threads]
#----------------------- Remove existing VMs. ----------------------------------
    print("Removing all AIs")
    for apps in api.applist(_cloud_name) :
        api.appdetach(_cloud_name,apps['uuid'])

except APIException as obj :
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)

except APINoSuchMetricException as obj :
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)

except KeyboardInterrupt :
    print("Aborting this VM.")

#except Exception, msg :
#    error = True
#    print "Problem during experiment: " + str(msg)

finally :
    if app is not None :
        try :
            if error :
                print("Destroying VM...")
                api.appdetach(_cloud_name, app["uuid"])
        except APIException as obj :
            print("Error finishing up: (" + str(obj.status) + "): " + obj.msg)
