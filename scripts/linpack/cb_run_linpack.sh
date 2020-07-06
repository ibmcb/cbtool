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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

LINPACK=`get_my_ai_attribute_with_default linpack ~/compilers_and_libraries_2016.0.038/linux/mkl/benchmarks/linpack/xlinpack_xeon64`
eval LINPACK=${LINPACK}

sudo ls ${LINPACK} 2>&1 > /dev/null
if [[ $? -ne 0 ]]
then
	LINPACK=$(sudo find ~ | grep xlinpack_xeon64)
fi
LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor 5000`
LINPACK_DAT='~/linpack.dat'
eval LINPACK_DAT=${LINPACK_DAT}

PROBLEM_SIZES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
LEADING_DIMENSIONS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))

LINPACK_IP=`get_ips_from_role linpack`

linux_distribution

export OMP_NUM_THREADS=$NR_CPUS
echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
echo "1 # number of tests" >> ${LINPACK_DAT}
echo "$PROBLEM_SIZES # problem sizes" >> ${LINPACK_DAT}
echo "$LEADING_DIMENSIONS # leading dimensions" >> ${LINPACK_DAT}
echo "${LOAD_DURATION} # times to run a test " >> ${LINPACK_DAT}
echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}

CMDLINE="${LINPACK} ${LINPACK_DAT}" 

execute_load_generator "$CMDLINE" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}
RESULTS=$(cat ${RUN_OUTPUT_FILE} | grep -A 1 Average | grep $PROBLEM_SIZES)
AVERAGE=$(echo $RESULTS | awk '{print $4}')
MAX=$(echo $RESULTS | awk '{print $5}')
    
~/cb_report_app_metrics.py \
throughput_max:$MAX:gflops \
throughput:$AVERAGE:gflops \
$(common_metrics)    
    
unset_load_gen

exit 0
