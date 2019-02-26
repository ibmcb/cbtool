#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

MYSQL_DATABASE_NAME=`get_my_ai_attribute_with_default mysql_database_name sysbenchdb`
MYSQL_ROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_root_password temp4now`
MYSQL_NONROOT_USER=`get_my_ai_attribute_with_default mysql_nonroot_user sysbench`
MYSQL_NONROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_nonroot_password sysbench`
MYSQL_DATA_DIR=`get_my_ai_attribute_with_default mysql_data_dir /sysbench`

MYSQL_IPS=`get_ips_from_role mysql`
LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
TABLE_SIZE=`get_my_ai_attribute_with_default table_size 10000`

CONN_STR="--mysql-host=${LOAD_GENERATOR_TARGET_IP} --mysql-db=${MYSQL_DATABASE_NAME} --mysql-user=${MYSQL_NONROOT_USER} --mysql-password=${MYSQL_NONROOT_PASSWORD}"

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
    GEN_COMMAND_LINE=""
else
    GENERATE_DATA=`get_my_ai_attribute_with_default regenerate_data true`
    GEN_COMMAND_LINE="sysbench ${CONN_STR} --db_driver=mysql /usr/share/sysbench/${LOAD_PROFILE}.lua cleanup;"
fi

GENERATE_DATA=$(echo $GENERATE_DATA | tr '[:upper:]' '[:lower:]')

if [[ ${GENERATE_DATA} == "true" ]]
then

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)

    DT_BUILD_CMD=~/build_daytrader_db.py
    eval DT_BUILD_CMD=${DT_BUILD_CMD}
                        
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the Sysbench load profile \"${LOAD_PROFILE}\"" 
    GEN_COMMAND_LINE="sysbench ${CONN_STR} --table-size=${TABLE_SIZE} --db_driver=mysql /usr/share/sysbench/${LOAD_PROFILE}.lua prepare"
    syslog_netcat "Command line is: ${GEN_COMMAND_LINE}"
    if [[ x"${log_output_command}" == x"true" ]]
    then
        syslog_netcat "Command output will be shown"
        $GEN_COMMAND_LINE 2>&1 | while read line ; do
            syslog_netcat "$line"
            echo $line >> $GEN_OUTPUT_FILE
        done
        ERROR=$?        
    else
        syslog_netcat "Command output will NOT be shown"
        $GEN_COMMAND_LINE 2>&1 >> $GEN_OUTPUT_FILE
        ERROR=$?
    fi
    END_GENERATION=$(get_time)
    update_app_errors $ERROR        

    DATA_GENERATION_TIME=$(expr ${END_GENERATION} - ${START_GENERATION})
    update_app_datagentime ${DATA_GENERATION_TIME}
    update_app_datagensize ${TABLE_SIZE}
else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the Sysbench load profile \"${LOAD_PROFILE}\""
    
fi

CMDLINE="sysbench ${CONN_STR} --table-size=${TABLE_SIZE} --num-threads=${LOAD_LEVEL} --time=${LOAD_DURATION} --max-requests=0 --db_driver=mysql /usr/share/sysbench/${LOAD_PROFILE}.lua run"
execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat $RUN_OUTPUT_FILE | grep transactions | grep per | cut -d '(' -f 2 | cut -d ' ' -f 1)
lat=$(cat $RUN_OUTPUT_FILE | grep avg: | awk '{ print $2 }')
lat_95=$(cat $RUN_OUTPUT_FILE | grep "95 percentile" | awk '{ print $4 }')

~/cb_report_app_metrics.py \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
throughput:$tp:tps \
$(format_for_report latency $lat) \
$(format_for_report 95_latency $lat_95) \
$(common_metrics)
 
unset_load_gen

exit 0
