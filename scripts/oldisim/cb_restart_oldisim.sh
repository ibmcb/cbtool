#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

START=`provision_application_start`

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

syslog_netcat "Start setup for oldisim on ${SHORT_HOSTNAME}"

OLDISIM_DIR=$(get_my_ai_attribute_with_default oldisim_dir ~/oldisim)
eval OLDISIM_DIR=${OLDISIM_DIR}

OPTS_OLDISIMBIN=''
if [[ ${my_role} == "oldisimleaf" ]]
then 
    ACTUAL_OLDISIMBIN="LeafNode"
fi

if [[ ${my_role} == "oldisimroot" ]]
then 
    ACTUAL_OLDISIMBIN="ParentNode"
    for node in $(get_ips_from_role oldisimleaf)
    do
        OPTS_OLDISIMBIN=${OPTS_OLDISIMBIN}" --leaf $node"
    done
fi

if [[ ${my_role} == "oldisimlb" ]]
then 
    ACTUAL_OLDISIMBIN="LoadBalancerNode"
    for node in $(get_ips_from_role oldisimroot)
    do
        OPTS_OLDISIMBIN=${OPTS_OLDISIMBIN}" --parent $node"
    done
fi

if [[ ${my_role} == "oldisimdriver" ]]
then 
    ACTUAL_OLDISIMBIN="DriverNode"
    for node in $(get_ips_from_role oldisimroot)
    do
        OPTS_OLDISIMBIN=${OPTS_OLDISIMBIN}" --server $node"
    done
fi

cd ${OLDISIM_DIR}
scons -j12
    
ACTUAL_OLDISIMBIN_FULL_PATH=${OLDISIM_DIR}/release/workloads/search/${ACTUAL_OLDISIMBIN}
CMDLINE="$ACTUAL_OLDISIMBIN_FULL_PATH $OPTS_OLDISIMBIN"
sudo ps aux | grep -v grep | grep ${ACTUAL_OLDISIMBIN_FULL_PATH}
if [[ $? -ne 0 ]]
then
    sudo tmux kill-session -t OLDISIM
    sudo tmux new -d -s OLDISIM
    syslog_netcat "Executing $CMDLINE..."    
    sudo tmux send-keys -t OLDISIM "$CMDLINE" Enter
    sleep 5
fi

sudo ps aux | grep -v grep | grep ${ACTUAL_OLDISIMBIN_FULL_PATH}
if [[ $? -ne 0 ]]
then
    syslog_netcat "Setup for oldisim on ${SHORT_HOSTNAME} Failed! - NOK"    
    exit 1
fi

syslog_netcat "Setup for oldisim on ${SHORT_HOSTNAME} - OK"
provision_application_stop $START
exit 0