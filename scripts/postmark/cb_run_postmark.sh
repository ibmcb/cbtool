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

POSTMARK_EXECUTABLE=$(which btest)
POSTMARK_DATA_DIR=$(get_my_ai_attribute_with_default postmark_data_dir ~/postmarkdir)        
LOAD_FACTOR=$(get_my_ai_attribute_with_default load_factor 10000)
SZ=$(get_my_ai_attribute_with_default sz 500,10000)
NR=$(get_my_ai_attribute_with_default nr 500)
SUBDIRECTORIES=$(get_my_ai_attribute_with_default subdirs 1)
READ_BS=$(get_my_ai_attribute_with_default read_bs 512)
WRITE_BS=$(get_my_ai_attribute_with_default write_bs 512)
BIAS_READ=$(get_my_ai_attribute_with_default bias_read 5)
BIAS_WRITE=$(get_my_ai_attribute_with_default bias_write 5)
BUFFERING=$(get_my_ai_attribute_with_default buffering true)

CONFIG_FILE=$(mktemp)

echo "set location $POSTMARK_DATA_DIR" >> $CONFIG_FILE
echo "set size $(echo $SZ | sed 's/,/ /g')" >> $CONFIG_FILE
echo "set number $NR" >> $CONFIG_FILE
echo "set transactions $((${LOAD_LEVEL}*${LOAD_FACTOR}))" >> $CONFIG_FILE
echo "set subdirectories ${SUBDIRECTORIES}" >> $CONFIG_FILE
echo "set read ${READ_BS}" >> $CONFIG_FILE
echo "set write ${WRITE_BS}" >> $CONFIG_FILE
echo "set bias read ${BIAS_READ}" >> $CONFIG_FILE
echo "set bias create ${BIAS_WRITE}" >> $CONFIG_FILE
echo "set buffering ${BUFFERING}" >> $CONFIG_FILE
echo "run" >> $CONFIG_FILE
echo "quit" >> $CONFIG_FILE
        
CMDLINE="sudo postmark $CONFIG_FILE"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat $RUN_OUTPUT_FILE | grep "of transactions" | cut -d '(' -f 2 | awk '{ print $1 }')
#cfps=$(cat $RUN_OUTPUT_FILE | grep created | cut -d '(' -f 2 | awk '{ print $1 }') 
#rfps=$(cat $RUN_OUTPUT_FILE | grep read | grep -v bytes | cut -d '(' -f 2 | awk '{ print $1 }')
#afps=$(cat $RUN_OUTPUT_FILE | grep appended | cut -d '(' -f 2 | awk '{ print $1 }')
#dfps=$(cat $RUN_OUTPUT_FILE | grep deleted | cut -d '(' -f 2 | awk '{ print $1 }')
rbw=$(cat $RUN_OUTPUT_FILE | grep read | grep bytes | cut -d '(' -f 2 | awk '{ print $1 }')
wbw=$(cat $RUN_OUTPUT_FILE | grep read | grep bytes | cut -d '(' -f 2 | awk '{ print $1 }') 

bw=$(echo "scale=2; ($rbw + $wbw)/1" | bc -l)

~/cb_report_app_metrics.py \
bandwidth:${bw}:mBps \
throughput:${tp}:tps \
$(common_metrics)
 
unset_load_gen

rm ${CONFIG_FILE}

exit 0
