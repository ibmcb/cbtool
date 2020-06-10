#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_mongo_cfg.sh -
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

cd ~
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

sudo ps aux | grep "$MONGODB_EXECUTABLE --configsvr --dbpath ${my_dbpath} --port 27017 --replSet cbcsrs --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log" | grep -v grep > /dev/null 2>&1
if [[ $? -ne 0 ]]
then    

    syslog_netcat "Starting mongo config server on ${SHORT_HOSTNAME}" 

    # Start Mongo Config-Server

    service_stop_disable mongod
    service_stop_disable mongodb
        
    sudo pkill -9 -f configsvr

    sudo screen -S MGCS -X quit
    sudo screen -d -m -S MGCS
    sudo screen -p 0 -S MGCS -X stuff "sudo rm /var/lib/mongo/mongod.lock$(printf \\r)"
    sudo screen -p 0 -S MGCS -X stuff "sudo $MONGODB_EXECUTABLE --configsvr --dbpath ${my_dbpath} --port 27017 --replSet cbcsrs --fork --bind_ip 0.0.0.0 --logpath /var/log/mongodb/mongodb.log$(printf \\r)"
    #sudo screen -p 0 -S MGCS -X stuff "sudo $MONGODB_EXECUTABLE --configsvr --dbpath $(sudo cat /etc/mongodb.conf | grep dbpath | cut -d '=' -f 2)$(printf \\r)"
fi
    
sleep 10

sudo screen -S MGCSI -X quit
sudo screen -d -m -S MGCSI
sudo screen -p 0 -S MGCSI -X stuff "mongo --port 27017 --eval \"var config = { _id: 'cbcsrs', members: [ { _id: 0, host: \\\\\"${my_ip_addr}:27017\\\\\" } ] }; rs.initiate( config ); while (rs.status().startupStatus || (rs.status().hasOwnProperty('myState') && rs.status().myState != 1)) { printjson( rs.status() ); sleep(1000); }; printjson( rs.status() );\"$(printf \\r)"

wait_until_port_open 127.0.0.1 27017 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
    syslog_netcat "MongoDB Configuration server running - OK"
else
    syslog_netcat "MongoS Configuration server failed to start - NOK"
fi

check_mongodb_cluster_state ${mongos_ip} cbdrs 0 20

provision_application_stop $START

exit ${STATUS}
