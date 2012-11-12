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

mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`

# amount of mem to reserve for the guest OS, the rest will be 
# assigned to the JVM
#range=600
range=0

# seconds to wait before the jballoon controller
# check if the memory assignmented changed (balloon size)
jballoon_wait=60

((mem=mem/1024))
#mem=2048
((initial=mem/4))
#initial=2048
((mem=mem-$range))

if [ -z "${DB_IP}" ]
then
	syslog_netcat "No \"DB2\" VM was created. Will use a Derby database, co-located with this WAS VM"
else
	syslog_netcat "Checking if the WAS server is pointing to DB2 server running on $DB_IP......"

	SERVERXMLPATH="/opt/wlp/usr/servers/tradeLiteServer/server.xml"
    result2="$(grep -c serverName=\"$DB_IP\" $SERVERXMLPATH )"

	if [[ x$result2 == x1 ]] ; then
		syslog_netcat "WAS on $SHORT_HOSTNAME is pointing to DB2 running on $DB_IP."
	else
		syslog_netcat "WAS on $SHORT_HOSTNAME is NOT pointing to DB2 running on $DB_IP. It needs to be configured and restarted."
		syslog_netcat "Killing all WAS processes...."
		sudo /opt/wlp/bin/server stop tradeLiteServer | while read line ; do syslog_netcat "$line" ; done
		syslog_netcat "Done killing all WAS processes"

		syslog_netcat "Changing configuration file to point the WAS server to DB2 server running on $DB_IP...."

		rm -rf /tmp/temp$$.txt
		cat >/tmp/temp$$.txt  <<EOF12345
<server>
	<featureManager>
		<feature>jsp-2.2</feature>
		<feature>jdbc-4.0</feature>
	</featureManager>
	<httpEndpoint id="defaultHttpEndpoint" host="*" httpPort="\${tradelite.http.port}">
		<tcpOptions soReuseAddr="true" />
	</httpEndpoint>
	<application type="war" id="tradelite" name="tradelite" location="\${shared.app.dir}/webcontainer/tradelite.war" />
	<jdbcDriver id="DB2JCC" libraryRef="DB2JCCLib"/>
	<library id="DB2JCCLib" filesetRef="DB2JCCFileset"/>
	<fileset id="DB2JCCFileset" dir="\${shared.resource.dir}/db2" includes="*.jar"/>
	<dataSource jndiName="jdbc/TradeDataSource" jdbcDriverRef="DB2JCC" id="TradeDataSource" statementCacheSize="60">
		<properties serverName="$DB_IP" portNumber="50007" databaseName="tradedb" driverType="4" user="klabuser" password="ki0000ki" />
    </dataSource>
	<executor name="LargeThreadPool" id="default" coreThreads="50" maxThreads="100" keepAlive="60s" stealPolicy="LOCAL" rejectedWorkPolicy="CALLER_RUNS" />
</server> 
EOF12345
	$SUDO_CMD /bin/cp /tmp/temp$$.txt $SERVERXMLPATH
	$SUDO_CMD /bin/rm /tmp/temp$$.txt
	$SUDO_CMD /bin/rm -rf /opt/wlp/usr/servers/tradeLiteServer/workarea
	$SUDO_CMD /bin/mkdir /opt/wlp/usr/servers/tradeLiteServer/workarea
	$SUDO_CMD /bin/chmod a+rx /opt/wlp/usr/servers/tradeLiteServer/workarea

	syslog_netcat "sudo return code $?"
	syslog_netcat "looking at path $SERVERXMLPATH on $(hostname)"
	ls -al $SERVERXMLPATH | syslog_netcat
	syslog_netcat "Done changing configuration file to point the WAS server to DB2 server running on $DB_IP"
	syslog_netcat "WAS will be restarted on $SHORT_HOSTNAME on 20 seconds....."
	sleep 20
	fi
fi


while [ "$ATTEMPTS" -ge  0 ] ; do 
    
    syslog_netcat "Checking for a WAS running on $SHORT_HOSTNAME...."
    result="$(ps -ef | grep tradeLiteServer | grep -v grep)"
    syslog_netcat "Done checking for a WAS server running on $SHORT_HOSTNAME"
    
    if [ x"$result" == x ] ; then        
        syslog_netcat "There is no WAS running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"
        syslog_netcat "WAS will be restarted on $SHORT_HOSTNAME"

        let ATTEMPTS=ATTEMPTS-1
        syslog_netcat "Gently stopping tradelite...."
		sudo /opt/wlp/bin/server stop tradeLiteServer | while read line; do syslog_netcat "$line" ; done

        syslog_netcat "Killing any WAS leftover processes...."
		for pid in $(pgrep -f java) ; do
			kill -9 $pid > /dev/null
		done
        syslog_netcat "Done killing any WAS leftover processes...."
        syslog_netcat "Starting WAS once..."
        sudo /opt/wlp/bin/server start tradeLiteServer | while read line ; do syslog_netcat "$line" ; done
        syslog_netcat "Done starting WAS once"

        syslog_netcat "Will wait 30 seconds and check for WAS processes...."
        sleep 30    
    else
		if [ -z "${DB_IP}" ]
		then
        	syslog_netcat "WAS restarted successfully on $SHORT_HOSTNAME ( pointing to Derby DB running on the same host) - OK";
		else
			syslog_netcat "WAS restarted successfully on $SHORT_HOSTNAME ( pointing to DB2 running on $DB_IP ) - OK";
		fi
        
        if [ x"$USEBALLOON" == xyes ]
        then
            if [ x"$(ps -ef | grep -v grep | grep jballoon_controller)" == x ]
			then
            	# "nohup" seems to be a problem for paramiko. Perhaps it could be executed inside a daemonized screen
                (nohup ./cb_jballoon_controller.sh $mem $range $jballoon_wait >> /tmp/jballoon_controller_log.txt &)
            else 
                syslog_netcat "WAS jballoon already running on $SHORT_HOSTNAME ( pointing to DB2 running on $DB_IP )"
            fi
        fi

		if [ -f .appfirstrun ];
		then
        	sleep 5
			# reload db each time to be safe
        	syslog_netcat "Performing resetTrade..."
        	curl "http://localhost:9080/tradelite/config?action=resetTrade" | tail -30 | while read line ; do syslog_netcat "$line" ; done
        	sleep 5 # again just to be sure
        	syslog_netcat "Performing buildDB..."
        	curl "http://localhost:9080/tradelite/config?action=buildDB" | tail -30 | while read line ; do syslog_netcat "$line" ; done
			exit 0
		else
			provision_application_stop $START
			exit 0
		fi
    fi
done
syslog_netcat "WAS could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2