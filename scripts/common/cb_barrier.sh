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

#source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

#####################################################
# barrier to ensure all AIs start/stop at roughly the
# same time
#####################################################
operation=$1

declare -A PARM

sync_counter=`get_my_ai_attribute sync_counter_name`
sync_counter=`echo ${sync_counter} | tr '[:upper:]' '[:lower:]'`
if [[ x"${sync_counter}" == x || x"${sync_counter}" == x"false" ]]
then
    syslog_netcat "No synchronization counter was specified, will start load asynchronously"
else
    syslog_netcat "Synchronization counter specified (${sync_counter}), will ${operation} load synchronously"
    barrier_channel=`get_my_ai_attribute sync_channel_name`
    barrier_value=`get_my_ai_attribute concurrent_ais`

	syslog_netcat "Checking counter and optional subcribe for \"go\" message on channel \"${barrier_channel}\""

	# The python utility needs to both lock and increment.
	subscribeai ${barrier_channel} go ${sync_counter} ${barrier_value}
	syslog_netcat "Check and subscribe complete."

	# This 'PARM' thing sounds like a nice idea, but in order to fix the race condition on counter_value,
    # we have to lock access to this variable in python (cb_subscribe.py).
    # So, this 'PARM' feature below will just have to wait for another day.
    #counter_value=`inter_ai_get_counter ${sync_counter}`
    #if [[ x"${operation}" == x"start" ]]
    #then
    #    specific_parameters=`get_my_ai_attribute specific_parameters`
    #    if [[ x"$specific_parameters" == x ]]
    #    then
    #        syslog_netcat "No specific parameters for this AI"
    #    else
    #        paramater_list=`echo ${specific_parameters} | tr '[:upper:]' '[:lower:]'`
    #        parameter_list=`echo ${specific_parameters} | sed s/':'/'\n'/g`
    #        counter=1
    #        for parameter in ${parameter_list}
    #        do
    #            syslog_netcat "Using parameter ${parameter}${counter_value}"
    #            PARM[${counter}]=`get_my_ai_attribute ${parameter}${counter_value}`
    #            syslog_netcat "${parameter}${counter_value} is ${PARM[${counter}]}"
    #            counter=$(($counter+1))
    #        done
    #    fi
    #fi

    #if [ "$leaderstatus" == "leader" ] ; then
    #    if [[ x"${operation}" == x"start" ]]
    #    then 
    #        if [[ x"${run_counter}" == x ]]
    #        then
    #            /bin/true
    #        else
    #            run_id=`inter_ai_increment_counter ${run_counter}`
    #            syslog_netcat "Experiment run counter specified (${run_counter}). The current run id is ${run_id}" 
    #        fi
    #    fi
    #    syslog_netcat "This is the AI number ${counter_value}. Load will ${operation} synchronously now."
        #####################################################
        # very important: reset the sync counter
        #####################################################
        #x=`inter_ai_reset_counter ${sync_counter}`
		#((subscribers=$barrier_value-1))
		#syslog_netcat "Expecting $subscribers subscribers after publish..."
        #y=`publish_msg AI ${barrier_channel} go $subscribers`
		#syslog_netcat "Publish complete."
    #fi
fi
    
if [ x"${collect_from_guest}" == x"true" ]
then
    if [ x"${LOAD_ID}" == x"1" ]
    then
        syslog_netcat "Restarting gmetad for first load"
        sudo su root -l -c "pkill -9 -f gmetad"
        ${dir}/monitor-core/gmetad-python/gmetad.py -c ~/gmetad-vms.conf -d 1
    fi
fi
