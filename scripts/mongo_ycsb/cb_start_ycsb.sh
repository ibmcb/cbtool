#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2009 Standard Performance Evaluation Corporation (SPEC)
#               All rights reserved.
#
# This source code is provided as is, without any express or implied warranty.
#
#/*******************************************************************************

#
#
#exit 1;

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

mongo=`get_ips_from_role mongodb`
if [ -z $mongo ] ; then
	syslog_netcat "mongo IP is null"
	exit 1;
fi

mongos=`get_ips_from_role mongos`
if [ -z $mongos ] ; then
	syslog_netcat "mongos IP is null"
	exit 1;
fi

mongocfg=`get_ips_from_role mongo_cfg_server`
if [ -z $mongocfg ] ; then
	syslog_netcat "mongocfg IP is null"
	exit 1;
fi

# Increase thread count
# sudo sed -i 's/threadcount=.*$/threadcount=1000/g' /root/YCSB/1instance.dat
# Increasea the fieldlength (default=100)
# sudo sh -c "echo fieldlength=1000 >> /root/YCSB/1instance.dat"

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

	# Check for New Shard

done < <(sudo /root/YCSB/bin/ycsb run mongodb -s -P /root/YCSB/workloads/workloadc -P /root/YCSB/1instance.dat 2>&1 | tee YCSB-CBTOOL-RUN)

~/cb_report_app_metrics.py throughput:$(expr $ops):tps latency:$(expr $latency):ms

if [ $? -gt 0 ] ; then
	syslog_netcat "problem running ycsb prime client on $(hostname)"
	exit 1
fi
