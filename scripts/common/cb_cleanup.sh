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

if [[ -f ~/cb_os_parameters.txt ]]
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

PERSISTENT_NET_RULES=$(find /etc/udev/rules.d/ | grep persistent-net.rules)
if [[ $? -eq 0 ]]
then
	syslog_netcat "Removing ${PERSISTENT_NET_RULES}..."	
	sudo mv $PERSISTENT_NET_RULES ~
	sudo touch $PERSISTENT_NET_RULES
	syslog_netcat "Done"
fi

CLOUD_INIT=$(find /var/lib/cloud/instances/ -maxdepth 1 -type d | grep $(hostname))
if [[ $? -eq 0 ]]
then
	syslog_netcat "Removing ${CLOUD_INIT}..."	
	sudo rm -rf $CLOUD_INIT
	sudo rm -rf /var/lib/cloud/instance
	syslog_netcat "Done"
fi

syslog_netcat "Removing all CB-related files..."
sudo rm -rf ~/redis* >/dev/null 2>&1
sudo rm -rf ~/barrier.py >/dev/null 2>&1
sudo rm -rf ~/scp2_python_proxy.rb >/dev/null 2>&1
sudo rm -rf ~/rsyslog.conf >/dev/null 2>&1
sudo rm -rf ~/scp_python_proxy.sh >/dev/null 2>&1
sudo rm -rf ~/monitor-core >/dev/null 2>&1
sudo rm -rf ~/standalone.sh >/dev/null 2>&1
sudo rm -rf ~/ai_mapping_file.txt >/dev/null 2>&1
sudo rm -rf ~/gmetad-vms.conf >/dev/null 2>&1
sudo rm -rf ~/gmond-vms.conf >/dev/null 2>&1
sudo rm -rf ~/ntp.conf >/dev/null 2>&1
sudo rm -rf ~/rsyslog.pid >/dev/null 2>&1
sudo rm -rf ~/cb_* >/dev/null 2>&1
syslog_netcat "Done"

syslog_netcat "OK"
exit 0