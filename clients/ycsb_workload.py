#!/usr/bin/env python
#/*******************************************************************************
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

from sys import path

import fnmatch
import os

_home = os.environ["HOME"]
_api_endpoint = "10.16.31.203"
_api_port = "7070"
_cloud_name = "myopenstack"
_app_name = "cassandra_ycsb"

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
            path.append(_path.replace("/lib/auxiliary",''))
            break

from lib.api.api_service_client import *

#----------------------- TO DO -------------------------------------------------
#
# Add shards every 10 minutes... Need to update to RHEL6.5 on my client
# Add clinet as well, determine delta.
# Make time configurable. / Randomize  
# Number of shards configurable
# Time it takes to load the data in the 3 shards.
# Have Block Storage be a config option : path to device. | and commit log.
# Check centos machines..
#
#-------------------------------------------------------------------------------

#----------------------- CloudBench API ----------------------------------------
api = APIClient("http://" + _api_endpoint + ":%s" % _api_port)
expid = "CASSANDRA_YCSB" + makeTimestamp().replace(" ", "_")

load_phase = True 
client_phase =  False 
base_phase = False 
run_phase = False 

base_runtime = 180 

try : 
    error = False
    app = None
    
    _cloud_attached = False
    for _cloud in api.cldlist() :
        if _cloud["name"] == _cloud_name :
            _cloud_attached = True
            _cloud_model = _cloud["model"]
            break

    if not _cloud_attached :
        print "Cloud " + _cloud_name + " not attached"
        exit(1)    

#-------------------------------------------------------------------------------
#
# Launch 1x YCSB, 1x Cassandra_Seed, 2x Cassandra Nodes
#
#-------------------------------------------------------------------------------
    app = api.appattach(_cloud_name, _app_name)

    api.appalter(_cloud_name, app["uuid"], "load_db_phase", "false")
    api.appalter(_cloud_name, app["uuid"], "run_base_phase", "false")
    api.appalter(_cloud_name, app["uuid"], "run_client_phase", "false")
    api.appalter(_cloud_name, app["uuid"], "run_load_phase", "false")

#-------------------------------------------------------------------------------
#
# Load DB Phase
#
#-------------------------------------------------------------------------------
    if load_phase : 
        print "Loading Database Phase"
        api.appalter(_cloud_name, app["uuid"], "load_db_phase", "false")

#-------------------------------------------------------------------------------
#
# Base Clinet Load
#
#-------------------------------------------------------------------------------
    if client_phase :
        api.appalter(_cloud_name, app["uuid"], "run_client_phase", "true") 

#-------------------------------------------------------------------------------
#   Once client_phase completes, move to base_load phase.
#-------------------------------------------------------------------------------
        base_phase = True

#-------------------------------------------------------------------------------
#
# Base Load
#
#-------------------------------------------------------------------------------
    if base_phase :
        api.appalter(_cloud_name, app["uuid"], "run_client_phase", "false") 
        api.appalter(_cloud_name, app["uuid"], "run_base_phase", "true")

 
#-------------------------------------------------------------------------------
# Run this loop 7 times.
#
# Run Phase
#
#-------------------------------------------------------------------------------
    if run_phase :
        for i in range(7,0,-1):
            print "Current Load : %s " % current_load 
            time.sleep(300)
            current_load=app["load_level"]
            print "Changing Load Level"
            api.appalter(_cloud_name, app["uuid"], "load_level", "800000")
            print "Adding new Client"
            api.appresize(_cloud_name, app["uuid"], "ycsb", "+1")
            time.sleep(300)
            print "Adding new Cassandra Instance"
            api.appresize(_cloud_name, app["uuid"], "cassandra", "+1")
            app = api.appshow(_cloud_name,app["uuid"])

except APIException, obj:
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg
except Exception, msg:
    error = True
    print "Problem during experiment: " + str(msg)
finally:
    print "App.. Launched"
