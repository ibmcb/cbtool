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

START=`provision_application_start`

MLG_HOME=~/3rd_party/mlgsrc
eval MLG_HOME=${MLG_HOME}

CBUSERLOGIN=`get_my_ai_attribute login`

sudo touch $MLG_HOME/run1.log
sudo chown ${CBUSERLOGIN}:${CBUSERLOGIN} $MLG_HOME/run1.log
sudo touch $MLG_HOME/run2.log
sudo chown ${CBUSERLOGIN}:${CBUSERLOGIN} $MLG_HOME/run2.log

NR_CPUS=`cat /proc/cpuinfo | grep processor | wc -l`

syslog_netcat "Compiling MLG"
cd ${MLG_HOME}
make clean
make
syslog_netcat "MLG compiled - OK"
provision_application_stop $START
exit 0
