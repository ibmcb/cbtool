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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

set_java_home

export RAMPUP_TIME=`get_my_ai_attribute_with_default specjbb_rampup 20`
export LOGIN=`get_my_ai_attribute login`

SPECJBB_IP=`get_ips_from_role specjbb`

#####################################################
# set up spec configuration and adjust to 
# reflect the parameters passed
#####################################################
SPEC_PATH=~/SPECjbb2015_1_00
eval SPEC_PATH=${SPEC_PATH}

STARTING_WAREHOUSES=$(echo "2 + ${LOAD_LEVEL}/2" | bc)
ENDING_WAREHOUSES=$(echo "3 + ${LOAD_LEVEL}" | bc)

#sudo cp -f ~/SPECjbb.props.template ${SPEC_PATH}/config/SPECjbb2015.props
#sudo sed -i s/"ENDING_WAREHOUSES"/"${ENDING_WAREHOUSES}"/g ${SPEC_PATH}/config/SPECjbb2015.props
#sudo sed -i s/"STARTING_WAREHOUSES"/"${STARTING_WAREHOUSES}"/g ${SPEC_PATH}/config/SPECjbb2015.props
#sudo sed -i s/"LOAD_DURATION_TMPLT"/"${LOAD_DURATION}"/g ${SPEC_PATH}/config/SPECjbb2015.props
#sudo sed -i s/"RAMPUP_TIME_TMPLT"/"${RAMPUP_TIME}"/g ${SPEC_PATH}/config/SPECjbb2015.props
syslog_netcat "Updating properties file SPECjbb.props with the following parameters starting_number_warehouses:${STARTING_WAREHOUSES},ending_number_warehouses:${ENDING_WAREHOUSES},measurement:${LOAD_DURATION},rampup:${RAMPUP_TIME}"

sudo chmod 755 $SPEC_PATH
sudo chmod 755 $SPEC_PATH/*.sh

sudo ls -la $SPEC_PATH/config/specjbb2015.props.orig 2>&1 > /dev/null
if [[ $? -ne 0 ]]
then
    sudo cp -f $SPEC_PATH/config/specjbb2015.props $SPEC_PATH/config/specjbb2015.props.orig 
fi

sudo cp -f $SPEC_PATH/config/specjbb2015.props.orig $SPEC_PATH/config/specjbb2015.props
        
sudo sed -i 's/#specjbb.controller.type=HBIR_RT/specjbb.controller.type=PRESET/g' $SPEC_PATH/config/specjbb2015.props
sudo sed -i 's/#specjbb.controller.preset.ir=1000/specjbb.controller.preset.ir=1000/g' $SPEC_PATH/config/specjbb2015.props
sudo sed -i 's/#specjbb.controller.preset.duration=600000/specjbb.controller.preset.duration=60000/g' $SPEC_PATH/config/specjbb2015.props

CMDLINE="java ${JAVA_EXTRA_CMD_OPTS} -jar specjbb2015.jar -m composite"

cd $SPEC_PATH

echo $CMDLINE

exit 0

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

cd ~

#####################################################
# extract and publish result
#####################################################
RESULTS_FILE=`cat $RUN_OUTPUT_FILE | grep Opened | grep raw | cut -d " " -f 2 | tr -d " "`

if [[ x"${RESULTS_FILE}" == x ]]
then
    syslog_netcat "An error prevented the production of the output file. Unable to collect and report results"
else
    syslog_netcat "SPECjbb benchmark run complete. Will collect and report the results. Output file name is ${RESULTS_FILE}"

    app_metric_string=""
    THROUGHPUT=`cat ${RESULTS_FILE} | grep score | tail -1 | cut -d "=" -f 2 | tr -d " "`

    app_metric_string+=" throughput:"${THROUGHPUT}":tps"    

    for TYPE in new_order payment order_status delivery stock_level cust_report
    do
        X=`cat ${RESULTS_FILE} | grep ${TYPE} | grep averagetime | tail -1 | cut -d "=" -f 2 | tr -d " "`
        RESPONSE_TIME=`echo ${X} | awk -F"E" 'BEGIN{OFMT="%10.10f"} {print $1 * (10 ^ $2) * 1000}'`
        if [[ ${TYPE} == "new_order" ]]
        then
            app_metric_string+=" latency:"${RESPONSE_TIME}":msec"
        fi
        app_metric_string+=" latency_${TYPE}:"${RESPONSE_TIME}":msec"
    done

    ~/cb_report_app_metrics.py \
    ${app_metric_string} \
    $(common_metrics)

fi

unset_load_gen

exit 0
