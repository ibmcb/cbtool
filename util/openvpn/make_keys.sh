#!/usr/bin/env bash
if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

pushd $dir

path=$dir/../../configs
client=client-cb-openvpn.conf
server=server-cb-openvpn.conf
cbpath=$(echo "$dir/../.." | sed -e "s/\(\/\)/(\\\)\1/g" | sed -e "s/\((\|)\)//g")

cp client.conf.template $path/$client
cp server.conf.template $path/$server 

cd easy-rsa
source vars
./clean-all 
./build-dh 
./pkitool --initca
./pkitool --server server
KEY_CN=client ./pkitool client
cd keys
openvpn --genkey --secret ta.key

echo "<ca>" >> $path/$server
echo "<ca>" >> $path/$client
cat ca.crt >> $path/$client
cat ca.crt >> $path/$server
echo "</ca>" >> $path/$client
echo "</ca>" >> $path/$server

echo "<tls-auth>" >> $path/$client
echo "<tls-auth>" >> $path/$server
cat ta.key >> $path/$client
cat ta.key >> $path/$server
echo "</tls-auth>" >> $path/$server
echo "</tls-auth>" >> $path/$client

echo "<cert>" >> $path/$server
echo "<cert>" >> $path/$client
cat client.crt >> $path/$client
cat server.crt >> $path/$server
echo "</cert>" >> $path/$server
echo "</cert>" >> $path/$client

echo "<key>" >> $path/$server
echo "<key>" >> $path/$client
cat client.key >> $path/$client
cat server.key >> $path/$server
echo "</key>" >> $path/$server
echo "</key>" >> $path/$client

echo "<dh>" >> $path/$server
cat dh1024.pem >> $path/$server
echo "</dh>" >> $path/$server

sed -ie "s/CBPATH/$cbpath/g" $path/$server 

popd
