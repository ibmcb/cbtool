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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

START=`provision_application_start`

syslog_netcat "Start storage setup for kernbench on ${SHORT_HOSTNAME}"

KERNBENCH_DATA_DIR=$(get_my_ai_attribute_with_default kernbench_data_dir /kernbench)
KERNBENCH_PATH=$(get_my_ai_attribute_with_default kernbench_path /foo)
mv $KERNBENCH_PATH/linux $KERNBENCH_DATA_DIR/
sync

syslog_netcat "Storage setup for kernbench on ${SHORT_HOSTNAME} - OK"
provision_application_stop $START
exit 0
