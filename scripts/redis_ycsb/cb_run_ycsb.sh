#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh


set_load_gen $@

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default regenerate_data true`
    GENERATE_DATA=$(echo ${GENERATE_DATA} | tr '[:upper:]' '[:lower:]')
fi

OPERATION_COUNT=`get_my_ai_attribute_with_default operation_count 10000`
READ_RATIO=`get_my_ai_attribute_with_default read_ratio workloaddefault`
UPDATE_RATIO=`get_my_ai_attribute_with_default update_ratio workloaddefault`
SCAN_RATIO=`get_my_ai_attribute_with_default scan_ratio workloaddefault`
INSERT_RATIO=`get_my_ai_attribute_with_default insert_ratio workloaddefault`
INPUT_RECORDS=`get_my_ai_attribute_with_default input_records 10000`
RECORD_SIZE=`get_my_ai_attribute_with_default record_size 2.35`
APP_COLLECTION=`get_my_ai_attribute_with_default app_collection lazy`
DATABASE_SIZE_VERSUS_MEMORY=`get_my_ai_attribute_with_default database_size_versus_memory 0.5`

if [[ ${READ_RATIO} != "workloaddefault" ]]
then
    RATIO_STRING=$(printf "0.%02d" $READ_RATIO)
    sudo sed -i "s/^readproportion=.*$/readproportion=$RATIO_STRING/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
fi

if [[ ${UPDATE_RATIO} != "workloaddefault" ]]
then
    RATIO_STRING=$(printf "0.%02d" $UPDATE_RATIO)
    sudo sed -i "s/^updateproportion=.*$/updateproportion=$RATIO_STRING/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
fi

if [[ ${SCAN_RATIO} != "workloaddefault" ]]
then
    RATIO_STRING=$(printf "0.%02d" $SCAN_RATIO)
    sudo sed -i "s/^scanproportion=.*$/scanproportion=$RATIO_STRING/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
fi

if [[ ${INSERT_RATIO} != "workloaddefault" ]]
then
    RATIO_STRING=$(printf "0.%02d" $INSERT_RATIO)
    sudo sed -i "s/^insertproportion=.*$/insertproportion=$RATIO_STRING/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
fi

# Determine memory size
MEM=`cat /proc/meminfo | grep MemTotal: | awk '{print $2}'`

if [[ $INPUT_RECORDS == "memory" ]]
then
    RECORDS=$(echo "${MEM} * ${DATABASE_SIZE_VERSUS_MEMORY} / ${RECORD_SIZE}" | bc)
else
    RECORDS=$INPUT_RECORDS
fi

# Update the Record Count new dat file
sudo touch $YCSB_PATH/custom_workload.dat
sudo sh -c "echo "recordcount=${RECORDS%.*}" > $YCSB_PATH/custom_workload.dat"
sudo sh -c "echo "operationcount=$OPERATION_COUNT" >> $YCSB_PATH/custom_workload.dat"

source ~/cb_barrier.sh start

if [[ ${GENERATE_DATA} == "true" ]]
then
	for REDIS_NODE in ${redis_ips}
	do
		syslog_netcat "Flushing database by executing redis-cli against node ${REDIS_NODE}"
		redis-cli -h ${REDIS_NODE} "FLUSHDB"
	    ERROR=$?
	    update_app_errors $ERROR
	done
	
    syslog_netcat "Number of records to be inserted : $RECORDS"

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)
    
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the YCSB load profile \"${LOAD_PROFILE}\"" 
    command_line="sudo $YCSB_PATH/bin/ycsb load redis -s -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p redis.host=$redis_ips_csv"
    syslog_netcat "Command line is: ${command_line}"
    if [[ x"${log_output_command}" == x"true" ]]
    then
        syslog_netcat "Command output will be shown"
        $command_line 2>&1 | while read line ; do
            syslog_netcat "$line"
            echo $line >> $GEN_OUTPUT_FILE
        done
    else
        syslog_netcat "Command output will NOT be shown"
        $command_line 2>&1 >> $GEN_OUTPUT_FILE
    fi
    END_GENERATION=$(get_time)
    DATA_GENERATION_TIME=$(expr ${END_GENERATION} - ${START_GENERATION})
    update_app_datagentime ${DATA_GENERATION_TIME}
    update_app_datagensize ${RECORDS}
else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the Redis YCSB load profile \"${LOAD_PROFILE}\""     
fi

CMDLINE="sudo $YCSB_PATH/bin/ycsb run redis -s -threads ${LOAD_LEVEL} -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p redis.host=$redis_ips_csv"

log_output_command=$(get_my_ai_attribute log_output_command)
log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

run_limit=`decrement_my_ai_attribute run_limit`

if [[ ${run_limit} -ge 0 ]]
then
    syslog_netcat "This AI will execute the load_generating process ${run_limit} more times" 
    syslog_netcat "Command line is: ${CMDLINE}. Output file is ${RUN_OUTPUT_FILE}"
    if [[ $APP_COLLECTION == "lazy" ]]
    then
        lazy_collection "$CMDLINE" ${RUN_OUTPUT_FILE} ${SLA_RUNTIME_TARGETS}
    else
        eager_collection "$CMDLINE" ${RUN_OUTPUT_FILE} ${SLA_RUNTIME_TARGETS}
    fi
else
    syslog_netcat "This AI reached the limit of load generation process executions. If you want this AI to continue to execute the load generator, reset the \"run_limit\" counter"
    sleep ${LOAD_DURATION}
fi

unset_load_gen

exit 0
