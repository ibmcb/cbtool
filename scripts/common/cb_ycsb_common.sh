#!/usr/bin/env bash

#/*******************************************************************************
#
# This source code is provided as is, without any express or implied warranty.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

#####################################################################################
# Common routines for YCSB 
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

declare -A token

LINUX_DISTRO=$(linux_distribution)
BACKEND_TYPE=$(get_my_ai_attribute type | sed 's/_ycsb//g')

set_java_home

if [[ $BACKEND_TYPE == "cassandra" ]]
then
    sudo mkdir -p /var/run/cassandra/
    sudo chmod 777 /var/run/cassandra
fi

MY_IP=$my_ip_addr

YCSB_PATH=$(get_my_ai_attribute_with_default ycsb_path ~/YCSB)
eval YCSB_PATH=${YCSB_PATH}

YCSB_PROFILE=`get_my_ai_attribute_with_default ycsb_profile cassandra-10`

if [[ $BACKEND_TYPE == "cassandra" ]]
then 
    CASSANDRA_DATA_DIR=$(get_my_ai_attribute_with_default cassandra_data_dir /dbstore)
    eval CASSANDRA_DATA_DIR=${CASSANDRA_DATA_DIR}

    CASSANDRA_DATA_FSTYP=$(get_my_ai_attribute_with_default cassandra_data_fstyp ext4)
    eval CASSANDRA_DATA_FSTYP=${CASSANDRA_DATA_FSTYP}

    SEED_DATA_DIR=$(get_my_ai_attribute_with_default seed_data_dir /dbstore)
    eval SEED_DATA_DIR=${SEED_DATA_DIR}

    SEED_DATA_FSTYP=$(get_my_ai_attribute_with_default seed_data_fstyp ext4)
    eval SEED_DATA_FSTYP=${SEED_DATA_FSTYP}

    cassandra_ips=`get_ips_from_role cassandra`
    seed_ips=`get_ips_from_role seed`
    
    db_nodes=`echo "${cassandra_ips}" | wc -w`
    seed_nodes=`echo "${seed_ips}" | wc -w`
    total_nodes=`expr $db_nodes + $seed_nodes`
    pos=0
    while read line
    do
        if [[ $pos -lt $total_nodes ]]
        then
            arr=(`echo ${seed_ips} ${cassandra_ips}`)
            ip=${arr[$pos]}
            token[$ip]=${line:10}
       fi
       pos=$((pos+1))
    done < <(token-generator $total_nodes|grep Node)

    my_token=${token[$MY_IP]}
    syslog_netcat "Cassandra token is \"${my_token}\""
        
    cassandra_ips_csv=`echo "${cassandra_ips}" | sed ':a;N;$!ba;s/\n/, /g'`

    seed_ips_csv=`echo "${seed_ips}" | sed ':a;N;$!ba;s/\n/, /g' | tr -d ' '`

    if [[ -z $cassandra_ips ]]
    then
        syslog_netcat "No VMs with the \"cassandra\" role have been found on this AI"
    else
        syslog_netcat "The VMs with the \"cassandra\" role on this AI have the following IPs: ${cassandra_ips_csv}"
    fi

    if [[ -z $seed_ips ]]
    then
        syslog_netcat "No VMs with the \"seed\" role have been found on this AI"
        exit 1;
    else
        syslog_netcat "The VMs with the \"seed\" role on this AI has the following IPs: ${seed_ips_csv}"
    fi
    
