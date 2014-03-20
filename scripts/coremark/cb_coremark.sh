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

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
	syslog_netcat "Usage: cb_coremark.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
coremark=`which coremark`

declare -A CMDLINE_START

CMDLINE_PARAMS_SEEDS="0x3415 0x3415 0x66"

CMDLINE_PARAMS_ITERATIONS[1]="100000"
CMDLINE_PARAMS_ITERATIONS[2]="200000"
CMDLINE_PARAMS_ITERATIONS[3]="500000"
CMDLINE_PARAMS_ITERATIONS[4]="1000000"
CMDLINE_PARAMS_ITERATIONS[5]="2000000"
CMDLINE_PARAMS_ITERATIONS[6]="5000000"
CMDLINE_PARAMS_ITERATIONS[7]="10000000"

CMDLINE_PARAMS_INTERNAL="7 1 2000"

ARRAY_SIZE=${#CMDLINE_PARAMS_ITERATIONS[*]}
if [ ${LOAD_LEVEL} -gt $ARRAY_SIZE ]; then
	CMDLINE="$coremark ${CMDLINE_PARAMS_SEEDS} ${CMDLINE_PARAMS_ITERATIONS[${ARRAY_SIZE}]} ${CMDLINE_PARAMS_INTERNAL}"
elif [ ${LOAD_LEVEL} -lt 1 ]; then
	CMDLINE="$coremark ${CMDLINE_PARAMS_SEEDS} ${CMDLINE_PARAMS_ITERATIONS[1]} ${CMDLINE_PARAMS_INTERNAL}"
else
	CMDLINE="$coremark ${CMDLINE_PARAMS_SEEDS} ${CMDLINE_PARAMS_ITERATIONS[${LOAD_LEVEL}]} ${CMDLINE_PARAMS_INTERNAL}"
fi

syslog_netcat "Benchmarking coremark SUT: COREMARK=${LOAD_GENERATOR_TARGET_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=`mktemp`

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"
if [ x"${log_output_command}" == x"true" ]; then
	syslog_netcat "Command output will be shown"
	$CMDLINE 2>&1 | while read line ; do
		syslog_netcat "$line"
		echo $line >> $OUTPUT_FILE
	done
else
	syslog_netcat "Command output will NOT be shown"
	$CMDLINE 2>&1 >> $OUTPUT_FILE
fi

syslog_netcat "coremark run complete. Will collect and report the results"

tp=`cat ${OUTPUT_FILE} | grep Sec | cut -d ":" -f 2 | tr -d ' '`
lat=`echo "\`cat ${OUTPUT_FILE} | grep time | cut -d ":" -f 2 | tr -d ' '\` * 1000 " | bc`

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec throughput:$tp:tps latency:$lat:msec

rm ${OUTPUT_FILE}

exit 0
