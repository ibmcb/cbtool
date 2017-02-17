#!/usr/bin/env bash

source ~/.bashrc

KUB_NAMESPACE_NAME=cb-namespace
KUB_QUOTA_NAME=cb-quota
KUB_NETWORK_NAME=cb-tenantnet
TNSRC_ERROR=0
  
obj_name=$(cat ${1} | grep '"'name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
counter=$(echo ${obj_name} | cut -d '_' -f 2)
step=$(cat ${1} | grep '"'staging'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g') 
model=$(cat ${1} | grep model | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
cloud_name=$(cat ${1} | grep '"'cloud_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
create_lb=$(cat ${1} | grep \"create_lb\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
ai_counter=$(cat ${1} | grep '"'ai_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | cut -d '_' -f 2)
kusername=$(cat ${1} | grep \"username\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
rc_path=$(cat ${1} | grep \"generated_configurations_dir\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
host_cloud_ip=$(cat ${1} | grep \"host_cloud_ip\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
tbs=$(cat ${1} | grep \"time_breakdown_step\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

KUBECFG=~/.kube/config
eval KUBECFG=${KUBECFG}
TRACE_FILE=/var/log/cloudbench/${kusername}_staging.log

#export NC_HOST_SYSLOG=${NC_HOST_SYSLOG:-localhost}
#export NC_PORT_SYSLOG=${NC_PORT_SYSLOG:-514}
#export NC_OPTIONS="-w1 -u"
#export NC_FACILITY_SYSLOG=${NC_FACILITY_SYSLOG:-128}
#export NC_CMD=${NC}" "${NC_OPTIONS}" "${NC_HOST_SYSLOG}" "${NC_PORT_SYSLOG}
                                        
if [[ -z $create_lb ]]
then
    create_lb=false
fi

if [[ -z $tbs ]]
then
    tbs=1
fi

source ${rc_path}/${kusername}_cb_lastcloudrc
    
function write_to_log {
    echo "$(date) - $obj_name - $1" >> $TRACE_FILE
    /bin/true
}

function tac {
    echo "${model}_$(printf %03d ${tbs})_"
    tbs=$((tbs+1))
    return $tbs
}    

function execute_command {
    #1 - Command
    #2 - Interval between attempts
    #3 - Attempts

    COMMAND=${1}
    
    if [[ -z $2 ]]
    then
        INTERATTEMPTINT=1
    else
        INTERATTEMPTINT=${2}
    fi
    
    if [[ -z $3 ]]
    then
        ATTEMPTS=1
    else
        ATTEMPTS=${3}
    fi
    
    if [[ -z $4 ]]
    then
        EC_FATAL=1
    else
        EC_FATAL=$4
    fi
    
    ATTEMPTCOUNTER=1
    while [[ "$ATTEMPTCOUNTER" -le "${ATTEMPTS}" ]]
    do
        write_to_log "Running command \"${COMMAND}\", attempt ${counter} of ${ATTEMPTS}..."
        if [[ $(echo ${COMMAND} | grep -c ';') -ne 0 || $(echo ${COMMAND} | grep -c '&&') -ne 0 ]]
        then
            EC_RESULT=$(echo ${COMMAND} | sed 's/\([^\\]\);/\1\\;/g')
        else
            EC_RESULT=$(${COMMAND} 2>&1)
        fi
        
        export EC_EXITCODE=$?
        export EC_RESULT        
        if [[ $EC_EXITCODE -ne 0 ]]
        then
            if [[ $ATTEMPTS -gt 1 ]]
            then
                X_MSG="Will try again, since the"
            else
                X_MSG="The"
            fi
            
            if [[ $EC_FATAL -eq 1 ]]
            then
                write_to_log "$X_MSG command \"${COMMAND}\" exit code was $EC_EXITCODE (FATAL FAILURE), and the output was ------- ${EC_RESULT}"
            else
                write_to_log "$X_MSG command \"${COMMAND}\" exit code was $EC_EXITCODE (TRIVIAL FAILURE)"
            fi

            sleep ${INTERATTEMPTINT}
            ATTEMPTCOUNTER="$(( $ATTEMPTCOUNTER + 1 ))"
        else
            write_to_log "After ${ATTEMPTCOUNTER} attempts (out of ${ATTEMPTS}) - the command \"${COMMAND}\" exit code is zero, and the output is ------- ${EC_RESULT}"
            break
        fi
    done

    if [[ $EC_EXITCODE -ne 0 && $EC_FATAL -eq 1 ]]
    then
        (>&2 echo "command \"${COMMAND}\" failed!")
        export TNSRC_ERROR=1
    fi
}

function create_namespace () {
    _n=$1
    namespaces=1        
    
    for ((i=1; i <= $namespaces ; i++))
    do 
        execute_command "kubectl --kubeconfig=${KUBECFG} describe namespace ${KUB_NAMESPACE_NAME}-${_n}-${i}" 1 1 0
        if [[ $EC_EXITCODE -ne 0 ]]
        then
            execute_command "kubectl --kubeconfig=${KUBECFG} create namespace ${KUB_NAMESPACE_NAME}-${_n}-${i}"
        fi
    done
}

function delete_namespace () {
    _n=$1
    namespaces=1
    
    for ((i=1; i <= $namespaces ; i++))
    do    
        execute_command "kubectl --kubeconfig=${KUBECFG} delete namespace ${KUB_NAMESPACE_NAME}-${_n}-${i}"
    done
}
 
function create_quota () {
    _n=$1
    numquotas=1
    
    for ((i=1; i <= $numquotas ; i++))
    do 
        execute_command "kubectl --kubeconfig=${KUBECFG} describe quota ${KUB_QUOTA_NAME}-${_n}-${i}" 1 1 0
        if [[ $EC_EXITCODE -ne 0 ]]
        then
            execute_command "kubectl --kubeconfig=${KUBECFG} create quota ${KUB_QUOTA_NAME}-${_n}-${i} --hard=cpu=100,memory=100G,pods=200,services=300,replicationcontrollers=200,resourcequotas=100,secrets=500,persistentvolumeclaims=100"
        fi
    done
}

function delete_quota () {
    _n=$1
    numquotas=1
    
    for ((i=1; i <= $numquotas ; i++))
    do    
        execute_command "kubectl --kubeconfig=${KUBECFG} delete quota ${KUB_QUOTA_NAME}-${_n}-${i}"
    done
}    
       
if [[ $step == "execute_deprovision_finished" ]]
then
    TNSR_OUTPUT="staging:execute_deprovision_finished"

    date0=`date +%s`
    delete_quota $counter
    date1=`date +%s`
    qdiff=$((date1-date0))
    delete_namespace $counter
    date2=`date +%s`
    nsdiff=$((date2-date1))        
    TNSR_OUTPUT=$TNSR_OUTPUT",kub_901_quota_deletion_time:${qdiff},kub_902_namespace_deletion_time:${nsdiff}"

fi

if [[ $step == "execute_provision_finished" ]]
then

    vm_uuid=$(cat ${1} | grep cloud_vm_uuid | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    run_cloud_ip=$(cat ${1} | grep run_cloud_ip | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
             
    date0=`date +%s`
    
            if [[ $ai_counter != "none" ]]
    then
        TNSR_OUTPUT="staging:none" 
        actual_counter=$ai_counter
    else
        TNSR_OUTPUT="staging:execute_deprovision_finished"                
        actual_counter=$counter
    fi
fi

if [[ $step == "execute_provision_originated" ]]
then
    
    credir=$(cat ${1} | grep credentials_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    basedir=$(cat ${1} | grep \"base_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

    snipa=$(sed -n ${counter}p $basedir/scenarios/scripts/pre_computed_nets.txt)

    if [[ $ai_counter == "none" ]]
    then
        TNSR_OUTPUT="staging:execute_provision_finished"
    else
        TNSR_OUTPUT="staging:execute_deprovision_finished,vm_staging:execute_provision_finished"
    fi

    date0=`date +%s`
    create_namespace $counter
    date1=`date +%s`
    nsdiff=$((date1-date0))
    tbstr=$(tac)
    tbs=$?
	TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}namespace_creation_time:${nsdiff}"
    create_quota $counter
    date2=`date +%s`
    qdiff=$((date2-date1))
    tbstr=$(tac)
    tbs=$?         
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}quota_creation_time:${qdiff}"
    TNSR_OUTPUT=$TNSR_OUTPUT",namespace:${KUB_NAMESPACE_NAME}-${counter}-1"
    TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${KUB_NAMESPACE_NAME}-${counter}-1"
    TNSR_OUTPUT=$TNSR_OUTPUT",time_breakdown_step:${tbs}"
fi

if [[ $TNSRC_ERROR -eq 0 ]]
then
    write_to_log "script for step $step executed successful"
    echo "$TNSR_OUTPUT"
    exit 0
else
    write_to_log "script for step $step failed"
    (>&2 echo "script for step $step failed")
    exit 1
fi