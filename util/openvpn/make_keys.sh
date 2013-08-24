#!/usr/bin/env bash
if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

pushd $dir

cp client.conf.template client.conf
cp server.conf.template server.conf 
cd easy-rsa
source vars
./clean-all 
./build-dh 
./pkitool --initca
./pkitool --server server
KEY_CN=client ./pkitool client
cd keys
openvpn --genkey --secret ta.key

echo "<ca>" >> $dir/server.conf
echo "<ca>" >> $dir/client.conf
cat ca.crt >> $dir/client.conf
cat ca.crt >> $dir/server.conf
echo "</ca>" >> $dir/client.conf
echo "</ca>" >> $dir/server.conf

echo "<tls-auth>" >> $dir/client.conf
echo "<tls-auth>" >> $dir/server.conf
cat ta.key >> $dir/client.conf
cat ta.key >> $dir/server.conf
echo "</tls-auth>" >> $dir/server.conf
echo "</tls-auth>" >> $dir/client.conf

echo "<cert>" >> $dir/server.conf
echo "<cert>" >> $dir/client.conf
cat client.crt >> $dir/client.conf
cat server.crt >> $dir/server.conf
echo "</cert>" >> $dir/server.conf
echo "</cert>" >> $dir/client.conf

echo "<key>" >> $dir/server.conf
echo "<key>" >> $dir/client.conf
cat client.key >> $dir/client.conf
cat server.key >> $dir/server.conf
echo "</key>" >> $dir/server.conf
echo "</key>" >> $dir/client.conf

echo "<dh>" >> $dir/server.conf
cat dh1024.pem >> $dir/server.conf
echo "</dh>" >> $dir/server.conf

popd
