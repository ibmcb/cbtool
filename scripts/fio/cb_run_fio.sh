#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

FIOIP=`get_ips_from_role fio`
OUT_FILE="fio-out.json"

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

FIO_ENGINE=$(get_my_ai_attribute_with_default fio_engine sync)
FIO_BS=$(get_my_ai_attribute_with_default fio_bs 64k)
FIO_DIRECT=$(get_my_ai_attribute_with_default fio_direct 1)
FIO_IOKIND=$(get_my_ai_attribute_with_default fio_iokind randread)
# file size to test in MB
FIO_FILE_SIZE=$(get_my_ai_attribute_with_default fio_file_size 128)
FIO_DATA_DIR=$(get_my_ai_attribute_with_default fio_data_dir /fiotest)
FIO_IODEPTH=$(get_my_ai_attribute_with_default fio_iodepth 8)
FIO_SYNC=$(get_my_ai_attribute_with_default fio_sync 0)
# seconds
FIO_RUNTIME=$LOAD_DURATION

# The randread and randwrite templates have been replaced by a
# fully-parameterized template.
cat ~/cb.fiojob.template > ~/cb.fiojob

sed -i "s^FIO_ENGINE^$FIO_ENGINE^g" ~/*.fiojob
sed -i "s^FIO_BS^$FIO_BS^g" ~/*.fiojob
sed -i "s^FIO_DIRECT^$FIO_DIRECT^g" ~/*.fiojob
sed -i "s^FIO_IOKIND^$FIO_IOKIND^g" ~/*.fiojob
sed -i "s^FIO_FILE_SIZE^${FIO_FILE_SIZE}m^g" ~/*.fiojob
sed -i "s^FIO_DATA_DIR^$FIO_DATA_DIR^g" ~/*.fiojob
# e.g: /fiotest/randwrite
sed -i "s^FIO_FILENAME^$FIO_DATA_DIR/$FIO_IOKIND^g" ~/*.fiojob
sed -i "s^FIO_RUNTIME^$FIO_RUNTIME^g" ~/*.fiojob
sed -i "s^FIO_IODEPTH^$FIO_IODEPTH^g" ~/*.fiojob
sed -i "s^FIO_SYNC^$FIO_SYNC^g" ~/*.fiojob

sudo mkdir -p $FIO_DATA_DIR

# for the randread and read tests, we want to create the test file only once
if test "$FIO_IOKIND" = "randread" -o "$FIO_IOKIND" = "read" -o "$FIO_IOKIND" = "randrw"; then
	if ! test -e $FIO_DATA_DIR/$FIO_IOKIND; then
		syslog_netcat "Creating FIO data file $FIO_DATA_DIR/$FIO_IOKIND"
		sudo rm -rf $FIO_DATA_DIR/*
		sudo dd if=/dev/zero of=$FIO_DATA_DIR/$FIO_IOKIND bs=1M count=$FIO_FILE_SIZE
		syslog_netcat "Creating FIO data file $FIO_DATA_DIR/$FIO_IOKIND done"
	fi
else
	sudo rm -rf $FIO_DATA_DIR/*
	sudo touch $FIO_DATA_DIR/$FIO_IOKIND
fi

#If more than one command is needed (e.g., connected by "&&" or ";", please dump it on script, instead of just assigining to the variable CMDLINE"
echo "#!/usr/bin/env bash" > fioloadgen.sh
echo "fio cb.fiojob --output-format=json > ${OUT_FILE}" >> fioloadgen.sh

sudo chmod 755 ./fioloadgen.sh
CMDLINE="sudo ./fioloadgen.sh"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

# We now output json from FIO so the fiostats.sh script has been replaced.
# The same metrics are still extracted.

# There is only one job per run (jobs[0])
READ_RUNTIME=$(jq '.jobs[0] .read .runtime' ${OUT_FILE})
WRITE_RUNTIME=$(jq '.jobs[0] .write .runtime' ${OUT_FILE})

RIOPS=0
RBW=0
RLATMIN=0
RLATMAX=0
RLATMEAN=0
RLATSTDDEV=0
RLATENCY=0
if test $READ_RUNTIME -gt 0; then
	RIOPS=$(jq '.jobs[0] .read .iops' ${OUT_FILE})
	RBW=$(jq '.jobs[0] .read .bw' ${OUT_FILE})
	RLATMIN=$(jq '.jobs[0] .read .lat .min' ${OUT_FILE})
	RLATMAX=$(jq '.jobs[0] .read .lat .max' ${OUT_FILE})
	RLATMEAN=$(jq '.jobs[0] .read .lat .mean' ${OUT_FILE})
	RLATSTDDEV=$(jq '.jobs[0] .read .lat .stddev' ${OUT_FILE})
	# read latency, 95th percentile in ms
	RLATENCY=$(echo "scale = 2; $(jq '.jobs[0] .read .clat .percentile["95.000000"]' ${OUT_FILE}) / 1000" | bc -l)
fi

WIOPS=0
WBW=0
WLATMIN=0
WLATMAX=0
WLATMEAN=0
WLATSTDDEV=0
WLATENCY=0
if test $WRITE_RUNTIME -gt 0; then
	WIOPS=$(jq '.jobs[0] .write .iops' ${OUT_FILE})
	WBW=$(jq '.jobs[0] .write .bw' ${OUT_FILE})
	WLATMIN=$(jq '.jobs[0] .write .lat .min' ${OUT_FILE})
	WLATMAX=$(jq '.jobs[0] .write .lat .max' ${OUT_FILE})
	WLATMEAN=$(jq '.jobs[0] .write .lat .mean' ${OUT_FILE})
	WLATSTDDEV=$(jq '.jobs[0] .write .lat .stddev' ${OUT_FILE})
	# write latency, 95th percentile in ms
	RLATENCY=$(echo "scale = 2; $(jq '.jobs[0] .write .clat .percentile["95.000000"]' ${OUT_FILE}) / 1000" | bc -l)
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
write_latstddev:$WLATSTDDEV:usec \
read_throughput:$RIOPS:tps \
read_latency:$RLATENCY:ms \
read_iops:$RIOPS:iops \
read_bw:$RBW:KiBs \
read_latmin:$RLATMIN:usec \
read_latmax:$RLATMAX:usec \
read_latmean:$RLATMEAN:usec \
read_latstddev:$RLATSTDDEV:usec \
latency:$LATENCY:ms \
throughput:$TPUT:tps \
$(common_metrics)    

unset_load_gen

exit 0
