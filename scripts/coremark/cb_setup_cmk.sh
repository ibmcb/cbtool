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

COREMARK_HOME=~/3rd_party/_coremark-1.0
eval COREMARK_HOME=${COREMARK_HOME}

CBUSERLOGIN=`get_my_ai_attribute login`

sudo touch $COREMARK_HOME/run1.log
sudo chown ${CBUSERLOGIN}:${CBUSERLOGIN} $COREMARK_HOME/run1.log
sudo touch $COREMARK_HOME/run2.log
sudo chown ${CBUSERLOGIN}:${CBUSERLOGIN} $COREMARK_HOME/run2.log

sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${COREMARK_HOME}

check_container 
    
if [[ $IS_CONTAINER -eq 1 ]]
then
    NR_CPUS=`echo $(get_my_vm_attribute size) | cut -d '-' -f 1`
else 
    NR_CPUS=`cat /proc/cpuinfo | grep processor | wc -l`
fi
THREADS_PER_CPU=`get_my_ai_attribute_with_default threads_per_cpu 2`
let NR_THREADS=${NR_CPUS}*${THREADS_PER_CPU}

syslog_netcat "Configuring coremark to run with ${NR_THREADS} threads (${THREADS_PER_CPU} threads per CPU)"
cd ${COREMARK_HOME}
rm -rf ${COREMARK_HOME}/coremark.exe

if [[ $(cat Makefile | grep -c lpthread) -eq 0 ]]
then
    sudo sed -i 's/CFLAGS +=/CFLAGS += -lpthread/g' Makefile
fi

COMMON_PARMS="PORT_DIR=linux ITERATIONS=100 REBUILD=1"

make "LDFLAGS=-L /lib64 -l pthread XCFLAGS=-DMULTITHREAD=${NR_THREADS} -DUSE_PTHREAD" $COMMON_PARMS

if [[ ! -f ${COREMARK_HOME}/coremark.exe ]]
then
	syslog_netcat "Coremark compilation failed, trying again, omiting LDFLAGS"
	make XCFLAGS="-DMULTITHREAD=${NR_THREADS} -DUSE_PTHREAD" $COMMON_PARMS
fi

if [[ ! -f ${COREMARK_HOME}/coremark.exe ]]
then
	syslog_netcat "Coremark compilation failed, trying again, with DUSE_FORK"	
	make XCFLAGS="-DMULTITHREAD=${NR_THREADS} -DUSE_FORK=1" $COMMON_PARMS
fi

if [[ ! -f ${COREMARK_HOME}/coremark.exe ]]
then
    syslog_netcat "Coremark configuration (compilation) failed - NOK"
    exit 1
fi

sudo ln -s ${COREMARK_HOME}/coremark.exe /usr/local/bin/coremark
syslog_netcat "Coremark configured - OK"
provision_application_stop $START
exit 0