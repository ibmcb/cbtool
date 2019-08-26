#!/usr/bin/env bash

#/*******************************************************************************
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
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_ycsb_common.sh

START=`provision_application_start`

CASSANDRA_REPLICATION_FACTOR=$(get_my_ai_attribute_with_default replication_factor 4)
sudo sed -i --follow-symlinks "s/REPLF/${CASSANDRA_REPLICATION_FACTOR}/g" *_create_keyspace.cassandra

FIRST_SEED=$(echo $seed_ips_csv | cut -d ',' -f 1)

check_cassandra_cluster_state ${FIRST_SEED} 1 1

provision_application_stop $START
exit 0
