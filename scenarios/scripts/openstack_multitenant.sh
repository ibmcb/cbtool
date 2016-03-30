#!/usr/bin/env bash

source ~/.bashrc

OSK_TENANT_NAME=cb-tenant
OSK_USER_NAME=cb-user
OSK_NETWORK_NAME=cb-tenantnet
OSK_SUBNETWORK_NAME=cb-subtenantnet
OSK_ROUTER_NAME=cb-router

#TNSRC_ERROR=0

#counter=$(echo ${1} | cut -d _ -f 5)
#counter=$(cat ${1} | grep counter | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')    
counter=$(cat ${1} | grep '"'name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | cut -d '_' -f 2)
step=$(cat ${1} | grep staging\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')    
model=$(cat ${1} | grep model | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
cloud_name=$(cat ${1} | grep '"'cloud_name'"' | cut -d ':' -f 2 | sed 's^"\|,\| ^^g' | tr '[:upper:]' '[:lower:]')

source ~/cbrc-${cloud_name}

function create_tenant () {
    _n=$1
    TINFO=$(openstack project show ${OSK_TENANT_NAME}-${_n} 2>&1)
    if [[ $(echo "$TINFO" | grep -c [[:space:]]id[[:space:]]) -eq 0 ]]
    then
        openstack project create ${OSK_TENANT_NAME}-${_n} > /dev/null 2>&1 || ( echo "tenant creation failed"; export TNSRC_ERROR=1 )
        TINFO=$(openstack project show ${OSK_TENANT_NAME}-${_n} 2>&1)
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
        export TENANT_JUST_CREATED=1
    else
        export TENANT_JUST_CREATED=0           
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
            neutron subnet-delete ${OSK_SUBNETWORK_NAME}-${_n}-${i}-${j} > /dev/null 2>&1
	        if [[ $? -ne 0 ]]
	        then
	            echo "subnet deletion failed" >&2
	            export TNSRC_ERROR=1
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
        neutron net-delete ${_t} ${OSK_NETWORK_NAME}-${_n}-${i} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            echo "network deletion failed" >&2
            export TNSRC_ERROR=1
        fi          
    done
}

function delete_user () {
    _n=$1 
    openstack user delete ${OSK_USER_NAME}-${_n} > /dev/null 2>&1
	if [[ $? -ne 0 ]]
	then
	    echo "user deletion failed" >&2
	    export TNSRC_ERROR=1
	fi              
}

function delete_tenant () {
    _n=$1
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
        date0=`date +%s`
        delete_router $counter
        date1=`date +%s`
        rdiff=$((date1-date0))
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,osk_901_router_deletion_time:${rdiff}"
        delete_subnet $counter
        date2=`date +%s`
        sdiff=$((date2-date1))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_902_subnet_deletion_time:${sdiff}"
        delete_network $counter
        date3=`date +%s`
        ndiff=$((date3-date2))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_903_network_deletion_time:${ndiff}"
        delete_user $counter
        date4=`date +%s`
        udiff=$((date4-date3))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_904_user_deletion_time:${udiff}"
        delete_tenant $counter  
        date5=`date +%s`
        udiff=$((date5-date4))
        TNSR_OUTPUT=$TNSR_OUTPUT",osk_905_tenant_deletion_time:${udiff}"
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
        TNSR_OUTPUT="staging:execute_deprovision_finished,tenant:${OSK_TENANT_NAME}-$counter"
        vm_uuid=$(cat ${1} | grep cloud_vm_uuid | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
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
    
            TNSR_OUTPUT=$TNSR_OUTPUT",osk_016_instance_scheduling_time:$sdiff,osk_016_instance_creation_time:$idiff,osk_016_port_creation_time:$pdiff"
        fi
        echo "$TNSR_OUTPUT"    
    fi
fi

if [[ $step == "execute_provision_originated" ]]
then
    
    credir=$(cat ${1} | grep credentials_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    basedir=$(cat ${1} | grep \"base_dir | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    keyname=$(cat ${1} | grep ssh_key_name | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    kusername=$(cat ${1} | grep \"username\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')
    ext_net=$(cat ${1} | grep \"floating_pool\" | cut -d ':' -f 2 | sed 's^"\|,\| ^^g')

    snipa=$(sed -n ${counter}p $basedir/scenarios/scripts/pre_computed_nets.txt)

    TNSR_OUTPUT="staging:execute_provision_finished"

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
        TNSR_OUTPUT=$TNSR_OUTPUT",tenant:${OSK_TENANT_NAME}-$counter,osk_001_tenant_creation_time:${tdiff}"
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
