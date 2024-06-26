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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

set_load_gen $@

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default regenerate_data false`
fi

export LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor "1000"`

export GENERATE_DATA=$(echo $GENERATE_DATA | tr '[:upper:]' '[:lower:]')

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_config_spark_common.sh

export SPARK_GATK4_HOME=`get_my_ai_attribute_with_default spark_gatk4_home ~/gatk-4.5.0.0`
eval SPARK_GATK4_HOME=${SPARK_GATK4_HOME}

export SPARK_GATK4_HDFS_TARGET=`get_my_ai_attribute_with_default spark_gatk4_hdfs_target q4_spark_eval`

export SPARK_GATK4_DIRECT_MEMORY=`get_my_ai_attribute_with_default spark_gatk4_direct_memory 4294967296`    
export SPARK_GATK4_PAIRHMM=`get_my_ai_attribute_with_default spark_gatk4_pairmm LOGLESS_CACHING`    

export SPARKBENCH_HOME=$(find ~ 2>&1 | grep examples/minimal-example.conf | sed 's^/examples/minimal-example.conf^^g')

export SPARK_MASTER_IP=$(get_ips_from_role sparkmaster)
export SPARK_MASTER_HOST=spark://$SPARK_MASTER_IP:7077

export SPARK_HDFS_BASE=$($HADOOP_HOME/bin/hdfs getconf -confKey fs.defaultFS)

export SPARK_HDFS_INPUT=$SPARK_HDFS_BASE/user/$(whoami)/$SPARK_GATK4_HDFS_TARGET
export SPARK_HDFS_OUTPUT=$SPARK_HDFS_BASE/user/$(whoami)/$SPARK_GATK4_HDFS_TARGET/output

