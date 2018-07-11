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
(bash -c "sleep 5; redis-cli -h SERVER_BOOTSTRAP -n OSCI_DBID -p OSCI_PORT hset TEST_USER:CLOUD_NAME:VM:PENDING:UUID cloud_init_vpn $VPNIP; exists=\$(redis-cli --raw -h SERVER_BOOTSTRAP -n OSCI_DBID -p OSCI_PORT hexists TEST_USER:CLOUD_NAME:VM:UUID cloud_init_vpn); if [ \$exists == 1 ] ; then redis-cli -h SERVER_BOOTSTRAP -n OSCI_DBID -p OSCI_PORT hset TEST_USER:CLOUD_NAME:VM:UUID cloud_init_vpn $VPNIP; redis-cli -h SERVER_BOOTSTRAP -n OSCI_DBID -p OSCI_PORT hset TEST_USER:CLOUD_NAME:VM:UUID prov_cloud_ip $VPNIP; fi" &)
(/tmp/cb_post_boot.sh &)
env | sort >> $logpath
exit 0
