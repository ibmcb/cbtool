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
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

START=`provision_application_start`
LOAD_BALANCER_TARGET=`get_my_ai_attribute load_balancer_target_role`
LOAD_BALANCER_TARGET_PORT=`get_my_ai_attribute load_balancer_target_port`
LOAD_BALANCER_TARGET_URL=`get_my_ai_attribute load_balancer_target_url`
LOAD_BALANCER_TARGET_IPS=`get_my_ai_attribute load_balancer_target_ip`

LOAD_BALANCER_TARGET_IPS_CSV=`echo ${LOAD_BALANCER_TARGET_IPS} | sed ':a;N;$!ba;s/\n/, /g'`
LOAD_BALANCER_TARGET_IPS=`echo ${LOAD_BALANCER_TARGET_IPS} | sed -e 's/, */ /g'`

haproxy_setup $LOAD_BALANCER_TARGET_PORT "$LOAD_BALANCER_TARGET_IPS"