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
_api_endpoint = "172.16.1.250"
_cloud_name = "TESTSIMCLOUD"
_app_name = "cassandra_ycsb"

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
            path.append(_path.replace("/lib/auxiliary",''))
            break



from lib.api.api_service_client import *
api = APIClient("http://" + _api_endpoint + ":7070")
expid = "CASSANDRA_YCSB" + makeTimestamp().replace(" ", "_")

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

    app = api.appattach(_cloud_name, _app_name)
    
except APIException, obj:
    error = True
    print "API Problem (" + str(obj.status) + "): " + obj.msg
except Exception, msg:
    error = True
    print "Problem during experiment: " + str(msg)
finally:
    print "Destroying APP.."
