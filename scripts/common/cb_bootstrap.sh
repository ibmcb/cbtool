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

# Better way of getting absolute path instead of relative path
if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi
    
NC=`which netcat` 
if [[ $? -ne 0 ]]
then
    NC=`which nc`
fi

function syslog_netcat {
    echo "$1"
}
        
function linux_distribution {
    IS_UBUNTU=$(cat /etc/*release | grep -c "Ubuntu")

    if [[ ${IS_UBUNTU} -ge 1 ]]
    then
        export LINUX_DISTRO=1
    fi
    
    IS_REDHAT=$(cat /etc/*release | grep -c "Red Hat\|CentOS\|Fedora")    
    if [[ ${IS_REDHAT} -ge 1 ]]
    then
        export LINUX_DISTRO=2
    fi
    
}

function blowawaypids {
    pids="$(pgrep -f "$1")"
    for pid in $pids ; do
        if [ $pid != $$ ] && [ $pid != $PPID ] ; then
            sudo kill -9 $pid
        fi
    done
}

# ################################################################
# Install a list of packages. Support multiple formats and multiple
# packages managers/formats.
# ################################################################
function package_install {
   # 1+ - package names (space-separated list)


    PACKAGE_LIST=$*


    if [[ $PACKAGE_LIST == "" ]]
    then
        return 0
    fi

    if [[ ${LINUX_DISTRO} -eq 1 ]]
    then
        if [[ $(echo "$PACKAGE_LIST" | grep -c ".deb") -eq 0 ]]
        then
            syslog_netcat "Installing packages \"$PACKAGE_LIST\" using \"apt-get\""
            sudo apt-get -q -y --force-yes --allow-unauthenticated -o Dpkg::Options::="--force-confnew" install $PACKAGE_LIST
        else
            syslog_netcat "Installing packages \"$PACKAGE_LIST\" using \"dpkg\""
            sudo dpkg -i $PACKAGE_LIST; sudo apt-get -f install -y --force-yes  --allow-unauthenticated
        fi
    elif [[ ${LINUX_DISTRO} -eq 2 ]]
    then
        if [[ $(echo "$PACKAGE_LIST" | grep -c ".rpm") -eq 0 ]]
        then
            syslog_netcat "Installing packages \"$PACKAGE_LIST\" using \"yum\""        
            sudo yum -y install $PACKAGE_LIST
        else
            syslog_netcat "Installing packages \"$PACKAGE_LIST\" using \"rpm\""
            # Unfortunately, the error codes produced by rpm are not informative.
            # For instance, if all packages are already installed, we will see
            # a non-zero exit code
            #sudo rpm -i $* 2>&1 >${INSTALL_LOG} || error_quit "Package install failed"    
            sudo rpm -i $PACKAGE_LIST 
        fi
    fi
}
export -f package_install

function service_stop_disable {
    #1 - service list (space-separated list)

    if [[ -z ${LINUX_DISTRO} ]]
    then
        linux_distribution
    fi
    
    for s in $*
    do

        if [[ ${LINUX_DISTRO} -eq 2 ]]
        then
            if [[ $(sudo systemctl | grep -c $s) -ne 0 ]]
            then
                STOP_COMMAND="sudo systemctl stop $s"
                DISABLE_COMMAND="sudo systemctl disable $s"
            else
                STOP_COMMAND="sudo service $s stop"
                DISABLE_COMMAND="sudo chkconfig $s off >/dev/null 2>&1"
            fi
        else
            STOP_COMMAND="sudo service $s stop"
            if [[ -f /etc/init/$s.conf ]]
            then
                DISABLE_COMMAND="sudo sh -c 'echo manual > /etc/init/$s.override'"
            else
                DISABLE_COMMAND="sudo update-rc.d -f $s remove"
            fi
        fi

        syslog_netcat "Stopping service \"${s}\" with command \"$STOP_COMMAND\"..."       
        bash -c "$STOP_COMMAND"

        syslog_netcat "Disabling service \"${s}\" with command \"$DISABLE_COMMAND\"..."               
        bash -c "$DISABLE_COMMAND"
        done
        /bin/true
}
export -f service_stop_disable
    
function service_restart_enable {
    #1 - service list (space-separated list)
        if [[ -z ${LINUX_DISTRO} ]]
        then
            linux_distribution
        fi

        for s in $*
        do            
            if [[ ${LINUX_DISTRO} -eq 2 ]]
            then
                if [[ $(sudo systemctl | grep -c $s) -ne 0 ]]
                then
                    START_COMMAND="sudo systemctl restart $s"
                    ENABLE_COMMAND="sudo systemctl enable $s"
                else
                    START_COMMAND="sudo service $s restart"
                    ENABLE_COMMAND="sudo chkconfig $s on >/dev/null 2>&1"
                fi
        else
            START_COMMAND="sudo service $s restart"
            if [[ -f /etc/init/$s.conf ]]
            then
                ENABLE_COMMAND="sudo rm -rf /etc/init/$s.override"            
            else
                ENABLE_COMMAND="sudo update-rc.d -f $s defaults"
            fi
        fi
        
        counter=1
        ATTEMPTS=7
        while [ "$counter" -le "$ATTEMPTS" ]
        do
            syslog_netcat "Restarting service \"${s}\", with command \"$START_COMMAND\", attempt ${counter} of ${ATTEMPTS}..."            
            bash -c "$START_COMMAND"
            if [[ $? -eq 0 ]]
            then
                syslog_netcat "Service \"$s\" was successfully restarted"
                syslog_netcat "Enabling service \"${s}\", with command \"$ENABLE_COMMAND\"..."   
                bash -c "$ENABLE_COMMAND"
                break
            else
                sleep 5
                counter="$(( $counter + 1 ))"
            fi
        done
        
        if [[ "${counter}" -ge "$ATTEMPTS" ]]
        then
            syslog_netcat "Service \"${s}\" failed to restart after ${ATTEMPTS} attempts"
            error_quit
        fi
    done
    
    /bin/true
}  
export -f service_restart_enable