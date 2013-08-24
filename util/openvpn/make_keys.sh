#!/usr/bin/env bash
if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

pushd $dir

cd easy-rsa
source vars
./clean-all 
./build-dh 
./pkitool --initca
./pkitool --server server
KEY_CN=client ./pkitool client
cd keys
openvpn --genkey --secret ta.key
cp server.crt server.key ca.crt dh1024.pem ta.key client.key client.crt $dir
popd
