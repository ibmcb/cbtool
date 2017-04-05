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

set_load_gen $@

AVAILABLE_NODES=$(get_available_nodes)

# Check for updated jar
GIRAPH_EXAMPLES=$(find $GIRAPH_HOME | grep giraph-examples | grep dependencies | grep -is snapshot | grep jar)

# If no updated jar, fall back to one packaged with base giraph image.
if [ -z "$GIRAPH_EXAMPLES" ]
then
    GIRAPH_EXAMPLES=$(find $GIRAPH_HOME | grep giraph-examples | grep dependencies | grep jar)
fi

NUM_WORKERS_FACTOR=`get_my_ai_attribute_with_default num_workers_factor 1`
NUM_WORKERS=$((${AVAILABLE_NODES} * ${NUM_WORKERS_FACTOR}))

# Out of core parameters
USE_OUT_OF_CORE=`get_my_ai_attribute_with_default use_out_of_core false`
USE_OUT_OF_CORE=$(echo $USE_OUT_OF_CORE | tr '[:upper:]' '[:lower:]')
OUT_OF_CORE_BASE_DIRECTORY=`get_my_ai_attribute_with_default out_of_core_base_directory /tmp`
eval OUT_OF_CORE_BASE_DIRECTORY=${OUT_OF_CORE_BASE_DIRECTORY}
mkdir -p $OUT_OF_CORE_BASE_DIRECTORY

IS_STATIC_GRAPH=`get_my_ai_attribute_with_default is_static_graph false`
IS_STATIC_GRAPH=$(echo $IS_STATIC_GRAPH | tr '[:upper:]' '[:lower:]')
MAX_PARTITIONS_IN_MEMORY=`get_my_ai_attribute_with_default max_partitions_in_memory 10`
MAX_MESSAGES_IN_MEMORY=`get_my_ai_attribute_with_default max_messages_in_memory 1000000`
MAX_HEAP_USAGE_BYTES=`get_my_ai_attribute_with_default max_heap_usage_bytes -1`

OOC_STRING="-Dgiraph.useOutOfCoreGraph=$USE_OUT_OF_CORE -Dgiraph.isStaticGraph=$IS_STATIC_GRAPH -Dgiraph.messageStoreFactoryClass=org.apache.giraph.comm.messages.out_of_core.DiskBackedMessageStoreFactory -Dgiraph.messagesDirectory=$OUT_OF_CORE_BASE_DIRECTORY/messages -Dgiraph.partitionsDirectory=$OUT_OF_CORE_BASE_DIRECTORY/partitions -Dgiraph.maxPartitionsInMemory=$MAX_PARTITIONS_IN_MEMORY -Dgiraph.maxMessagesInMemory=$MAX_MESSAGES_IN_MEMORY -Dgiraph.maxHeapUsage=$MAX_HEAP_USAGE_BYTES"

case ${LOAD_PROFILE} in
    pagerank)
    LOAD_PROFILE="PageRankBenchmark"
    EDGES_PER_VERTEX=`get_my_ai_attribute_with_default edges_per_vertex 2`
    NUM_SUPERSTEPS=`get_my_ai_attribute_with_default num_supersteps 10`
    NUM_VERTICES_FACTOR=`get_my_ai_attribute_with_default num_vertices_factor 10`
    NUM_VERTICES=$((${LOAD_LEVEL}*${NUM_VERTICES_FACTOR}))
    CMDLINE="${HADOOP_HOME}/bin/hadoop jar $GIRAPH_EXAMPLES org.apache.giraph.benchmark.$LOAD_PROFILE -e $EDGES_PER_VERTEX -s $NUM_SUPERSTEPS -v -V $NUM_VERTICES -w $NUM_WORKERS "
    if [[ ${USE_OUT_OF_CORE} == "true" ]]
    then
        CMDLINE="${HADOOP_HOME}/bin/hadoop jar $GIRAPH_EXAMPLES org.apache.giraph.benchmark.$LOAD_PROFILE $OOC_STRING -e $EDGES_PER_VERTEX -s $NUM_SUPERSTEPS -v -V $NUM_VERTICES -w $NUM_WORKERS "
    fi
    ;;
    topkpagerank)
    LOAD_PROFILE="TopkPageRankBenchmark"
    EDGES_PER_VERTEX=`get_my_ai_attribute_with_default edges_per_vertex 2`
    NUM_SUPERSTEPS=`get_my_ai_attribute_with_default num_supersteps 10`
    NUM_VERTICES_FACTOR=`get_my_ai_attribute_with_default num_vertices_factor 10`
    NUM_VERTICES=$((${LOAD_LEVEL}*${NUM_VERTICES_FACTOR}))
    NUM_PAGERANK_SUPERSTEPS=`get_my_ai_attribute_with_default num_pagerank_supersteps 5`
    NUM_TOPK_VERTICES=`get_my_ai_attribute_with_default num_topk_vertices 10`
    CMDLINE="${HADOOP_HOME}/bin/hadoop jar $GIRAPH_EXAMPLES org.apache.giraph.benchmark.$LOAD_PROFILE -e $EDGES_PER_VERTEX -s $NUM_SUPERSTEPS -v -V $NUM_VERTICES -w $NUM_WORKERS -k $NUM_TOPK_VERTICES -p $NUM_PAGERANK_SUPERSTEPS "
    if [[ ${USE_OUT_OF_CORE} == "true" ]]
    then
        CMDLINE="${HADOOP_HOME}/bin/hadoop jar $GIRAPH_EXAMPLES org.apache.giraph.benchmark.$LOAD_PROFILE $OOC_STRING -e $EDGES_PER_VERTEX -s $NUM_SUPERSTEPS -v -V $NUM_VERTICES -w $NUM_WORKERS -k $NUM_TOPK_VERTICES -p $NUM_PAGERANK_SUPERSTEPS "
    fi
    ;;
    *)
    syslog_netcat "Unknown load profile: ${LOAD_PROFILE}"
    exit 1
esac
    
DATA_HDFS=`get_my_ai_attribute_with_default dfs_data_dir /tmp/cbhadoopdata`
export DATA_HDFS

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

#Parse and report the performace

lat=$(cat ${RUN_OUTPUT_FILE} | grep "Total (m" | cut -d '=' -f 2)
#tput=`cat ${HIBENCH_HOME}/hibench.report | grep -v Type | tr -s ' ' | cut -d ' ' -f 6`

check_hadoop_cluster_state 1 1
ERROR=$?
update_app_errors $ERROR

~/cb_report_app_metrics.py \
latency:$lat:msec \
$(common_metrics)    
    
unset_load_gen

exit 0
