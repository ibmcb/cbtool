#!/usr/bin/env bash

JAVA_VENDOR="openjdk"
if [[ ! -z $1 ]]
then
    JAVA_VENDOR=$1
fi

if [[ ! -z $2 ]]
then
    GREP_JAVA_VERSION="grep \-$2"
    JAVA_VERSION=$2
else
    GREP_JAVA_VERSION="grep -v dddddddddddddd"
    JAVA_VERSION=1
fi

if [[ $JAVA_VENDOR == "openjdk" ]]
then
    ls -t /usr/lib/jvm | grep java | sed '/^$/d' | $GREP_JAVA_VERSION > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        echo "ERROR"
        exit 1
    else
        JAVA_HOME=/usr/lib/jvm/$(ls -t /usr/lib/jvm | grep java | sed '/^$/d' | $GREP_JAVA_VERSION | sort -r | head -n 1)/jre
    fi
elif [[ $JAVA_VENDOR == "ibm" ]]
then
    JAVA_HOME=$(sudo find /opt/ibm/ | grep jre/bin/javaws | sed 's^/bin/javaws^^g' | $GREP_JAVA_VERSION | sort -r | head -n 1)
else
    JAVA_HOME=$(sudo find $JAVA_VENDOR | grep jre/bin/javaws | sed 's^/bin/javaws^^g' | $GREP_JAVA_VERSION | sort -r | head -n 1)    
fi

if [[ -d $JAVA_HOME ]]
then
    echo "$JAVA_HOME"
    exit 0    
else
    echo "ERROR"
    exit 1
fi