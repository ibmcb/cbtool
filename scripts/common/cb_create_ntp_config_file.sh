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

TIMESERVER=`get_global_sub_attribute mon_defaults timeserver`

NTP_CONF_FILE=~/ntp.conf

syslog_netcat "Force ntp time synchronization with server ${TIMESERVER}"
sudo ntpdate ${TIMESERVER}
sudo mkdir -p /etc/ntp

echo "driftfile /etc/ntp/ntp.drift" > ${NTP_CONF_FILE}
echo "tracefile /etc/ntp/ntp.trace" >> ${NTP_CONF_FILE}
echo "logfile /etc/ntp/ntp.log" >> ${NTP_CONF_FILE}

TIMESERVER=$(echo $TIMESERVER | sed 's/,/ /g')
for TIMESRVNODE in $TIMESERVER
do
    echo "server ${TIMESERVER}" >> ${NTP_CONF_FILE}
done

sudo /bin/cp ${NTP_CONF_FILE} /etc/ntp.conf
sudo /bin/cp ${NTP_CONF_FILE} /var/lib/ntp/ntp.conf.dhcp