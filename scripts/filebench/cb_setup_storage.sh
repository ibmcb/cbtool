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

START=`provision_application_start`

sudo bash -c "echo \"0\" > /proc/sys/kernel/randomize_va_space"

mount_filesystem_on_volume $FILEBENCH_DATA_DIR $FILEBENCH_DATA_FSTYP ${my_login_username} $FILEBENCH_DATA_VOLUME

syslog_netcat "Storage setup for filebench - OK"
provision_application_stop $START
exit 0
