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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@
   
STRESS_RAM_PERCENTAGE=`get_my_ai_attribute_with_default stress_ram_percentage 0`

--vm X --vm-keep

CMDLINE="stress-ng --metrics-brief --perf -t ${LOAD_DURATION}"
if [ ${STRESS_RAM_PERCENTAGE} != 0 ] ; then
	# Set the stress memory size to be a percentage of main memory
	check_container
	if [ ${IS_CONTAINER} -eq 1 ] && [ `get_my_vm_attribute model` == "pdm" ] ; then
		size=`get_my_vm_attribute size`
		syslog_netcat "stress is running on bare metal, will use a container size of: ${size}"
		mb_total=$(echo $size | cut -d "-" -f 2)
		mb=$(echo "${mb_total} * ${STRESS_RAM_PERCENTAGE} / 100" | bc)
	else
		syslog_netcat "stress is running in a VM."
		# We are in a VM
		kb=$(cat /proc/meminfo  | sed -e "s/ \+/ /g" | grep MemTotal | cut -d " " -f 2)
		mb=$(echo "$kb / 1024 * ${STRESS_RAM_PERCENTAGE} / 100" | bc)
	fi

	syslog_netcat "Calculated memory size: ${mb} MB"

	# Stress automatically splits up the bytes across all the VM workers equally
	CMDLINE="$CMDLINE --vm ${LOAD_LEVEL} --vm-bytes ${mb}M --vm-keep"
else
	CMDLINE="$CMDLINE --cpu ${LOAD_LEVEL} --cpu-method ${LOAD_PROFILE}"
fi

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat ${RUN_OUTPUT_FILE} | grep cpu[[:space:]] | awk '{ print $10 }')

~/cb_report_app_metrics.py \
throughput:$tp:tps \
$(common_metrics)    

unset_load_gen

exit 0
