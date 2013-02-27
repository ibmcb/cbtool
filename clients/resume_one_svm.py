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
from sys import path

import os
import fnmatch

_home = os.environ["HOME"]

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from lib.api.api_service_client import *

api = APIClient("http://localhost:7070")

expid = "ft_" + makeTimestamp().replace(" ", "_")

if len(sys.argv) != 3 :
        print "./" + sys.argv[0] + " [type] [role]"
        exit(1)

needed_type = sys.argv[1]
needed_role = sys.argv[2]

print "Going to resume VM role " + needed_role + " from first saved App of type " + needed_type + "..."

try :
    error = False
    app = None
    api.cldalter("time", "experiment_id", "not_ready_yet")
    apps = api.applist("all")
    if len(apps) == 0 :
        print "No saved Apps available. Make some."
        exit(1)

    found = None
    for app in apps :
        if app["type"] == needed_type :
            found = app
            name = None
            for vm in app["vms"].split(",") :
                uuid, role, temp_name = vm.split("|")
                if role == needed_role :
                    name = temp_name
                    vm = api.vmshow(uuid)
                    break

            if name is None:
                app = None
                print needed_role + " vm not found."
                exit(1)

            break

    if not found :
        app = None
        print needed_type + " application not found."
        exit(1)

    api.cldalter("time", "experiment_id", expid)

    print "Found App " + app["name"] + ". Generating scripts..."

    file1 = "/home/mrhines/ftvm/vmstatus.sh"
    file2 = "/home/mrhines/ftvm/qemudebug.sh"
    file3 = "/home/mrhines/ftvm/pingvm.sh"
    file4 = "/home/mrhines/ftvm/consolevm.sh"
    file5 = "/home/mrhines/ftvm/replicate.sh"

    f = open(file1, 'w+')

    f.write("#!/usr/bin/env bash\n")
    f.write("sudo virsh qemu-monitor-command " + vm["cloud_vm_name"] + " --hmp --cmd \"info status\"\n")
    f.write("sudo virsh qemu-monitor-command " + vm["cloud_vm_name"] + " --hmp --cmd \"info migrate\"\n")
    f.close()
    os.chmod(file1, 0755)
    f = open(file2, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("gdb /home/mrhines/ftvm/x86_64-softmmu/qemu-system-x86_64 --pid $(pgrep -f " + vm["cloud_vm_name"] + ") -ex \"handle SIGUSR2 noprint\" -ex \"set do_event_callbacks = 0\" -ex \"set do_timer_callbacks = 1\" -ex \"continue\"\n")
    f.close()
    os.chmod(file2, 0755)

    f = open(file3, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("ping " + vm["cloud_ip"] + "\n")
    f.close()
    os.chmod(file3, 0755)

    f = open(file4, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("sudo virsh console " + vm["cloud_uuid"] + "\n")
    f.close()
    os.chmod(file4, 0755)

    appdetails = api.appshow(app['uuid'])
    if appdetails["state"] == "save" :
        print "App " + app["name"] + " " + app["uuid"] + " is saved, restoring ..."
        api.apprestore(app["uuid"])

    print "Attaching SVM to VM " + name + " ..."
    svm = api.svmattach(uuid)

    print "Attached. Waiting until CTRL-C terminate..."
    while True :
        sleep(10)

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
                print "Putting app back to sleep..."
                api.appsave(app["uuid"])
            else :
                print "Destroying application..."
                api.appdetach(app["uuid"], True)
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
