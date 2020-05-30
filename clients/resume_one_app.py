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

expid = "ft_" + makeTimestamp().replace(" ", "_")

try :
    error = False
    app = None
    api.cldalter(cloud_name, "time", "experiment_id", "not_ready_yet")
    uuids = api.applist(cloud_name, "save", 1)
    if len(uuids) == 0 :
        print("No saved Apps available. Make some.")
        exit(1)
        
    app = api.appshow(uuids[0])

    name = None
    for vm in app["vms"].split(",") :
        uuid, role, temp_name = vm.split("|")
        if role == "was" :
            name = temp_name
            vm = api.vmshow(cloud_name, uuid)
            break

    if name is None:
        print("WebSphere vm not found.")
        exit(1)

    api.cldalter(cloud_name, "time", "experiment_id", expid)

    print("Found App " + app["name"] + ". Generating scripts...")

    file1 = "/home/mrhines/kemari/vmstatus.sh"
    file2 = "/home/mrhines/kemari/qemudebug.sh"
    file3 = "/home/mrhines/kemari/pingvm.sh"
    file4 = "/home/mrhines/kemari/consolevm.sh"

    f = open(file1, 'w+')

    f.write("#!/usr/bin/env bash\n")
    f.write("sudo virsh qemu-monitor-command cb-mrhines-" + name + "-was --hmp --cmd \"info status\"\n")
    f.write("sudo virsh qemu-monitor-command cb-mrhines-" + name + "-was --hmp --cmd \"info migrate\"\n")
    f.close()
    os.chmod(file1, 0o755)
    f = open(file2, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("gdb /home/mrhines/kemari/x86_64-softmmu/qemu-system-x86_64 --pid $(pgrep -f " + name + ") -ex \"handle SIGUSR2 noprint\" -ex \"continue\"\n")
    f.close()
    os.chmod(file2, 0o755)

    f = open(file3, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("ping " + vm["cloud_ip"] + "\n")
    f.close()
    os.chmod(file3, 0o755)

    f = open(file4, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("sudo virsh console " + vm["cloud_uuid"] + "\n")
    f.close()
    os.chmod(file4, 0o755)

    print("Restore app " + app["name"] + " " + app["uuid"] + " ...")

    api.apprestore(cloud_name, app["uuid"])

    print("Resumed. Waiting until CTRL-C terminate...")
    while True :
        sleep(10)

except APIException as obj :
    error = True
    print("API Problem (" + str(obj.status) + "): " + obj.msg)
except KeyboardInterrupt :
    print("Aborting this APP.")
except Exception as msg :
    error = True
    print("Problem during experiment: " + str(msg))

finally :
    if app is not None :
        try :
            if error :
                print("Destroying application...")
                api.appdetach(cloud_name, app["uuid"])
            else :
                print("Putting app back to sleep...")
                api.appsave(cloud_name, app["uuid"])
        except APIException as obj :
            print("Error finishing up: (" + str(obj.status) + "): " + obj.msg)
