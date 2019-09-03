#!/bin/bash

CB_PUBKEY_SOURCE=$1
CB_USERNAME=$2

pushd $CB_PUBKEY_SOURCE/credentials >/dev/null 2>&1

for pk in $(ls *.pub)
do
    CB_PK=$(cat $pk)
    for usr in /home/$CB_USERNAME /root
    do
    	echo "Checking injected keys for user $usr"
        sudo grep "$CB_PK" $usr/.ssh/authorized_keys >/dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            sudo bash -c "echo \"$CB_PK\" >> $usr/.ssh/authorized_keys" 
        fi
    done
done

popd

exit 0