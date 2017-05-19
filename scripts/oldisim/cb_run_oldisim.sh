#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

cd ~

OLDISIM_DIR=$(get_my_ai_attribute_with_default oldisim_dir ~/oldisim)
eval OLDISIM_DIR=${OLDISIM_DIR}

OPTS_OLDISIMBIN=''
if [[ ${my_role} == "oldisimdriver" ]]
then 
    ACTUAL_OLDISIMBIN="DriverNode"
    for node in $(get_ips_from_role oldisimroot)
    do
        OPTS_OLDISIMBIN=${OPTS_OLDISIMBIN}" --server $node"
    done
fi
OPTS_OLDISIMBIN=${OPTS_OLDISIMBIN}" --threads $LOAD_LEVEL"

ACTUAL_OLDISIMBIN_FULL_PATH=${OLDISIM_DIR}/release/workloads/search/${ACTUAL_OLDISIMBIN}

echo "#!/usr/bin/env bash" > ~/cb_exec_oldisim.sh
echo "$ACTUAL_OLDISIMBIN_FULL_PATH $OPTS_OLDISIMBIN &" >> ~/cb_exec_oldisim.sh
echo "MYPID=\$(sudo ps aux | grep -v grep | grep $ACTUAL_OLDISIMBIN_FULL_PATH | awk '{ print \$2 }')" >> ~/cb_exec_oldisim.sh
echo "sleep ${LOAD_DURATION}" >> ~/cb_exec_oldisim.sh
echo "sudo kill -SIGINT \$MYPID" >> ~/cb_exec_oldisim.sh
echo "sleep 5" >> ~/cb_exec_oldisim.sh
echo "exit 0" >> ~/cb_exec_oldisim.sh
sudo chmod 755 ~/cb_exec_oldisim.sh
CMDLINE="./cb_exec_oldisim.sh"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

tp=$(cat ${RUN_OUTPUT_FILE} | grep QPS | awk '{ print $2 }')
lat=$(cat ${RUN_OUTPUT_FILE} | grep avg | sed 's/avg: //g' | tr -d ' ')
lat_95=$( cat ${RUN_OUTPUT_FILE} | grep 95p | sed 's/95p: //g' | tr -d ' ')

~/cb_report_app_metrics.py \
datagen_time:$(update_app_datagentime):sec \
datagen_size:$(update_app_datagensize):records \
throughput:$tp:tps \
$(format_for_report latency $lat) \
$(format_for_report 95_latency $lat_95) \
$(common_metrics)
 
unset_load_gen

exit 0
