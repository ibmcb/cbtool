#!/usr/bin/env bash

source ~/.bashrc

SIM_TENANT_NAME=cb-tenant
SIM_USER_NAME=cb-user
SIM_NETWORK_NAME=cb-tenantnet
SIM_SUBNETWORK_NAME=cb-subtenantnet
SIM_ROUTER_NAME=cb-router
SIM_LBPOOL_NAME=cb-lbpool
SIM_LBVIP_NAME=cb-lbvip
SIM_LBMEMBER_NAME=cb-lbmember
SIM_LB_PROTOCOL=TCP
SIM_LB_PROTOCOL_PORT=22
TNSRC_ERROR=0
  
obj_name=$(cat ${1} | grep '"'name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
counter=$(echo ${obj_name} | cut -d '_' -f 2)
step=$(cat ${1} | grep '"'staging'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')    
model=$(cat ${1} | grep model | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
cloud_name=$(cat ${1} | grep '"'cloud_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
create_lb=$(cat ${1} | grep \"create_lb\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
ai_counter=$(cat ${1} | grep '"'ai_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | cut -d '_' -f 2)
kusername=$(cat ${1} | grep \"username\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
tbs=$(cat ${1} | grep \"time_breakdown_step\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

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

if [[ -f ~/cbrc-${cloud_name} ]]
then
    source ~/cbrc-${cloud_name}
fi
    
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
    sleep $[ ( $RANDOM % 2 )  + 1 ]s
}

function create_tenant () {
    _n=$1
    #    TINFO=$(openstack project show ${SIM_TENANT_NAME}-${_n} 2>&1)
    execute_command "echo create project ${SIM_TENANT_NAME}-${_n}" 1 1 0
    export TENANT_JUST_CREATED=1    
    TID=$(uuidgen)
    export TID
}

function update_quotas () {
    _t=$1
    execute_command "echo quota-update ${_t} --metadata-items 100000"
    execute_command "echo quota-update ${_t} --instances 100000"
    #    execute_command "nova quota-update ${_t} --volumes 10000"
    #    execute_command "nova quota-update ${_t} --gigabytes 1000000"
    execute_command "echo quota-update ${_t} --floating-ips 10000"
    execute_command "echo quota-update ${_t} --ram 1000000000"
    execute_command "echo quota-update ${_t} --cores 100000"
    #    execute_command "cinder quota-update --volumes 10000 ${TID}"
}

function create_user () {
    _n=$1
    _t=$2
    execute_command "echo user create --password temp4now --project ${_t} --email user-${_n}@nowhere.org --enable ${SIM_USER_NAME}-${_n}"
    export USER_JUST_CREATED=1
}

function update_security_groups () {
    _t=$1
    execute_command "echo security-group-list --tenant-id ${_t}"
    secgroup=$(uuidgen)
    execute_command "echo security-group-rule-create $secgroup --direction ingress --protocol icmp"        
    execute_command "echo security-group-rule-create $secgroup --direction ingress --protocol tcp --port-range-min 22 --port-range-max 22"
}

function add_keypair () {
    keypath=$1
    keyname=$2
    kusername=$3    
    _n=$4
    execute_command "echo --os-tenant-name cb-tenant-${_n} --os-username ${SIM_USER_NAME}-${_n} --os-password temp4now keypair-add --pub-key $keypath/${keyname}.pub ${kusername}_cb-tenant-${_n}_${keyname}"
}

function create_network () {
    _n=$1
    _t=$2
    
    if [[ -z $3 ]]
    then
        numnets=1
    else
        numnets=$3
    fi
    
    execute_command "echo net-create --tenant-id ${_t} ${SIM_NETWORK_NAME}-${_n}-${i}"
}

function create_subnet() {
    _n=$1
    _t=$2
    _snipa=$3
    
    if [[ -z $4 ]]
    then
        numnets=1
    else
        numnets=$4
    fi

    if [[ -z $5 ]]
    then
        numsubnets=1
    else
        numsubnets=$5
    fi    

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do
            execute_command "echo subnet-create --tenant-id ${_t} --name ${SIM_SUBNETWORK_NAME}-${_n}-${i}-${j} --enable-dhcp ${SIM_NETWORK_NAME}-${_n}-${i} ${_snipa}"
        done
    done
}

function create_router () {
    _n=$1
    _t=$2
    if [[ -z $3 ]]
    then
        numrouters=1
    else
        numrouters=$3
    fi
    
    for ((i=1; i <= $numrouters ; i++))
    do
        execute_command "echo router-create --tenant-id ${_t} ${SIM_ROUTER_NAME}-${_n}-${i}"
        export ROUTER_JUST_CREATED=1
    done
}

function router_set_gateway () {
    _n=$1
    _extnet=$2
    if [[ -z $3 ]]
    then
        numrouters=1
    else
        numrouters=$3
    fi
    
    for ((i=1; i <= $numrouters ; i++))
    do
        execute_command "echo router-gateway-set ${SIM_ROUTER_NAME}-${_n}-${i} ${_extnet}"
    done
}

function attach_to_router () {
    _n=$1

    if [[ -z $2 ]]
    then
        numnets=1
    else
        numnets=$2
    fi

    if [[ -z $3 ]]
    then
        numsubnets=1
    else
        numsubnets=$3
    fi        
        
    if [[ -z $4 ]]
    then
        numrouters=1
    else
        numrouters=$4
    fi

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numrouters ; k++))
            do
                execute_command "echo router-interface-add  ${SIM_ROUTER_NAME}-${_n}-${k} ${SIM_SUBNETWORK_NAME}-${_n}-${i}-${j}"
            done
        done
    done
}

function create_lb_pools () {
    _n=$1
    _t=$2
    
    if [[ -z $3 ]]
    then
        numnets=1
    else
        numnets=$3
    fi

    if [[ -z $4 ]]
    then
        numsubnets=1
    else
        numsubnets=$4
    fi        
        
    if [[ -z $5 ]]
    then
        numpools=1
    else
        numpools=$5
    fi

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numpools ; k++))
            do
                execute_command "echo lb-pool-create --name ${SIM_LBPOOL_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol ${SIM_LB_PROTOCOL} --subnet-id ${SIM_SUBNETWORK_NAME}-${_n}-${i}-${j} --lb-method ROUND_ROBIN"
            done
        done
    done
}

function create_lb_vips () {
    _n=$1
    _t=$2
    
    if [[ -z $3 ]]
    then
        numnets=1
    else
        numnets=$3
    fi

    if [[ -z $4 ]]
    then
        numsubnets=1
    else
        numsubnets=$4
    fi        
        
    if [[ -z $5 ]]
    then
        numpools=1
    else
        numpools=$5
    fi
    
    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numpools ; k++))
            do
                execute_command "echo neutron lb-vip-create --name ${SIM_LBVIP_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol-port ${SIM_LB_PROTOCOL_PORT} --protocol ${SIM_LB_PROTOCOL} --subnet-id ${SIM_SUBNETWORK_NAME}-${_n}-${i}-${j} ${SIM_LBPOOL_NAME}-${_n}-${i}-${j}-${k}"
                export LB_VIP_PORT=$(uuidgen)
            done
        done
    done
}
    
