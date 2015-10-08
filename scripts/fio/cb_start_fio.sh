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

if [[ ${WAIT_FOR} == 0 ]]
then 

  syslog_netcat "Waiting for signal"

else
 WRITE_OUTPUT=$(fio randwrite.fiojob --minimal > fio.run; rm -rf randwrites.1.0; ./fiostats.sh fio.run)
 WIOPS=$(echo $WRITE_OUTPUT | awk '{print $2}')
 WLATENCY=$(echo $WRITE_OUTPUT | awk '{print $3}')

 READ_OUTPUT=$(fio randread.fiojob --minimal > fio.run; rm -rf randreads.1.0; ./fiostats.sh fio.run)
 RIOPS=$(echo $READ_OUTPUT | awk '{print $2}')
 RLATENCY=$(echo $READ_OUTPUT | awk '{print $3}')

 ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
 load_level:${LOAD_LEVEL}:load \
 load_profile:${LOAD_PROFILE}:name \
 load_duration:${LOAD_DURATION}:sec \
 write_max:$WIOPS:tps \
 write_latency:$WLATENCY:ms \
 read_max:$RIOPS:tps \
 read_latency:$RLATENCY:ms \
 ${SLA_RUNTIME_TARGETS}
fi

exit 0
