#!/usr/bin/env bash

#/*******************************************************************************
#
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_mongo.sh -
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
MY_IP=$(ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1')

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

pos=1
sudo sh -c "echo 127.0.0.1 localhost > /etc/hosts"
for db in $cassandra
do
        sudo sh -c "echo $db cassandra$pos cassandra-$pos >> /etc/hosts"
        ((pos++))
done

#
# Update Cassandra Config
#
sudo sed -i 's/initial_token: $/initial_token: 0/g' /etc/cassandra/conf/cassandra.yaml
sudo sed -i 's/- seeds: $/- seeds: $seed/g' /etc/cassandra/conf/cassandra.yaml
sudo sed -i 's/listen_address: $/listen_address: $MY_IP/g' /etc/cassandra/conf/cassandra.yaml
sudo sed -i 's/rpc_address: $/rpc_address: 0\.0\.0\.0/g' /etc/cassandra/conf/cassandra.yaml

#
# Remove possible old runs
#
rm -rf /var/lib/cassandra/saved_caches/*
rm -rf /var/lib/cassandra/data/system/*

#
# Start the database
#
syslog_netcat "Starting cassandra on ${SHORT_HOSTNAME}" 
sudo service cassandra start 

provision_application_stop $START