function create_lb_member () {
    _n=$1
    _t=$2
    _ipaddr=$3

    
    #for instaddr in $(openstack server list --project ${SIM_NETWORK_NAME}-${_n}-1 -c Networks | grep cb-tenantnet | cut -d '=' -f 2 | cut -d ',' -f 1)

    execute_command "echo lb-member-create --tenant-id ${_t} --protocol-port ${SIM_LB_PROTOCOL_PORT} --address ${_ipaddr} ${SIM_LBPOOL_NAME}-${_n}-1-1-1"
}

function check_lb_pool_active() {
    _n=$1
    _t=$2
    _attempts=$3
    _interval=$4

    _counter=0
    #for instaddr in $(openstack server list --project ${SIM_NETWORK_NAME}-${_n}-1 -c Networks | grep cb-tenantnet | cut -d '=' -f 2 | cut -d ',' -f 1)
    dateX=`date +%s`
    LB_ACTIVE=0
    while [[ "${_counter}" -le "${_attempts}" && $LB_POOL_READY -eq 0 ]]
    do
                    
        execute_command "echo ACTIVE" 1 1 0
        if [[ $(echo "$EC_RESULT" | grep -c ACTIVE) -ne 0 ]]
        then
            LB_POOL_READY=1
        elif [[ $(echo "$EC_RESULT" | grep -c ERROR) -ne 0 ]]
        then
            LB_POOL_READY=2        
        else
            LB_POOL_READY=0
            sleep ${_interval}
            _counter="$(( ${_counter} + 1 ))"            
        fi
    done
    dateY=`date +%s`
    lbcheckdiff=$((dateY-dateX))
    if [[ $LB_POOL_READY -eq 0 ]]
    then
        echo "lb pool checking failed (not ready)" >&2
        write_to_log "lb pool checking failed (not ready) after $lbcheckdiff seconds (FATAL FAILURE)"
        export TNSRC_ERROR=1
    elif [[ $LB_POOL_READY -eq 2 ]]
    then
        echo "lb pool checking failed (error)" >&2
        write_to_log "lb pool checking failed (error) after $lbcheckdiff seconds (FATAL FAILURE)"
        export TNSRC_ERROR=1
    else
        write_to_log "lb pool checking successful after $lbcheckdiff seconds"        
    fi
}

