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
cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_java_home

MYSQL_DATABASE_NAME=`get_my_ai_attribute_with_default mysql_database_name tradedb`
MYSQL_NONROOT_USER=`get_my_ai_attribute_with_default mysql_nonroot_user trade`
MYSQL_NONROOT_PASSWORD=`get_my_ai_attribute_with_default mysql_nonroot_password trade`
MYSQL_DATA_DIR=`get_my_ai_attribute_with_default mysql_data_dir /tradedb`

USEBALLOON=no
ECLIPSED=False

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
NETSTAT_CMD=`which netstat`
SUDO_CMD=`which sudo`
ATTEMPTS=3

DB_IP=`get_ips_from_role mysql`

START=`provision_application_start`

DT_MYSQL_PLAN=$(find ~ | grep target/classes/daytrader-mysql-xa-plan.xml | grep -v orig | head -1)
DT_EAR=$(find ~ | find ~ | grep daytrader-ear-[0-9]\.[0-9]\.[0-9]\.ear | head -1)

GERONIMO_DEPLOY=$(find ~ | grep bin/deploy | grep -v bat | grep -v framework)
GERONIMO_MAIN=$(find ~ | grep bin/geronimo | grep -v bat | grep -v framework)
GERONIMO_PROPERTIES=$(find ~ | grep -v karaf | grep /etc/config.properties)

${SUDO_CMD} chown -R $(whoami):$(whoami) ~/daytrader-parent*
${SUDO_CMD} chown -R $(whoami):$(whoami) ~/geronimo-tomcat*

#syslog_netcat "Undeploying any old DayTraders"
#$GERONIMO_DEPLOY --user system --password manager undeploy org.apache.geronimo.daytrader/daytrader/3.0.0/car

syslog_netcat "Checking if the Geronimo server is pointing to MySQL server running on $DB_IP......"

syslog_netcat "Changing configuration file to point the Geronimo server to MySQL server running on $DB_IP...."
    
syslog_netcat "Trying.. sed command output.. next:"
${SUDO_CMD} sed -i "s/<config\-property\-setting name=\"ServerName\">.*<\/config\-property\-setting>/<config\-property\-setting name=\"ServerName\">"$DB_IP"<\/config\-property\-setting>/g" $DT_MYSQL_PLAN
syslog_netcat "SED Error: $?"
JAVA_VERSION=$(${JAVA_HOME}/bin/java -version 2>&1 | grep version | awk '{ print $3 }' | sed 's/"//g' | cut -d '.' -f 2)
${SUDO_CMD} sed -i "s/jre-1.7=/jre-1.${JAVA_VERSION}=/g" $GERONIMO_PROPERTIES
syslog_netcat "SED Error: $?"

syslog_netcat "Done changing configuration file to point the Geronimo server to MySQL server running on $DB_IP"

mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`

# amount of mem to reserve for the guest OS, the rest will be 
# assigned to the JVM
if [[ $USEBALLOON == yes ]]
then
    syslog_netcat "Java Balloon Activated"
    range=600
else
    range=0
fi

# seconds to wait before the jballoon controller
# check if the memory assignmented changed (balloon size)
jballoon_wait=20

if [[ $USEBALLOON == yes && $ECLIPSED == "True" ]]
then
    mem=`get_my_vm_attribute vmemory_max`
    syslog_netcat "Setting up Geronimo to support eclipsing: $mem MB"
else
    ((mem=mem/1024))
fi

((initial=mem/4))
((mem=mem-$range))

syslog_netcat "Geronimo will be restarted on $SHORT_HOSTNAME on 5 seconds....."
sleep 5

while [[ "$ATTEMPTS" -ge  0 ]]
do 
    
    syslog_netcat "Checking for a Geronimo running on $SHORT_HOSTNAME...."
    ${SUDO_CMD} bash -c "export JAVA_HOME=$JAVA_HOME; export PATH=$PATH; $GERONIMO_DEPLOY --user system --password manager list-modules" | grep -Fq "+ org.apache.geronimo.daytrader/daytrader/3.0.0/car"
    DAYTRADER_NOT_LOADED=$?    
    syslog_netcat "Done checking for a Geronimo server running on $SHORT_HOSTNAME with DayTrader"
    
    if [[ $DAYTRADER_NOT_LOADED -ne 0 ]]
    then        
        syslog_netcat "There is no Geronimo running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"

        let ATTEMPTS=ATTEMPTS-1
        syslog_netcat "Killing any Geronimo leftover processes...."
        for pid in $(pgrep -f "(java)")
        do
            ${SUDO_CMD} kill -9 $pid > /dev/null
        done
        syslog_netcat "Done killing any Geronimo leftover processes...."
        syslog_netcat "Starting Geronimo..."
        ${SUDO_CMD} bash -c "export JAVA_HOME=$JAVA_HOME; export PATH=$PATH; ${GERONIMO_MAIN} start"
        syslog_netcat "Geronimo started on $SHORT_HOSTNAME ( pointing to MySQL running on $DB_IP )."
        syslog_netcat "Will wait 30 seconds and check for Geronimo processes...."
        sleep 30 
        syslog_netcat "Undeploy previous DayTrader(s)"
        ${SUDO_CMD} bash -c "export JAVA_HOME=$JAVA_HOME; export PATH=$PATH; ${GERONIMO_DEPLOY} --user system --password manager undeploy org.apache.geronimo.daytrader/daytrader/3.0.0/car"
        sleep 10 
        syslog_netcat "Deploy DayTrader ($DT_MYSQL_PLAN)"
        ${SUDO_CMD} bash -c "export JAVA_HOME=$JAVA_HOME; export PATH=$PATH; ${GERONIMO_DEPLOY} --user system --password manager deploy $DT_EAR $DT_MYSQL_PLAN"
        sleep 10 
    else 
        syslog_netcat "Geronimo restarted successfully on $SHORT_HOSTNAME ( pointing to MySQL running on $DB_IP ) - OK";
        provision_application_stop $START
        exit 0        
    fi
done
syslog_netcat "Geronimo could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
    
