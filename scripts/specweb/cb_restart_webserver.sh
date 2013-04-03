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
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

standalone=`online_or_offline "$1"`

if [ $standalone == offline ] ; then
	post_boot_steps offline 
fi

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
syslog_netcat "restarting webserver on ${SHORT_HOSTNAME}" 
sudo kill -9 $(pidof php5) 2>/dev/null
sudo kill -9 $(pidof httpd) 2>/dev/null
sudo /etc/init.d/apache2 restart 2>/dev/null | while read line ; do 
	syslog_netcat "$line" &
done

provision_application_stop $START
