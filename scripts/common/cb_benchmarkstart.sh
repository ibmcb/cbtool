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

# Disabled for scalability purposes
# refresh_hosts_file

LOAD_GENERATOR_ROLE=`get_ai_attribute ${my_ai_uuid} load_generator_role`
LOAD_GENERATOR_IP=`get_ai_attribute ${my_ai_uuid} load_generator_ip`

SCRIPT_NAME=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3

SCREEN_SESSION_NAME=s_`echo ${SCRIPT_NAME:3} | cut -d "." -f 1`d

syslog_netcat "Checking if a ${SCRIPT_NAME} script instance is still running on the AI's LOAD GENERATOR at ${LOAD_GENERATOR_IP} (${LOAD_GENERATOR_ROLE} VM)"
process_list=`ssh -i ${private_file} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no ${LOAD_GENERATOR_IP} "ps aux | grep ${SCRIPT_NAME} | grep -v benchmarkstart | grep -v grep | wc -l"`

if [ x"${process_list}" == x0 ]; then
        syslog_netcat "Removing any already running *screen session* (${SCREEN_SESSION_NAME}) on the AI's LOAD GENERATOR at ${LOAD_GENERATOR_IP} (${LOAD_GENERATOR_ROLE} VM)"
        ssh -i ${private_file} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no ${LOAD_GENERATOR_IP} "pkill -f ${SCREEN_SESSION_NAME}"
        syslog_netcat "Starting a new benchmark run on the AI's LOAD GENERATOR ${LOAD_GENERATOR_IP} (${LOAD_GENERATOR_ROLE} VM)"
        ssh -i ${private_file} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no ${LOAD_GENERATOR_IP} "screen -dmLS ${SCREEN_SESSION_NAME}; sleep 2; screen -S ${SCREEN_SESSION_NAME} -p 0 -X stuff \"~/${SCRIPT_NAME} ${LOAD_LEVEL} ${LOAD_DURATION}\"$(printf \\r)"
else
        syslog_netcat "A previous ${SCRIPT_NAME} script instance is still running on the AI's LOAD GENERATOR at ${LOAD_GENERATOR_IP} (${LOAD_GENERATOR_ROLE} VM). Will try again after ${LOAD_DURATION} seconds"        
fi
exit 0
