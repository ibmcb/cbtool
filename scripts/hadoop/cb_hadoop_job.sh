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

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
    syslog_netcat "Usage: cb_hadoop_job.sh <load_profile> <load level> <load duration> <load_id>"
    exit 1
fi

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default generate_data true`
fi

DATA_HDFS=`get_my_ai_attribute_with_default dfs_data_dir /tmp/cbhadoopdata`
export DATA_HDFS

LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor "10000"`

case ${LOAD_PROFILE} in
    bayes)
    PAGES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    CLASSES=`get_my_ai_attribute_with_default classes "20"`
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    NGRAMS=`get_my_ai_attribute_with_default ngrams "3"`
    export PAGES
    export NUM_MAPS
    export NUM_REDS
    export NGRAMS
    syslog_netcat "Parameters used for bayes are: PAGES=${PAGES}, CLASSES=${CLASSES}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}, NGRAMS=${NGRAMS}"    
    ;;
    dfsioe)
    RD_NUM_OF_FILES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    RD_FILE_SIZE=`get_my_ai_attribute_with_default rd_file_size "2"`
    WT_NUM_OF_FILES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    WT_FILE_SIZE=`get_my_ai_attribute_with_default wt_file_size "1"`
    export RD_NUM_OF_FILES
    export RD_FILE_SIZE
    export WT_NUM_OF_FILES
    export WT_FILE_SIZE
    syslog_netcat "Parameters used for dfsioe are: RD_NUM_OF_FILES=${RD_NUM_OF_FILES}, RD_FILE_SIZE=${RD_FILE_SIZE}, WT_NUM_OF_FILES=${WT_NUM_OF_FILES}, WT_FILE_SIZE=${WT_FILE_SIZE}"    
    ;;
    hivebench)
    USERVISITS=$((8*${LOAD_LEVEL}*${LOAD_FACTOR}))
    PAGES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    export USERVISITS
    export PAGES
    export NUM_MAPS
    export NUM_REDS
    syslog_netcat "Parameters used for hivebench are: USERVISITS=${USERVISITS}, PAGES=${PAGES}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}"
    ;;
    kmeans)
    NUM_OF_CLUSTERS=`get_my_ai_attribute_with_default num_of_clusters "5"`
    NUM_OF_SAMPLES=$((5*${LOAD_LEVEL}*${LOAD_FACTOR}))
    SAMPLES_PER_INPUTFILE=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    DIMENSIONS=`get_my_ai_attribute_with_default dimensions "20"`
    MAX_ITERATION=`get_my_ai_attribute_with_default max_iteration "5"`
    export NUM_OF_CLUSTERS
    export NUM_OF_SAMPLES
    export SAMPLES_PER_INPUTFILE
    export DIMENSIONS
    export MAX_ITERATION
    syslog_netcat "Parameters used for kmeans are: NUM_OF_CLUSTERS=${NUM_OF_CLUSTERS}, NUM_OF_SAMPLES=${NUM_OF_SAMPLES}, SAMPLES_PER_INPUTFILE=${SAMPLES_PER_INPUTFILE}, DIMENSIONS=${DIMENSIONS}, MAX_ITERATION=${MAX_ITERATION}"
    ;;
    mm)
    ROWS_OF_BLOCKS=`get_my_ai_attribute_with_default rows_of_blocks "2"`
    COLS_OF_BLOCKS=`get_my_ai_attribute_with_default cols_of_blocks "2"`
    TOTAL_ROWS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    TOTAL_COLS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))    
    SEED_BASE=`get_my_ai_attribute_with_default seed_base "1234567890"`
    export ROWS_OF_BLOCKS
    export COLS_OF_BLOCKS
    export TOTAL_ROWS
    export TOTAL_COLS
    export SEED_BASE
    syslog_netcat "Parameters used for mm are: ROWS_OF_BLOCKS=${ROWS_OF_BLOCKS}, COLS_OF_BLOCKS=${COLS_OF_BLOCKS}, TOTAL_ROWS=${TOTAL_ROWS}, TOTAL_COLS=${TOTAL_COLS}, SEED_BASE=${SEED_BASE}"
    ;;
    nutchindexing)
    PAGES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    export PAGES
    export NUM_MAPS
    export NUM_REDS
    syslog_netcat "Parameters used for nutchindexing are: PAGES=${PAGES}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}"
    ;;
    pagerank)
    PAGES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    NUM_ITERATIONS=`get_my_ai_attribute_with_default num_iterations "3"`
    BLOCK=`get_my_ai_attribute_with_default block "0"`
    BLOCK_WIDTH=`get_my_ai_attribute_with_default block_width "16"`
    export PAGES
    export NUM_MAPS
    export NUM_REDS
    export BLOCK
    export BLOCK_WIDTH
    syslog_netcat "Parameters used for pagerank are: PAGES=${PAGES}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}, BLOCK=${BLOCK}, BLOCK_WIDTH=${BLOCK_WIDTH}"
    ;;
    sort)
    DATASIZE=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    export DATASIZE
    export NUM_MAPS
    export NUM_REDS
    syslog_netcat "Parameters used for sort are: DATASIZE=${DATASIZE}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}"
    ;;
    terasort)
    DATASIZE=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    export DATASIZE
    export NUM_MAPS
    export NUM_REDS
    syslog_netcat "Parameters used for terasort are: DATASIZE=${DATASIZE}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}"
    ;;
    wordcount)
    DATASIZE=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
    NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
    export DATASIZE
    export NUM_MAPS
    export NUM_REDS
    syslog_netcat "Parameters used for wordcount are: DATASIZE=${DATASIZE}, NUM_MAPS=${NUM_MAPS}, NUM_REDS=${NUM_REDS}"
    ;;
    *)
    syslog_netcat "Unknown load profile: ${LOAD_PROFILE}"
    exit 1
