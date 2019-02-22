#!/usr/bin/env bash

if [[ ! -z $1 ]]
then
	GREP_HADOOP_VERSION="grep \-$1"
else
	GREP_HADOOP_VERSION="grep -v dddddddddddddd"
fi

for HADOOP_CPATH in ~ /home/cbuser /usr/local
do
    if [[ $(sudo ls $HADOOP_CPATH | $GREP_HADOOP_VERSION | grep -v tar | grep -v tgz | grep -v spark | grep -c hadoop) -ne 0 ]]
    then
        eval HADOOP_CPATH=${HADOOP_CPATH}
        HADOOP_HOME=$(ls ${HADOOP_CPATH} | grep -v tar | grep -v tgz | grep -v spark | grep -v hadoop_store | grep hadoop | sort -r | head -n1)
        eval HADOOP_HOME=$HADOOP_CPATH/${HADOOP_HOME}
        if [[ -d $HADOOP_HOME ]]
        then
            echo "1"
            exit 0
        fi
    fi
done
echo "0"
exit 1