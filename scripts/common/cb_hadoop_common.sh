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

export JAVA_HOME=${JAVA_HOME}

if [[ -z ${HADOOP_HOME} ]]
then
    HADOOP_HOME=`get_my_ai_attribute_with_default hadoop_home ~/hadoop-2.6.0`
    eval HADOOP_HOME=${HADOOP_HOME}
    syslog_netcat "HADOOP_HOME not defined on the environment. Value obtained from CB's Object Store was \"$HADOOP_HOME\""
else
    syslog_netcat "HADOOP_HOME already defined on the environment (\"$HADOOP_HOME\")"     
fi
    
if [[ ! -d ${HADOOP_HOME} ]]
then
    syslog_netcat "The value specified in the AI attribute HADOOP_HOME (\"$HADOOP_HOME\") points to a non-existing directory. Will search ~ for a hadoop dir." 
    HADOOP_HOME=$(ls ~ | grep -v tar | grep hadoop- | sort -r | head -n1)
    eval HADOOP_HOME="~/${HADOOP_HOME}"
    if [[ ! -d $HADOOP_HOME ]]
    then
        syslog_netcat "Unable to find a directory with a Hadoop installation - NOK"
        exit 1
    fi
fi

export HADOOP_HOME=${HADOOP_HOME}

syslog_netcat "HADOOP_HOME was determined to be $HADOOP_HOME"     

if [[ -f ~/.bashrc ]]
then
    is_hadoop_home_export=`grep -c "HADOOP_HOME=${HADOOP_HOME}" ~/.bashrc`
    if [[ $is_hadoop_home_export -eq 0 ]]
    then
        syslog_netcat "Adding HADOOP_HOME ($HADOOP_HOME) to bashrc"
        echo "export HADOOP_HOME=${HADOOP_HOME}" >> ~/.bashrc
        echo "export PATH=\$PATH:$HADOOP_HOME/bin" >> ~/.bashrc
    fi
fi
    
if [[ -z ${HADOOP_CONF_DIR} ]]
then
    HADOOP_CONF_DIR=$(find $HADOOP_HOME -name core-site.xml | grep -v templates | sed 's/core-site.xml//g' | tail -1)
    syslog_netcat "HADOOP_CONF_DIR not defined on the environment. Assuming \"$HADOOP_CONF_DIR\" as the directory"
fi

if [[ ! -d $HADOOP_CONF_DIR ]]
then
    syslog_netcat "Error. The detected HADOOP_CONF_DIR ($HADOOP_CONF_DIR) is not a directory - NOK"
    exit 1
fi
  
if [[ -f ~/.bashrc ]]
then
    is_hadoop_conf_export=`grep -c "HADOOP_CONF_DIR=${HADOOP_CONF_DIR}" ~/.bashrc`
    if [[ $is_hadoop_conf_export -eq 0 ]]
    then
        syslog_netcat "Adding HADOOP_CONF_DIR ($HADOOP_CONF_DIR) to bashrc"
        echo "export HADOOP_CONF_DIR=${HADOOP_CONF_DIR}" >> ~/.bashrc
    fi
fi            

export HADOOP_CONF_DIR=${HADOOP_CONF_DIR}

if [[ -z ${HADOOP_EXECUTABLE} ]]
then
    HADOOP_EXECUTABLE=$(find $HADOOP_HOME -name hadoop.cmd | grep -v templates | sed 's/.cmd//g' | tail -1)
    syslog_netcat "HADOOP_EXECUTABLE not defined on the environment. Assuming \"$HADOOP_EXECUTABLE\" as the executable"
fi

if [[ ! -f $HADOOP_EXECUTABLE ]]
then
    syslog_netcat "Error. The detected HADOOP_EXECUTABLE ($HADOOP_EXECUTABLE) does not exist - NOK"
    exit 1
fi
  
if [[ -f ~/.bashrc ]]
then
    is_hadoop_executable_export=`grep -c "HADOOP_EXECUTABLE=${HADOOP_EXECUTABLE}" ~/.bashrc`
    if [[ $is_hadoop_executable_export -eq 0 ]]
    then
        syslog_netcat "Adding HADOOP_EXECUTABLE ($HADOOP_EXECUTABLE) to bashrc"
        echo "export HADOOP_EXECUTABLE=${HADOOP_EXECUTABLE}" >> ~/.bashrc
    fi
