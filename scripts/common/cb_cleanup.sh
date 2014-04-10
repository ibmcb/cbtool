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
    NC=`which netcat` 
    if [[ $? -ne 0 ]]
    then
        NC=`which nc`
    fi

    function syslog_netcat {
        echo "$1"
    }
        
    function linux_distribution {
        IS_UBUNTU=$(cat /etc/*release | grep -c "Ubuntu")

        if [[ ${IS_UBUNTU} -ge 1 ]]
        then
            export LINUX_DISTRO=1
        fi

        IS_REDHAT=$(cat /etc/*release | grep -c "Red Hat\|CentOS\|Fedora")
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

syslog_netcat "Killing all CB-related processes..."
sudo pkill -9 -f cloud-api
sudo pkill -9 -f cloud-gui        
sudo pkill -9 -f ai-
sudo pkill -9 -f vm-
sudo pkill -9 -f submit-
sudo pkill -9 -f capture-
sudo pkill -9 -f -f gtkCBUI
sudo pkill -9 -f gmetad.py
sudo pkill -9 -f gmond
sudo pkill -9 -f rsyslog
sudo pkill -9 -f ntp
sudo pkill -9 -f redis
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