#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2009 Standard Performance Evaluation Corporation (SPEC)
#               All rights reserved.
#
# This source code is provided as is, without any express or implied warranty.
#
# cb_restart_ycsb.sh -
#
#
# @author Joe Talerico, jtaleric@redhat.com
#/*******************************************************************************

source ~/.bashrc
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

standalone=`online_or_offline "$1"`

if [ $standalone == offline ] ; then
	post_boot_steps offline 
fi

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

mongo=`get_ips_from_role mongodb`
pos=1
sudo sh -c "echo 127.0.0.1 localhost > /etc/hosts"
for db in $mongo
do
	sudo sh -c "echo $db mongo$pos mongodb-$pos >> /etc/hosts"
	(pos++)
done

provision_application_stop $START
