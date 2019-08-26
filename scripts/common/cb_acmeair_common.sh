#!/usr/bin/env bash

#/*******************************************************************************
#
# This source code is provided as is, without any express or implied warranty.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

#####################################################################################
# Common routines for YCSB 
#####################################################################################

source ~/.bashrc

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

declare -A token

LINUX_DISTRO=$(linux_distribution)
BACKEND_TYPE=$(get_my_ai_attribute type | sed 's/_acmeair//g')

set_java_home

MY_IP=$my_ip_addr

ACMEAIR_PATH=$(get_my_ai_attribute_with_default acmeair_path ~/acmeair-monolithic-java)
eval ACMEAIR_PATH=${ACMEAIR_PATH}

ACMEAIR_DRIVER_PATH=$(get_my_ai_attribute_with_default acmeair_driver_path ~/acmeair-driver)
eval ACMEAIR_DRIVER_PATH=${ACMEAIR_DRIVER_PATH}

ACMEAIR_PROPERTIES=$(get_my_ai_attribute_with_default acmeair_properties ~/acmeair.properties)
eval ACMEAIR_PROPERTIES=${ACMEAIR_PROPERTIES}
export ACMEAIR_PROPERTIES=$ACMEAIR_PROPERTIES

ACMEAIR_HTTP_PORT=$(get_my_ai_attribute_with_default acmeair_http_port 9085)
eval ACMEAIR_HTTP_PORT=${ACMEAIR_HTTP_PORT}

ACMEAIR_HTTPS_PORT=$(get_my_ai_attribute_with_default acmeair_https_port 9485)
eval ACMEAIR_HTTPS_PORT=${ACMEAIR_HTTPS_PORT}

WLP_SERVERDIR=$(get_my_ai_attribute_with_default wlp_serverdir /opt/ibm/wlp)
eval WLP_SERVERDIR=${WLP_SERVERDIR}
export WLP_SERVERDIR=$WLP_SERVERDIR

liberty_ip=`get_ips_from_role liberty`
if [ -z $liberty_ip ]
then
    syslog_netcat "liberty IP is null"
    exit 1
fi

if [[ $BACKEND_TYPE == "websphere" ]]
then 
    /bin/true    
elif [[ $BACKEND_TYPE == "mongo" ]]
then 

    MONGODB_DATA_DIR=$(get_my_ai_attribute_with_default mongodb_data_dir /dbstore)
    eval MONGODB_DATA_DIR=${MONGODB_DATA_DIR}

    MONGODB_DATA_FSTYP=$(get_my_ai_attribute_with_default mongodb_data_fstyp ext4)
    eval MONGODB_DATA_FSTYP=${MONGODB_DATA_FSTYP}

    MONGODB_USER=$(sudo cat /etc/passwd | grep mongo | cut -d ':' -f 1)

    MONGODB_EXECUTABLE=$(which mongodb)
    if [[ $? -ne 0 ]]
    then
        MONGODB_EXECUTABLE=$(which mongod)
    fi
    
    sudo ls /etc/mongodb.conf > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        MONGODB_CONF_FILE=/etc/mongodb.conf
    else
        MONGODB_CONF_FILE=/etc/mongod.conf
    fi
                        
    mongos_ip=`get_ips_from_role mongos`
    if [ -z $mongos_ip ]
    then
        syslog_netcat "mongos IP is null"
        exit 1
    fi
    
    mongocfg_ip=`get_ips_from_role mongo_cfg_server`
    if [ -z $mongocfg_ip ]
    then
        syslog_netcat "mongocfg IP is null"
        exit 1
    fi
    
    mongo_ips=`get_ips_from_role mongodb`
    
    total_nodes=`echo "${mongo_ips}" | wc -w`

    mongo_ips_csv=`echo "${mongo_ips}" | sed ':a;N;$!ba;s/\n/, /g'`

    if [[ $(cat /etc/hosts | grep -c mongo-cfg-server) -eq 0 ]]
    then    
        sudo sh -c "echo $mongocfg_ip mongo-cfg-server >> /etc/hosts"
    fi

    if [[ $(cat /etc/hosts | grep -c mongos) -eq 0 ]]
    then    
        sudo sh -c "echo $mongos_ip mongos >> /etc/hosts"
    fi                
else 
    syslog_netcat "Unsupported backend type ($BACKEND_TYPE). Exiting with error"
    exit 1
fi

function check_mongodb_cluster_state {

    syslog_netcat "Waiting for all nodes to become available..."

    MONGOSHN=$1
    MONGORS=$2
    ATTEMPTS=$3
    INTERVAL=$4

    counter=0

    which cbcluster >/dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "#!/usr/bin/env bash" > /tmp/cbcluster
        echo "mongo --host ${mongos_ip}:27017 --eval \"db.printShardingStatus()\"" >> /tmp/cbcluster
        sudo chmod 0755 /tmp/cbcluster
        sudo mv /tmp/cbcluster /usr/local/bin/cbcluster
    fi

    if [[ $ATTEMPTS -eq 0 ]]
    then
        return 0
    fi
    
    NODES_REGISTERED=0
    while [[ $NODES_REGISTERED -ne $total_nodes ]]
    do
        syslog_netcat "Obtaining the node list for this MongoDB cluster by running \"mongo --host ${MONGOSHN}:27017 --eval \"db.printShardingStatus()\" | grep \"${MONGORS} | wc -l\"..."            
        NODES_REGISTERED=$(mongo --host ${MONGOSHN}:27017 --eval "db.printShardingStatus()" | grep \"${MONGORS} | grep host | wc -l)                        

        syslog_netcat "Nodes registered on the cluster: $NODES_REGISTERED out of $total_nodes"        
        counter="$(( $counter + 1 ))"

        sleep $INTERVAL
    done

    if [[ $counter -gt $ATTEMPTS ]]
    then
        return 1
    else
        return 0
    fi
}
export -f check_mongodb_cluster_state
