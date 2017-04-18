#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

cd ~

WRK_DIR="~/wrk"
eval WRK_DIR=${WRK_DIR}

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${WRK_DIR}

LOAD_GENERATOR_TARGET_IP=`get_my_ai_attribute load_generator_target_ip`
CONNECTIONS=$(get_my_ai_attribute_with_default connections 400)
PROTOCOL=$(get_my_ai_attribute_with_default protocol http)
URL=$(get_my_ai_attribute_with_default url index.html)

cd $WRK_DIR

CMDLINE="./wrk -t${LOAD_LEVEL} -d${LOAD_DURATION} -c${CONNECTIONS} ${PROTOCOL}://${LOAD_GENERATOR_TARGET_IP}/${URL}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

cd ~

lat=$(cat ${RUN_OUTPUT_FILE} | grep Latency | awk '{ print $2 }')
tp=$(cat ${RUN_OUTPUT_FILE} | grep Req/Sec | awk '{ print $2 }')

~/cb_report_app_metrics.py \
$(format_for_report latency $lat) \
$(format_for_report throughput $tp) \
$(common_metrics)

unset_load_gen

exit 0