fi

export HADOOP_EXECUTABLE=${HADOOP_EXECUTABLE}

if [[ -z ${GIRAPH_HOME} ]]
then
    GIRAPH_HOME=`get_my_ai_attribute_with_default giraph_home ~/giraph/giraph/`    
    eval GIRAPH_HOME=${GIRAPH_HOME}

    if [[ -f ~/.bashrc ]]
    then
        is_giraph_home_export=`grep -c "GIRAPH_HOME=${GIRAPH_HOME}" ~/.bashrc`
        if [[ $is_giraph_home_export -eq 0 ]]
        then
            syslog_netcat "Adding GIRAPH_HOME ($GIRAPH_HOME) to bashrc"
            echo "export GIRAPH_HOME=${GIRAPH_HOME}" >> ~/.bashrc
        fi
    fi
fi

export GIRAPH_HOME=${GIRAPH_HOME}

if [[ -z ${ZOOKEPER_HOME} ]]
then
    ZOOKEPER_HOME=`get_my_ai_attribute_with_default zookeper_home ~/giraph/zookeeper/zookeeper-3.4.6/`
    
    eval ZOOKEPER_HOME=${ZOOKEPER_HOME}

    if [[ -f ~/.bashrc ]]
    then
        is_zookeper_home_export=`grep -c "ZOOKEPER_HOME=${ZOOKEPER_HOME}" ~/.bashrc`
        if [[ $is_zookeper_home_export -eq 0 ]]
        then
            syslog_netcat "Adding ZOOKEPER_HOME ($ZOOKEPER_HOME) to bashrc"
            echo "export ZOOKEPER_HOME=${ZOOKEPER_HOME}" >> ~/.bashrc
        fi
    fi
fi

export ZOOKEPER_HOME=${ZOOKEPER_HOME}

if [[ -z ${HIBENCH_HOME} ]]
then
    HIBENCH_HOME=`get_my_ai_attribute_with_default hibench_home ~/HiBench`

    eval HIBENCH_HOME=${HIBENCH_HOME}
    
    if [[ -f ~/.bashrc ]]
    then
        is_hibench_home_export=`grep -c "HIBENCH_HOME=${HIBENCH_HOME}" ~/.bashrc`
        if [[ $is_hibench_home_export -eq 0 ]]
        then
            syslog_netcat "Adding HIBENCH_HOME ($HIBENCH_HOME) to bashrc"
            echo "export HIBENCH_HOME=${HIBENCH_HOME}" >> ~/.bashrc
        fi
    fi
fi

if [[ -d ${HADOOP_HOME}/sbin ]]
then
    HADOOP_BIN_DIR=${HADOOP_HOME}/sbin
else
    HADOOP_BIN_DIR=${HADOOP_HOME}/bin
fi

if [[ $(echo $my_type | grep -c giraph) -ne 0 ]]
then
    hadoop_master_ip=`get_ips_from_role giraphmaster`

    slave_ips=`get_ips_from_role giraphslave`
else
    hadoop_master_ip=`get_ips_from_role hadoopmaster`

    slave_ips=`get_ips_from_role hadoopslave`

fi

slave_ips_csv=$(echo ${slave_ips} | sed ':a;N;$!ba;s/\n/,/g')
slave_ips_csv=$(echo ${slave_ips_csv} | sed 's/ /,/g')

# Determine whether to use YARN aka MRv2
hadoop_version=$($HADOOP_HOME/bin/hadoop version | sed '1!d')
hadoop_version_nr=$(echo ${hadoop_version} | sed 's/Hadoop //g')
hadoop_version_major=`echo ${hadoop_version} | sed 's/Hadoop \([0-9]*\)\..*/\1/'`
hadoop_version_minor=`echo ${hadoop_version} | sed 's/Hadoop [0-9]*\.\([0-9]*\).*/\1/'`

