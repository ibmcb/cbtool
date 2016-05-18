#!/usr/bin/env bash

source ~/.bashrc

OSK_TENANT_NAME=cb-tenant
OSK_USER_NAME=cb-user
OSK_NETWORK_NAME=cb-tenantnet
OSK_SUBNETWORK_NAME=cb-subtenantnet
OSK_ROUTER_NAME=cb-router
OSK_LBPOOL_NAME=cb-lbpool
OSK_LBVIP_NAME=cb-lbvip
OSK_LBMEMBER_NAME=cb-lbmember

#TNSRC_ERROR=0
  
counter=$(cat ${1} | grep '"'name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | cut -d '_' -f 2)
step=$(cat ${1} | grep '"'staging'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')    
model=$(cat ${1} | grep model | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
cloud_name=$(cat ${1} | grep '"'cloud_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
create_lb=$(cat ${1} | grep \"create_lb\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')
ai_counter=$(cat ${1} | grep '"'ai_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | cut -d '_' -f 2)
                    
if [[ -z $create_lb ]]
then
    create_lb=false
fi
        
source ~/cbrc-${cloud_name}

function create_tenant () {
    _n=$1
    TINFO=$(openstack project show ${OSK_TENANT_NAME}-${_n} 2>&1)
    export TENANT_JUST_CREATED=0    
    if [[ $(echo "$TINFO" | grep -c [[:space:]]id[[:space:]]) -eq 0 ]]
    then
        openstack project create ${OSK_TENANT_NAME}-${_n} > /dev/null 2>&1 || ( echo "tenant creation failed"; export TNSRC_ERROR=1 )
        TINFO=$(openstack project show ${OSK_TENANT_NAME}-${_n} 2>&1)
        export TENANT_JUST_CREATED=1
    fi
    TID=$(echo "$TINFO" | grep [[:space:]]id[[:space:]] | cut -d '|' -f 3 | tr -d ' ')
    export TID
}

function update_quotas () {
    _t=$1
    nova quota-update ${_t} --metadata-items 100000 > /dev/null 2>&1
    nova quota-update ${_t} --instances 100000 > /dev/null 2>&1
    nova quota-update ${_t} --volumes 10000 > /dev/null 2>&1
    nova quota-update ${_t} --gigabytes 1000000 > /dev/null 2>&1
    nova quota-update ${_t} --floating-ips 100 > /dev/null 2>&1
    nova quota-update ${_t} --ram 1000000000 > /dev/null 2>&1
    nova quota-update ${_t} --cores 100000 > /dev/null 2>&1
    #cinder quota-update --volumes 10000 ${TID} > /dev/null 2>&1
}

function create_user () {
    _n=$1
    _t=$2
    openstack user show ${OSK_USER_NAME}-${_n} > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then    
        openstack user create --password temp4now --project ${_t} --email user-${_n}@nowhere.org --enable ${OSK_USER_NAME}-${_n} > /dev/null 2>&1 
        if [[ $? -ne 0 ]]
        then
            echo "user creation failed" >&2
            export TNSRC_ERROR=1
        fi
        export USER_JUST_CREATED=1
    else
        export USER_JUST_CREATED=0           
    fi
}

function update_security_groups () {
    _t=$1
    secgroup=$(neutron security-group-list --tenant-id ${_t} | grep default | awk '{ print $2 }')
    neutron security-group-rule-create $secgroup --direction ingress --protocol icmp > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "failed to update secgroup" >&2
        export TNSRC_ERROR=1
    fi    
    neutron security-group-rule-create $secgroup --direction ingress --protocol tcp --port-range-min 22 --port-range-max 22 > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "failed to update secgroup" >&2
        export TNSRC_ERROR=1
    fi    
}

function add_keypair () {
    keypath=$1
    keyname=$2
    kusername=$3    
    _n=$4
    nova --os-tenant-name cb-tenant-${_n} --os-username ${OSK_USER_NAME}-${_n} --os-password temp4now keypair-add --pub-key $keypath/${keyname}.pub ${kusername}_cb-tenant-${_n}_${keyname} > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "pubkey injection failed" >&2
        export TNSRC_ERROR=1
    fi
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
    
    for ((i=1; i <= $numnets ; i++))
    do 
        neutron net-show ${OSK_NETWORK_NAME}-${_n}-${i} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then         
            neutron net-create --tenant-id ${_t} ${OSK_NETWORK_NAME}-${_n}-${i} > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then
                echo "network creation failed" >&2
                export TNSRC_ERROR=1
            fi        
        fi
    done
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
            neutron subnet-show ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then                                                                      
                neutron subnet-create --tenant-id ${_t} --name ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} --enable-dhcp ${OSK_NETWORK_NAME}-${_n}-${i} ${_snipa} > /dev/null 2>&1
                if [[ $? -ne 0 ]]
                then
                    echo "subnet creation failed" >&2
                    export TNSRC_ERROR=1
                fi  
            fi
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
        neutron router-show ${OSK_ROUTER_NAME}-${_n}-${i} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            neutron router-create --tenant-id ${_t} ${OSK_ROUTER_NAME}-${_n}-${i} > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then
                echo "router creation failed" >&2
                export TNSRC_ERROR=1
            fi                  
            export ROUTER_JUST_CREATED=1
        else
            export ROUTER_JUST_CREATED=0
        fi
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
        neutron router-gateway-set ${OSK_ROUTER_NAME}-${_n}-${i} ${_extnet} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "setting router gateway failed" >&2
            export TNSRC_ERROR=1
        fi              
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
                neutron router-interface-add  ${OSK_ROUTER_NAME}-${_n}-${k} ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} > /dev/null 2>&1 
                if [[ $? -ne 0 ]]
                then
                    echo "router attachment failed" >&2
                    export TNSRC_ERROR=1
                fi         
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
                neutron lb-pool-show ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} > /dev/null 2>&1
                if [[ $? -ne 0 ]]
                then    
#                    neutron lb-pool-create --name ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol HTTP --subnet-id ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} --lb-method ROUND_ROBIN > /dev/null 2>&1
                    neutron lb-pool-create --name ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol TCP --subnet-id ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} --lb-method ROUND_ROBIN > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "lb pool creation failed" >&2
                        export TNSRC_ERROR=1
                    fi
                else
                    /bin/true
                fi    
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
                neutron lb-vip-show ${OSK_LBVIP_NAME}-${_n}-${i}-${j}-${k}  > /dev/null 2>&1
                if [[ $? -ne 0 ]]
                then
