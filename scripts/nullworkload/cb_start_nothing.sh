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

syslog_netcat "Start nothing on ${SHORT_HOSTNAME}"

mount_filesystem_on_volume ${NULLWORKLOAD_BLOCK_DATA_DIR} $NULLWORKLOAD_BLOCK_DATA_FSTYP
mount_filesystem_on_memory ${NULLWORKLOAD_MEMORY_DATA_DIR} $NULLWORKLOAD_MEMORY_DATA_FSTYP 200m
mount_remote_filesystem ${NULLWORKLOAD_REMOTE_DATA_DIR} $NULLWORKLOAD_REMOTE_DATA_FSTYP $NULLWORKLOAD_FILESERVER_IP $NULLWORKLOAD_FILESERVER_PATH

syslog_netcat "Nothing started on ${SHORT_HOSTNAME} - OK"
provision_application_stop $START
exit 0
