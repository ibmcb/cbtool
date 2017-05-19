#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

MULTICHASE_DIR="~/multichase"
eval MULTICHASE_DIR=${MULTICHASE_DIR}

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${MULTICHASE_DIR}

ARRAY_SIZE=$(get_my_ai_attribute_with_default array_size 1g)
STRIDE_SIZE=$(get_my_ai_attribute_with_default stride_size 128)

cd ${MULTICHASE_DIR}

CMDLINE="./multichase -m ${ARRAY_SIZE} -s ${STRIDE_SIZE} -c ${LOAD_PROFILE} -n $((${LOAD_DURATION}*2)) -t ${LOAD_LEVEL} -a"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

cd ~

tp=$(cat ${RUN_OUTPUT_FILE})
tp=$(echo "scale=4; $tp * 2" | bc -l)

~/cb_report_app_metrics.py \
throughput:${tp}:sps \
$(common_metrics)

unset_load_gen

exit 0