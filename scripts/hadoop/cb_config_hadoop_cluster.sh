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
#####################################################################################

#####################################################################################
# Assumptions: 
#   1. There is only one master VM which serves as a NameNode and a 
#      Jobtracker / Resource Manager, and is not also a slave (meaning DataNode, TaskTracker).
#   2. There is at least one slave VM which is a different machine from
#       master vm.
#####################################################################################

syslog_netcat "Updating local Hadoop cluster configuration files..."

hadoop_version_string=`$HADOOP_HOME/bin/hadoop version | sed '1!d'`
syslog_netcat "Hadoop home directory is ${HADOOP_HOME}"
syslog_netcat "Hadoop version is $hadoop_version_string"
syslog_netcat "Hadoop configuration directory is ${HADOOP_CONF_DIR}"

DFS_NAME_DIR=`get_my_ai_attribute_with_default dfs_name_dir /tmp/cbhadoopname`
eval DFS_NAME_DIR=${DFS_NAME_DIR}
syslog_netcat "Local directory for Hadoop namenode is ${DFS_NAME_DIR}"

DFS_DATA_DIR=`get_my_ai_attribute_with_default dfs_data_dir /tmp/cbhadoopdata`
eval DFS_DATA_DIR=${DFS_DATA_DIR}
syslog_netcat "Local directory for Hadoop datanode is ${DFS_NAME_DIR}"

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	syslog_netcat "Hadoop will be configured to use MRv2 (YARN)"
else
	syslog_netcat "Hadoop will be configured to use MRv1"
fi

###################################################################
# Verify current user has write access to Hadoop configuration directory
###################################################################

echo "Test" > $HADOOP_CONF_DIR/test
if [ $? -eq 0 ]; then
	rm $HADOOP_CONF_DIR/test
else
	syslog_netcat "Error: User $(whoami) unable to write to Hadoop configuration directory ${HADOOP_CONF_DIR} - NOK"
        exit 1
fi

###################################################################
# Disable IPv6 use by Hadoop
###################################################################

if [ -e ${HADOOP_CONF_DIR}/hadoop-env.sh ]; then
	is_preferIPv4Stack=`cat ${HADOOP_CONF_DIR}/hadoop-env.sh | grep -c "preferIPv4Stack=true"`
	if [ ${is_preferIPv4Stack} -eq 0 ]; then
		syslog_netcat "Adding extra options to existing hadoop-env.sh to ignore IPv6 addresses"
		echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" >> $HADOOP_CONF_DIR/hadoop-env.sh
		echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh
	fi
else
	syslog_netcat "Creating hadoop-env.sh file with options to ignore IPv6 addresses"
	echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" > $HADOOP_CONF_DIR/hadoop-env.sh
	echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh
fi

###################################################################
# Set up masters and slaves files
###################################################################

syslog_netcat "Updating masters, slaves files in ${HADOOP_CONF_DIR}..."
echo "${hadoop_master_ip}" > $HADOOP_CONF_DIR/masters
if [ $? -ne 0 ]; then
   syslog_netcat "Error creating $HADOOP_CONF_DIR/masters - NOK"
   exit 1
fi

echo "${slave_ips}" > $HADOOP_CONF_DIR/slaves
if [ $? -ne 0 ]; then
   syslog_netcat "Error creating $HADOOP_CONF_DIR/slavess - NOK"
   exit 1
fi
syslog_netcat "...masters, slaves files updated."

###################################################################
# Create core-site.xml, hdfs-site.xml, and mapred-site.xml files
###################################################################

syslog_netcat "Creating files core-site.xml, hdfs-site.xml and mapred-site.xml..."
cat << EOF > $HADOOP_CONF_DIR/core-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>fs.default.name</name>
<value>hdfs://HADOOP_NAMENODE_IP:9000</value>
<final>true</final>
</property>
</configuration>
EOF
if [ $? -ne 0 ]; then
   syslog_netcat "Error creating core-site.xml - NOK"
   exit 1
else
   echo "...core-site.xml successfully created."
fi


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

	if [ $? -ne 0 ]; then
	   syslog_netcat "Error creating mapred-site.xml - NOK"
	   exit 1
	else
	   echo "...mapred-site.xml successfully created."
	fi

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

	if [ $? -ne 0 ]; then
	   syslog_netcat "Error creating mapred-site.xml - NOK"
	   exit 1
	else
	   echo "...mapred-site.xml successfully created."
	fi
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

	if [ $? -ne 0 ]; then
	   syslog_netcat "Error creating hdfs-site.xml - NOK"
	   exit 1
	else
	   echo "...hdfs-site.xml successfully created."
	fi

else
	cat << EOF > $HADOOP_CONF_DIR/hdfs-site.xml
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<property>
<name>dfs.name.dir</name>
<value>DFS_NAME_DIR</value>
<final>true</final>
</property>

<property>
<name>dfs.data.dir</name>
<value>DFS_DATA_DIR</value>
</property>
</configuration>
EOF

	if [ $? -ne 0 ]; then
	   syslog_netcat "Error creating hdfs-site.xml - NOK"
	   exit 1
	else
	   echo "...hdfs-site.xml successfully created."
	fi

fi

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	syslog_netcat "Creating file yarn-site.xml..."

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

	if [ $? -ne 0 ]; then
	   syslog_netcat "Error creating yarn-site.xml - NOK"
	   exit 1
	else
	   echo "...yarn-site.xml successfully created."
	fi
fi

###################################################################
# Updating hadoop config files to replace placeholders with actual values
###################################################################

syslog_netcat "Updating placeholders in hadoop config files..."
sudo sed -i -e "s/HADOOP_NAMENODE_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/core-site.xml
sudo sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/mapred-site.xml
sudo sed -i -e "s/NUM_REPLICA/1/g" $HADOOP_CONF_DIR/hdfs-site.xml #3 is default. 1 is given for sort's performance

if [ ${hadoop_use_yarn} -eq 1 ] ; then
	sudo sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/yarn-site.xml
fi

TEMP_DFS_NAME_DIR=`echo ${DFS_NAME_DIR} | sed -e "s/\//-__-__/g"`
TEMP_DFS_DATA_DIR=`echo ${DFS_DATA_DIR} | sed -e "s/\//-__-__/g"`

sudo sed -i -e "s/DFS_NAME_DIR/${TEMP_DFS_NAME_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml
sudo sed -i -e "s/DFS_DATA_DIR/${TEMP_DFS_DATA_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml

sudo sed -i -e "s/-__-__/\//g" $HADOOP_CONF_DIR/hdfs-site.xml

syslog_netcat "Placeholders updated."

###################################################################
# Editing hadoop conf.xml files for the optional confs 
# as defined in cb_hadoop_common.sh
###################################################################
syslog_netcat "Applying any additional Hadoop parameters specified in cb_hadoop_common.sh..."

#core-site.xml
output_file=$HADOOP_CONF_DIR/core-site.xml
sudo sed -i -e "s/<\/configuration>//" $output_file
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
sudo sed -i -e "s/<\/configuration>//" $output_file
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
sudo sed -i -e "s/<\/configuration>//" $output_file
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
syslog_netcat "...Done applying any additional Hadoop parameters."

###################################################################
# If /etc/hadoop exists, copy hadoop configuration files there too
###################################################################

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

syslog_netcat "Done updating local Hadoop cluster configuration files."
exit 0
