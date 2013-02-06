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
	syslog_netcat "Usage: cb_ddgen.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

BLOCK_SIZE=`get_my_ai_attribute_with_default block_size 64k`
DATA_SOURCE=`get_my_ai_attribute_with_default data_source /dev/urandom`
DATA_DESTINATION=`get_my_ai_attribute_with_default data_destination /root`
RUN_JUST_ONCE=`get_my_ai_attribute_with_default run_just_once false`
RUN_COUNTER_NAME=`get_my_ai_attribute_with_default run_counter_name none`

CMDLINE="sudo dd if=${DATA_SOURCE} of=${DATA_DESTINATION}/testfile.bin oflag=direct bs=${BLOCK_SIZE} count=${LOAD_LEVEL}"

syslog_netcat "Benchmarking ddgen SUT: HPCVM=${my_ip_addr} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=`mktemp`
source ~/cb_barrier.sh start

if [[ -f ~/.ranonce && "$RUN_JUST_ONCE" = "true" ]]
then
	syslog_netcat "Already run ddgen once, and \"RUN_JUST_ONCE\" parameter is set to \"true\". Will not run it again"
	sleep ${LOAD_DURATION}
else
	syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"
	if [ x"${log_output_command}" == x"true" ]; then
		syslog_netcat "Command output will be shown"
		$CMDLINE 2>&1 | while read line ; do
			syslog_netcat "$line"
			echo $line >> $OUTPUT_FILE
		done
		touch ~/.ranonce
		if [ "$RUN_COUNTER_NAME" != "none" ]
		then
			syslog_netcat "A \"run_counter_name\" (${RUN_COUNTER_NAME}) was defined for this AI. Will update its value by +1"
			ai_increment_counter ${RUN_COUNTER_NAME}
		fi
	else
		syslog_netcat "Command output will NOT be shown"
		$CMDLINE 2>&1 >> $OUTPUT_FILE
	fi
	
	syslog_netcat "ddgen run complete. Will collect and report the results"

	bw=`cat ${OUTPUT_FILE} | grep copied | awk '{ print $8 }'`
	unbw=`cat ${OUTPUT_FILE} | grep copied | awk '{ print $9 }'`
	
	report_app_metrics load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec bandwidth:${bw}:${unbw}
	
	rm ${OUTPUT_FILE}
fi
exit 0
