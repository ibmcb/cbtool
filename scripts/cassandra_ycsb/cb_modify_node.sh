#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
# 
# cb_modify_node.sh -
#
#
# @author: Joe Talerico - jtaleric@redhat.com
#/*******************************************************************************

cd ~
source ~/.bashrc
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
        source $dir/cb_common.sh
else
        source $dir/../common/cb_common.sh
fi

cassandra=`get_ips_from_role cassandra`
if [ -z "$cassandra" ] ; then
        syslog_netcat "cassandra IP is null"
        exit 1;
fi

MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`

while [ -z "$MY_IP" ] ; do
        syslog_netcat "MY IP is null"
        MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`
        sleep 1
done

seed=`get_ips_from_role seed`
if [ -z $seed ] ; then
        syslog_netcat "seed IP is null"
        exit 1;
fi

#
# Determine remove or add 
#
# dbs=`echo $cassandra | wc -w`

#
# Determine current nodes 
#
nodes=`nodetool ring | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}'`
if [ $? == 1 ] ; then 
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
	if ! [[ "$nodes" =~ "$db_chk" ]]; then 
             syslog_netcat " Adding the follow node : cassandra$pos"
             ((pos++))
	fi
 done
else 
 exit 0
fi

if [ $? -gt 0 ] ; then
	syslog_netcat "problem modifying nodes $(hostname)"
	exit 1
fi
