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

echo $(date +%s) > /tmp/provision_generic_start
echo $(date +%s) > /tmp/quiescent_time_start
# Better way of getting absolute path instead of relative path
if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

if [[ $(echo $dir | grep -c common) -eq 1 ]]
then
    ln -sf $dir/* ~
fi
#ln -sf ~/cloudbench/jar/*.jar ~
rm -rf ~/cb_os_cache.txt

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

sudo bash -c "echo \"${my_ip_addr}   $(hostname)\" >> /etc/hosts"

syslog_netcat "Starting generic VM post_boot configuration"
linux_distribution
setup_passwordless_ssh

syslog_netcat "Relaxing all security configurations"
security_configuration

load_manager_vm_uuid=`get_my_ai_attribute load_manager_vm`

if [[ x"${my_vm_uuid}" == x"${load_manager_vm_uuid}" || x"${my_type}" == x"none" ]]
then
    syslog_netcat "Starting (AI) Log store..."
    start_syslog `get_global_sub_attribute logstore port`
    syslog_netcat "Local (AI) Log store started"
    syslog_netcat "Starting (AI) Object store..."
    start_redis ${osportnumber}
    syslog_netcat "Local (AI) Object store started"
    setup_rclocal_restarts
fi

sysctl -w vm.nr_hugepages=2800
run_dhcp_additional_nics
refresh_hosts_file
automount_data_dirs
fix_ulimit

which virsh > /dev/null 2>&1
if [[ $? -eq 0 ]]
then
    sudo virsh net-destroy default >/dev/null 2>&1
    sudo virsh net-undefine default >/dev/null 2>&1
fi

configure_firewall=$(get_my_vm_attribute configure_firewall)
if [[ $(echo $configure_firewall | tr '[:upper:]' '[:lower:]') == "true" ]]
then
    configure_firewall
fi

post_boot_executed=`get_my_vm_attribute post_boot_executed`

if [[ x"${post_boot_executed}" == x"true" ]]
then
    syslog_netcat "cb_post_boot.sh already executed on this VM"
else
    syslog_netcat "Executing \"post_boot_steps\" function"
    post_boot_steps False
    UTC_LOCAL_OFFSET=$(python -c "from time import timezone, localtime, altzone; _ulo = timezone * -1 if (localtime().tm_isdst == 0) else altzone * -1; print _ulo")
    put_my_pending_vm_attribute utc_offset_on_vm $UTC_LOCAL_OFFSET

    EXTRA_NICS_WITH_IP=$(sudo ip -o addr list | grep -Ev 'virbr|docker|tun|xenbr|lxbr|lxdbr|cni|flannel|inet6|[[:space:]]lo[[:space:]]' | grep -v [[:space:]]$my_if[[:space:]] | awk '{ print $2"-"$4}' | cut -d '/' -f 1 | sed ':a;N;$!ba;s/\n/,/g')
    if [[ ! -z $EXTRA_NICS_WITH_IP ]]
    then
        put_my_vm_attribute extra_cloud_ips $EXTRA_NICS_WITH_IP
    fi

    set_nic_mtu

    syslog_netcat "Updating \"post_boot_executed\" to \"true\""
    put_my_vm_attribute post_boot_executed true
    provision_generic_stop  
fi

syslog_netcat "Ended generic VM post_boot configuration - OK"
exit 0
