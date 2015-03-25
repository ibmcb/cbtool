#!/usr/bin/env bash

#/*******************************************************************************
#
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
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

mount_filesystem_on_volume ${CASSANDRA_DATA_DIR} $CASSANDRA_DATA_FSTYP cassandra

#
# Cassandra directory structure
#
sudo mkdir -p ${CASSANDRA_DATA_DIR}/store/cassandra/data
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/commitlog 
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/saved_caches
sudo chown -R cassandra:cassandra ${CASSANDRA_DATA_DIR}

CASSANDRA_REPLICATION_FACTOR=$(get_my_ai_attribute_with_default replication_factor 4)
sudo sed -i "s/REPLF/${CASSANDRA_REPLICATION_FACTOR}/g" create_keyspace.cassandra

CASSANDRA_CONF_PATH=$(get_my_ai_attribute_with_default cassandra_conf_path /etc/cassandra/cassandra.yaml)

if [[ ! -f $CASSANDRA_CONF_PATH ]]
then
    CASSANDRA_CONF_PATH=$(sudo find /etc -name cassandra.yaml)
fi

#
# Update the cassandra config
#
TEMP_CASSANDRA_DATA_DIR=$(echo ${CASSANDRA_DATA_DIR} | sed 's/\//_+-_-+/g')
sudo sed -i "s/\/var\/lib\//${TEMP_CASSANDRA_DATA_DIR}\//g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/_+-_-+/\//g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/'Test Cluster'/'${my_ai_name}'/g" ${CASSANDRA_CONF_PATH}

pos=1
for db in $cassandra_ips
do
    if [[ $(cat /etc/hosts | grep -c "cassandra$pos ") -eq 0 ]]
    then
        sudo sh -c "echo $db cassandra$pos cassandra-$pos >> /etc/hosts"
    fi
    ((pos++))
done

#
# Cassandra will not properly start if the hostname is not in DNS or /etc/hosts
#
sudo sh -c "echo ${MY_IP} ${SHORT_HOSTNAME} >> /etc/hosts"

#
# Update Cassandra Config
#
sudo sed -i "s/initial_token:$/initial_token: ${my_token//[[:blank:]]/}/g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/- seeds:.*$/- seeds: $seed_ips_csv/g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/listen_address:.*$/listen_address: $MY_IP/g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/partitioner: org.apache.cassandra.dht.Murmur3Partitioner/partitioner: org.apache.cassandra.dht.RandomPartitioner/g" ${CASSANDRA_CONF_PATH}
sudo sed -i "s/rpc_address:.*$/rpc_address: ${MY_IP}/g" ${CASSANDRA_CONF_PATH}

#
# Remove possible old runs
#
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/saved_caches/*
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/data/system/*
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/commitlog/*

syslog_netcat "my ip : $MY_IP"

#
# Start the database
#
FIRST_SEED=$(echo $seed_ips_csv | cut -d ',' -f 1)

syslog_netcat "Performing a quick check on ${SHORT_HOSTNAME} in order to decide on Cassandra restart" 
check_cassandra_cluster_state ${FIRST_SEED} 1 1

STATUS=$?
if [[ $STATUS -ne 0 ]]
then 
    syslog_netcat "The exit code of \"check_cassandra_cluster_state ${FIRST_SEED} 1 1\" was $STATUS. Starting cassandra on ${SHORT_HOSTNAME}" 
    service_restart_enable cassandra

    # Give all the Java services time to start
    wait_until_port_open ${MY_IP} 9160 20 5

    STATUS=$?

    if [[ ${STATUS} -eq 0 ]]
    then
        syslog_netcat "Cassandra seed server running"
        check_cassandra_cluster_state ${FIRST_SEED} 10 20
        STATUS=$?
        if [[  $STATUS -eq 0 ]]
        then 
            syslog_netcat "Cassandra cluster fully formed. All nodes registered after Cassandra restart"
        else
            syslog_netcat "Failed to form Cassandra cluster! - NOK"    
        fi          
    else
        syslog_netcat "Cassandra seed server failed to start"
        STATUS=1
    fi
else                  
    syslog_netcat "Cassandra cluster fully formed. All nodes registered. Bypassing Cassandra restart."
    STATUS=0
fi
    
#
# Init database
#

if [[ ${MY_IP} == ${FIRST_SEED} ]]
then
    if [[ $(cassandra-cli -h ${MY_IP} -f list_keyspace.cassandra | grep Keyspace | grep -c usertable) -eq 0 ]]
    then
        cassandra-cli -h ${FIRST_SEED} -f create_keyspace.cassandra
    fi
fi
provision_application_stop $START

exit ${STATUS}
