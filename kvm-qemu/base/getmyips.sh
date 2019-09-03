#!/bin/bash
NR_VNICS=$(ip -o link | grep -Ev 'virbr|docker|tun|xenbr|lxbr|lxdbr|cni|flannel|inet6|[[:space:]]lo:' | wc -l)

if [[ $NR_VNICS -gt 1 ]]
then
	
    export MY_PRIVATE_IP_LIST=$(ip -o addr list | grep -Ev 'virbr|docker|tun|xenbr|lxbr|lxdbr|cni|flannel|inet6|[[:space:]]lo[[:space:]]' | grep inet | awk '{ print $2,$3,$4 }' | grep -E 'inet (192\.168|10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.)' | awk '{ print $3 }' | cut -d '/' -f 1)
    export MY_PRIVATE_IP=$(echo $MY_PRIVATE_IP_LIST | cut -d ' ' -f 1)
    export MY_PRIVATE_IF=$(ip -o addr | grep $MY_PRIVATE_IP | awk '{ print $2 }')
    export MY_PUBLIC_IP=$(ip -o addr list | grep -Ev 'virbr|docker|tun|xenbr|lxbr|lxdbr|cni|flannel|inet6|[[:space:]]lo[[:space:]]' | grep -Ev "$(echo $MY_PRIVATE_IP_LIST | sed 's/ /|/g')" | grep -v inet6 | grep inet | awk '{ print $2,$3,$4 }' | awk '{ print $3 }' | cut -d '/' -f 1 | head -n 1)
    export MY_PUBLIC_IF=$(ip -o addr | grep $MY_PUBLIC_IP | awk '{ print $2 }')		
fi
