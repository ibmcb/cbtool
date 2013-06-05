#!/usr/bin/env bash

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")

if [ x"$1" == x ] ; then
    echo "need remote cloudbench identifier"
    exit 1
fi
id=$1
shift
echo "Using cloudbench identifier: $id"

if [ x"$1" == x ] ; then
    echo "missing remote username to login with"
	exit 1
fi

user=$1
shift
echo "remote username: $user"

if [ x"$1" == x ] ; then
    echo "missing path to python program to remote debug"
	exit 1
fi

path=$@
shift

program=$(echo "$path" | sed -e "s/.*\///g")

echo "debugging program: $program"


host=$($dir/../cb vmshow $id | grep "|cloud_ip" | sed -e "s/|//g" | sed -e "s/ \+/ /g" | cut -d " " -f 2)
if [ $? -gt 0 ] ; then
    echo "failed to retrieve IP address for cloudbench identifier: $id"
    exit 1
fi

echo "cloudbench ID: $id => $host"

DEST=$host
pkill -9 -f lsync.config.$DEST
pkill -9 -f lsync.config.p$DEST

echo "$DEST" > ~/lsync/debug.remote_host
cp ~/lsync/lsync.config.orig.klabuser ~/lsync/lsync.config.$DEST
sed -ie "s/DESTINATION/$DEST/g" ~/lsync/lsync.config.$DEST
lsyncd -nodaemon -delay 0 ~/lsync/lsync.config.$DEST &
cp ~/lsync/lsync.config.orig.pydev ~/lsync/lsync.config.p$DEST
sed -ie "s/DESTINATION/$DEST/g" ~/lsync/lsync.config.p$DEST
lsyncd -nodaemon -delay 0 ~/lsync/lsync.config.p$DEST &
sleep 2

ssh -o StrictHostKeyChecking=no -t -t $user@$host "for pid in \$(pgrep -f \"$program\") ; do if [ \$pid == \$\$ ] ; then echo skipping \$pid; continue; fi; if [ \$PPID == \$pid ] ; then echo skipping parent ssh process \$pid; continue; fi; echo killing process pid \$pid; kill -9 \$pid; done"

me=$(whoami)

ssh -o StrictHostKeyChecking=no -t -t $user@$host "if [ ! -e /home/$me ] ; then sudo mkdir /home/$me; fi; sudo mv -f /home/$me/cbtool /home/$me/cbtool.bak; sudo ln -sf ~/.metadata /home/$me/.metadata; sudo ln -sf ~/cbtool /home/$me/cbtool; ln -sf ~/cbtool/lib/debug/debug.michael.py ~/cbtool/debug.py"

scp -qr $dir/pydevd $user@$host:cbtool/util/
scp -qr $dir/ftc.py $user@$host:cbtool/util/
command="$path $@ -d 127.0.0.1 2>&1"
echo "running: $command"
ssh -i $dir/../credentials/klab_id_rsa -R 5678:127.0.0.1:5678 -X -o StrictHostKeyChecking=no -t -t $user@$host $command
ssh -i $dir/../credentials/klab_id_rsa -R 5678:127.0.0.1:5678 -X -o StrictHostKeyChecking=no -t -t $user@$host bash -x -c "ps -ef | grep cbact | grep -v grep"
