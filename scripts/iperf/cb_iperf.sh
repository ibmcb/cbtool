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

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
	syslog_netcat "Usage: cb_iperf.sh <load profile> <load level> <load duration> <load_id>"
	exit 1
fi

LOAD_GENERATOR_IP=$(get_my_ai_attribute load_generator_ip)
LOAD_GENERATOR_TARGET_IP=$(get_my_ai_attribute load_generator_target_ip)

iperf=$(which iperf)

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

if [[ ${LOAD_PROFILE} == "udp" ]]
then
	ADDITIONAL_CLI_OPT=" -u "
else :
	ADDITIONAL_CLI_OPT=""
fi

source ~/cb_barrier.sh start

CMDLINE="$iperf -c ${LOAD_GENERATOR_TARGET_IP} -t ${LOAD_DURATION} -P ${LOAD_LEVEL} -f m ${ADDITIONAL_CLI_OPT}"

syslog_netcat "Benchmarking iperf SUT: NET_CLIENT=${LOAD_GENERATOR_IP} -> NET_SERVER=${LOAD_GENERATOR_TARGET_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=$(mktemp)

execute_load_generator "${CMDLINE}" ${OUTPUT_FILE} ${LOAD_DURATION}

syslog_netcat "iperf run complete. Will collect and report the results"

if [[ $(cat ${OUTPUT_FILE} | grep -c "\[SUM\]") -ne 0 ]]
then
	bw=$(cat ${OUTPUT_FILE} | grep SUM | awk '{ print $6 }' | tr -d ' ')
else
	bw=$(cat ${OUTPUT_FILE} | grep Mbits | awk '{ print $7 }' | tr -d ' ')
fi

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
errors:$(update_app_errors):num \
completion_time:$(update_app_completiontime):sec \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
bandwidth:$bw:Mbps \
${SLA_RUNTIME_TARGETS}

rm ${OUTPUT_FILE}

exit 0