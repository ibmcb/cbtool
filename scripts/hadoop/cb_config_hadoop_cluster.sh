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

#####################################################################################
# Hadoop cluster preparation
# - Editing configuration files
# - Just before formatting namenode, starting masters and slaves
#####################################################################################

#####################################################################################
#Current logic works under the assumption that 
#   1. there is only one master vm which serves as a NameNode and a JobTracker, 
#      and never works as a slave (meaning DataNode, TaskTracker).
#   2. there is at least one slave machine which is physically different from
#       master vm.
#####################################################################################

syslog_netcat "hadoop_master_ip: $hadoop_master_ip"
syslog_netcat "..my_ip=$my_ip_addr .."
hadoop_version_string=`$HADOOP_HOME/bin/hadoop version | sed '1!d'`
syslog_netcat "..Hadoop Version is $hadoop_version_string .."

is_preferIPv4Stack=`cat ${HADOOP_CONF_DIR}/hadoop-env.sh | grep -c "preferIPv4Stack=true"`
if [ ${is_preferIPv4Stack} -eq 0 ]
then
	syslog_netcat "Adding extra options to hadoop-env.sh to ignore IPv6 addresses"
	echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" >> $HADOOP_CONF_DIR/hadoop-env.sh
	echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh
fi

DFS_NAME_DIR=`get_my_ai_attribute_with_default dfs_name_dir /tmp/cbhadoopname`
eval DFS_NAME_DIR=${DFS_NAME_DIR}

DFS_DATA_DIR=`get_my_ai_attribute_with_default dfs_data_dir /tmp/cbhadoopdata`
eval DFS_DATA_DIR=${DFS_DATA_DIR}

###################################################################
# Set up masters/slaves files in the hadoop master vm
###################################################################

syslog_netcat "..Updating masters/slaves files in ${HADOOP_CONF_DIR}..."
echo "${hadoop_master_ip}" > $HADOOP_CONF_DIR/masters
echo "${slave_ips}" > $HADOOP_CONF_DIR/slaves
syslog_netcat "....Done...."

syslog_netcat "..Creating files core-site.xml, hdfs-site.xml and mapred-site.xml in ${HADOOP_CONF_DIR}..."
cat << EOF > $HADOOP_CONF_DIR/core-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>fs.default.name</name>
<value>hdfs://HADOOP_NAMENODE_IP:9000</value>
<description>The name of the default file system. Either the
literal string "local" or a host:port for NDFS.
</description>
<final>true</final>
</property>
</configuration>
EOF

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	cat << EOF > $HADOOP_CONF_DIR/mapred-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>mapreduce.framework.name</name>
<value>yarn</value>
<final>true</final>
</property>

<property>
<name>mapreduce.jobhistory.address</name>
<value>HADOOP_JOBTRACKER_IP:10020</value>
<final>true</final>
</property>
</configuration>
EOF

else
	cat << EOF > $HADOOP_CONF_DIR/mapred-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>mapred.job.tracker</name>
<value>HADOOP_JOBTRACKER_IP:9001</value>
<final>true</final>
</property>
</configuration>
EOF
fi


if [ ${hadoop_use_yarn} -eq 1 ] ; then
	cat << EOF > $HADOOP_CONF_DIR/hdfs-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>dfs.replication</name>
<value>3</value>
</property>

<property>
<name>dfs.namenode.name.dir</name>
<value>DFS_NAME_DIR</value>
</property>

<property>
<name>dfs.datanode.data.dir</name>
<value>DFS_DATA_DIR</value>
</property>
</configuration>
EOF

else
	cat << EOF > $HADOOP_CONF_DIR/hdfs-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>dfs.name.dir</name>
<value>DFS_NAME_DIR</value>
<description>Determines where on the local filesystem the DFS name node
should store the name table. If this is a comma-delimited list
of directories then the name table is replicated in all of the
directories, for redundancy. </description>
<final>true</final>
</property>

