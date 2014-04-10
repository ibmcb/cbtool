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

#####################################################################################
# Common routines for YCSB 
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [[ -e $dir/cb_common.sh ]]
then
    source $dir/cb_common.sh
else
    source $dir/../common/cb_common.sh
fi

MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`

while [[ -z $MY_IP ]] 
do
    syslog_netcat "MY IP is null"
    MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`
    sleep 1
done

YCSB_PATH=$(get_my_ai_attribute_with_default ycsb_path ~/YCSB)
eval YCSB_PATH=${YCSB_PATH}

CASSANDRA_DATA_DIR=$(get_my_ai_attribute_with_default cassandra_data_dir /dbstore)
eval CASSANDRA_DATA_DIR=${CASSANDRA_DATA_DIR}

cassandra_ips=`get_ips_from_role cassandra`

cassandra_ips_csv=`echo ${cassandra_ips} | sed ':a;N;$!ba;s/\n/, /g'`

if [[ -z $cassandra_ips ]]
then
    syslog_netcat "No VMs with the \"cassandra\" role have been found on this AI"
    exit 1;
else
    syslog_netcat "The VMs with the \"cassandra\" role on this AI have the following IPs: ${cassandra_ips_csv}"
fi

seed_ip=`get_ips_from_role seed`
if [[ -z $seed_ip ]]
then
    syslog_netcat "No VMs with the \"seed\" role have been found on this AI"
    exit 1;
else
    syslog_netcat "The VM with the \"seed\" role on this AI has the following IP: ${seed_ip}"
fi

#
# Update /etc/hosts file
#
pos=1
if [[ $(cat /etc/hosts | grep -c cassandra-seed) -eq 0 ]]
then
    sudo sh -c "echo $seed_ip cassandra-seed >> /etc/hosts"
fi