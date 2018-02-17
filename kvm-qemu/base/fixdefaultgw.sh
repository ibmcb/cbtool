#!/bin/bash
NR_VNICS=$(ip addr | grep -v lo | grep mtu | wc -l)

if [[ $NR_VNICS -gt 1 ]]
then
    PRIVATE_IP=$(ip -o addr list | grep -v virbr | grep -v docker | grep -v tun | grep -v inet6 | grep inet | awk '{ print $2,$3,$4 }' | grep -E 'inet (192\.168|10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.)' | awk '{ print $3 }' | cut -d '/' -f 1 | head -n 1)
    PRIVATE_IF=$(ip -o addr | grep $PRIVATE_IP | awk '{ print $2 }')
    PUBLIC_IP=$(ip -o addr list | grep -v virbr | grep -v docker | grep -v tun | grep -v 127.0.0.1 | grep -v $PRIVATE_IP | grep -v inet6 | grep inet | awk '{ print $2,$3,$4 }' | awk '{ print $3 }' | cut -d '/' -f 1 | head -n 1)
    PUBLIC_IF=$(ip -o addr | grep $PUBLIC_IP | awk '{ print $2 }')

    netstat -rn | grep UG | grep $PUBLIC_IF
    COUT=$?
    DEFAULT_GW=$(netstat -rn | grep UG | awk '{ print $2 }')
    DEFAULT_IF=$(netstat -rn | grep UG | awk '{ print $8 }')

    if [[ $COUT -ne 0 ]]
    then
        echo "Deleting default route with \"root delete default gw $DEFAULT_GW $DEFAULT_IF\"" >> /tmp/fixdefaultgw
        route delete default gw $DEFAULT_GW $DEFAULT_IF
        echo "Restarting (ifdown/ifup) $PUBLIC_IF" >> /tmp/fixdefaultgw
        ifdown $PUBLIC_IF; ifup $PUBLIC_IF
        netstat -rn | grep UG | grep $PUBLIC_IF
        DEFAULT_GW=$(netstat -rn | grep UG | awk '{ print $2 }')
        DEFAULT_IF=$(netstat -rn | grep UG | awk '{ print $8 }')        
        if [[ $? -eq 0 ]]
        then
            echo "Default GW ($DEFAULT_GW) is now accessible through the PUBLIC interface ($PUBLIC_IF)" >> /tmp/fixdefaultgw
        else
            echo "Something went wrong. Default GW ($DEFAULT_GW) is still specified over the PRIVATE interface ($PRIVATE_IF)" >> /tmp/fixdefaultgw
            exit 1
        fi
    else
        echo "Default GW ($DEFAULT_GW) was already accessible through the PUBLIC interface ($PUBLIC_IF)" >> /tmp/fixdefaultgw
    fi
else
    echo "Single VNIC. Nothing to be done" >> /tmp/fixdefaultgw    
fi
exit 0