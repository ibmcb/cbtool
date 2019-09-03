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

START=`provision_application_start`

SLURM_CONFIG_SOURCE_DIR=~/ubuntu-slurm
eval SLURM_CONFIG_SOURCE_DIR=${SLURM_CONFIG_SOURCE_DIR}

SLURM_CPU_PER_NODE=$(get_my_ai_attribute_with_default slurm_cpu_per_node 2)
SLURM_MEMORY_PER_NODE=$(get_my_ai_attribute_with_default slurm_memory_per_node 3072)
SLURM_DISK_PER_NODE=$(get_my_ai_attribute_with_default slurm_disk_per_node 8192)
    
sudo ln -s /etc/slurm-llnl /etc/slurm
sudo ln -s /usr/lib/x86_64-linux-gnu/slurm-wlm /usr/lib/slurm

sudo mkdir -p /etc/slurm/prolog.d /etc/slurm/epilog.d /var/spool/slurm/ctld /var/spool/slurmd /var/spool/slurm/d /var/log/slurm         

sudo cp $SLURM_CONFIG_SOURCE_DIR/slurm.conf /etc/slurm/

sudo cp $SLURM_CONFIG_SOURCE_DIR/slurmdbd.conf /etc/slurm/

sudo chown slurm:slurm /etc/slurm /var/spool/slurm/ctld /var/spool/slurmd /var/spool/slurm/d /var/log/slurm

sudo sed -i 's/^#.*OPTIONS=/OPTIONS=/g' /etc/default/munge
sudo sed -i 's^PidFile=.*^PidFile=/var/run/slurm-llnl/slurmdbd.pid^g' /etc/slurm/slurmdbd.conf

sudo sed -i 's^SlurmctldPidFile=.*^SlurmctldPidFile=/var/run/slurm-llnl/slurmctld.pid^g' /etc/slurm/slurm.conf
sudo sed -i 's^SlurmdPidFile=.*^SlurmdPidFile=/var/run/slurm-llnl/slurmd.pid^g' /etc/slurm/slurm.conf

sudo sed -i 's^SlurmctldLogFile=.*^SlurmctldLogFile=/var/log/slurm/slurmctld.log^g' /etc/slurm/slurm.conf
sudo sed -i 's^SlurmdLogFile=.*^SlurmdLogFile=/var/log/slurm/slurmd.log^g' /etc/slurm/slurm.conf

sudo ln -s /usr/lib/x86_64-linux-gnu/slurm-wlm /usr/lib/slurm
sudo ln -s /lib/x86_64-linux-gnu/libpthread.so.0 /usr/lib/x86_64-linux-gnu/slurm-wlm/libpthread.so.0
sudo ln -s /lib/x86_64-linux-gnu/libc.so.6 /usr/lib/x86_64-linux-gnu/slurm-wlm/libc.so.6

sudo bash -c "echo -n \"${my_ai_name}\" | sha512sum | cut -d' ' -f1 >/etc/munge/munge.key"

SERVICES[1]="mysql"
SERVICES[2]="mysqld"

linux_distribution

if [[ ${my_role} == "slurmcontroller" ]]
then
    sudo mysql -u root < ~/mariadb_list_database.sql | grep slurm_acct_db  >/dev/null 2>&1        
    if [[ $? -ne 0 ]]
    then
        service_restart_enable ${SERVICES[${LINUX_DISTRO}]}        
        syslog_netcat "Creating slurmdb on MySQL server running on ${SHORT_HOSTNAME}" 
        sudo mysql -u root < ~/mariadb_create_database.sql
        if [[ $? -eq 0 ]]
        then
            syslog_netcat "slurmdb successfully created on MySQL server running on ${SHORT_HOSTNAME}" 
        fi
    fi
fi

syslog_netcat "Updating \"slurm.conf\"..."
sudo sed -i "s/ClusterName=.*/ClusterName=$my_ai_name/g" /etc/slurm/slurm.conf
sudo sed -i "s/ControlMachine=.*/ControlMachine=$(get_hostnames_from_role slurmcontroller)/g" /etc/slurm/slurm.conf
sudo sed -i '/GresTypes=gpu/d' /etc/slurm/slurm.conf
sudo sed -i '/DefMemPerNode=64000/d' /etc/slurm/slurm.conf    
sudo sed -i '/NodeName=linux1 Gres=gpu:8 CPUs=80 Sockets=2 CoresPerSocket=20 ThreadsPerCore=2 RealMemory=515896 State=UNKNOWN/d' /etc/slurm/slurm.conf
sudo sed -i '/PartitionName=debug Nodes=ALL Default=YES MaxTime=INFINITE State=UP/d' /etc/slurm/slurm.conf
sudo bash -c "echo \"PartitionName=${my_ai_name}p1 Nodes=ALL Default=YES MaxTime=INFINITE State=UP\" >> /etc/slurm/slurm.conf"
for cn in $(get_hostnames_from_role slurmcompute)
do
    sudo bash -c "echo \"Nodename=$cn CPUs=$SLURM_CPU_PER_NODE RealMemory=$SLURM_MEMORY_PER_NODE TmpDisk=$SLURM_DISK_PER_NODE\" >> /etc/slurm/slurm.conf"
done

sudo bash -c "echo \"CgroupAutomount=yes\" > /etc/slurm/cgroup.conf"
sudo bash -c "echo \"ConstrainCores=yes\" >> /etc/slurm/cgroup.conf"

exit 0