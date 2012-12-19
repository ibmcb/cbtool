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

# Better way of getting absolute path instead of relative path
if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

ln -sf $dir/* ~
#ln -sf ~/cloudbench/jar/*.jar ~
rm -rf ~/cb_os_cache.txt

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

syslog_netcat "Starting generic VM post_boot configuration"
load_manager_vm_uuid=`get_my_ai_attribute load_manager_vm`

if [[ x"${my_vm_uuid}" == x"${load_manager_vm_uuid}" || x"${my_type}" == x"none" ]]
then
	start_syslog ${osportnumber}
	syslog_netcat "Local (AI) Log store started"
	start_redis ${osportnumber}
	syslog_netcat "Local (AI) Object store started"
fi

refresh_hosts_file
post_boot_executed=`get_my_vm_attribute post_boot_executed`

if [ x"${post_boot_executed}" == x"true" ]; then
	syslog_netcat "cb_post_boot.sh already executed on this VM"
else
	syslog_netcat "Executing \"post_boot_steps\" function"
	post_boot_steps online
	syslog_netcat "Updating \"post_boot_executed\" to \"true\""
	put_my_vm_attribute post_boot_executed true
fi
syslog_netcat "Ended generic VM post_boot configuration - OK"
exit 0