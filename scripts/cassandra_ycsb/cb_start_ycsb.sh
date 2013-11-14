#!/usr/bin/env bash

#/*******************************************************************************
# This source code is provided as is, without any express or implied warranty.
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************
#
#

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
    LOAD_PROFILE=$1
    LOAD_LEVEL=$2
    LOAD_DURATION=$3
    LOAD_ID=$4
fi

seed=`get_ips_from_role seed`

ops=0
latency=0
syslog_netcat "YCSB Workload starting...."

while read line ; do
	IFS=',' read -a array <<< "$line"
	if [[ ${array[0]} == *OVERALL* ]] ; then
		if [[ ${array[1]} == *Throughput* ]] ; then
			ops=${array[2]}
		fi
	fi
	if [[ ${array[0]} == *UPDATE* ]] ; then
		if [[ ${array[1]} == *AverageLatency* ]] ; then
			latency=${array[2]}
		fi
	fi
	if [[ ${array[0]} == *READ* ]] ; then
		if [[ ${array[1]} == *AverageLatency* ]] ; then
			latency=${array[2]}
		fi
	fi

done < <(sudo /root/YCSB/bin/ycsb run cassandra-10 -s -P /root/YCSB/workloads/workloadc -P /root/YCSB/1instance.dat -p hosts="$seed" 2>&1 )

~/cb_report_app_metrics.py throughput:$(expr $ops):tps latency:$(expr $latency):ms

if [ $? -gt 0 ] ; then
	syslog_netcat "problem running ycsb prime client on $(hostname)"
	exit 1
fi
