#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2022 Akamai

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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

SPARK_RAM_PERCENTAGE=`get_my_ai_attribute_with_default spark_ram_percentage 90`
kb=$(cat /proc/meminfo  | sed -e "s/ \+/ /g" | grep MemTotal | cut -d " " -f 2)
mb=$(echo "$kb / 1024 * ${SPARK_RAM_PERCENTAGE} / 100" | bc)

SPARK_CPU_RESERVED=`get_my_ai_attribute_with_default spark_cpu_reserved 1`
if [ $SPARK_CPU_RESERVED -lt $NR_CPUS ] ; then
	AVAIL_CPUS="$((NR_CPUS-SPARK_CPU_RESERVED))"
else
	AVAIL_CPUS="$NR_CPUS"
fi

syslog_netcat "Memory limit: ${mb}MB ($SPARK_RAM_PERCENTAGE %)"
syslog_netcat "CPU limit: ${AVAIL_CPUS} / $NR_CPUS"

SPARK_EXECUTOR_CORES=`get_my_ai_attribute_with_default spark_executor_cores NA`
if [[ $SPARK_EXECUTOR_CORES == "NA" ]] ; then
	SPARK_EXECUTOR_CORES="$AVAIL_CPUS"
else
	syslog_netcat "Overriding executor CPUs to use $SPARK_EXECUTOR_CORES instead"
fi
SPARK_EXECUTOR_MEMORY=`get_my_ai_attribute_with_default spark_executor_memory NA`

if [[ $SPARK_EXECUTOR_MEMORY == "NA" ]] ; then
	SPARK_EXECUTOR_MEMORY=${mb}
else
	syslog_netcat "Overriding executor memory to use $SPARK_EXECTUOR_MEMORY MB instead"
fi

export SPARK_DRIVER_MEMORY=`get_my_ai_attribute_with_default spark_driver_memory NA`

if [[ $SPARK_DRIVER_MEMORY == "NA" ]] ; then
	SPARK_DRIVER_MEMORY=${mb}
else
	syslog_netcat "Overriding driver memory to use $SPARK_DRIVER_MEMORY MB instead"
fi