esac

syslog_netcat "Removing old HiBench report file"
rm -rf ${HIBENCH_HOME}/hibench.report

GENERATE_DATA=$(echo $GENERATE_DATA | tr '[:upper:]' '[:lower:]')

if [[ ${GENERATE_DATA} == "true" ]]
then
    OUTPUT_FILE=$(mktemp)

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)
    
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the hadoop load profile \"${LOAD_PROFILE}\"" 
    command_line="${HIBENCH_HOME}/${LOAD_PROFILE}/bin/prepare.sh"
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

    if [[ $(cat ${OUTPUT_FILE} | grep -c HDFS_BYTES_WRITTEN) -ne 0 ]]
    then
        cat ${OUTPUT_FILE} | grep HDFS_BYTES_WRITTEN | cut -d '=' -f 2 > /tmp/data_generation_size
    fi
else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the hadoop load profile \"${LOAD_PROFILE}\""     
fi

CMDLINE="${HIBENCH_HOME}/${LOAD_PROFILE}/bin/run.sh"

syslog_netcat "Benchmarking hadoop SUT: MASTER=${hadoop_master_ip} -> SLAVES=${slave_ips_csv} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=$(mktemp)

execute_load_generator "${CMDLINE}" ${OUTPUT_FILE} ${LOAD_DURATION}

syslog_netcat "..hadoop job is done. Ready to do a summary..."

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

# Collect data generation size, taking care of reporting the size
# with a minus sign in case data was not generated on this 
# run
if [[ -f /tmp/old_data_generation_size ]]
then
    datagensize=-$(cat /tmp/old_data_generation_size)
fi

if [[ -f /tmp/data_generation_size ]]
then
    datagensize=$(cat /tmp/data_generation_size)
    datagensize=$(echo "$datagensize / 1024" | bc)
    echo ${datagensize} > /tmp/data_generation_size    
    mv /tmp/data_generation_size /tmp/old_data_generation_size
fi

#Parse and report the performace

lat=`cat ${HIBENCH_HOME}/hibench.report | grep -v Type | tr -s ' ' | cut -d ' ' -f 5`
lat=`echo "${lat} * 1000" | bc`
tput=`cat ${HIBENCH_HOME}/hibench.report | grep -v Type | tr -s ' ' | cut -d ' ' -f 6`

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
throughput:$tput:tps latency:$lat:msec \
datagen_time:${datagentime}:sec \
datagen_size:${datagensize}:MB \
${SLA_RUNTIME_TARGETS}

rm ${OUTPUT_FILE}

syslog_netcat "...hadoop job finished..."

exit 0