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

standalone=`online_or_offline "$1"`

if [ $standalone == offline ] ; then
	post_boot_steps offline 
fi

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`

while [ -z $MY_IP ] ; do
        syslog_netcat "MY IP is null"
	MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`
	sleep 1
done

cassandra=`get_ips_from_role cassandra`
if [ -z $cassandra ] ; then
        syslog_netcat "cassandra IP is null"
        exit 1;
fi

seed=`get_ips_from_role seed`
if [ -z $seed ] ; then
        syslog_netcat "seed IP is null"
        exit 1;
fi

sudo service cassandra stop 

pos=1
tk_pos=0
sudo sh -c "echo 127.0.0.1 localhost > /etc/hosts"
sudo sh -c "echo $seed cassandra-seed >> /etc/hosts"
sudo sh -c "echo $MY_IP cassandra >> /etc/hosts"
for db in $cassandra
do
        sudo sh -c "echo $db cassandra$pos cassandra-$pos >> /etc/hosts"
        if [ $MY_IP = $db ] ; then
                tk_pos=$pos
        fi
        ((pos++))
done

token_pos=$(($tk_pos+2))
token=$(token-generator $pos | sed -n ${token_pos}p)

#
# Update Cassandra Config
#
sudo sed -i "s/initial_token:$/initial_token: ${token:10}/g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/- seeds:.*$/- seeds: $seed/g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i "s/listen_address:.*$/listen_address: ${MY_IP}/g" /etc/cassandra/conf/cassandra.yaml
sudo sed -i 's/rpc_address:.*$/rpc_address: 0\.0\.0\.0/g' /etc/cassandra/conf/cassandra.yaml

#
# Remove possible old runs
#
sudo rm -rf /var/lib/cassandra/saved_caches/*
sudo rm -rf /var/lib/cassandra/data/system/*
sudo rm -rf /var/lib/cassandra/commitlog/*

#
# Start the database
#
syslog_netcat "Starting cassandra on ${SHORT_HOSTNAME}" 
sudo service cassandra start 

provision_application_stop $START
