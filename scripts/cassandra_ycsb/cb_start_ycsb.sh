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

cd ~
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

#----------------------- Track all YCSB results  -------------------------------

#----------------------- Total op/sec ------------------------------------------
ops=0

#----------------------- Current op/sec for this client ------------------------
write_current_ops=0
read_current_ops=0
update_current_ops=0

#----------------------- Tracking Latency --------------------------------------
# <operation>_latency=average,min,max,95,99
#-------------------------------------------------------------------------------
write_latency=0
read_latency=0
update_latency=0

#----------------------- Old tracking ------------------------------------------
latency=0
#syslog_netcat "Current LOAD_LEVEL: ${LOAD_LEVEL}"
#sudo sed -i "s/operationcount=.*$/operationcount=${LOAD_LEVEL}/g" /root/YCSB/custom_workload.dat 
syslog_netcat "YCSB Workload starting...."
while read line ; do
#-------------------------------------------------------------------------------
# Need to track each YCSB Clients current operation count.
# NEED TO:
#       Create a variable that reports to CBTool the current operation
#-------------------------------------------------------------------------------
        if [[ "$line" ~= "[0-9]+\s sec:" ]] ; then
          CURRENT_OPS=$(echo $line | awk '{print $3}')
        fi

	IFS=',' read -a array <<< "$line"
	if [[ ${array[0]} == *OVERALL* ]] ; then
		if [[ ${array[1]} == *Throughput* ]] ; then
			ops=${array[2]}
		fi
	fi
#----------------------- Track Latency -----------------------------------------
        if [[ ${array[0]} == *UPDATE* ]] ; then
                if [[ ${array[1]} == *AverageLatency* ]] ; then
                        update_avg_latency=${array[2]}
                fi
                if [[ ${array[1]} == *MinLatency* ]] ; then
                        update_min_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *MaxLatency* ]] ; then
                        update_max_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *95thPercent* ]] ; then
                        update_95_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *99thPercent* ]] ; then
                        update_99_latency="${array[2]}"
                fi
        fi
        if [[ ${array[0]} == *READ* ]] ; then
                if [[ ${array[1]} == *AverageLatency* ]] ; then
                        read_avg_latency=${array[2]}
                fi
                if [[ ${array[1]} == *MinLatency* ]] ; then
                        read_min_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *MaxLatency* ]] ; then
                        read_max_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *95thPercent* ]] ; then
                        read_95_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *99thPercent* ]] ; then
                        read_99_latency="${array[2]}"
                fi
        fi
        if [[ ${array[0]} == *WRITE* ]] ; then
                if [[ ${array[1]} == *AverageLatency* ]] ; then
                        write_avg_latency=${array[2]}
                fi
                if [[ ${array[1]} == *MinLatency* ]] ; then
                        write_min_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *MaxLatency* ]] ; then
                        write_max_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *95thPercent* ]] ; then
                        write_95_latency="${array[2]}"
                fi
                if [[ ${array[1]} == *99thPercent* ]] ; then
                        write_99_latency="${array[2]}"
                fi
        fi
done < <(sudo /root/YCSB/bin/ycsb run cassandra-10 -s -P /root/YCSB/workloads/workloada -P /root/YCSB/custom_workload.dat -p hosts="$seed" 2>&1 )

if [[ $write_avg_latency -ne 0 ]] ; then
 ~/cb_report_app_metrics.py throughput:$(expr $ops):tps \
 write_avg_latency:$(expr $write_avg_latency):us \
 write_min_latency:$(expr $write_min_latency):us \
 write_max_latency:$(expr $write_max_latency):us \
 write_95_latency:$(expr $write_95_latency):us \
 write_99_latency:$(expr $write_99_latency):us \
 read_avg_latency:$(expr $read_avg_latency):us \
 read_min_latency:$(expr $read_min_latency):us \
 read_max_latency:$(expr $read_max_latency):us \
 read_95_latency:$(expr $read_95_latency):us \
 read_99_latency:$(expr $read_99_latency):us \
 update_avg_latency:$(expr $update_avg_latency):us \
 update_min_latency:$(expr $update_min_latency):us \
 update_max_latency:$(expr $update_max_latency):us \
 update_95_latency:$(expr $update_95_latency):us \
 update_99_latency:$(expr $update_99_latency):us
fi
if [[ $write_avg_latency -eq 0 ]] ; then
 ~/cb_report_app_metrics.py throughput:$(expr $ops):tps read_avg_latency:$(expr $read_avg_latency):us\
 read_min_latency:$(expr $read_min_latency):us\
 read_max_latency:$(expr $read_max_latency):us\
 read_95_latency:$(expr $read_95_latency):us\
 read_99_latency:$(expr $read_99_latency):us\
 update_avg_latency:$(expr $update_avg_latency):us\
 update_min_latency:$(expr $update_min_latency):us\
 update_max_latency:$(expr $update_max_latency):us\
 update_95_latency:$(expr $update_95_latency):us\
 update_99_latency:$(expr $update_99_latency):us
fi

if [ $? -gt 0 ] ; then
	syslog_netcat "problem running ycsb prime client on $(hostname)"
	exit 1
fi
