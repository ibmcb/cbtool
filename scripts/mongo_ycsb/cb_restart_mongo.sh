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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

pos=1
    
for db in $mongo_ips
do
    if [[ $(cat /etc/hosts | grep -c "mongo$pos ") -eq 0 ]]
    then
        sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
    fi
    ((pos++))
done

service_stop_disable mongod
service_stop_disable mongodb

# Update Mongo Config

sudo chown -R ${MONGODB_USER}:${MONGODB_USER} ${MONGODB_DATA_DIR}

if [[ -d ${MONGODB_DATA_DIR} ]]
then
    sudo sed -i "s^dbpath=.*$^dbpath=${MONGODB_DATA_DIR}^g" ${MONGODB_CONF_FILE}
fi
sudo sed -i "s/bind_ip.*$/bind_ip = ${my_ip_addr}/g" ${MONGODB_CONF_FILE}
sudo sed -i "s/port.*$/port = 27017/g" ${MONGODB_CONF_FILE}

my_position=$(cat /etc/hosts | grep ${my_ip_addr} | grep mongodb- | tail -1 | awk '{ print $2 }' | sed 's/mongo//g')
my_dbpath=$(sudo cat /etc/mongodb.conf | grep dbpath | cut -d '=' -f 2)

sudo ps aux | grep "mongod --port 27017 --dbpath ${my_dbpath} --shardsvr --replSet cbdrs${my_position} --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log" | grep -v grep > /dev/null 2>&1
if [[ $? -ne 0 ]]
then

    syslog_netcat "Starting mongod on ${SHORT_HOSTNAME}" 

    sudo pkill -9 -f shardsvr
    sudo screen -S MGS -X quit
    sudo screen -d -m -S MGS
    sudo screen -p 0 -S MGS -X stuff "sudo rm /var/lib/mongo/mongod.lock$(printf \\r)"
    sudo screen -p 0 -S MGS -X stuff "mongod --port 27017 --dbpath ${my_dbpath} --shardsvr --replSet cbdrs${my_position} --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log$(printf \\r)"
fi
    
sleep 10

sudo screen -S MGSI -X quit
sudo screen -d -m -S MGSI
sudo screen -p 0 -S MGSI -X stuff "mongo --port 27017 --eval \"var config = { _id: \\\\\"cbdrs${my_position}\\\\\", members: [ { _id: 0, host: \\\\\"${my_ip_addr}:27017\\\\\" } ] }; rs.initiate( config ); while (rs.status().startupStatus || (rs.status().hasOwnProperty('myState') && rs.status().myState != 1)) { printjson( rs.status() ); sleep(1000); }; printjson( rs.status() );\"$(printf \\r)"

wait_until_port_open ${my_ip_addr} 27017 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
    syslog_netcat "MongoDB server running - OK"
else
    syslog_netcat "MongoDB server failed to start - NOK"
fi

check_mongodb_cluster_state ${mongos_ip} cbdrs 0 20

provision_application_stop $START

exit ${STATUS}
