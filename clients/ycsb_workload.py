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

#--------------------------------- START CB API --------------------------------

from sys import path, argv
from time import sleep

import fnmatch
import os
import pwd

home = os.environ["HOME"]
username = pwd.getpwuid(os.getuid())[0]

api_file_name = "/tmp/cb_api_" + username
if os.access(api_file_name, os.F_OK) :    
    try :
        _fd = open(api_file_name, 'r')
        _api_conn_info = _fd.read()
        _fd.close()
    except :
        _msg = "Unable to open file containing API connection information "
        _msg += "(" + api_file_name + ")."
        print(_msg)
        exit(4)
else :
    _msg = "Unable to locate file containing API connection information "
    _msg += "(" + api_file_name + ")."
    print(_msg)
    exit(4)

_path_set = False

for _path, _dirs, _files in os.walk(os.path.abspath(path[0] + "/../")):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        if _path.count("/lib/auxiliary") :
            path.append(_path.replace("/lib/auxiliary",''))
            _path_set = True
            break
    if _path_set :
        break

from lib.api.api_service_client import *

_msg = "Connecting to API daemon (" + _api_conn_info + ")..."
print(_msg)
api = APIClient(_api_conn_info)

#---------------------------------- END CB API ---------------------------------

if len(argv) < 2 :
        print("./" + argv[0] + " <cloud_name>")
        exit(1)

cloud_name = argv[1]

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
expid = "CASSANDRA_YCSB" + makeTimestamp().replace(" ", "_")

_app_name = "cassandra_ycsb"
current_load = "NA"
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
        if _cloud["name"] == cloud_name :
            _cloud_attached = True
            _cloud_model = _cloud["model"]
            break

    if not _cloud_attached :
        print("Cloud " + cloud_name + " not attached")
        exit(1)    

#-------------------------------------------------------------------------------
#
# Launch 1x YCSB, 1x Cassandra_Seed, 2x Cassandra Nodes
#
#-------------------------------------------------------------------------------
    app = api.appattach(cloud_name, _app_name)

    api.appalter(cloud_name, app["uuid"], "load_db_phase", "false")
    api.appalter(cloud_name, app["uuid"], "run_base_phase", "false")
    api.appalter(cloud_name, app["uuid"], "run_client_phase", "false")
    api.appalter(cloud_name, app["uuid"], "run_load_phase", "false")

#-------------------------------------------------------------------------------
#
# Load DB Phase
#
#-------------------------------------------------------------------------------
    if load_phase : 
        print("Loading Database Phase")
        api.appalter(cloud_name, app["uuid"], "load_db_phase", "false")

#-------------------------------------------------------------------------------
#
# Base Clinet Load
#
#-------------------------------------------------------------------------------
    if client_phase :
        api.appalter(cloud_name, app["uuid"], "run_client_phase", "true") 
        # Start Client at small load
        # Run for 100M Operations
        # Start a second Client ?
        
        # Monitor throughput / latency 
        #   + Witness Drops in throughput and/or increase in latency
        #       - Reactive : Add new shard
        
        #
        # 5 Clients -> 99% Latency is increase -> add 6th client, add a new shard 
        #
        
        #
        # Define Load : 
        #
        
        
        # Do we have a fixed load per client?
        #   Fixed ops / but increase # of threads? Load is the # of threads
        #   As soon as a clinet becomes the bottleneck add more clients
        
        # Number of ops / client
        # Number of clients are fixed
        # 10k ops / client, 
        
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
        api.appalter(cloud_name, app["uuid"], "run_client_phase", "false") 
        api.appalter(cloud_name, app["uuid"], "run_base_phase", "true")

 
#-------------------------------------------------------------------------------
# Run this loop 7 times.
#
# Run Phase
#
#-------------------------------------------------------------------------------
    if run_phase :
        for i in range(7,0,-1):
            print("Current Load : %s " % current_load) 
            time.sleep(300)
            current_load=app["load_level"]
            print("Changing Load Level")
            api.appalter(cloud_name, app["uuid"], "load_level", "800000")
            print("Adding new Client")
            api.appresize(cloud_name, app["uuid"], "ycsb", "+1")
            time.sleep(300)
            print("Adding new Cassandra Instance")
            api.appresize(cloud_name, app["uuid"], "cassandra", "+1")
            app = api.appshow(cloud_name,app["uuid"])

except APIException as obj:
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)
except Exception as msg:
    error = True
    print("Problem during experiment: " + str(msg))
finally:
    print("App.. Launched")
