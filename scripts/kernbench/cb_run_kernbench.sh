#!/usr/bin/env bash

cd ~

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

KERNBENCH_NR_CPUS=$(get_my_ai_attribute_with_default kernbench_nr_cpus 0)
KERNBENCH_DATA_DIR=$(get_my_ai_attribute_with_default kernbench_data_dir /kernbench)
KERNBENCH_PATH=$(get_my_ai_attribute_with_default kernbench_path /foo)

# Override the default 4*cpu for make -j <nr>
if test $KERNBENCH_NR_CPUS = 0; then
	NRJOBS=""
else
	NRJOBS="-o $KERNBENCH_NR_CPUS"
fi

CMDLINE="sudo ./kernbenchloadgen.sh $KERNBENCH_PATH $KERNBENCH_DATA_DIR $NRJOBS"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

elapsed_time=$(grep "Elapsed Time" ${KERNBENCH_PATH}/kernbench.log | awk '{print $3}')
user_time=$(grep "User Time" ${KERNBENCH_PATH}/kernbench.log | awk '{print $3}')
system_time=$(grep "System Time" ${KERNBENCH_PATH}/kernbench.log | awk '{print $3}')
percent_cpu=$(grep "Percent CPU" ${KERNBENCH_PATH}/kernbench.log | awk '{print $3}')
context_switches=$(grep "Context Switches" ${KERNBENCH_PATH}/kernbench.log | awk '{print $3}')
sleeps=$(grep "Sleeps" ${KERNBENCH_PATH}/kernbench.log | awk '{print $2}')

~/cb_report_app_metrics.py \
elapsed_time:$elapsed_time:s \
user_time:$user_time:s \
system_time:$system_time:s \
percent_cpu:$percent_cpu:pc \
context_switches:$context_switches:nr \
sleeps:$sleeps:nr \
$(common_metrics)

echo "~/cb_report_app_metrics.py \
	elapsed_time:$elapsed_time:s \
	user_time:$user_time:s \
	system_time:$system_time:s \
	percent_cpu:$percent_cpu:pc \
	context_switches:$context_switches:nr \
	sleeps:$sleeps:nr \
	$(common_metrics)" >>/tmp/metrics.txt

rm ${KERNBENCH_PATH}/kernbench.log

unset_load_gen

exit 0
