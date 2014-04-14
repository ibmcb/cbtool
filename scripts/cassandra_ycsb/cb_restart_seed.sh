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

source ~/.bashrc
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi
standalone=`online_or_offline "$4"`
if [ $standalone == online ] ; then
          YCSB_PATH=`get_my_ai_attribute YCSB_PATH`
fi

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

CINDER=true
#
# Check if CBTool attached the Block storage volume.
# !! Script assumes /dev/vdb !!
#
sudo mkfs.ext4 /dev/vdb
if [ $? -ne 0 ] ; then
  syslog_netcat "Cinder did not attach the volume, or the guest does not see it."
  CINDER=false
fi

sudo mkdir -p ${CASSANDRA_DATA_DIR}

if $CINDER ; then
  sudo mount /dev/vdb ${CASSANDRA_DATA_DIR}
fi

#
# Update the cassandra config
#
TEMP_CASSANDRA_DATA_DIR=$(echo ${CASSANDRA_DATA_DIR} | sed 's/\//_+-_-+/g')
sudo sed -i "s/\/var\/lib\//${TEMP_CASSANDRA_DATA_DIR}\//g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/_+-_-+/\//g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/'Test Cluster'/'${my_ai_name}'/g" /etc/cassandra/conf/cassandra.yaml

#
# Cassandra directory structure
#
sudo mkdir -p ${CASSANDRA_DATA_DIR}/store/cassandra/data
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/commitlog 
sudo mkdir -p ${CASSANDRA_DATA_DIR}/cassandra/saved_caches
sudo chown -R cassandra:cassandra ${CASSANDRA_DATA_DIR}

for db in $cassandra_ips
do
    if [[ $(cat /etc/hosts | grep -c cassandra$pos) -eq 0 ]]
    then
        sudo sh -c "echo $db cassandra$pos cassandra-$pos >> /etc/hosts"
    fi
    ((pos++))
done

#
# Update Cassandra Config
#
sudo sed -i 's/initial_token:$/initial_token: 0/g' /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/- seeds:.*$/- seeds: $seed_ip/g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/listen_address:.*$/listen_address: $MY_IP/g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i 's/rpc_address:.*$/rpc_address: 0\.0\.0\.0/g' /etc/cassandra/conf/cassandra.yaml

#
# Remove possible old runs
#
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/saved_caches/*
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/data/system/*
sudo rm -rf ${CASSANDRA_DATA_DIR}/cassandra/commitlog/*

#
# Start the database
#
syslog_netcat "Starting cassandra on ${SHORT_HOSTNAME}" 
sudo service cassandra start 

# Give all the Java services time to start
wait_until_port_open 127.0.0.1 9160 20 5

#
# Init database
#
cassandra-cli -f cassandra-init.cassandra

provision_application_stop $START
exit 0
