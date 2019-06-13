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

MYSQL_CONF_FILE=`get_my_ai_attribute_with_default mysql_conf_file /etc/mysql/mysql.conf.d/mysqld.cnf`
MYSQL_RAM_PERCENTAGE=`get_my_ai_attribute_with_default mysql_ram_percentage 70`
MYSQL_INNODB_IO_CAPACITY=`get_my_ai_attribute_with_default mysql_innodb_io_capacity 200`
MYSQL_INNODB_LOG_FILE_SIZE=`get_my_ai_attribute_with_default mysql_innodb_log_file_size 48M`
MYSQL_QUERY_CACHE_SIZE=`get_my_ai_attribute_with_default mysql_query_cache_size 16M`
MYSQL_TMP_TABLE_SIZE=`get_my_ai_attribute_with_default mysql_tmp_table_size 16M`
MYSQL_TABLE_OPEN_CACHE=`get_my_ai_attribute_with_default mysql_table_open_cache 2000`

SUDO_CMD=`which sudo`

RESTART_MYSQL=0

update_mysql_setting()
{
	SETTING=$1
	VALUE=$2

	if grep "${SETTING} = ${VALUE}" ${MYSQL_CONF_FILE} >/dev/null; then
		return
	fi

	syslog_netcat "Updating ${SETTING} to ${VALUE}"
	${SUDO_CMD} sed -i 's/${SETTING}.*/${SETTING} = ${VALUE}' ${MYSQL_CONF_FILE}
	RESTART_MYSQL=1
}

# Check if mysql has the right cache size or update it.
kb=$(cat /proc/meminfo  | sed -e "s/ \+/ /g" | grep MemTotal | cut -d " " -f 2) 
mb=$(echo "$kb / 1024 * ${MYSQL_RAM_PERCENTAGE} / 100" | bc)

update_mysql_setting innodb_buffer_pool_size ${mb}M
update_mysql_setting innodb_io_capacity ${MYSQL_INNODB_IO_CAPACITY}
update_mysql_setting innodb_log_file_size ${MYSQL_INNODB_LOG_FILE_SIZE}
update_mysql_setting query_cache_size ${MYSQL_QUERY_CACHE_SIZE}
update_mysql_setting tmp_table_size ${MYSQL_TMP_TABLE_SIZE}
update_mysql_setting table_open_cache ${MYSQL_TABLE_OPEN_CACHE}

if test ${RESTART_MYSQL} = 1; then
	service mysql restart
	syslog_netcat "Restarting MySQL after setting update"
fi
