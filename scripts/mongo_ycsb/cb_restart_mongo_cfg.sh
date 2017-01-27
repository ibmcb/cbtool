#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_mongo_cfg.sh -
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

automount_data_dirs

# Remove all previous configurations
sudo rm -rf ${MONGODB_DATA_DIR}/configdb/*

pos=1

for db in $mongo_ips
do
    if [[ $(cat /etc/hosts | grep -c "mongo$pos ") -eq 0 ]]
    then    
        sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
    fi
    ((pos++))
done

linux_distribution

# Start Mongo Config-Serverv

SERVICES[1]="mongodb"
SERVICES[2]="mongod"

if [[ ! -f ${MONGODB_DATA_DIR} ]]
then
    MONGODB_DATA_DIR=/var/lib/mongo
fi

sudo pkill -9 -f ${SERVICES[${LINUX_DISTRO}]}

sudo screen -S MGCS -X quit
sudo screen -d -m -S MGCS
sudo screen -p 0 -S MGCS -X stuff "sudo rm /var/lib/mongo/mongod.lock$(printf \\r)"
sudo screen -p 0 -S MGCS -X stuff "sudo ${SERVICES[${LINUX_DISTRO}]} --configsvr --dbpath ${MONGODB_DATA_DIR}$(printf \\r)"

wait_until_port_open 127.0.0.1 27019 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
    syslog_netcat "MongoDB Configuration server running - OK"
else
    syslog_netcat "MongoS Configuration server failed to start - NOK"
fi

provision_application_stop $START

exit ${STATUS}
