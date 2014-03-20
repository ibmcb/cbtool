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

#####################################################################################
# Common routines for hadoop 
# - getting the host ip
# - getting the hadoop master ip
# - hadoop paths
# - LOAD_LEVEL definitions
# - Determine whether to use original map-reduce or YARN
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

if [[ -z ${JAVA_HOME} ]]
then
	JAVA_HOME=`get_my_ai_attribute_with_default java_home ~/jdk1.6.0_21`
	eval JAVA_HOME=${JAVA_HOME}
	if [[ -f ~/.bashrc ]]
	then
		is_java_home_export=`grep -c "JAVA_HOME=${JAVA_HOME}" ~/.bashrc`
		if [[ $is_java_home_export -eq 0 ]]
		then
			syslog_netcat "Adding JAVA_HOME to bashrc"
			echo "export JAVA_HOME=${JAVA_HOME}" >> ~/.bashrc
		fi
	fi
fi

if [[ -z ${HADOOP_HOME} ]]
then
	HADOOP_HOME=`get_my_ai_attribute_with_default hadoop_home ~/hadoop-1.2.1`
	
	HADOOP_VERSION=`echo ${HADOOP_HOME} | sed 's/hadoop-//g' | sed 's/-bin//g'` 
	eval HADOOP_HOME=${HADOOP_HOME}

	if [[ -f ~/.bashrc ]]
	then
		is_hadoop_home_export=`grep -c "HADOOP_HOME=${HADOOP_HOME}" ~/.bashrc`
		if [[ $is_hadoop_home_export -eq 0 ]]
		then
			syslog_netcat "Adding HADOOP_HOME to bashrc"
			echo "export HADOOP_HOME=${HADOOP_HOME}" >> ~/.bashrc
			echo "export PATH=\$PATH:$HADOOP_HOME/bin" >> ~/.bashrc
		fi
	fi
fi

if [[ -z ${HADOOP_CONF_DIR} ]]
then
	if [[ -d $HADOOP_HOME/conf ]]; then
		HADOOP_CONF_DIR=$HADOOP_HOME/conf
		syslog_netcat "Setting HADOOP_CONF_DIR to $HADOOP_CONF_DIR"
	else
		if [[ -d $HADOOP_HOME/etc/hadoop ]]; then
			HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
			syslog_netcat "Setting HADOOP_CONF_DIR to $HADOOP_CONF_DIR"
		else
			syslog_netcat "Error - Cannot find hadoop configuration directory."
		fi
	fi
fi

if [[ -z ${HIBENCH_HOME} ]]
then
	HIBENCH_HOME=`get_my_ai_attribute_with_default hibench_home ~/HiBench`

	if [[ -f ~/.bashrc ]]
	then
		is_hibench_home_export=`grep -c "HIBENCH_HOME=${HIBENCH_HOME}" ~/.bashrc`
		if [[ $is_hibench_home_export -eq 0 ]]
		then
			syslog_netcat "Adding HIBENCH_HOME to bashrc"
			echo "export HIBENCH_HOME=${HIBENCH_HOME}" >> ~/.bashrc
		fi
	fi
fi

hadoop_master_ip=`get_ips_from_role hadoopmaster`

slave_ips=`get_ips_from_role hadoopslave`

slave_ips_csv=`echo ${slave_ips} | sed ':a;N;$!ba;s/\n/, /g'`

# Determine whether to use YARN aka MRv2
hadoop_version=`$HADOOP_HOME/bin/hadoop version | sed '1!d'`
hadoop_version_major=`echo ${hadoop_version} | sed 's/Hadoop \([0-9]*\)\..*/\1/'`
hadoop_version_minor=`echo ${hadoop_version} | sed 's/Hadoop [0-9]*\.\([0-9]*\).*/\1/'`

hadoop_use_yarn=0
if [ $hadoop_version_major -gt 2 ]; then
   hadoop_use_yarn=1
else
   if [[ $hadoop_version_major -eq 2  &&  $hadoop_version_minor -gt 1 ]]; then
      hadoop_use_yarn=1
   fi
fi

#######################################################################################
# Result log destinations 
#
# Should be set correctly by the user
# Currently the following (especially the IP of CB master VM) info. is hard-coded.
#######################################################################################
	
#HADOOP_LOG_DEST="172.16.1.202:/home/${my_login_username}/hadoopautoconfig/hadoopvisualizer/logs"
	
#######################################################################################
# Optional hadoop cluster configuration related options. 
#
# Used for hadoop conf's .xml files
#######################################################################################
#declare -A HDFS_SITE_PROPERTIES
#HDFS_SITE_PROPERTIES["dfs.block.size"]=67108864
#
#declare -A MAPRED_SITE_PROPERTIES 
#MAPRED_SITE_PROPERTIES["mapred.min.split.size"]=0
#MAPRED_SITE_PROPERTIES["mapred.max.split.size"]=16777216
