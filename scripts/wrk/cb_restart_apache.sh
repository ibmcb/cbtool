#!/usr/bin/env bash

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

START=`provision_application_start`

PROTOCOL=$(get_my_ai_attribute_with_default protocol http)
URL=$(get_my_ai_attribute_with_default url index.html)

linux_distribution
SERVICES[1]="apache2"
SERVICES[2]="httpd"

wget -N -P /tmp ${PROTOCOL}://${my_ip_addr}/${URL}

if [[ $? -ne 0 ]]
then
    service_stop_disable ${SERVICES[${LINUX_DISTRO}]}
    syslog_netcat "Starting Apache on ${SHORT_HOSTNAME}" 
    service_restart_enable ${SERVICES[${LINUX_DISTRO}]}

    wait_until_port_open 127.0.0.1 80 20 5

    STATUS=$?
    
    if [[ ${STATUS} -eq 0 ]]
    then
        syslog_netcat "Apache server running"
    else
        syslog_netcat "Apache server failed to start"
    fi

    wget -N -P /tmp ${PROTOCOL}://${my_ip_addr}/${URL}
    STATUS=$?
fi

provision_application_stop $START
exit ${STATUS}