export HIBENCH_HOME=${HIBENCH_HOME}
HADOOP_EXAMPLES_JAR=${HADOOP_HOME}/$(get_my_ai_attribute_with_default hadoop_examples share/hadoop/mapreduce/hadoop-mapreduce-examples-VERSION.jar)
export HADOOP_EXAMPLES_JAR=$(echo $HADOOP_EXAMPLES_JAR | sed "s/VERSION/$hadoop_version_nr/g")

hadoop_use_yarn=0
if [ $hadoop_version_major -gt 2 ]
then
    hadoop_use_yarn=1
else
    if [[ $hadoop_version_major -eq 2  &&  $hadoop_version_minor -gt 1 ]]
    then
        hadoop_use_yarn=1
    fi
fi

function check_write_access {
###################################################################
# Verify current user has write access to Hadoop configuration directory
###################################################################

    echo "Test" > $HADOOP_CONF_DIR/test
    if [[ $? -eq 0 ]]
    then
        syslog_netcat "User $(whoami) is able to write to Hadoop configuration directory ${HADOOP_CONF_DIR}"
        rm $HADOOP_CONF_DIR/test
    else
        syslog_netcat "Error: User $(whoami) unable to write to Hadoop configuration directory ${HADOOP_CONF_DIR} - NOK"
        exit 1
    fi
}
export -f check_write_access

function disable_ip_version_six {
###################################################################
# Disable IPv6 use by Hadoop
###################################################################

    if [[ -e ${HADOOP_CONF_DIR}/hadoop-env.sh ]]
    then
        is_preferIPv4Stack=`cat ${HADOOP_CONF_DIR}/hadoop-env.sh | grep -c "preferIPv4Stack=true"`
        if [[ ${is_preferIPv4Stack} -eq 0 ]]
        then
            syslog_netcat "Adding extra options to existing hadoop-env.sh to ignore IPv6 addresses"
            echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" >> $HADOOP_CONF_DIR/hadoop-env.sh
            echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh
        fi
    else
        syslog_netcat "Creating hadoop-env.sh file with options to ignore IPv6 addresses"
        echo "export HADOOP_OPTS=-Djava.net.preferIPv4Stack=true" > $HADOOP_CONF_DIR/hadoop-env.sh
        echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh
    fi
}
export -f disable_ip_version_six

function create_master_and_slaves_files {
###################################################################
# Set up masters and slaves files
###################################################################

    syslog_netcat "Updating masters, slaves files in ${HADOOP_CONF_DIR}..."
    echo "${hadoop_master_ip}" > $HADOOP_CONF_DIR/masters
    if [[ $? -ne 0 ]]
    then
       syslog_netcat "Error creating $HADOOP_CONF_DIR/masters - NOK"
       exit 1
    fi
    
    echo "${slave_ips}" > $HADOOP_CONF_DIR/slaves
    if [[ $? -ne 0 ]]
    then
       syslog_netcat "Error creating $HADOOP_CONF_DIR/slavess - NOK"
       exit 1
    fi
    syslog_netcat "...masters, slaves files updated."
}
export -f create_master_and_slaves_files

function create_hadoop_config_files {
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

    if [[ $? -ne 0 ]]
    then
       syslog_netcat "Error creating core-site.xml - NOK"
       exit 1
    else
       echo "...core-site.xml successfully created."
    fi
    
    
    if [ ${hadoop_use_yarn} -eq 1 ]
    then
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

        if [ $? -ne 0 ]
        then
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

        if [ $? -ne 0 ]
        then
           syslog_netcat "Error creating mapred-site.xml - NOK"
           exit 1
        else
           echo "...mapred-site.xml successfully created."
        fi
    fi

    if [ ${hadoop_use_yarn} -eq 1 ]
    then
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

        if [ $? -ne 0 ]
        then
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

        if [ $? -ne 0 ]
        then
           syslog_netcat "Error creating hdfs-site.xml - NOK"
           exit 1
        else
           echo "...hdfs-site.xml successfully created."
        fi
    
    fi
    
    if [ ${hadoop_use_yarn} -eq 1 ]
    then
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

        if [ $? -ne 0 ]
        then
           syslog_netcat "Error creating yarn-site.xml - NOK"
           exit 1
        else
           echo "...yarn-site.xml successfully created."
        fi
    fi
}
export -f create_hadoop_config_files

