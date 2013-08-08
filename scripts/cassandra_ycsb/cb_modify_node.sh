#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
# 
# cb_modify_node.sh -
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

cassandra=`get_ips_from_role cassandra`
if [ -z $mongos ] ; then
        syslog_netcat "cassandra IP is null"
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
# Determine remove or add 
#
dbs=`echo $cassandra | wc -w`

#
# Determine current nodes 
#
nodes=`nodetool ring | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}'`

#
# Modify Nodes 
#
pos=$dbs

#
# Still need to add the Remove node case, Cassandra should be easier to remove a node.
# Since in theory, there is on SPF in Cassandra.
#
for db in $cassandra
do
	db_chk=`cat /etc/hosts | grep $db | awk '{ print $2 }'`
	if [[ ! "$nodes" =~ "$db_chk" ]]; then 
             syslog_netcat " Adding the follow node : cassandra$pos"
             ((pos++))
	fi
done

if [ $? -gt 0 ] ; then
	syslog_netcat "problem modifying nodes $(hostname)"
	exit 1
fi