elif [[ $BACKEND_TYPE == "mongo" ]]
then 

    MONGODB_DATA_DIR=$(get_my_ai_attribute_with_default mongodb_data_dir /dbstore)
    eval MONGODB_DATA_DIR=${MONGODB_DATA_DIR}

    MONGODB_DATA_FSTYP=$(get_my_ai_attribute_with_default mongodb_data_fstyp ext4)
    eval MONGODB_DATA_FSTYP=${MONGODB_DATA_FSTYP}

    MONGODB_USER=$(sudo cat /etc/passwd | grep mongo | cut -d ':' -f 1)

    MONGODB_EXECUTABLE=$(which mongodb)
    if [[ $? -ne 0 ]]
    then
        MONGODB_EXECUTABLE=$(which mongod)
    fi
    
    sudo ls /etc/mongodb.conf > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        MONGODB_CONF_FILE=/etc/mongodb.conf
    else
        MONGODB_CONF_FILE=/etc/mongod.conf
    fi
                        
    mongos_ip=`get_ips_from_role mongos`
    if [ -z $mongos_ip ]
    then
        syslog_netcat "mongos IP is null"
        exit 1
    fi
    
    mongocfg_ip=`get_ips_from_role mongo_cfg_server`
    if [ -z $mongocfg_ip ]
    then
        syslog_netcat "mongocfg IP is null"
        exit 1
    fi
    
    mongo_ips=`get_ips_from_role mongodb`
    
    total_nodes=`echo "${mongo_ips}" | wc -w`

    mongo_ips_csv=`echo "${mongo_ips}" | sed ':a;N;$!ba;s/\n/, /g'`

    if [[ $(cat /etc/hosts | grep -c mongo-cfg-server) -eq 0 ]]
    then    
        sudo sh -c "echo $mongocfg_ip mongo-cfg-server >> /etc/hosts"
    fi

    if [[ $(cat /etc/hosts | grep -c mongos) -eq 0 ]]
    then    
        sudo sh -c "echo $mongos_ip mongos >> /etc/hosts"
    fi

elif [[ $BACKEND_TYPE == "redis" ]]
then 
    REDIS_DATA_DIR=$(get_my_ai_attribute_with_default redis_data_dir /dbstore)
    eval REDIS_DATA_DIR=${REDIS_DATA_DIR}

    redis_ips=`get_ips_from_role redis`
    if [ -z $redis_ips ]
    then
        syslog_netcat "redis IP is null"
        exit 1
    fi    

    redis_ips_csv=`echo "${redis_ips}" | sed ':a;N;$!ba;s/\n/, /g'`
                
else 
    syslog_netcat "Unsupported backend type ($BACKEND_TYPE). Exiting with error"
    exit 1
fi

