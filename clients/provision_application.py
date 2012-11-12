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
from time import sleep
from api_service_client import *

api = APIClient("http://172.16.1.222:7070")

try :
    error = False
    app = None

    print "creating new application..."
    app = api.appattach("nullworkload")

    print app["name"]

    # 'app' is a dicitionary containing all the details of the VMs and
    # applications the were created in the cloud

    #print "CTRL-C to unpause..."
    #while True :
    sleep(10)

    print "destroying application..."

    api.appdetach(app["uuid"])

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg

except KeyboardInterrupt :
    print "Aborting this APP."

except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    if app is not None :
        try :
            if error :
                print "Destroying application..."
                api.appdetach(app["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
