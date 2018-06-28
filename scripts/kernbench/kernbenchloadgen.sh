#!/usr/bin/env bash

KERNBENCH_PATH=$1
KERNBENCH_DATA_DIR=$2
NRJOBS=$2

cd ${KERNBENCH_DATA_DIR}/linux
${KERNBENCH_PATH}/ltp/utils/benchmark/kernbench-0.42/kernbench -n 1 -H -M $NRJOBS
mv kernbench.log ${KERNBENCH_PATH}
