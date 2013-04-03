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

START=`provision_application_start`
my_ip=`get_my_ip_addr`
my_role=`get_my_role`

pids="$(pgrep -f spec)"

if [ x"$pids" != x ] ; then
	syslog_netcat "killing java clients on $my_ip ($my_role)"
	for pid in $pids ; do
		kill -9 $pid
	done
else
	syslog_netcat "no java clients running on $my_ip ($my_role)"
fi
provision_application_stop $START
