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

# Better way of getting absolute path instead of relative path
if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi
    
# Get all parameters to connect to the datastore
cloudname=`cat ~/cb_os_parameters.txt | grep "#OSCN" | cut -d "-" -f 2`
oshostname=`cat ~/cb_os_parameters.txt | grep "#OSHN" | cut -d "-" -f 2`
osportnumber=`cat ~/cb_os_parameters.txt | grep "#OSPN" | cut -d "-" -f 2`
osdatabasenumber=`cat ~/cb_os_parameters.txt | grep "#OSDN" | cut -d "-" -f 2`
osinstance=`cat ~/cb_os_parameters.txt | grep "#OSOI" | sed 's/#OSOI-//g'`
osprocid=`echo ${osinstance} | cut -d ":" -f 1`
osmode=`cat ~/cb_os_parameters.txt | grep "#OSMO" | cut -d "-" -f 2`
my_vm_uuid=`cat ~/cb_os_parameters.txt | grep VMUUID | sed 's/#VMUUID-//g'`

RANGE=60
ATTEMPTS=3

SETUP_TIME=20

ai_mapping_file=~/ai_mapping_file.txt

PGREP_CMD=`which pgrep`
PKILL_CMD=`which pkill`
SUBSCRIBE_CMD=~/cb_subscribe.py
RSYSLOGD_CMD=/sbin/rsyslogd

NC=`which netcat` 
if [[ $? -ne 0 ]]
then
    NC=`which nc`
fi

if [ x"$PGREP_CMD" == x ] ; then
    echo "please install pgrep"
    exit 2
fi

if [ x"$PKILL_CMD" == x ] ; then
    echo "please install pkill"
    exit 2
fi

if [ x"$RSYSLOGD_CMD" == x ] ; then
    echo "please install rsyslogd"
    exit 2
fi

export PATH=$PATH:~
eval PATH=$PATH

# Test for redis-cli
if [ x"$(uname -a | grep CYGWIN)" != x ] ; then
    rediscli="$dir/redis.bat"
else
    rediscli=`which redis-cli 2>&1`
    if [ $? -gt 0 ] ; then
        echo "can't find system redis. trying to use local one..."
        rediscli=${dir}/../../binaries/common/linux/redis-cli
        $rediscli -v
        if [ $? -gt 0 ] ; then
            exit 2
            echo "please install the redis command line"
        fi
        echo "local redis worked. moving on now."
    fi
fi

SCRIPT_NAME=$(echo "$BASH_SOURCE" | sed -e "s/.*\///g")

function check_container {
    if [[ $(sudo cat /proc/1/cgroup | grep -c docker) -ne 0 ]]
    then
        export IS_CONTAINER=1
        if [[ -z $LC_ALL ]]
        then 
            export LC_ALL=C
        fi
        export NR_CPUS=`echo $(get_my_vm_attribute size) | cut -d '-' -f 1`                  
    else
        export IS_CONTAINER=0
        export NR_CPUS=`cat /proc/cpuinfo | grep processor | wc -l`                
    fi
}
export -f check_container
    
function check_gpu_cuda {    
    syslog_netcat "Check if cuda is installed..."
    sudo ls -la /usr/local/cuda
    if [[ $? -eq 0 ]]
    then
        syslog_netcat "The cuda directory (/usr/local/cuda) was found"
        syslog_netcat "Check if GPUs are present"
        sudo bash -c "cd /usr/local/cuda/samples/1_Utilities/deviceQuery && make && ./deviceQuery"
        if [[ $? -eq 0 ]]
        then
            syslog_netcat "GPU driver modules are loaded"
            export IS_GPU=1
        else
            syslog_netcat "GPU driver modules cannot be found"
            export IS_GPU=0            
        fi
    else
        syslog_netcat "The cuda directory does not exist"
        export IS_GPU=0
    fi
}
export -f check_gpu_cuda
    
