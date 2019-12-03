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

PACKET_SIZE=$(get_my_ai_attribute_with_default packet_size auto)
PACKET_TTL=$(get_my_ai_attribute_with_default packet_ttl auto)
EXTERNAL_TARGET=$(get_my_ai_attribute_with_default external_target none)

ping=$(which ping)

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

ADDITIONAL_CLI_OPT=""

if [[ $PACKET_SIZE != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -s $PACKET_SIZE "
fi

if [[ $PACKET_TTL != "auto" ]]
then
    ADDITIONAL_CLI_OPT=$ADDITIONAL_CLI_OPT" -t $PACKET_TTL "
fi

if [[ ${EXTERNAL_TARGET} != "none" ]]
then            
    LOAD_GENERATOR_TARGET_IP=${EXTERNAL_TARGET} 
fi            
                                    
CMDLINE="$ping -c ${LOAD_LEVEL} ${ADDITIONAL_CLI_OPT} ${LOAD_GENERATOR_TARGET_IP}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

lat=$(cat ${RUN_OUTPUT_FILE} | grep rtt | awk '{ print $4 }' | cut -d '/' -f 2 | tr -d ' ')

~/cb_report_app_metrics.py \
latency:$lat:ms \
$(common_metrics)
 
unset_load_gen

exit 0
