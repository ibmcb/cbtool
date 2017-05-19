#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2016 DigitalOcean, Inc.

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

BTEST_EXECUTABLE=$(which btest)
if [[ $? -ne 0 ]]
then
    BTEST_EXECUTABLE=${dir}/cbtool/3rd_party/btest/btest
fi

BTEST_DATA_DIR=$(get_my_ai_attribute_with_default btest_data_dir ~/btestfile)        

# TODO:
# 1. Support -X trim flag on SSD-backed volumes
# 2. Issue sudo fstrim /

if [[ $LOAD_PROFILE == "default" ]]
then
    LOAD_PROFILE="4096;32;50;100;500"
fi
    
threads=$LOAD_LEVEL
block=$(echo $LOAD_PROFILE | cut -d ";" -f 1)
queuedepth=$(echo $LOAD_PROFILE | cut -d ";" -f 2)
read_percent=$(echo $LOAD_PROFILE | cut -d ";" -f 3)
random_percent=$(echo $LOAD_PROFILE | cut -d ";" -f 4)
sizemb=$(echo $LOAD_PROFILE | cut -d ";" -f 5)

sudo rm -f $BTEST_DATA_DIR/btestfile;

# This has no effect if # ./install -r workload -w btest # is done properly
# No effect if libaio is installed properly via ./install
if [ x"$(ldconfig -p | grep libaio)" == x ] ; then
    export LD_PRELOAD=${dir}/libaio.so.1.0.1
fi

CMDLINE="sudo $BTEST_EXECUTABLE -F -T $threads -b $block -D -l ${sizemb}m -w $queuedepth -t $LOAD_DURATION -F $random_percent $read_percent $BTEST_DATA_DIR/btestfile"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

sudo rm -f $BTEST_DATA_DIR/btestfile;

tp=`grep "Total:" ${RUN_OUTPUT_FILE} | grep -v ms | cut -d " " -f 4`
lat=`grep "Total:" ${RUN_OUTPUT_FILE} | grep -v ms | cut -d " " -f 8`

~/cb_report_app_metrics.py \
throughput:${tp}:tps \
latency:${lat}:msec \
$(common_metrics)    
    
unset_load_gen

exit 0