#                    export LB_VIP_PORT=$(neutron lb-vip-create --name ${OSK_LBVIP_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol-port 80 --protocol HTTP --subnet-id ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} | grep port_id | cut -d "|" -f 3)
                    export LB_VIP_PORT=$(neutron lb-vip-create --name ${OSK_LBVIP_NAME}-${_n}-${i}-${j}-${k} --tenant-id ${_t} --protocol-port 22 --protocol TCP --subnet-id ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} | grep port_id | cut -d "|" -f 3)
                    if [[ $? -ne 0 ]]
                    then
                        echo "lb VIP creation failed" >&2
                        export TNSRC_ERROR=1
                    fi
                else
                    /bin/ture
                fi
            done
        done
    done
}
    
function create_lb_member () {
    _n=$1
    _t=$2
    _ipaddr=$3

    
    #for instaddr in $(openstack server list --project ${OSK_NETWORK_NAME}-${_n}-1 -c Networks | grep cb-tenantnet | cut -d '=' -f 2 | cut -d ',' -f 1)

#    neutron lb-member-create --tenant-id ${_t} --protocol-port 80 --address ${_ipaddr} ${OSK_LBPOOL_NAME}-${_n}-1-1-1 > /dev/null 2>&1
    neutron lb-member-create --tenant-id ${_t} --protocol-port 22 --address ${_ipaddr} ${OSK_LBPOOL_NAME}-${_n}-1-1-1 > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "lb member creation failed" >&2
        export TNSRC_ERROR=1
    fi
}

function check_lb_active () {
    _n=$1
    _t=$2
    
    #for instaddr in $(openstack server list --project ${OSK_NETWORK_NAME}-${_n}-1 -c Networks | grep cb-tenantnet | cut -d '=' -f 2 | cut -d ',' -f 1)

    neutron lb-pool-list --tenant-id ${_t} | grep ACTIVE > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "lb pool creation failed" >&2
        export TNSRC_ERROR=1
    fi    
    
    neutron lb-vip-list --tenant-id ${_t} | grep ACTIVE > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "lb VIP creation failed" >&2
        export TNSRC_ERROR=1
    fi
        
}

