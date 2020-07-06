#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_hadoop_common.sh

function check_spark_cluster_state {
    ATTEMPTS=$1
    INTERVAL=$2

    if [[ $ATTEMPTS -eq 1 && $INTERVAL -eq 1 ]]
    then
        QUICK_CHECK=1
    else
        QUICK_CHECK=0
    fi
    
    if [[ x"$my_role" == x"sparkmaster"  ]] 
    then
        syslog_netcat "Waiting for all Workers to become available..."
    
        # Will wait 5 minutes for datanodes to start; else throw error

        log_file=$(find $SPARK_HOME/logs | grep $(hostname) | grep Master)
        TOTAL_NODES=$(echo $slave_ips_csv | awk -F"," '{print NF}')
        while [[ ${WORKERNODES_AVAILABLE} != "true" && $ATTEMPTS -gt 0 ]]
        do
            if [[ -z $log_file ]]
            then
                AVAILABLE_NODES=0
            else 
                AVAILABLE_NODES=$(cat $log_file | grep "Registering worker" | wc -l)
            fi
            DEAD_NODES=0
            REPORTED_TOTAL_NODES=$((AVAILABLE_NODES+DEAD_NODES))

            if [[ -z ${REPORTED_TOTAL_NODES} ]]
            then
                REPORTED_TOTAL_NODES=0
            fi

            if [[ -z ${AVAILABLE_NODES} ]]
            then
                AVAILABLE_NODES=0
            fi            
                                    
            if [[ ${AVAILABLE_NODES} -ne 0 && z${AVAILABLE_NODES} == z${TOTAL_NODES} ]]
            then
                WORKERNODES_AVAILABLE="true"
                syslog_netcat "...All Workers (${TOTAL_NODES}) available."
                break
            else
                WORKERNODES_AVAILABLE="false"
                syslog_netcat "Number of workers available is ${AVAILABLE_NODES} (out of $TOTAL_NODES). Will sleep $INTERVAL seconds and attempt $ATTEMPTS more times."
            fi
    
            ((ATTEMPTS=ATTEMPTS-1))
    
            sleep $INTERVAL
        done

        if [[ "$ATTEMPTS" -eq 0 ]]
        then
            if [[ $QUICK_CHECK -eq 0 ]]
            then
                syslog_netcat "Timeout Error waiting for workers to start. ${AVAILABLE_NODES} of ${TOTAL_NODES} are live. - NOK"
            else
                syslog_netcat "Spark cluster not formed yet."
            fi
            return 1

        fi
        
        return 0

    fi
}
export -f check_spark_cluster_state


if [[ $(echo $my_role | grep -c master) -ne 0 ]]
then
    
    mkdir $SPARK_HOME/logs
    
    check_spark_cluster_state 1 1

    cd $SPARK_HOME
    ./sbin/start-all.sh
    
    #check_hadoop_cluster_state 30 10
    check_spark_cluster_state 2 2 
    ERROR=$?
    update_app_errors $ERROR

    if [[ $ERROR -ne 0 ]]
    then
        syslog_netcat "Unable to start Spark cluster"
        exit 1
    fi
    
fi

syslog_netcat "Spark services started."
provision_application_stop
exit 0
