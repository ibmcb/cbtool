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

DATABASE_PATH=/tradedb
DATABASE_NAME=tradedb
RAMDISK_DEVICE=/dev/ram0
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

RAMDISK=`get_my_ai_attribute db2_on_ramdisk`
RAMDISK=`echo ${RAMDISK} | tr '[:upper:]' '[:lower:]'`

SIZE=`get_my_ai_attribute_with_default tradedb_size small`

if [[ x"${RAMDISK}" == x || x"${RAMDISK}" == "false" ]]; then
	syslog_netcat "DB2 will be run from an actual storage volume (${DATABASE_PATH}) on host ($SHORT_HOSTNAME)"
else
	syslog_netcat "Setting RAMDISK (${RAMDISK_DEVICE} for holding DB2 database ${DATABASE_NAME} on host ($SHORT_HOSTNAME)"
	sudo mkdir ${DATABASE_PATH} 
	sudo mkfs.ext4 -F /dev/ram0
	sudo mount /dev/ram0 $DATABASE_PATH
	sudo chown ${my_login_username}:${my_login_username} $DATABASE_PATH
	syslog_netcat "Copying ${DATABASE_PATH}_${SIZE} contents to ${DATABASE_PATH}"
	cp -r ${DATABASE_PATH}_${SIZE}/* ${DATABASE_PATH}
	syslog_netcat "DB2 database ${DATABASE_NAME} now on ramdisk device ${RAMDISK_DEVICE} - OK"
fi
exit 0
