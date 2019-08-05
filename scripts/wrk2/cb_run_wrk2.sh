#!/usr/bin/env bash
#/*******************************************************************************
# Copyright (c) 2019 DigitalOcean

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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

cd ~

WRK2_DIR="~/wrk2"
eval WRK2_DIR=${WRK2_DIR}

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${WRK2_DIR}

LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
CONNECTIONS=$(get_my_ai_attribute_with_default connections 400)
PROTOCOL=$(get_my_ai_attribute_with_default protocol http)
RESPONSESIZE=$(get_my_ai_attribute_with_default responsesize 0)
RESPONSEDELAY=$(get_my_ai_attribute_with_default responsedelay 0)
THREADS=$(get_my_ai_attribute_with_default threads auto)


if [ x"$THREADS" == x"auto" ] ; then
	NR_CPUS=`cat /proc/cpuinfo | grep processor | wc -l`
	syslog_netcat "Setting threads = ${NR_CPUS}"
	THREADS=${NR_CPUS}
fi

cd $WRK2_DIR

CMDLINE="./wrk -t${THREADS} -d${LOAD_DURATION} -c${CONNECTIONS} -R ${LOAD_LEVEL} -H 'sleep: ${RESPONSEDELAY}' -H 'size: ${RESPONSESIZE}' ${PROTOCOL}://${LOAD_GENERATOR_TARGET_IP}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

cd ~

lat=$(cat ${RUN_OUTPUT_FILE} | grep Latency | awk '{ print $2 }')
tp=$(cat ${RUN_OUTPUT_FILE} | grep Req/Sec | awk '{ print $2 }')
tptotal=$(cat ${RUN_OUTPUT_FILE} | grep Requests/sec | awk '{ print $2 }')
connecterrors=$(cat ${RUN_OUTPUT_FILE} | grep "errors" | awk '{ print $4 }' | grep -oE "[0-9]+")
readerrors=$(cat ${RUN_OUTPUT_FILE} | grep "errors" | awk '{ print $6 }' | grep -oE "[0-9]+")
writeerrors=$(cat ${RUN_OUTPUT_FILE} | grep "errors" | awk '{ print $8 }' | grep -oE "[0-9]+")
timeouts=$(cat ${RUN_OUTPUT_FILE} | grep "errors" | awk '{ print $10 }' | grep -oE "[0-9]+")

~/cb_report_app_metrics.py \
$(format_for_report latency $lat) \
$(format_for_report throughput $tp) \
$(format_for_report throughput_total $tptotal) \
$(format_for_report connecterrors $connecterrors) \
$(format_for_report readerrors $readerrors) \
$(format_for_report writeerrors $writeerrors) \
$(format_for_report timeouts $timeouts) \
$(common_metrics)

unset_load_gen

exit 0
