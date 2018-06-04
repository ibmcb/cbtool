#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

mkdir -p /var/log/cloudbench

logpath=/var/log/cloudbench/${USER}_openvpn_client.log
tap=$1
mtu=$2
other_mtu=$3
VPNIP=$4
peer=$5
dunno=$6

echo "client connected $(date) params: $@" >> $logpath

# This is deliberate: We *must* call redis-cli here when VPN_ONLY = $True 
# because is this the only time which the VPN is fully connected. It cannot be
# called earlier.
(bash -c "sleep 5; redis-cli -h SERVER_BOOTSTRAP -n OSCI_DBID -p OSCI_PORT hset TEST_USER:CLOUD_NAME:VM:PENDING:UUID cloud_init_vpn $VPNIP" &)

# Run cloudbench's cloud-agnostic userdata later. Backwards compatible with VPN_ONLY = False
(/tmp/userscript.sh &)

env | sort >> $logpath

exit 0
