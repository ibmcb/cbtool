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

syslog_netcat "$0 started..."

# parse the loadlevel and launch the job
loadlevel=$1
load_duration=$2
LOAD_ID=$3

# get the hadoop option from the datastore
get_last_from_list $REDIS_OPT_LIST 
hadoop_job_options=`echo ${last_elem} | cut -d":" -f 1`
attempt_counter=`echo ${last_elem} | cut -d":" -f 2`
syslog_netcat "hadoop_job_options: ${hadoop_job_options} , attempt_counter: ${attempt_counter}"
if [ x"${hadoop_job_options}" == x ] ; then
	if [ x"${attempt_counter}" == x ] ; then
		syslog_netcat "${REDIS_OPT_LIST} is empty. Will try next time."
		exit 0
	fi
fi

# remove the used options
remove_from_list $REDIS_OPT_LIST "${last_elem}"

command_line="$jar_command ${tab_loadlevel_jar} ${hadoop_job_options}  ${tab_loadlevel_input} ${tab_loadlevel_output}"

report_metric "load" ${loadlevel} "int32" load hadoopmaster
report_metric "load_id" $LOAD_ID "int32" seqnum hadoopmaster

syslog_netcat "..hadoop job is starting: ${command_line}.."

$command_line 2>&1 | while read line ; do 
	syslog_netcat "$line"
done

syslog_netcat "..hadoop job is done. Ready to do a summary..."

#Parse and report the performace
LOG_SUMMARY_EXE=./job_history_summary.py
summary_tmp=summary.txt
username=`whoami`

logfile_path=`$HADOOP_EXE fs -ls /user/$username/${tab_loadlevel_output}/_logs/history | grep -v ".xml" | grep -v Found | awk '{print $8}'`
syslog_netcat "....logfile_path: $logfile_path"
logfile_name=`basename $logfile_path`
syslog_netcat "....logfile_name: $logfile_name"

conffile_path=`$HADOOP_EXE fs -ls /user/$username/${tab_loadlevel_output}/_logs/history | grep ".xml" | grep -v Found | awk '{print $8}'`
syslog_netcat "....conffile_path: $conffile_path"
conffile_name=`basename $conffile_path`
syslog_netcat "....conffile_name: $conffile_name"

#get logfile to the local fs
if [ "$logfile_path" != "" ]; then
	$HADOOP_EXE fs -get $logfile_path ./
fi
if [ "$conffile_path" != "" ]; then
	$HADOOP_EXE fs -get $conffile_path ./
fi

if [ -f $logfile_name ]; then
	cat $logfile_name | $LOG_SUMMARY_EXE > $summary_tmp
	report_metric "mrlatency" `grep -i mrlatency $summary_tmp | awk '{print $2}'` "float" sec hadoopmaster
	report_metric "totlatency" `grep -i totlatency $summary_tmp | awk '{print $2}'` "float" sec hadoopmaster

	rsync ${logfile_name} $HADOOP_LOG_DEST/${logfile_name} 
	syslog_netcat "..sending $logfile_name to $HADOOP_LOG_DEST" 
	rsync ${conffile_name} $HADOOP_LOG_DEST/${conffile_name} 
	syslog_netcat "..sending $conffile_name to $HADOOP_LOG_DEST" 

	#push the name of the logfile to the output list
	res="${logfile_name}:${conffile_name}:${attempt_counter}"
	add_to_list $REDIS_RES_LIST $res
	syslog_netcat "... pushing $res is pushed to $REDIS_RES_LIST ..."
	
	short_name=${tab_loadlevel_output}
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
report_metric "load" 0 "int32" load hadoopmaster
exit 0
