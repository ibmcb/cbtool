#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

FIOIP=`get_ips_from_role fio`
OUT_FILE="fio-out.json"

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

FIO_ENGINE=$(get_my_ai_attribute_with_default fio_engine sync)
FIO_RBD_POOL=$(get_my_ai_attribute_with_default fio_rbd_pool none)
FIO_RBD_NAME=$(get_my_ai_attribute_with_default fio_rbd_name none)

FIO_VERIFY=$(get_my_ai_attribute_with_default fio_verify none)
FIO_VERIFY_FATAL=$(get_my_ai_attribute_with_default fio_verify_fatal 0)

FIO_PRE_CREATE_DATA=$(get_my_ai_attribute_with_default fio_pre_create_data /dev/zero)

FIO_BS=$(get_my_ai_attribute_with_default fio_bs 64k)
FIO_DIRECT=$(get_my_ai_attribute_with_default fio_direct 1)
FIO_CREATE_ON_OPEN=$(get_my_ai_attribute_with_default fio_create_on_open 1)

# file size to test in MB
FIO_FILE_SIZE=$(get_my_ai_attribute_with_default fio_file_size 128M)

FIO_DATA_DIR=$(get_my_ai_attribute_with_default fio_data_dir /fiotest)
FIO_IODEPTH=$(get_my_ai_attribute_with_default fio_iodepth 8)
FIO_SYNC=$(get_my_ai_attribute_with_default fio_sync 0)

FIO_RWMIXREAD=$(get_my_ai_attribute_with_default fio_rwmixread 50)
FIO_RWMIXWRITE=$(get_my_ai_attribute_with_default fio_rwmixwrite 50)
FIO_RAMP_TIME=$(get_my_ai_attribute_with_default fio_ramp_time none)
FIO_INVALIDATE=$(get_my_ai_attribute_with_default fio_invalidate 1)

cat ~/cb.fiojob.template > ~/cb.fiojob

