#!/usr/bin/env bash

#/*******************************************************************************
#/*******************************************************************************

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
    source $dir/cb_common.sh
else
    source $dir/../common/cb_common.sh
fi

standalone=`online_or_offline "$5"`

export PATH=$PATH:~/iwl/bin
eval PATH=${PATH}

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/iwl/bin
eval LD_LIBRARY_PATH=${LD_LIBRARY_PATH}

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

if [ $standalone == online ] ; then
    # retrieve online values from API
    LOAD_PROFILE=$1
    LOAD_LEVEL=$2
    LOAD_DURATION=$3
    LOAD_ID=$4
    SLA_RUNTIME_TARGETS=$5    
    WAS_IPS=`get_ips_from_role was`
    DB2_IP=`get_ips_from_role db2`
    IS_LOAD_BALANCED=`get_my_ai_attribute load_balancer`
    IS_LOAD_BALANCED=`echo ${IS_LOAD_BALANCED} | tr '[:upper:]' '[:lower:]'`
    LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
    NR_QUOTES=`get_my_ai_attribute_with_default nr_quotes $NR_QUOTES`
    NR_USERS=`get_my_ai_attribute_with_default nr_quotes $NR_USERS`
    APP_COLLECTION=`get_my_ai_attribute_with_default app_collection lazy`
    PERIODIC_MEASUREMENTS=`get_my_ai_attribute_with_default periodic_measurements false`
else
    LOAD_LEVEL=$6
    LOAD_DURATION=$7
    LOAD_ID=$(date +%s)
    WAS_IPS=$5
    DB2_IP=unknown
    IS_LOAD_BALANCED="unknown"
    LOAD_GENERATOR_TARGET_IP=$5
    log_output_command="true"
    PERIODIC_MEASUREMENTES="unknowm"
    APP_COLLECTION="unknowm"
    standalone_verify "$LOAD_GENERATOR_TARGET_IP" "Need ip address of websphere or loadbalancer."
    standalone_verify "$LOAD_LEVEL" "Need number of clients to send load. Values start at 1. A good starting value is 10."
    standalone_verify "$LOAD_DURATION" "Need number of seconds to run client before stopping."
    post_boot_steps offline 
fi

WAS_IPS_CSV=`echo ${WAS_IPS} | sed ':a;N;$!ba;s/\n/, /g'`

if [ x"${collect_from_guest}" == x"true" ]
then
    if [ x"${LOAD_ID}" == x"1" ]
    then
        syslog_netcat "Restarting gmetad for DayTrader's first load"
        sudo su root -l -c "pkill -9 -f gmetad"
        ${dir}/monitor-core/gmetad-python/gmetad.py -c /home/klabuser/gmetad-vms.conf -d 1
    fi
fi

if [ x"${IS_LOAD_BALANCED}" == x"true" ]
then
    LOAD_BALANCER_IP=`get_ips_from_role lb`
    syslog_netcat "Benchmarking daytrader SUT: LOAD_BALANCER=${LOAD_BALANCER_IP} -> WAS_SERVERS=${WAS_IPS_CSV} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"
else
    syslog_netcat "Benchmarking daytrader SUT: WAS_SERVER=${WAS_IPS} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID})"
fi

CMDLINE="python /home/cbtool/cbtool/scripts/daytrader-open/warmup-daytrader.py -s ${LOAD_GENERATOR_TARGET_IP} -u ${NR_USERS} -q ${NR_QUOTES} -t 200 "

PERIODIC_MEASUREMENTES=`echo ${PERIODIC_MEASUREMENTS} | tr '[:upper:]' '[:lower:]'`
if [ x"$PERIODIC_MEASUREMENTS" == x"true" ]
then
    syslog_netcat "Periodic measurement of WAS and DB2 vms is enabled"
    for ip in $WAS_IPS
    do
        reset_periodic_monitor cb_was_collect.py 30 $ip
    done

    reset_periodic_monitor cb_db2_collect.py 30 $DB2_IP
else 
    syslog_netcat "Periodic measurement of WAS and DB2 vms is disabled"
fi

source ~/cb_barrier.sh start

OUTPUT_FILE=`mktemp`

syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}. Application data collection mode is ${APP_COLLECTION}"

LOAD_GENERATOR_START=$(date +%s)  
$CMDLINE 2>&1 | while read line ; do
    if [ x"${log_output_command}" == x"true" ]; then
        syslog_netcat "$line"
    fi
    echo $line >> $OUTPUT_FILE

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
    
            ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
            load_level:${LOAD_LEVEL}:load \
            load_duration:${LOAD_DURATION}:sec \
            load_profile:${LOAD_PROFILE}:name \
            throughput:$tp:tps \
            latency:$lat:msec \
            ${SLA_RUNTIME_TARGETS}
        fi
    fi
done
ERROR=$?
LOAD_GENERATOR_END=$(date +%s)

update_app_errors $ERROR
    
update_app_completiontime $(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START )) 

syslog_netcat "daytrader-run complete. Will collect and report the results"
tp=`cat ${OUTPUT_FILE} | grep throughput | grep Page | grep -v element | cut -d " " -f 5 | tr -d ' '`
lat=`echo "\`cat ${OUTPUT_FILE} | grep response | grep -v all | cut -d " " -f 9 | tr -d ' '\` * 1000" | bc`
~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
errors:$(update_app_errors):num \
completion_time:$(update_app_completiontime):sec \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
throughput:$tp:tps latency:$lat:msec \
${SLA_RUNTIME_TARGETS}

rm ${OUTPUT_FILE}

exit 0
exit 0