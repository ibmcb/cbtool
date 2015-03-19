#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5
WAIT_FOR=`get_my_ai_attribute_with_default wait_for 0`

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

LINPACK='./linpack/benchmarks/linpack/xlinpack_xeon64'
LINPACK_DAT='./linpack.dat'
NUM_CPU=`cat /proc/cpuinfo | grep processor | wc -l`
export OMP_NUM_THREADS=$NUM_CPU
echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
echo "1 # number of tests" >> ${LINPACK_DAT}
#echo "10514 # problem sizes" >> ${LINPACK_DAT}
echo "5000 # problem sizes" >> ${LINPACK_DAT}
echo "20016 # leading dimensions" >> ${LINPACK_DAT}
echo "2 # times to run a test " >> ${LINPACK_DAT}
echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}

if [ ${WAIT_FOR} == 0 ] ; then 
  syslog_netcat "Waiting for singal"
else
 OUTPUT=$(${LINPACK} < ${LINPACK_DAT} | grep -A 1 Average | grep 20016)
 AVERAGE=$(echo $OUTPUT | awk '{print $4}')
 MAX=$(echo $OUTPUT | awk '{print $5}')

 ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
 load_level:${LOAD_LEVEL}:load \
 load_profile:${LOAD_PROFILE}:name \
 load_duration:${LOAD_DURATION}:sec \
 throughput_max:$MAX:tps \
 throughput_average:$AVERAGE:tps \
 ${SLA_RUNTIME_TARGETS}
fi

exit 0
