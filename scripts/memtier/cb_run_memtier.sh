#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

cd ~

CBUSERLOGIN=`get_my_ai_attribute login`
LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
RATIO=$(get_my_ai_attribute_with_default ratio 5:10)
PIPELINE=$(get_my_ai_attribute_with_default pipeline 1)
CLIENTS_PER_THREAD=$(get_my_ai_attribute_with_default clients_per_thread 10)

CMDLINE="memtier_benchmark  -s ${LOAD_GENERATOR_TARGET_IP} -c ${CLIENTS_PER_THREAD} -t ${LOAD_LEVEL} --ratio ${RATIO} --pipeline ${PIPELINE} --test-time ${LOAD_DURATION} --hide-histogram"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

lat=$(cat ${RUN_OUTPUT_FILE} | grep Totals | awk '{ print $5 }')
tp=$(cat ${RUN_OUTPUT_FILE} | grep Totals | awk '{ print $2 }')
bw=$(cat ${RUN_OUTPUT_FILE} | grep Totals | awk '{ print $6 }')

~/cb_report_app_metrics.py \
throughput:$tp:tps \
latency:$lat:sec \
bandwidth:$tp:KBps \
$(common_metrics)

unset_load_gen

exit 0