if [[ ${GENERATE_DATA} == "true" && $(echo ${LOAD_PROFILE} | grep gatk4) ]]
then

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    START_GENERATION=$(get_time)
    
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the spark load profile \"${LOAD_PROFILE}\"" 
    
    if [[ ${LOAD_PROFILE} == "gatk4s" ]]
    then
        _SPARK_GATK4_SOURCE_SDIR=small
    elif [[ ${LOAD_PROFILE} == "gatk4f" ]]
    then
        _SPARK_GATK4_SOURCE_SDIR=full
    elif [[ ${LOAD_PROFILE} == "gatk4m" ]]
    then
        _SPARK_GATK4_SOURCE_SDIR=medium
    fi        

	_SPARK_GATK4_SOURCE_CDIRS=$HOME
            
    mount | grep -v nfsd | grep -v xenfs | grep nfs > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        _SPARK_GATK4_SOURCE_CDIRS="$HOME $(mount | grep -v nfsd | grep -v xenfs | grep nfs | awk '{ print $3 }')"
    fi

    for _SPARK_GAT4_DIR in ${_SPARK_GATK4_SOURCE_CDIRS}
    do
        _SPARK_GATK4_CDIR=$(find ${_SPARK_GAT4_DIR} -type d -not -empty | grep -i gatk4 | grep ${_SPARK_GATK4_SOURCE_SDIR} | head -n 1)
        if [[ ! -z ${_SPARK_GATK4_CDIR} ]]    
        then
            sudo ls ${_SPARK_GATK4_CDIR} > /dev/null 2>&1
            if [[ $? -eq 0 ]]
            then
                SPARK_GATK4_SOURCE_DIR=${_SPARK_GATK4_CDIR}
                break
            fi
        fi
    done
    
    eval SPARK_GATK4_SOURCE_DIR=${SPARK_GATK4_SOURCE_DIR}
    export SPARK_GATK4_SOURCE_DIR=$SPARK_GATK4_SOURCE_DIR

    SPARK_GATK4_HDFS_TARGET=`get_my_ai_attribute_with_default spark_gatk4_hdfs_target q4_spark_eval`    

    syslog_netcat "Populating HDFS \"$SPARK_GATK4_HDFS_TARGET\" with data from \"$SPARK_GATK4_SOURCE_DIR\"..." 

    ERROR=0
    
    $HADOOP_HOME/bin/hadoop fs -stat $SPARK_GATK4_HDFS_TARGET > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        $HADOOP_HOME/bin/hadoop fs -rm -f -R $SPARK_GATK4_HDFS_TARGET 
        COUT=$?
        let ERROR+=$COUT
    fi
    
    # Create data directory in HDFS
    $HADOOP_HOME/bin/hadoop fs -mkdir -p $SPARK_GATK4_HDFS_TARGET
    COUT=$?
    let ERROR+=$COUT    

    sudo chmod -R 755 $SPARK_GATK4_SOURCE_DIR
    if [[ ${LOAD_PROFILE} == "gatk4s" ]] && [[ ! -e /user/$USER/$SPARK_GATK4_HDFS_TARGET ]] ; then
            sudo mkdir -p /user/$USER/
            sudo cp -r $SPARK_GATK4_SOURCE_DIR /user/$USER/$SPARK_GATK4_HDFS_TARGET
    fi
    $HADOOP_HOME/bin/hdfs dfs -copyFromLocal $SPARK_GATK4_SOURCE_DIR/* /user/$USER/$SPARK_GATK4_HDFS_TARGET/.            
    COUT=$?
    let ERROR+=$COUT
    
    END_GENERATION=$(get_time)
    update_app_errors $ERROR        

    DATA_GENERATION_TIME=$(expr ${END_GENERATION} - ${START_GENERATION})
    update_app_datagentime ${DATA_GENERATION_TIME}
    update_app_datagensize $($HADOOP_HOME/bin/hdfs dfs -du -s $SPARK_GATK4_HDFS_TARGET | awk '{ print $1 }')

else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the spark load profile \"${LOAD_PROFILE}\""
fi

MULTIPLE=0

if [[ ${LOAD_PROFILE} == "pi" ]]
then
    export SPARKBENCH_CONFIG_FILE=cbpi.conf
    cp $SPARKBENCH_HOME/examples/minimal-example.conf $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    export NUM_SLICES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))    
    sed -i "s/slices =.*/slices = $NUM_SLICES/g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    CMDLINE="${SPARKBENCH_HOME}/bin/spark-bench.sh ${SPARKBENCH_HOME}/examples/$SPARKBENCH_CONFIG_FILE"    
elif [[ ${LOAD_PROFILE} == "csv-vs-parquet" ]]
then
    export SPARKBENCH_CONFIG_FILE=cbcsv-vs-parquet.conf    
    cp $SPARKBENCH_HOME/examples/csv-vs-parquet.conf $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    export NUM_ROWS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    export NUM_COLS=$((${LOAD_LEVEL}*24))
    sed -i "s^spark-home =.*^spark-home = \"$SPARK_HOME\"^g"  $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    sed -i "s^master =.*^master = \"$SPARK_MASTER_HOST\"^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    sed -i "s^executor-memory =.*^executor-memory = \"${SPARK_EXECUTOR_MEMORY}m\"^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE    
    sed -i "s^executor-memory =.*^executor-memory = \"${SPARK_EXECUTOR_MEMORY}m\"^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    sed -i "s^rows =.*^rows = $NUM_ROWS^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    sed -i "s^cols =.*^cols = $NUM_COLS^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    sed -i "s^hdfs:///tmp/^$SPARK_HDFS_BASE/user/$(whoami)/^g" $SPARKBENCH_HOME/examples/$SPARKBENCH_CONFIG_FILE
    CMDLINE="${SPARKBENCH_HOME}/bin/spark-bench.sh ${SPARKBENCH_HOME}/examples/$SPARKBENCH_CONFIG_FILE"
