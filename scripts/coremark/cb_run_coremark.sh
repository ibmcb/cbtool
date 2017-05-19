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

LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor 10000`
coremark=`which coremark`

declare -A CMDLINE_START

CMDLINE_PARAMS_SEEDS="0x3415 0x3415 0x66"

CMDLINE_PARAMS_ITERATIONS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
CMDLINE_PARAMS_INTERNAL="7 1 2000"

CMDLINE="$coremark ${CMDLINE_PARAMS_SEEDS} ${CMDLINE_PARAMS_ITERATIONS} ${CMDLINE_PARAMS_INTERNAL}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=`cat ${RUN_OUTPUT_FILE} | grep Sec | cut -d ":" -f 2 | tr -d ' '`
lat=`echo "\`cat ${RUN_OUTPUT_FILE} | grep time | cut -d ":" -f 2 | tr -d ' '\` * 1000 " | bc`

~/cb_report_app_metrics.py \
throughput:$tp:tps \
latency:$lat:msec \
$(common_metrics)    

unset_load_gen

exit 0
