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

CBRSYNC_REMOTE_DIR=$(echo $CBRSYNC_BASE_DIR | sed "s^$HOME^^g" | sed "s^host^repos^g")

if [[ -z $1 ]] 
then
    echo "Usage: $CBRSYNC_BASE_DIR/util/cbrsync.sh <DESTINATION IP> [user] [build|run]"
    exit 1
fi

CBRSYNC_USER=
if [[ ! -z $2 ]]
then
    CBRSYNC_USER=${2}@
fi

CBRSYNC_ADDITIONAL_EXCLUDE="--exclude 3rd_party/workload/"
if [[ ! -z $3 ]]
then
    if [[ $3 == "build" ]]
    then
        CBRSYNC_ADDITIONAL_EXCLUDE=""
    fi
fi
CBRSYNC_TARGETS=$(echo $1 | sed 's/,/ /g')

for CBRSYNC_TARGET in $CBRSYNC_TARGETS
do

    echo "## Checking the ability to passwordless SSH into ${CBRSYNC_USER}${CBRSYNC_TARGET}" 
    ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${CBRSYNC_USER}${CBRSYNC_TARGET} "/bin/true" > /dev/null 2>&1

    if [[ $? -ne 0 ]]
    then
        echo "Unable to passwordless SSH into ${CBRSYNC_TARGET}"
        exit 1
    fi

    ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${CBRSYNC_USER}${CBRSYNC_TARGET} "mkdir -p ~/$CBRSYNC_REMOTE_DIR/" > /dev/null 2>&1
    rsync -az $CBRSYNC_ADDITIONAL_EXCLUDE --exclude *.pyc --exclude .git/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude .cb_history --include=lib/stores/ --exclude stores/ --exclude jar/ --exclude windows/ $CBRSYNC_BASE_DIR/ ${CBRSYNC_USER}${CBRSYNC_TARGET}:~/$CBRSYNC_REMOTE_DIR/
	if [[ $? -eq 0 ]]
	then
    	echo "## CB code successfully updated on ${CBRSYNC_USER}${CBRSYNC_TARGET}:~/$CBRSYNC_REMOTE_DIR/" 
	fi
done
exit 0