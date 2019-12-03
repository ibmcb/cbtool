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

TRAFFIC_DIRECTION=$(get_my_ai_attribute_with_default traffic_direction r)
TRAFFIC_MSS=$(get_my_ai_attribute_with_default traffic_mss auto)
TRAFFIC_WINDOW=$(get_my_ai_attribute_with_default traffic_window auto)
RATE_LIMIT=$(get_my_ai_attribute_with_default rate_limit none)
EXTERNAL_TARGET=$(get_my_ai_attribute_with_default external_target none)

nuttcp=$(which nuttcp)

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

ADDITIONAL_CLI_OPT=""
if [[ ${LOAD_PROFILE} == "udp" ]]
then
    ADDITIONAL_CLI_OPT=" -u "
fi

if [[ $TRAFFIC_MSS != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -M $TRAFFIC_MSS "
fi

if [[ $TRAFFIC_WINDOW != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -w $TRAFFIC_WINDOW "
fi

if [[ $RATE_LIMIT != "none" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -R $RATE_LIMIT "
fi    

if [[ ${EXTERNAL_TARGET} != "none" ]]
then            
    LOAD_GENERATOR_TARGET_IP=${EXTERNAL_TARGET} 
fi            

CMDLINE="$nuttcp -$TRAFFIC_DIRECTION -T ${LOAD_DURATION} -N ${LOAD_LEVEL} ${ADDITIONAL_CLI_OPT} ${LOAD_GENERATOR_TARGET_IP}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

bw=$(cat ${RUN_OUTPUT_FILE} | awk '{ print $7 }' | tr -d ' ')

~/cb_report_app_metrics.py \
bandwidth:$bw:Mbps \
$(common_metrics)
 
unset_load_gen

exit 0