elif [[ ${LOAD_PROFILE} == "gatk4s" ]]
then
    # Source: https://github.com/broadinstitute/gatk/blob/master/scripts/spark_eval/small_reads-pipeline_hdfs.sh
    CMDLINE="python3 $SPARK_GATK4_HOME/gatk ReadsPipelineSpark -I $SPARK_HDFS_INPUT/CEUTrio.HiSeq.WGS.b37.NA12878.20.21.bam -O $SPARK_HDFS_OUTPUT/CEUTrio.HiSeq.WGS.b37.NA12878.20.21_LOAD.vcf -R $SPARK_HDFS_INPUT/human_g1k_v37.20.21.fasta --known-sites $SPARK_HDFS_INPUT/dbsnp_138.b37.20.21.vcf -pairHMM $SPARK_GATK4_PAIRHMM --max-reads-per-alignment-start 10 --verbosity ERROR -- --spark-runner SPARK --spark-master $SPARK_MASTER_HOST" 
    MULTIPLE=1
elif [[ ${LOAD_PROFILE} == "gatk4m" ]]
then
    # SOURCE: https://github.com/broadinstitute/gatk/blob/master/scripts/spark_eval/exome_md-bqsr-hc_hdfs.sh
    # This is only one stage that is part of a 3-stage job.
    # We could explore the performance utilization of the other stages, if necessary
    CMDLINE="python3 $SPARK_GATK4_HOME/gatk MarkDuplicatesSpark -I $SPARK_HDFS_INPUT/NA12878.ga2.exome.maq.raw.bam -O $SPARK_HDFS_OUTPUT/markdups-sharded_LOAD --sharded-output true --verbosity ERROR -- --spark-runner SPARK --spark-master $SPARK_MASTER_HOST"
    MULTIPLE=1
elif [[ ${LOAD_PROFILE} == "gatk4f" ]]
then
    CMDLINE="python3 $SPARK_GATK4_HOME/gatk ReadsPipelineSpark -I $SPARK_HDFS_INPUT/WGS-G94982-NA12878-no-NC_007605.bam -O $SPARK_HDFS_OUTPUT/WGS-G94982-NA12878_LOAD.vcf -R $SPARK_HDFS_INPUT/human_g1k_v37.2bit --known-sites $SPARK_HDFS_INPUT/dbsnp_138.b37.vcf -pairHMM $SPARK_GATK4_PAIRHMM --max-reads-per-alignment-start 10 --verbosity ERROR -- --spark-runner SPARK --spark-master $SPARK_MASTER_HOST"
    MULTIPLE=1
fi

cores=$(wget http://localhost:8080/json -O - -o /dev/null | jq .cores)
memory=$(wget http://localhost:8080/json -O - -o /dev/null | jq .memory)
workers=$(wget http://localhost:8080/json -O - -o /dev/null | jq .aliveworkers)

if [ $MULTIPLE -eq 1 ] ; then
	((cores=cores/LOAD_LEVEL))
	((memory=memory/LOAD_LEVEL/workers))

	for num in $(seq 1 ${LOAD_LEVEL}) ; do
		COMMAND=$(echo "$CMDLINE" | sed "s/LOAD/${num}/g")
		COMMAND="$COMMAND --total-executor-cores ${cores} --executor-memory ${memory}m --driver-memory ${SPARK_DRIVER_MEMORY}m"
		execute_load_generator "${COMMAND}" ${RUN_OUTPUT_FILE}.${num} ${LOAD_DURATION} &
	done
	wait
else
	execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE}.1 ${LOAD_DURATION}
fi

#Parse and report the performace

echo $LOAD_PROFILE | grep gatk4 > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    lat=`cat ${RUN_OUTPUT_FILE}.1 | grep "${LOAD_PROFILE}|" | awk '{ print $2 }' | cut -d '|' -f 1`
else
    lat=`cat ${RUN_OUTPUT_FILE}.1 | grep "Elapsed time" | awk '{ print $11 }'`
    lat=`echo "${lat} * 60" | bc`
fi

check_hadoop_cluster_state 1 1
ERROR=$?
update_app_errors $ERROR

~/cb_report_app_metrics.py \
latency:$lat:msec \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
$(common_metrics)    
    
unset_load_gen

exit 0
