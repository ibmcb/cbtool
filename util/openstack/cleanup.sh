#!/usr/bin/env bash

OSK_TENANT_NAME=cb-tenant
OSK_USER_NAME=cb-user
OSK_NETWORK_NAME=cb-tenantnet
OSK_SUBNETWORK_NAME=cb-subtenantnet
OSK_ROUTER_NAME=cb-router

function all_clear () {

    for iuuid in $(nova list --all-tenants | grep ${CB_CLOUD_NAME} | grep ${CB_USERNAME} | awk '{ print $2 }')
    do
        echo "deleting instance $iuuid"
        nova delete $iuuid
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

for RCFILE in $(ls ~/cbrc-*)
do
    source $RCFILE
    all_clear
done
