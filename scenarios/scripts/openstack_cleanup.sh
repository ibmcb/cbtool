#!/usr/bin/env bash

OSK_TENANT_NAME=cb-tenant
OSK_USER_NAME=cb-user
OSK_NETWORK_NAME=cb-tenantnet
OSK_SUBNETWORK_NAME=cb-subtenantnet
OSK_ROUTER_NAME=cb-router
OSK_LBPOOL_NAME=cb-lbpool
OSK_LBVIP_NAME=cb-lbvip
OSK_LBMEMBER_NAME=cb-lbmember
FLAVOR_SIZE=5

function all_clear () {

    for iuuid in $(nova list --all-tenants | grep ${CB_CLOUD_NAME} | grep ${CB_USERNAME} | awk '{ print $2 }')
    do
        echo "deleting instance $iuuid"
        nova delete $iuuid
    done 

    # delete pools
    for lbpool in $(neutron lb-pool-list | grep $OSK_LBPOOL_NAME | awk '{ print $2 }')
    do
        echo "deleting lbpool $lbpool"
        for lbvip in $(neutron lb-vip-list --pool-id $lbpool -c id -c pool_id | awk '{ print $2 }')
        do
            neutron lb-vip-delete $lbvip 
        done
        
        for lbmember in $(neutron lb-member --pool-id $lbpool-list -c id -c pool_id | awk '{ print $2 }')
        do
            neutron lb-member-delete $lbmember
        done
    
        neutron lb-pool-delete $lbpool         
    done    

    for fip in $(neutron floatingip-list | awk '{if(length($4)<2)print $2}')
    do
        echo "deleting floating IP $fip"
        neutron floatingip-delete $fip
    done    
            
    # delete routers
    for rtr in $(neutron router-list | grep $OSK_ROUTER_NAME | awk '{ print $2 }')
    do
        echo "deleting router $rtr"
        for sn in $(neutron router-port-list $rtr -F fixed_ips | grep subnet_id | awk '{ print $3 }' | sed 's/"//g' | sed 's/,//g')
        do
            neutron router-interface-delete $rtr $sn
        done        
        neutron router-delete $rtr > /dev/null 2>&1
    done    
    
    # delete subnets
    for subnet in $(neutron subnet-list | grep $OSK_SUBNETWORK_NAME | awk '{ print $2 }')
    do
        echo "deleting subnet $subnet"
        neutron subnet-delete $subnet > /dev/null 2>&1
    done

    # delete networks
    for net in $(neutron net-list | grep $OSK_NETWORK_NAME | awk '{ print $2 }')
    do
        echo "deleting net $net"
        neutron net-delete $net > /dev/null 2>&1
    done

    # delete users
    for user in $(openstack user list | grep $OSK_USER_NAME | awk '{ print $2 }')
    do
        echo "deleting user $user"
        openstack user delete $user > /dev/null 2>&1
    done

    # delete tenants
    for tid in $(openstack project list | grep ${OSK_TENANT_NAME} | awk -F '|' '{ print $3 }')
    do  
        echo "deleting neutron security groups belonging to tenant $tid"
        for sid in $(neutron security-group-list --tenant_id $tid | grep default | awk '{ print $2 }')
        do 
            neutron security-group-delete $sid
        done

        echo "deleting tenant $tid"
        openstack project delete $tid
    done
}

function set_quotas () {
    neutron quota-update --security-group-rule -1
    neutron quota-update --security-group -1
    neutron quota-update --subnet -1
    neutron quota-update --floatingip -1
    neutron quota-update --network -1
    neutron quota-update --port -1
    neutron quota-update --rbac_policy -1
    neutron quota-update --router -1
}

function create_smallest_flavor {
    if [[ $(nova flavor-list | grep f1.nano | grep -c 64[[:space:]]) -eq 0 ]]
    then
        nova flavor-create f1.nano auto 64 $FLAVOR_SIZE 1
    fi

}

for RCFILE in $(ls ~/cbrc-*)
do
    source $RCFILE
    all_clear
    set_quotas
    create_smallest_flavor
done
