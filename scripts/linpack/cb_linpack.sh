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
    syslog_netcat "Usage: cb_linpack.sh <load_profile> <load level> <load duration> <load_id>"
    exit 1
fi

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

LINPACK=`get_my_ai_attribute_with_default linpack ~/linpack/benchmarks/linpack/xlinpack_xeon64`
eval LINPACK=${LINPACK}
LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor 1000`
LINPACK_DAT='~/linpack.dat'
eval LINPACK_DAT=${LINPACK_DAT}

OUTPUT_FILE=$(mktemp)

PROBLEM_SIZES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
LEADING_DIMENSIONS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))

NUM_CPU=`cat /proc/cpuinfo | grep processor | wc -l`
export OMP_NUM_THREADS=$NUM_CPU
echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
echo "1 # number of tests" >> ${LINPACK_DAT}
echo "$PROBLEM_SIZES # problem sizes" >> ${LINPACK_DAT}
echo "$LEADING_DIMENSIONS # leading dimensions" >> ${LINPACK_DAT}
echo "2 # times to run a test " >> ${LINPACK_DAT}
echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}

CMDLINE="${LINPACK} ${LINPACK_DAT}" 

execute_load_generator "$CMDLINE" ${OUTPUT_FILE} ${LOAD_DURATION}
RESULTS=$(cat ${OUTPUT_FILE} | grep -A 1 Average | grep $PROBLEM_SIZES)
AVERAGE=$(echo $RESULTS | awk '{print $4}')
MAX=$(echo $RESULTS | awk '{print $5}')
    
~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
throughput_max:$MAX:tps \
throughput:$AVERAGE:tps \
completion_time:$(update_app_completiontime):sec \
quiescent_time:$(update_app_quiescent):sec \    
${SLA_RUNTIME_TARGETS}

exit 0