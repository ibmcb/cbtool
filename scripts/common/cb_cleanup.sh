#!/usr/bin/env bash

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

if [[ -f /home/cloud-user/cb_os_parameters.txt ]]
then
    source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh
else
    source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_bootstrap.sh
fi
    
syslog_netcat "Killing all CB-related processes..."
blowawaypids cloud-api
blowawaypids cloud-gui        
blowawaypids ai-
blowawaypids vm-
blowawaypids submit-
blowawaypids capture-
blowawaypids -f gtkCBUI
blowawaypids gmetad.py
blowawaypids gmond
blowawaypids rsyslog
blowawaypids ntp
blowawaypids redis
syslog_netcat "Done"

syslog_netcat "Removing all CB-related files..."
rm -rf ~/redis*
rm -rf ~/__init__.py 
rm -rf ~/barrier.py
rm -rf ~/scp2_python_proxy.rb
rm -rf ~/rsyslog.conf
rm -rf ~/scp_python_proxy.sh
rm -rf ~/monitor-core
rm -rf ~/util
rm -rf ~/standalone.sh; 
rm -rf ~/ai_mapping_file.txt
rm -rf ~/gmetad-vms.conf
rm -rf ~/gmond-vms.conf
rm -rf ~/ntp.conf
rm -rf ~/rsyslog.pid
rm -rf ~/logs
rm -rf ~/et*
rm -rf ~/cb_*
syslog_netcat "Done"

syslog_netcat "OK"
exit 0
