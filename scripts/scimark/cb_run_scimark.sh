#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh
SCIMARK_HOME=`get_my_ai_attribute_with_default scimark_home "~"`

set_load_gen $@

set_java_home

cd ${SCIMARK_HOME}

SCIMARK_DIR="${SCIMARK_HOME}/jnt"
eval SCIMARK_DIR=${SCIMARK_DIR}

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${SCIMARK_DIR}

if [[ $LOAD_LEVEL -eq 1 ]]
then
	DATASIZE=""
else
	DATASIZE="-large"
fi

CMDLINE="java jnt.scimark2.commandline ${DATASIZE}"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat ${RUN_OUTPUT_FILE} | grep Composite | awk '{ print $3 }')
fft_tp=$(cat ${RUN_OUTPUT_FILE} | grep FFT | awk '{ print $3 }')
sor_tp=$(cat ${RUN_OUTPUT_FILE} | grep SOR | awk '{ print $3 }')
mc_tp=$(cat ${RUN_OUTPUT_FILE} | grep Monte | awk '{ print $4 }')
mm_tp=$(cat ${RUN_OUTPUT_FILE} | grep Sparse | awk '{ print $5 }')
lu_tp=$(cat ${RUN_OUTPUT_FILE} | grep LU | awk '{ print $3 }')

~/cb_report_app_metrics.py \
throughput:${tp}:mflops \
fft_throughput:${fft_tp}:mflops \
sor_throughput:${sor_tp}:mflops \
mc_throughput:${mc_tp}:mflops \
mm_throughput:${mm_tp}:mflops \
lu_throughput:${lu_tp}:mflops \
$(common_metrics)

unset_load_gen

exit 0
