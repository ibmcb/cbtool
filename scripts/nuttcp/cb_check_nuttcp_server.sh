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

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

START=$(provision_application_start)

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

which nuttcp
if [ $? -gt 0 ] ; then
    syslog_netcat "nuttcp client/server not installed on ${SHORT_HOSTNAME} - NOK"
    exit 2
else 
    syslog_netcat "nuttcp client/server installed on ${SHORT_HOSTNAME} - OK"
    provision_application_stop $START
fi

is_nuttcp_running=$(sudo ps aux | grep nuttcp | grep -v grep | grep -v bash | grep S)
if [[ x"${is_nuttcp_running}" == x ]]
then
    syslog_netcat "Starting nuttcp server on ${SHORT_HOSTNAME}"
    sudo screen -S NUTTCPSERVER -X quit
    sudo screen -d -m -S NUTTCPSERVER
    sudo screen -p 0 -S NUTTCPSERVER -X stuff "nuttcp -S $(printf \\r)"
fi

sleep 2

is_nuttcp_listening=$(sudo netstat -tunlp | grep LISTEN | grep nuttcp)
if [[ x"${is_nuttcp_listening}" == x ]]
then
    syslog_netcat "nuttcp server is not listening on ${SHORT_HOSTNAME} - NOK"
    exit 2
else
    syslog_netcat "nuttcp server is listening on ${SHORT_HOSTNAME} - OK"
    provision_application_stop $START
    exit 0
fi