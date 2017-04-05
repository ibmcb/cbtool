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
set_load_gen $@

export PATH=$PATH:~/iwl/bin
eval PATH=${PATH}

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/iwl/bin
eval LD_LIBRARY_PATH=${LD_LIBRARY_PATH}

sudo ln -s ~/iwl/bin/iwlengine /usr/local/bin/
sudo ln -s ~/iwl/bin/iwlparse /usr/local/bin/
sudo ln -s ~/iwl/bin/iwldaemon /usr/local/bin/

SIZE=`get_my_ai_attribute_with_default tradedb_size small`
case "$SIZE" in 
    small )
        NR_QUOTES=40000
        NR_USERS=15000
        ;;
    large )
        NR_QUOTES=6000000
        NR_USERS=3000000
        ;;
esac
syslog_netcat "Selected TRADEDB size is $SIZE. The number of quotes will be $NR_QUOTES and the number of users will be $NR_USERS"

WAS_IPS=`get_ips_from_role was`
DB2_IPS=`get_ips_from_role db2`
IS_LOAD_BALANCED=`get_my_ai_attribute load_balancer`
IS_LOAD_BALANCED=`echo ${IS_LOAD_BALANCED} | tr '[:upper:]' '[:lower:]'`
LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
NR_QUOTES=`get_my_ai_attribute_with_default nr_quotes $NR_QUOTES`
NR_USERS=`get_my_ai_attribute_with_default nr_quotes $NR_USERS`
APP_COLLECTION=`get_my_ai_attribute_with_default app_collection lazy`
PERIODIC_MEASUREMENTS=`get_my_ai_attribute_with_default periodic_measurements false`

WAS_IPS_CSV=`echo ${WAS_IPS} | sed ':a;N;$!ba;s/\n/, /g'`
DB2_IPS_CSV=`echo ${DB2_IPS} | sed ':a;N;$!ba;s/\n/, /g'`

if [ x"${LOAD_PROFILE}" == "default" ]
then
    JXS_SCRIPT=~/iwl/bin/test.jxs 
else 
    JXS_SCRIPT=~/iwl/bin/test.jxs 
fi
eval JXS_SCRIPT=${JXS_SCRIPT}
    
if [ x"${IS_LOAD_BALANCED}" == x"true" ]
then
    LOAD_BALANCER_IP=`get_ips_from_role lb`
    #    syslog_netcat "Benchmarking daytrader SUT: LOAD_BALANCER=${LOAD_BALANCER_IP} -> WAS_SERVERS=${WAS_IPS_CSV} -> DB2_SERVERS=${DB2_IPS_CSV} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"
else
	/bin/true
    #    syslog_netcat "Benchmarking daytrader SUT: WAS_SERVER=${WAS_IPS} -> DB2_SERVERS=${DB2_IPS_CSV} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})"
fi

CMDLINE="iwlengine --enginename testit --define hostname=${LOAD_GENERATOR_TARGET_IP}:9080 --define botClient=0 --define topClient=${NR_USERS} --define stocks=${NR_QUOTES} -e 0 -s ${JXS_SCRIPT} --timelimit $LOAD_DURATION -c $LOAD_LEVEL"

PERIODIC_MEASUREMENTES=`echo ${PERIODIC_MEASUREMENTS} | tr '[:upper:]' '[:lower:]'`
if [ x"$PERIODIC_MEASUREMENTS" == x"true" ]
then
    syslog_netcat "Periodic measurement of WAS and DB2 vms is enabled"
    for ip in $WAS_IPS
    do
        reset_periodic_monitor cb_was_collect.py 30 $ip
    done

    reset_periodic_monitor cb_db2_collect.py 30 $DB2_IPS
else 
    syslog_netcat "Periodic measurement of WAS and DB2 vms is disabled"
fi

source ~/cb_barrier.sh start

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${RUN_OUTPUT_FILE}. Application data collection mode is ${APP_COLLECTION}"

LOAD_GENERATOR_START=$(date +%s)
$CMDLINE 2>&1 | while read line ; do
    if [ x"${log_output_command}" == x"true" ]
    then
        syslog_netcat "$line"
    fi
    echo $line >> $RUN_OUTPUT_FILE
    
    if [ x"${APP_COLLECTION}" == x"eager" ]; then
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
        
            ~/cb_report_app_metrics.py \
            throughput:$tp:tps \
            latency:$lat:msec \
            $(common_metrics)
        fi
    fi
done
ERROR=$?
LOAD_GENERATOR_END=$(date +%s)

update_app_errors $ERROR
    
update_app_completiontime $(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START ))      
            
syslog_netcat "iwlengine run complete. Will collect and report the results"
tp=`cat ${RUN_OUTPUT_FILE} | grep throughput | grep Page | grep -v element | cut -d " " -f 5 | tr -d ' '`
lat=`echo "\`cat ${RUN_OUTPUT_FILE} | grep response | grep -v all | cut -d " " -f 9 | tr -d ' '\` * 1000" | bc`
~/cb_report_app_metrics.py \
throughput:$tp:tps \
latency:$lat:msec \
$(common_metrics)    
    
unset_load_gen

exit 0