function create_floating_ip () {
    _ext_net=$1
    LB_FLOATING_INFO=$(neutron floatingip-create ${ext_net} --tenant-id ${tenant_id})
    if [[ $? -ne 0 ]]
    then
        echo "lb FIP creation failed" >&2        
        export TNSRC_ERROR=1
    else
        export LB_FLOATING_ID=$(echo "$LB_FLOATING_INFO" | grep [[:space:]]id[[:space:]] | cut -d "|" -f 3)
        export LB_FLOATING_ADDR=$(echo "$LB_FLOATING_INFO" | grep floating_ip_address | cut -d "|" -f 3)        
    fi
}
    
function associate_floating_ip () {
    _lb_fip_id=$1
    _lb_vip_port=$2
    
    neutron floatingip-associate ${_lb_fip_id} ${_lb_vip_port} > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "lb FIP association failed" >&2
        export TNSRC_ERROR=1
    fi
}
 
function connect_to_floating_ip () {
    _ssh_priv_key=$1
    _login_user=$2
    _fip=$3
    
    ssh -i ${_ssh_priv_key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -l ${_login_user} ${_fip} "/bin/true" > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "lb FIP connection failed" >&2
        export TNSRC_ERROR=1
    fi
}                                        
                                                                                                                   
function delete_floating_ip () {
    _lb_fip_id=$1
    
    neutron floatingip-delete ${_lb_fip_id} > /dev/null 2>&1    
    if [[ $? -ne 0 ]]
    then
        echo "lb FIP deletion failed" >&2        
        export TNSRC_ERROR=1
    fi
}

function delete_lb_member () {
    _n=$1
    _t=$2
    _ipaddr=$3

    LB_UUID=$(neutron lb-member-list --address ${_ipaddr} -c id -f value)
    if [[ ! -z $LB_UUID ]]
    then
        neutron lb-member-delete $LB_UUID > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "lb member deletion failed" >&2
            export TNSRC_ERROR=1
        fi  
    else
        /bin/true
    fi
}

function delete_lb_members () {
    _n=$1
    _t=$2

    for LB_MEMBER_UUID in $(neutron lb-member-list --tenant-id ${_t} -c id -f value)
    do 
        neutron lb-member-delete $LB_MEMBER_UUID > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "lb member deletion failed" >&2
            export TNSRC_ERROR=1
        fi
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
                neutron lb-vip-show ${OSK_LBVIP_NAME}-${_n}-${i}-${j}-${k}  > /dev/null 2>&1
                if [[ $? -eq 0 ]]
                then
                    neutron lb-vip-delete ${OSK_LBVIP_NAME}-${_n}-${i}-${j}-${k} > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "lb VIP creation failed" >&2
                        export TNSRC_ERROR=1
                    fi                  
                else
                    /bin/ture
                fi
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
                neutron lb-pool-show ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k} > /dev/null 2>&1
                if [[ $? -eq 0 ]]
                then    
                    neutron lb-pool-delete ${OSK_LBPOOL_NAME}-${_n}-${i}-${j}-${k}  > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "lb pool creation failed" >&2
                        export TNSRC_ERROR=1
                    fi                  
                else
                    /bin/true
                fi    
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
                neutron router-show ${OSK_ROUTER_NAME}-${_n}-${k} > /dev/null 2>&1
                if [[ $? -eq 0 ]]
                then
                    for sn in $(neutron router-port-list ${OSK_ROUTER_NAME}-${_n}-${k} -F fixed_ips | grep subnet_id | awk '{ print $3 }' | sed 's/"//g' | sed 's/,//g')
                    do
                        neutron router-interface-delete ${OSK_ROUTER_NAME}-${_n}-${k} $sn > /dev/null 2>&1
                    done        
                    neutron router-delete ${OSK_ROUTER_NAME}-${_n}-${k} > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "router deletion failed" >&2
                        export TNSRC_ERROR=1
                    fi
                fi                       
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
            neutron subnet-show ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} > /dev/null 2>&1
            if [[ $? -eq 0 ]]
            then                                       
                neutron subnet-delete ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} > /dev/null 2>&1
                if [[ $? -ne 0 ]]
                then
                    echo "subnet deletion failed" >&2
                    export TNSRC_ERROR=1
                fi
            fi                                     
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
        neutron net-show ${OSK_NETWORK_NAME}-${_n}-${i} > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then        
            neutron net-delete ${OSK_NETWORK_NAME}-${_n}-${i} > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then
                echo "network deletion failed" >&2
                export TNSRC_ERROR=1
            fi
        fi          
    done
}

