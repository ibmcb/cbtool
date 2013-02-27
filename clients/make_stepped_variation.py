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
The idea here is to submitter to attach a number of applications,
allow them to reach a steady state performance, 
then save the applications to disk.

This is accomplished in your cloud definitions with the following:

  [AI_DEFAULTS]
  SAVE_ON_ATTACH = $True
  SECONDS_BEFORE_SAVE = 900 # empirical delay to get warm caches

Let the submitter run for a while with this configuration and
detach it (waituntil) when you have enough applications.

Then run this script:

We use the API to resume one of the applications, and run
through a series of performance changes so that the 
"elasticity manager" can make some decisions.

Just read the API calls......they're self-explanatory.
'''
from sys import path

import fnmatch
import os

_home = os.environ["HOME"]

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from lib.api.api_service_client import *

api = APIClient("http://172.16.1.222:7070")

expid = "daytrader_" + makeTimestamp().replace(" ", "_")
print "starting experiment: " + expid

try :
    error = False
    app = None
    api.cldalter("time", "experiment_id", "not_ready_yet")
    uuids = api.applist("save", 1)
    if len(uuids) == 0 :
        print "No saved AIs available. Make some."
        exit(1)
        
    app = api.appshow(uuids[0])

    api.cldalter("time", "experiment_id", expid)

    '''
    delay = 600
    forward = range(1, 30)
    reverse = range(1, 29)
    reverse.reverse()
    for load_level in (forward + reverse):
        print "New load: " + str(load_level) + "..."
        api.appalter(app["uuid"], "load_level", load_level)
        print "Sleeping for " + str(delay) + " secs..." 
        sleep(delay)
    '''

except APIException, obj :
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg
except KeyboardInterrupt :
    print "Aborting this AI."
except Exception, msg :
    error = True
    print "Problem during experiment: " + str(msg)

finally :
    if app is not None :
        try :
            if error :
                print "Destroying application..."
                api.appdetach(app["uuid"])
            else :
                print "Putting app back to sleep..."
                api.appsave(app["uuid"])
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
