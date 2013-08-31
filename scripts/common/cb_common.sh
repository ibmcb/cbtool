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
GMETAD_PATH=$dir/../../3rd_party/monitor-core/gmetad-python

ai_mapping_file=~/ai_mapping_file.txt
standalone="online"

PGREP_CMD=`which pgrep`
PKILL_CMD=`which pkill`
SUBSCRIBE_CMD=~/cb_subscribe.py
RSYSLOGD_CMD=/sbin/rsyslogd

NC=`which nc`

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

SCRIPT_NAME=$0

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
	uip=$1
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
my_role=`get_my_vm_attribute role`
my_ai_name=`get_my_vm_attribute ai_name`
my_ai_uuid=`get_my_vm_attribute ai`
my_base_type=`get_my_vm_attribute base_type`
my_cloud_model=`get_my_vm_attribute model`
my_ip_addr=`get_my_vm_attribute cloud_ip`
my_type=`get_my_vm_attribute type`
my_login_username=`get_my_vm_attribute login`
my_remote_dir=`get_my_vm_attribute remote_dir_name`

function put_hash {
	object_type=$1
	key_name=$2
	attribute_name=`echo $3 | tr '[:upper:]' '[:lower:]'`
	attribute_value=$4
	retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber hset ${osinstance}:${object_type}:${key_name} ${attribute_name} ${attribute_value}" 1
}

