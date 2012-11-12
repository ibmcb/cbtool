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

pushd `dirname $0` > /dev/null
dir=$(pwd)
popd

TARGET=$1
PORT_NUMBER=$2
PYTHON_PROXY_SCRIPT=$3
IAAS_ACCESS_ID=$4
IAAS_ENDPOINT=$5
IAAS_PRIVATE_KEY=$6
IAAS_SERVICE_PUBLIC_KEY=$7
IAAS_TIMEOUT=300

is_proxy_python_running=`ssh root@${TARGET} "ps aux | grep -v grep | grep -c scp_*python_proxy.rb"`

if [ ${is_proxy_python_running} -eq 1 ]
then
	echo "Python proxy is already running on VM ${TARGET}"
	exit 0
else
	echo "Python proxy is not running on VM ${TARGET}"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "pkill -9 -f python_proxyd"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "pkill -9 -f scp2_python_proxy.rb"
	TRANSFER=`rsync -e "ssh -o StrictHostKeyChecking=no -l root" -az $dir/${PYTHON_PROXY_SCRIPT} ${TARGET}:~`
	ECODE=$?
	
	if [ ${ECODE} -ne 0 ]
	then
		exit 3
	fi

	# Had to do this to make it work on SCP v1. Some stray "'" single-quote
	# character kept screwing up the SSH command.
	# Please do not change unless backwards-tested on v1

	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo \"#!/bin/bash\" > /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo export IAAS_ACCESS_ID=\"$IAAS_ACCESS_ID\" >> /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo export IAAS_ENDPOINT=\"$IAAS_ENDPOINT\" >> /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo export IAAS_PRIVATE_KEY=\"$IAAS_PRIVATE_KEY\"  >> /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo export IAAS_SERVICE_PUBLIC_KEY=\"$IAAS_SERVICE_PUBLIC_KEY\"  >> /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "echo export IAAS_TIMEOUT=\"$IAAS_TIMEOUT\" >> /tmp/iaasrc.cb"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "screen -dmS python_proxyd; sleep 2"
	ssh -o StrictHostKeyChecking=no root@${TARGET} "screen -S python_proxyd -p 0 -X stuff \"source /tmp/iaasrc.cb; ruby ${PYTHON_PROXY_SCRIPT} $PORT_NUMBER\"$(printf \\r)"

fi
exit 0
