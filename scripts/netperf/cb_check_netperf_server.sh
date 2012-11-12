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

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

no_netserver=`which netserver | grep no`
if [ x"${no_netserver}" != x ]; then
	syslog_netcat "Netperf server not installed on ${SHORT_HOSTNAME} - NOK"
	exit 2
fi

is_netserver_configured=`cat /etc/services | grep netperf`
if [ x"${is_netserver_configured}" == x ]; then
	syslog_netcat "Netperf server is not configured on ${SHORT_HOSTNAME} - NOK"
	exit 2
fi

is_netserver_listening=`netstat -a | grep LISTEN | grep netperf`
if [ x"${is_netserver_listening}" == x ]; then
	syslog_netcat "Netperf server is not listening on ${SHORT_HOSTNAME} - NOK"
	exit 2
else
	syslog_netcat "Netperf server is listening on ${SHORT_HOSTNAME} - OK"
	provision_application_stop $START
	exit 0
fi