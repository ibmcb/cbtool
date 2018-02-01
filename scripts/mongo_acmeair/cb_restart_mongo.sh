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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_acmeair_common.sh

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

SERVICES[1]="mongodb"
SERVICES[2]="mongod"
service_stop_disable ${SERVICES[${LINUX_DISTRO}]}

# Update Mongo Config

sudo chown -R ${MONGODB_USER}:${MONGODB_USER} ${MONGODB_DATA_DIR}

if [[ -d ${MONGODB_DATA_DIR} ]]
then
    sudo sed -i "s^dbpath=.*$^dbpath=${MONGODB_DATA_DIR}^g" ${MONGODB_CONF_FILE}
fi
sudo sed -i "s/bind_ip.*$/bind_ip = ${my_ip_addr}/g" ${MONGODB_CONF_FILE}
sudo sed -i "s/port.*$/port = 27017/g" ${MONGODB_CONF_FILE}

syslog_netcat "Starting mongod on ${SHORT_HOSTNAME}" 
if [[ $(cat /etc/redhat-release | grep -c Fedora) -eq 0 ]]
then
    service_restart_enable ${SERVICES[${LINUX_DISTRO}]}
else
    sudo pkill -9 -f $MONGODB_EXECUTABLE
    sudo screen -S MGS -X quit
    sudo screen -d -m -S MGS
    sudo screen -p 0 -S MGS -X stuff "sudo rm /var/lib/mongo/mongod.lock$(printf \\r)"
    sudo screen -p 0 -S MGS -X stuff "service mongod restart$(printf \\r)"
fi

wait_until_port_open ${my_ip_addr} 27017 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
    syslog_netcat "MongoDB server running - OK"
else
    syslog_netcat "MongoDB server failed to start - NOK"
fi

provision_application_stop $START
exit ${STATUS}
