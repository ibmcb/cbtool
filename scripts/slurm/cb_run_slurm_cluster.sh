#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

cd ~

CMDLINE="sleep 600"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat ${RUN_OUTPUT_FILE} | grep QPS | awk '{ print $2 }')
lat=$(cat ${RUN_OUTPUT_FILE} | grep avg | sed 's/avg: //g' | tr -d ' ')
lat_95=$( cat ${RUN_OUTPUT_FILE} | grep 95p | sed 's/95p: //g' | tr -d ' ')

~/cb_report_app_metrics.py \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
throughput:$tp:tps \
$(format_for_report latency $lat) \
$(format_for_report 95_latency $lat_95) \
$(common_metrics)
 
unset_load_gen

exit 0