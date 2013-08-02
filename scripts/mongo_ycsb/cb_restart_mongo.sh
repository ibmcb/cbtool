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

# Update Mongo Config
sudo sed -i 's/dbpath=.*$/dbpath=\/var\/lib\/mongo/g' /etc/mongod.conf
sudo sed -i 's/port=.*$/port = 27017/g' /etc/mongod.conf

syslog_netcat "Starting mongod on ${SHORT_HOSTNAME}" 
sudo service mongod start 

provision_application_stop $START
