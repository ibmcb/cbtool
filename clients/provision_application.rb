#!/usr/bin/env ruby 
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


#This is a RUBY example of how to provision an Application through CloudBench
#This assumes you have already attached to a cloud through the GUI or CLI.

require 'api_service_client'

api = APIClient.new("172.16.1.222", 7070)

begin
    error = false 
    app = false 

    print "creating new Application...\n"
    app = api.appattach("SIM1", "nullworkload")

    print app["name"], "\n"

    for vm in app["vms"].split(",") do
        uuid, role, name = vm.split("|") 
        for data in api.get_latest_data("SIM1", uuid, "runtime_app_VM") do
            print data
	end
    end

    # 'app' is a dicitionary containing all the details of the VM

    print "CTRL-C to unpause...\n"
    while true do
      sleep(10)
    end

    print "destroying App...\n"
    api.appdetach("SIM1", app["uuid"])

rescue APIException => obj
    error = true 
    print "API Problem: (#{obj})\n"

rescue APINoSuchMetricException => obj
    error = true 
    print "API Problem: (#{obj})\n"

rescue SystemExit, Interrupt 
    error = true
    print "Aborting this VM.\n"

rescue Exception => e
    error = true 
    print "Problem during experiment: #{e.message}\n"

ensure
    if app 
      if error
        begin
         print "Destroying Application...\n"
	 api.appdetach("SIM1", app["uuid"])
        rescue APIException => obj
            print "Error finishing up: (#{obj})\n"
        end
      end
    end
end
