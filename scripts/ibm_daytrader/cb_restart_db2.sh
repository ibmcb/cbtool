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
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

DB2_INSTANCE_NAME=`get_my_ai_attribute_with_default db2_instance_name klabuser`
INSTANCE_PATH=/home/${DB2_INSTANCE_NAME}
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
NETSTAT_CMD=`which netstat`
SUDO_CMD=`which sudo`
ATTEMPTS=3
START=`provision_application_start`
SIZE=`get_my_ai_attribute_with_default tradedb_size small`

syslog_netcat "Moving /tradedb_${SIZE} to /tradedb"
sudo mv /tradedb_${SIZE} /tradedb

syslog_netcat "Setting DB2 for the new hostname ($SHORT_HOSTNAME)"
sudo chmod 666 $INSTANCE_PATH/sqllib/db2nodes.cfg
chmod u+wx $INSTANCE_PATH/sqllib/db2nodes.cfg
echo "0 $SHORT_HOSTNAME 0" > $INSTANCE_PATH/sqllib/db2nodes.cfg
sudo rm -rf $INSTANCE_PATH/sqllib/spmlog/*
sudo -u ${DB2_INSTANCE_NAME} -H sh -c "cd ~; . ~/.bashrc; db2 update dbm cfg using spm_name NULL"

syslog_netcat "Done setting DB2 for the new hostname ($SHORT_HOSTNAME)"

while [ "$ATTEMPTS" -ge  0 ]
do
	syslog_netcat "Checking for DB2 instances in $SHORT_HOSTNAME...."
	result1="$($SUDO_CMD $NETSTAT_CMD -atnp | grep 50007)"
	result2="$(ps aux | grep db2acd | grep -v grep)"
	if [ x"$result1" == x -o y"$result2" == y ] ; then 
		sleep 2
		syslog_netcat "DB2 not running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"
		syslog_netcat "DB2 being restarted on $SHORT_HOSTNAME"
		let ATTEMPTS=ATTEMPTS-1
		syslog_netcat "Running db2stop...."
		sudo -u ${DB2_INSTANCE_NAME} -H sh -c "cd ~; . ~/.bashrc; $INSTANCE_PATH/sqllib/adm/db2stop force"
		syslog_netcat "Done running db2stop...."
		sleep 2
		syslog_netcat "Running db2_kill..."
		sudo -u ${DB2_INSTANCE_NAME} -H sh -c "cd ~; . ~/.bashrc; /opt/ibm/db2/V9.7/bin/db2_kill"
		syslog_netcat "Done running db2_kill"
		sleep 2
		syslog_netcat "Running db2ftok..."
		sudo -u ${DB2_INSTANCE_NAME} -H sh -c "cd ~; . ~/.bashrc; /opt/ibm/db2/V9.7/bin/db2ftok"
		syslog_netcat "Done running db2ftok"
		sleep 2
		syslog_netcat "Running db2start once...."
		sudo -u ${DB2_INSTANCE_NAME} -H sh -c "cd ~; . ~/.bashrc; $INSTANCE_PATH/sqllib/adm/db2start"
		syslog_netcat "Done. Let's wait 5 seconds and check for running DB2 instances again..."
		sleep 5
		#db2 connect to tradedb
		#syslog_netcat "Performing a DB2 reorgchk ...."
		#db2 reorgchk update statistics on table all
		#db2 terminate
		#db2 disconnect all
		#syslog_netcat "Reorgchk complete."
	else
		syslog_netcat "DB2 restarted succesfully on $SHORT_HOSTNAME - OK"
		provision_application_stop $START
		exit 0
	fi
done
syslog_netcat "DB2 could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2