#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2009 Standard Performance Evaluation Corporation (SPEC)
#               All rights reserved.
#
# This source code is provided as is, without any express or implied warranty.
# 
# cb_modify_shard.sh -
#
#
# @author: Joe Talerico - jtaleric@redhat.com
#/*******************************************************************************

source ~/.bashrc
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
        source $dir/cb_common.sh
else
        source $dir/../common/cb_common.sh
fi

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
for db in $mongo
do
        sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
        ((pos++))
done

#
# Determine remove or add 
#
# old_dbs=`cat /etc/hosts | sed -n '/.*db.*/p' | wc -l`
dbs=`echo $mongo | wc -w`

#
# Udpate Mongos sh.addShard 
#
# Determine current shards
#
shards=`mongo --host mongos:27017 --eval "sh.status()" | sed -n '/.*"host" : "\(.*\)" }$/p' | sed -e 's/.*"host" : "\(.*\):[0-9]*" }$/\1/'`

#
# Modify Shards
#
mongo=`get_ips_from_role mongodb`
# This will only work for adding... Removing might be more involved.
pos=$dbs

for db in $mongo
do
	db_chk=`cat /etc/hosts | grep $db | awk '{ print $2 }'`
	if [[ ! "$shards" =~ "$db_chk" ]]; then 
             mongo --host mongos:27017 --eval "sh.addShard(\"mongo$pos:27017\")"
             syslog_netcat " Adding the follow shard :mongo$pos:27017 "
             ((pos++))
	fi
done

if [ $? -gt 0 ] ; then
	syslog_netcat "problem running ycsb prime client on $(hostname)"
	exit 1
fi
