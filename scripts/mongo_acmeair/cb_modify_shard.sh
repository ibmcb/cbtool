#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
# 
# cb_modify_shard.sh -
#
#
# @author: Joe Talerico - jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_acmeair_common.sh

START=`provision_application_start`

cd ~

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

#
# Determine remove or add 
#
# old_dbs=`cat /etc/hosts | sed -n '/.*db.*/p' | wc -l`
dbs=`echo $mongo_ips | wc -w`

#
# Udpate Mongos sh.addShard 
#
# Determine current shards
#
shards=`mongo --host mongos:27017 --eval "sh.status()" | sed -n '/.*"host" : "\(.*\)" }$/p' | sed -e 's/.*"host" : "\(.*\):[0-9]*" }$/\1/'`

#
# Modify Shards
#

# This will only work for adding... Removing might be more involved.
pos=$dbs

for db in $mongo_ips
do
    db_chk=`cat /etc/hosts | grep $db | awk '{ print $2 }'`
    if [[ ! "$shards" =~ "$db_chk" ]]
    then 
        mongo --host mongos:27017 --eval "sh.addShard(\"mongo$pos:27017\")"
        syslog_netcat " Adding the follow shard :mongo$pos:27017 "
        ((pos++))
    fi
done

if [ $? -gt 0 ] ; then
    syslog_netcat "problem adding shard from ${SHORT_HOSTNAME} - NOK"
    exit 1
fi
