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

SERVICES[1]="mongodb"
SERVICES[2]="mongod"
service_stop_disable ${SERVICES[${LINUX_DISTRO}]}

MONGODB_CONF_FILE[1]=/etc/mongodb.conf
MONGODB_CONF_FILE[2]=/etc/mongod.conf

sudo mkdir -p ${MONGODB_DATA_DIR}

VOLUME=$(get_attached_volumes)
if [[ $VOLUME != "NONE" ]]
then
    if [[ $(check_filesystem $VOLUME) == "none" ]]
    then
        syslog_netcat "Creating $MONGODB_DATA_FSTYP filesystem on volume $VOLUME"
        sudo mkfs.$MONGODB_DATA_FSTYP -F $VOLUME
    fi
    syslog_netcat "Making $MONGODB_DATA_FSTYP filesystem on volume $VOLUME accessible through the mountpoint ${MONGODB_DATA_DIR}"
    sudo mount $VOLUME ${MONGODB_DATA_DIR}
fi

# Update Mongo Config

if [[ -f ${MONGODB_DATA_DIR} ]]
then
    TEMP_MONGODB_DATA_DIR=$(echo ${MONGODB_DATA_DIR} | sed 's/\//_+-_-+/g')
    sudo sed -i "s/dbpath=.*$/dbpath=${TEMP_MONGODB_DATA_DIR}\//g" ${MONGODB_CONF_FILE[${LINUX_DISTRO}]}
    sudo sed -i "s/_+-_-+/\//g" ${MONGODB_CONF_FILE[${LINUX_DISTRO}]}
fi
sudo sed -i "s/port=.*$/port = 27017/g" ${MONGODB_CONF_FILE[${LINUX_DISTRO}]}

syslog_netcat "Starting mongod on ${SHORT_HOSTNAME}" 
if [[ $(cat /etc/redhat-release | grep -c Fedora) -eq 0 ]]
then
    service_restart_enable ${SERVICES[${LINUX_DISTRO}]}
else
    sudo pkill -9 -f /usr/bin/mongod
    sudo screen -S MGS -X quit
    sudo screen -d -m -S MGS
    sudo screen -p 0 -S MGS -X stuff "sudo rm /var/lib/mongo/mongod.lock$(printf \\r)"
    sudo screen -p 0 -S MGS -X stuff "service mongod restart$(printf \\r)"
fi

wait_until_port_open 127.0.0.1 27017 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
        syslog_netcat "MongoDB server running - OK"
else
        syslog_netcat "MongoDB server failed to start - NOK"
fi

provision_application_stop $START
exit ${STATUS}