function check_lb_vip_active() {
    _n=$1
    _t=$2
    _attempts=$3
    _interval=$4

    _counter=0
    #for instaddr in $(openstack server list --project ${SIM_NETWORK_NAME}-${_n}-1 -c Networks | grep cb-tenantnet | cut -d '=' -f 2 | cut -d ',' -f 1)
    dateX=`date +%s`
    LB_ACTIVE=0
    while [[ "${_counter}" -le "${_attempts}" && $LB_VIP_READY -eq 0 ]]
    do                            
        execute_command "echo ACTIVE" 1 1 0
        if [[ $(echo "$EC_RESULT" | grep -c ACTIVE) -ne 0 ]]
        then
            LB_VIP_READY=1
        elif [[ $(echo "$EC_RESULT" | grep -c ERROR) -ne 0 ]]
        then 
            LB_VIP_READY=2        
        else
            LB_VIP_READY=0
            sleep ${_interval}
            _counter="$(( ${_counter} + 1 ))"            
        fi
    done
    dateY=`date +%s`
    lbcheckdiff=$((dateY-dateX))    
    if [[ $LB_VIP_READY -eq 0 ]]
    then
        echo "lb vip checking failed (not ready)" >&2
        write_to_log "lb vip checking failed (not ready) after $lbcheckdiff seconds (FATAL FAILURE)"        
        export TNSRC_ERROR=1
    elif [[ $LB_VIP_READY -eq 2 ]]
    then
        echo "lb vip checking failed (error)" >&2
        write_to_log "lb vip checking failed (error) after $lbcheckdiff seconds (FATAL FAILURE)"        
        export TNSRC_ERROR=1
    else
        write_to_log "lb vip checking successful after $lbcheckdiff seconds"                        
    fi    
}

function create_floating_ip () {
    _ext_net=$1
    _tenant_id=$2
    execute_command "echo floatingip-create ${ext_net} --tenant-id ${_tenant_id}"

    export LB_FLOATING_ID=$(echo "$EC_RESULT" | grep [[:space:]]id[[:space:]] | cut -d "|" -f 3 | tr -d '[[:space:]]')
    export LB_FLOATING_ADDR=$(echo "$EC_RESULT" | grep floating_ip_address | cut -d "|" -f 3 | tr -d '[[:space:]]')        
}
    
function associate_floating_ip () {
    _lb_fip_id=$1
    _lb_vip_port=$2
    
    execute_command "echo floatingip-associate ${_lb_fip_id} ${_lb_vip_port}"
}
 
