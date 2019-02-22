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
	JAVA_HOME=/usr/lib/jvm/$(ls -t /usr/lib/jvm | grep java | sed '/^$/d' | $GREP_JAVA_VERSION | sort -r | head -n 1)/jre
elif [[ $JAVA_VENDOR == "ibm" ]]
then
	JAVA_HOME=$(sudo find /opt/ibm/ | grep jre/bin/javaws | sed 's^/bin/javaws^^g' | $GREP_JAVA_VERSION | sort -r | head -n 1)
else
	JAVA_HOME=$(sudo find $JAVA_VENDOR | grep jre/bin/javaws | sed 's^/bin/javaws^^g' | $GREP_JAVA_VERSION | sort -r | head -n 1)	
fi

if [[ -d $JAVA_HOME ]]
then
	echo "$JAVA_VERSION"
    exit 0    
else
	echo "0"
	exit 1
fi