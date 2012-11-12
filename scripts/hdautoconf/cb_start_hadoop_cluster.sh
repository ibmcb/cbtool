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

syslog_netcat "Configuring Hadoop cluster on master ${hadoop_master_ip} with slaves ${slave_ips_csv} (my ip is ${my_ip})"

#start mapreduce
if [ x"$my_role" == x"hadoopmaster" ]; then
	syslog_netcat "....Formating namenode...."
	${HADOOP_HOME}/bin/hadoop namenode -format

	syslog_netcat "....starting hadoop service...."
	${HADOOP_HOME}/bin/start-dfs.sh
	${HADOOP_HOME}/bin/start-mapred.sh
fi

#Prepare input data for the hadoop execution
# Run teragen!
if [ x"$my_role" == x"hadoopmaster" ]; then
	syslog_netcat "....Generate input by \"${tab_loadlevel_geninput} \"!...."
	$jar_command ${tab_loadlevel_geninput} 2>&1 | while read line; do
		syslog_netcat "$line"
	done
	syslog_netcat "......Done......"
fi
syslog_netcat "......exit......"
provision_application_stop $START

