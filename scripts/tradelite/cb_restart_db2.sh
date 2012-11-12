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

INSTANCE_PATH=~
SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)
NETSTAT_CMD=`which netstat`
SUDO_CMD=`which sudo`
ATTEMPTS=3
START=`provision_application_start`

SIZE=`get_my_ai_attribute_with_default tradedb_size small`

syslog_netcat "Moving /tradedb_${SIZE} to /tradedb"
sudo mv /tradedb_${SIZE} /tradedb

syslog_netcat "Setting DB2 for the new hostname ($SHORT_HOSTNAME)"
sudo chmod 666 $INSTANCE_PATH/sqllib/db2nodes.cfg
chmod u+wx $INSTANCE_PATH/sqllib/db2nodes.cfg
echo "0 $SHORT_HOSTNAME 0" > $INSTANCE_PATH/sqllib/db2nodes.cfg
sudo rm -rf $INSTANCE_PATH/sqllib/spmlog/*
db2 update dbm cfg using spm_name NULL
syslog_netcat "Done setting DB2 for the new hostname ($SHORT_HOSTNAME)"

while [ "$ATTEMPTS" -ge  0 ]
do
	syslog_netcat "Checking for DB2 instances in $SHORT_HOSTNAME...."
	result1="$($SUDO_CMD $NETSTAT_CMD -atnp | grep 50007)"
	result2="$(ps aux | grep db2acd | grep -v grep)"
	if [ x"$result1" == x -o y"$result2" == y ] ; then 
		sleep 2
		syslog_netcat "DB2 not running on $SHORT_HOSTNAME... will try to start it $ATTEMPTS more times"
		syslog_netcat "DB2 being restarted on $SHORT_HOSTNAME"
		let ATTEMPTS=ATTEMPTS-1

        cat >/tmp/tmpdb2setup$$.sql <<EOF12345
CREATE TABLE HOLDINGEJB (PURCHASEPRICE DECIMAL(14, 2), HOLDINGID INTEGER NOT NULL, QUANTITY DOUBLE NOT NULL, PURCHASEDATE TIMESTAMP, ACCOUNT_ACCOUNTID INTEGER, QUOTE_SYMBOL VARCHAR(250))

ALTER TABLE HOLDINGEJB ADD CONSTRAINT PK_HOLDINGEJB PRIMARY KEY (HOLDINGID)

CREATE TABLE ACCOUNTPROFILEEJB (ADDRESS VARCHAR(250), PASSWD VARCHAR(250), USERID VARCHAR(250) NOT NULL, EMAIL VARCHAR(250), CREDITCARD VARCHAR(250), FULLNAME VARCHAR(250))

ALTER TABLE ACCOUNTPROFILEEJB ADD CONSTRAINT PK_ACCOUNTPROFILE2 PRIMARY KEY (USERID)

CREATE TABLE QUOTEEJB (LOW DECIMAL(14, 2), OPEN1 DECIMAL(14, 2), VOLUME DOUBLE NOT NULL, PRICE DECIMAL(14, 2), HIGH DECIMAL(14, 2), COMPANYNAME VARCHAR(250), SYMBOL VARCHAR(250) NOT NULL, CHANGE1 DOUBLE NOT NULL)

ALTER TABLE QUOTEEJB ADD CONSTRAINT PK_QUOTEEJB PRIMARY KEY (SYMBOL)

CREATE TABLE KEYGENEJB (KEYVAL INTEGER NOT NULL, KEYNAME VARCHAR(250) NOT NULL)

ALTER TABLE KEYGENEJB ADD CONSTRAINT PK_KEYGENEJB PRIMARY KEY (KEYNAME)

CREATE TABLE ACCOUNTEJB (CREATIONDATE TIMESTAMP, OPENBALANCE DECIMAL(14, 2), LOGOUTCOUNT INTEGER NOT NULL, BALANCE DECIMAL(14, 2), ACCOUNTID INTEGER NOT NULL, LASTLOGIN TIMESTAMP, LOGINCOUNT INTEGER NOT NULL, PROFILE_USERID VARCHAR(250))

ALTER TABLE ACCOUNTEJB ADD CONSTRAINT PK_ACCOUNTEJB PRIMARY KEY (ACCOUNTID)

CREATE TABLE ORDEREJB (ORDERFEE DECIMAL(14, 2), COMPLETIONDATE TIMESTAMP, ORDERTYPE VARCHAR(250), ORDERSTATUS VARCHAR(250), PRICE DECIMAL(14, 2), QUANTITY DOUBLE NOT NULL, OPENDATE TIMESTAMP, ORDERID INTEGER NOT NULL, ACCOUNT_ACCOUNTID INTEGER, QUOTE_SYMBOL VARCHAR(250), HOLDING_HOLDINGID INTEGER)

ALTER TABLE ORDEREJB ADD CONSTRAINT PK_ORDEREJB PRIMARY KEY (ORDERID)

ALTER TABLE HOLDINGEJB VOLATILE
ALTER TABLE ACCOUNTPROFILEEJB VOLATILE
ALTER TABLE QUOTEEJB VOLATILE
ALTER TABLE KEYGENEJB VOLATILE
ALTER TABLE ACCOUNTEJB VOLATILE
ALTER TABLE ORDEREJB VOLATILE

CREATE INDEX ACCOUNT_USERID ON ACCOUNTEJB(PROFILE_USERID)
CREATE INDEX HOLDING_ACCOUNTID ON HOLDINGEJB(ACCOUNT_ACCOUNTID)
CREATE INDEX ORDER_ACCOUNTID ON ORDEREJB(ACCOUNT_ACCOUNTID)
CREATE INDEX ORDER_HOLDINGID ON ORDEREJB(HOLDING_HOLDINGID)
CREATE INDEX CLOSED_ORDERS ON ORDEREJB(ACCOUNT_ACCOUNTID,ORDERSTATUS)
EOF12345

		syslog_netcat "Running db2stop..."
		$INSTANCE_PATH/sqllib/adm/db2stop force | while read line ; do syslog_netcat "$line" ; done
		syslog_netcat "Done running db2stop...."
		sleep 2
		syslog_netcat "Running db2_kill..."
		/opt/ibm/db2/V9.7/bin/db2_kill
		syslog_netcat "Done running db2_kill"
		sleep 2
		syslog_netcat "Running db2ftok..."
		/opt/ibm/db2/V9.7/bin/db2ftok
		syslog_netcat "Done running db2ftok"
		sleep 2
		syslog_netcat "Running db2start once..."
		$INSTANCE_PATH/sqllib/adm/db2start | while read line ; do syslog_netcat "$line" ; done
		syslog_netcat "Done. Let's wait 5 seconds and check for running DB2 instances again..."
		sleep 5
		syslog_netcat "Reinitializing DB2 tradedb for tradelite..."
		syslog_netcat "Dropping old tradedb..."
		db2 drop db tradedb
		syslog_netcat "Creating new tradedb..."
		db2 create db tradedb
		syslog_netcat "Connecting to new tradedb..."
        db2 connect to tradedb
        syslog_netcat "Running sql setup..."
        db2 < /tmp/tmpdb2setup$$.sql
		syslog_netcat "Disconnecting from new tradedb..."
		db2 disconnect tradedb
        rm  /tmp/tmpdb2setup$$.sql
        syslog_netcat "Reinit complete."
	else
		syslog_netcat "DB2 restarted succesfully on $SHORT_HOSTNAME - OK"
		provision_application_stop $START
		exit 0
	fi
done
syslog_netcat "DB2 could not be restarted on $SHORT_HOSTNAME - NOK"
exit 2
