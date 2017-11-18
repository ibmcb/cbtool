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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

operation="ai-qemu"
daemonize=" --daemon"
options="$@"

if [ x"$options" != x ] ; then
	daemonize=""
	for pid in $(pgrep -f $operation) ; do 
		if [ $pid == $$ ] ; then 
			echo skipping $pid
			continue
		fi
		if [ $PPID == $pid ] ; then 
			echo skipping parent ssh process $pid
			continue
		fi
		kill -9 $pid
	done
fi

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

load_manager_vm=`get_my_ai_attribute load_manager_vm`

if [ x"${load_manager_vm}" == x"${my_vm_uuid}" ] ; then
	running_load_managers=`pgrep -f $operation`
	
	if [ x"${running_load_managers}" == x ] ; then
	    syslog_netcat "Starting QEMU Scraper"
            ~/${my_remote_dir}/cbact --procid=${osprocid} --uuid=${my_ai_uuid} --syslogp=${NC_PORT_SYSLOG} --syslogf=19 --syslogr=${NC_PROTO_SYSLOG} --syslogh=${NC_HOST_SYSLOG} --operation=$operation $daemonize $options
	    exit 0
	else
	    syslog_netcat "A QEMU Scraper is already running"
	    exit 2
	fi
fi
exit 0
