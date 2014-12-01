#!/usr/bin/env bash

# This script is a self-contained complete
# openvpn key generator so that CloudBench
# users do not need "understand" anything
# about openvpn. They should assume that openvpn
# in the cloud "just works" without having to
# fiddle around with key generation. It important
# not to include these keys in the main source code,
# thus they need to be generated on the fly and
# also on a per-cloud basis.

if [ $0 != "-bash" ] ; then
	pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
	popd 2>&1 > /dev/null
fi

if [ x"$1" == x ] || [ x"$2" == x ] ; then
    echo "Need OpenVPN server address range. Example ./make_keys.sh 10.5.0.0 255.255.0.0 cloud-name [public routable address of bootstrap server]"
    exit 1
fi

network=$1
mask=$2
shift
shift

if [ x"$1" == x ] ; then
    echo "Need cloud name."
    exit 1
fi

cloud=$1
shift

if [ x"$1" == x ] ; then
    echo "Need public IP address where external cloud clients connect."
    exit 1
fi
publicip=$1
shift

pushd $dir

path=$dir/../../configs
client=client-cb-openvpn-$cloud.conf
server=server-cb-openvpn-$cloud.conf
mongo=mongo-cb-openvpn-$cloud.conf
cbpath=$(echo "$dir/../.." | sed -e "s/\(\/\)/(\\\)\1/g" | sed -e "s/\((\|)\)//g")

cp client.conf.template $path/$client
cat client.conf.template | grep -v "cb_vm_ready.sh" > $path/$mongo
cp server.conf.template $path/$server 

sed -ie "s/ADDRESS_RANGE/$network $mask/g" $path/$server
sed -ie "s/DESTINATION/$publicip/g" $path/$mongo

cd easy-rsa
source vars
./clean-all 
./build-dh 
./pkitool --initca
./pkitool --server server
KEY_CN=client ./pkitool client
cd keys
openvpn --genkey --secret ta.key

for file in $server $client $mongo ; do 
    echo "<ca>" >> $path/$file
    cat ca.crt >> $path/$file
    echo "</ca>" >> $path/$file

    echo "<tls-auth>" >> $path/$file
    cat ta.key >> $path/$file
    echo "</tls-auth>" >> $path/$file
done

for file in $client $mongo ; do
    echo "<cert>" >> $path/$file
    cat client.crt >> $path/$file
    echo "</cert>" >> $path/$file
    echo "<key>" >> $path/$file
    cat client.key >> $path/$file
    echo "</key>" >> $path/$file
done

echo "<cert>" >> $path/$server
cat server.crt >> $path/$server
echo "</cert>" >> $path/$server
echo "<key>" >> $path/$server
cat server.key >> $path/$server
echo "</key>" >> $path/$server

echo "<dh>" >> $path/$server
cat dh1024.pem >> $path/$server
echo "</dh>" >> $path/$server

sed -ie "s/CBPATH/$cbpath/g" $path/$server 

rm -f $path/${server}e
rm -f $path/${mongo}e

popd
