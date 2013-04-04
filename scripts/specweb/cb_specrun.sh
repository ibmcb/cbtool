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

if [ $standalone == online ] ; then
	LOAD_LEVEL=$1
	LOAD_DURATION=$2
	LOAD_LEVEL_ID=$3
	web=`get_ips_from_role specwebfront`
	be=`get_ips_from_role specwebback`
else
	web=$5
	be=$6
	LOAD_LEVEL=$7
	LOAD_DURATION=$8
	LOAD_ID=$(date +%s)

	standalone_verify "$web" "Need ip address of apache."
	standalone_verify "$be" "Need ip address of backend simulator."
	standalone_verify "$LOAD_LEVEL" "Need number of clients to send load.  Values start at 1. A good starting value is 100."
	standalone_verify "$LOAD_DURATION" "Need number of seconds to run client before stopping."
	post_boot_steps offline 
fi

sleep ${SETUP_TIME}
report_metric "load_id" $LOAD_ID "int32" seqnum 0 all
report_metric "load" 0 "int32" load 0 all

syslog_netcat "Benchmarking SPECWeb SUT: specwebfront=${web} -> specwebbackend=${be} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})" 

sudo rm -rf $dir/results
mkdir $dir/results

sed -ie "s/^SIMULTANEOUS_SESSIONS =.*/SIMULTANEOUS_SESSIONS = $LOAD_LEVEL/g" $dir/Test.config 
sed -ie "s/^WEB_SERVER =.*/WEB_SERVER = $web/g" $dir/Test.config 
sed -ie "s/^BESIM_SERVER =.*/BESIM_SERVER = $be/g" $dir/Test.config 
sed -ie "s/^DEBUG_LEVEL =.*/DEBUG_LEVEL = 0/g" $dir/Test.config 
sed -ie "s/^POLL_CLIENTS.*/POLL_CLIENTS = 1/g" $dir/Test.config
sed -ie "s/^USE_GUI =.*/USE_GUI = 0/g" $dir/Test.config
sed -ie "s/^BESIM_PERSISTENT =.*/BESIM_PERSISTENT = 1/g" $dir/Test.config
sed -ie "s/^MAX_OVERTHINK_TIME =.*/MAX_OVERTHINK_TIME = 36000000/g" $dir/Test.config
sed -ie "s/^THREAD_RAMPUP_SECONDS =.*/THREAD_RAMPUP_SECONDS = 30/g" $dir/Test.config
sed -ie "s/^THREAD_RAMPDOWN_SECONDS =.*/THREAD_RAMPDOWN_SECONDS = 30/g" $dir/Test.config

# Multi-client support, add more ips to the string to add more clients
others="127.0.0.1"

sed -ie "s/^CLIENTS = .*/CLIENTS = \"$others\"/g" $dir/Test.config 

#per workLOAD_LEVEL settings:

sed -ie "s/^RAMPUP_SECONDS =.*/RAMPUP_SECONDS = 30/g" $dir/SPECweb_Banking.config 
sed -ie "s/^RAMPUP_DOWN =.*/RAMPUP_DOWN = 30/g" $dir/SPECweb_Banking.config 
sed -ie "s/^USE_SSL =.*/USE_SSL = 0/g" $dir/SPECweb_Banking.config 
sed -ie "s/^INTRA_INTERVAL_RAMP_SEC =.*/INTRA_INTERVAL_RAMP_SEC = 30/g" $dir/SPECweb_Banking.config
sed -ie "s/^RUN_SECONDS =.*/RUN_SECONDS = $LOAD_DURATION/g" $dir/SPECweb_Banking.config

# For dynamic LOAD_LEVEL, SIMULTANEOUS_SESSION must have multiple values while the
# following value should have a REALLY large LOAD_DURATION RUN_SECONDS
#sed -ie "s/^RUN_SECONDS =.*/RUN_SECONDS = 172800/g" $dir/SPECweb_Banking.config

reset_periodic_monitor specwebfront_collect.py 30 $web
reset_periodic_monitor specwebback_collect.py 30 $be

sleep 5
heap=256
pushd ~
if [ $standalone == online ] ; then
	pushd ~
else
	pushd $dir/../specweb
fi

for pid in $(pgrep -f java) ; do
	kill -9 $pid > /dev/null
done

CMDLINE="java -Xms${heap}m -Xmx${heap}m -classpath .:specwebclient.jar specwebclient"
report_metric "load" $LOAD_LEVEL "int32" load 0 all

syslog_netcat "Command line is: ${CMDLINE}"
$CMDLINE 2>&1 | while read line ; do syslog_netcat "$line" ; done &
sleep 5

OUTPUT_FILE=`mktemp`

CMDLINE="java -Xms${heap}m -Xmx${heap}m -classpath .:jcommon-1.0.15.jar:jfreechart-1.0.12.jar:specweb.jar specweb"

syslog_netcat "Command line is: ${CMDLINE}"
$CMDLINE 2>&1 | while read line ; do
	syslog_netcat "$line"
	echo $line >> $OUTPUT_FILE
done

popd

rm $OUTPUT_FILE

exit 0
