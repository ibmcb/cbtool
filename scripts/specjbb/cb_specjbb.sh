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
	syslog_netcat "Usage: cb_specjbb.sh <load_profile> <load level> <load duration> <load_id>"
	exit 1
fi

export MYAINAME=`get_my_ai_attribute name`
export JVM=`echo ${MYAINAME} | cut -d "_" -f 2`
export RAMPUP_TIME=`get_my_ai_attribute_with_default specjbb_rampup 20`
export EXPERIMENT_BASE_ID=`get_my_ai_attribute experiment_base_id`
export EXPERIMENT_RUN_ID=`get_global_sub_attribute time experiment_id`
export JAVA_HOME=~/`get_my_ai_attribute java_home`
export GC_POLICY=`get_my_ai_attribute gc_policy`
export BALLOON_SIZE=`get_my_ai_attribute_with_default balloon_size 500` 
export BALLOON_DELAY=`get_my_ai_attribute_with_default balloon_delay 300`
export EXPERIMENT_REMOTE_BASE_DIR=`get_my_ai_attribute experiment_remote_base_dir`
export LOGIN=`get_my_ai_attribute login`
export REMOTEHOST=`get_my_ai_attribute experiment_output_collection_host`
export EXPOUTCOLDIR=`get_my_ai_attribute experiment_output_collection_dir`
export TERM_COUNTER=`get_my_ai_attribute term_counter_name`

SPECJBB_IP=`get_ips_from_role specjbb`

cd ~

#####################################################
# rysnc to update the VM and spec files if necessary
#####################################################
if [ x"${REMOTE_HOST}" != x ]
then
	syslog_netcat "Starting rsync"
	RSYNCOMMAND="rsync ${LOGIN}@${REMOTEHOST}:${EXPERIMENT_REMOTE_BASE_DIR}/jvm/ ${JAVA_HOME}"
	$RSYNCOMMAND | while read line ; do
		syslog_netcat "$line"
	done
	syslog_netcat "Rsync complete" 
fi

#####################################################
# set up spec configuration and adjust to 
# reflect the parameters passed
#####################################################
export SPEC_PATH=~
export AGENT_PATH=$JAVA_HOME/jre/lib/amd64/default
rm -f ~/SPECjbb.props
cp ~/SPECjbb.props.template ~/SPECjbb.props
sed -i s/"LOAD_DURATION_TMPLT"/"${LOAD_DURATION}"/g ~/SPECjbb.props
sed -i s/"RAMPUP_TIME_TMPLT"/"${RAMPUP_TIME}"/g ~/SPECjbb.props
syslog_netcat "Updating properties file SPECjbb.props with the load duration value of measurement:${LOAD_DURATION} rampup:${RAMPUP_TIME}"

source ~/cb_barrier.sh start

#####################################################
# same thing for the JVM
#####################################################
if [ -z "${counter_value}" ]
then
	counter_value=1
fi
syslog_netcat "Assigning identifier \"${counter_value}\" to this JVM"
export JVM=jvm${counter_value}

export EXPERIMENT_RUN_ID=${EXPERIMENT_RUN_ID}`ai_get_counter ${run_counter}`
syslog_netcat "Experiment ID is ${EXPERIMENT_RUN_ID}"

#####################################################
# build the balloon configuration
#####################################################
if [ x"$specific_parameters" == x ]; then
	true
else :
	BALLOON_SIZE=${PARM[1]}
	BALLOON_DELAY=${PARM[2]}
fi
export BALLOON_OPTIONS="-agentpath:${AGENT_PATH}/libballoon27.so=size:${BALLOON_SIZE},holdtime:2000,delay:${BALLOON_DELAY}"
export SOFTMX_OPTIONS="-agentpath:${AGENT_PATH}/libosmemory27.so=Interval:5000"

#####################################################
# build the command line to run based on the parameters
#####################################################
CMDLINE_START="${JAVA_HOME}/jre/bin/java ${GC_OPTIONS} "

declare -A CMDLINE_MIDDLE

CMDLINE_MIDDLE[1]="-Xverbosegclog:${JVM}-gc -Xmx525M ${BALLOON_OPTIONS} ${SOFTMX_OPTIONS} "

