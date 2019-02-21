#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi

CBRSYNC_BASE_DIR=$(pwd)

if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

if [[ $(echo $CBRSYNC_BASE_DIR | rev | cut -d '/' -f 1 | rev) == "util" ]]
then
    CBRSYNC_BASE_DIR=$(echo $CBRSYNC_BASE_DIR | sed 's/util//g')
fi

CBRSYNC_REMOTE_DIR=$(echo $CBRSYNC_BASE_DIR | sed "s^$HOME^^g")

if [[ -z $1 ]] 
then
    echo "Usage $CBRSYNC_BASE_DIR/cbrsync.sh <DESTINATION IP> [build|run]"
    exit 1
fi

CBRSYNC_ADDITIONAL_EXCLUDE="--exclude 3rd_party/workload/"
if [[ ! -z $2 ]]
then
    if [[ $2 == "build" ]]
    then
        CBRSYNC_ADDITIONAL_EXCLUDE=""
    fi
fi
CBRSYNC_TARGETS=$(echo $1 | sed 's/,/ /g')

for CBRSYNC_TARGET in $CBRSYNC_TARGETS
do

    echo "## Checking the ability to passwordless SSH into ${CBRSYNC_TARGET}"
    ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${CBRSYNC_TARGET} "/bin/true" > /dev/null 2>&1

    if [[ $? -ne 0 ]]
    then
        echo "Unable to passwordless SSH into ${CBRSYNC_TARGET}"
        exit 1
    fi

    ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${CBRSYNC_TARGET} "mkdir -p ~/$CBRSYNC_REMOTE_DIR/" > /dev/null 2>&1
    rsync -avzP $CBRSYNC_ADDITIONAL_EXCLUDE --exclude .git/ --exclude old_data/ --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/ $CBRSYNC_BASE_DIR/ ${CBRSYNC_TARGET}:~/$CBRSYNC_REMOTE_DIR
done
