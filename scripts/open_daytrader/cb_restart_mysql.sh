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
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

standalone=`online_or_offline "$1"`

if [ $standalone == offline ] ; then
	post_boot_steps offline 
fi

INSTANCE_PATH=~
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
NETSTAT_CMD=`which netstat`
SUDO_CMD=`which sudo`
ATTEMPTS=3
START=`provision_application_start`

while [ "$ATTEMPTS" -ge  0 ]
do
	syslog_netcat "Checking for MySQL instances in $SHORT_HOSTNAME...."
        ps -aux | grep -v grep | grep "mysqld" > dev/null
        if [ $? -ne 0 ]; then
		syslog_netcat "MySMySQL restarted succesfully on $SHORT_HOSTNAME - OK"
		provision_application_stop $START
		exit 0
	else 
		let ATTEMPTS=ATTEMPTS-1
		syslog_netcat "Trying to start MySQL"
		service mysqld start
	fi
done
syslog_netcat "MySQL could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
