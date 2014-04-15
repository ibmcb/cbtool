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

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
    syslog_netcat "Usage: cb_start_ycsb.sh <load_profile> <load level> <load duration> <load_id>"
    exit 1
fi

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default generate_data false`
fi

OPERATION_COUNT=`get_my_ai_attribute_with_default operation_count 100000`
READ_RATIO=`get_my_ai_attribute_with_default read_ratio workloaddefault`
UPDATE_RATIO=`get_my_ai_attribute_with_default update_ratio workloaddefault`
INPUT_RECORDS=`get_my_ai_attribute_with_default input_records memory`
INPUT_RECORDS_FACTOR=`get_my_ai_attribute_with_default input_records_factor 10000`
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
    RECORDS=$(python -c 'from __future__ import division; print ((('"${MEM}"'/1024)/1024)*'"${DATABASE_SIZE_VERSUS_MEMORY}"')*'"${INPUT_RECORDS_FACTOR}"'')
else 
    RECORDS=$INPUT_RECORDS
fi
syslog_netcat "Number of records to be inserted : $RECORDS"

# Update the Record Count new dat file
sudo touch $YCSB_PATH/custom_workload.dat
sudo sh -c "echo "recordcount=${RECORDS%.*}" > $YCSB_PATH/custom_workload.dat"
sudo sh -c "echo "operationcount=$OPERATION_COUNT" >> $YCSB_PATH/custom_workload.dat"

run_client_phase=`get_my_ai_attribute run_client_phase`
syslog_netcat "Run client phase? $run_client_phase"
run_base_phase=`get_my_ai_attribute run_base_phase`
syslog_netcat "Run base phase? $run_base_phase"
load_phase=`get_my_ai_attribute run_load_phase` 
syslog_netcat "Run load phase? $load_phase"
db_load_phase=`get_my_ai_attribute load_db_phase` 
syslog_netcat "DB load phase? $db_load_phase"

if [[ $db_load_phase ]] ; then
if [[ ${GENERATE_DATA} == "true" ]]
then
    OUTPUT_FILE=$(mktemp)

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)
    
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the YCSB load profile \"${LOAD_PROFILE}\"" 
    command_line="sudo $YCSB_PATH/bin/ycsb load cassandra-10 -s -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p hosts=$seed_ip"
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
fi

if [[ $load_phase ]] ; then

#----------------------- Track all YCSB results  -------------------------------

#----------------------- Total op/sec ------------------------------------------
ops=0

#----------------------- Current op/sec for this client ------------------------
write_current_ops=0
read_current_ops=0
update_current_ops=0

#----------------------- Tracking Latency --------------------------------------
# <operation>_latency=average,min,max,95,99
#-------------------------------------------------------------------------------
write_latency=0
read_latency=0
update_latency=0

#----------------------- Old tracking ------------------------------------------
latency=0

CMDLINE="sudo $YCSB_PATH/bin/ycsb run cassandra-10 -s -threads ${LOAD_LEVEL} -P $YCSB_PATH/workloads/${LOAD_PROFILE} -P $YCSB_PATH/custom_workload.dat -p hosts=$seed_ip"

syslog_netcat "Benchmarking YCSB SUT: SEED=${seed_ip} -> CASSANDRAS=${cassandra_ips_csv} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

source ~/cb_barrier.sh start

log_output_command=$(get_my_ai_attribute log_output_command)
log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

run_limit=`decrement_my_ai_attribute run_limit`

if [[ ${run_limit} -ge 0 ]]
then
    syslog_netcat "This AI will execute the load_generating process ${run_limit} more times" 
    syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE}"

    while read line ; do
#-------------------------------------------------------------------------------
# Need to track each YCSB Clients current operation count.
# NEED TO:
#       Create a variable that reports to CBTool the current operation
#-------------------------------------------------------------------------------
        if [[ "$line" =~ "[0-9]+\s sec:" ]]
        then
            CURRENT_OPS=$(echo $line | awk '{print $3}')
            syslog_netcat "Current Ops : $CURRENT_OPS"
            if [[ "$line" == *READ* ]]
            then
                AVG_READ_LATENCY=$(echo $line | awk '{print $11}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netcat "Current Avg. Read Latency : $AVG_READ_LATENCY"
            fi
            
            if [[ "$line" == *WRITE* ]]
            then
                AVG_WRITE_LATENCY=$(echo $line | awk '{print $9}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netncat "Current Avg. Write Latency : $AVG_WRITE_LATENCY"
            fi
            
            if [[ "$line" == *UPDATE* ]]
            then
                AVG_UPDATE_LATENCY=$(echo $line | awk '{print $9}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netncat "Current Avg. Update Latency : $AVG_UPDATE_LATENCY"
            fi
        fi
    
        IFS=',' read -a array <<< "$line"
        if [[ ${array[0]} == *OVERALL* ]]
        then
            if [[ ${array[1]} == *Throughput* ]]
            then
                ops=${array[2]}
            fi
        fi
#----------------------- Track Latency -----------------------------------------
        if [[ ${array[0]} == *UPDATE* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                update_avg_latency=${array[2]}
            fi
            
            if [[ ${array[1]} == *MinLatency* ]]
            then
                update_min_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                update_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                update_95_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *99thPercent* ]]
            then
                update_99_latency="${array[2]}"
            fi
        fi
        
        if [[ ${array[0]} == *READ* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                read_avg_latency=${array[2]}
            fi
            
            if [[ ${array[1]} == *MinLatency* ]]
            then
                read_min_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                read_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                read_95_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *99thPercent* ]]
            then
                read_99_latency="${array[2]}"
            fi
        fi
        
        if [[ ${array[0]} == *WRITE* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                write_avg_latency=${array[2]}
            fi
            if [[ ${array[1]} == *MinLatency* ]]
            then
                write_min_latency="${array[2]}"
            fi
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                write_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                write_95_latency="${array[2]}"
            fi
            if [[ ${array[1]} == *99thPercent* ]]
            then
                write_99_latency="${array[2]}"
            fi
        fi
    done < <($CMDLINE 2>&1)
else
    syslog_netcat "This AI reached the limit of load generation process executions. If you want this AI to continue to execute the load generator, reset the \"run_limit\" counter"
    sleep ${LOAD_DURATION}
fi
    
# Collect data generation time, taking care of reporting the time
# with a minus sign in case data was not generated on this 
# run
if [[ -f /tmp/old_data_generation_time ]]
then
    datagentime=-$(cat /tmp/old_data_generation_time)
fi

if [[ -f /tmp/data_generation_time ]]
then
    datagentime=$(cat /tmp/data_generation_time)
    mv /tmp/data_generation_time /tmp/old_data_generation_time
fi

if [[ $write_avg_latency -ne 0 ]]
then
    ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
    load_level:${LOAD_LEVEL}:load \
    load_profile:${LOAD_PROFILE}:name \
    throughput:$(expr $ops):tps \
    write_avg_latency:$(expr $write_avg_latency):us \
    write_min_latency:$(expr $write_min_latency):us \
    write_max_latency:$(expr $write_max_latency):us \
    write_95_latency:$(expr $write_95_latency):us \
    write_99_latency:$(expr $write_99_latency):us \
    read_avg_latency:$(expr $read_avg_latency):us \
    read_min_latency:$(expr $read_min_latency):us \
    read_max_latency:$(expr $read_max_latency):us \
    read_95_latency:$(expr $read_95_latency):us \
    read_99_latency:$(expr $read_99_latency):us \
    update_avg_latency:$(expr $update_avg_latency):us \
    update_min_latency:$(expr $update_min_latency):us \
    update_max_latency:$(expr $update_max_latency):us \
    update_95_latency:$(expr $update_95_latency):us \
    update_99_latency:$(expr $update_99_latency):us \
    datagen_time:${datagentime}:sec
fi

if [[ $write_avg_latency -eq 0 ]]
then
    ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
    load_level:${LOAD_LEVEL}:load \
    load_profile:${LOAD_PROFILE}:name \
    throughput:$(expr $ops):tps \
    read_avg_latency:$(expr $read_avg_latency):us \
    read_min_latency:$(expr $read_min_latency):us \
    read_max_latency:$(expr $read_max_latency):us \
    read_95_latency:$(expr $read_95_latency):us \
    read_99_latency:$(expr $read_99_latency):us \
    update_avg_latency:$(expr $update_avg_latency):us \
    update_min_latency:$(expr $update_min_latency):us \
    update_max_latency:$(expr $update_max_latency):us \
    update_95_latency:$(expr $update_95_latency):us \
    update_99_latency:$(expr $update_99_latency):us \
    datagen_time:${datagentime}:sec
fi

if [[ $? -gt 0 ]]
then
    syslog_netcat "problem running ycsb prime client on $(hostname)"
    exit 1
fi

exit 0

fi