function delete_user () {
    _n=$1 
    openstack user show ${OSK_USER_NAME}-${_n} > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        openstack user delete ${OSK_USER_NAME}-${_n} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "user deletion failed" >&2
            export TNSRC_ERROR=1
        fi
    fi            
}

function delete_tenant () {
    _n=$1
    openstack project show ${OSK_TENANT_NAME}-${_n} > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then

        TID=$(openstack project show ${OSK_TENANT_NAME}-${_n} | grep [[:space:]]id[[:space:]] | cut -d '|' -f 3 | tr -d ' ')
        for SECGID in $(neutron security-group-list --tenant_id $TID | grep default | awk '{ print $2 }')
        do 
            neutron security-group-delete $SECGID
        done        
        
        openstack project delete ${OSK_TENANT_NAME}-${_n} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "tenant deletion failed" >&2
            export TNSRC_ERROR=1
        fi
    fi          
}
    
if [[ $step == "execute_deprovision_finished" ]]
then
    TNSR_OUTPUT="staging:execute_deprovision_finished"

    if [[ $model == "sim" ]]
    then
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,sim_901_test_deletion_time:1"
        echo "$TNSR_OUTPUT"
    elif [[ $model == "osk" ]]
    then
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
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,osk_901_lb_deletion_time:${ldiff}"
        delete_router $counter
        date2=`date +%s`
        rdiff=$((date2-date1))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_902_router_deletion_time:${rdiff}"
        delete_subnet $counter
        date3=`date +%s`
        sdiff=$((date3-date2))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_903_subnet_deletion_time:${sdiff}"
        delete_network $counter
        date4=`date +%s`
        ndiff=$((date4-date3))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_904_network_deletion_time:${ndiff}"
        delete_user $counter
        date5=`date +%s`
        udiff=$((date5-date4))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_905_user_deletion_time:${udiff}"
        delete_tenant $counter  
        date6=`date +%s`
        udiff=$((date6-date5))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_906_tenant_deletion_time:${udiff}"
        if [[ $TNSRC_ERROR -eq 0 ]]
        then
            echo "$TNSR_OUTPUT"
        else
            exit 1
        fi
    else
        exit 0
    fi
fi

