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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_filebench_common.sh

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
	syslog_netcat "Usage: cb_filebench.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

FILEBENCH_IP=`get_ips_from_role filebench`

filebench=`which ${FB_BINARY_NAME}`

cd ~

PERSONALITY_TEMPLATE="cb_"${LOAD_PROFILE}".f"
PERSONALITY_FILE=`mktemp`

cat ${PERSONALITY_TEMPLATE} > ${PERSONALITY_FILE}

sed -i "s/STORAGE_PATH/$STORAGE_PATH/g" ${PERSONALITY_FILE}
sed -i "s/LOAD_DURATION/$LOAD_DURATION/g" ${PERSONALITY_FILE}

source ~/cb_barrier.sh start

CMDLINE="${filebench} -f ${PERSONALITY_FILE}"

syslog_netcat "Benchmarking filebench SUT: FILEBENCH=${FILEBENCH_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=$(mktemp)

execute_load_generator "${CMDLINE}" ${OUTPUT_FILE} ${LOAD_DURATION}

COMPLETION_TIME=$?
 
syslog_netcat "filebench run complete. Will collect and report the results"

tp=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 2 | tr -d ' ' | sed 's/\(.*\)...../\1/'`
lat=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 6 | tr -d ' ' | sed 's/\(.*\)........./\1/'`
bw=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 4 | tr -d ' ' | sed 's/\(.*\)..../\1/'`

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
completion_time:${COMPLETION_TIME}:sec \
latency:$lat:msec \
throughput:$tp:tps \
bandwidth:$bw:MBps \
${SLA_RUNTIME_TARGETS}

rm ${OUTPUT_FILE}
rm ${PERSONALITY_FILE}

exit 0