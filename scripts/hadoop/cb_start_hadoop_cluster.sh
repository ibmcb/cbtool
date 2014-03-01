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
	if [ ${hadoop_use_yarn} -eq 1 ] ; then
		syslog_netcat "...Formatting Namenode..."
		${HADOOP_HOME}/bin/hadoop namenode -format -force

		syslog_netcat "...Starting Namenode daemon..."
		${HADOOP_HOME}/sbin/hadoop-daemon.sh start namenode

		syslog_netcat "...Starting YARN Resource Manager daemon..."
		${HADOOP_HOME}/sbin/yarn-daemon.sh start resourcemanager
		syslog_netcat "...Starting Job History daemon..."
		${HADOOP_HOME}/sbin/mr-jobhistory-daemon.sh start historyserver

	else
		syslog_netcat "....Formating namenode...."
		${HADOOP_HOME}/bin/hadoop namenode -format

		syslog_netcat "....starting hadoop services...."
		syslog_netcat "....starting primary NameNode...."
		${HADOOP_HOME}/bin/start-dfs.sh
		syslog_netcat "....starting JobTracker...."
		${HADOOP_HOME}/bin/start-mapred.sh
	#	${HADOOP_HOME}/bin/start-all.sh
	fi
else
	if [ ${hadoop_use_yarn} -eq 1 ] ; then
		syslog_netcat "....starting datanode on ${my_ip_addr} ..."
		${HADOOP_HOME}/sbin/hadoop-daemon.sh start datanode
		datanode_error=`grep FATAL ${HADOOP_HOME}/logs/hadoop*.log`
		if [ x"$datanode_error" != x ] ; then
		        syslog_netcat "Error starting datanode on ${my_ip_addr}: ${datanode_error} "
		        exit 1
		fi
		syslog_netcat "....starting nodemanager on ${my_ip_addr} ..."
		${HADOOP_HOME}/sbin/yarn-daemon.sh start nodemanager
	fi
fi

if [ x"$my_role" == x"hadoopmaster" ]; then
	syslog_netcat "Waiting for all Datanodes to become available....."
	syslog_netcat "`${HADOOP_HOME}/bin/hadoop dfsadmin -report`"
	while [ z${DATANODES_AVAILABLE} != z"true" ]
	do
	    DFSADMINOUTPUT=`${HADOOP_HOME}/bin/hadoop dfsadmin -report | grep "Datanodes available"`
	    AVAILABLE_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 2`
	    TOTAL_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 3 | sed 's/(//g'`
		if [[ ${AVAILABLE_NODES} -ne 0 && z${AVAILABLE_NODES} == z${TOTAL_NODES} ]]
	    then
	        DATANODES_AVAILABLE="true"
	    else
	        DATANODES_AVAILABLE="false"
	    fi
	    sleep 1
	done
	syslog_netcat "All Datanodes (${TOTAL_NODES}) available now"

	if [ ${hadoop_use_yarn} -eq 1 ] ; then

		syslog_netcat "Creating map-reduce history directory on HDFS filesystem..."
		hadoop dfs -mkdir /mr-history
		hadoop dfs -mkdir /mr-history/done
		hadoop dfs -mkdir /mr-history/tmp
		hadoop dfs -chmod -R 777 /mr-history/done
		hadoop dfs -chmod -R 777 /mr-history/tmp
	fi

fi


if [ x"$my_role" == x"hadoopmaster" ]; then
	if [ -f ~/mm.tar ]; then 
		cd ${HIBENCH_HOME}
		tar -xvf ~/mm.tar
		rm ~/mm.tar
	fi
fi

syslog_netcat "......exit......"
provision_application_stop $START
exit 0
