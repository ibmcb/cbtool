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

LOGIN=`get_my_ai_attribute login`
LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor "10000"`

SPECJBB_IP=`get_ips_from_role specjbb`

SPEC_PATH=~/SPECjbb2015_1_00
eval SPEC_PATH=${SPEC_PATH}

sudo chmod 755 $SPEC_PATH
sudo chmod 755 $SPEC_PATH/*.sh

sudo ls -la $SPEC_PATH/config/specjbb2015.props.orig 2>&1 > /dev/null
if [[ $? -ne 0 ]]
then
    sudo cp -f $SPEC_PATH/config/specjbb2015.props $SPEC_PATH/config/specjbb2015.props.orig 
fi

sudo cp -f $SPEC_PATH/config/specjbb2015.props.orig $SPEC_PATH/config/specjbb2015.props

if [[ ${LOAD_PROFILE} == "preset" ]]
then
    EFFECTIVE_IR=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
    EFFECTIVE_DUR=$((${LOAD_DURATION}*1000))
    sudo sed -i "s/#specjbb.controller.type=.*/specjbb.controller.type=PRESET/g" $SPEC_PATH/config/specjbb2015.props
    sudo sed -i "s/#specjbb.controller.preset.ir=.*/specjbb.controller.preset.ir=${EFFECTIVE_IR}/g" $SPEC_PATH/config/specjbb2015.props
    sudo sed -i "s/#specjbb.controller.preset.duration=.*/specjbb.controller.preset.duration=${EFFECTIVE_DUR}/g" $SPEC_PATH/config/specjbb2015.props
fi

if [[ ${LOAD_PROFILE} == "hbir" ]]
then
    sudo sed -i 's/#specjbb.controller.type=.*/specjbb.controller.type=HBIR/g' $SPEC_PATH/config/specjbb2015.props
fi

CMDLINE="java ${JAVA_EXTRA_CMD_OPTS} -jar specjbb2015.jar -m composite -ikv"

cd $SPEC_PATH

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

rm -rf result/*
rm -rf specjbb2015*.data.gz

cd ~

if [[ ${LOAD_PROFILE} == "hbir" ]]
then
    tp=$(cat $RUN_OUTPUT_FILE | grep settled | awk '{ print $11 }' | sed 's/,//g')
fi
    
if [[ ${LOAD_PROFILE} == "preset" ]]
then
    tp=$(cat $RUN_OUTPUT_FILE | grep reqs | grep "IR = ${EFFECTIVE_IR}" | tail -1 | awk '{ print $19 }')    
fi

~/cb_report_app_metrics.py \
throughput:$tp:tps \
$(common_metrics)

unset_load_gen

exit 0