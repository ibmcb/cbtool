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

USEBALLOON=no

DB_IP=`get_ips_from_role db2`
USEBALLOON=`get_my_ai_attribute_with_default use_java_balloon $USEBALLOON`
ECLIPSED=`get_my_vm_attribute eclipsed`

START=`provision_application_start`
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
SUDO_CMD=`which sudo`
PKILL_CMD=`which pkill`
ATTEMPTS=3

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
    mem=`get_my_ai_attribute_with_default jvm_size`
    syslog_netcat "Setting up WAS to support eclipsing: $mem MB"
else
    ((mem=mem/1024))
fi

((initial=mem/4))
((mem=mem-$range))

syslog_netcat "Checking if the WAS server is pointing to DB2 server running on $DB_IP......"
if [ x"name=\"serverName\" type=\"java.lang.String\" value=\"$DB_IP\"" == x"$(grep -oE "name=\"serverName\" type=\"java.lang.String\" value=\".*\"" /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/config/cells/glasgowNode01Cell/nodes/glasgowNode01/resources.xml | uniq)" ] ; then
    syslog_netcat "WAS on $SHORT_HOSTNAME is pointing to DB2 running on $DB_IP."
else
    syslog_netcat "WAS on $SHORT_HOSTNAME is NOT pointing to DB2 running on $DB_IP. It needs to be configured and restarted."
    syslog_netcat "Killing all WAS processes...."
    for pid in $(pgrep -f "(java|jballoon)") ; do
    kill -9 $pid > /dev/null
    done
    syslog_netcat "Done killing all WAS processes"
    
    syslog_netcat "Changing configuration file to point the WAS server to DB2 server running on $DB_IP...."
    $SUDO_CMD sed -ie "s/name=\"serverName\" type=\"java.lang.String\" value=\".*\"/name=\"serverName\" type=\"java.lang.String\" value=\"$DB_IP\"/g" /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/config/cells/glasgowNode01Cell/nodes/glasgowNode01/resources.xml
    $SUDO_CMD rm -rf  /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/wstemp/*
    syslog_netcat "Done changing configuration file to point the WAS server to DB2 server running on $DB_IP"
    syslog_netcat "WAS will be restarted on $SHORT_HOSTNAME on 5 seconds....."
    sleep 5
fi

while [[ "$ATTEMPTS" -ge  0 ]]
do

    syslog_netcat "Checking for a WAS running on $SHORT_HOSTNAME...."
    result="$(ps -ef | grep WebSphere | grep -v grep)"
    sudo rm -rf /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/core.*
    sudo rm -rf /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/javacore.*
    sudo rm -rf /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/heapdump.*
    sudo rm -rf /opt/was-install/WebSphere/AppServer/profiles/AppSrv01/Snap.*
    syslog_netcat "Done checking for a WAS server running on $SHORT_HOSTNAME"
    
    if [[ x"$result" == x ]]
    then
        syslog_netcat "There is no WAS running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"

        syslog_netcat "Enabling PMI infrastructure on $SHORT_HOSTNAME"
        echo -e "AdminConfig.modify('(cells/glasgowNode01Cell/nodes/glasgowNode01/servers/server1|server.xml#PMIService_1183122130078)', '[[enable true] [synchronizedUpdate false] [statisticSet all]]')\nAdminConfig.save()\n" | $SUDO_CMD /opt/was-install/WebSphere/AppServer/bin/wsadmin.sh -conntype NONE -lang jython > /dev/null 2>&1
        syslog_netcat "Done enabling PMI infrastucture on $SHORT_HOSTNAME"

        syslog_netcat "Setting JVM heap size...."
        $SUDO_CMD /opt/was-install/WebSphere/AppServer/bin/wsadmin.sh -conntype NONE -lang jython -f $dir/cb_changeWASheap.py $initial $mem | while read line ; do syslog_netcat "$line" ; done

        syslog_netcat "Done setting JVM heap size"

        let ATTEMPTS=ATTEMPTS-1
        syslog_netcat "Killing any WAS leftover processes...."
        for pid in $(pgrep -f "(java|jballoon)")
        do
            kill -9 $pid > /dev/null
        done
        syslog_netcat "Done killing any WAS leftover processes...."
        syslog_netcat "Starting WAS..."
        sudo /opt/was-install/WebSphere/AppServer/bin/startServer.sh server1 -trace | while read line ; do syslog_netcat "$line" ; done
        syslog_netcat "WAS started on $SHORT_HOSTNAME ( pointing to DB2 running on $DB_IP )."
        syslog_netcat "Will wait 5 seconds and check for WAS processes...."
        sleep 5
    else 
        syslog_netcat "WAS restarted successfully on $SHORT_HOSTNAME ( pointing to DB2 running on $DB_IP ) - OK";

        if [[ x"$USEBALLOON" == xyes ]]
        then
            if [[ x"$(ps -ef | grep -v grep | grep jballoon_controller)" == x ]]
            then
                CMD="nohup ./cb_jballoon_controller.sh $mem $range $jballoon_wait"
                syslog_netcat "Starting jballoon controller with $CMD"
                ($CMD &)
            else 
                syslog_netcat "WAS jballoon already running on $SHORT_HOSTNAME ( pointing to DB2 running on $DB_IP )"
            fi
        fi
    
        if [[ -f .appfirstrun ]]
        then
            exit 0
        else
            provision_application_stop $START
            exit 0
        fi
    fi
done
syslog_netcat "WAS could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
