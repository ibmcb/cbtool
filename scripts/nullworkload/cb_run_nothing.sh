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
	syslog_netcat "Usage: cb_run_nothing.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

CMDLINE="sleep ${LOAD_DURATION}"

syslog_netcat "Benchmarking nullworkload SUT: TINYVM=${my_ip_addr} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=`mktemp`

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"
if [ x"${log_output_command}" == x"true" ]; then
	syslog_netcat "Command output will be shown"
	$CMDLINE | while read line ; do
		syslog_netcat "$line"
		echo $line >> $OUTPUT_FILE
	done
else
	syslog_netcat "Command output will NOT be shown"
	$CMDLINE 2>&1 >> $OUTPUT_FILE
fi

syslog_netcat "nullworkload run complete. Will collect and report the results"

bw=`echo "$LOAD_ID*3.14 + 3.14" | bc`
tp=`echo "$LOAD_ID*2.78 + 2.78" | bc`
lat=`echo "$LOAD_ID*0.577 + 0.577" | bc`

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum load_profile:${LOAD_PROFILE}:name load_level:${LOAD_LEVEL}:load load_duration:${LOAD_DURATION}:sec bandwidth:${bw}:mbps throughput:${tp}:tps latency:${lat}:msec

rm ${OUTPUT_FILE}

exit 0
