#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

# The purpose of this script is when the user has the VPN server
# running in a different location than the tool itself (i.e. the
# local VPN server is not publicly available.
# In these cases, the user should join the tool's machine (such
# as a laptop or other machine) to the VPN using the template
# generated in configs/generated/XXXXX_mongo-cb-XXXXX.conf

# This particular client config is generated just for this purposes.

# The problem is that whenever you sleep your laptop or restart
# the VM/machine running cloudbench, the client gets a new IP address.
# Thus, instead of updating the cloudbench configuration file itself
# all the time, we're going to invoke the cloudbench CLI and
# correct the key/value pair instead.

mkdir -p /var/log/cloudbench

tap=$1
mtu=$2
other_mtu=$3
VPNIP=$4
peer=$5
dunno=$6

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

who=$(stat -c '%U' $dir)
logpath=/var/log/cloudbench/${who}_openvpn_mongo_client.log

echo "client connected $(date) params: $@" >> $logpath

# NOTE: This will only work if the default cloud is it the one using the VPN.
(su ${who} bash -c "sleep 5; ${dir}/../../cb cldalter vpn server_bootstrap $VPNIP" >> $logpath &)

env | sort >> $logpath

exit 0
