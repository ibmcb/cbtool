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

syslog_netcat "Stopping Hadoop cluster on master ${hadoop_master_ip} with slaves ${slave_ips_csv} (my ip is ${my_ip_addr})"

#start mapreduce
if [ x"$my_role" == x"giraphmaster" ]; then
	if [ ${hadoop_use_yarn} -eq 1 ] ; then
		syslog_netcat "....stopping namenode, yarn, and jobhistory daemons...."
		${HADOOP_HOME}/sbin/hadoop-daemon.sh stop namenode
		${HADOOP_HOME}/sbin/yarn-daemon.sh stop resourcemanager
		${HADOOP_HOME}/sbin/mr-jobhistory-daemon.sh stop historyserver
	else
		syslog_netcat "....stopping hadoop service...."
		${HADOOP_HOME}/bin/stop-mapred.sh
		${HADOOP_HOME}/bin/stop-dfs.sh
	fi
else
	if [ ${hadoop_use_yarn} -eq 1 ] ; then
		${HADOOP_HOME}/sbin/hadoop-daemon.sh stop datanode
		${HADOOP_HOME}/sbin/yarn-daemon.sh stop nodemanager
	fi
fi

syslog_netcat "......exit......"
exit 0
