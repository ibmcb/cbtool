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

FORCE_FAILURE_ON_RESET=$(get_my_ai_attribute_with_default force_failure_on_reset false)
FORCE_FAILURE_ON_RESET=$(echo ${FORCE_FAILURE_ON_RESET} | tr '[:upper:]' '[:lower:]')

if [[ $FORCE_FAILURE_ON_RESET == "false" ]]
then
	syslog_netcat "Nothing reset on ${SHORT_HOSTNAME} - OK"
    exit 0
else
	syslog_netcat "Nothing reset FAILED on ${SHORT_HOSTNAME} - NOK"
    exit 1
fi