if [[ $step == "execute_provision_finished" ]]
then
    if [[ $model == "sim" ]]
    then
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,sim_051_test_creation_time:10"
        echo "$TNSR_OUTPUT"
    else
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
            lb_vip_port=$(cat ${1} | grep \"lb_vip_port\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
            ssh_priv_key=$(cat ${1} | grep \"identity\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
            login_user=$(cat ${1} | grep \"login\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')       
            create_lb_member $actual_counter $tenant_id $run_cloud_ip
            check_lb_active $actual_counter $tenant_id
            create_floating_ip $ext_net
            associate_floating_ip $LB_FLOATING_ID $lb_vip_port
            connect_to_floating_ip $ssh_priv_key $login_user $LB_FLOATING_ADDR
        fi
        
        date1=`date +%s`
        ldiff=$((date1-date0))
        
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$actual_counter"        
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_017_lb_member_creation:${ldiff},lb_fip_id:$LB_FLOATING_ID,lb_fip_addr:$LB_FLOATING_ADDR"  
        
        stacky_output=$(stacky uuid $vm_uuid)
        
        if [[ $(echo "$stacky_output" | grep -c "No results") -eq 0 ]]
        then
            idiff=$(echo "$stacky_output" | grep '|[[:space:]]\.[[:space:]]|' | grep compute.instance.create | awk '{ print$7 }')
            sdiff=$(echo "$stacky_output" | grep '|[[:space:]]\.[[:space:]]|' | grep scheduler.select_destinations | awk '{ print$7 }')
            pdiff=$(echo "$stacky_output" | grep '|[[:space:]]\.[[:space:]]|' | grep port.create | awk '{ print$7 }')
            
            if [[ $(echo $idiff | grep -c ':') -ne 0 ]]
            then 
                idiff=$(echo $idiff | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
            else
                idiff=$idiff"NA"
            fi

            if [[ $(echo $sdiff | grep -c ':') -ne 0 ]]
            then 
                sdiff=$(echo $sdiff | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
            else
                sdiff=$sdiff"NA"
            fi            

            if [[ $(echo $pdiff | grep -c ':') -ne 0 ]]
            then 
                pdiff=$(echo $pdiff | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
            else
                pdiff=$pdiff"NA"
            fi                                                
    
            TNSR_OUTPUT=$TNSR_OUTPUT",osk_018_instance_scheduling_time:$sdiff,osk_019_instance_creation_time:$idiff,osk_018_port_creation_time:$pdiff"
        fi
        
        if [[ $TNSRC_ERROR -eq 0 ]]
        then
            echo "$TNSR_OUTPUT"
        else
            exit 1
        fi   
    fi
fi

if [[ $step == "execute_provision_originated" ]]
then
    
    credir=$(cat ${1} | grep credentials_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    basedir=$(cat ${1} | grep \"base_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    keyname=$(cat ${1} | grep ssh_key_name | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    kusername=$(cat ${1} | grep \"username\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    ext_net=$(cat ${1} | grep \"floating_pool\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

    if [[ $model == "osk" ]]
    then
        if [[ -z $ext_net ]]
        then
            echo "error: floating_pool not defined"
            exit 1
        fi
    fi

    snipa=$(sed -n ${counter}p $basedir/scenarios/scripts/pre_computed_nets.txt)

    if [[ $ai_counter == "none" ]]
    then
        TNSR_OUTPUT="staging:execute_provision_finished"
    else
        TNSR_OUTPUT="staging:execute_deprovision_finished,vm_staging:execute_provision_finished"
    fi

    if [[ $model == "sim" ]]
    then
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,sim_001_test_creation_time:1"
        echo "$TNSR_OUTPUT"
    elif [[ $model == "osk" ]]
    then             
        date0=`date +%s`
        create_tenant $counter
        date1=`date +%s`
        tdiff=$((date1-date0))
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,project:$TID,osk_001_tenant_creation_time:${tdiff}"
        if [[ $TENANT_JUST_CREATED -eq 1 ]]
        then   
            update_quotas $TID
        fi
        date2=`date +%s`
        qdiff=$((date2-date1))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_002_quota_update_time:$qdiff"
        create_user $counter $TID
        date3=`date +%s`
        udiff=$((date3-date2))
        TNSR_OUTPUT=$TNSR_OUTPUT",user:$OSK_USER_NAME-${counter},osk_003_user_creation_time:$udiff"
        if [[ $TENANT_JUST_CREATED -eq 1 ]]
        then           
            update_security_groups $TID
        fi
        date4=`date +%s`
        gdiff=$((date4-date3))
        TNSR_OUTPUT=$TNSR_OUTPUT",ssh_key_injected:true,osk_004_security_group_update_time:$gdiff"
        if [[ $TENANT_JUST_CREATED -eq 1 ]]
        then           
            add_keypair $credir $keyname $kusername $counter
        fi
        date5=`date +%s`
        kdiff=$((date5-date4))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_005_keypair_creation_time:$kdiff"    
        create_network $counter $TID
        date6=`date +%s`
        ndiff=$((date6-date5))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_006_net_creation_time:${ndiff},netname:${OSK_NETWORK_NAME}-${counter}-1,run_netname:${OSK_NETWORK_NAME}-${counter}-1,prov_netname:${OSK_NETWORK_NAME}-${counter}-1"        
        create_subnet $counter $TID $snipa
        date7=`date +%s`
        sdiff=$((date7-date6))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_007_subnet_creation_time:${sdiff}"
        create_router $counter $TID     
        date8=`date +%s`
        rdiff=$((date8-date7))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_008_router_creation_time:${rdiff}"
        if [[ $ROUTER_JUST_CREATED -eq 1 ]]
        then
            attach_to_router $counter
            router_set_gateway $counter $ext_net
        fi
        date9=`date +%s`
        xdiff=$((date9-date8))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_009_router_attachment:${xdiff}"
        if [[ $create_lb == "true" ]]
        then
            TNSR_OUTPUT=$TNSR_OUTPUT",create_lb:true"
            create_lb_pools $counter $TID
            create_lb_vips $counter $TID
            TNSR_OUTPUT=$TNSR_OUTPUT",lb_vip_port:$LB_VIP_PORT"       
        fi
        date10=`date +%s`
        xdiff=$((date10-date9))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_010_lb_creation:${xdiff}"                
        if [[ $TNSRC_ERROR -eq 0 ]]
        then
            echo "$TNSR_OUTPUT"
        else
            exit 1
        fi
    else
        exit 0        
    fi
fi