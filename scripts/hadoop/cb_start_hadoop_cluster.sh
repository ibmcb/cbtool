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

syslog_netcat "Starting Hadoop cluster..."
if [[ x"$my_role" == x"hadoopmaster" ]] 
then
    syslog_netcat "Machine ${my_ip_addr} has role of hadoop master"
else
    syslog_netcat "Machine ${my_ip_addr} has role of hadoop slave"
fi

#####################################################################################
# Start hadoop services / daemons
#####################################################################################

syslog_netcat "Starting Hadoop services..."

if [[ x"$my_role" == x"hadoopmaster" ]]
then
    
    if [[ ${hadoop_use_yarn} -eq 1 ]]
    then
        syslog_netcat "...Formatting Namenode..."
        ${HADOOP_HOME}/bin/hadoop namenode -format -force
        if [[ $? -ne 0 ]]
        then
            syslog_netcat "Error when formatting namenode - NOK"
            exit 1
        fi

        syslog_netcat "...Starting Namenode daemon..."
        ${HADOOP_HOME}/sbin/hadoop-daemon.sh start namenode

        syslog_netcat "...Starting YARN Resource Manager daemon..."
        ${HADOOP_HOME}/sbin/yarn-daemon.sh start resourcemanager

        syslog_netcat "...Starting Job History daemon..."
        ${HADOOP_HOME}/sbin/mr-jobhistory-daemon.sh start historyserver

    else
        syslog_netcat "...Formating Namenode..."

        #${HADOOP_HOME}/bin/hadoop namenode -format -force
        # Default Hadoop permissions require hadoop superuser to format namenode
        #  Attempt to identify superuser, with default value of hdfs

        DFS_NAME_DIR=`get_my_ai_attribute_with_default dfs_name_dir /tmp/cbhadoopname`
        
        if [[ ! -d ${DFS_NAME_DIR} ]]
        then
            sudo mkdir ${DFS_NAME_DIR}
        fi

        set -- `sudo ls -l ${DFS_NAME_DIR}`
        dfs_name_dir_owner=$5

        if [[ x$dfs_name_dir_owner == x ]]
        then
#            dfs_name_dir_owner="hdfs"
            dfs_name_dir_owner=$(whoami)
            sudo chown -R $(whoami) ${DFS_NAME_DIR}
        fi

        sudo -u ${dfs_name_dir_owner} ${HADOOP_HOME}/bin/hadoop namenode -format -force
        if [[ $? -ne 0 ]]
        then
            syslog_netcat "Error when formatting namenode as user ${dfs_name_dir_owner} - NOK"
            exit 1
        fi

        syslog_netcat "...Namenode formatted."

        syslog_netcat "...Starting primary Namenode service..."
        if [[ -e ${HADOOP_HOME}/bin/start-dfs.sh ]] 
        then
            syslog_netcat "...start-dfs.sh script exists, using that to launch Namenode services..."
            ${HADOOP_HOME}/bin/start-dfs.sh
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
        if [[ -e ${HADOOP_HOME}/bin/start-mapred.sh ]]
        then
            syslog_netcat "...start-mapred.sh script exists, using that to launch Jobtracker services..."
            ${HADOOP_HOME}/bin/start-mapred.sh
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

else
    
    if [[ ${hadoop_use_yarn} -eq 1 ]]
    then
        syslog_netcat "...Starting datanode..."
        ${HADOOP_HOME}/sbin/hadoop-daemon.sh start datanode
        datanode_error=`grep FATAL ${HADOOP_HOME}/logs/hadoop*.log`
        if [[ x"$datanode_error" != x ]]
        then
            syslog_netcat "Error starting datanode on ${my_ip_addr}: ${datanode_error} - NOK"
            exit 1
        fi
        syslog_netcat "....starting nodemanager on ${my_ip_addr} ..."
        ${HADOOP_HOME}/sbin/yarn-daemon.sh start nodemanager
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
fi

#####################################################################################
# On Master node, wait for all slave datanodes to start
#####################################################################################

if [[ x"$my_role" == x"hadoopmaster" ]] 
then
    syslog_netcat "Waiting for all Datanodes to become available..."

    ATTEMPTS=30
    # Will wait 5 minutes for datanodes to start; else throw error

    while [[ z${DATANODES_AVAILABLE} != z"true" ]]
    do
        # CDH format: Datanodes available: 4 (5 total, 1 dead)
        # Apache format: Live datanodes (4):
        #                Dead datanodes (1):
        DFSADMINOUTPUT=`${HADOOP_HOME}/bin/hadoop dfsadmin -report | grep "Datanodes available"`
        if [ -z "$DFSADMINOUTPUT" ]
        then
             # Format: Live datanodes (4):
             AVAILABLE_NODES=`${HADOOP_HOME}/bin/hadoop dfsadmin -report | grep "Live datanodes" | awk -F"[()]" '{print $2}'`
             DEAD_NODES=`${HADOOP_HOME}/bin/hadoop dfsadmin -report | grep "Dead datanodes" | awk -F"[()]" '{print $2}'`
             TOTAL_NODES=$((AVAILABLE_NODES+DEAD_NODES))
        else
             AVAILABLE_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 2`
             TOTAL_NODES=`echo ${DFSADMINOUTPUT} | cut -d ":" -f 2 | cut -d " " -f 3 | sed 's/(//g'`
        fi
        if [[ ${AVAILABLE_NODES} -ne 0 && z${AVAILABLE_NODES} == z${TOTAL_NODES} ]]
        then
            DATANODES_AVAILABLE="true"
        else
            DATANODES_AVAILABLE="false"
        fi

        ((ATTEMPTS=ATTEMPTS-1))
        if [ "$ATTEMPTS" -eq 0 ]
        then
            syslog_netcat "Timeout Error waiting for datanodes to start. ${AVAILABLE_NODES} of ${TOTAL_NODES} are live. - NOK"
            syslog_netcat "`${HADOOP_HOME}/bin/hadoop dfsadmin -report`"
            exit 1
        fi

        sleep 10
    done

    syslog_netcat "...All Datanodes (${TOTAL_NODES}) available."

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

#####################################################################################
# Do...something with a tar file.  I'm Not sure what. 
#####################################################################################

if [[ x"$my_role" == x"hadoopmaster" ]] 
then
    if [[ -f ~/mm.tar ]]
    then 
        cd ${HIBENCH_HOME}
        tar -xvf ~/mm.tar
        rm ~/mm.tar
    fi
fi

syslog_netcat "Hadoop services started."
provision_application_stop $START
exit 0
