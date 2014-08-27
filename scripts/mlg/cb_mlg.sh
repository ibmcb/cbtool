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
	syslog_netcat "Usage: cb_mlg.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
MLG_HOME=~/3rd_party/mlgsrc
eval MLG_HOME=${MLG_HOME}
mlg="/usr/bin/time $MLG_HOME/mlg"

sudo su -c "echo 3 > /proc/sys/vm/drop_caches"
kb=$(cat /proc/meminfo | grep MemFree | sed "s/MemFree: \+//g" | sed "s/ kB//g")
mb=$(echo "$kb / 1024 * 0.9" | bc | sed -e "s/\..*//g")

syslog_netcat "memsize: $mb"
ARRAY_SIZE=${#CMDLINE_PARAMS_ITERATIONS[*]}
if [ ${LOAD_LEVEL} -eq 1 ]; then
	CMDLINE="$mlg -t 1 -M $mb -s 4 -a ${LOAD_PROFILE} -r 75 -n ${LOAD_DURATION}"
fi

syslog_netcat "Benchmarking mlg SUT: MLG=${LOAD_GENERATOR_TARGET_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=`mktemp`

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"
start=$(date +%s)
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
stop=$(date +%s)

syslog_netcat "mlg run complete. Will collect and report the results"

tp=`cat ${OUTPUT_FILE} | grep "1:" |  sed -e "s/\t/ /g" | sed -e "s/ \+/ /g" | cut -d " " -f 2`
((lat=stop-start))
yslog_netcat "tp: $tp lat: $lat"

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
throughput:$tp:tps \
latency:$lat:sec \
${SLA_RUNTIME_TARGETS}

rm ${OUTPUT_FILE}

exit 0
