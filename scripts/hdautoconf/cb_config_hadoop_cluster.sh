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

#source ~/.bashrc


source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

#####################################################################################
# Hadoop cluster preparation
# - Editing configuration files
# - Just before formatting namenode, starting masters and slaves
#####################################################################################


#####################################################################################
#Current logic works under the assumption that 
#   1. there is only one master vm which serves as a NameNode and a JobTracker, 
#      and never works as a slave (meaning DataNode, TaskTracker).
#   2. there is at least one slave machine which is pysically different from
#       master vm.
#####################################################################################





syslog_netcat "hadoop_master_ip: $hadoop_master_ip"
syslog_netcat "..my_ip=$my_ip .."

###################################################################
# Set up masters/slaves files in the hadoop master vm
###################################################################
syslog_netcat "Adding extra options to hadoop-env.sh to ignore IPv6 addresses"
echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" >> $HADOOP_CONF_DIR/hadoop-env.sh

if [ "$my_ip" = "$hadoop_master_ip" ]; then
	if [ -f $HADOOP_CONF_DIR/masters ]; then
		rm $HADOOP_CONF_DIR/masters; touch $HADOOP_CONF_DIR/masters
	fi
	if [ -f $HADOOP_CONF_DIR/slaves ]; then
		rm $HADOOP_CONF_DIR/slaves; touch $HADOOP_CONF_DIR/slaves
	fi
	syslog_netcat "..Editing masters/slaves files.."
	echo "$my_ip" >> $HADOOP_CONF_DIR/masters
	echo "${slave_ips}" >> $HADOOP_CONF_DIR/slaves
	syslog_netcat "....Done...."
else
	if [ -f $HADOOP_CONF_DIR/masters ]; then
		rm $HADOOP_CONF_DIR/masters
	fi
	if [ -f $HADOOP_CONF_DIR/slaves ]; then
		rm $HADOOP_CONF_DIR/slaves
	fi
fi

###################################################################
# Editing hadoop conf .xml files to add mendatory conf knobs. 
#
# NOTE: ONE PROBLEM: the input tmp conf files should also contain 
#       the strings "HADDOP_NAMENODE_IP" and "HADOOP_JOBTRACKER_IP" !!!
#       Now we have the fix: the name of the knob and its value
#	can be defined in cb_hadoop_common.sh (see below). 
#	But currently since the hadoop conf .xml files in the golden image
#	are using have the following placeholders (HADOOP_NAMENODE_IP..),
#	we stick to the following three seds.	
###################################################################

syslog_netcat "..Editing hadoop conf files"
sed -i s/HADOOP_NAMENODE_IP/$hadoop_master_ip/g $HADOOP_CONF_DIR/core-site.xml
sed -i s/HADOOP_JOBTRACKER_IP/$hadoop_master_ip/g $HADOOP_CONF_DIR/mapred-site.xml
sed -i s/NUM_REPLICA/1/g $HADOOP_CONF_DIR/hdfs-site.xml #3 is default. 1 is given for sort's performance

###################################################################
# Editing hadoop conf .xml files for the optional confs 
# as defined in cb_hadoop_common.sh
###################################################################
#core-site.xml
output_file=$HADOOP_CONF_DIR/core-site.xml
sed -i -e "s/<\/configuration>//" $output_file
for k in "${!CORE_SITE_PROPERTIES[@]}"
do
	echo "<property>" >> $output_file

	content="<name>""${k}""</name>"
	echo "${content}" >> $output_file 
	content="<value>""${CORE_SITE_PROPERTIES[$k]}""</value>"
	echo "${content}" >> $output_file 

	echo "</property>" >> $output_file

done
echo "</configuration>" >> $output_file 

#hdfs-site.xml
output_file=$HADOOP_CONF_DIR/hdfs-site.xml
sed -i -e "s/<\/configuration>//" $output_file
for k in "${!HDFS_SITE_PROPERTIES[@]}"
do
	echo "<property>" >> $output_file

	content="<name>""${k}""</name>"
	echo "${content}" >> $output_file 
	content="<value>""${HDFS_SITE_PROPERTIES[$k]}""</value>"
	echo "${content}" >> $output_file 

	echo "</property>" >> $output_file

done
echo "</configuration>" >> $output_file 

#mapred-site.xml
output_file=$HADOOP_CONF_DIR/mapred-site.xml
sed -i -e "s/<\/configuration>//" $output_file
for k in "${!MAPRED_SITE_PROPERTIES[@]}"
do
	echo "<property>" >> $output_file

	content="<name>""${k}""</name>"
	echo "${content}" >> $output_file 
	content="<value>""${MAPRED_SITE_PROPERTIES[$k]}""</value>"
	echo "${content}" >> $output_file 

	echo "</property>" >> $output_file

done
echo "</configuration>" >> $output_file 
syslog_netcat "....Done...."
