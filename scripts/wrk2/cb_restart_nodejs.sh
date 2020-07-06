#!/usr/bin/env bash
#/*******************************************************************************
# Copyright (c) 2019 DigitalOcean

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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

START=`provision_application_start`
LOAD_PROFILE=$(get_my_ai_attribute load_profile)

linux_distribution

chmod +x $dir/backend.js

is_nodejs_running=$(sudo ps aux | grep node | grep -v grep | grep "backend.js")
if [[ x"${is_nodejs_running}" == x ]]
then
    syslog_netcat "Starting Nodejs server on ${SHORT_HOSTNAME}"
	sudo screen -d -m -S NODEJSSERVER bash -c "$dir/backend.js"
	wait_until_port_open 127.0.0.1 80 20 5
fi

# The backend will always be non-ssl via haproxy SSL termination.
wget -N -P /tmp http://${my_ip_addr}

STATUS=$?

if [[ $STATUS -ne 0 ]]
then
    syslog_netcat "Nodejs server is not listening on ${SHORT_HOSTNAME} - NOK"
else
    syslog_netcat "Nodejs server is listening on ${SHORT_HOSTNAME} - OK"
fi

provision_application_stop $START
exit ${STATUS}
