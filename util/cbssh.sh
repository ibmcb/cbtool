#!/usr/bin/env bash

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
user=klabuser

if [ x"$1" == x ] ; then
    echo "need remote cloudbench identifier"
    exit 1
fi
id=$1
host=$($dir/../cb vmshow $id | grep "|cloud_ip" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)
if [ $? -gt 0 ] ; then
    echo "failed to retrieve IP address for cloudbench identifier: $id"
    exit 1
fi

echo "logging in: cloudbench ID: $id => $host"

ssh -i $dir/../credentials/klab_id_rsa -R 5678:127.0.0.1:5678 -X -o StrictHostKeyChecking=no -t -t $user@$host
