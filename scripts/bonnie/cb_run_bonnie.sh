#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2016 DigitalOcean, Inc.

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

BONNIE_EXECUTABLE=$(sudo which bonnie)
BONNIE_DATA_DIR=$(get_my_ai_attribute_with_default bonnie_data_dir ~/btestfile)        

if [[ $LOAD_PROFILE == "default" ]]
then
    EXTRA_CMD="-r 1000 -s 2000"
else
    EXTRA_CMD=''
fi

CMDLINE="sudo $BONNIE_EXECUTABLE -d $BONNIE_DATA_DIR -c $LOAD_LEVEL -u root $EXTRA_CMD"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp_w_char=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 8)
tp_w_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 10)
tp_rw_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 12)
tp_r_char=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 14)
tp_r_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 16)
#tp_rand_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 18)

lat_w_char=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 37)
lat_w_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 38)
lat_rw_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 39)
lat_r_char=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 40)
lat_r_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 41)
lat_rand_block=$(cat ${RUN_OUTPUT_FILE} | tail -1 | cut -d ',' -f 42)

echo $tp_w_block | grep +++
is_tp_w_block_ok=$?

echo $tp_r_block | grep +++
is_tp_r_block_ok=$?

LATENCY=$(echo "scale=2; ($lat_w_block + $lat_r_block)/2" | sed 's/us//g' | sed 's/ms//g' | bc -l)

if [[ $is_tp_w_block_ok -eq 1 && $is_tp_r_block_ok -eq 1 ]]
then
    TPUT=$(echo "scale=2; ($tp_w_block + $tp_r_block)/2" | bc -l)
fi

tp_w_block=$(echo $tp_w_block | grep -v +++++)
tp_r_block=$(echo $tp_r_block | grep -v +++++)

~/cb_report_app_metrics.py \
tp_w_char:$tp_w_char:KBps \
tp_w_block:$tp_w_block:KBps \
tp_rw_block:$tp_rw_block:KBps \
tp_r_char:$tp_r_char:KBps \
tp_r_block:$tp_r_block:KBps \
$(format_for_report lat_w_char $lat_w_char) \
$(format_for_report lat_w_block $lat_w_block) \
$(format_for_report lat_rw_block $lat_rw_block) \
$(format_for_report lat_r_char $lat_r_char) \
$(format_for_report lat_r_block $lat_r_block) \
$(format_for_report lat_rand_block $lat_rand_block) \
latency:${LATENCY}:usec \
throughput:${TPUT}:ops \
$(common_metrics)    
    
unset_load_gen

exit 0