function lazy_collection {

    CMDLINE=$1
    OUTPUT_FILE=$2.run
    SLA_RUNTIME_TARGETS=$3
    
    ops=0
    latency=0

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    run_limit=`decrement_my_ai_attribute run_limit`

    if [[ -f /tmp/quiescent_time_start ]]
    then
        QSTART=$(cat /tmp/quiescent_time_start)
        END=$(date +%s)
        DIFF=$(( $END - $QSTART ))
        echo $DIFF > /tmp/quiescent_time        
    fi

    LOAD_GENERATOR_START=$(date +%s)    
    while read line
    do
        log_output_command=$(get_my_ai_attribute log_output_command)
        log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')
        if [[ x"${log_output_command}" == x"true" ]] ; then
	    syslog_netcat "$line"
	fi
        echo $line >> $OUTPUT_FILE
        IFS=',' read -a array <<< "$line"
        if [[ ${array[0]} == *OVERALL* ]]
        then
            if [[ ${array[1]} == *Throughput* ]]
            then
                ops=${array[2]}
            fi
        fi
        if [[ ${array[0]} == *UPDATE* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                latency=${array[2]}
            fi
        fi
        if [[ ${array[0]} == *READ* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                latency=${array[2]}
            fi
        fi
    
    # Check for New Shard
    
    done < <($CMDLINE 2>&1)
    
    ERROR=$?
    update_app_errors $ERROR
    
    LOAD_GENERATOR_END=$(date +%s)
    APP_COMPLETION_TIME=$(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START ))       
    update_app_completiontime $APP_COMPLETION_TIME

    echo $(date +%s) > /tmp/quiescent_time_start

    syslog_netcat "RUN COMPLETE: ${LIDMSG}"    
    
    if [[ $BACKEND_TYPE == "cassandra" ]]
    then
        FIRST_SEED=$(echo $seed_ips_csv | cut -d ',' -f 1)
        check_cassandra_cluster_state ${FIRST_SEED} 1 1
        ERROR=$?
        update_app_errors $ERROR
    fi

    insert_operations=$(cat $OUTPUT_FILE | grep Operations | grep INSERT | cut -d ',' -f 3 | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
    read_operations=$(cat $OUTPUT_FILE | grep Operations | grep READ | cut -d ',' -f 3 | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')

    CB_REPORT_CLI_PARMS=force_conversion_us_to_ms
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_id:${LOAD_ID}:seqnum
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_level:${LOAD_LEVEL}:load
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_profile:${LOAD_PROFILE}:name
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_duration:${LOAD_DURATION}:sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'completion_time:$(update_app_completiontime):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'throughput:$(expr $ops):tps
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'errors:$(update_app_errors):num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'datagen_time:$(update_app_datagentime):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'datagen_size:$(update_app_datagensize):records
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'read_operations:$read_operations:num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'insert_operations:$insert_operations:num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'quiescent_time:$(update_app_quiescent):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'latency:$(expr $latency):us
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' '${SLA_RUNTIME_TARGETS}

    ~/cb_report_app_metrics.py $CB_REPORT_CLI_PARMS
        
    syslog_netcat "Exit code for \"~/cb_report_app_metrics.py $CB_REPORT_CLI_PARMS\" is $?"    
}

function get_cassandra_cli {

    local=$1
    
    if [[ $local -eq 1 ]]
    then
        ACTUAL_NODE=$MY_IP
    else
        ACTUAL_NODE=$(echo $seed_ips_csv | cut -d ',' -f 1)
    fi
    
    if [[ $YCSB_PROFILE == "cassandra2-cql" ]]
    then
        cqlsh ${ACTUAL_NODE} -f cqlsh_list_keyspace.cassandra > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CCLIN=cqlsh
            export CCLI="$CCLIN ${ACTUAL_NODE}"
            export CTBN=ycsb
            syslog_netcat "Successfully contacted Cassandra with command \"$CCLI -f ${CCLIN}_list_keyspace.cassandra\" through node ${ACTUAL_NODE}"
            return 0
        else
            syslog_netcat "Failed while attempting to contact Cassandra with command \"$CCLI -f ${CCLIN}_list_keyspace.cassandra\" through node ${ACTUAL_NODE}"            
            return 1
        fi
    else
        cassandra-cli -h ${ACTUAL_NODE} -f cassandra-cli_list_keyspace.cassandra > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then    
            export CCLIN=cassandra-cli
            export CCLI="$CCLIN -h ${ACTUAL_NODE}"
            export CTBN=usertable
            syslog_netcat "Successfully contacted Cassandra with command \"$CCLI -f ${CCLIN}_list_keyspace.cassandra\" through node ${ACTUAL_NODE}"
            return 0
        else
            syslog_netcat "Failed while attempting to contact Cassandra with command \"$CCLI -f ${CCLIN}_list_keyspace.cassandra\" through node ${ACTUAL_NODE}"            
            return 1     
        fi
    fi
}    
export -f get_cassandra_cli
           
function check_cassandra_cluster_state {

    syslog_netcat "Waiting for all nodes to become available..."

    NODETOOLHN=$1
    ATTEMPTS=$2
    INTERVAL=$3

    counter=0
    get_cassandra_cli $(sudo ifconfig -a | grep -c ${NODETOOLHN}[[:space:]])

    has_system_keyspace=$($CCLI -f ${CCLIN}_list_keyspace.cassandra | sed 's/system_traces//g' | grep -c [[:space:]]system)

    NODETOOLAUTH="-u cassandra -pw cassandra" 

    which cbcluster >/dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "#!/usr/bin/env bash" > /tmp/cbcluster
        echo "export JAVA_HOME=${JAVA_HOME}" >> /tmp/cbcluster
        echo "nodetool $NODETOOLAUTH -h ${NODETOOLHN} status" >> /tmp/cbcluster    
        sudo chmod 0755 /tmp/cbcluster
        sudo mv /tmp/cbcluster /usr/local/bin/cbcluster
    fi                

    NODES_REGISTERED=0    
                                                   
    while [[ ($NODES_REGISTERED -ne $total_nodes || $has_system_keyspace -ne 1) && "$counter" -le "$ATTEMPTS" ]]
    do
        syslog_netcat "Obtaining the node list for this Cassandra cluster by running \"nodetool $NODETOOLAUTH -h ${NODETOOLHN} status\"..."            
        for NODEIP in $(nodetool $NODETOOLAUTH -h ${NODETOOLHN} status | tail -n +6 | grep -v "Non-system" | awk '{ print $2 }')
        do
            if [[ $(sudo cat /etc/hosts | grep -c $NODEIP) -ne 0 ]]
            then
                NODES_REGISTERED="$(( $NODES_REGISTERED + 1 ))"
            fi            
        done

        syslog_netcat "Nodes registered on the cluster: $NODES_REGISTERED out of $total_nodes"        
        counter="$(( $counter + 1 ))"
        
        syslog_netcat "Make sure that Keyspace \"system\" is present"
        has_system_keyspace=$($CCLI -f ${CCLIN}_list_keyspace.cassandra | sed 's/system_traces//g' | grep -c [[:space:]]system) 
        
        sleep $INTERVAL
    done

    if [[ $counter -gt $ATTEMPTS || $has_system_keyspace -eq 0 ]]
    then
        return 1
    else
        return 0
    fi
}
export -f check_cassandra_cluster_state

function check_mongodb_cluster_state {

    syslog_netcat "Waiting for all nodes to become available..."

    MONGOSHN=$1
    MONGORS=$2
    ATTEMPTS=$3
    INTERVAL=$4

    counter=0

    which cbcluster >/dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "#!/usr/bin/env bash" > /tmp/cbcluster
        echo "mongo --host ${mongos_ip}:27017 --eval \"db.printShardingStatus()\"" >> /tmp/cbcluster
        sudo chmod 0755 /tmp/cbcluster
        sudo mv /tmp/cbcluster /usr/local/bin/cbcluster
    fi

    if [[ $ATTEMPTS -eq 0 ]]
    then
        return 0
    fi
    
    NODES_REGISTERED=0
    while [[ $NODES_REGISTERED -ne $total_nodes ]]
    do
        syslog_netcat "Obtaining the node list for this MongoDB cluster by running \"mongo --host ${MONGOSHN}:27017 --eval \"db.printShardingStatus()\" | grep \"${MONGORS} | wc -l\"..."            
        NODES_REGISTERED=$(mongo --host ${MONGOSHN}:27017 --eval "db.printShardingStatus()" | grep \"${MONGORS} | grep host | wc -l)                        

        syslog_netcat "Nodes registered on the cluster: $NODES_REGISTERED out of $total_nodes"        
        counter="$(( $counter + 1 ))"

        sleep $INTERVAL
    done

    if [[ $counter -gt $ATTEMPTS ]]
    then
        return 1
    else
        return 0
    fi
}
export -f check_mongodb_cluster_state

function show_cassandra_cluster_schema {

    if [[ -z ${1} ]]
    then
        NODETOOLHN=${MY_IP}
    else
        NODETOOLHN=$1
    fi
    nodetool $NODETOOLAUTH -h ${NODETOOLHN} describecluster
}
export -f show_cassandra_cluster_schema

function eager_collection {
    CMDLINE=$1
    OUTPUT_FILE=$2.run
    SLA_RUNTIME_TARGETS=$3
        
    #----------------------- Track all YCSB results  -------------------------------

    #----------------------- Total op/sec ------------------------------------------
    ops=0

    #----------------------- Operation types ---------------------------------------
    # Also, assign an array index to each operation to store results.
    # Using an array reduces the number of variables and makes the code more
    # maintainable.
    #-------------------------------------------------------------------------------
    OPERATIONS=(READ UPDATE INSERT SCAN)
    READ=0
    UPDATE=1
    INSERT=2
    SCAN=3

    #----------------------- Tracking Latency --------------------------------------
    # <operation>_[average|min|max|95|99]_latency
    # declare arrays for latency measurementes and measurement units.
    #-------------------------------------------------------------------------------
    declare -a latency_avg
    declare -a latency_min
    declare -a latency_max
    declare -a latency_95
    declare -a latency_99
    declare -a latency_avg_units
    declare -a latency_min_units
    declare -a latency_max_units
    declare -a latency_95_units
    declare -a latency_99_units

    LOAD_GENERATOR_START=$(date +%s)      
    while read line
    do
        log_output_command=$(get_my_ai_attribute log_output_command)
        log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')
        if [[ x"${log_output_command}" == x"true" ]] ; then
	    syslog_netcat "$line"
	fi
        echo $line >> $OUTPUT_FILE
    #-------------------------------------------------------------------------------
    # Need to track each YCSB Clients current operation count.
    # NEED TO:
    #       Create a variable that reports to CBTool the current operation
    # This regex is broken.  So are all of the awk commands. They all reference
    # an incorrect column for the claimed variable.
    #-------------------------------------------------------------------------------
        if [[ "$line" =~ "[0-9]+\s sec:" ]]
        then
            CURRENT_OPS=$(echo $line | awk '{print $3}')
            syslog_netcat "Current Ops : $CURRENT_OPS"
            if [[ "$line" == *READ* ]]
            then
                AVG_READ_LATENCY=$(echo $line | awk '{print $11}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netcat "Current Avg. Read Latency : $AVG_READ_LATENCY"
            fi
            
            if [[ "$line" == *WRITE* ]]
            then
                AVG_WRITE_LATENCY=$(echo $line | awk '{print $9}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netcat "Current Avg. Write Latency : $AVG_WRITE_LATENCY"
            fi
            
            if [[ "$line" == *UPDATE* ]]
            then
                AVG_UPDATE_LATENCY=$(echo $line | awk '{print $9}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netcat "Current Avg. Update Latency : $AVG_UPDATE_LATENCY"
            fi
        fi
    
    #----------------------- Track Latency -----------------------------------------
    # example text:  [READ], 95thPercentileLatency(ms), 15
    # where READ can be INSERT, OVERALL, READ, SCAN, UPDATE
    #-------------------------------------------------------------------------------
        IFS=',' read -a array <<< "$line"
        if [[ ${array[0]} == *OVERALL* ]]
        then
            if [[ ${array[1]} == *Throughput* ]]
            then
                ops=${array[2]}
            fi
        fi
   
        # Look for all Operations in this line read from YCSB output.
        # Exit operation loop once a match is found. Only one OPERATION can exist on each line.
        # (That is different than the real-time tracking done in the (broken) section above.
        #  Those lines will contain multiple measurements on a single line.)
        for OPERATION in "${OPERATIONS[@]}"
        do
            # dereference Operation variable to extract integer array index for 
            # this operation.
            # - this works because above we defined a variable with a name
            #   equal to the operation name.
            # - eval executes something like 'echo $READ'
            index=$(eval echo \$$OPERATION)

            if [[ ${array[0]} == *${OPERATION}* ]]
            then
                # Grab units from second item in array.  Units are in parentheses.
                # Preserve old behavior if not found. (==> set to 'us')
                # example text:  [READ], 95thPercentileLatency(ms), 15
                units='us'
                if [[ ${array[1]} =~ \(([a-zA-Z]+)\) ]];
                then
                    units=${BASH_REMATCH[1]}
                fi

                # 'expr' will remove any leading or trailing spaces from numbers
                value=$(expr ${array[2]})

                if [[ ${array[1]} == *AverageLatency* ]]
                then
                    latency_avg[$index]=$value
                    latency_avg_units[$index]=$units
                    break
                elif [[ ${array[1]} == *MinLatency* ]]
                then
                    latency_min[$index]=$value
                    latency_min_units[$index]=$units
                    break
                elif [[ ${array[1]} == *MaxLatency* ]]
                then
                    latency_max[$index]=$value
                    latency_max_units[$index]=$units
                    break
                elif [[ ${array[1]} == *95thPercent* ]]
                then
                    latency_95[$index]=$value
                    latency_95_units[$index]=$units
                    break
                elif [[ ${array[1]} == *99thPercent* ]]
                then
                    latency_99[$index]=$value
                    latency_99_units[$index]=$units
                    break
                fi
            fi
        done
    done < <($CMDLINE 2>&1)

    # Check for a non-zero exit code of YCSB. If non-zero, consider it as an error.
    ERROR=$?
    update_app_errors $ERROR
    
    LOAD_GENERATOR_END=$(date +%s)
    update_app_completiontime $(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START ))       

    syslog_netcat "RUN COMPLETE: ${LIDMSG}"

    FIRST_SEED=$(echo $seed_ips_csv | cut -d ',' -f 1)

    # Check for a fully formed cluster *after* YCSB ran. If not, consider it as an error.
    check_cassandra_cluster_state ${FIRST_SEED} 1 1
    ERROR=$?
    update_app_errors $ERROR

    # Build space separated string with all latency metrics collected from YCSB output.
    latency_result_text=""
    for OPERATION in "${OPERATIONS[@]}"
    do
        index=$(eval echo \$$OPERATION)
        oper=$(echo $OPERATION | tr '[:upper:]' '[:lower:]')
        # this test determines if we stored anything in array entry while reading YCSB output.
        # see bash 'shell parameter expansion'
        # ${var+isset} returns 'isset' if $var is set
        # ${var+isset} returns nothing if $var is not set
        if [[ ${latency_avg_units[$index]+isset} ]]
        then
            # Let's report something as latency. We'll pick insert operations to report latency.
	    # The other metrics will still be reported as normal.
	    if [ "${oper}" == "insert" ] ; then
		    latency_result_text="$latency_result_text latency:${latency_avg[$index]}:${latency_avg_units[$index]}"
	    fi
            latency_result_text="$latency_result_text ${oper}_avg_latency:${latency_avg[$index]}:${latency_avg_units[$index]}"
            latency_result_text="$latency_result_text ${oper}_min_latency:${latency_min[$index]}:${latency_min_units[$index]}"
            latency_result_text="$latency_result_text ${oper}_max_latency:${latency_max[$index]}:${latency_max_units[$index]}"
            latency_result_text="$latency_result_text ${oper}_95_latency:${latency_95[$index]}:${latency_95_units[$index]}"
            latency_result_text="$latency_result_text ${oper}_99_latency:${latency_99[$index]}:${latency_99_units[$index]}"
        fi
    done

    insert_operations=$(cat $OUTPUT_FILE | grep Operations | grep INSERT | cut -d ',' -f 3 | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
    read_operations=$(cat $OUTPUT_FILE | grep Operations | grep READ | cut -d ',' -f 3 | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
    
    # Preserve old behavior:  Send data back to Cloudbench orchestrator even
    # if no latency data was collected.    
    CB_REPORT_CLI_PARMS=force_conversion_us_to_ms
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_id:${LOAD_ID}:seqnum
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_level:${LOAD_LEVEL}:load
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_profile:${LOAD_PROFILE}:name
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'load_duration:${LOAD_DURATION}:sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'completion_time:$(update_app_completiontime):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'throughput:$(expr $ops):tps
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'errors:$(update_app_errors):num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'datagen_time:$(update_app_datagentime):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'datagen_size:$(update_app_datagensize):records
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'read_operations:$read_operations:num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'insert_operations:$insert_operations:num
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' 'quiescent_time:$(update_app_quiescent):sec
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' '$latency_result_text
    CB_REPORT_CLI_PARMS=$CB_REPORT_CLI_PARMS' '${SLA_RUNTIME_TARGETS}

    ~/cb_report_app_metrics.py $CB_REPORT_CLI_PARMS
    
    syslog_netcat "Exit code for \"~/cb_report_app_metrics.py $CB_REPORT_CLI_PARMS\" is $?"
}
