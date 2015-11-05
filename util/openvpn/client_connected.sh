#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

logpath=/var/log/cloudbench/$USER_openvpn_client.log

echo "client connected $(date) params: $@" >> $logpath

env | sort >> $logpath

exit 0
