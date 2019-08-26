#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_mongos.sh - 
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

# Remove all previous configurations
sudo rm -rf $(sudo cat /etc/mongodb.conf | grep dbpath | cut -d '=' -f 2)/configdb/*

pos=1

for db in $mongo_ips
do
    if [[ $(cat /etc/hosts | grep -c "mongo$pos ") -eq 0 ]]
    then    
        sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
    fi
    ((pos++))
done

sudo sed -i "s/bind_ip.*$/bind_ip = ${my_ip_addr}/g" ${MONGODB_CONF_FILE}
sudo sed -i "s/port.*$/port = 27017/g" ${MONGODB_CONF_FILE}

my_dbpath=$(sudo cat /etc/mongodb.conf | grep dbpath | cut -d '=' -f 2)

sudo ps aux | grep "mongos --configdb cbcsrs/${mongocfg_ip}:27017 --port 27017 --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log" | grep -v grep > /dev/null 2>&1
if [[ $? -ne 0 ]]
then

    syslog_netcat "Starting mongo router (mongos) on ${SHORT_HOSTNAME}" 

    service_stop_disable mongod
    service_stop_disable mongodb

#
# Start Mongos 
#
    sudo pkill -9 -f configdb
    sudo screen -S MGSS -X quit
    sudo screen -d -m -S MGSS
    sudo screen -p 0 -S MGSS -X stuff "sudo mongos --configdb cbcsrs/${mongocfg_ip}:27017 --port 27017 --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log$(printf \\r)"
    #sudo screen -p 0 -S MGSS -X stuff "sudo mongos --configdb cbcsrs/${mongocfg_ip}:27017 --port 27017 --dbpath ${my_dbpath} --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log$(printf \\r)"
fi

wait_until_port_open ${my_ip_addr} 27017 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
    syslog_netcat "MongoDB Sharding server running"
else
    syslog_netcat "MongoS Sharding server failed to start"
fi

#
# Add Shards
#

mongo --host ${mongos_ip}:27017 --eval "db.printShardingStatus()" | grep cbdrs | grep host | awk '{ print $7 }' | sed 's/,//g' | sed 's/"//g' 2>&1 > /tmp/shardlist

pos=1
for db in $mongo_ips
do
    grep cbdrs${pos}/$db:27017 /tmp/shardlist > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        mongo --host ${mongos_ip}:27017 --eval "sh.addShard(\"cbdrs${pos}/$db:27017\")"
        syslog_netcat " Adding shard with \"mongo --host ${mongos_ip}:27017 --eval \"sh.addShard(\\"cbdrs${pos}/$db:27017\\")\""
    fi
    ((pos++))
done

check_mongodb_cluster_state ${mongos_ip} cbdrs 10 20

STATUS=$?

provision_application_stop $START

exit $STATUS
