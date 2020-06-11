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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

BLOCK_SIZE=`get_my_ai_attribute_with_default block_size 64k`
DATA_SOURCE=`get_my_ai_attribute_with_default data_source /dev/urandom`
DDGEN_DATA_DIR=$(get_my_ai_attribute_with_default ddgen_data_dir /ddgentest)

CMDLINE="sudo dd if=${DATA_SOURCE} of=${DDGEN_DATA_DIR}/testfile.bin oflag=direct bs=${BLOCK_SIZE} count=${LOAD_LEVEL}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}
            
cat ${RUN_OUTPUT_FILE} | grep " failed "
if [[ $? -eq 0 ]]
then
    update_app_errors 1
fi

bw=`cat ${RUN_OUTPUT_FILE} | grep copied | awk '{ print $10 }'`
unbw=`cat ${RUN_OUTPUT_FILE} | grep copied | awk '{ print $11 }'`
    
~/cb_report_app_metrics.py \
bandwidth:${bw}:${unbw} \
$(common_metrics)    
    
unset_load_gen

exit 0