function put_my_vm_attribute {
	attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	attribute_value=$2	
	put_hash VM ${my_vm_uuid} ${attribute_name} ${attribute_value}
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
my_username=`get_my_ai_attribute username`

function put_my_ai_attribute {
	attribute_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	attribute_value=$2
	put_hash AI ${my_ai_uuid} ${attribute_name} ${attribute_value}
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
	rm -rf ${ai_mapping_file}
	for vm in $vmlist
	do
		vmuuid=`echo $vm | cut -d "|" -f 1`
		vmip=`get_vm_attribute ${vmuuid} cloud_ip`
		vmhn=`get_vm_attribute ${vmuuid} cloud_hostname`
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

function ai_increment_counter {
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	increment_counter AI ${counter_name}
}

function get_counter {
	object_type=$1
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber get ${osinstance}:${object_type}:${counter_name}" 1
}

function ai_get_counter {
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	get_counter AI ${counter_name}
}

function reset_counter {
	object_type=$1
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber set ${osinstance}:${object_type}:${counter_name} 0" 1
}

function ai_reset_counter {
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	reset_counter AI ${counter_name}
}

function decrement_counter {
	object_type=$1
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber decr ${osinstance}:${object_type}:${counter_name}" 1
}

function ai_decrement_counter {
	counter_name=`echo $1 | tr '[:upper:]' '[:lower:]'`
	decrement_counter AI ${counter_name}
}

function publish_msg {
	object_type=`echo $1 | tr '[:lower:]' '[:upper:]'`
	channel=$2
	msg=$3
	retriable_execution "$rediscli -h $oshostname -p $osportnumber -n $osdatabasenumber publish ${osinstance}:${object_type}:${channel} \"$msg\""
	}

function publishvm {
	$channel=$1
	$msg=$2
	publish_msg VM $channel $msg
	}

function publishai {
	$channel=$1
	$msg=$2
	publish_msg AI $channel $msg
	}
	
function subscribemsg {
	object=`echo $1 | tr '[:lower:]' '[:upper:]'`
	channel=$2
	message=$3
	${SUBSCRIBE_CMD} ${object} ${channel} $message
}

function subscribevm {
	channel=$1
	message=$2
	${SUBSCRIBE_CMD} VM ${channel} $message
}

function subscribeai {
	channel=$1
	message=$2
	${SUBSCRIBE_CMD} AI ${channel} $message
}

log_output_command=`get_my_ai_attribute log_output_command`
log_output_command=`echo ${log_output_command} | tr '[:upper:]' '[:lower:]'`
load_manager_ip=`get_my_ai_attribute load_manager_ip`

if [ x"${NC_HOST_SYSLOG}" == x ]; then
	if [ x"${osmode}" != x"scalable" ]; then
		NC_HOST_SYSLOG=`get_global_sub_attribute logstore hostname`
        NC_OPTIONS="-w1 -u"
	else 
		NC_HOST_SYSLOG=`get_my_ai_attribute load_manager_ip`
        NC_OPTIONS="-w1 -u -q1"
	fi
fi

if [ x"${NC_PORT_SYSLOG}" == x ]; then
	NC_PORT_SYSLOG=`get_global_sub_attribute logstore port`
fi

if [ x"${NC_FACILITY_SYSLOG}" == x ]; then
	NC_FACILITY_SYSLOG="<"`get_global_sub_attribute logstore script_facility`">"
fi

NC_CMD=${NC}" "${NC_OPTIONS}" "${NC_HOST_SYSLOG}" "${NC_PORT_SYSLOG}

function syslog_netcat {
	if [ $standalone == online ] ; then 
		echo "${NC_FACILITY_SYSLOG} - $SCRIPT_NAME: ${1}"
		echo "${NC_FACILITY_SYSLOG} - $SCRIPT_NAME: ${1}" | $NC_CMD &
	else
		echo "$1"
	fi
}

function refresh_hosts_file {

	if [ x"${my_ai_uuid}" != x"none" ]; then
		build_ai_mapping
    fi

    # Adding multiple names for the same IP in /etc/hosts
    # is not a problem. We have no control over what name
    # is handed out by DHCP, so just do it anyway
    echo "${my_ip_addr} ${HOSTNAME}" >> ${ai_mapping_file}

	syslog_netcat "Refreshing hosts file ... "
	sudo bash -c "rm -f /etc/hosts; echo '127.0.0.1 localhost' >> /etc/hosts; cat ${ai_mapping_file} >> /etc/hosts"
}

function provision_application_start {
	date +%s
}

function provision_application_stop {
	START=$1
	if [ "$standalone" = "offline" ] ; then
		syslog_netcat "Application Instance executed in \"standalone\" mode. Will not report application startup time"
		return
	fi
	if [ ! -e .appfirstrun ] ; then
		touch .appfirstrun
		END=$(date +%s)
		DIFF=$(( $END - $START ))
		syslog_netcat "Updating vm application startup time with value ${DIFF}"
		put_my_vm_attribute mgt_006_application_start $DIFF
	else
		syslog_netcat "Application Instance already deployed (once). Will not report application startup time (again)"	
	fi
}

function start_redis {
	is_redis_running=`ps aux | grep -v grep | grep -c redis.conf`
	if [ ${is_redis_running} -eq 0 ]
	then
		rm -rf ~/dump.rdb
		TMPLT_OBJSTORE_PORT=$1
		syslog_netcat "Updating object store configuration template"
		sed -i s/"TMPLT_PORT"/"${TMPLT_OBJSTORE_PORT}"/g ~/redis.conf
		sed -i s/"TMPLT_USERNAME"/"${LOGNAME}"/g ~/redis.conf
		syslog_netcat "Starting object store"
		REDIS_SERVER=`which redis-server`
		${REDIS_SERVER} ~/redis.conf
	fi
}

function start_syslog {
	is_syslog_running=`ps aux | grep -v grep | grep -c rsyslog.conf`
	if [ ${is_syslog_running} -eq 0 ]
	then 
		mkdir -p ~/logs
		TMPLT_LOGSTORE_PORT=$1
		sed -i s/"TMPLT_LOGSTORE_PORT"/"${TMPLT_LOGSTORE_PORT}"/g ~/rsyslog.conf
		sed -i s/"TMPLT_USERNAME"/"${LOGNAME}"/g ~/rsyslog.conf
		RSYSLOG=`sudo which rsyslogd`
		${RSYSLOG} -c 4 -f ~/rsyslog.conf -i ~/rsyslog.pid
	fi
}

function restart_ntp {
	is_ntp_service_name_ntpd=`ls -la /etc/init.d/ | grep -v ntpdate | grep -v open | grep -c ntpd`
	if [ ${is_ntp_service_name_ntpd} -eq 0 ]
	then
		ntp_service_name="ntp"
	else
		ntp_service_name="ntpd"
	fi
	syslog_netcat "Stopping ${ntp_service_name} service...." 
	sudo service ${ntp_service_name} stop
	syslog_netcat "Creating ${ntp_service_name} (ntp.conf) file"
	~/cb_create_ntp_config_file.sh
	syslog_netcat "Starting ${ntp_service_name} service...." 
	sudo service ${ntp_service_name} start
}

function online_or_offline {
	if [ x"$1" == x ] ; then
		echo online 
	else
		echo offline 
	fi
}

function standalone_verify {
	param=$1
	msg=$2
	if [ x"$param" == x ] ; then
		echo "$msg"
		exit 1
	fi
}

function post_boot_steps {
	standalone=$1

	if [ ! -e /usr/lib64 ]; then
		syslog_netcat "Creating symbolic link /usr/lib64 -> /usr/lib"
		sudo ln -s /usr/lib /usr/lib64
	fi

	# Do specific things for windows and exit
	if [ x"$(uname -a | grep CYGWIN)" != x ] ; then
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

    # Our CB images are missing a getty on tty0
    if [ x"$(lsb_release -d | grep -i ubuntu)" != x ] ; then
        syslog_netcat "This machine is Ubuntu. Making sure there's a getty on tty0..."
        sudo screen -d -m -S getty bash -c "sudo /sbin/getty -8 38400 tty0"
    fi

	if [ $standalone == online ] ; then
		syslog_netcat "Killing previously running ganglia monitoring processes on $SHORT_HOSTNAME"
		$SUDO_CMD $KILL_CMD screen 
		$SUDO_CMD $KILL_CMD gmond 
		sleep 3
		result="$(ps aux | grep gmond | grep -v grep)"
		if [ x"$result" == x ] ; then
			syslog_netcat "Ganglia monitoring processes killed successfully on $SHORT_HOSTNAME"
		else
			syslog_netcat "Ganglia monitoring processes could not be killed on $SHORT_HOSTNAME - NOK"
			exit 2
		fi
		syslog_netcat "Previously running ganglia monitoring processes killed $SHORT_HOSTNAME"
	fi

	# fix the db2 data authentication permissions first
	if [ x"$(echo $0 | grep cb_restart_db2)" != x ] || [ x"${my_role}" == x"db2" ] ; then
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

	if [ $standalone == online ] ; then
		sleep 1

		sudo bash -c "chmod 777 /dev/pts/*"
		restart_ntp
		sudo ln -sf ${dir}/../../3rd_party/monitor-core ~
		sudo ln -sf ${dir}/../../util ~

		# specweb VMs are 32-bit
		if [ ! -e /usr/lib64/ganglia ] && [ -e /usr/lib/ganglia ] ; then
			sudo ln -sf /usr/lib/ganglia/ /usr/lib64/ganglia
		fi

		if [ x"${my_ai_uuid}" != x"none" ]; then
			syslog_netcat "Copying application-specific scripts to the home directory"
			ln -sf "${dir}/../${my_base_type}/"* ~
		fi

		if [ x"${collect_from_guest}" == x"true" ]; then
			syslog_netcat "Collect from Guest is ${collect_from_guest}"
			syslog_netcat "Creating ganglia (gmond) file"
			~/cb_create_gmond_config_file.sh
			syslog_netcat "Restarting ganglia monitoring processes (gmond) on $SHORT_HOSTNAME"
			GANGLIA_FILE_LOCATION=~
			eval GANGLIA_FILE_LOCATION=${GANGLIA_FILE_LOCATION}
			sudo pkill -9 -f gmond
            sudo screen -d -m -S gmond bash -c "while true ; do sleep 10; if [ x\`$PIDOF_CMD gmond\` == x ] ; then gmond -c ${GANGLIA_FILE_LOCATION}/gmond-vms.conf; fi; done"
			result="$(ps aux | grep gmond | grep -v grep)"
			if [ x"$result" == x ] ; then
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
				sudo pkill -9 -f gmetad

				$GMETAD_PATH/gmetad.py -c ~/gmetad-vms.conf -d 1
#				$GMETAD_PATH/gmetad.py -c ~/gmetad-vms.conf --syslogn 127.0.0.1 --syslogp 6379 --syslogf 22 -d 4

				result="$(ps aux | grep gmeta | grep -v grep)"
				if [ x"$result" == x ] ; then
					syslog_netcat "Ganglia meta process (gmetad) could not be restarted on $SHORT_HOSTNAME - NOK"
					exit 2
				else
					syslog_netcat "Ganglia meta process (gmetad) restarted successfully on $SHORT_HOSTNAME"
				fi
			fi
		else
			syslog_netcat "Collect from Guest is ${collect_from_guest}"
			sleep 2
			syslog_netcat "Bypassing the gmond and gmetad restart"
		fi
	fi
}

function get_offline_ip {
	ip -o addr show $(ip route | grep default | grep -oE "dev [a-z]+[0-9]+" | sed "s/dev //g") | grep -Eo "[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*" | grep -v 255
}
