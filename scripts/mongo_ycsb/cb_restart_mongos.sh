#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2009 Standard Performance Evaluation Corporation (SPEC)
#               All rights reserved.
#
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_mongos.sh - 
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

# Remove all previous configurations
sudo rm -rf /data/configdb/*

mongos=`get_ips_from_role mongos`
if [ -z $mongos ] ; then
        syslog_netcat "mongos IP is null"
        exit 1;
fi

mongocfg=`get_ips_from_role mongo_cfg_server`
if [ -z $mongocfg ] ; then
        syslog_netcat "mongocfg IP is null"
        exit 1;
fi

mongo=`get_ips_from_role mongodb`
pos=1
sudo sh -c "echo 127.0.0.1 localhost > /etc/hosts"
sudo sh -c "echo $mongocfg mongo-cfg-server >> /etc/hosts"
sudo sh -c "echo $mongos mongos >> /etc/hosts"
#
# Add MongoDB Servers to /etc/hosts
#
for db in $mongo
do
        sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
        ((pos++))
done

#
# Start Mongos 
#
sudo mongos --configdb mongo-cfg-server:27019 > mongos.out 2>&1&
syslog_netcat "Mongos Service started"

#
# Needed to wait for mongos to fully start before adding shards.
#
sleep 2

#
# Add Shards
#
mongo=`get_ips_from_role mongodb`
pos=1
for db in $mongo
do
	mongo --host mongos:27017 --eval "sh.addShard(\"mongo$pos:27017\")"
	syslog_netcat " Adding the follow shard :mongo$pos:27017 "
        ((pos++))
done

#
# Build YCSB Database
#
sudo /root/YCSB/bin/ycsb load mongodb -s -P /root/YCSB/workloads/workloada -p recordcount=1000000

#
# Enable Sharding for YCSB
#
mongo --host mongos:27017 --eval "sh.enableSharding(\"ycsb\")"
mongo mongos:27017/ycsb --eval "db.usertable.ensureIndex( { _id: \"hashed\" } )"
mongo mongos:27017/ycsb --eval "sh.shardCollection(\"ycsb.usertable\", { _id: \"hashed\" } )"

#
# Change chunk size to 32MB (optiona?) 
#
mongo --host mongos:27017/ycsb --eval "db.settings.save( { _id:\"chunksize\", value: 32 } )"

provision_application_stop $START
