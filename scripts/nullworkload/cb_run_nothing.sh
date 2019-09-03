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

CMDLINE="sleep ${LOAD_DURATION}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

FORCE_FAILURE_ON_EXECUTION=$(get_my_ai_attribute_with_default force_failure_on_execution false)
FORCE_FAILURE_ON_EXECUTION=$(echo ${FORCE_FAILURE_ON_EXECUTION} | tr '[:upper:]' '[:lower:]')

if [[ $FORCE_FAILURE_ON_EXECUTION == "false" ]]
then
    
    bw=`echo "$LOAD_ID*3.14 + 3.14" | bc`
    tp=`echo "$LOAD_ID*2.78 + 2.78" | bc`
    lat=`echo "$LOAD_ID*0.577 + 0.577" | bc`
    
    ~/cb_report_app_metrics.py \
    bandwidth:${bw}:mbps \
    throughput:${tp}:tps \
    latency:${lat}:msec \
    $(common_metrics)    
    
    unset_load_gen
    
    exit 0
else
    syslog_netcat "nullworkload run forced failure!"
    
    unset_load_gen
    
    exit 1
fi
