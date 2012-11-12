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
START=`provision_application_start`

syslog_netcat "Starting Hadoop cluster on master ${hadoop_master_ip} with slaves ${slave_ips_csv} (my ip is ${my_ip_addr})"

#start mapreduce
if [ x"$my_role" == x"hadoopmaster" ]; then
	syslog_netcat "....Formating namenode...."
	${HADOOP_HOME}/bin/hadoop namenode -format

	syslog_netcat "....starting hadoop service...."
	${HADOOP_HOME}/bin/start-dfs.sh
	${HADOOP_HOME}/bin/start-mapred.sh
fi

#Prepare input data for the hadoop execution
#Run teragen!

if [ x"$my_role" == x"hadoopmaster" ]; then

	dont_generate_input_data=`get_my_ai_attribute dont_generate_input_data`
	dont_generate_input_data=`echo ${dont_generate_input_data} | tr '[:upper:]' '[:lower:]'`

	if [ "${dont_generate_input_data}" = "true" ]
	then
		syslog_netcat "AI parameter \"dont_generate_input_data\" set to \"true\". No input data will be generated (useful for diagnostic purposes)"
	else
		for key in "${!tab_LOAD_LEVEL_geninput[@]}"
		do
			syslog_netcat "....Generate input by \"${tab_LOAD_LEVEL_geninput[$key]} \"!...."
			$jar_command ${tab_LOAD_LEVEL_geninput[$key]} 2>&1 | while read line; do
				syslog_netcat "$line"
			done
			syslog_netcat "......Done......"
		done
	fi
fi
syslog_netcat "......exit......"
provision_application_stop $START
exit 0
