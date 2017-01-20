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

DB_IP=`get_ips_from_role db2`
START=`provision_application_start`
LOAD_BALANCER_TARGET=`get_my_ai_attribute load_balancer_target_role`
LOAD_BALANCER_TARGET_PORT=`get_my_ai_attribute load_balancer_target_port`
LOAD_BALANCER_TARGET_URL=`get_my_ai_attribute load_balancer_target_url`
LOAD_BALANCER_TARGET_IPS=`get_my_ai_attribute load_balancer_target_ip`

LOAD_BALANCER_TARGET_IPS_CSV=`echo ${LOAD_BALANCER_TARGET_IPS} | sed ':a;N;$!ba;s/\n/, /g'`
LOAD_BALANCER_TARGET_IPS=`echo ${LOAD_BALANCER_TARGET_IPS} | sed -e 's/, */ /g'`

# TARGET IPS has a comma in it, get rid of it

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
ATTEMPTS=3

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
