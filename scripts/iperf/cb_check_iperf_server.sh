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

which iperf
if [ $? -gt 0 ] ; then
    syslog_netcat "iperf client/server not installed on ${SHORT_HOSTNAME} - NOK"
    exit 2
else
    syslog_netcat "iperf client/server installed on ${SHORT_HOSTNAME} - OK"
    provision_application_stop $START
fi

LOAD_PROFILE=$(get_my_ai_attribute load_profile)

is_iperfserver_running=$(sudo ps aux | grep iperf | grep -v grep | grep "\-s")
if [[ x"${is_iperfserver_running}" == x ]]
then
    syslog_netcat "Starting iperf server on ${SHORT_HOSTNAME}"
    if [[ ${LOAD_PROFILE} == "udp" ]]
    then    
        sudo screen -d -m -S IPERFSERVER bash -c "iperf -s -u"
    else
        sudo screen -d -m -S IPERFSERVER bash -c "iperf -s"
    fi
fi

if [[ ${LOAD_PROFILE} == "udp" ]]
then
    is_iperfserver_listening=$(sudo ps aux | grep iperf | grep -v grep | grep "\-s \-u")
else
    is_iperfserver_listening=$(sudo netstat -tunlp | grep LISTEN | grep iperf)
fi

if [[ x"${is_iperfserver_listening}" == x ]]
then
    syslog_netcat "iperf server is not listening on ${SHORT_HOSTNAME} - NOK"
    exit 2
else
    syslog_netcat "iperf server is listening on ${SHORT_HOSTNAME} - OK"
    provision_application_stop $START
    exit 0
fi
