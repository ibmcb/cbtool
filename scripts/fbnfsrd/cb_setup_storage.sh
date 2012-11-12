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

STORAGESERVER_IP=`get_ips_from_role storageserver`

syslog_netcat "Setting up filebench storage on /$STORAGE_PATH (NFS Mount from ${STORAGESERVER_IP})"

sudo bash -c "echo \"0\" > /proc/sys/kernel/randomize_va_space"

sudo mkdir -p /$STORAGE_PATH

sudo chown ${USERNAME}:${USERNAME} /$STORAGE_PATH

sudo mount -t nfs ${STORAGESERVER_IP}:/$STORAGE_PATH /$STORAGE_PATH


syslog_netcat "Storage setup for filebench - OK"
exit 0