function connect_to_floating_ip () {
    _ssh_priv_key=$1
    _login_user=$2
    _fip=$3
    
    #ssh -i ${_ssh_priv_key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -l ${_login_user} ${_fip} "/bin/true" > /dev/null 2>&1
    execute_command "/bin/nc -z -w 10 ${_fip} ${SIM_LB_PROTOCOL_PORT}"
}                                        
                                                                                                                   
function delete_floating_ip () {
    _lb_fip_id=$1
    
    execute_command "echo floatingip-delete ${_lb_fip_id}"
}

function delete_lb_member () {
    _n=$1
    _t=$2
    _ipaddr=$3

    LB_UUID=$(uuidgen)
    execute_commad "echo lb-member-delete $LB_UUID"  
}

function delete_lb_members () {
    _n=$1
    _t=$2


    for LB_MEMBER_UUID in $(uuidgen)
    do 
        execute_command "echo lb-member-delete $LB_MEMBER_UUID"
    done

}

function delete_lb_vips () {
    _n=$1
    _t=$2
    
    if [[ -z $3 ]]
    then
        numnets=1
    else
        numnets=$3
    fi

    if [[ -z $4 ]]
    then
        numsubnets=1
    else
        numsubnets=$4
    fi        
        
    if [[ -z $5 ]]
    then
        numpools=1
    else
        numpools=$5
    fi
    
    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numpools ; k++))
            do
                #execute_command "neutron lb-vip-show ${SIM_LBVIP_NAME}-${_n}-${i}-${j}-${k}"
                execute_command "echo lb-vip-delete ${SIM_LBVIP_NAME}-${_n}-${i}-${j}-${k}"
            done
        done
    done
}

function delete_lb_pools () {
    _n=$1
    _t=$2
    
    if [[ -z $3 ]]
    then
        numnets=1
    else
        numnets=$3
    fi

    if [[ -z $4 ]]
    then
        numsubnets=1
    else
        numsubnets=$4
    fi        
        
    if [[ -z $5 ]]
    then
        numpools=1
    else
        numpools=$5
    fi

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numpools ; k++))
            do
                #execute_command "neutron lb-pool-show ${SIM_LBPOOL_NAME}-${_n}-${i}-${j}-${k}"
                execute_command "echo lb-pool-delete ${SIM_LBPOOL_NAME}-${_n}-${i}-${j}-${k}"
            done
        done
    done
}

function delete_router () {
    _n=$1

    if [[ -z $2 ]]
    then
        numnets=1
    else
        numnets=$2
    fi

    if [[ -z $3 ]]
    then
        numsubnets=1
    else
        numsubnets=$3
    fi        
        
    if [[ -z $4 ]]
    then
        numrouters=1
    else
        numrouters=$4
    fi

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do                            
            for ((k=1; k <= $numrouters ; k++))
            do
                for sn in $(uuidgen)
                do
                    execute_command "echo router-interface-delete ${SIM_ROUTER_NAME}-${_n}-${k} $sn" 1 1 0
                done        
                execute_command "echo router-delete ${SIM_ROUTER_NAME}-${_n}-${k}"
            done
        done
    done
}

function delete_subnet() {
    _n=$1
    
    if [[ -z $2 ]]
    then
        numnets=1
    else
        numnets=$2
    fi

    if [[ -z $3 ]]
    then
        numsubnets=1
    else
        numsubnets=$3
    fi    

    for ((i=1; i <= $numnets ; i++))
    do
        for ((j=1; j <= $numsubnets ; j++))
        do  
            execute_command "echo subnet-delete ${SIM_SUBNETWORK_NAME}-${_n}-${i}-${j}"
        done
    done
}

function delete_network () {
    _n=$1
    
    if [[ -z $2 ]]
    then
        numnets=1
    else
        numnets=$2
    fi
    
    for ((i=1; i <= $numnets ; i++))
    do    
        execute_command "echo net-delete ${SIM_NETWORK_NAME}-${_n}-${i}"
    done
}

function delete_user () {
    _n=$1 
    execute_command "echo user delete ${SIM_USER_NAME}-${_n}"
}

