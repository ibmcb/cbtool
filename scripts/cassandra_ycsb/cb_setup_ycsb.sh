#!/usr/bin/env bash

#/*******************************************************************************
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
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

standalone=`online_or_offline "$4"`

<<<<<<< HEAD
START=`provision_application_start`

provision_application_stop $START
exit 0
=======
if [ $standalone == online ] ; then
    # retrieve online values from API
    LOAD_LEVEL=$1
    LOAD_ID=$2
    OPERATION_COUNT=`get_my_ai_attribute OPERATION_COUNT`
    READ_RATIO=`get_my_ai_attribute READ_RATIO`
    UPDATE_RATIO=`get_my_ai_attribute UPDATE_RATIO`
    YCSB_PATH=`get_my_ai_attribute YCSB_PATH`
    INPUT_RECORDS=`get_my_ai_attribute INPUT_RECORDS`
fi

syslog_netcat "INPUT_RECORDS: $INPUT_RECORDS"
syslog_netcat "YCSB: $YCSB_PATH"
syslog_netcat "READ_RATIO: $READ_RATIO"

seed=`get_ips_from_role seed`

sudo sed -i "s/^readproportion=.*$/readproportion=0\.$READ_RATIO/g" $YCSB_PATH/workloads/workloada
sudo sed -i "s/^updateproportion=.*$/updateproportion=0\.$UPDATE_RATIO/g" $YCSB_PATH/workloads/workloada

# Determine memory size
MEM=`cat /proc/meminfo | grep MemTotal: | awk '{print $2}'`
RECORDS=$(python -c 'from __future__ import division; print ((('"${MEM}"'/1024)/1024)*10)*1000000')
if [ $INPUT_RECORDS -ne 0 ]; then
 RECORDS=$INPUT_RECORDS
fi
syslog_netcat "Number of records to be inserted : $RECORDS"

# Update the Record Count new dat file
sudo touch $YCSB_PATH/custom_workload.dat
sudo sh -c "echo "recordcount=${RECORDS%.*}" > $YCSB_PATH/custom_workload.dat"
sudo sh -c "echo "operationcount=$OPERATION_COUNT" >> $YCSB_PATH/custom_workload.dat"
# Need to determine # of threads to start with in the baseload.

# Load the Database
start_time=$(date)
syslog_netcat "Start of YCSB Loading: $start_time"
sudo $YCSB_PATH/bin/ycsb load cassandra-10 -s -P $YCSB_PATH/workloads/workloada -P $YCSB_PATH/custom_workload.dat -p hosts="$seed" 2>&1 | tee YCSB-CBTOOL-RUN
end_time=$(date)
syslog_netcat "End of YCSB Loading: $end_time"

exit 0
>>>>>>> 70caec64b1b3a59e00c46ddac1fdcf88dc6142ca
