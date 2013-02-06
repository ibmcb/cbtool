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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
	syslog_netcat "Usage: cb_hadoop_job.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

is_valid_LOAD_LEVEL=0
for k in "${!tab_LOAD_LEVEL_jar[@]}"
do
	if [ "$k" -eq "$LOAD_LEVEL" ]; then
		is_valid_LOAD_LEVEL=1
	fi
done
if [ ${is_valid_LOAD_LEVEL} -eq 0 ]; then
	LOAD_LEVEL=1
fi

syslog_netcat "Benchmarking hadoop SUT: MASTER=${hadoop_master_ip} -> SLAVES=${slave_ips_csv} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

command_line="$jar_command ${tab_LOAD_LEVEL_jar[$LOAD_LEVEL]} ${tab_LOAD_LEVEL_options[$LOAD_LEVEL]}  ${tab_LOAD_LEVEL_input[$LOAD_LEVEL]} ${tab_LOAD_LEVEL_output[$LOAD_LEVEL]}"

source ~/cb_barrier.sh start

OUTPUT_FILE=`mktemp`

syslog_netcat "Command line is: ${command_line}"
if [ x"${log_output_command}" == x"true" ]; then
	syslog_netcat "Command output will be shown"
	$command_line | while read line ; do
		syslog_netcat "$line"
		echo $line >> $OUTPUT_FILE
	done
else
	syslog_netcat "Command output will NOT be shown"
	$command_line 2>&1 >> $OUTPUT_FILE
fi

syslog_netcat "..hadoop job is done. Ready to do a summary..."

#Parse and report the performace

~/cb_hadoop_report.py ${HADOOP_EXE} /user/${my_login_username}/${tab_LOAD_LEVEL_output[$LOAD_LEVEL]}/_logs/history load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec

logfile_name=`$HADOOP_EXE fs -ls /user/${my_login_username}/${tab_LOAD_LEVEL_output[$LOAD_LEVEL]}/_logs/history | grep -v ".xml" | grep -v Found | awk '{print $8}'`
syslog_netcat "....logfile_name: $logfile_name"

if [ x"${logfile_name}" != x ]; then
#       rsync ${logfile_name} $HADOOP_LOG_DEST/${logfile_name}_${LOAD_LEVEL} 
#       syslog_netcat "sending $logfile_name ${CB_NODE}:$HADOOP_LOG_DIR/${logfile_name}_${LOAD_LEVEL}" 

        short_name=${tab_LOAD_LEVEL_output[$LOAD_LEVEL]}
        filename=`$HADOOP_EXE fs -ls | grep $short_name | awk '{print $NF}'`
        if [[ $filename =~ /*/*/$short_name ]]
        then
                $HADOOP_EXE fs -rmr $filename
                syslog_netcat "---removing old dir $filename---"
        fi

else
        syslog_netcat "File $logfile_name does not exist"
fi
syslog_netcat "...hadoop job finished..."

exit 0
