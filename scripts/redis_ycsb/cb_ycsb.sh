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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

cd ~

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5 
	
if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
    syslog_netcat "Usage: cb_ycsb.sh <load_profile> <load level> <load duration> <load_id>"
    exit 1
fi

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default generate_data true`
fi

OPERATION_COUNT=`get_my_ai_attribute_with_default operation_count 100000`
READ_RATIO=`get_my_ai_attribute_with_default read_ratio workloaddefault`
UPDATE_RATIO=`get_my_ai_attribute_with_default update_ratio workloaddefault`
INPUT_RECORDS=`get_my_ai_attribute_with_default input_records 100000`
RECORD_SIZE=`get_my_ai_attribute_with_default record_size 2.35`
APP_COLLECTION=`get_my_ai_attribute_with_default app_collection lazy`
DATABASE_SIZE_VERSUS_MEMORY=`get_my_ai_attribute_with_default database_size_versus_memory 0.5`

if [[ ${READ_RATIO} != "workloaddefault" ]]
then
    sudo sed -i "s/^readproportion=.*$/readproportion=0\.$READ_RATIO/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
fi

if [[ ${UPDATE_RATIO} != "workloaddefault" ]]
then
    sudo sed -i "s/^updateproportion=.*$/updateproportion=0\.$UPDATE_RATIO/g" $YCSB_PATH/workloads/${LOAD_PROFILE}
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

OUTPUT_FILE=$(mktemp)
if [[ ${GENERATE_DATA} == "true" ]]
then
    syslog_netcat "Number of records to be inserted : $RECORDS"

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)
    
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the YCSB load profile \"${LOAD_PROFILE}\"" 
    command_line="sudo $YCSB_PATH/bin/ycsb load redis -s -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p redis.host=$redis_ip"
    syslog_netcat "Command line is: ${command_line}"
    if [[ x"${log_output_command}" == x"true" ]]
    then
        syslog_netcat "Command output will be shown"
        $command_line 2>&1 | while read line ; do
            syslog_netcat "$line"
            echo $line >> $OUTPUT_FILE
        done
    else
        syslog_netcat "Command output will NOT be shown"
        $command_line 2>&1 >> $OUTPUT_FILE
    fi
    END_GENERATION=$(get_time)
    DATA_GENERATION_TIME=$(expr ${END_GENERATION} - ${START_GENERATION})
    echo ${DATA_GENERATION_TIME} > /tmp/data_generation_time
else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the hadoop load profile \"${LOAD_PROFILE}\""     
fi

CMDLINE="sudo $YCSB_PATH/bin/ycsb run redis -s -threads ${LOAD_LEVEL} -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p redis.host=$redis_ip"

syslog_netcat "Benchmarking YCSB SUT: REDIS=${redis_ip} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

source ~/cb_barrier.sh start

log_output_command=$(get_my_ai_attribute log_output_command)
log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

run_limit=`decrement_my_ai_attribute run_limit`

if [[ ${run_limit} -ge 0 ]]
then
    syslog_netcat "This AI will execute the load_generating process ${run_limit} more times" 
    syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"
    if [[ $APP_COLLECTION == "lazy" ]]
    then
        lazy_collection "$CMDLINE" ${SLA_RUNTIME_TARGETS}
    else
        eager_collection "$CMDLINE" ${SLA_RUNTIME_TARGETS}
    fi
else
    syslog_netcat "This AI reached the limit of load generation process executions. If you want this AI to continue to execute the load generator, reset the \"run_limit\" counter"
    sleep ${LOAD_DURATION}
fi

exit 0