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

set_load_gen $@
    
LOAD_GENERATOR_IP=$(get_my_ai_attribute load_generator_ip)
LOAD_GENERATOR_TARGET_IP=$(get_my_ai_attribute load_generator_target_ip)

TRAFFIC_MSS=$(get_my_ai_attribute_with_default traffic_mss auto)
RATE_LIMIT=$(get_my_ai_attribute_with_default rate_limit auto)
BUFFER_LENGTH=$(get_my_ai_attribute_with_default buffer_length auto)
EXTERNAL_TARGET=$(get_my_ai_attribute_with_default external_target none)

iperf=$(which iperf)

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

ADDITIONAL_CLI_OPT=""
if [[ ${LOAD_PROFILE} == "udp" ]]
then
    ADDITIONAL_CLI_OPT=" -u "
fi

if [[ $TRAFFIC_MSS != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" --mss $TRAFFIC_MSS "
fi

if [[ $RATE_LIMIT != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -b $RATE_LIMIT "
fi    

if [[ $BUFFER_LENGTH != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -l $BUFFER_LENGTH "
fi    

if [[ ${EXTERNAL_TARGET} != "none" ]]
then            
    LOAD_GENERATOR_TARGET_IP=${EXTERNAL_TARGET} 
fi

CMDLINE="$iperf -c ${LOAD_GENERATOR_TARGET_IP} -t ${LOAD_DURATION} -P ${LOAD_LEVEL} -f m ${ADDITIONAL_CLI_OPT}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

~/cb_iperf_process.py ${RUN_OUTPUT_FILE}

~/cb_report_app_metrics.py \
bandwidth:$(cat /tmp/iperf_bw):Mbps \
jitter:$(cat /tmp/iperf_jitter):ms \
loss:$(cat /tmp/iperf_loss):pct \
$(common_metrics)    
    
unset_load_gen

exit 0
