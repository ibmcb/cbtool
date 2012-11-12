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
# - loadlevel definitions
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

HADOOP_HOME=~/hadoop-0.20.2
HADOOP_CONF_DIR=$HADOOP_HOME/conf

hadoop_master_ip=`get_ips_from_role hadoopmaster`

my_ip=`get_my_ip_addr`

slave_ips=`get_ips_from_role hadoopslave`

slave_ips_csv=`echo ${slave_ips} | sed ':a;N;$!ba;s/\n/, /g'`

#
# loadlevel defs
#

HADOOP_EXE="$HADOOP_HOME/bin/hadoop" 
jar_command="$HADOOP_EXE jar"


# terasort
tab_loadlevel_jar="$HADOOP_HOME/hadoop-*examples*.jar terasort"
tab_loadlevel_input="sort-input-1"
tab_loadlevel_output="sort-output-1"
#tab_loadlevel_geninput="$HADOOP_HOME/hadoop-*examples*.jar teragen 80000000 ${tab_loadlevel_input}"
tab_loadlevel_geninput="$HADOOP_HOME/hadoop-*examples*.jar teragen 160000000 ${tab_loadlevel_input}" #16GB in total
#tab_loadlevel_geninput="$HADOOP_HOME/hadoop-*examples*.jar teragen 1000 ${tab_loadlevel_input}"



login_user=`get_login_username`
	#	LOGIN=`get_my_ai_attribute login`

syslog_netcat "login_user: ${login_user}"
EXPOUTCOLHOST=`get_my_ai_attribute experiment_output_collection_host`
syslog_netcat "EXPOUTCOLHOST: ${EXPOUTCOLHOST}"


#Currently the following (especially the IP of CB master VM) info. is hard-coded.
#HADOOP_LOG_DEST="172.16.1.202:/home/${login_user}/hadoopautoconfig/hadoopvisualizer/logs"
#HADOOP_LOG_DEST="${EXPOUTCOLHOST}:/home/${login_user}/hadoopautoconfig/hadooptuning/resources/logs/apr-06-2012-2nodes-8GB"
#HADOOP_LOG_DEST="${EXPOUTCOLHOST}:/home/${login_user}/hadoopautoconfig/hadooptuning/resources/logs/apr-06-2012-10nodes-5GB"
HADOOP_LOG_DEST="${EXPOUTCOLHOST}:/home/${login_user}/hadoopautoconfig/hadooptuning/resources/logs/apr-16-2012-16nodes-16GB"

#redis operation
REDIS_OPT_LIST="hadoopopts"
REDIS_RES_LIST="hadoopres"

#######################################################################################
# Optional hadoop cluster configuration related options. 
#
# Used for hadoop conf's .xml files
#######################################################################################
declare -A HDFS_SITE_PROPERTIES
HDFS_SITE_PROPERTIES["dfs.block.size"]=268435456
#
declare -A MAPRED_SITE_PROPERTIES 
MAPRED_SITE_PROPERTIES["mapred.min.split.size"]=16777216
