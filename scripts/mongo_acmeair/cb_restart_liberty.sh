#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_acmeair_common.sh

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} $WLP_SERVERDIR

liberty_server_status=$(curl -s -o /dev/null -w "%{http_code}" http://${liberty_ip}:${ACMEAIR_HTTP_PORT}/index.html)

if [[ $liberty_server_status -eq 200 ]]
then
    syslog_netcat "Liberty server, with AcmeAir Application, is already running"
    exit 0
else    
    syslog_netcat "Liberty server is not running. Starting Liberty server with AcmeAir Application"
fi

sudo ls -la $WLP_SERVERDIR/usr/servers/acmeair > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    cd $WLP_SERVERDIR
    bin/server create acmeair
    cd ~
    sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} $WLP_SERVERDIR    
fi
    
sudo ls -la $WLP_SERVERDIR/usr/servers/acmeair/apps/*.war > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
#    ACMEAIR_APP=$(find $ACMEAIR_PATH | grep acmeair-webapp-.*war | head -n 1)
	cp ~/mileage.csv $ACMEAIR_PATH/src/main/resources/mileage.csv
	cd ~/acmeair
	mvn clean package
	ACMEAIR_APP=$(find $ACMEAIR_PATH | grep acmeair-java-.*war | head -n 1)	
	cd ~
    sudo cp $ACMEAIR_APP $WLP_SERVERDIR/usr/servers/acmeair/apps/
else 
	ACMEAIR_APP=$(find $ACMEAIR_PATH | grep acmeair-java-.*war | head -n 1)		
fi

ACMEAIR_APP=$(echo $ACMEAIR_APP | rev | cut -d '/' -f1 | rev)

MONGODB_JAVA_DRIVER=$(sudo find $WLP_SERVERDIR | grep mongo-java-driver-.*.jar | head -n 1 | sed "s^$WLP_SERVERDIR/usr/shared/resources^^g")

sudo cp ~/template_server.xml $WLP_SERVERDIR/usr/servers/acmeair/server.xml

sudo sed -i "s^REPLACE_MONGODB_JAVA_DRIVER^$MONGODB_JAVA_DRIVER^g" $WLP_SERVERDIR/usr/servers/acmeair/server.xml
sudo sed -i "s^REPLACE_ACMEAIR_APP^$ACMEAIR_APP^g" $WLP_SERVERDIR/usr/servers/acmeair/server.xml
sudo sed -i "s^REPLACE_MONGOS_IP^$mongos_ip^g" $WLP_SERVERDIR/usr/servers/acmeair/server.xml
sudo sed -i "s^REPLACE_ACMEAIR_HTTP_PORT^$ACMEAIR_HTTP_PORT^g" $WLP_SERVERDIR/usr/servers/acmeair/server.xml
sudo sed -i "s^REPLACE_ACMEAIR_HTTPS_PORT^$ACMEAIR_HTTPS_PORT^g" $WLP_SERVERDIR/usr/servers/acmeair/server.xml

#cat > $ACMEAIR_PROPERTIES <<EOF
#hostname=$mongos_ip
#port=27017
#dbname=acmeair
##username=dbuser
##password=1234
##connectionsPerHost=
##minConnectionsPerHost=
##maxWaitTime=
##connectTimeout=
##socketTimeout=
##socketKeepAlive=
##sslEnabled=
##threadsAllowedToBlockForConnectionMultiplier=
#EOF

export MONGO_MANUAL=true
export MONGO_HOST=$mongos_ip
export MONGO_PORT=27017
export MONGO_USER=
export MONGO_PASSWORD=

sudo ps aux | grep -v grep | grep acmeair > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    cd $WLP_SERVERDIR
    bin/server start acmeair
    cd ~
    sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} $WLP_SERVERDIR
fi

sleep 5

liberty_server_status=$(curl -s -o /dev/null -w "%{http_code}" http://${liberty_ip}:${ACMEAIR_HTTP_PORT}/index.html)

if [[ $liberty_server_status -eq 200 ]]
then
    syslog_netcat "Liberty server, with AcmeAir Application, is already running"
    exit 0
else    
    syslog_netcat "Liberty server is with AcmeAir Application, failed to start"
    exit 1
fi