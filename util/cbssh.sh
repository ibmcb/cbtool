#!/usr/bin/env bash

dir="$(dirname "$(readlink -f "$0")")"

if [[ -z $1 ]]
then
    echo "need a VM cloudbench identifier (e.g. vm_10)"
    echo "usage $0 <VM IDENTIFIER> [CLOUD CONFIGURATION FILE]"
    exit 1
fi
VMID=$1

docker=$(which docker)
CONFIG_FILE=
if [[ x"$docker" != x ]] ; then
	RUNNING_DOCKER=$(sudo ${docker} ps -a 2>&1 | grep ${USER} | grep cbon)
fi
# FIXME: This broke regular cbssh because it drops into this target instead of the fallthrough.
# Please try to detect docker usage with another workaround.
if [[ ! false ]] && [[ x"$docker" != x ]] && [[ $? -eq 0 ]]
then
	CB_DOCKER="docker exec -it $(echo $RUNNING_DOCKER 2>&1 | awk '{ print $1 }')" 
	CB_EXECUTABLE=/home/cbuser/repos/cloudbench/cb
else 
	RUNNING_CB=$(sudo ps aux | grep -v grep | grep -e "python.*cb " | grep "\-c")
	if [[ $? -eq 0 ]]
	then
	    for WORD in $RUNNING_CB
	    do
	    
	        if [[ CONFIG_FILE -eq 1 ]]
	        then
	            CONFIG_FILE=$WORD
	            break
	        fi
	        
	        if [[ $WORD == "--config" || $WORD == "-c" ]]
	        then
	            CONFIG_FILE=1
	        fi
	    done
	 fi
	
	if [[ ! -z $3 ]]
	then
	    CONFIG_FILE=$3
	fi
	
	if [[ ! -z $CONFIG_FILE ]]
	then
	    CONFIG_FILE="--config $CONFIG_FILE"
	fi

	if [[ ! -z $2 ]]
	then
	    CB_EXECUTABLE=$2/cb
	else
	    CB_EXECUTABLE=$dir/../cb
	fi
	
	if [[ ! -f $CB_EXECUTABLE ]]
	then
	    echo "Unable to find CB executable in $CB_EXECUTABLE. Please specificy a directory for it with $0 <VM IDENTIFIER> [CB DIR] [CLOUD CONFIGURATION FILE]"
	    exit 1
	fi
fi

INFO=$($CB_DOCKER $CB_EXECUTABLE $CONFIG_FILE vmshow $VMID)

VMIP=$(echo "$INFO" | grep "|prov_cloud_ip" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)
VMLOGIN=$(echo "$INFO" | grep "|login" | grep -v "login=" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)
VMKEY=$(echo "$INFO" | grep "|identity" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | sed 's/\$//g' | tr -d '\r' | cut -d " " -f 2)
VMSSHCONF=$(echo "$INFO" | grep "|ssh_config_file" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)
VMSSHPORT=$(echo "$INFO" | grep "|prov_cloud_port" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)

if [[ ${#VMIP} -eq 0 ]]
then
    echo "Unable to get IP address for ${VMID} ($VMIP)"
    exit 1
fi

if [[ ${#VMLOGIN} -eq 0 ]]
then
    echo "Unable to get login for ${VMID} ($VMLOGIN)"
    exit 1
else :
    SSH_CMD_PART5="-l $VMLOGIN"
fi

if [[ ${#VMKEY} -eq 0 ]]
then
    echo "Unable to get private key file path for ${VMID} ($VMKEY)"
    exit 1
else :
    SSH_CMD_PART1="-i $VMKEY"
fi

if [[ ${#VMSSHPORT} -ne 0 ]]
then
    SSH_CMD_PART3="-p $VMSSHPORT"
fi

if [[ ${#VMSSHCONF} -eq 0 ]]
then
    SSH_CMD_PART2=""
else :
    SSH_CMD_PART2="-F $VMSSHCONF"
fi

SSH_CMD_PART4="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes"

echo "logging in: cloudbench ID: $VMID => $VMLOGIN@$VMIP"

$CB_DOCKER ssh ${SSH_CMD_PART1} ${SSH_CMD_PART2} ${SSH_CMD_PART3} ${SSH_CMD_PART4} ${SSH_CMD_PART5} $VMIP "${*:2}"

echo -e "\n\nExit code for command \nssh ${SSH_CMD_PART1} ${SSH_CMD_PART2} ${SSH_CMD_PART3} ${SSH_CMD_PART4} ${SSH_CMD_PART5} $VMIP \"${*:2}\"\nhas the value of $?"
