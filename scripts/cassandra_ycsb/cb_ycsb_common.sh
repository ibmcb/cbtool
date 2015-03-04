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

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [[ -e $dir/cb_common.sh ]]
then
    source $dir/cb_common.sh
else
    source $dir/../common/cb_common.sh
fi

declare -A token

LINUX_DISTRO=$(linux_distribution)
sudo mkdir -p /var/run/cassandra/
sudo chmod 777 /var/run/cassandra

MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`

while [[ -z $MY_IP ]] 
do
    syslog_netcat "MY IP is null"
    MY_IP=`/sbin/ifconfig eth0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tr -d '\r\n'`
    sleep 1
done

YCSB_PATH=$(get_my_ai_attribute_with_default ycsb_path ~/YCSB)
eval YCSB_PATH=${YCSB_PATH}

BACKEND_TYPE=$(get_my_ai_attribute type | sed 's/_ycsb//g')

if [[ $BACKEND_TYPE == "cassandra" ]]
then 
    CASSANDRA_DATA_DIR=$(get_my_ai_attribute_with_default cassandra_data_dir /dbstore)
    eval CASSANDRA_DATA_DIR=${CASSANDRA_DATA_DIR}

    CASSANDRA_DATA_FSTYP=$(get_my_ai_attribute_with_default cassandra_data_fstyp ext4)
    eval CASSANDRA_DATA_FSTYP=${CASSANDRA_DATA_FSTYP}

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
        
    cassandra_ips_csv=`echo ${cassandra_ips} | sed ':a;N;$!ba;s/\n/, /g'`

    seed_ips_csv=`echo ${seed_ips} | sed 's/ /,/g'`

    if [[ -z $cassandra_ips ]]
    then
        syslog_netcat "No VMs with the \"cassandra\" role have been found on this AI"
        exit 1;
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
    
    mongo_ips_csv=`echo ${mongo_ips} | sed ':a;N;$!ba;s/\n/, /g'`

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

    redis_ip=`get_ips_from_role redis`
    if [ -z $redis_ip ]
    then
        syslog_netcat "redis IP is null"
        exit 1
    fi    
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
    
    while read line
    do
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
    
    if [[ $? -gt 0 ]]
    then
        syslog_netcat "problem running ycsb prime client on $(hostname)"
        exit 1
    fi
    
    # Collect data generation time, taking care of reporting the time
    # with a minus sign in case data was not generated on this 
    # run
    if [[ -f /tmp/old_data_generation_time ]]
    then
        datagentime=-$(cat /tmp/old_data_generation_time)
    fi
    
    if [[ -f /tmp/data_generation_time ]]
    then
        datagentime=$(cat /tmp/data_generation_time)
        mv /tmp/data_generation_time /tmp/old_data_generation_time
    fi

    if [[ -f /tmp/old_data_generation_size ]]
    then
        datagensize=-$(cat /tmp/old_data_generation_size)
    fi

    if [[ -f /tmp/data_generation_size ]]
    then
        datagensize=$(cat /tmp/data_generation_size)
        mv /tmp/data_generation_size /tmp/old_data_generation_size        
    fi  

    ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
    load_level:${LOAD_LEVEL}:load \
    load_profile:${LOAD_PROFILE}:name \
    load_duration:${LOAD_DURATION}:sec \
    throughput:$(expr $ops):tps \
    latency:$(expr $latency):us \
    datagen_time:${datagentime}:sec \
    datagen_size:${datagensize}:records \
    ${SLA_RUNTIME_TARGETS}
}

function check_cluster_state {

    syslog_netcat "Waiting for all nodes to become available..."

    NODETOOLHN=$1
    ATTEMPTS=$2
    INTERVAL=$3

    counter=0
    
    while [[ $NODES_REGISTERED -ne $total_nodes && "$counter" -le "$ATTEMPTS" ]]
    do
        NODES_REGISTERED=0    
        syslog_netcat "Obtaining the node list for this Cassandra cluster..."            
        for NODEIP in $(nodetool -h ${NODETOOLHN} status | tail -n +6 | grep -v "Non-system" | awk '{ print $2 }')
        do
            if [[ $(sudo cat /etc/hosts | grep -c $NODEIP) -ne 0 ]]
            then
                NODES_REGISTERED="$(( $NODES_REGISTERED + 1 ))"
            fi            
        done

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
export -f check_cluster_state

function eager_collection {
    CMDLINE=$1
    OUTPUT_FILE=$2.run
    SLA_RUNTIME_TARGETS=$3
    
    #----------------------- Track all YCSB results  -------------------------------

    #----------------------- Total op/sec ------------------------------------------
    ops=0

    #----------------------- Current op/sec for this client ------------------------
    write_current_ops=0
    read_current_ops=0
    update_current_ops=0

    #----------------------- Tracking Latency --------------------------------------
    # <operation>_latency=average,min,max,95,99
    #-------------------------------------------------------------------------------
    write_latency=0
    read_latency=0
    update_latency=0

    #----------------------- Old tracking ------------------------------------------
    latency=0    
    
    while read line
    do
        echo $line >> $OUTPUT_FILE
    #-------------------------------------------------------------------------------
    # Need to track each YCSB Clients current operation count.
    # NEED TO:
    #       Create a variable that reports to CBTool the current operation
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
                syslog_netncat "Current Avg. Write Latency : $AVG_WRITE_LATENCY"
            fi
            
            if [[ "$line" == *UPDATE* ]]
            then
                AVG_UPDATE_LATENCY=$(echo $line | awk '{print $9}' | sed 's/^.*[^0-9]\([0-9]*\.[0-9]*\)/\1/' | rev | cut -c 2- | rev)
                syslog_netncat "Current Avg. Update Latency : $AVG_UPDATE_LATENCY"
            fi
        fi
    
        IFS=',' read -a array <<< "$line"
        if [[ ${array[0]} == *OVERALL* ]]
        then
            if [[ ${array[1]} == *Throughput* ]]
            then
                ops=${array[2]}
            fi
        fi
    
    #----------------------- Track Latency -----------------------------------------
        if [[ ${array[0]} == *UPDATE* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                update_avg_latency=${array[2]}
            fi
            
            if [[ ${array[1]} == *MinLatency* ]]
            then
                update_min_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                update_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                update_95_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *99thPercent* ]]
            then
                update_99_latency="${array[2]}"
            fi
        fi
        
        if [[ ${array[0]} == *READ* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                read_avg_latency=${array[2]}
            fi
            
            if [[ ${array[1]} == *MinLatency* ]]
            then
                read_min_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                read_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                read_95_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *99thPercent* ]]
            then
                read_99_latency="${array[2]}"
            fi
        fi
        
        if [[ ${array[0]} == *WRITE* ]]
        then
            if [[ ${array[1]} == *AverageLatency* ]]
            then
                write_avg_latency=${array[2]}
            fi
            if [[ ${array[1]} == *MinLatency* ]]
            then
                write_min_latency="${array[2]}"
            fi
            if [[ ${array[1]} == *MaxLatency* ]]
            then
                write_max_latency="${array[2]}"
            fi
            
            if [[ ${array[1]} == *95thPercent* ]]
            then
                write_95_latency="${array[2]}"
            fi
            if [[ ${array[1]} == *99thPercent* ]]
            then
                write_99_latency="${array[2]}"
            fi
        fi
    done < <($CMDLINE 2>&1)
    
    if [[ $? -gt 0 ]]
    then
        syslog_netcat "problem running ycsb prime client on $(hostname)"
        exit 1
    fi
    
    # Collect data generation time, taking care of reporting the time
    # with a minus sign in case data was not generated on this 
    # run
    if [[ -f /tmp/old_data_generation_time ]]
    then
        datagentime=-$(cat /tmp/old_data_generation_time)
    fi
    
    if [[ -f /tmp/data_generation_time ]]
    then
        datagentime=$(cat /tmp/data_generation_time)
        mv /tmp/data_generation_time /tmp/old_data_generation_time
    fi

    if [[ -f /tmp/old_data_generation_size ]]
    then
        datagensize=-$(cat /tmp/old_data_generation_size)
    fi

    if [[ -f /tmp/data_generation_size ]]
    then
        datagensize=$(cat /tmp/data_generation_size)
        mv /tmp/data_generation_size /tmp/old_data_generation_size        
    fi

    if [[ $write_avg_latency -ne 0 ]]
    then
        ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
        load_level:${LOAD_LEVEL}:load \
        load_profile:${LOAD_PROFILE}:name \
        load_duration:${LOAD_DURATION}:sec \
        throughput:$(expr $ops):tps \
        write_avg_latency:$(expr $write_avg_latency):us \
        write_min_latency:$(expr $write_min_latency):us \
        write_max_latency:$(expr $write_max_latency):us \
        write_95_latency:$(expr $write_95_latency):us \
        write_99_latency:$(expr $write_99_latency):us \
        read_avg_latency:$(expr $read_avg_latency):us \
        read_min_latency:$(expr $read_min_latency):us \
        read_max_latency:$(expr $read_max_latency):us \
        read_95_latency:$(expr $read_95_latency):us \
        read_99_latency:$(expr $read_99_latency):us \
        update_avg_latency:$(expr $update_avg_latency):us \
        update_min_latency:$(expr $update_min_latency):us \
        update_max_latency:$(expr $update_max_latency):us \
        update_95_latency:$(expr $update_95_latency):us \
        update_99_latency:$(expr $update_99_latency):us \
        datagen_time:${datagentime}:sec \
        datagen_size:${datagensize}:records \      
        ${SLA_RUNTIME_TARGETS}
    fi

    if [[ $write_avg_latency -eq 0 ]]
    then
        ~/cb_report_app_metrics.py load_id:${LOAD_ID}:seqnum \
        load_level:${LOAD_LEVEL}:load \
        load_profile:${LOAD_PROFILE}:name \
        load_duration:${LOAD_DURATION}:sec \
        throughput:$(expr $ops):tps \
        read_avg_latency:$(expr $read_avg_latency):us \
        read_min_latency:$(expr $read_min_latency):us \
        read_max_latency:$(expr $read_max_latency):us \
        read_95_latency:$(expr $read_95_latency):us \
        read_99_latency:$(expr $read_99_latency):us \
        update_avg_latency:$(expr $update_avg_latency):us \
        update_min_latency:$(expr $update_min_latency):us \
        update_max_latency:$(expr $update_max_latency):us \
        update_95_latency:$(expr $update_95_latency):us \
        update_99_latency:$(expr $update_99_latency):us \
        datagen_time:${datagentime}:sec \
        datagen_size:${datagensize}:records \      
        ${SLA_RUNTIME_TARGETS}        
    fi
}