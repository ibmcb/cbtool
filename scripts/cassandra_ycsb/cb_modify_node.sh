#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author: Joe Talerico - jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

cd ~

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

#
# Determine remove or add 
#
# dbs=`echo $cassandra | wc -w`

automount_data_dirs

sudo mkdir -p ${CASSANDRA_DATA_DIR}
sudo mkdir -p ${CASSANDRA_DATA_DIR}/store/cassandra/data
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/commitlog 
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/saved_caches
sudo chown -R cassandra:cassandra ${CASSANDRA_DATA_DIR}

#
# Determine current nodes 
#
nodes=`nodetool ring | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}'`
if [[ $? == 1 ]]
then 
    service_stop_disable cassandra

    pos=1
    tk_pos=0

    #    sudo sh -c "echo $MY_IP cassandra >> /etc/hosts"
    for db in $cassandra_ips
    do
        if [[ $(cat /etc/hosts | grep -c "cassandra${pos} ") -eq 0 ]]
        then
            sudo sh -c "echo $db cassandra$pos cassandra-$pos >> /etc/hosts"
        fi

        if [[ $MY_IP = $db ]]
        then
            k_pos=$pos
        fi
        ((pos++))
    done

CASSANDRA_CONF_PATH=$(get_my_ai_attribute_with_default cassandra_conf_path /etc/cassandra/cassandra.yaml)

if [[ ! -f $CASSANDRA_CONF_PATH ]]
then
    CASSANDRA_CONF_PATH=$(sudo find /etc -name cassandra.yaml)
fi

CASSANDRA_CONF_DIR=$(echo "$CASSANDRA_CONF_PATH" | sed 's/cassandra.yaml//g')

sudo ls ${CASSANDRA_CONF_DIR}/jmxremote.password
if [[ $? -ne 0 ]]
then
    sudo echo "cassandra cassandra" > /tmp/jmxremote.password
    sudo mv /tmp/jmxremote.password ${CASSANDRA_CONF_DIR}/jmxremote.password
    sudo chown cassandra:cassandra ${CASSANDRA_CONF_DIR}/jmxremote.password
    sudo chmod 0600 ${CASSANDRA_CONF_DIR}/jmxremote.password
fi
    
if [[ $(sudo grep -c cassandra ${JAVA_HOME}/lib/management/jmxremote.access) -eq 0 ]]
then
    sudo sed -i 's/monitorRole   readonly/monitorRole   readonly\ncassandra    readwrite\n/g' ${JAVA_HOME}/lib/management/jmxremote.access
fi
    
if [[ $(grep -c "LOCAL_JMX=no" ${CASSANDRA_CONF_DIR}/cassandra-env.sh) -eq 0 ]]
then
    LINE_NUMBER=$(sudo grep -n LOCAL_JMX=yes ${CASSANDRA_CONF_DIR}/cassandra-env.sh | cut -d ':' -f 1)
    LINE_NUMBER=$((LINE_NUMBER-2))
    sudo sed -i -e "${LINE_NUMBER}i\LOCAL_JMX=no" ${CASSANDRA_CONF_DIR}/cassandra-env.sh
fi

#
# Update Cassandra Config
#
    #sudo sed -i "s/.*initial_token:.*/initial_token: ${my_token//[[:blank:]]/}/g" ${CASSANDRA_CONF_PATH}
    sudo sed -i "s/- seeds:.*$/- seeds: $seeds_ips_csv/g" $CASSANDRA_CONF_PATH
    sudo sed -i "s/listen_address:.*$/listen_address: ${MY_IP}/g" $CASSANDRA_CONF_PATH
    sudo sed -i "s/rpc_address:.*$/rpc_address: ${MY_IP}/g" ${CASSANDRA_CONF_PATH}
    sudo sed -i "s/start_rpc:.*$/start_rpc: true/g" ${CASSANDRA_CONF_PATH}
    
    if [[ -d ${CASSANDRA_DATA_DIR} ]]
    then
        sudo sed -i "s^/var/lib/^${CASSANDRA_DATA_DIR}/^g" ${CASSANDRA_CONF_PATH}
    fi
    sudo sed -i "s/'Test Cluster'/'${my_ai_name}'/g" $CASSANDRA_CONF_PATH

#
# Start the database
#
    syslog_netcat "Starting cassandra on ${SHORT_HOSTNAME}"
    service_start_enable cassandra

#
# Modify Nodes 
#
    pos=$dbs

#
# Still need to add the Remove node case, Cassandra should be easier to remove a node.
# Since in theory, there is no SPF in Cassandra.
#
    for db in $cassandra_ips
    do
        db_chk=`cat /etc/hosts | grep $db | awk '{ print $2 }'`
        if ! [[ "$nodes" =~ "$db_chk" ]]
        then 
            syslog_netcat " Adding the following node : cassandra$pos"
            ((pos++))
        fi
    done
else 
    exit 0
fi

if [[ $? -gt 0 ]]
then
    syslog_netcat "problem modifying nodes ${SHORT_HOSTNAME} - NOK"
    exit 1
fi
exit 0