if [[ $FIO_VERIFY != "none" ]]
then
    sed -i "s^#verify=FIO_VERIFY^verify=$FIO_VERIFY^g" ~/*.fiojob
    sed -i "s^#verify_fatal=FIO_VERIFY_FATAL^verify_fatal=$FIO_VERIFY_FATAL^g" ~/*.fiojob
fi

sed -i "s^FIO_ENGINE^$FIO_ENGINE^g" ~/*.fiojob
sed -i "s^FIO_BS^$FIO_BS^g" ~/*.fiojob
sed -i "s^FIO_DIRECT^$FIO_DIRECT^g" ~/*.fiojob
sed -i "s^FIO_CREATE_ON_OPEN^$FIO_CREATE_ON_OPEN^g" ~/*.fiojob
sed -i "s^LOAD_PROFILE^$LOAD_PROFILE^g" ~/*.fiojob
sed -i "s^LOAD_LEVEL^$LOAD_LEVEL^g" ~/*.fiojob
sed -i "s^FIO_FILE_SIZE^${FIO_FILE_SIZE}^g" ~/*.fiojob
sed -i "s^FIO_INVALIDATE^${FIO_INVALIDATE}m^g" ~/*.fiojob

if [[ $(echo $FIO_DATA_DIR | tr '[:upper:]' '[:lower:]') != "none" ]]
then
    sudo mkdir -p $FIO_DATA_DIR
    FIO_FILENAME=$FIO_DATA_DIR/$LOAD_PROFILE
else
    FIO_FILENAME=$(get_attached_volumes)
fi    

sed -i "s^FIO_FILENAME^$FIO_FILENAME^g" ~/*.fiojob
sed -i "s^LOAD_DURATION^$LOAD_DURATION^g" ~/*.fiojob
sed -i "s^FIO_IODEPTH^$FIO_IODEPTH^g" ~/*.fiojob
sed -i "s^FIO_SYNC^$FIO_SYNC^g" ~/*.fiojob

if [[ $FIO_RAMP_TIME != "none" ]]
then
    sed -i "s^#ramp_time=FIO_RAMP_TIME^ramp_time=$FIO_RAMP_TIME^g" ~/*.fiojob
fi

if test "$LOAD_PROFILE" = "readwrite" -o "$LOAD_PROFILE" = "randrw"
then
    sed -i "s^#rwmixread=FIO_RWMIXREAD^rwmixread=$FIO_RWMIXREAD^g" ~/*.fiojob
    sed -i "s^#rwmixwrite=FIO_RWMIXWRITE^rwmixwrite=$FIO_RWMIXWRITE^g" ~/*.fiojob
fi

# for the randread and read tests, we want to create the test file only once
if test "$LOAD_PROFILE" = "randread" -o "$LOAD_PROFILE" = "read" -o "$LOAD_PROFILE" = "readwrite" -o "$LOAD_PROFILE" = "randrw"
then
	if [[ $LOAD_ID -eq 1 ]]
	then
		BCSS=1M
		BCFFS=$(echo $FIO_FILE_SIZE | sed 's/G/*1024/g' | sed 's/M/*1/g' | bc)
		syslog_netcat "Creating FIO data file $FIO_FILENAME by writing $BCFFS $BCSS blocks from $FIO_PRE_CREATE_DATA ..."	
		if [[ $(echo $FIO_DATA_DIR | tr '[:upper:]' '[:lower:]') != "none" ]]
		then	
	        sudo rm -rf $FIO_DATA_DIR/*
        fi
        CRCMD="sudo dd if=$FIO_PRE_CREATE_DATA of=$FIO_FILENAME iflag=fullblock bs=$BCSS count=$BCFFS"
        $CRCMD
		syslog_netcat "Creating FIO data file $FIO_FILENAME with \"$CRCMD\" done"	        	
    fi
else
    if [[ $(echo $FIO_DATA_DIR | tr '[:upper:]' '[:lower:]') != "none" ]]
    then
        sudo rm -rf $FIO_DATA_DIR/*
    fi    
    sudo touch $FIO_FILENAME
fi

#If more than one command is needed (e.g., connected by "&&" or ";", please dump it on script, instead of just assigining to the variable CMDLINE"
echo "#!/usr/bin/env bash" > fioloadgen.sh
echo "sudo fio cb.fiojob --output-format=json" >> fioloadgen.sh

sudo chmod 755 ./fioloadgen.sh
CMDLINE="sudo ./fioloadgen.sh"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

# There is only one job per run (jobs[0])
READ_RUNTIME=$(jq '.jobs[0] .read .runtime' ${RUN_OUTPUT_FILE})
WRITE_RUNTIME=$(jq '.jobs[0] .write .runtime' ${RUN_OUTPUT_FILE})

RIOPS=0
RBW=0
RLATMIN=0
RLATMAX=0
RLATMEAN=0
RLATSTDDEV=0
RLATENCY=0
if test $READ_RUNTIME -gt 0; then
    RIOPS=$(jq '.jobs[0] .read .iops' ${RUN_OUTPUT_FILE})
    RBW=$(jq '.jobs[0] .read .bw' ${RUN_OUTPUT_FILE})
    RLATMIN=$(echo "scale = 2; $(jq '.jobs[0] .read .lat_ns .min' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    RLATMAX=$(echo "scale = 2; $(jq '.jobs[0] .read .lat_ns .max' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    RLATMEAN=$(echo "scale = 2; $(jq '.jobs[0] .read .lat_ns .mean' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    RLATSTDDEV=$(jq '.jobs[0] .read .lat_ns .stddev' ${RUN_OUTPUT_FILE})
    # read latency, 95th percentile in ms
    RLATENCY=$(echo "scale = 2; $(jq '.jobs[0] .read .clat_ns .percentile["95.000000"]' ${RUN_OUTPUT_FILE}) / 1000000" | bc -l)
fi

WIOPS=0
WBW=0
WLATMIN=0
WLATMAX=0
WLATMEAN=0
WLATSTDDEV=0
WLATENCY=0
if test $WRITE_RUNTIME -gt 0; then
    WIOPS=$(jq '.jobs[0] .write .iops' ${RUN_OUTPUT_FILE})
    WBW=$(jq '.jobs[0] .write .bw' ${RUN_OUTPUT_FILE})
    WLATMIN=$(echo "scale = 2; $(jq '.jobs[0] .write .lat_ns .min' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    WLATMAX=$(echo "scale = 2; $(jq '.jobs[0] .write .lat_ns .max' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    WLATMEAN=$(echo "scale = 2; $(jq '.jobs[0] .write .lat_ns .mean' ${RUN_OUTPUT_FILE})/ 1000" | bc -l)
    WLATSTDDEV=$(jq '.jobs[0] .write .lat_ns .stddev' ${RUN_OUTPUT_FILE})
    # write latency, 95th percentile in ms
    WLATENCY=$(echo "scale = 2; $(jq '.jobs[0] .write .clat_ns .percentile["95.000000"]' ${RUN_OUTPUT_FILE}) / 1000000" | bc -l)
fi

LATENCY=$(echo "scale=2; ($WLATENCY + $RLATENCY)/2" | bc -l)
TPUT=$(echo "scale=2; ($WIOPS + $RIOPS)/2" | bc -l)

~/cb_report_app_metrics.py \
write_throughput:$WIOPS:tps \
write_latency:$WLATENCY:ms \
write_iops:$WIOPS:iops \
write_bw:$WBW:KiBs \
write_latmin:$WLATMIN:usec \
write_latmax:$WLATMAX:usec \
write_latmean:$WLATMEAN:usec \
write_latstddev:$WLATSTDDEV:nsec \
read_throughput:$RIOPS:tps \
read_latency:$RLATENCY:ms \
read_iops:$RIOPS:iops \
read_bw:$RBW:KiBs \
read_latmin:$RLATMIN:usec \
read_latmax:$RLATMAX:usec \
read_latmean:$RLATMEAN:usec \
read_latstddev:$RLATSTDDEV:nsec \
latency:$LATENCY:ms \
throughput:$TPUT:tps \
$(common_metrics)    

unset_load_gen

exit 0
