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

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
	syslog_netcat "Usage: cb_filebench.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

FILEBENCH_IP=`get_ips_from_role filebench`

filebench=`which ${FB_BINARY_NAME}`

cd ~

declare -A PERSONALITY

PERSONALITY[1]="cb_fileserver.f"
PERSONALITY[2]="cb_oltp_noism.f"
PERSONALITY[3]="cb_varmail.f"
PERSONALITY[4]="cb_videoserver.f"
PERSONALITY[5]="cb_webproxy.f"

ARRAY_SIZE=${#PERSONALITY[*]}
if [ ${LOAD_LEVEL} -gt $ARRAY_SIZE ]; then
	PERSONALITY_TEMPLATE=${PERSONALITY[${ARRAY_SIZE}]}
elif [ ${LOAD_LEVEL} -lt 1 ]; then
	PERSONALITY_TEMPLATE=${PERSONALITY[1]}
else
    PERSONALITY_TEMPLATE=${PERSONALITY[${LOAD_LEVEL}]}
fi

PERSONALITY_FILE=`mktemp`

cat ${PERSONALITY_TEMPLATE} > ${PERSONALITY_FILE}

sed -i "s/STORAGE_PATH/$STORAGE_PATH/g" ${PERSONALITY_FILE}
sed -i "s/LOAD_DURATION/$LOAD_DURATION/g" ${PERSONALITY_FILE}

CMDLINE="${filebench} -f ${PERSONALITY_FILE}"

syslog_netcat "Benchmarking filebench SUT: FILEBENCH=${FILEBENCH_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=`mktemp`

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}"
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

#is_filebench_running="true"

#while [ x"${is_filebench_running}" != x ]
#do
#	is_filebench_running=`pgrep -f "${CMDLINE}"`
#	sleep 5
#done
 
syslog_netcat "filebench run complete. Will collect and report the results"

tp=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 2 | tr -d ' ' | sed 's/\(.*\)...../\1/'`
lat=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 6 | tr -d ' ' | sed 's/\(.*\)........./\1/'`
bw=`cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 4 | tr -d ' ' | sed 's/\(.*\)..../\1/'`

report_app_metrics load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec latency:$lat:msec throughput:$tp:tps bandwidth:$bw:MBps

rm ${OUTPUT_FILE}
rm ${PERSONALITY_FILE}

exit 0
