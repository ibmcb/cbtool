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

MPIEXECUTABLE_PATH=$(get_my_ai_attribute_with_default mpiexecutable_path /usr/lib64/openmpi/bin/)
MPILIBRARY_PATH=$(get_my_ai_attribute_with_default mpilibrary_path /usr/lib64/openmpi/lib/)

echo "export PATH=\$PATH:$MPIEXECUTABLE_PATH" >> ~/.bashrc
echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$MPILIBRARY_PATH" >> ~/.bashrc

MPIEXECUTABLE=`which mpirun` 
if [[ $? -ne 0 ]]
then
    sudo ln -s ${MPIEXECUTABLE_PATH} /usr/local/bin/mpirun
fi

FEN_IP=`get_ips_from_role FEN_HPC`
CN_IP=`get_ips_from_role CN_HPC`

syslog_netcat "fen_hpc_ip: $FEN_IP"

CN_IP_CSV=`echo ${CN_IP} | sed ':a;N;$!ba;s/\n/, /g'`
syslog_netcat "cn_hpc_ip: $CN_IP_CSV"

#grep -v "localhost\|just_for_lost" /etc/hosts |grep "fen_hpc"     |cut -d " " -f 1 > ~/cluster.hosts
#grep -v "localhost\|just_for_lost" /etc/hosts |grep "cn_hpc" |cut -d " " -f 1 >> ~/cluster.hosts

exit 0