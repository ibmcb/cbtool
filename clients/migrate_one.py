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
import re

path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/..")

from lib.api.api_service_client import *

api = APIClient("http://172.16.1.222:7070")

expid = "ft_" + makeTimestamp().replace(" ", "_")

if len(sys.argv) != 5 :
        print "./" + sys.argv[0] + " [cloud_name] [type] [role] [migrate|protect]"
        exit(1)

needed_cloud_name = sys.argv[1]
needed_type = sys.argv[2]
needed_role = sys.argv[3]
action = sys.argv[4]

print "Going to resume VM role " + needed_role + " from first saved App of type " + needed_type + "..."

try :
    error = False
    app = None
    api.cldalter(needed_cloud_name, "time", "experiment_id", "not_ready_yet")
    apps = api.applist(needed_cloud_name, "all")
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
                    vm = api.vmshow(needed_cloud_name, uuid)
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

    api.cldalter(needed_cloud_name, "time", "experiment_id", expid)

    print "Found App " + app["name"] + ". Generating scripts..."

    file1 = "/home/mrhines/ftvm/vmstatus.sh"
    file2 = "/home/mrhines/ftvm/qemudebug.sh"
    file3 = "/home/mrhines/ftvm/pingvm.sh"
    file4 = "/home/mrhines/ftvm/consolevm.sh"
    file5 = "/home/mrhines/ftvm/loginvm.sh"

    f = open(file1, 'w+')

    f.write("#!/usr/bin/env bash\n")
    f.write("sudo virsh qemu-monitor-command " + vm["cloud_vm_name"] + " --hmp --cmd \"info status\"\n")
    f.write("sudo virsh qemu-monitor-command " + vm["cloud_vm_name"] + " --hmp --cmd \"info migrate\"\n")
    f.close()
    os.chmod(file1, 0755)
    f = open(file2, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("gdb /home/mrhines/qemu/x86_64-softmmu/qemu-system-x86_64 --pid $(pgrep -f " + vm["cloud_vm_name"] + ") -ex \"handle SIGUSR2 noprint\" -ex \"\" -ex \"continue\"\n")
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

    f = open(file5, 'w+')
    f.write("#!/usr/bin/env bash\n")
    f.write("ssh klabuser@" + vm["cloud_ip"] + "\n")
    f.close()
    os.chmod(file5, 0755)

    appdetails = api.appshow(needed_cloud_name, app['uuid'])
    if appdetails["state"] == "save" :
        print "App " + app["name"] + " " + app["uuid"] + " is saved, restoring ..."
        api.apprestore(needed_cloud_name, app["uuid"])

    secs=10
    print "Wait " + str(secs) + " seconds before migrating..."
    sleep(secs)
    hosts = api.hostlist(needed_cloud_name)
    found = False 
    print "searching for 1st available host to " + action + " to..."
    for host in hosts :
        if host["cloud_hostname"] != vm["host_name"] :
            print "Migrating VM " + name + " to " + host["cloud_hostname"] + "..."
            if action == "migrate" :
                api.vmmigrate(needed_cloud_name, vm["uuid"], host["name"], vm["migrate_protocol"])
            else :
                api.vmprotect(needed_cloud_name, vm["uuid"], host["name"], vm["protect_protocol"])
            found = True
            print "Migrate complete"
    
    if not found :
        print "available host not found =("

    print "Waiting for CTRL-C..."
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
            print "Destroying application..."
            api.appdetach(needed_cloud_name, app["uuid"], True)
        except APIException, obj :
            print "Error finishing up: (" + str(obj.status) + "): " + obj.msg
