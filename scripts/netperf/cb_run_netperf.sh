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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

LOAD_GENERATOR_IP=$(get_my_ai_attribute load_generator_ip)
LOAD_GENERATOR_TARGET_IP=$(get_my_ai_attribute load_generator_target_ip)

netperf=$(which netperf)

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')

SEND_BUFFER_SIZE=$(get_my_ai_attribute_with_default send_buffer_size auto)
RECV_BUFFER_SIZE=$(get_my_ai_attribute_with_default recv_buffer_size auto)
CLIENT_BUFFER_SIZE=$(get_my_ai_attribute_with_default client_buffer_size auto)
SERVER_BUFFER_SIZE=$(get_my_ai_attribute_with_default server_buffer_size auto)
REQUEST_RESPONSE_SIZE=$(get_my_ai_attribute_with_default request_response_size auto)
EXTERNAL_TARGET=$(get_my_ai_attribute_with_default external_target none)

declare -A CMDLINE_START

CMDLINE_START["tcp_stream"]="-t TCP_STREAM"
CMDLINE_START["tcp_maerts"]="-t TCP_MAERTS"
CMDLINE_START["udp_stream"]="-t UDP_STREAM"
CMDLINE_START["tcp_rr"]="-t TCP_RR"
CMDLINE_START["tcp_cc"]="-t TCP_CC"
CMDLINE_START["tcp_crr"]="-t TCP_CRR"
CMDLINE_START["udp_rr"]="-t UDP_RR"

if [[ $SEND_BUFFER_SIZE != "auto" || $RECV_BUFFER_SIZE != "auto" || $CLIENT_BUFFER_SIZE != "auto" || $SERVER_BUFFER_SIZE != "auto" || $REQUEST_RESPONSE_SIZE != auto ]]
then
    PROFILE_SPECIFIC="--"
elif [ x"$LOAD_LEVEL" != x"1" ] ; then
    # Repurpose the load level for use as the packet size
    PROFILE_SPECIFIC="-- -m $LOAD_LEVEL"
else
    PROFILE_SPECIFIC=""    
fi

if [[ $(echo $LOAD_PROFILE | grep -c rr) -ne 0 ]]
then
    CMDLINE_END="-D 10 -H ${LOAD_GENERATOR_TARGET_IP} -l ${LOAD_DURATION} $PROFILE_SPECIFIC "

    if [[ $REQUEST_RESPONSE_SIZE != "auto" ]]
    then
        CMDLINE_END=$CMDLINE_END" -r "$REQUEST_RESPONSE_SIZE
    fi    
            
else
    CMDLINE_END="-D 10 -f m -H ${LOAD_GENERATOR_TARGET_IP} -l ${LOAD_DURATION} $PROFILE_SPECIFIC "
    
    if [[ $SEND_BUFFER_SIZE != "auto" ]]
    then
        CMDLINE_END=$CMDLINE_END" -s "$SEND_BUFFER_SIZE
    fi
    
    if [[ $RECV_BUFFER_SIZE != "auto" ]]
    then
        CMDLINE_END=$CMDLINE_END" -S "$RECV_BUFFER_SIZE
    fi            
fi

if [[ $CLIENT_BUFFER_SIZE != "auto" ]]
then
    CMDLINE_END=$CMDLINE_END" -s "$CLIENT_BUFFER_SIZE
fi            

if [[ $SERVER_BUFFER_SIZE != "auto" ]]
then
    CMDLINE_END=$CMDLINE_END" -S "$SERVER_BUFFER_SIZE
fi            

if [[ x"${CMDLINE_START[${LOAD_PROFILE}]}" == x ]]
then
    CMDLINE="$netperf ${CMDLINE_START["tcp_stream"]} $CMDLINE_END"
else 
    CMDLINE="$netperf ${CMDLINE_START[${LOAD_PROFILE}]} $CMDLINE_END"
fi

if [[ ${EXTERNAL_TARGET} != "none" ]]
then            
    LOAD_GENERATOR_TARGET_IP=${EXTERNAL_TARGET} 
fi

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

syslog_netcat "netperf run complete. Will collect and report the results"

if [[ $LOAD_PROFILE == "tcp_stream" || $LOAD_PROFILE == "tcp_maerts" ]]
then
    bw=$(tail -1 ${RUN_OUTPUT_FILE} | awk '{ print $5 }' | tr -d ' ')
elif [[ $LOAD_PROFILE == "udp_stream" ]]
then
    bw=$(tail -2 ${RUN_OUTPUT_FILE} | head -1 | awk '{ print $4 }' | tr -d ' ')
else
    tp=$(tail -2 ${RUN_OUTPUT_FILE} | head -1 | awk '{ print $6 }' | tr -d ' ')
fi

~/cb_report_app_metrics.py \
throughput:$tp:tps \
bandwidth:$bw:Mbps \
$(common_metrics)    
    
unset_load_gen

exit 0
