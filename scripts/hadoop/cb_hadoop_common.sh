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
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

HADOOP_HOME=~/hadoop-0.20.2
HADOOP_CONF_DIR=$HADOOP_HOME/conf

hadoop_master_ip=`get_ips_from_role hadoopmaster`

slave_ips=`get_ips_from_role hadoopslave`

slave_ips_csv=`echo ${slave_ips} | sed ':a;N;$!ba;s/\n/, /g'`

#############################################################################
# LOAD_LEVEL defs -- different hadoop jobs
#
# - jar / input / output
#############################################################################

HADOOP_EXE="$HADOOP_HOME/bin/hadoop" 
jar_command="$HADOOP_EXE jar"

declare -A tab_LOAD_LEVEL_jar
declare -A tab_LOAD_LEVEL_input
declare -A tab_LOAD_LEVEL_output
declare -A tab_LOAD_LEVEL_geninput
declare -A tab_LOAD_LEVEL_options

if [ x"$my_role" == x"hadoopmaster" ]
then

	load_level=`get_my_ai_attribute load_level`
	load_factor=`get_my_ai_attribute_with_default tradedb_size 1000`
	
	is_max_min=`echo ${load_level} | grep -c "I"`
	
	if [ "${is_max_min}" = "1" ]
	then
		load_level_min=`echo $load_level | cut -d "I" -f 4`
		load_level_max=`echo $load_level | cut -d "I" -f 5`
	else
		load_level_min=${load_level}
		load_level_max=$((${load_level}+1))
	fi 
	syslog_netcat "Mininum load level is ${load_level_min}. Maximum load level is ${load_level_max}"
	for ((i = ${load_level_min} ; i < ${load_level_max} ; i++))
	do
	## terasort with 100-byte records
		tab_LOAD_LEVEL_jar[$i]="$HADOOP_HOME/hadoop-*examples*.jar terasort"
		tab_LOAD_LEVEL_input[$i]="sort-input-$i"
		tab_LOAD_LEVEL_output[$i]="sort-output-$i"
		teragen_size=$(($i*${load_factor}))
		tab_LOAD_LEVEL_geninput[$i]="$HADOOP_HOME/hadoop-*examples*.jar teragen ${teragen_size} ${tab_LOAD_LEVEL_input[$i]}" #giga-sort
		tab_LOAD_LEVEL_options[$i]=
	done
fi
## random writer - not used so far
#tab_LOAD_LEVEL_jar[5]="$HADOOP_HOME/hadoop-*examples*.jar randomwriter"
#tab_LOAD_LEVEL_input[5]=
#tab_LOAD_LEVEL_output[5]="rdw-5"
#tab_LOAD_LEVEL_geninput[5]=
#tab_LOAD_LEVEL_options[5]="-Dtest.randomwrite.bytes_per_map=1000"
	
## wordcount - not used so far
#tab_LOAD_LEVEL_jar[6]="$HADOOP_HOME/hadoop-*examples*.jar wordcount"
#tab_LOAD_LEVEL_input[6]="wc-input-1"
#tab_LOAD_LEVEL_output[6]="wc-output-1"
#tab_LOAD_LEVEL_geninput[6]= "$HADOOP_EXE fs -mkdir ${tab_LOAD_LEVEL_input[6]}; $HADOOP_EXE fs -put ./${tab_LOAD_LEVEL_input[3]} ${tab_LOAD_LEVEL_input[3]}"
#tab_LOAD_LEVEL_options[6]=  #could be [-m <#maps>] [-r <#reducers>]
	
#######################################################################################
# Resuling log destinations 
#
# Should be set correctly by the user
# Currently the following (especially the IP of CB master VM) info. is hard-coded.
#######################################################################################
#login_user=`get_login_username`
	
#HADOOP_LOG_DEST="172.16.1.202:/home/${login_user}/hadoopautoconfig/hadoopvisualizer/logs"
	
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
