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

USEBALLOON=no

if [ $standalone == online ] ; then
	DB_IP=`get_ips_from_role db2`
	USEBALLOON=`get_my_ai_attribute_with_default use_java_balloon $USEBALLOON`
	ECLIPSED=`get_my_vm_attribute eclipsed`
else
	standalone_verify "$2" "Need ip address of database."
	DB_IP=$2
	post_boot_steps offline 
	ECLIPSED="false"
fi

START=`provision_application_start`
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
SUDO_CMD=`which sudo`
PKILL_CMD=`which pkill`
ATTEMPTS=3

syslog_netcat "Undeploying any old DayTraders"

/home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager undeploy org.apache.geronimo.daytrader/daytrader/3.0.0/car

syslog_netcat "Checking if the Geronimo server is pointing to MySQL server running on $DB_IP......"

syslog_netcat "Changing configuration file to point the Geronimo server to MySQL server running on $DB_IP...."
	
syslog_netcat "Trying.. sed command output.. next:"
sed "s/<config\-property\-setting name=\"ServerName\">.*<\/config\-property\-setting>/<config\-property\-setting name=\"ServerName\">"$DB_IP"<\/config\-property\-setting>/g" /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml > /home/cbtool/tmp.xml && mv /home/cbtool/tmp.xml /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml

syslog_netcat "SED Error: $?"

syslog_netcat "Done changing configuration file to point the Geronimo server to MySQL server running on $DB_IP"


mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`

# amount of mem to reserve for the guest OS, the rest will be 
# assigned to the JVM
if [ $USEBALLOON == yes ] ; then
	syslog_netcat "Java Balloon Activated"
	range=600
else
	range=0
fi

# seconds to wait before the jballoon controller
# check if the memory assignmented changed (balloon size)
jballoon_wait=20

if [ $USEBALLOON == yes ] && [ $ECLIPSED == "True" ] ; then
	mem=`get_my_vm_attribute vmemory_max`
	syslog_netcat "Setting up Geronimo to support eclipsing: $mem MB"
else
	((mem=mem/1024))
fi

((initial=mem/4))
((mem=mem-$range))

syslog_netcat "Geronimo will be restarted on $SHORT_HOSTNAME on 5 seconds....."
sleep 5

while [ "$ATTEMPTS" -ge  0 ] ; do 
    
    syslog_netcat "Checking for a Geronimo running on $SHORT_HOSTNAME...."
    result="$(sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager list-modules | grep -Fxq \"+ org.apache.geronimo.daytrader/daytrader/3.0.0/car\")"
    sslog_netcat "Done checking for a Geronimo server running on $SHORT_HOSTNAME with DayTrader"
    
    if [ x"$result" == x ] ; then        
		syslog_netcat "There is no Geronimo running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"

		let ATTEMPTS=ATTEMPTS-1
		syslog_netcat "Killing any Geronimo leftover processes...."
		for pid in $(pgrep -f "(java)") ; do
			kill -9 $pid > /dev/null
		done
		syslog_netcat "Done killing any Geronimo leftover processes...."
		syslog_netcat "Starting Geronimo..."
		sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/geronimo start
		syslog_netcat "Geronimo started on $SHORT_HOSTNAME ( pointing to MySQL running on $DB_IP )."
		syslog_netcat "Will wait 30 seconds and check for Geronimo processes...."
		sleep 30 
		syslog_netcat "Undeploy previous DayTrader(s)"
		sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager undeploy org.apache.geronimo.daytrader/daytrader/3.0.0/car
		sleep 10 
		syslog_netcat "Deploy DayTrader"
		sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager deploy /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/assemblies/daytrader-ear/target/daytrader-ear-3.0.0.ear /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml
		sleep 10 

		syslog_netcat "Checking for DayTrader"
		if sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager list-modules | grep -Fxq "+ org.apache.geronimo.daytrader/daytrader/3.0.0/car"
		then
			syslog_netcat "DayTrader is running"
		else 
			syslog_netcat "DayTrader not running, trying again"		
			sudo /home/cbtool/daytrader/geronimo-tomcat7-javaee6-3.0.0/bin/deploy --user system --password manager deploy /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/assemblies/daytrader-ear/target/daytrader-ear-3.0.0.ear /home/cbtool/daytrader/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml
		fi	
    else 
		syslog_netcat "Geronimo restarted successfully on $SHORT_HOSTNAME ( pointing to MySQL running on $DB_IP ) - OK";

    fi
	
    if [ -f .appfirstrun ]; then
	exit 0
    else
	provision_application_stop $START
	exit 0
    fi
done
syslog_netcat "Geronimo could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
