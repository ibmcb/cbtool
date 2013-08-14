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

REG_HOSTNAME=$1
REG_USERNAME=$2
REG_LOCAL_DIR=$3

echo "Updating git master branch on ${REG_HOSTNAME} (user ${REG_USERNAME})"
update_git=`ssh ${REG_HOSTNAME} "su - ${REG_USERNAME}; git pull"`
if [ ${update_git} -eq 0 ]
then
	echo "Git master branch updated successfully"
else
	echo "Git error update error!"
	exit 1
fi

echo "Creating Regression Test experiment plan"
${REG_LOCAL_DIR}/regression/regression_test.py make
scp 

exit

ssh ${REG_USERNAME} "su - ${REG_USERNAME}; rm ~/*.csv; ./hard_reset.sh; time ./cloudbench/cloudbench.py --trace util/regression_test/regression_test_experiment_plan.txt 2>&1 > x.txt

CB_DIRECTORY=$3
CB_STORES_DIRECTORY=$4
CB_PORT=$5

if [ -z "$CB_USERNAME" ]
then
	CB_USERNAME=${LOGNAME}
fi

if [ -z "$CB_DIRECTORY" ]
then
	CB_DIRECTORY=${HOME}
fi

mkdir -p ${CB_STORES_DIRECTORY}/logs

TMPLT_CB_STORES_DIRECTORY=`echo ${CB_STORES_DIRECTORY} | sed s/"\\/"/"_+-"/g`

if [ -z "$CB_PORT" ]
then
	CB_PORT="49004"
else
	CB_PORT=${CB_PORT}
fi

if [ "${CB_STORE_TYPE}" = "object" ]
then
	is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_redis.conf`
	if [ ${is_process_running} -eq 0 ]
	then
		echo "Configuring Object Store configuration file from template"
		cp ${CB_DIRECTORY}/scripts/stores/redis.conf.template ${CB_STORES_DIRECTORY}/${CB_USERNAME}_redis.conf

		sed -i s/"CB_PORT"/"${CB_PORT}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_redis.conf
		sed -i s/"TMPLT_CB_STORES_DIRECTORY"/"${TMPLT_CB_STORES_DIRECTORY}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_redis.conf
		sed -i s/"_+-"/"\\/"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_redis.conf

		echo "Starting Object Store"
		redis_binary=`which redis-server`
		$redis_binary ${CB_STORES_DIRECTORY}/${CB_USERNAME}_redis.conf

		is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_redis.conf`
	else
		echo "Object Store already configured and running"
		exit 0
	fi
fi

if [ "${CB_STORE_TYPE}" = "log" ]
then
	is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_rsyslog.conf`
	if [ ${is_process_running} -eq 0 ]
	then
		echo "Configuring Log Store configuration file from template"
		cp ${CB_DIRECTORY}/scripts/stores/rsyslog.conf.template ${CB_STORES_DIRECTORY}/${CB_USERNAME}_rsyslog.conf

		sed -i s/"CB_PORT"/"${CB_PORT}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_rsyslog.conf
		sed -i s/"TMPLT_CB_STORES_DIRECTORY"/"${TMPLT_CB_STORES_DIRECTORY}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_rsyslog.conf
		sed -i s/"_+-"/"\\/"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_rsyslog.conf

		mkdir -p ${CB_STORES_DIRECTORY}/logs

		echo "Starting Log Store"
		rsyslog_binary=`which rsyslogd`
		$rsyslog_binary -c 4 -f ${CB_STORES_DIRECTORY}/${CB_USERNAME}_rsyslog.conf -i ${CB_STORES_DIRECTORY}/rsyslog.pid

		is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_rsyslog.conf`
	else
		echo "Log Store already configured and running"
		exit 0
	fi
fi

if [ "${CB_STORE_TYPE}" = "metric" ]
then
	is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_mdb.conf`
	if [ ${is_process_running} -eq 0 ]
	then
		echo "Configuring Metric Store configuration file from template"
		cp ${CB_DIRECTORY}/scripts/stores/mdb.conf.template ${CB_STORES_DIRECTORY}/${CB_USERNAME}_mdb.conf

		sed -i s/"CB_PORT"/"${CB_PORT}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_mdb.conf
		sed -i s/"TMPLT_CB_STORES_DIRECTORY"/"${TMPLT_CB_STORES_DIRECTORY}"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_mdb.conf
		sed -i s/"_+-"/"\\/"/g ${CB_STORES_DIRECTORY}/${CB_USERNAME}_mdb.conf

		echo "Starting Metric Store"
		mongod_binary=`which mongod`
		$mongod_binary -f ${CB_STORES_DIRECTORY}/${CB_USERNAME}_mdb.conf --pidfilepath ${CB_STORES_DIRECTORY}/mdb.pid

		is_process_running=`sudo ps aux | grep -v grep | grep -c ${CB_USERNAME}_mdb.conf`
    	
		sleep 90
	else
		echo "Metric Store already configured and running"
		exit 0
	fi
fi

if [ ${is_process_running} -eq 1 ]
then
	echo "CloudBench ${CB_STORE_TYPE} store started successfully"
	exit 0
else
	echo "CloudBench ${CB_STORE_TYPE} store did not start successfully"
	exit 1
fi
