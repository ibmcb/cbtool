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
import sys
from api_service_client import *
from time import sleep, time

api = APIClient("http://172.16.1.222:7070")
#api = APIClient("http://10.10.3.10:7070")

start = int(time())
expid = "daytrader_" + makeTimestamp(start).replace(" ", "_")

print "starting experiment: " + expid

try :
    '''
    Mockup of what needs to happen for CloudNet use case
    '''
    vm = None
    app = None
    error = False

    api.cldalter("time", "experiment_id", expid)

    _tmp_app = api.appinit("daytrader")
    uuid = _tmp_app["uuid"]
    print "Started an APP with uuid = " + uuid 
    for vm_uuid in _tmp_app["vms"].keys() :
        print _tmp_app["vms"][vm_uuid]["role"]
    app = api.apprun(uuid)
    print "Resumed APP with uuid = " + app["uuid"]
    print str(app)
    
    api.appalter(app["uuid"], "load_level", 20)
    

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg
except KeyboardInterrupt :
    print "Aborting this experiment."
except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    try :
        if vm is not None :
            print "Destroying VM..."
            api.vmdetach(vm["uuid"])
        if app is not None :
            print "Destroying APP.."
            api.appdetach(app["uuid"])
    except APIException, obj :
        print "Error cleaning up: (" + str(obj.status) + "): " + obj.msg