CMDLINE_END="-cp $SPEC_PATH/jbb.jar:$SPEC_PATH/check.jar spec.jbb.JBBmain"

ARRAY_SIZE=${#CMDLINE_MIDDLE[*]}
if [ ${LOAD_LEVEL} -gt $ARRAY_SIZE ]; then
	CMDLINE="${CMDLINE_START}${CMDLINE_MIDDLE[${ARRAY_SIZE}]}$CMDLINE_END"
elif [ ${LOAD_LEVEL} -lt 1 ]; then
	CMDLINE="${CMDLINE_START}${CMDLINE_MIDDLE[1]}$CMDLINE_END"
else
	CMDLINE="${CMDLINE_START}${CMDLINE_MIDDLE[${LOAD_LEVEL}]}$CMDLINE_END"
fi

syslog_netcat "Benchmarking SPECjbb SUT: WAS=${SPECJBB_IP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"
OUTPUT_FILE=`mktemp`

syslog_netcat "Command line is: ${CMDLINE}"
$CMDLINE 2>&1 | while read line ; do
	syslog_netcat "$line"
	echo $line >> $OUTPUT_FILE
done

#####################################################
# extract and publish result
#####################################################
RESULTS_FILE=`cat $OUTPUT_FILE | grep Opened | grep raw | cut -d " " -f 2 | tr -d " "`

if [ x"${RESULTS_FILE}" == x ]; then
	syslog_netcat "An error prevented the production of the output file. Unable to collect and report results"
else
	syslog_netcat "SPECjbb benchmark run complete. Will collect and report the results. Output file name is ${RESULTS_FILE}"

	app_metric_string=""
	for TEST in test1 test2
	do
		THROUGHPUT=`cat ${RESULTS_FILE} | grep score | grep ${TEST} | cut -d "=" -f 2 | tr -d " "`

		app_metric_string+=" throughput_${TEST}:"${THROUGHPUT}":tps"
		for TYPE in payment order_status delivery stock_level cust_report
		do
			X=`cat ${RESULTS_FILE} | grep ${TEST} | grep ${TYPE} | grep averagetime | cut -d "=" -f 2 | tr -d " "`
			RESPONSE_TIME=`echo ${X} | awk -F"E" 'BEGIN{OFMT="%10.10f"} {print $1 * (10 ^ $2) * 1000}'`
			app_metric_string+=" latency_${TEST}_${TYPE}:"${RESPONSE_TIME}":msec"
		done
	done
	~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec ${app_metric_string}

	if [ x"${EXPOUTCOLDIR}" == x ]; then
		true
	else :
		#####################################################
		# scp the output files back to the ed on the parameters
		#####################################################
		syslog_netcat "Transferring output files for ${JVM} to:${EXPERIMENT_REMOTE_BASE_DIR}/${EXPOUTCOLDIR}/${EXPERIMENT_BASE_ID}_${EXPERIMENT_RUN_ID}"
		echo "mkdir ${EXPERIMENT_REMOTE_BASE_DIR}/${EXPOUTCOLDIR}/${EXPERIMENT_BASE_ID}_${EXPERIMENT_RUN_ID};exit" |ssh ${LOGIN}@${REMOTEHOST}
		scp ${JVM}-gc ${LOGIN}@${REMOTEHOST}:~/${EXPERIMENT_REMOTE_BASE_DIR}/${EXPOUTCOLDIR}/${EXPERIMENT_BASE_ID}_${EXPERIMENT_RUN_ID}/${JVM}-gc
		scp ${OUTPUT_FILE} ${LOGIN}@${REMOTEHOST}:~/${EXPERIMENT_REMOTE_BASE_DIR}/${EXPOUTCOLDIR}/${EXPERIMENT_BASE_ID}_${EXPERIMENT_RUN_ID}/${JVM}-output
		syslog_netcat "Transfer is complete for ${JVM}"
	fi

	rm ${OUTPUT_FILE}
	rm ${JVM}-gc

fi

###############################################
# no indicate that we are done
###############################################
if [ -z ${TERM_COUNTER} ]
then
	true
else
	term_value=`ai_increment_counter ${TERM_COUNTER}`
	syslog_netcat "Term counter(${TERM_COUNTER}) value: ${term_value}"
fi

exit 0
