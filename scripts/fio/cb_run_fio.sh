#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

FIOIP=`get_ips_from_role fio`

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

FIO_DATA_DIR=$(get_my_ai_attribute_with_default fio_data_dir /fiotest)
FIO_DATA_FSTYP=$(get_my_ai_attribute_with_default fio_data_fstyp ext4)
FIO_DATA_VOLUME=$(get_my_ai_attribute_with_default fio_data_volume NONE)

FIO_ENGINE=$(get_my_ai_attribute_with_default fio_engine sync)
FIO_BS=$(get_my_ai_attribute_with_default fio_bs 64k) 
FIO_DIRECT=$(get_my_ai_attribute_with_default fio_direct 1)
FIO_FILE_SIZE=$(get_my_ai_attribute_with_default fio_file_size 1g)
FIO_RATE_IOPS=$(get_my_ai_attribute_with_default fio_rate_iops 100) 

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

#If more than one command is needed (e.g., connected by "&&" or ";", please dump it on script, instead of just assigining to the variable CMDLINE"
echo "#!/usr/bin/env bash" > fioloadgen.sh
echo "fio randwrite.fiojob --minimal --output fiorandwrite.run && fio randread.fiojob --minimal --output fiorandread.run" >> fioloadgen.sh
sudo chmod 755 ./fioloadgen.sh
CMDLINE="sudo ./fioloadgen.sh"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

WRITE_OUTPUT=$(./fiostats.sh fiorandwrite.run)
WIOPS=$(echo $WRITE_OUTPUT | awk '{print $2}')
WLATENCY=$(echo $WRITE_OUTPUT | awk '{print $3}')

READ_OUTPUT=$(./fiostats.sh fiorandread.run)
RIOPS=$(echo $READ_OUTPUT | awk '{print $2}')
RLATENCY=$(echo $READ_OUTPUT | awk '{print $3}')

LATENCY=$(echo "scale=2; ($WLATENCY + $RLATENCY)/2" | bc -l)
TPUT=$(echo "scale=2; ($WIOPS + $RIOPS)/2" | bc -l)

~/cb_report_app_metrics.py \
write_throughput:$WIOPS:tps \
write_latency:$WLATENCY:ms \
read_throughput:$RIOPS:tps \
read_latency:$RLATENCY:ms \
latency:$LATENCY:ms \
throughput:$TPUT:tps \
$(common_metrics)    

unset_load_gen

exit 0