function delete_tenant () {
    _n=$1
    execute_command "echo project show ${SIM_TENANT_NAME}-${_n}" 

    for SECGID in $(uuidgen)
    do 
        execute_command "echo security-group-delete $SECGID"
    done        
    
    execute_command "echo project delete ${SIM_TENANT_NAME}-${_n}"
}
    
if [[ $step == "execute_deprovision_finished" ]]
then
    TNSR_OUTPUT="staging:execute_deprovision_finished"

    tenant_id=$(cat ${1} | grep \"project\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    date0=`date +%s`
    if [[ $create_lb == "true" ]]
    then
        lb_fip_id=$(cat ${1} | grep \"lb_fip_id\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')                          
        delete_lb_members $counter $tenant_id
        delete_lb_vips $counter $tenant_id
        delete_lb_pools $counter $tenant_id
        delete_floating_ip $lb_fip_id
    fi
    date1=`date +%s`
    ldiff=$((date1-date0))
    TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${SIM_TENANT_NAME}-$counter,sim_901_lb_deletion_time:${ldiff}"
    delete_router $counter
    date2=`date +%s`
    rdiff=$((date2-date1))
    TNSR_OUTPUT=$TNSR_OUTPUT",sim_902_router_deletion_time:${rdiff}"
    delete_subnet $counter
    date3=`date +%s`
    sdiff=$((date3-date2))
    TNSR_OUTPUT=$TNSR_OUTPUT",sim_903_subnet_deletion_time:${sdiff}"
    delete_network $counter
    date4=`date +%s`
    ndiff=$((date4-date3))
    TNSR_OUTPUT=$TNSR_OUTPUT",sim_904_network_deletion_time:${ndiff}"
    delete_user $counter
    date5=`date +%s`
    udiff=$((date5-date4))
    TNSR_OUTPUT=$TNSR_OUTPUT",sim_905_user_deletion_time:${udiff}"
    delete_tenant $counter  
    date6=`date +%s`
    udiff=$((date6-date5))
    TNSR_OUTPUT=$TNSR_OUTPUT",sim_906_tenant_deletion_time:${udiff}"
fi
    
if [[ $step == "execute_provision_finished" ]]
then

    vm_uuid=$(cat ${1} | grep cloud_vm_uuid | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    run_cloud_ip=$(cat ${1} | grep run_cloud_ip | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    tenant_id=$(cat ${1} | grep \"project\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    ext_net=$(cat ${1} | grep \"floating_pool\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
             
    date0=`date +%s`
    
    if [[ $ai_counter != "none" ]]
    then
        TNSR_OUTPUT="staging:none" 
        actual_counter=$ai_counter
    else
        TNSR_OUTPUT="staging:execute_deprovision_finished"                
                actual_counter=$counter
    fi
    
    if [[ $create_lb == "true" ]]
    then
        lb_floating_addr=$(cat ${1} | grep \"lb_fip_addr\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
        ssh_priv_key=$(cat ${1} | grep \"identity\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
        login_user=$(cat ${1} | grep \"login\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')       
        create_lb_member $actual_counter $tenant_id $run_cloud_ip
        connect_to_floating_ip $ssh_priv_key $login_user $lb_floating_addr
    fi
    
    date1=`date +%s`
    ldiff=$((date1-date0))

    tbstr=$(tac)
    tbs=$?   
    TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${SIM_TENANT_NAME}-$actual_counter"        
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}lb_member_creation:${ldiff}"  
        
    idiff=3
    sdiff=1
    pdiff=1    

    tbstr=$(tac)
    tbs=$?                                           
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}instance_scheduling_time:$sdiff"

    tbstr=$(tac)
    tbs=$?                                                   
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}instance_creation_time:$idiff"

    tbstr=$(tac)
    tbs=$?                                               
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}port_creation_time:$pdiff"
fi

if [[ $step == "execute_provision_originated" ]]
then
    
    credir=$(cat ${1} | grep credentials_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    basedir=$(cat ${1} | grep \"base_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    keyname=$(cat ${1} | grep ssh_key_name | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    ext_net=$(cat ${1} | grep \"floating_pool\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

    snipa=$(sed -n ${counter}p $basedir/scenarios/scripts/pre_computed_nets.txt)

    if [[ $ai_counter == "none" ]]
    then
        TNSR_OUTPUT="staging:execute_provision_finished"
    else
        TNSR_OUTPUT="staging:execute_deprovision_finished,vm_staging:execute_provision_finished"
    fi

    date0=`date +%s`
    create_tenant $counter
    date1=`date +%s`
    tdiff=$((date1-date0))
    tbstr=$(tac)
    tbs=$?          
    TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${SIM_TENANT_NAME}-$counter,project:$TID,${tbstr}tenant_creation_time:${tdiff}"
            
    if [[ $TENANT_JUST_CREATED -eq 1 ]]
    then   
        update_quotas $TID
    fi
    date2=`date +%s`
    qdiff=$((date2-date1))
    tbstr=$(tac)
    tbs=$?          
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}quota_update_time:$qdiff"
    create_user $counter $TID
    date3=`date +%s`
    udiff=$((date3-date2))
    tbstr=$(tac)
    tbs=$?          
    TNSR_OUTPUT=$TNSR_OUTPUT",user:$SIM_USER_NAME-${counter},${tbstr}user_creation_time:$udiff"
    if [[ $TENANT_JUST_CREATED -eq 1 ]]
    then           
        update_security_groups $TID
    fi
    date4=`date +%s`
    gdiff=$((date4-date3))
    tbstr=$(tac)
    tbs=$?           
    TNSR_OUTPUT=$TNSR_OUTPUT",ssh_key_injected:true,${tbstr}security_group_update_time:$gdiff"
    if [[ $TENANT_JUST_CREATED -eq 1 ]]
    then           
        add_keypair $credir $keyname $kusername $counter
    fi
    date5=`date +%s`
    kdiff=$((date5-date4))
    tbstr=$(tac)
    tbs=$?
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}keypair_creation_time:$kdiff"    
    create_network $counter $TID
    date6=`date +%s`
    ndiff=$((date6-date5))
    tbstr=$(tac)
    tbs=$?           
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}net_creation_time:${ndiff},netname:${SIM_NETWORK_NAME}-${counter}-1,run_netname:${SIM_NETWORK_NAME}-${counter}-1,prov_netname:${SIM_NETWORK_NAME}-${counter}-1"        
    create_subnet $counter $TID $snipa
    date7=`date +%s`
    sdiff=$((date7-date6))
    tbstr=$(tac)
    tbs=$?           
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}subnet_creation_time:${sdiff}"
    create_router $counter $TID     
    date8=`date +%s`
    rdiff=$((date8-date7))
    tbstr=$(tac)
    tbs=$?           
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}router_creation_time:${rdiff}"
    if [[ $ROUTER_JUST_CREATED -eq 1 ]]
    then
        attach_to_router $counter
        router_set_gateway $counter $ext_net
    fi
    date9=`date +%s`
    xdiff=$((date9-date8))
    tbstr=$(tac)
    tbs=$?           
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}router_attachment_time:${xdiff}"
    if [[ $create_lb == "true" ]]
    then
        TNSR_OUTPUT=$TNSR_OUTPUT",create_lb:true"
        create_lb_pools $counter $TID
        check_lb_pool_active $counter $TID 15 3
        create_lb_vips $counter $TID
        check_lb_vip_active $counter $TID 15 3                        
        create_floating_ip $ext_net $TID
        associate_floating_ip $LB_FLOATING_ID $LB_VIP_PORT
        TNSR_OUTPUT=$TNSR_OUTPUT",lb_vip_port:$LB_VIP_PORT,lb_fip_addr:$LB_FLOATING_ADDR,lb_fip_id:$LB_FLOATING_ID"
    fi
    date10=`date +%s`
    xdiff=$((date10-date9))
    tbstr=$(tac)
    tbs=$?    
    TNSR_OUTPUT=$TNSR_OUTPUT",${tbstr}lb_creation_time:${xdiff},time_breakdown_step:${tbs}"               

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