function update_hadoop_config_files {
###################################################################
# Updating hadoop config files to replace placeholders with actual values
###################################################################

    syslog_netcat "Updating placeholders in hadoop config files..."
    sudo sed -i -e "s/HADOOP_NAMENODE_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/core-site.xml
    sudo sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/mapred-site.xml
    sudo sed -i -e "s/NUM_REPLICA/1/g" $HADOOP_CONF_DIR/hdfs-site.xml #3 is default. 1 is given for sort's performance
    
    if [ ${hadoop_use_yarn} -eq 1 ]
    then
        sudo sed -i -e "s/HADOOP_JOBTRACKER_IP/${hadoop_master_ip}/g" $HADOOP_CONF_DIR/yarn-site.xml
    fi
    
    TEMP_DFS_NAME_DIR=`echo ${DFS_NAME_DIR} | sed -e "s/\//-__-__/g"`
    TEMP_DFS_DATA_DIR=`echo ${DFS_DATA_DIR} | sed -e "s/\//-__-__/g"`
    
    sudo sed -i -e "s/DFS_NAME_DIR/${TEMP_DFS_NAME_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml
    sudo sed -i -e "s/DFS_DATA_DIR/${TEMP_DFS_DATA_DIR}/g" $HADOOP_CONF_DIR/hdfs-site.xml
    
    sudo sed -i -e "s/-__-__/\//g" $HADOOP_CONF_DIR/hdfs-site.xml
    
    syslog_netcat "Placeholders updated."    
}
export -f update_hadoop_config_files

function configure_hadoop_ganglia_collection {
###################################################################
# Update hadoop-metrics2.properties to send metrics to ganglia
###################################################################

# All slaves report their hadoop data to master which then sends it
# to cloudbench node.

    GANGLIA_COLLECTOR_VM_PORT=`get_global_sub_attribute mon_defaults collector_vm_port`
    
    cat <<EOF >> $HADOOP_CONF_DIR/hadoop-metrics2.properties
namenode.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
namenode.sink.ganglia.period=10
namenode.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

datanode.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
datanode.sink.ganglia.period=10
datanode.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

jobtracker.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
jobtracker.sink.ganglia.period=10
jobtracker.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

tasktracker.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
tasktracker.sink.ganglia.period=10
tasktracker.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

maptask.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
maptask.sink.ganglia.period=10
maptask.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

reducetask.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31
reducetask.sink.ganglia.period=10
reducetask.sink.ganglia.servers=${hadoop_master_ip}:${GANGLIA_COLLECTOR_VM_PORT}

EOF
}
export -f configure_hadoop_ganglia_collection

function copy_hadoop_config_files_to_etc {
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
        sudo cp $HADOOP_CONF_DIR/mapred-site.xml /etc/hadoop
        sudo cp $HADOOP_CONF_DIR/hdfs-site.xml /etc/hadoop
        
        if [ ${hadoop_use_yarn} -eq 1 ]
        then
            sudo cp $HADOOP_CONF_DIR/yarn-site.xml /etc/hadoop
        fi
    fi
}
export -f copy_hadoop_config_files_to_etc

