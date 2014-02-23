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
	function syslog_netcat {
		echo "$1"
	}
		
	function linux_distribution {
    	IS_UBUNTU=$(cat /etc/*release | grep -c "Ubuntu")

    	if [[ ${IS_UBUNTU} -eq 1 ]]
    	then
        	export LINUX_DISTRO=1
    	fi

    	IS_REDHAT=$(cat /etc/*release | grep -c "Red Hat")    
    	if [[ ${IS_REDHAT} -ge 1 ]]
    	then
        	export LINUX_DISTRO=2
    	fi
    
    	return ${LINUX_DISTRO}
	}

	function service_stop_disable {
    	#1 - service list (space-separated list)

    	for s in $* ; do
        	syslog_netcat "Stopping service \"${s}\"..."       
        	sudo service $s stop 
        
        	if [[ ${LINUX_DISTRO} -eq 1 ]]
        	then
            	sudo bash -c "echo 'manual' > /etc/init/$s.override" 
        	fi

        	if [[ ${LINUX_DISTRO} -eq 2 ]]
        	then
            	sudo chkconfig $s off >/dev/null 2>&1
        	fi
    	done
    	/bin/true
	}

fi

syslog_netcat "Removing /etc/udev/rules.d/70-persistent-net-rules"
sudo mv /etc/udev/rules.d/70-persistent-net-rules ~
sudo touch /etc/udev/rules.d/70-persistent-net-rules

syslog_netcat "Disabling services..."
SERVICES[1]="mongodb mysql redis-server"
SERVICES[2]="mongod mysqld redis"
service_stop_disable ${SERVICES[${LINUX_DISTRO}]}

syslog_netcat "Killing all CB-related processes"
sudo pkill -9 -f cloudbenc
sudo pkill -9 -f cbtool    
sudo pkill -9 -f gmetad.py
sudo pkill -9 -f gmond
sudo pkill -9 -f rsyslog
sudo pkill -9 -f ntp
sudo pkill -9 -f redis

syslog_netcat "Removing all CB-related files"
rm ~/redis*
rm ~/__init__.py 
rm ~/barrier.py
rm ~/scp2_python_proxy.rb
rm ~/rsyslog.conf
rm ~/scp_python_proxy.sh
rm ~/monitor-core
rm ~/util
rm ~/standalone.sh; 
rm ~/ai_mapping_file.txt
rm ~/gmetad-vms.conf
rm ~/gmond-vms.conf
rm ~/ntp.conf
rm ~/rsyslog.pid
rm -rf ~/logs
rm ~/et*
rm ~/cb_*

syslog_netcat "Done"
