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

if [[ $(echo $my_role | grep -c master) -ne 0 ]]
then
    check_hadoop_cluster_state 1 1

    if [[ $? -ne 0 ]]
    then
        start_master_hadooop_services
    fi
    
    check_hadoop_cluster_state 30 10
    ERROR=$?
    update_app_errors $ERROR

    if [[ $ERROR -ne 0 ]]
    then
        syslog_netcat "Unable to start Hadoop cluster"
        exit 1
    fi
    
    create_mapreduce_history    

    setup_matrix_multiplication
    
else
    start_slave_hadoop_services
fi

syslog_netcat "Hadoop services started."
provision_application_stop
exit 0
