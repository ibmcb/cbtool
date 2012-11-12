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

source ~/.bashrc
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

GMETAD_VMS=~/gmetad-vms.conf

myip=`get_my_ip_addr`
COLLECTOR_UNICAST_IP=`get_ai_attribute ${my_ai_uuid} metric_aggregator_ip`
COLLECTOR_AGGREGATOR_PORT=`get_global_sub_attribute mon_defaults collector_aggregator_port`
COLLECTOR_SUMMARIZER_PORT=`get_global_sub_attribute mon_defaults collector_summarizer_port`
COLLECTOR_VM_PORT=`get_global_sub_attribute mon_defaults collector_vm_port`
PLUGINS_DIR=~/monitor-core/gmetad-python/plugins
MAIN_PATH=~/cbtool
API_HOSTNAME=`get_global_sub_attribute api_defaults hostname`
API_PORT=`get_global_sub_attribute api_defaults port` 

#DATA_SOURCE="data_source \"127.0.0.1\" 127.0.0.1:${COLLECTOR_VM_PORT}\n"
#if [ x"${my_type}" == x"none" ]
#then
#	DATA_SOURCE+="data_source \"${myip}\" ${myip}:${COLLECTOR_VM_PORT}\n"
#else
#	for vmip in `get_vm_ips_from_ai`
#	do
#		DATA_SOURCE+="data_source \"${vmip}\" ${vmip}:${COLLECTOR_VM_PORT}\n"
#	done
#fi
#DATA_SOURCE=`echo -e $DATA_SOURCE`

cat << EOF > $GMETAD_VMS
xml_port ${COLLECTOR_AGGREGATOR_PORT}
interactive_port ${COLLECTOR_SUMMARIZER_PORT}
plugins_dir ${PLUGINS_DIR}
data_source "127.0.0.1" 127.0.0.1:${COLLECTOR_VM_PORT}
mongodb { 
        path ${MAIN_PATH}
        api http://${API_HOSTNAME}:${API_PORT}
        cloud_name ${cloudname}
}
EOF
