#!/usr/bin/env bash

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_acmeair_common.sh

set_load_gen $@

if [[ ${LOAD_ID} == "1" ]]
then
    GENERATE_DATA="true"
else
    GENERATE_DATA=`get_my_ai_attribute_with_default regenerate_data true`
fi

GENERATE_DATA=$(echo $GENERATE_DATA | tr '[:upper:]' '[:lower:]')

if [[ ${GENERATE_DATA} == "true" ]]
then

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    NUM_CUSTOMERS=`get_my_ai_attribute_with_default num_customers 1000`

    START_GENERATION=$(get_time)
                                                
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"true\". Will generate data for the AcmeAir load profile \"${LOAD_PROFILE}\"" 
    command_line="curl http://${liberty_ip}:${ACMEAIR_HTTP_PORT}/rest/info/loader/load?numCustomers=$NUM_CUSTOMERS"
    syslog_netcat "Command line is: ${command_line}"
    if [[ x"${log_output_command}" == x"true" ]]
    then
        syslog_netcat "Command output will be shown"
        $command_line 2>&1 | while read line ; do
            syslog_netcat "$line"
            echo $line >> $GEN_OUTPUT_FILE
        done
        ERROR=$?        
    else
        syslog_netcat "Command output will NOT be shown"
        $command_line 2>&1 >> $GEN_OUTPUT_FILE
        ERROR=$?
    fi
    END_GENERATION=$(get_time)
    update_app_errors $ERROR

    DATA_GENERATION_TIME=$(expr ${END_GENERATION} - ${START_GENERATION})
    update_app_datagentime ${DATA_GENERATION_TIME}
    update_app_datagensize $(echo "$NR_USERS + $NR_QUOTES" | bc)
else
    syslog_netcat "The value of the parameter \"GENERATE_DATA\" is \"false\". Will bypass data generation for the AcmeAir load profile \"${LOAD_PROFILE}\""    
fi

ACMEAIR_DRIVER_RAMPUP_TIME=`get_my_ai_attribute_with_default acmeair_driver_rampup_time 10`

if [[ -f $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx.original ]]
then
    cp $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx.original
fi

sed -i "s^<stringProp name=\"ThreadGroup.num_threads\">.*</stringProp>^<stringProp name=\"ThreadGroup.num_threads\">$LOAD_LEVEL</stringProp>^g" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx
sed -i "s^<stringProp name=\"ThreadGroup.duration\">.*</stringProp>^<stringProp name=\"ThreadGroup.duration\">$LOAD_DURATION</stringProp>^g" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx
sed -i "s^<stringProp name=\"HTTPSampler.port\">.\+</stringProp>^<stringProp name=\"HTTPSampler.port\">$ACMEAIR_HTTP_PORT</stringProp>^" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx
sed -i "s^<stringProp name=\"maximumValue\">.*</stringProp>^<stringProp name=\"maximumValue\">$NUM_CUSTOMERS</stringProp>^g" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx
sed -i "s^<stringProp name=\"ThreadGroup.ramp_time\">.*</stringProp>^<stringProp name=\"ThreadGroup.ramp_time\">$ACMEAIR_DRIVER_RAMPUP_TIME</stringProp>^g" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx
sed -i "s^              <stringProp name=\"Argument.value\">/acmeair-webapp</stringProp>^              <stringProp name=\"Argument.value\">/</stringProp>^" $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/AcmeAir.jmx

echo "$liberty_ip" > $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/hosts.csv

if [[ -f $ACMEAIR_PATH/AcmeAir-v5.jmx.original ]]
then
    cp $ACMEAIR_PATH/AcmeAir-v5.jmx $ACMEAIR_PATH/AcmeAir-v5.jmx.original
fi

sed -i "s^<stringProp name=\"ThreadGroup.num_threads\">.*</stringProp>^<stringProp name=\"ThreadGroup.num_threads\">$LOAD_LEVEL</stringProp>^g" $ACMEAIR_PATH/AcmeAir-v5.jmx
sed -i "s^<stringProp name=\"ThreadGroup.duration\">.*</stringProp>^<stringProp name=\"ThreadGroup.duration\">$LOAD_DURATION</stringProp>^g" $ACMEAIR_PATH/AcmeAir-v5.jmx
sed -i "s^<stringProp name=\"HTTPSampler.port\">.\+</stringProp>^<stringProp name=\"HTTPSampler.port\">$ACMEAIR_HTTP_PORT</stringProp>^" $ACMEAIR_PATH/AcmeAir-v5.jmx
sed -i "s^<stringProp name=\"maximumValue\">.*</stringProp>^<stringProp name=\"maximumValue\">$NUM_CUSTOMERS</stringProp>^g" $ACMEAIR_PATH/AcmeAir-v5.jmx
sed -i "s^<stringProp name=\"ThreadGroup.ramp_time\">.*</stringProp>^<stringProp name=\"ThreadGroup.ramp_time\">$ACMEAIR_DRIVER_RAMPUP_TIME</stringProp>^g" $ACMEAIR_PATH/AcmeAir-v5.jmx
sed -i "s^              <stringProp name=\"Argument.value\">/acmeair-webapp</stringProp>^              <stringProp name=\"Argument.value\">/</stringProp>^" $ACMEAIR_PATH/AcmeAir-v5.jmx

echo "$liberty_ip" > $ACMEAIR_PATH/hosts.csv

cd $ACMEAIR_DRIVER_PATH/acmeair-jmeter/scripts/

CMDLINE="jmeter -n -t AcmeAir.jmx -j AcmeAir1.log"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

throughput=$(cat ${RUN_OUTPUT_FILE} | grep summary | tail -1 | awk '{ print $7 }' | sed 's^/s^^g')
latency=$(cat ${RUN_OUTPUT_FILE} | grep summary | tail -1 | awk '{ print $9 }')
min_latency=$(cat ${RUN_OUTPUT_FILE} | grep summary | tail -1 | awk '{ print $11 }')
max_latency=$(cat $RUN_OUTPUT_FILE | grep summary | tail -1 | awk '{ print $13 }')
transaction_errors=$(cat $RUN_OUTPUT_FILE | grep summary | tail -1 | awk '{ print $15 }')

~/cb_report_app_metrics.py \
min_latency:$min_latency:ms \
max_latency:$max_latency:ms \
transaction_errors:$transaction_errors:num \
latency:${latency}:ms \
throughput:${throughput}:ops \
$(common_metrics)    

unset_load_gen

exit 0
