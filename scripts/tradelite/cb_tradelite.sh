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

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

standalone=`online_or_offline "$4"`

export PATH=$PATH:~/iwl/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/iwl/bin

NR_QUOTES=40000
NR_USERS=15000

if [ $standalone == online ] ; then
	# retrieve online values from API
	LOAD_LEVEL=$1
	LOAD_DURATION=$2
	LOAD_ID=$3
	WAS_IPS=`get_ips_from_role was`
	DB2_IP=`get_ips_from_role db2`
	IS_LOAD_BALANCED=`get_my_ai_attribute load_balancer`
	LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
	NR_QUOTES=`get_my_ai_attribute_with_default nr_quotes $NR_QUOTES`
	NR_USERS=`get_my_ai_attribute_with_default nr_quotes $NR_QUOTES`
	APP_COLLECTION=`get_my_ai_attribute_with_default app_collection lazy`
else
	# offline, so get variables from command-line
	LOAD_LEVEL=$6
	LOAD_DURATION=$7
	LOAD_ID=$(date +%s)
	WAS_IPS=$5
	IS_LOAD_BALANCED="unknown"
	LOAD_GENERATOR_TARGET_IP=$5
	NR_QUOTES=40000
	NR_USERS=15000
	log_output_command="true"
	standalone_verify "$LOAD_GENERATOR_TARGET_IP" "Need ip address of websphere or loadbalancer."
	standalone_verify "$LOAD_LEVEL" "Need number of clients to send load. Values start at 1. A good starting value is 10."
	standalone_verify "$LOAD_DURATION" "Need number of seconds to run client before stopping."
	post_boot_steps offline 
fi

WAS_IPS_CSV=`echo ${WAS_IPS} | sed ':a;N;$!ba;s/\n/, /g'`

if [ x"${IS_LOAD_BALANCED}" == x"true" ]
then
	LOAD_BALANCER_IP=`get_ips_from_role lb`
	syslog_netcat "Benchmarking tradelite SUT: LOAD_BALANCER=${LOAD_BALANCER_IP} -> WAS_SERVERS=${WAS_IPS_CSV} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})"
else
	syslog_netcat "Benchmarking tradelite SUT: WAS_SERVER=${WAS_IPS} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})"
fi

CMDLINE="iwlengine --enginename testit --define hostname=${LOAD_GENERATOR_TARGET_IP}:9080 --define botClient=0 --define topClient=${NR_USERS} --define stocks=${NR_QUOTES} -e 0 -s /home/klabuser/iwl/bin/TradeApp.jxs --timelimit $LOAD_DURATION -c $LOAD_LEVEL"

PERIODIC_MEASUREMENTS=`get_my_ai_attribute_with_default periodic_measurements false`
PERIODIC_MEASUREMENTES=`echo ${PERIODIC_MEASUREMENTS} | tr '[:upper:]' '[:lower:]'`
if [ x"$PERIODIC_MEASUREMENTS" == x"true" ]
then
	syslog_netcat "Periodic measurement of WAS and DB2 vms is enabled"
	for ip in $WAS_IPS
	do
		reset_periodic_monitor was_collect.py 30 $ip
	done

	reset_periodic_monitor db2_collect.py 30 $DB2_IP
else 
	syslog_netcat "Periodic measurement of WAS and DB2 vms is disabled"
fi

OUTPUT_FILE=`mktemp`

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}. Application data collection mode is ${APP_COLLECTION}"

$CMDLINE | while read line ; do
	if [ x"${log_output_command}" == x"true" ]; then
		syslog_netcat "$line"
	fi
	echo $line >> $OUTPUT_FILE

	if [ x"${APP_COLLECTION}" == x"eager"]; then
		if [ x"`echo "$line" | grep -E "pg elem\/s"`" != x ] ; then
			tp=$(echo "$line" | grep -Eo "pg elem/s = [0-9]+\.[0-9]*$" | grep -oE "[0-9]+\.[0-9]*")
			lat=$(echo "$line" | grep -Eo "resp avg = [0-9]+\.[0-9]* |" | grep -oE "[0-9]+\.[0-9]*")
			if [ x"$tp" == x ] ; then
				tp=-1
			fi
			if [ x"$lat" == x ] ; then
				lat=-1
			else
				lat=$(echo "$lat * 1000" | bc)
			fi
	
			report_app_metrics load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_duration:${LOAD_DURATION}:sec throughput:$tp:tps latency:$lat:msec
		fi
	fi
done

syslog_netcat "iwlengine run complete. Will collect and report the results"
tp=`cat ${OUTPUT_FILE} | grep throughput | grep Page | grep -v element | cut -d " " -f 5 | tr -d ' '`
lat=`echo "\`cat ${OUTPUT_FILE} | grep response | grep -v all | cut -d " " -f 9 | tr -d ' '\` * 1000" | bc`
report_app_metrics load_id:${LOAD_ID}:seqnum load_level:${LOAD_LEVEL}:load load_duration:${LOAD_DURATION}:sec throughput:$tp:tps latency:$lat:msec

rm ${OUTPUT_FILE}

exit 0