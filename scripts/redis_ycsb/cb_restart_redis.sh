#!/usr/bin/env bash

#/*******************************************************************************
#
# This source code is provided as is, without any express or implied warranty.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

pos=1

for db in $redis_ip
do
    if [[ $(cat /etc/hosts | grep -c "redis$pos ") -eq 0 ]]
    then
        sudo sh -c "echo $db redis$pos redis-$pos >> /etc/hosts"
    fi
    ((pos++))
done

SERVICES[1]="redis-server"
SERVICES[2]="redis"
service_stop_disable ${SERVICES[${LINUX_DISTRO}]}

REDIS_CONF_FILE[1]=/etc/redis/redis.conf
REDIS_CONF_FILE[2]=/etc/redis.conf

# Update Redis Config

if [[ -f ${REDIS_DATA_DIR} ]]
then
    TEMP_REDIS_DATA_DIR=$(echo ${REDIS_DATA_DIR} | sed 's/\//_+-_-+/g')
    sudo sed -i "s/dir *$/dir ${TEMP_REDIS_DATA_DIR}\//g" ${REDIS_CONF_FILE[${LINUX_DISTRO}]}
    sudo sed -i "s/_+-_-+/\//g" ${REDIS_CONF_FILE[${LINUX_DISTRO}]}
fi
sudo sed -i "s/port *$/port 6379/g" ${REDIS_CONF_FILE[${LINUX_DISTRO}]}

syslog_netcat "Starting Redis on ${SHORT_HOSTNAME}" 
service_restart_enable ${SERVICES[${LINUX_DISTRO}]}

wait_until_port_open 127.0.0.1 6379 20 5

STATUS=$?

if [[ ${STATUS} -eq 0 ]]
then
        syslog_netcat "Redis server running"
else
        syslog_netcat "Redis server failed to start"
fi

provision_application_stop $START
exit ${STATUS}

