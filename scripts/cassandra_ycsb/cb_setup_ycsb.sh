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

source ~/.bashrc
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
        source $dir/cb_common.sh
else
        source $dir/../common/cb_common.sh
fi

if [ $standalone == online ] ; then
    # retrieve online values from API
    #LOAD_PROFILE=$1
    LOAD_LEVEL=$2
    #LOAD_DURATION=$3
    LOAD_ID=$4
fi

seed=`get_ips_from_role seed`

# Update workload A to have the 70/30 mix.
sudo sed -i 's/^readproportion=.*$/readproportion=0\.7/g' /root/YCSB/workloads/workloada
sudo sed -i 's/^updateproportion=.*$/updateproportion=0\.3/g' /root/YCSB/workloads/workloada

# Determine memory size
MEM=`cat /proc/meminfo | grep MemTotal: | awk '{print $2}'`
RECORDS=$(python -c 'from __future__ import division; print ((('"${MEM}"'/1024)/1024)*10)*1000000')
syslog_netcat "Number of records to be inserted : $RECORDS million"

# Update the Record Count new dat file
sudo touch /root/YCSB/custom_workload.dat
sudo sh -c "echo "recordcount=${RECORDS%.*}" > /root/YCSB/custom_workload.dat"
sudo sh -c "echo "operationcount=10000000" >> /root/YCSB/custom_workload.dat"
# Need to determine # of threads to start with in the baseload.

# Load the Database
start_time=$(date)
syslog_netcat "Start of YCSB Loading: $start_time"
sudo /root/YCSB/bin/ycsb load cassandra-10 -s -P /root/YCSB/workloads/workloada -P /root/YCSB/custom_workload.dat -p hosts="$seed" 2>&1 | tee YCSB-CBTOOL-RUN
end_time=$(date)
syslog_netcat "End of YCSB Loading: $end_time"

if [ $? -gt 0 ] ; then
	syslog_netcat "problem running ycsb prime client on $(hostname)"
	exit 1
fi
provision_application_stop $START
