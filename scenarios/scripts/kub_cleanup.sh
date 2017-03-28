#!/usr/bin/env bash

source ~/.bashrc

KUB_NAMESPACE_NAME=cb-namespace
KUB_QUOTA_NAME=cb-quota
KUB_NETWORK_NAME=cb-tenantnet
TNSRC_ERROR=0

function all_clear () {

    CB_CLOUD_NAME=$(echo "$CB_CLOUD_NAME" | tr '[:upper:]' '[:lower:]')
#    for NS in $(kubectl get namespaces | grep ${KUB_NAMESPACE_NAME} | awk '{ print $1 }')
    for NS in $(kubectl get namespaces | awk '{ print $1 }')
    do
        for D in $(kubectl --namespace $NS get deployments | grep ${CB_CLOUD_NAME} | grep ${CB_USERNAME} | awk '{ print $1 }')
        do  
            echo "deleting deployment $D (namespace $NS)"
            kubectl --namespace $NS delete deployments ${D}
        done

        for RS in $(kubectl --namespace $NS get replicasets | grep ${CB_CLOUD_NAME} | grep ${CB_USERNAME} | awk '{ print $1 }')
        do  
            echo "deleting replicaset $RS (namespace $NS)"
            kubectl --namespace $NS delete replicaset ${D}
        done        

        for P in $(kubectl --namespace $NS get pods | grep ${CB_CLOUD_NAME} | grep ${CB_USERNAME} | awk '{ print $1 }')
        do  
            echo "deleting pods $P (namespace $NS)"
            kubectl --namespace $NS delete pods ${P}
        done        

        echo $NS | grep ${KUB_NAMESPACE_NAME} 
        
        if [[ $? -eq 0 ]]
        then
            echo "deleting namespace $NS"       
            kubectl delete namespace $NS
        fi
    done

    for Q in $(kubectl get quota | grep ${KUB_QUOTA_NAME} | awk '{ print $1 }')
    do  
        echo "deleting quota $Q"
        kubectl delete quota ${Q}
    done                
}
    
MY_PATH="`dirname \"$0\"`"
MY_PATH="`( cd \"$MY_PATH\" && pwd )`"
RC_PATH=${MY_PATH}/../../configs/generated/
RC_PATH="`( cd \"$RC_PATH\" && pwd )`"
source $RC_PATH/$(whoami)_cb_lastcloudrc
all_clear