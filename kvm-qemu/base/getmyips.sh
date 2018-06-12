#!/bin/bash
NR_VNICS=$(ip addr | grep -v lo | grep -v virbr | grep -v docker | grep -v tun | grep mtu | wc -l)

if [[ $NR_VNICS -gt 1 ]]
then
    export MY_PRIVATE_IP=$(ip -o addr list | grep -v virbr | grep -v docker | grep -v tun | grep -v inet6 | grep inet | awk '{ print $2,$3,$4 }' | grep -E 'inet (192\.168|10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|90\.90\.)' | awk '{ print $3 }' | cut -d '/' -f 1 | head -n 1)
    export MY_PRIVATE_IF=$(ip -o addr | grep $PRIVATE_IP | awk '{ print $2 }')
    export MY_PUBLIC_IP=$(ip -o addr list | grep -v virbr | grep -v docker | grep -v tun | grep -v 127.0.0.1 | grep -v $PRIVATE_IP | grep -v inet6 | grep inet | awk '{ print $2,$3,$4 }' | awk '{ print $3 }' | cut -d '/' -f 1 | head -n 1)
    export MY_PUBLIC_IF=$(ip -o addr | grep $PUBLIC_IP | awk '{ print $2 }')
fi