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

# Used for remote-debugging. Eclipse passes "--debug_host". If there are such
# options, then do not daemonize the process so that we may connect the debugger
daemonize=" --daemon"
options="$@"
if [ x"$options" != x ] ; then
    daemonize=""
fi

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

running_subscribers=`pgrep -f ai-subscribe`

if [ x"${running_subscribers}" == x ] ; then
    syslog_netcat "Starting Subscriber"
	~/cloudbench/cbact --procid=${osprocid} --uuid=${my_ai_uuid} --operation=ai-subscribe $daemonize $options
    exit 0
else
	syslog_netcat "A Subscriber is already running"
    exit 2
fi


