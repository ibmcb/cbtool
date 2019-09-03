#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2019 IBM Corp.

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

service_restart_enable munge 

munge -n >/dev/null 2>&1 
if [[ $? -ne 0 ]]
then 
    syslog_netcat "Munge configuration successfully checked on ${SHORT_HOSTNAME}"
else
    syslog_netcat "Munge configuration checking failure on ${SHORT_HOSTNAME}"
fi

if [[ ${my_role} == "slurmcontroller" ]]
then
    service_restart_enable slurmdbd

    service_restart_enable slurmctld

#    sudo sacctmgr add cluster $my_ai_name -i
#    sudo sacctmgr add account compute-account description="Compute accounts" Organization=OurOrg -i
#    sudo sacctmgr create user $(whoami) account=compute-account adminlevel=None -i
else
    wait_until_port_open $(get_ips_from_role slurmcontroller) 6817 20 5
    service_restart_enable slurmd
fi

provision_application_stop

exit 0