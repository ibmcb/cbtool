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

MYSQL_DATABASE_NAME=`get_my_ai_attribute_with_default mysql_database_name sysbenchdb`
MYSQL_ROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_root_password temp4now`
MYSQL_NONROOT_USER=`get_my_ai_attribute_with_default mysql_nonroot_user sysbench`
MYSQL_NONROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_nonroot_password sysbench`
MYSQL_DATA_DIR=`get_my_ai_attribute_with_default mysql_data_dir /sysbench`
MYSQL_CONF_FILE=`get_my_ai_attribute_with_default mysql_conf_file /etc/mysql/mysql.conf.d/mysqld.cnf`
MYSQL_RAM_PERCENTAGE=`get_my_ai_attribute_with_default mysql_ram_percentage 70`
MYSQL_INNODB_IO_CAPACITY=`get_my_ai_attribute_with_default mysql_innodb_io_capacity 200`
MYSQL_INNODB_LOG_FILE_SIZE=`get_my_ai_attribute_with_default mysql_innodb_log_file_size 48M`
MYSQL_QUERY_CACHE_SIZE=`get_my_ai_attribute_with_default mysql_query_cache_size 16M`
MYSQL_TMP_TABLE_SIZE=`get_my_ai_attribute_with_default mysql_tmp_table_size 16M`
MYSQL_TABLE_OPEN_CACHE=`get_my_ai_attribute_with_default mysql_table_open_cache 2000`
MYSQL_ENABLE_PMM_CLIENT=`get_my_ai_attribute_with_default mysql_enable_pmm_client False`
MYSQL_PMM_SERVER=`get_my_ai_attribute_with_default mysql_pmm_server 0.0.0.0:80`
LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`

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

${SUDO_CMD} sed -i "s^bind-address.*^bind-address            = ${LOAD_GENERATOR_TARGET_IP}^g" ${MYSQL_CONF_FILE}

${SUDO_CMD} sed -i '/innodb_io_capacity/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/innodb_log_file_size/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/innodb_buffer_pool_size/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/query_cache_size/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/tmp_table_size/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/table_open_cache/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/innodb_buffer_pool_dump_at_shutdown/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/innodb_buffer_pool_load_at_startup/d' ${MYSQL_CONF_FILE}
${SUDO_CMD} sed -i '/max_connections/d' ${MYSQL_CONF_FILE}

# Set mysql's memory cache size to be a percentage of main memory
check_container
if [ ${IS_CONTAINER} -eq 1 ] && [ `get_my_vm_attribute model` == "pdm" ] ; then
        size=`get_my_vm_attribute size`
	syslog_netcat "MySQL is running on bare metal, will use a container size of: ${size}"
        mb_total=$(echo $size | cut -d "-" -f 2)
	mb=$(echo "${mb_total} * ${MYSQL_RAM_PERCENTAGE} / 100" | bc)
else
	syslog_netcat "MySQL is running in a VM."
        # We are in a VM
        kb=$(cat /proc/meminfo  | sed -e "s/ \+/ /g" | grep MemTotal | cut -d " " -f 2)
        mb=$(echo "$kb / 1024 * ${MYSQL_RAM_PERCENTAGE} / 100" | bc)
fi

syslog_netcat "Calculated cache size: ${mb} MB"

${SUDO_CMD} su -c "echo 'innodb_buffer_pool_size = ${mb}M' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'innodb_io_capacity = ${MYSQL_INNODB_IO_CAPACITY}' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'innodb_log_file_size = ${MYSQL_INNODB_LOG_FILE_SIZE}' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'query_cache_size = ${MYSQL_QUERY_CACHE_SIZE}' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'tmp_table_size = ${MYSQL_TMP_TABLE_SIZE}' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'table_open_cache = ${MYSQL_TABLE_OPEN_CACHE}' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'max_connections = 2000' >> ${MYSQL_CONF_FILE}"
${SUDO_CMD} su -c "echo 'large-pages' >> ${MYSQL_CONF_FILE}"

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
		if test ${MYSQL_ENABLE_PMM_CLIENT} = 'True'; then
			if ! grep Ubuntu /etc/lsb-release >/dev/null 2>&1; then
				syslog_netcat "PMM Client installation only supported on Ubuntu"
			else
				${SUDO_CMD} sed -i '/innodb_monitor_enable/d' ${MYSQL_CONF_FILE}
				${SUDO_CMD} sed -i '/performance_schema/d' ${MYSQL_CONF_FILE}
				${SUDO_CMD} su -c "echo 'innodb_monitor_enable=all' >> ${MYSQL_CONF_FILE}"
				${SUDO_CMD} su -c "echo 'performance_schema=ON' >> ${MYSQL_CONF_FILE}"
				service mysql restart

				wget https://repo.percona.com/apt/percona-release_latest.generic_all.deb
				sudo dpkg -i percona-release_latest.generic_all.deb
				sudo apt-get update
				sudo apt-get -y install pmm-client
				pmm-admin config --server ${MYSQL_PMM_SERVER}
				pmm-admin add mysql --user root --password ${MYSQL_ROOT_PASSWORD} --create-user
				pmm-admin add mysql --user root --password ${MYSQL_ROOT_PASSWORD} --query-source perfschema
			fi
		fi

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
