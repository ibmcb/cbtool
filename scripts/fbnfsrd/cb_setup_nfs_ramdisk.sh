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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_filebench_common.sh

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

syslog_netcat "Setting RAMDISK for NFS export from host ($SHORT_HOSTNAME)"
if [ -d ${STORAGE_PATH} ]; then
    sudo mv /${STORAGE_PATH} /${STORAGE_PATH}_mdd
fi
fscreated=`mount | grep -c fbtest`
if [ x"${fscreated}" == x0 ]; then
	sudo mkdir -p /${STORAGE_PATH}
	sudo mkfs.ext4 /dev/ram0
	sudo mount /dev/ram0 /$STORAGE_PATH
	sudo chown ${my_login_username}:${my_login_username} /$STORAGE_PATH
fi

sudo bash -c "echo \"/${STORAGE_PATH} *(rw,async)\" > /etc/exports"
sudo /etc/init.d/nfs restart
syslog_netcat "RAMDISK NFS export from host ($SHORT_HOSTNAME) set up - OK"
exit 0
