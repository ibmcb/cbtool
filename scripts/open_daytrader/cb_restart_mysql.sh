#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

source ~/.bashrc
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

MYSQL_DATABASE_NAME=`get_my_ai_attribute_with_default mysql_database_name tradedb`
MYSQL_ROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_root_password temp4now`
MYSQL_NONROOT_USER=`get_my_ai_attribute_with_default mysql_nonroot_user trade`
MYSQL_NONROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_nonroot_password trade`
MYSQL_DATA_DIR=`get_my_ai_attribute_with_default mysql_data_dir /tradedb`
TRADEDB_SIZE=`get_my_ai_attribute_with_default tradedb_size small`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
NETSTAT_CMD=`which netstat`
SUDO_CMD=`which sudo`
ATTEMPTS=3
START=`provision_application_start`

SERVICES[1]="mysql"
SERVICES[2]="mysqld"

if [[ ${MYSQL_DATA_DIR} != "/var/lib/mysql"  && ! -L /var/lib/mysql ]]
then
    syslog_netcat "Relocating MySQL base directory..."
	service_stop_disable ${SERVICES[${LINUX_DISTRO}]}
    ${SUDO_CMD} rsync -az --delete --inplace /var/lib/mysql/ ${MYSQL_DATA_DIR}/
    ${SUDO_CMD} rm -rf /var/lib/mysql
    ${SUDO_CMD} ln -s ${MYSQL_DATA_DIR} /var/lib/mysql        
fi    

${SUDO_CMD} sed -i "s^bind-address.*^bind-address            = $my_ip_addr^g" /etc/mysql/mysql.conf.d/mysqld.cnf

if [[ $(${SUDO_CMD} ls /etc/apparmor.d/tunables/ | grep -c alias) -ne 0 ]]
then
    if [[ $(${SUDO_CMD} cat /etc/apparmor.d/tunables/alias | grep -c ${MYSQL_DATA_DIR}) -eq 0 ]]
    then
        ${SUDO_CMD} bash -c "echo \"alias /var/lib/mysql/ -> ${MYSQL_DATA_DIR}/,\" >> /etc/apparmor.d/tunables/alias"
        ${SUDO_CMD} service apparmor reload
    fi
fi

while [ "$ATTEMPTS" -ge  0 ]
do
	syslog_netcat "Checking for MySQL instances in $SHORT_HOSTNAME...."
	${SUDO_CMD} mysql --user=root --password=${MYSQL_ROOT_PASSWORD} -e "SHOW DATABASES;" | grep $MYSQL_DATABASE_NAME
	if [ $? -eq 0 ]
	then
		syslog_netcat "MySQL restarted succesfully on $SHORT_HOSTNAME - OK"
		provision_application_stop $START
		exit 0
	else 
		let ATTEMPTS=ATTEMPTS-1
		syslog_netcat "Trying to start MySQL"
		service_stop_disable ${SERVICES[${LINUX_DISTRO}]}
		service_restart_enable ${SERVICES[${LINUX_DISTRO}]}
		sleep 10
		${SUDO_CMD} mysql --user=root --password=${MYSQL_ROOT_PASSWORD} -e "set global max_connect_errors=100000;FLUSH HOSTS;"
		${SUDO_CMD} mysql --user=root --password=${MYSQL_ROOT_PASSWORD} -e "CREATE DATABASE ${MYSQL_DATABASE_NAME}; "
		${SUDO_CMD} mysql --user=root --password=${MYSQL_ROOT_PASSWORD} -e "GRANT ALL ON ${MYSQL_DATABASE_NAME}.* TO '${MYSQL_NONROOT_USER}'@'%' IDENTIFIED BY '${MYSQL_NONROOT_PASSWORD}';"
	fi
done

syslog_netcat "MySQL could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