function linux_distribution {
    IS_UBUNTU=$(cat /etc/*release | grep -c "Ubuntu")

    if [[ ${IS_UBUNTU} -ge 1 ]]
    then
        export LINUX_DISTRO=1
    fi
    
    IS_REDHAT=$(cat /etc/*release | grep -c "Red Hat\|CentOS\|Fedora")    
    if [[ ${IS_REDHAT} -ge 1 ]]
    then
        export LINUX_DISTRO=2
    fi
    
    check_container
}
export -f linux_distribution

function service_stop_disable {
    #1 - service list (space-separated list)

    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi
    
    for s in $*
    do
        if [[ ${LINUX_DISTRO} -eq 2 ]]
        then
            if [[ $(sudo sv status $s 2>&1 | grep -v "fail:" | grep -c $s) -ne 0 ]]
            then
                STOP_COMMAND="sudo sv stop $s"
                DISABLE_COMMAND="sudo touch /etc/service/$s/down"
            elif [[ $(sudo systemctl | grep -c $s) -ne 0 ]]
            then
                STOP_COMMAND="sudo systemctl stop $s"
                DISABLE_COMMAND="sudo systemctl disable $s"
            else
                STOP_COMMAND="sudo service $s stop"
                DISABLE_COMMAND="sudo chkconfig $s off >/dev/null 2>&1"
            fi
        else
            if [[ $(sudo sv status $s 2>&1 | grep -v "fail:" | grep -c $s) -ne 0 ]]
            then
                STOP_COMMAND="sudo sv stop $s"
                DISABLE_COMMAND="sudo touch /etc/service/$s/down"
            elif [[ $(sudo systemctl | grep -c $s) -ne 0 ]]
            then
                STOP_COMMAND="sudo systemctl stop $s"
                DISABLE_COMMAND="sudo systemctl disable $s"
            else
                STOP_COMMAND="sudo service $s stop"
                if [[ -f /etc/init/$s.conf ]]
                then
                    DISABLE_COMMAND="sudo sh -c 'echo manual > /etc/init/$s.override'"
                else
                    DISABLE_COMMAND="sudo update-rc.d -f $s remove"
                fi                    
            fi
        fi

        syslog_netcat "Stopping service \"${s}\" with command \"$STOP_COMMAND\"..."       
        bash -c "$STOP_COMMAND"

        syslog_netcat "Disabling service \"${s}\" with command \"$DISABLE_COMMAND\"..."               
        bash -c "$DISABLE_COMMAND"
    done
    /bin/true
}
export -f service_stop_disable
    
function service_restart_enable {
    #1 - service list (space-separated list)
    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi
    
    for s in $*
    do            
        if [[ ${LINUX_DISTRO} -eq 2 ]]
        then
            if [[ $(sudo sv status $s 2>&1 | grep -v "fail:" | grep -c $s) -ne 0 ]]
            then
                START_COMMAND="sudo sv restart $s"
                ENABLE_COMMAND="sudo rm /etc/service/$s/down"            
            elif [[ $(sudo systemctl 2>&1 | grep -c $s) -ne 0 && $(sudo find /etc/systemd 2>&1 | grep -c $s) -ne 0 ]]
            then
                START_COMMAND="sudo systemctl restart $s"
                ENABLE_COMMAND="sudo systemctl enable $s"
            else
                START_COMMAND="sudo service $s restart"
                ENABLE_COMMAND="sudo chkconfig $s on >/dev/null 2>&1"
            fi
        else
            if [[ $(sudo sv status $s 2>&1 | grep -v "fail:" | grep -c $s) -ne 0 ]]
            then
                START_COMMAND="sudo sv restart $s"
                ENABLE_COMMAND="sudo rm /etc/service/$s/down"            
            elif [[ $(sudo systemctl 2>&1 | grep -c $s) -ne 0 ]]
            then
                START_COMMAND="sudo systemctl restart $s"
                ENABLE_COMMAND="sudo systemctl enable $s"
            else
                START_COMMAND="sudo service $s restart"
                if [[ -f /etc/init/$s.conf ]]
                then
                    ENABLE_COMMAND="sudo rm -rf /etc/init/$s.override"            
                else
                    ENABLE_COMMAND="sudo update-rc.d -f $s defaults"
                fi
            fi
        fi
    
        counter=1
        ATTEMPTS=7
        while [ "$counter" -le "$ATTEMPTS" ]
        do
            syslog_netcat "Restarting service \"${s}\", with command \"$START_COMMAND\", attempt ${counter} of ${ATTEMPTS}..."            
            bash -c "$START_COMMAND"
            if [[ $? -eq 0 ]]
            then
                syslog_netcat "Service \"$s\" was successfully restarted"
                syslog_netcat "Enabling service \"${s}\", with command \"$ENABLE_COMMAND\"..."   
                bash -c "$ENABLE_COMMAND"
                break
            else
                sleep 5
                counter="$(( $counter + 1 ))"
            fi
        done
    
        if [[ "${counter}" -ge "$ATTEMPTS" ]]
        then
            syslog_netcat "Service \"${s}\" failed to restart after ${ATTEMPTS} attempts"
            exit 1
        fi
    done
    
    /bin/true
}
export -f service_restart_enable

function retriable_execution {
        COMMAND=$1
        non_cacheable=$2

        ECODE=1
        ATTEMPT=0
        OUTERR=1
        EXPRESSION=`echo $1 | cut -d ' ' -f 9-15`

        if [[ -f ~/cb_os_cache.txt && ${non_cacheable} -eq 0 ]]; then
            OUTPUT=`cat ~/cb_os_cache.txt | grep "${EXPRESSION}" -m 1 | awk '{print $NF}'`
        fi

        if [ x"${OUTPUT}" == x ]; then
            can_cache=1
        else
            can_cache=0
        fi

        if [[ x"${OUTPUT}" == x || x"${osmode}" != x"scalable" ]]; then
            while [[ (( ${ECODE} -ne 0 || ${OUTERR} -eq 1 )) && ${ATTEMPT} -le ${ATTEMPTS} ]]
            do
                OUTPUT=`${COMMAND}`
                ECODE=$?
                OUTERR=`echo ${OUTPUT} | grep -c "ERR"`
                SLEEP_TIME=$(( $RANDOM % ${RANGE} ))
                SLEEP_TIME=$(( ${SLEEP_TIME} * ${ATTEMPT} ))
                sleep $SLEEP_TIME
                ATTEMPT=$(( ${ATTEMPT} + 1 ))
            done
        fi

    if [[ x"${OUTPUT}" != x && ${can_cache} -eq 1 && ${non_cacheable} -eq 0 ]]; then
        echo "${EXPRESSION} ${OUTPUT}" >> ~/cb_os_cache.txt
        fi

        echo $OUTPUT
}

function get_time {
        time=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber time" 1`
        echo -n $time | cut -d " " -f 1
}

function get_vm_uuid_from_ip {
    uip=$(echo $1 | cut -d '-' -f 1)
    fqon=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber get ${osinstance}:VM:TAG:CLOUD_IP:${uip}" 0`
    echo $fqon | cut -d ':' -f 4
}

function get_hash {
    object_type=$1
    key_name=$2
    attribute_name=`echo $3 | tr '[:upper:]' '[:lower:]'`
    non_cacheable=$4
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber hget ${osinstance}:${object_type}:${key_name} ${attribute_name}" ${non_cacheable} 
}

function get_vm_attribute {
    vmuuid=$1
    attribute=`echo $2 | tr '[:upper:]' '[:lower:]'`
    get_hash VM ${vmuuid} ${attribute} 0
}

function get_my_vm_attribute {
    attribute=`echo $1 | tr '[:upper:]' '[:lower:]'`
    get_hash VM ${my_vm_uuid} ${attribute} 0
}
export -f get_my_vm_attribute

function get_my_vm_attribute_with_default {
    NAME=$1
    DEFAULT=$2
    TEST="`get_my_vm_attribute $NAME`"

    if [ x"$TEST" != x ] ; then
        echo "$TEST"
    elif [ x"$DEFAULT" != x ] ; then
        echo "$DEFAULT"
    else
        syslog_netcat "Configuration error: Value for key ($NAME) not available online or offline."
        exit 1
    fi
}
export -f get_my_vm_attribute_with_default

function blowawaypids {
    pids="$(pgrep -f "$1")"
    for pid in $pids ; do
        if [ $pid != $$ ] && [ $pid != $PPID ] ; then
            sudo kill -9 $pid
        fi
    done
}
export -f blowawaypids

function wait_until_port_open {
    #1 - host name
    #2 - port number
    #3 - number of attempts
    #4 - time between attempts

    counter=1
    ATTEMPTS=${3}
    while [ "$counter" -le "$ATTEMPTS" ]
    do
        ${NC} -z -w 3 ${1} ${2}
        if [[ $? -eq 0 ]]
        then
            syslog_netcat "Port ${2} on host ${1} was found open after ${counter} attempts"
            return 0
        fi
        sleep ${4}
        counter="$(( $counter + 1 ))"
    done
    syslog_netcat "Port ${2} on host ${1} was NOT found open after ${counter} attempts!"
    return 1
}
export -f wait_until_port_open

function be_open_or_die {
    host=$1
    port=$2
    proto=$3
    delay=$4
    tries=$5
    nmapcount=0
    while [ $nmapcount -lt $tries ] ; do
        $dir/cb_nmap.py $host $port $proto
        if [ $? -eq 0 ] ; then
            echo "port checker: host $host is open."
            return
        fi
        ((nmapcount=nmapcount+1))
        if [ $nmapcount -lt $tries ] ; then
            echo "port checker: host $host port not open yet..."
            sleep $delay 
        fi
    done
    echo "port checker: host $host port $port could not be reached. Dying now."
    exit 1
}
export -f be_open_or_die

# This is the first redis function to execute during post boot.
# Sometimes the VPN comes up to slow, so, if it doesn't work, then
# we need to try again.
be_open_or_die $oshostname $osportnumber tcp 30 5
    
my_role=`get_my_vm_attribute role`
my_ai_name=`get_my_vm_attribute ai_name`
my_ai_uuid=`get_my_vm_attribute ai`
my_base_type=`get_my_vm_attribute base_type`
my_cloud_model=`get_my_vm_attribute model`
my_ip_addr=`get_my_vm_attribute cloud_ip`

function get_attached_volumes {
    # Wierdo clouds, like Amazon expose naming schemes like `/dev/nvme0n1p1` for the root volume.
    # So, we need a beefier regex.
    ROOT_VOLUME=$(sudo mount | grep "/ " | cut -d ' ' -f 1 | sed "s/\([a-z]*[0-9]\+\|[0-9]\+\)$//g")
    SWAP_VOLUME=$(sudo swapon -s | grep dev | cut -d ' ' -f 1 | tr -d 0-9)
    if [[ -z ${SWAP_VOLUME} ]]
    then
        SWAP_VOLUME="NONE"
    fi
    VOLUME_LIST=$(sudo fdisk -l 2>&1 | grep Disk | grep bytes | grep -v ${ROOT_VOLUME} | grep -v ${SWAP_VOLUME} | awk '{if($5>1073741824)print $2, $5}' | head -n1 | cut -d ':' -f 1)
    if [[ -z ${VOLUME_LIST} ]]
    then
        VOLUME_LIST="NONE"
    fi
    echo $VOLUME_LIST
}
export -f get_attached_volumes

function check_filesystem {
    if [[ $(sudo blkid ${1} | grep -c TYPE) -eq 0 ]]
    then
        echo "none"
    else
        echo $(sudo blkid ${1} | grep TYPE | cut -d ' ' -f 3 | sed 's/TYPE=//g' | sed 's/"//g' | tr -d '\040\011\012\015')
    fi
}
export -f check_filesystem

function mount_filesystem_on_volume {
    MOUNTPOINT_DIR=$1
    FILESYS_TYPE=$2
    MOUNTPOINT_OWNER=$3
    VOLUME=$4

    if [[ -z $MOUNTPOINT_DIR ]]
    then
        syslog_netcat "No mountpoint specified. Bypassing mounting"
        return 1
    fi
    
    if [[ -z $FILESYS_TYPE ]]
    then
        FILESYS_TYPE=ext4
    fi
    
    if [[ -z $VOLUME ]]
    then        
        VOLUME=$(get_attached_volumes)
    else
        if [[ $(sudo fdisk -l | grep -c $VOLUME) -eq 0 ]]
        then
            VOLUME="NONE"
        fi
    fi

    sudo mkdir -p $MOUNTPOINT_DIR

    if [[ -z $MOUNTPOINT_OWNER  ]]
    then
        MOUNTPOINT_OWER=${my_login_username}
    fi
    
    sudo chown -R ${MOUNTPOINT_OWNER}:${MOUNTPOINT_OWNER} $MOUNTPOINT_DIR
        
    if [[ $VOLUME != "NONE" ]]
    then
        
        if [[ $(sudo mount | grep $VOLUME | grep -c $MOUNTPOINT_DIR) -eq 0 ]]
        then
            syslog_netcat "Setting ${FILESYS_TYPE} storage ($MOUNTPOINT_DIR) on volume $VOLUME...."

            if [[ $(check_filesystem $VOLUME) == "none" ]]
            then
                syslog_netcat "Creating $FILESYS_TYPE filesystem on volume $VOLUME"
                sudo mkfs.$FILESYS_TYPE -F $VOLUME
            fi
            
            syslog_netcat "Making $FILESYS_TYPE filesystem on volume $VOLUME accessible through the mountpoint ${MOUNTPOINT_DIR}"
            sudo mount $VOLUME ${MOUNTPOINT_DIR}
            
            if [[ $? -ne 0 ]]
            then
                syslog_netcat "Error while mounting $FILESYS_TYPE filesystem on volume $VOLUME on mountpoint ${MOUNTPOINT_DIR} - NOK" 
                exit 1
            fi
        else
            syslog_netcat "${FILESYS_TYPE} storage ($MOUNTPOINT_DIR) on volume $VOLUME is already setup!"            
        fi
        
        sudo chown -R ${MOUNTPOINT_OWER}:${MOUNTPOINT_OWER} $MOUNTPOINT_DIR
    fi
    return 0
}
export -f mount_filesystem_on_volume

function mount_filesystem_on_memory {

    RAMDEVICE=/dev/ram0
    
    MOUNTPOINT_DIR=$1
    FILESYS_TYPE=$2
    MEMORY_DISK_SIZE=$3
    MOUNTPOINT_OWNER=$4

    if [[ -z $MOUNTPOINT_DIR ]]
    then
        syslog_netcat "No mountpoint specified. Bypassing mounting"
        return 1
    fi    

    if [[ -z $FILESYS_TYPE ]]
    then
        syslog_netcat "No filesystem type specified. Bypassing mounting"
        return 1
    fi    

    if [[ -z $MEMORY_DISK_SIZE ]]
    then
        syslog_netcat "No memory disk size specified. Bypassing mounting"
        return 1
    fi    

    if [[ -z $MOUNTPOINT_OWNER  ]]
    then
        MOUNTPOINT_OWER=${my_login_username}
    fi
    
    sudo mkdir -p $MOUNTPOINT_DIR

    sudo chown -R ${MOUNTPOINT_OWER}:${MOUNTPOINT_OWER} $MOUNTPOINT_DIR
                    
    if [[ $FILESYS_TYPE == "tmpfs" ]]
    then
        if [[ $(sudo mount | grep $FILESYS_TYPE | grep -c $MOUNTPOINT_DIR) -eq 0 ]]
        then        
            syslog_netcat "Making tmpfs filesystem on accessible through the mountpoint ${MOUNTPOINT_DIR}..."
            sudo mount -t tmpfs -o size=${MEMORY_DISK_SIZE},noatime,nodiratime tmpfs $MOUNTPOINT_DIR
        else
            syslog_netcat "A tmpfs filesystem is already accessible through the mountpoint ${MOUNTPOINT_DIR}!"
        fi            
    else
        if [[ $(sudo mount | grep $RAMDEVICE | grep -c $MOUNTPOINT_DIR) -eq 0 ]]
        then                
            syslog_netcat "Making $FILESYS_TYPE filesystem on ram disk $RAMDEVICE accessible through the mountpoint ${MOUNTPOINT_DIR}..."
            if [[ $(check_filesystem $RAMDEVICE) == "none" ]]
            then
                syslog_netcat "Creating $FILESYS_TYPE filesystem on volume $VOLUME"
                sudo mkfs.ext4 -F $RAMDEVICE
            fi            
            sudo mount $RAMDEVICE $MOUNTPOINT_DIR
        else
            syslog_netcat "An ext4 filesystem on ramdisk $RAMDEVICE is accessible through the mountpoint ${MOUNTPOINT_DIR}!"            
        fi    
    fi

    sudo chown -R ${MOUNTPOINT_OWER}:${MOUNTPOINT_OWER} $MOUNTPOINT_DIR

    return 0
}
export -f mount_filesystem_on_memory

function mount_remote_filesystem {
    MOUNTPOINT_DIR=$1
    FILESYS_TYPE=$2
    FILESERVER_IP=$3
    FILESERVER_PATH=$4
    
    if [[ -z $MOUNTPOINT_DIR ]]
    then
        syslog_netcat "No mountpoint specified. Bypassing mounting"
        return 1
    fi    

    if [[ -z $FILESERVER_IP ]]
    then
        syslog_netcat "No fileserver IP specified. Bypassing mounting"
        return 1
    fi            
                        
    sudo mkdir -p $MOUNTPOINT_DIR

    sudo chown -R ${MOUNTPOINT_OWER}:${MOUNTPOINT_OWER} $MOUNTPOINT_DIR
            
    if [[ $FILESYS_TYPE == "nfs" ]]
    then

        if [[ $(sudo mount | grep $FILESERVER_IP:${FILESERVER_PATH} | grep -c $MOUNTPOINT_DIR) -eq 0 ]]
        then
            syslog_netcat "Setting nfs storage on ($MOUNTPOINT_DIR) from $FILESERVER_IP:${FILESERVER_PATH}...."
            sudo mount $FILESERVER_IP:${FILESERVER_PATH} $MOUNTPOINT_DIR
        else
            syslog_netcat "Nfs storage on ($MOUNTPOINT_DIR) from $FILESERVER_IP:${FILESERVER_PATH} is already setup!"            
        fi
    fi
    
    return 0
}
export -f mount_remote_filesystem
    
my_if=$(netstat -rn | grep UG | awk '{ print $8 }')
my_type=`get_my_vm_attribute type`
my_login_username=`get_my_vm_attribute login`
my_remote_dir=`get_my_vm_attribute remote_dir_name`

function counter_hash {
    object_type=$1
    key_name=$2
    attribute_name=`echo $3 | tr '[:upper:]' '[:lower:]'`
    attribute_value=$4
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber hincrby ${osinstance}:${object_type}:${key_name} ${attribute_name} ${attribute_value}" 1
}

function increment_my_ai_attribute {
    attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    counter_hash AI ${my_ai_uuid} ${attribute_name} 1
}

function decrement_my_ai_attribute {
    attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    counter_hash AI ${my_ai_uuid} ${attribute_name} -1
}

function put_my_vm_attribute {
    attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    attribute_value=$2    
    put_hash VM ${my_vm_uuid} ${attribute_name} ${attribute_value}
}

function put_my_pending_vm_attribute {
    attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    attribute_value=$2    
    put_hash VM:PENDING ${my_vm_uuid} ${attribute_name} ${attribute_value}
}

function get_ai_attribute {
    aiuuid=`echo $1 | tr '[:lower:]' '[:upper:]'`
    attribute=`echo $2 | tr '[:upper:]' '[:lower:]'`
    get_hash AI ${aiuuid} ${attribute} 0
}

function get_my_ai_attribute {
    attribute=`echo $1 | tr '[:upper:]' '[:lower:]'`
    get_hash AI ${my_ai_uuid} ${attribute} 0
}
export -f get_my_ai_attribute

metric_aggregator_vm_uuid=`get_my_ai_attribute metric_aggregator_vm`

function get_my_ai_attribute_with_default {
    NAME=$1
    DEFAULT=$2
    TEST="`get_my_ai_attribute $NAME`"

    if [ x"$TEST" != x ] ; then
        echo "$TEST"
    elif [ x"$DEFAULT" != x ] ; then
        echo "$DEFAULT"
    else
        syslog_netcat "Configuration error: Value for key ($NAME) not available online or offline."
        exit 1
    fi
}
export -f get_my_ai_attribute_with_default
my_username=`get_my_ai_attribute username`

function put_my_ai_attribute {
    attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    attribute_value=$2
    put_hash AI ${my_ai_uuid} ${attribute_name} ${attribute_value}
}

function put_hash {
    object_type=$1
    key_name=$2
    attribute_name=`echo $3 | tr '[:upper:]' '[:lower:]'`
    attribute_value=$4
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber hset ${osinstance}:${object_type}:${key_name} ${attribute_name} ${attribute_value}" 1
}

function get_vm_uuid_from_hostname {
    uhostname=$1
    fqon=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber get ${osinstance}:VM:TAG:CLOUD_HOSTNAME:${uhostname}" 0`
    echo $fqon | cut -d ':' -f 4
}

function get_global_sub_attribute {
    global_attribute=`echo $1 | tr '[:upper:]' '[:lower:]'`
    global_sub_attribute=`echo $2 | tr '[:upper:]' '[:lower:]'`
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber hget ${osinstance}:GLOBAL:${global_attribute} ${global_sub_attribute}" 0
}
metricstore_hostname=`get_global_sub_attribute metricstore host`
metricstore_port=`get_global_sub_attribute metricstore port`
metricstore_database=`get_global_sub_attribute metricstore database`
metricstore_kind=`get_global_sub_attribute metricstore kind`
metricstore_username=`get_global_sub_attribute metricstore username`
metricstore_password=`get_global_sub_attribute metricstore password`
metricstore_timeout=`get_global_sub_attribute metricstore timeout`
my_experiment_id=`get_global_sub_attribute time experiment_id`
collect_from_guest=`get_global_sub_attribute mon_defaults collect_from_guest`
collect_from_guest=`echo ${collect_from_guest} | tr '[:upper:]' '[:lower:]'`

function get_vm_uuids_from_ai {
    uai=`echo $1 | tr '[:lower:]' '[:upper:]'`
    vmuuidlist=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber zrange ${osinstance}:VM:VIEW:BYAI:${uai}_A 0 -1" 1`
    for vmuuid in $vmuuidlist
    do
        echo $vmuuid
    done
}

function get_vm_ips_from_ai {
    cat ${ai_mapping_file} | grep -v just_for_lost | cut -d ' ' -f 1
}

function get_vm_uuids_from_role {
    cat ${ai_mapping_file} | grep $1 | grep -v just_for_lost | cut -d ',' -f 2
}

function get_hostname_from_role {
    role=`echo $1 | tr '[:upper:]' '[:lower:]'`
    vmuuid=`get_vm_uuids_from_role $role`
    get_vm_attribute ${vmuuid} cloud_hostname
}

function get_vm_hostnames_from_ai {
    uai=`echo $1 | tr '[:lower:]' '[:upper:]'`
    vmuuidlist=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber zrange ${osinstance}:VM:VIEW:BYAI:${uai}_A 0 -1" 1`
    for vmuuid in $vmuuidlist
    do
        get_vm_attribute ${vmuuid} cloud_hostname
    done
}

function build_ai_mapping {
    vmlist=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber zrange ${osinstance}:VM:VIEW:BYAI:${my_ai_uuid}_A 0 -1" 1`
    sudo rm -rf ${ai_mapping_file}
    for vm in $vmlist
    do
        vmuuid=`echo $vm | cut -d "|" -f 1`
        vmip=`get_vm_attribute ${vmuuid} cloud_ip`
        vmhn=`get_vm_attribute ${vmuuid} cloud_hostname`
        vmhn=`echo $vmhn | tr '[:upper:]' '[:lower:]'`
        vmrole=`get_vm_attribute ${vmuuid} role`
        vmclouduuid=`get_vm_attribute ${vmuuid} cloud_uuid`
        echo "${vmip}    ${vmhn}    #${vmrole}    ${vmclouduuid}    ,${vmuuid}" >> ${ai_mapping_file}
        # This is for LOST. It's buggy. It needs the '.' because it
        # doesn't understand shortnames/longnames properly
        echo "${vmip}    ${vmhn}.    #${vmrole}    ${vmclouduuid}    ,just_for_lost" >> ${ai_mapping_file}
    done
}

function get_ips_from_role {
    urole=`echo $1 | tr '[:upper:]' '[:lower:]'`
    vmuuidlist=`get_vm_uuids_from_role ${urole}`
    for vmuuid in $vmuuidlist
    do
        get_vm_attribute ${vmuuid} cloud_ip
    done
}

function add_to_list {
    object_type=$1
    list_name=$2
    list_element_value=$3
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber rpush ${osinstance}:${object_type}:${list_name} ${list_element_value}" 1
}

function remove_from_list {
    object_type=$1
    list_name=$2
    list_element_value="$3"
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber lrem ${osinstance}:${object_type}:${list_name} 0 ${list_element_value}" 1
}

function get_last_from_list {
    object_type=$1
    list_name=$2
    tmp_file="var.txt"
    if [ -f $tmp_file ] ; then
        rm $tmp_file
    fi
    list_contents=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber lrange ${osinstance}:${object_type}:${list_name} -1 -1" 1`
    echo $list_contents > $tmp_file
    last_elem=`cat $tmp_file`
}

function get_first_from_list {
    object_type=$1
    list_name=$2
    if [ -f val.txt ] ; then
        rm val.txt
    fi
    list_contents=`retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber lrange ${osinstance}:${object_type}:${list_name} 0 0" 1`
    echo $list_contents > val.txt
    first_elem=`cat val.txt` #what if the list is empty?? - the first_elem will be empty, too. 
}

function get_whole_list {
    object_type=$1
    list_name=$2
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber lrange ${osinstance}:${object_type}:${list_name} 0 1000000" 1
}

function remove_list {
    object_type=$1
    list_name=$2
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber del ${osinstance}:${object_type}:${list_name}" 1
}

function increment_counter {
    object_type=$1
    counter_name=`echo $2 | tr '[:upper:]' '[:lower:]'`
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber incr ${osinstance}:${object_type}:${counter_name}" 1
}

function inter_ai_increment_counter {
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    increment_counter AI ${counter_name}
}

function get_counter {
    object_type=$1
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber get ${osinstance}:${object_type}:${counter_name}" 1
}

function inter_ai_get_counter {
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    get_counter AI ${counter_name}
}

function reset_counter {
    object_type=$1
    counter_name=`echo $2 | tr '[:upper:]' '[:lower:]'`
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber set ${osinstance}:${object_type}:${counter_name} 0" 1
}

function inter_ai_reset_counter {
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    reset_counter AI ${counter_name}
}

function decrement_counter {
    object_type=$1
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber decr ${osinstance}:${object_type}:${counter_name}" 1
}

function inter_ai_decrement_counter {
    counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
    decrement_counter AI ${counter_name}
}

function publish_msg {
    object_type=`echo $1 | tr '[:lower:]' '[:upper:]'`
    channel=$2
    msg=$3
    subscribers=$4

    total=0
    while true ; do
        got=$(retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber publish ${osinstance}:${object_type}:${channel} \"$msg\"")
        got=$(echo $got | grep -oE [0-9]+)
        ((total=total+got))
        syslog_netcat "Got $got subscribers. Total $total / $subscribers"
        if [ x"$subscribers" != x ] ; then
            syslog_netcat "Checking subscribers..."
            if [ $total -lt $subscribers ] ; then
                syslog_netcat "Not enough."
                sleep 5
                continue
            fi
            syslog_netcat "Sufficient."
            total=0
            break
        else
            syslog_netcat "No subscribers requested."
            break
        fi
    done
}

function publishvm {
    channel=$1
    msg=$2
    publish_msg VM $channel $msg
}

function publishai {
    channel=$1
    msg=$2
    publish_msg AI $channel $msg
}
    
function subscribemsg {
    object=`echo $1 | tr '[:lower:]' '[:upper:]'`
    channel=$2
    message=$3
    ${SUBSCRIBE_CMD} ${object} ${channel} $message $@ | while read line ; do
        syslog_netcat "$line"
    done
}

function subscribevm {
    channel=$1
    message=$2
    ${SUBSCRIBE_CMD} VM ${channel} $message $@ | while read line ; do
        syslog_netcat "$line"
    done
}

function subscribeai {
    channel=$1
    message=$2
    shift
    shift
    ${SUBSCRIBE_CMD} AI ${channel} $message $@ | while read line ; do
        syslog_netcat "$line"
    done
}

load_manager_ip=`get_my_ai_attribute load_manager_ip`

if [ x"${NC_HOST_SYSLOG}" == x ]; then
    # These are cacheable now. (Thank you. =). No need to skip them in scalable mode.
    # We still want rsyslog support in scalable mode.
    USE_VPN_IP=`get_global_sub_attribute vm_defaults use_vpn_ip`
    VPN_ONLY=`get_global_sub_attribute vm_defaults vpn_only`

    # We cannot log anything with VPN_ONLY if we don't use the VPN server's IP address

    if [ x"$USE_VPN_IP" == x"True" ] && [ x"$VPN_ONLY" == x"True" ] ; then
        NC_HOST_SYSLOG=`get_global_sub_attribute vpn server_bootstrap`
    else
        if [ x"${osmode}" != x"scalable" ]; then
            NC_HOST_SYSLOG=`get_global_sub_attribute logstore hostname`
        else 
            NC_HOST_SYSLOG=${load_manager_ip}
        fi
    fi

    NC_PROTO_SYSLOG=`get_global_sub_attribute logstore protocol`

    PROTO=" "
    if [ "$NC_PROTO_SYSLOG" == "UDP" ] ; then
       PROTO="-u"
    fi
    if [ x"${osmode}" != x"scalable" ]; then
        NC_OPTIONS="-w1 $PROTO"
    else 
        NC_OPTIONS="-w1 $PROTO -q1"
    fi
fi

if [ x"${NC_PROTO_SYSLOG}" == x ]; then
    NC_PROTO_SYSLOG=`get_global_sub_attribute logstore protocol`
fi

if [ x"${NC_PORT_SYSLOG}" == x ]; then
    NC_PORT_SYSLOG=`get_global_sub_attribute logstore port`
fi

if [ x"${NC_FACILITY_SYSLOG}" == x ]; then
    NC_FACILITY_SYSLOG="<"`get_global_sub_attribute logstore script_facility`">"
fi

NC_CMD=${NC}" "${NC_OPTIONS}" "${NC_HOST_SYSLOG}" "${NC_PORT_SYSLOG}

# Need to make this rfc3164-compliant by including the 'hostname' and the 'program name'
hn=$(uname -n)
default=$(/sbin/ip route | grep default)
if [ x"$default" != x ] ; then
    interface=$(echo "$default" | sed -e 's/.* dev \+//g' | sed -e "s/ .*//g")
    self=$(/sbin/ifconfig $interface | grep -oE "inet addr:[0-9]+.[0-9]+.[0-9]+.[0-9]+" | sed -e "s/inet addr\://g" | tr "." "-")
    hn="${hn}_${self}"
fi


function syslog_netcat {
    # I'm modifying this slightly. There's nothing wrong with logging in scalable mode,
    # except that we should not be calling slow functions in scalable mode. We still
    # want rsyslog functions to work in scalable mode when cloudbench is running as a service.
    EXPID="$(get_my_vm_attribute experiment_id)"

    echo "$SCRIPT_NAME ($$): ${1}"

    # In rfc3164 format, there cannot be a space between the hostname and the facility number.
    # It's pretty silly, but it doesn't work without removing the space.
    echo "${NC_FACILITY_SYSLOG}$hn cloudbench ${EXPID} $SCRIPT_NAME ($$): ${1}" | $NC_CMD &
}

function refresh_hosts_file {

    if [[ x"${my_ai_uuid}" != x"none" ]] 
    then
        build_ai_mapping
    fi

    # Adding multiple names for the same IP in /etc/hosts
    # is not a problem.
    if [[ $(cat ${ai_mapping_file} | grep -c ${HOSTNAME}) -eq 0 ]]
    then
        echo "${my_ip_addr}    ${HOSTNAME}" >> ${ai_mapping_file}
    fi
    
    syslog_netcat "Refreshing hosts file ... "
    sudo bash -c "rm -f /etc/hosts; echo '127.0.0.1    localhost' >> /etc/hosts; cat ${ai_mapping_file} >> /etc/hosts"
}

function provision_application_start {
    if [[ -f /tmp/provision_application_start ]]
    then
        PASTART=$(cat /tmp/provision_application_start)
    else 
        PASTART=$(date +%s)
        echo $PASTART > /tmp/provision_application_start
    fi
    echo $PASTART
}
export -f provision_application_start

function provision_application_stop {
    PASTART=$1
    
    if [[ -z $PASTART ]]
    then
        if [[ -f /tmp/provision_application_start ]]
        then
            PASTART=$(cat /tmp/provision_application_start)
            rm /tmp/provision_application_start
        fi
    fi

    if [[ ! -e .appfirstrun ]]
    then
        touch .appfirstrun
        END=$(date +%s)
        DIFF=$(( $END - $PASTART ))
        syslog_netcat "Updating vm application startup time with value ${DIFF}"
        put_my_pending_vm_attribute application_start_on_vm $DIFF          
        #        put_my_pending_vm_attribute mgt_007_application_start $DIFF
    else
        syslog_netcat "Application Instance already deployed (once). Will not report application startup time (again)"    
    fi
}
export -f provision_application_stop

function provision_generic_start {
    PASTART=$(date +%s)
    echo $PASTART > /tmp/provision_generic_start
    echo $PASTART
}
export -f provision_generic_start

function provision_generic_stop {
    PASTART=$1
    
    if [[ -z $PASTART ]]
    then
        if [[ -f /tmp/provision_generic_start ]]
        then
            PASTART=$(cat /tmp/provision_generic_start)
            rm /tmp/provision_generic_start
        fi
    fi

    if [[ ! -e .genfirstrun ]]
    then
        touch .genfirstrun
        END=$(date +%s)
        DIFF=$(( $END - $PASTART ))
        syslog_netcat "Updating instance preparation time with value ${DIFF}"
        put_my_pending_vm_attribute instance_preparation_on_vm $DIFF        
        #        put_my_pending_vm_attribute mgt_006_instance_preparation $DIFF
    else
        syslog_netcat "Generic startup already run (once). Will not report instance preparation time (again)"    
    fi
}
export -f provision_generic_stop

function security_configuration {

    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi

    if [[ $IS_CONTAINER -eq 0 ]]
    then                                        
        FW_SERVICE[1]="ufw"
        FW_SERVICE[2]="iptables"
    
        service_stop_disable ${FW_SERVICE[${LINUX_DISTRO}]}
    
        if [[ ${LINUX_DISTRO} -eq 1 ]]
        then
            syslog_netcat "Disabling Apparmor..."
            service_stop_disable apparmor
            sudo service apparmor teardown
        fi
                
        if [[ ${LINUX_DISTRO} -eq 2 ]]
        then 
            syslog_netcat "Disabling SElinux..."        
            sudo sed -i "s/^SELINUX=.*/SELINUX=disabled/" /etc/selinux/config
            sudo setenforce 0
        fi
        syslog_netcat "Done"
    else
        syslog_netcat "Running inside a container, Apparmor/SElinux not present"
    fi
}
export -f security_configuration

function start_redis {
    
    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi

    REDIS_SERVICE[1]="redis-server"
    REDIS_SERVICE[2]="redis"

    REDIS_CONFIG[1]="/etc/redis/redis.conf"
    REDIS_CONFIG[2]="/etc/redis.conf"

    if [[ $IS_CONTAINER -eq 0 ]]
    then        
        service_stop_disable ${REDIS_SERVICE[${LINUX_DISTRO}]}
    fi
    
    TMPLT_OBJSTORE_PORT=$1
    syslog_netcat "Updating object store configuration template"
    sudo cp ${REDIS_CONFIG[${LINUX_DISTRO}]} ${REDIS_CONFIG[${LINUX_DISTRO}]}.old                
    sudo sed -i s/"port 6379"/"port ${TMPLT_OBJSTORE_PORT}"/g ${REDIS_CONFIG[${LINUX_DISTRO}]}

    if [[ $IS_CONTAINER -eq 0 ]]
    then            
        service_restart_enable ${REDIS_SERVICE[${LINUX_DISTRO}]}
    fi
}
export -f start_redis

function start_syslog {
    if [[ $IS_CONTAINER -eq 0 ]]
    then                                            
        is_syslog_running=`ps aux | grep -v grep | grep -c rsyslog.conf`
        if [ ${is_syslog_running} -eq 0 ]
        then 
            mkdir -p ~/logs
            TMPLT_LOGSTORE_PORT=$1
            sed -i s/"TMPLT_LOGSTORE_PORT"/"${TMPLT_LOGSTORE_PORT}"/g ~/rsyslog.conf
            sed -i s/"TMPLT_USERNAME"/"${LOGNAME}"/g ~/rsyslog.conf
            RSYSLOG=`sudo which rsyslogd`
            ${RSYSLOG} -f ~/rsyslog.conf -i ~/rsyslog.pid
        fi
    fi
}
export -f start_syslog

function restart_ntp {

    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi

    NTP_SERVICE[1]="ntp"
    NTP_SERVICE[2]="ntpd" 

    if [[ $IS_CONTAINER -eq 0 ]]
    then                                        
        service_stop_disable ${NTP_SERVICE[${LINUX_DISTRO}]}
    fi
    
    syslog_netcat "Creating ${NTP_SERVICE[${LINUX_DISTRO}]} (ntp.conf) file"
    ~/cb_create_ntp_config_file.sh
    
    syslog_netcat "Forcing clock update from ntp"
    sudo ~/cb_timebound_exec.py ntpd -gq 5
    
    if [[ $IS_CONTAINER -eq 0 ]]
    then        
        service_restart_enable ${NTP_SERVICE[${LINUX_DISTRO}]}
    fi
}
export -f restart_ntp

function online_or_offline {
    if [ x"$1" == x ] ; then
        echo online 
    else
        echo offline 
    fi
}

function comment_lines {
    sed -i "$1"' s/^/#/' "$2"
}
export -f comment_lines

function post_boot_steps {

    if [[ ! -e /usr/lib64 ]]
    then
        syslog_netcat "Creating symbolic link /usr/lib64 -> /usr/lib"
        sudo ln -s /usr/lib /usr/lib64
    fi

    # Do specific things for windows and exit
    if [[ x"$(uname -a | grep CYGWIN)" != x ]]
    then
        syslog_netcat "This machine is windows. Performing windows-only setup"
        syslog_netcat "Removing log files to prepare for renaming..."
        rm -f ~/*.log
        syslog_netcat "Restoring MOM timeout..."
        sed -ie "s/conn.settimeout(None)/conn.settimeout(5)/g" /cygdrive/c/EclipseWorkspaces/mom-python2.6/Mom-py2.6/src/GuestNetworkDaemon.py
        syslog_netcat "Finished"
        exit 0
    fi

    SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
    KILL_CMD=`which killall`
    SUDO_CMD=`which sudo`
    export PATH=$PATH:/sbin
    PIDOF_CMD=`which pidof`

    stop_ganglia

    # fix the db2 data authentication permissions first
    if [[ x"$(echo $0 | grep cb_restart_db2)" != x ]] || [[ x"${my_role}" == x"db2" ]]
    then
        syslog_netcat "Fixing up DB2 authentication permissions"
        sudo chmod u+s ~/sqllib/security/db2aud
        sudo rm -f ~/sqllib/security/db2chkau
        sudo chown bin:bin /opt/ibm/db2/V9.7/security64/db2chkau
        sudo chmod 555 /opt/ibm/db2/V9.7/security64/db2chkau
        sudo ln -s /opt/ibm/db2/V9.7/security64/db2chkau ~/sqllib/security/db2chkau
        sudo chown root:$(whoami) ~/sqllib/security/db2chpw
        sudo chown root:$(whoami) ~/sqllib/security/db2ckpw
        sudo chmod u+s ~/sqllib/security/db2chpw
        sudo chmod u+s ~/sqllib/security/db2ckpw
        sudo chmod g+s ~/sqllib/security/db2flacc
    fi

    sleep 1

    sudo bash -c "chmod 777 /dev/pts/*"
    DISABLE_TIMESYNC=$(get_my_vm_attribute disable_timesync)
    DISABLE_TIMESYNC=$(echo ${DISABLE_TIMESYNC} | tr '[:upper:]' '[:lower:]')
    if [[ $DISABLE_TIMESYNC == "false" ]] 
    then
        restart_ntp
    fi
    sudo ln -sf ${dir}/../../3rd_party/monitor-core ~
    sudo ln -sf ${dir}/../../util ~

    # for 32-bit VMs
    if [[ ! -e /usr/lib64/ganglia && -e /usr/lib/ganglia ]]
    then
        sudo ln -sf /usr/lib/ganglia/ /usr/lib64/ganglia
    fi

    if [[ x"${my_ai_uuid}" != x"none" ]]
    then
        syslog_netcat "Copying application-specific scripts to the home directory"
        ln -sf "${dir}/../${my_base_type}/"* ~
    fi

    if [[ x"${collect_from_guest}" == x"true" ]]
    then
        syslog_netcat "Collect from Guest is ${collect_from_guest}"
        start_ganglia
    else
        syslog_netcat "Collect from Guest is ${collect_from_guest}"
        sleep 2
        syslog_netcat "Bypassing the gmond and gmetad restart"
    fi

}
    
function stop_ganglia {
            
    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi

    if [[ $IS_CONTAINER -eq 0 ]]
    then        
        GANGLIA_SERVICE[1]="ganglia-monitor gmetad"
        GANGLIA_SERVICE[2]="gmond gmetad"
          
        service_stop_disable ${GANGLIA_SERVICE[${LINUX_DISTRO}]}          
        
        syslog_netcat "Killing previously running ganglia monitoring processes on $SHORT_HOSTNAME"
        gpid="$(pidof gmond)"
        blowawaypids gmond
        sleep 3
        if [[ x"$gpid" == x ]] || [[ x"$(pidof gmond)" == x ]]
        then
            syslog_netcat "Ganglia monitoring processes killed successfully on $SHORT_HOSTNAME"
        else
            syslog_netcat "Ganglia monitoring processes could not be killed on $SHORT_HOSTNAME - NOK"
            exit 2
        fi
        syslog_netcat "Previously running ganglia monitoring processes killed $SHORT_HOSTNAME"
    fi
}
export -f stop_ganglia

function start_ganglia {

    syslog_netcat "Creating ganglia (gmond) file"
    ~/cb_create_gmond_config_file.sh
    syslog_netcat "Restarting ganglia monitoring processes (gmond) on $SHORT_HOSTNAME"
    GANGLIA_FILE_LOCATION=~
    eval GANGLIA_FILE_LOCATION=${GANGLIA_FILE_LOCATION}
    blowawaypids gmond
    sudo screen -d -m -S gmond bash -c "while true ; do if [ x\`$PIDOF_CMD gmond\` == x ] ; then gmond -c ${GANGLIA_FILE_LOCATION}/gmond-vms.conf; fi; sleep 10; done"
    sleep 2
    if [[ x"$(pidof gmond)" == x ]]
    then
        syslog_netcat "Ganglia monitoring processes (gmond) could not be restarted on $SHORT_HOSTNAME - NOK"
        exit 2
    else
        syslog_netcat "Ganglia monitoring processes (gmond) restarted successfully on $SHORT_HOSTNAME"
    fi
    
    if [[ x"${my_vm_uuid}" == x"${metric_aggregator_vm_uuid}" || x"${my_type}" == x"none" ]]
    then
        syslog_netcat "Starting Gmetad"
        ~/cb_create_gmetad_config_file.sh
        syslog_netcat "Restarting ganglia meta process (gmetad) on $SHORT_HOSTNAME"
        blowawaypids gmetad

        GMETAD_PATH=~/${my_remote_dir}/3rd_party/monitor-core/gmetad-python
        
        eval GMETAD_PATH=${GMETAD_PATH}
        $GMETAD_PATH/gmetad.py -c ~/gmetad-vms.conf -d 1
#       $GMETAD_PATH/gmetad.py -c ~/gmetad-vms.conf --syslogn 127.0.0.1 --syslogp 6379 --syslogf 22 -d 4

        result="$(ps aux | grep gmeta | grep -v grep)"
        if [[ x"$result" == x ]]
        then
            syslog_netcat "Ganglia meta process (gmetad) could not be restarted on $SHORT_HOSTNAME - NOK"
            exit 2
        else
            syslog_netcat "Ganglia meta process (gmetad) restarted successfully on $SHORT_HOSTNAME"
        fi
    fi
}
export -f start_ganglia    

function execute_load_generator {

    CMDLINE=$1
    OUTPUT_FILE=$2
    LOAD_DURATION=$3

    source ~/cb_barrier.sh start

    log_output_command=$(get_my_ai_attribute log_output_command)
    log_output_command=$(echo ${log_output_command} | tr '[:upper:]' '[:lower:]')

    run_limit=`decrement_my_ai_attribute run_limit`

    if [[ -f /tmp/quiescent_time_start ]]
    then
        QSTART=$(cat /tmp/quiescent_time_start)
        END=$(date +%s)
        DIFF=$(( $END - $QSTART ))
        echo $DIFF > /tmp/quiescent_time        
    fi
    
    if [[ ${run_limit} -ge 0 ]]
    then
        syslog_netcat "This AI will execute the load_generating process ${run_limit} more times (LOAD_ID=${LOAD_ID}, AI_UUID=$my_ai_uuid, VM_UUID=$my_vm_uuid)" 
        syslog_netcat "Command line is: ${CMDLINE}. Output file is ${OUTPUT_FILE} (LOAD_ID=${LOAD_ID}, AI_UUID=$my_ai_uuid, VM_UUID=$my_vm_uuid)"
        if [[ x"${log_output_command}" == x"true" ]]
        then
            syslog_netcat "Command output will be shown"
            LOAD_GENERATOR_START=$(date +%s)
            $CMDLINE 2>&1 | while read line ; do
                syslog_netcat "$line"
                echo $line >> $OUTPUT_FILE
            done
            ERROR=$?
            LOAD_GENERATOR_END=$(date +%s)
            APP_COMPLETION_TIME=$(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START )) 
        else
            syslog_netcat "Command output will NOT be shown"
            LOAD_GENERATOR_START=$(date +%s)            
            $CMDLINE 2>&1 >> $OUTPUT_FILE
            ERROR=$?
            LOAD_GENERATOR_END=$(date +%s)
            APP_COMPLETION_TIME=$(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START ))            
        fi
    else
        LOAD_GENERATOR_START=$(date +%s)        
        syslog_netcat "This AI reached the limit of load generation process executions. If you want this AI to continue to execute the load generator, reset the \"run_limit\" counter (LOAD_ID=${LOAD_ID}, AI_UUID=$my_ai_uuid, VM_UUID=$my_vm_uuid)"
        sleep ${LOAD_DURATION}
        LOAD_GENERATOR_END=$(date +%s)
        ERROR=$?
        APP_COMPLETION_TIME=$(( $LOAD_GENERATOR_END - $LOAD_GENERATOR_START ))
    fi
    update_app_errors $ERROR
    update_app_completiontime $APP_COMPLETION_TIME
    
    echo $(date +%s) > /tmp/quiescent_time_start

    if [[ ! -z $LIDMSG ]]
    then
        syslog_netcat "RUN COMPLETE: ${LIDMSG}"    
    fi
                
    return 0
}
export -f execute_load_generator
            
function setup_passwordless_ssh {

    SSH_KEY_NAME=$(get_my_vm_attribute identity)
    REMOTE_DIR_NAME=$(get_my_vm_attribute remote_dir_name)
    SSH_KEY_NAME=$(echo ${SSH_KEY_NAME} | rev | cut -d '/' -f 1 | rev)

    syslog_netcat "VMs need to be able to perform passwordless SSH between each other. Updating ~/.ssh/id_rsa to be the same on all VMs.."
    #sudo chmod 0600 ~/${REMOTE_DIR_NAME}/credentials/$SSH_KEY_NAME
    sudo find ~ -name $SSH_KEY_NAME -exec chmod 0600 {} \;
    sudo cat ~/${REMOTE_DIR_NAME}/credentials/$SSH_KEY_NAME > ~/.ssh/id_rsa
    sudo chmod 0600 ~/.ssh/id_rsa
    sudo cat ~/${REMOTE_DIR_NAME}/credentials/$SSH_KEY_NAME.pub > ~/.ssh/id_rsa.pub
    sudo chmod 0600 ~/.ssh/id_rsa.pub

    if [[ $(cat ~/.ssh/config | grep -c StrictHostKeyChecking) -eq 0 ]]
    then
        echo "StrictHostKeyChecking no" >> ~/.ssh/config
    fi

    if [[ $(cat ~/.ssh/config | grep -c UserKnownHostsFile) -eq 0 ]]
    then
        echo "UserKnownHostsFile /dev/null" >> ~/.ssh/config
    fi
    chmod 0644 ~/.ssh/config
}
export -f setup_passwordless_ssh

function update_app_errors {

    if [[ ! -z $1 ]]
    then
        ERROR=$1
    else
        ERROR=0
    fi
    
    if [[ ! -z $2 ]]
    then
        rm -rf /tmp/app_errors
    fi
    
    if [[ ! -f /tmp/app_errors ]]
    then
        echo "0" > /tmp/app_errors
    fi

    if [[ $ERROR -ne 0 ]]
    then
        curr_err=$(cat /tmp/app_errors)
        new_err="$(( $curr_err + 1 ))"
        echo $new_err > /tmp/app_errors
    else
        new_err=$(cat /tmp/app_errors )
    fi    
    
    echo $new_err
    return 0
}
export -f update_app_errors

function update_app_datagentime {

    if [[ ! -z $1 ]]
    then
        echo $1 > /tmp/data_generation_time
        return 0
    fi
        
    if [[ -f /tmp/old_data_generation_time ]]
    then
        datagentime=-$(cat /tmp/old_data_generation_time)
    fi
    
    if [[ -f /tmp/data_generation_time ]]
    then
        datagentime=$(cat /tmp/data_generation_time)
        mv /tmp/data_generation_time /tmp/old_data_generation_time
    fi
    
    echo $datagentime
    return 0
}
export -f update_app_datagentime

function update_app_datagensize {
    if [[ ! -z $1 ]]
    then
        echo $1 > /tmp/data_generation_size
        return 0
    fi
        
    if [[ -f /tmp/old_data_generation_size ]]
    then
        datagensize=-$(cat /tmp/old_data_generation_size)
    fi

    if [[ -f /tmp/data_generation_size ]]
    then
        datagensize=$(cat /tmp/data_generation_size)
        mv /tmp/data_generation_size /tmp/old_data_generation_size        
    fi
    
    echo $datagensize
    return 0
}
export -f update_app_datagensize

function update_app_completiontime {

    if [[ ! -z $1 ]]
    then
        echo $1 > /tmp/app_completiontime
        return 0
    fi
        
    if [[ -f /tmp/old_app_completiontime ]]
    then
        completiontime=-$(cat /tmp/old_app_completiontime)
    fi
    
    if [[ -f /tmp/app_completiontime ]]
    then
        completiontime=$(cat /tmp/app_completiontime)
        mv /tmp/app_completiontime /tmp/old_app_completiontime
    fi
    
    echo $completiontime

    return 0
}
export -f update_app_completiontime

function update_app_quiescent {
        
    if [[ -f /tmp/quiescent_time ]]
    then
        quiescent_time=$(cat /tmp/quiescent_time)
    else
        quiescent_time=-1 
    fi
    
    echo $quiescent_time
    return 0
}
export -f update_app_quiescent

function vercomp {
    if [[ $1 == $2 ]]
    then
        return 0
    fi
    
    local IFS=.
    local i ver1=($1) ver2=($2)

    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done
    return 0
}
export -f vercomp

function get_offline_ip {
    ip -o addr show $(ip route | grep default | grep -oE "dev [a-z]+[0-9]+" | sed "s/dev //g") | grep -Eo "[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*" | grep -v 255
}

function automount_data_dirs {
    #    ROLE_DATA_DIR=$(get_my_ai_attribute_with_default ${my_role}_data_dir none)
    #    ROLE_DATA_FSTYP=$(get_my_ai_attribute_with_default ${my_role}_data_fstyp local)

    ROLE_DATA_DIR=$(get_my_vm_attribute_with_default data_dir none)
    ROLE_DATA_FSTYP=$(get_my_vm_attribute_with_default data_fstyp local)

    if [[ $ROLE_DATA_DIR != "none" ]]
    then
        syslog_netcat "Creating directory \"$ROLE_DATA_DIR\""
        sudo mkdir -p $ROLE_DATA_DIR
    fi
            
    if [[ $ROLE_DATA_FSTYP == "ramdisk" || $ROLE_DATA_FSTYP == "tmpfs" ]]
    then

        #        ROLE_DATA_SIZE=$(get_my_ai_attribute_with_default ${my_role}_data_size 256m)
        DATA_SIZE=$(get_my_vm_attribute_with_default data_size 256m)
        mount_filesystem_on_memory ${ROLE_DATA_DIR} $ROLE_DATA_FSTYP ${ROLE_DATA_SIZE} ${my_login_username}
        
    elif [[ $ROLE_DATA_FSTYP == "nfs" ]]
    then
        
        #        ROLE_DATA_FILESERVER_IP=$(get_my_ai_attribute_with_default ${my_role}_data_fileserver_ip none)
        #        ROLE_DATA_FILESERVER_PATH=$(get_my_ai_attribute_with_default ${my_role}_data_fileserver_path none)
        DATA_FILESERVER_IP=$(get_my_vm_attribute_with_default data_fileserver_ip none)
        DATA_FILESERVER_PATH=$(get_my_vm_attribute_with_default data_fileserver_path none)        
        if [[ $ROLE_DATA_FILESERVER_IP != "none" && $ROLE_DATA_FILESERVER_PATH != "none" ]]
        then         
            mount_remote_filesystem ${ROLE_DATA_DIR} ${ROLE_DATA_FSTYP} ${ROLE_DATA_FILESERVER_IP} ${ROLE_DATA_FILESERVER_PATH}    
        fi
    else
        if [[ $(get_attached_volumes) != "NONE" ]]
        then
            mount_filesystem_on_volume ${ROLE_DATA_DIR} $ROLE_DATA_FSTYP ${my_login_username}
        fi
    fi
}
export -f automount_data_dirs

function haproxy_setup {
    LOAD_BALANCER_PORTS=$1
    LOAD_BALANCER_BACKEND_SERVERS=$2

    LOAD_BALANCER_MODE="http"
    if [[ ! -z $3 ]]
    then
        LOAD_BALANCER_MODE=$3
    fi
            
    f=/tmp/haporxy.cfg
cat << EOF > $f
global
  chroot  /var/lib/haproxy
  daemon
  group  haproxy
  log  127.0.0.1 local0
  maxconn  4096
  pidfile  /var/run/haproxy.pid
  stats  socket /var/lib/haproxy/stats
  user  haproxy

defaults
  log  global
  maxconn  8000
  stats  enable
  timeout  http-request 10s
  timeout  queue 1m
  timeout  connect 10s
  timeout  client 1m
  timeout  server 1m
  timeout  check 10s

EOF

    LOAD_BALANCER_PORTS=$(echo $LOAD_BALANCER_PORTS | sed 's/,/ /g')
    
    for LBP in $LOAD_BALANCER_PORTS
    do
        echo "" >> $f    
        echo "listen ${my_type}${LBP}" >> $f
        echo "  bind 0.0.0.0:${LBP}" >> $f   
        
        if [[ $LOAD_BALANCER_NODE == "http" ]]
        then
            echo "  mode http" >> $f            
            echo "  retries 3" >> $f
            echo "  option tcplog" >> $f
            echo "  option redispatch" >> $f
            echo "  balance roundrobin" >> $f
        fi
            
        if [[ $LOAD_BALANCER_NODE == "tcp" ]]
        then
            echo "  mode tcp" >> $f
            echo "  retries 3" >> $f
            echo "  option tcplog" >> $f 
            echo "  option redispatch" >> $f
        fi        
            
        for BACKEND_IP in $LOAD_BALANCER_BACKEND_SERVERS
        do
            echo "  server $(cat /etc/hosts | grep $BACKEND_IP | grep -v lost | awk '{ print $2 }') $BACKEND_IP:$LBP check" >> $f
        done   
    done    
    sudo ls /etc/haproxy/haproxy.cfg.backup
    if [[ $? -ne 0 ]]
    then
        sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup
    fi

    sudo mv $f /etc/haproxy/haproxy.cfg
    
    SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
    ATTEMPTS=3
    while [[ "$ATTEMPTS" -ge  0 ]]
    do 
        syslog_netcat "Checking for an HAproxy load balancer running on $SHORT_HOSTNAME...."
        result="$(ps -ef | grep haproxy | grep -v grep)"
        
        if [[ x"$result" == x ]]
        then 
            ((ATTEMPTS=ATTEMPTS-1))
            syslog_netcat "There is no load balancer running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"
    
            service_restart_enable haproxy
            syslog_netcat "HAproxy started on $SHORT_HOSTNAME ( pointing to target service running on $LOAD_BALANCER_TARGET_IPS )."
            syslog_netcat "Will wait 5 seconds and check for haproxy processes...."
            sleep 5
        else 
            syslog_netcat "HAproxy load balancer restarted successfully on $SHORT_HOSTNAME ( pointing to target service running on $LOAD_BALANCER_TARGET_IPS ) - OK";
    
            provision_application_stop $START
        fi    
        exit 0
    
    done
    syslog_netcat "haproxy load Balancer could not be restarted on $SHORT_HOSTNAME - NOK"
    exit 2
}
export -f haproxy_setup

#FIXME
function ihs_setup {
    syslog_netcat "Fixing up httpd.conf..... to point to IPs ${LOAD_BALANCER_TARGET_IPS_CSV}"
    
    conf_file=/opt/IBM/HTTPServer/conf/httpd.conf
    tmp_file=/tmp/http.conf.tmp
    
    if [[ x"$(grep "balancer\://$LOAD_BALANCER_TARGET" $conf_file)" == x ]]
    then
        sudo cp $conf_file $tmp_file
        sudo chmod 777 $tmp_file
    
        echo "<Proxy balancer://$LOAD_BALANCER_TARGET>" >> $tmp_file
    
        for ip in $LOAD_BALANCER_TARGET_IPS ; do
            echo "BalancerMember http://$ip:$LOAD_BALANCER_TARGET_PORT/$LOAD_BALANCER_TARGET_URL" >> $tmp_file
        done
    
    
        echo "</Proxy>" >> $tmp_file
        echo "ProxyPass /daytrader balancer://$LOAD_BALANCER_TARGET" >> $tmp_file
        echo "ProxyPassReverse /daytrader balancer://$LOAD_BALANCER_TARGET" >> $tmp_file
    
        syslog_netcat "Done setting up child load targets for balancer in httpd.conf..."
    
        sudo cp $tmp_file $conf_file
    else
        syslog_netcat "httpd.conf already fixed. skipping..."
    fi

    SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)    
    ATTEMPTS=3
    while [[ "$ATTEMPTS" -ge  0 ]]
    do 
        syslog_netcat "Checking for a http load balancer running on $SHORT_HOSTNAME...."
        result="$(ps -ef | grep httpd | grep -v grep)"
        syslog_netcat "Done checking for a WAS server running on $SHORT_HOSTNAME"
        
        if [[ x"$result" == x ]]
        then 
            ((ATTEMPTS=ATTEMPTS-1))
            syslog_netcat "There is no load balancer running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"
    
            sudo /opt/IBM/HTTPServer/bin/apachectl restart
            sudo /opt/IBM/HTTPServer/bin/adminctl restart
            syslog_netcat "Apache started on $SHORT_HOSTNAME ( pointing to target service running on $LOAD_BALANCER_TARGET_IPS )."
            syslog_netcat "Will wait 5 seconds and check for httpd processes...."
            sleep 5
        else 
            syslog_netcat "Load balancer restarted successfully on $SHORT_HOSTNAME ( pointing to target service running on $LOAD_BALANCER_TARGET_IPS ) - OK";
    
            provision_application_stop $START
        fi    
        exit 0
    
    done
    syslog_netcat "Load Balancer could not be restarted on $SHORT_HOSTNAME - NOK"
    exit 2
}
export -f ihs_setup

function set_java_home {
    if [[ -z ${JAVA_HOME} ]]
    then
        JAVA_HOME=$(get_my_ai_attribute_with_default java_home auto)
    
        if [[ ${JAVA_HOME} != "auto" ]]   
        then
            sudo ls $JAVA_HOME
            if [[ $? -ne 0 ]]
            then
                syslog_netcat "The JAVA_HOME specified in the AI attributes \"${JAVA_HOME}\" could not be located: setting it to \"auto\"..."
                JAVA_HOME="auto"
            fi
        fi
        
        if [[ ${JAVA_HOME} == "auto" ]]
        then

            syslog_netcat "The JAVA_HOME was set to \"auto\". Attempting to find the most recent in /opt/ibm"
            sudo ls /opt/ibm/java-*
            if [[ $? -eq 0 ]]
            then
                JAVA_HOME=$(sudo find /opt/ibm/ | grep jre/bin/javaws | sed 's^/bin/javaws^^g' | sort -r | head -n 1)
            else            
                syslog_netcat "The JAVA_HOME was set to \"auto\". Attempting to find the most recent in /usr/lib/jvm"
                JAVA_HOME=/usr/lib/jvm/$(ls -t /usr/lib/jvm | grep java | sed '/^$/d' | sort -r | head -n 1)/jre
            fi
        fi
    
        syslog_netcat "JAVA_HOME determined to be \"${JAVA_HOME}\""    
                
        eval JAVA_HOME=${JAVA_HOME}
        if [[ -f ~/.bashrc ]]
        then
            is_java_home_export=`grep -c "JAVA_HOME=${JAVA_HOME}" ~/.bashrc`
            if [[ $is_java_home_export -eq 0 ]]
            then
                syslog_netcat "Adding JAVA_HOME=${JAVA_HOME} to bashrc"
                echo "export JAVA_HOME=${JAVA_HOME}" >> ~/.bashrc
            fi
        fi
    else
        syslog_netcat "Line \"export JAVA_HOME=${JAVA_HOME}\" was already added to bashrc"    
    fi

    export JAVA_HOME=${JAVA_HOME}
    echo $PATH | grep ${JAVA_HOME}/bin
    if [[ $? -ne 0 ]]
    then
        export PATH=${JAVA_HOME}/bin:$PATH
    fi
    
    JAVA_MAX_MEM_HEAP=$(get_my_ai_attribute_with_default java_max_mem_heap 0.8)

    check_container 
    
    if [[ $IS_CONTAINER -eq 1 ]]
    then
        mem=`echo $(get_my_vm_attribute size) | cut -d '-' -f 2`
        export JAVA_MAX_MEM_HEAP=$(echo "scale=0; $mem*${JAVA_MAX_MEM_HEAP}" | bc -l)        
    else 
        mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`
        export JAVA_MAX_MEM_HEAP=$(echo "scale=0; $mem*${JAVA_MAX_MEM_HEAP}/1024" | bc -l)        
    fi
    
    JAVA_EXTRA_CMD_OPTS=$(get_my_ai_attribute_with_default java_extra_cmd_opts "-Xms256m")
    
    echo $JAVA_EXTRA_CMD_OPTS | grep Xmx
    if [[ $? -ne 0 ]]
    then
        export JAVA_EXTRA_CMD_OPTS="-Xmx"$(echo ${JAVA_MAX_MEM_HEAP} | cut -d '.' -f 1)"m "$JAVA_EXTRA_CMD_OPTS
    fi
}
export -f set_java_home

my_sut=$(get_my_ai_attribute sut)
    
function set_load_gen {
    LOAD_PROFILE=$1
    LOAD_LEVEL=$2
    LOAD_DURATION=$3
    LOAD_ID=$4
    SLA_RUNTIME_TARGETS=$5

    if [[ -z "$LOAD_PROFILE" || -z "$LOAD_LEVEL" || -z "$LOAD_DURATION" || -z "$LOAD_ID" ]]
    then
        syslog_netcat "Usage: $0 <load_profile> <load level> <load duration> <load_id> [sla_targets]"
        exit 1
    else
        export LOAD_PROFILE=$LOAD_PROFILE
        export LOAD_LEVEL=$LOAD_LEVEL
        export LOAD_DURATION=$LOAD_DURATION
        export LOAD_ID=$LOAD_ID
    fi
    
    if [[ -z "$SLA_RUNTIME_TARGETS" ]]
    then
        /bin/true
    else
        export SLA_RUNTIME_TARGETS=$SLA_RUNTIME_TARGETS
    fi

    export GEN_OUTPUT_FILE=$(mktemp)
    export RUN_OUTPUT_FILE=$(mktemp)

#    export RUN_ID=$(echo $OUTPUT_FILE | sed 's^/tmp/tmp.^^g')
    lidmsgs="Benchmarking $my_type SUT: "
    lidmsgm=''
    
    for ir in $(echo $my_sut | sed 's/->/ /g' | sed 's/[0-9]_x_//g')
    do
        lidmsgm=${lidmsgm}$(echo $ir | tr '[:lower:]' '[:upper:]')"="$(echo `get_ips_from_role $ir` | sed 's/ /,/g')" -> "
    done
    lidmsgm=${lidmsgm}"_+"
    lidmsgm=$(echo ${lidmsgm} | sed 's/-> _+/ /g')
    lidmsge="with LOAD_PROFILE=${LOAD_PROFILE}, LOAD_LEVEL=${LOAD_LEVEL} and LOAD_DURATION=${LOAD_DURATION} (LOAD_ID=${LOAD_ID}, AI_UUID=$my_ai_uuid, VM_UUID=$my_vm_uuid)"
    
    export LIDMSG=${lidmsgs}${lidmsgm}${lidmsge}
                
    update_app_errors 0 reset
    syslog_netcat "PREPARING: ${LIDMSG}"
}    
export -f set_load_gen

function unset_load_gen {
    rm ${RUN_OUTPUT_FILE}
    rm ${GEN_OUTPUT_FILE}
    syslog_netcat "METRIC COLLECTION COMPLETE: ${LIDMSG}"
}
export -f unset_load_gen
    
function format_for_report {
    metric_name=$1
    metric_value=$2
    
    echo $metric_value | grep [0-9].us > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        echo $metric_name":"$(echo $2 | sed 's/us//g')":us"
        return 0
    fi

    echo $metric_value | grep [0-9].k > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then        
        echo $metric_name":"$(echo "scale=2; $2 * 1000" | sed 's/k//g' | bc -l)":tps"
        return 0
    fi    

    echo $metric_value | grep [0-9].ms > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        echo $metric_name":"$(echo $2 | sed 's/ms//g')":ms"
        return 0
    fi    
}
export -f format_for_report

function common_metrics {
    mtr_str=''
    mtr_str=${mtr_str}" load_id:${LOAD_ID}:seqnum"
    mtr_str=${mtr_str}" load_profile:${LOAD_PROFILE}:name" 
    mtr_str=${mtr_str}" load_level:${LOAD_LEVEL}:load"
    mtr_str=${mtr_str}" load_duration:${LOAD_DURATION}:sec"
    mtr_str=${mtr_str}" errors:$(update_app_errors):num"
    mtr_str=${mtr_str}" completion_time:$(update_app_completiontime):sec"
    mtr_str=${mtr_str}" quiescent_time:$(update_app_quiescent):sec"
    if [[ -z $SLA_RUNTIME_TARGETS ]]
    then
        mtr_str=${mtr_str}" "$SLA_RUNTIME_TARGETS
    fi
    echo $mtr_str
}
export -f common_metrics