function get_available_nodes {
    # CDH format: Datanodes available: 4 (5 total, 1 dead)
    # Apache format: Live datanodes (4):
    #                Dead datanodes (1):
    AVAILABLE_NODES=0
    DFSADMINOUTPUT=`$HADOOP_HOME/bin/hadoop dfsadmin -report 2>&1 | grep "Datanodes available"`
    if [ -z "$DFSADMINOUTPUT" ]
    then
         # Format: Live datanodes (4):
         AVAILABLE_NODES=`$HADOOP_HOME/bin/hadoop dfsadmin -report 2>&1 | grep "Live datanodes" | awk -F"[()]" '{print $2}'`
    else
         AVAILABLE_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 2`
    fi
    
    echo $AVAILABLE_NODES
}
export -f get_available_nodes

function check_hadoop_cluster_state {
#####################################################################################
# On Master node, wait for all slave datanodes to start
#####################################################################################
    ATTEMPTS=$1
    INTERVAL=$2

    if [[ $ATTEMPTS -eq 1 && $INTERVAL -eq 1 ]]
    then
        QUICK_CHECK=1
    else
        QUICK_CHECK=0
    fi
    
    if [[ x"$my_role" == x"hadoopmaster" || x"$my_role" == x"giraphmaster" ]] 
    then
        syslog_netcat "Waiting for all Datanodes to become available..."
    
        # Will wait 5 minutes for datanodes to start; else throw error
        
#        TOTAL_NODES=$(echo $slave_ips_csv','$hadoop_master_ip | awk -F"," '{print NF}')
        TOTAL_NODES=$(echo $slave_ips_csv | awk -F"," '{print NF}')
        while [[ ${DATANODES_AVAILABLE} != "true" && $ATTEMPTS -gt 0 ]]
        do
            # CDH format: Datanodes available: 4 (5 total, 1 dead)
            # Apache format: Live datanodes (4):
            #                Dead datanodes (1):
            DFSADMINOUTPUT=`$HADOOP_HOME/bin/hadoop dfsadmin -report | grep "Datanodes available"`
            if [ -z "$DFSADMINOUTPUT" ]
            then
                 # Format: Live datanodes (4):
                 AVAILABLE_NODES=`$HADOOP_HOME/bin/hadoop dfsadmin -report | grep "Live datanodes" | awk -F"[()]" '{print $2}'`
                 DEAD_NODES=`$HADOOP_HOME/bin/hadoop dfsadmin -report | grep "Dead datanodes" | awk -F"[()]" '{print $2}'`
                 REPORTED_TOTAL_NODES=$((AVAILABLE_NODES+DEAD_NODES))
            else
                 AVAILABLE_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 2`
                 REPORTED_TOTAL_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 3 | sed 's/(//g'`
            fi

            if [[ -z ${REPORTED_TOTAL_NODES} ]]
            then
                REPORTED_TOTAL_NODES=0
            fi

            if [[ -z ${AVAILABLE_NODES} ]]
            then
                AVAILABLE_NODES=0
            fi            
                                    
            if [[ ${AVAILABLE_NODES} -ne 0 && z${AVAILABLE_NODES} == z${TOTAL_NODES} ]]
            then
                DATANODES_AVAILABLE="true"
                syslog_netcat "...All Datanodes (${TOTAL_NODES}) available."
                break
            else
                DATANODES_AVAILABLE="false"
                syslog_netcat "Number of datanodes available is ${AVAILABLE_NODES} (out of $TOTAL_NODES). Will sleep $INTERVAL seconds and attempt $ATTEMPTS more times."
            fi
    
            ((ATTEMPTS=ATTEMPTS-1))
    
            sleep $INTERVAL
        done

        if [[ "$ATTEMPTS" -eq 0 ]]
        then
            if [[ $QUICK_CHECK -eq 0 ]]
            then
                syslog_netcat "Timeout Error waiting for datanodes to start. ${AVAILABLE_NODES} of ${TOTAL_NODES} are live. - NOK"
                syslog_netcat "`$HADOOP_HOME/bin/hadoop dfsadmin -report`"
            else
                syslog_netcat "Hadoop cluster not formed yet."
            fi
            return 1

        fi
        
        return 0

    fi
}
export -f check_hadoop_cluster_state

function create_mapreduce_history {
#####################################################################################
# On Master node, wait for all slave datanodes to start
#####################################################################################

    if [[ x"$my_role" == x"hadoopmaster" || x"$my_role" == x"giraphmaster" ]] 
    then
        if [[ ${hadoop_use_yarn} -eq 1 ]]
        then
            syslog_netcat "Creating map-reduce history directory on HDFS filesystem..."
            hadoop dfs -mkdir /mr-history
            hadoop dfs -mkdir /mr-history/done
            hadoop dfs -mkdir /mr-history/tmp
            hadoop dfs -chmod -R 777 /mr-history/done
            hadoop dfs -chmod -R 777 /mr-history/tmp
        fi
    
    fi
}
export -f create_mapreduce_history
    
function start_master_hadooop_services {
    syslog_netcat "Starting Hadoop Master services..."
    if [[ ${hadoop_use_yarn} -eq 1 ]]
        then
            syslog_netcat "...Formatting Namenode..."
            $HADOOP_HOME/bin/hadoop namenode -format -force
            if [[ $? -ne 0 ]]
            then
                syslog_netcat "Error when formatting namenode - NOK"
                exit 1
            fi
    
            syslog_netcat "...Starting Namenode daemon..."
            ${HADOOP_BIN_DIR}/hadoop-daemon.sh start namenode
    
            syslog_netcat "...Starting YARN Resource Manager daemon..."
            ${HADOOP_BIN_DIR}/yarn-daemon.sh start resourcemanager
    
            syslog_netcat "...Starting Job History daemon..."
            ${HADOOP_BIN_DIR}/mr-jobhistory-daemon.sh start historyserver
    
        else
            syslog_netcat "...Formating Namenode..."
    
            #$HADOOP_HOME/bin/hadoop namenode -format -force
            # Default Hadoop permissions require hadoop superuser to format namenode
            #  Attempt to identify superuser, with default value of hdfs

            DFS_NAME_DIR=`get_my_ai_attribute_with_default dfs_name_dir /tmp/cbhadoopname`        
            
            set -- `sudo ls -l ${DFS_NAME_DIR}`
            dfs_name_dir_owner=$5
    
            if [[ x$dfs_name_dir_owner == x ]]
            then
#            dfs_name_dir_owner="hdfs"
                dfs_name_dir_owner=$(whoami)
                sudo chown -R $(whoami) ${DFS_NAME_DIR}
            fi
    
            sudo -u ${dfs_name_dir_owner} $HADOOP_HOME/bin/hadoop namenode -format -force
            if [[ $? -ne 0 ]]
            then
                syslog_netcat "Error when formatting namenode (on $DFS_NAME_DIR) as user ${dfs_name_dir_owner} - NOK"
                exit 1
            fi
    
            syslog_netcat "...Namenode formatted."
    
            syslog_netcat "...Starting primary Namenode service..."
            if [[ -e ${HADOOP_BIN_DIR}/start-dfs.sh ]] 
            then
                syslog_netcat "...start-dfs.sh script exists, using that to launch Namenode services..."
                ${HADOOP_BIN_DIR}/start-dfs.sh
                namenode_running=`ps aux | grep -e [n]amenode`
                if [[ x"$namenode_running" == x ]] 
                then
                    syslog_netcat "Error - Namenode service did not start - NOK"
                    exit 1
                else
                    syslog_netcat "...Namenode process appears to be running."
                fi
    
            else
                syslog_netcat "...No start-dfs script exists. Attempting to identify namenode service..."
    
                for x in `cd /etc/init.d ; ls *namenode*`
                do 
                    syslog_netcat "...Starting service ${x} ..."
                    sudo /sbin/service $x start 
                    namenode_running=`ps aux | grep -e [n]amenode`
                    if [[ x"$namenode_running" == x ]]
                    then
                        # I probably shouldn't hard-code the path to log directory.
                        errorstring=`grep "FATAL\|Exception" /var/log/hadoop-hdfs/*.log`
                        syslog_netcat "Error starting ${x} on ${my_ip_addr}. ${errorstring} NOK"
                        exit 1
                    else
                        syslog_netcat "...Namenode process appears to be running."
                    fi
                done
            fi
    
            syslog_netcat "...Starting JobTracker service..."
            if [[ -e ${HADOOP_BIN_DIR}/start-mapred.sh ]]
            then
                syslog_netcat "...start-mapred.sh script exists, using that to launch Jobtracker services..."
                ${HADOOP_BIN_DIR}/start-mapred.sh
                jobtracker_running=`ps aux | grep -e [j]obtracker`
                if [[ x"$jobtracker_running" == x ]] 
                then
                    syslog_netcat "Error starting jobtracker on ${my_ip_addr} - NOK"
                    exit 1
                else
                    syslog_netcat "...Jobtracker process appears to be running."
                fi
    
            else
                syslog_netcat "...No start-mapred script exists. Attempting to identify Jobtracker service..."
    
                for x in `cd /etc/init.d ; ls *jobtracker*`
                do 
                    syslog_netcat "...Starting service ${x} ..."
                    sudo /sbin/service $x start 
                    jobtracker_running=`ps aux | grep -e [j]obtracker`
                    if [[ x"$jobtracker_running" == x ]] 
                    then
                        syslog_netcat "Error starting ${x} on ${my_ip_addr} - NOK"
                        exit 1
                    else
                        syslog_netcat "...Jobtracker process appears to be running."
                    fi
                done
            fi
    
        fi
        
}
export -f start_master_hadooop_services

function start_slave_hadoop_services {
#####################################################################################
# Start hadoop services / daemons
#####################################################################################
    syslog_netcat "Starting Hadoop Slave services..."
            
    if [[ ${hadoop_use_yarn} -eq 1 ]]
    then
        
        syslog_netcat "...Starting datanode..."
        ${HADOOP_BIN_DIR}/hadoop-daemon.sh start datanode
        datanode_error=`grep FATAL ${HADOOP_HOME}/logs/hadoop*.log`
        if [[ x"$datanode_error" != x ]]
        then
            syslog_netcat "Error starting datanode on ${my_ip_addr}: ${datanode_error} - NOK"
            exit 1
        fi
        
        syslog_netcat "....starting nodemanager on ${my_ip_addr} ..."
        ${HADOOP_BIN_DIR}/yarn-daemon.sh start nodemanager
    else
        
        for x in `cd /etc/init.d ; ls *datanode*`
        do 
            syslog_netcat "...Starting service ${x} ..."
            sudo /sbin/service $x start 
            datanode_running=`ps aux | grep -e [d]atanode`
            if [[ x"$datanode_running" == x ]]
            then
                errorstring=`grep "FATAL\|Exception" /var/log/hadoop-hdfs/*.log`
                syslog_netcat "Error starting ${x} on ${my_ip_addr}. ${errorstring} - NOK"
                exit 1
            else
                syslog_netcat "...Datanode process appears to be running."
            fi
            
        done
        
        for x in `cd /etc/init.d ; ls *tasktracker*`
        do
            syslog_netcat "....starting service ${x} on ${my_ip_addr} ..."
            sudo /sbin/service $x start 
                
            tasktracker_running=`ps aux | grep -e [t]asktracker`
            if [[ x"$tasktracker_running" == x ]]
            then
                syslog_netcat "Error starting ${x} on ${my_ip_addr} - NOK"
                exit 1
            else
                syslog_netcat "...Tasktracker process appears to be running."
        
            fi
        done
        
    fi
}
export -f start_slave_hadoop_services

function setup_matrix_multiplication {

    if [[ x"$my_role" == x"hadoopmaster" ]] 
    then
        if [[ -f ~/mm.tar ]]
        then 
            cd ${HIBENCH_HOME}
            tar -xvf ~/mm.tar
            rm ~/mm.tar
        fi
    fi

}
export -f setup_matrix_multiplication

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
declare -A MAPRED_SITE_PROPERTIES 
#MAPRED_SITE_PROPERTIES["mapred.min.split.size"]=0
#MAPRED_SITE_PROPERTIES["mapred.max.split.size"]=16777216
#MAPRED_SITE_PROPERTIES["mapreduce.tasktracker.map.tasks.maximum"]=4
#MAPRED_SITE_PROPERTIES["mapreduce.tasktracker.reduce.tasks.maximum"]=4
NUM_MAPS=`get_my_ai_attribute_with_default num_maps "2"`
NUM_REDS=`get_my_ai_attribute_with_default num_reds "2"`
export NUM_MAPS
export NUM_REDS
MAPRED_SITE_PROPERTIES["mapreduce.job.maps"]=${NUM_MAPS}
MAPRED_SITE_PROPERTIES["mapreduce.job.reduces"]=${NUM_REDS}
