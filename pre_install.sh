#!/usr/bin/env bash

SUDOCMD=$(which sudo)

$SUDOCMD cat /etc/hosts | grep $(hostname) > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    $SUDOCMD bash -c "echo \"127.0.0.1 $(hostname)\" >> /etc/hosts"
fi

python3 -V >/dev/null 2>&1
if [[ $? -ne 0 ]]
then
    $SUDOCMD cat /etc/*release* | grep Ubuntu >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        $SUDOCMD apt-get update; $SUDOCMD DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip epel-release
    fi
    $SUDOCMD cat /etc/*release* | grep CentOS >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        $SUDOCMD yum install -y python3 dnf-plugins-core
    fi

fi

python3 -V >/dev/null 2>&1
if [[ $? -ne 0 ]]
then
    exit 1
else
    $SUDOCMD cat /etc/*release* | grep CentOS >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        $SUDOCMD yum config-manager --set-enabled PowerTools
	cat << EOF > /tmp/mongodb-org.repo
[mongodb-org-3.6]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/8/mongodb-org/3.6/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc
EOF
        $SUDOCMD mv /tmp/mongodb-org.repo /etc/yum.repos.d/mongodb-org.repo
    fi
    exit 0
fi
