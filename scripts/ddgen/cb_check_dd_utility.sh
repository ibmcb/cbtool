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

DDGEN_DATA_DIR=$(get_my_ai_attribute_with_default DDGEN_data_dir /ddgentest)
DDGEN_DATA_FSTYP=$(get_my_ai_attribute_with_default DDGEN_data_fstyp ext4)

mount_filesystem_on_volume ${DDGEN_DATA_DIR} $DDGEN_DATA_FSTYP ${my_login_username}

syslog_netcat "Checking if the dd utility exists on ${SHORT_HOSTNAME}"
DD=`which dd 2>&1`
if [ $? -gt 0 ] ; then
	syslog_netcat "Can't find the dd utility on ${SHORT_HOSTNAME} - NOK"
	exit 1
else :
	syslog_netcat "dd utility to be used on ${SHORT_HOSTNAME} is $DD - OK"
fi
provision_application_stop $START
exit 0