<property>
<name>dfs.data.dir</name>
<value>DFS_DATA_DIR</value>
<description>Determines where on the local filesystem an DFS data node
should store its blocks. If this is a comma-delimited
list of directories, then data will be stored in all named
directories, typically on different devices.
Directories that do not exist are ignored.
</description>
</property>
</configuration>
EOF
fi

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	syslog_netcat "..Creating file yarn-site.xml in ${HADOOP_CONF_DIR}..."

	cat << EOF > $HADOOP_CONF_DIR/yarn-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>yarn.nodemanager.aux-services</name>
<value>mapreduce_shuffle</value>
<final>true</final>
</property>

<property>
<name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name>
<value>org.apache.hadoop.mapred.ShuffleHandler</value>
<final>true</final>
</property>

<property>
<name>yarn.resourcemanager.address</name>
<value>HADOOP_JOBTRACKER_IP:8032</value>
<final>true</final>
</property>

<property>
<name>yarn.resourcemanager.scheduler.address</name>
<value>HADOOP_JOBTRACKER_IP:8030</value>
<final>true</final>
</property>

<property>
<name>yarn.resourcemanager.resource-tracker.address</name>
<value>HADOOP_JOBTRACKER_IP:8031</value>
<final>true</final>
</property>
</configuration>
EOF

fi

syslog_netcat "....Done...."

###################################################################
# Editing hadoop conf.xml files to add mandatory conf knobs. 
#
# NOTE: ONE PROBLEM: the input tmp conf files should also contain 
#       the strings "HADDOP_NAMENODE_IP" and "HADOOP_JOBTRACKER_IP" !!!
#       Now we have the fix: the name of the knob and its value
#	can be defined in cb_hadoop_common.sh (see below). 
#	But currently since the hadoop conf.xml files in the golden image
#	are using have the following placeholders (HADOOP_NAMENODE_IP..),
#	we stick to the following three seds.	
###################################################################

syslog_netcat "..Editing hadoop conf files"
sed -i -e "s/HADOOP_NAMENODE_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/core-site.xml
sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/mapred-site.xml
sed -i -e "s/NUM_REPLICA/1/g" $HADOOP_CONF_DIR/hdfs-site.xml #3 is default. 1 is given for sort's performance

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/yarn-site.xml
fi


TEMP_DFS_NAME_DIR=`echo ${DFS_NAME_DIR} | sed -e "s/\//-__-__/g"`
TEMP_DFS_DATA_DIR=`echo ${DFS_DATA_DIR} | sed -e "s/\//-__-__/g"`

sed -i -e "s/DFS_NAME_DIR/${TEMP_DFS_NAME_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml
sed -i -e "s/DFS_DATA_DIR/${TEMP_DFS_DATA_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml

sed -i -e "s/-__-__/\//g" $HADOOP_CONF_DIR/hdfs-site.xml

###################################################################
# Editing hadoop conf.xml files for the optional confs 
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

if [ -d /etc/hadoop ]
then
	syslog_netcat "Since a \"/etc/hadoop/\" directory was detected, configuration files will be copied to there too"
	sudo cp $HADOOP_CONF_DIR/hadoop-env.sh /etc/hadoop
	sudo cp $HADOOP_CONF_DIR/core-site.xml /etc/hadoop
	if [ -e $HADOOP_CONF_DIR/slaves ]
	then
		sudo cp $HADOOP_CONF_DIR/slaves /etc/hadoop
	fi
	if [ -e $HADOOP_CONF_DIR/masters ]
	then
		sudo cp $HADOOP_CONF_DIR/masters /etc/hadoop
	fi
	sudo cp $HADOOP_CONF_DIR/mapred-site.xml /etc/hadop
	sudo cp $HADOOP_CONF_DIR/hdfs-site.xml /etc/hadoop
	if [ ${hadoop_use_yarn} -eq 1 ] ; then
		sudo cp $HADOOP_CONF_DIR/yarn-site.xml /etc/hadop
	fi
fi

syslog_netcat "....Done...."
exit 0
