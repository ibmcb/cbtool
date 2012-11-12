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

LOAD_LEVEL=$1
LOAD_DURATION=$2
LOAD_ID=$3

sleep ${SETUP_TIME}
report_metric "load_id" $LOAD_ID "int32" seqnum 0 all
report_metric "load" 0 "int32" load 0 all
#report_metric "throughput" 0 "float" tps 0
#report_metric "latency" 0 "float" msec 0
#report_metric "bandwidth" 0 "float" mBps 0

FILEBENCH_IP=`get_ips_from_role filebench`

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

syslog_netcat "Benchmarking filebench SUT: FILEBENCH=${FILEBENCH_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})"

OUTPUT_FILE=`mktemp`

report_metric "load" $LOAD_LEVEL "int32" load 0 all

syslog_netcat "Command line is: ${CMDLINE}"
$CMDLINE | while read line ; do
        syslog_netcat "$line"
        echo $line >> $OUTPUT_FILE
done

syslog_netcat "filebench run complete. Will collect and report the results"

report_metric "throughput" `cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 2 | tr -d ' ' | sed 's/\(.*\)...../\1/'` "float" tps 0
report_metric "latency" `cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 6 | tr -d ' ' | sed 's/\(.*\)........./\1/'` "float" msec 0
report_metric "bandwidth" `cat ${OUTPUT_FILE} | grep Summary | cut -d "," -f 4 | tr -d ' ' | sed 's/\(.*\)..../\1/'` "float" mBps 0

rm ${OUTPUT_FILE}
rm ${PERSONALITY_FILE}

exit 0