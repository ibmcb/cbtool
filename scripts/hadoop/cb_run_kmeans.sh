#!/usr/bin/env bash
#/*******************************************************************************
# Copyright (c) 2014 Gartner, Inc.
# ...and you thought Gartner didn't do any real work!

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

# This script runs kmeans from a CloudBench-created hadoopmaster instance
# Assumines CloudBench has already executed cb_start_hadoop_cluster scripts, and thus Hadoop daemons are already running
# Probably assumes lots of other things too, like that you know what the heck you're doing

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
        source $dir/cb_common.sh
else
        source $dir/../common/cb_common.sh
fi

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

syslog_netcat "Starting script to generate kmeans data and run kmeans."

export COMPRESS_GLOBAL=0
export HADOOP_EXECUTABLE=${HADOOP_HOME}/bin/hadoop
export MAPRED_EXECUTABLE=${HADOOP_HOME}/bin/mapred
export HADOOP_EXAMPLES_JAR=${HADOOP_HOME}/hadoop-examples.jar
export HADOOP_VERSION=hadoop2
export HIBENCH_VERSION="2.2"
export HIBENCH_CONF=${HIBENCH_HOME}/conf
export HIBENCH_REPORT=${HIBENCH_HOME}/hibench.report

if [ -f "${HIBENCH_CONF}/funcs.sh" ]; then
    . "${HIBENCH_CONF}/funcs.sh"
fi

export MAHOUT_HOME=${HIBENCH_HOME}/common/mahout-distribution-0.7-$HADOOP_VERSION
export DATATOOLS=${HIBENCH_HOME}/common/autogen/dist/datatools.jar

export DATA_HDFS=/HiBench

# Get kmeans parameters set in CB configuration files
NUM_OF_SAMPLES=`get_my_ai_attribute_with_default num_of_samples "3000000"`
DIMENSIONS=`get_my_ai_attribute_with_default dimensions "20"`
NUM_OF_CLUSTERS=`get_my_ai_attribute_with_default num_of_clusters "5"`
MAX_ITERATION=`get_my_ai_attribute_with_default max_iteration "5"`
export NUM_OF_SAMPLES
export DIMENSIONS
export NUM_OF_CLUSTERS
export MAX_ITERATION

syslog_netcat "Reading kmeans parameters from HiBench kmeans configuration file..."
cd ${HIBENCH_HOME}/kmeans/conf
source ${HIBENCH_HOME}/kmeans/conf/configure.sh

syslog_netcat "Removing any old kmeans input data files from HDFS..."
$HADOOP_EXECUTABLE dfs -rm -r ${INPUT_HDFS}
COMPRESS_OPT="-compress false"

cd ${HIBENCH_HOME}/kmeans/bin
rm -rf $TMPLOGFILE

START_TIME_GENERATOR=`date +%s`

syslog_netcat "Generating kmeans data: CLUSTERS=${NUM_OF_CLUSTERS} SAMPLES=${NUM_OF_SAMPLES} SAMPLES_PER_FILE=${SAMPLES_PER_INPUTFILE} DIMENSIONS=${DIMENSIONS}"
OPTION="-sampleDir ${INPUT_SAMPLE} -clusterDir ${INPUT_CLUSTER} -numClusters ${NUM_OF_CLUSTERS} -numSamples ${NUM_OF_SAMPLES} -samplesPerFile ${SAMPLES_PER_INPUTFILE} -sampleDimension ${DIMENSIONS}"
export HADOOP_CLASSPATH=`${MAHOUT_HOME}/bin/mahout classpath | tail -1`
$HADOOP_EXECUTABLE --config $HADOOP_CONF_DIR jar ${DATATOOLS} org.apache.mahout.clustering.kmeans.GenKMeansDataset -libjars $MAHOUT_HOME/examples/target/mahout-examples-0.7-job.jar ${COMPRESS_OPT} ${OPTION} 2>&1 | tee $TMPLOGFILE

STOP_TIME_GENERATOR=`date +%s`
syslog_netcat "Finished kmeans data generation."
KMEANS_LOAD_TIME=$(($STOP_TIME_GENERATOR - $START_TIME_GENERATOR))

COMPRESS_OPT="-Dmapred.output.compress=false"

syslog_netcat "Removing any old kmeans output data files from HDFS..."
$HADOOP_EXECUTABLE dfs -rmr ${OUTPUT_HDFS}

if [ "x"$HADOOP_VERSION == "xhadoop2" ]; then
  SSIZE=`grep "BYTES_DATA_GENERATED=" $TMPLOGFILE | sed 's/BYTES_DATA_GENERATED=//'`
else
  SSIZE=$($HADOOP_EXECUTABLE job -history $INPUT_SAMPLE | grep 'HiBench.Counters.*|BYTES_DATA_GENERATED')
  SSIZE=${SSIZE##*|}
  SSIZE=${SSIZE//,/}
fi
CSIZE=`dir_size $INPUT_CLUSTER`
SIZE=$(($SSIZE+$CSIZE))
syslog_netcat "kmeans database size: ${SIZE} bytes"

OPTION="$COMPRESS_OPT -i ${INPUT_SAMPLE} -c ${INPUT_CLUSTER} -o ${OUTPUT_HDFS} -x ${MAX_ITERATION} -ow -cl -cd 0.5 -dm org.apache.mahout.common.distance.EuclideanDistanceMeasure -xm mapreduce"

syslog_netcat "Launching kmeans mahout job with options {$OPTION}"

START_TIME=`timestamp`
${HIBENCH_HOME}/common/mahout-distribution-0.7-$HADOOP_VERSION/bin/mahout kmeans ${OPTION} | while read line ; do
     syslog_netcat "$line"
     echo $line
done
END_TIME=`timestamp`

# post-running
syslog_netcat "kmeans mahout job complete. Generating HiBench report..."
gen_report "KMEANS" ${START_TIME} ${END_TIME} ${SIZE}

syslog_netcat "Parsing Hadoop config files and HiBench report file for test results..."
slavecount=`wc -l "${HADOOP_CONF_DIR}/slaves" | awk '{print $1'}`
lat=`cat ${HIBENCH_REPORT} | grep -v Type | tr -s ' ' | cut -d ' ' -f 5`
tput=`cat ${HIBENCH_REPORT} | grep -v Type | tr -s ' ' | cut -d ' ' -f 6`

syslog_netcat "Reporting results to CloudBench..."
syslog_netcat "KMEANS results: slaves=${slavecount},samples=${NUM_OF_SAMPLES},clusters=${NUM_OF_CLUSTERS},dimensions=${DIMENSIONS},db_size=${SIZE},db_load_time=${KMEANS_LOAD_TIME},throughput=$tput,run_time=$lat"
~/cb_report_app_metrics.py load_profile:${LOAD_PROFILE}:name load_duration:${LOAD_DURATION}:sec slaves:${slavecount}:instances dataset_samples:${NUM_OF_SAMPLES}:samples dataset_clusters:${NUM_OF_CLUSTERS}:clusters dataset_dimensions:${DIMENSIONS}:dimensions dataset_size:${SIZE}:bytes db_load_time:${KMEANS_LOAD_TIME}:sec throughput:$tput:Bps time:$lat:sec

syslog_netcat "Kmeans finished."

