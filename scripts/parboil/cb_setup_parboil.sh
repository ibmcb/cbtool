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

syslog_netcat "Checking if the parboil executable exists on ${SHORT_HOSTNAME}"
PARBOIL_DIR=$(get_my_ai_attribute_with_default parboil_dir ~)
eval PARBOIL_DIR=${PARBOIL_DIR}
PARBOIL_EXECUTABLE=${PARBOIL_DIR}/parboil

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${PARBOIL_DIR}

check_gpu_cuda

if [[ $IS_GPU -eq 0 ]]
then
    PATCH_LINE=$(grep -nri "grep cuda" $PARBOIL_DIR/common/mk | head -1 | cut -d ':' -f 2)
    comment_lines $PATCH_LINE $PARBOIL_DIR/common/mk/cuda.mk
fi

${PARBOIL_EXECUTABLE} list
if [[ $? -gt 0 ]]
then
    syslog_netcat "Can't find the parboil executable on ${SHORT_HOSTNAME} - NOK"
    exit 1
else :
    syslog_netcat "Parboil executable to be used on ${SHORT_HOSTNAME} is ${PARBOIL_EXECUTABLE} - OK"
fi
provision_application_stop $START
exit 0