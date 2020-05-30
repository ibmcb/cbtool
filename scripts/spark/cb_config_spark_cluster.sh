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

#####################################################################################
# Hadoop cluster preparation
# - Editing configuration files
#####################################################################################

#####################################################################################
# Assumptions: 
#   1. There is only one master VM which serves as a NameNode and a 
#      Jobtracker / Resource Manager, and is not also a slave (meaning DataNode, TaskTracker).
#   2. There is at least one slave VM which is a different machine from
#       master vm.
#####################################################################################

syslog_netcat "Updating local Spark cluster configuration files..."

if [[ ! -z $SPARK_CONF_DIR ]] 
then
    syslog_netcat "Updating masters, slaves files in ${SPARK_CONF_DIR}..."
    echo "${spark_master_ip}" > $SPARK_CONF_DIR/masters
    echo "${slave_ips}" > $SPARK_CONF_DIR/slaves
fi

syslog_netcat "...masters, slaves files updated."

syslog_netcat "Updating spark-env.sh..."

cp -f $SPARK_CONF_DIR/spark-env.sh.template $SPARK_CONF_DIR/spark-env.sh

echo "export JAVA_HOME=${JAVA_HOME}" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_LOCAL_DIRS=`get_my_ai_attribute_with_default spark_local_dirs /dev/shm/spark_tmp`
eval SPARK_LOCAL_DIRS=${SPARK_LOCAL_DIRS}
echo "export SPARK_LOCAL_DIRS=$SPARK_LOCAL_DIRS" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_WORKER_DIR=`get_my_ai_attribute_with_default spark_worker_dir ~/swork`
eval SPARK_WORKER_DIR=${SPARK_WORKER_DIR}
echo "export SPARK_WORKER_DIR=$SPARK_WORKER_DIR" >> $SPARK_CONF_DIR/spark-env.sh    
            
SPARK_WORKER_CORES=`get_my_ai_attribute_with_default spark_worker_cores 8`
echo "export SPARK_WORKER_CORES=$SPARK_WORKER_CORES" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_WORKER_MEMORY=`get_my_ai_attribute_with_default spark_worker_memory 8192m`
echo "export SPARK_WORKER_MEMORY=$SPARK_WORKER_MEMORY" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_EXECUTOR_INSTANCES=`get_my_ai_attribute_with_default spark_executor_instances NA`
if [[ $SPARK_EXECUTOR_INSTANCES != "NA" ]]
then
	echo "export SPARK_EXECUTOR_INSTANCES=$SPARK_EXECUTOR_INSTANCES" >> $SPARK_CONF_DIR/spark-env.sh
fi

SPARK_EXECUTOR_CORES=`get_my_ai_attribute_with_default spark_executor_cores NA`
if [[ $SPARK_EXECUTOR_CORES != "NA" ]]
then
	echo "export SPARK_EXECUTOR_CORES=$SPARK_EXECUTOR_CORES" >> $SPARK_CONF_DIR/spark-env.sh
fi

SPARK_EXECUTOR_MEMORY=`get_my_ai_attribute_with_default spark_executor_memory 8192m`
echo "export SPARK_EXECUTOR_MEMORY=$SPARK_EXECUTOR_MEMORY" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_WORKER_OPTS=`get_my_ai_attribute_with_default spark_worker_opts NA`
if [[ $SPARK_WORKER_OPTS != "NA" ]]
then
	echo "export SPARK_WORKER_OPTS=$SPARK_WORKER_OPTS" >> $SPARK_CONF_DIR/spark-env.sh
fi

#SPARK_DAEMON_MEMORY=`get_my_ai_attribute_with_default spark_daemon_memory 1g`
#echo "export SPARK_DAEMON_MEMORY=$SPARK_DAEMON_MEMORY" >> $SPARK_CONF_DIR/spark-env.sh

SPARK_HISTORY_OPTS=`get_my_ai_attribute_with_default spark_history_opts NA`
if [[ $SPARK_HISTORY_OPTS != "NA" ]]
then
	echo "export SPARK_HISTORY_OPTS=$SPARK_HISTORY_OPTS" >> $SPARK_CONF_DIR/spark-env.sh
fi

SPARK_SHUFFLE_OPTS=`get_my_ai_attribute_with_default spark_shuffle_opts NA`
if [[ $SPARK_SHUFFLE_OPTS != "NA" ]]
then
	echo "export SPARK_SHUFFLE_OPTS=$SPARK_SHUFFLE_OPTS" >> $SPARK_CONF_DIR/spark-env.sh
fi

SPARK_DAEMON_JAVA_OPTS=`get_my_ai_attribute_with_default spark_daemon_java_opts NA`
if [[ $SPARK_DAEMON_JAVA_OPTS != "NA" ]]
then
	echo "export SPARK_DAEMON_JAVA_OPTS=$SPARK_DAEMON_JAVA_OPTS" >> $SPARK_CONF_DIR/spark-env.sh
fi

syslog_netcat "...spark-env.sh updated."

syslog_netcat "Done updating local Spark cluster configuration files."
exit 0
