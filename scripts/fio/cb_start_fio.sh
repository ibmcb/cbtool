#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_fio_common.sh

LOAD_PROFILE=$1
LOAD_LEVEL=$2
LOAD_DURATION=$3
LOAD_ID=$4
SLA_RUNTIME_TARGETS=$5 

if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
then
    syslog_netcat "Usage: cb_start_fio.sh <load_profile> <load level> <load duration> <load_id>"
    exit 1
fi

FIOIP=`get_ips_from_role fio`

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

cat ~/randwrite.fiojob.template > ~/randwrite.fiojob
cat ~/randread.fiojob.template > ~/randread.fiojob

sed -i "s^FIO_DATA_DIR^$FIO_DATA_DIR^g" ~/*.fiojob
sed -i "s/FIO_ENGINE/$FIO_ENGINE/g" ~/*.fiojob
sed -i "s/FIO_BS/$FIO_BS/g" ~/*.fiojob
sed -i "s/FIO_DIRECT/$FIO_DIRECT/g" ~/*.fiojob
sed -i "s/FIO_FILE_SIZE/$FIO_FILE_SIZE/g" ~/*.fiojob
sed -i "s/FIO_RATE_IOPS/$FIO_RATE_IOPS/g" ~/*.fiojob
sed -i "s/LOAD_LEVEL/$LOAD_LEVEL/g" ~/*.fiojob

sudo rm -rf $FIO_DATA_DIR/*

update_app_errors 0 reset

#If more than one command is needed (e.g., connected by "&&" or ";", please dump it on script, instead of just assigining to the variable CMDLINE"
echo "fio randwrite.fiojob --minimal --output fiorandwrite.run && fio randread.fiojob --minimal --output fiorandread.run" > fioloadgen.sh
CMDLINE="bash fioloadgen.sh"

syslog_netcat "Benchmarking filebench SUT: FIO=${FIOIP} with LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID} and LOAD_PROFILE=${LOAD_PROFILE})"

OUTPUT_FILE=$(mktemp)

execute_load_generator "${CMDLINE}" ${OUTPUT_FILE} ${LOAD_DURATION}

WRITE_OUTPUT=$(./fiostats.sh fiorandwrite.run)
WIOPS=$(echo $WRITE_OUTPUT | awk '{print $2}')
WLATENCY=$(echo $WRITE_OUTPUT | awk '{print $3}')

READ_OUTPUT=$(./fiostats.sh fiorandread.run)
RIOPS=$(echo $READ_OUTPUT | awk '{print $2}')
RLATENCY=$(echo $READ_OUTPUT | awk '{print $3}')

LATENCY=$(echo "scale=2; ($WLATENCY + $RLATENCY)/2" | bc -l)
TPUT=$(echo "scale=2; ($WIOPS + $RIOPS)/2" | bc -l)

~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
load_level:${LOAD_LEVEL}:load \
load_profile:${LOAD_PROFILE}:name \
load_duration:${LOAD_DURATION}:sec \
write_throughput:$WIOPS:tps \
write_latency:$WLATENCY:ms \
read_throughput:$RIOPS:tps \
read_latency:$RLATENCY:ms \
latency:$LATENCY:ms \
throughput:$TPUT:tps \
errors:$(update_app_errors):num \
completion_time:$(update_app_completiontime):sec \
quiescent_time:$(update_app_quiescent):sec \
${SLA_RUNTIME_TARGETS}

exit 0
