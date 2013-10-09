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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

syslog_netcat "Killing all CB-related processes"
sudo pkill -9 -f cloudbenc
sudo pkill -9 -f gmetad.py
sudo pkill -9 -f gmond
sudo pkill -9 -f rsyslog
sudo pkill -9 -f ntp
sudo pkill -9 -f redis-server 

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
#rm ~/cb_*

syslog_netcat "Done"
