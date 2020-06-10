#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

cd ~
dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
if [ -e $dir/cb_common.sh ] ; then
	source $dir/cb_common.sh
else
	source $dir/../common/cb_common.sh
fi

# This is the JBalloon controller script for WAS 
# It runs in the guest and monitors the amount of memory currently assigned to the VM
# and keeps the amount of memory reserved for the guest OS constant. For example
# if the VM was assigned with 2.0GB, the java heap size is 1.5GB and the
# amount of reserved mem for the OS should be 0.5GB, each time the 
# balloon inflates by X MB, the JBalloon will be inflated by X MB

usage () {
 syslog_netcat "usage: jballoon_controller [max jvm heap (MB)] [range between jvm heap and vm mem (MB)] [check delay (ms)]"
 exit 1
}

set_jballoon() {
 size=$1
 wget --timeout=10 http://localhost:9080/JBalloonWAR/setSize?sizeMB=$size -O /dev/null -o /dev/null        
}

if [ x"$1" != x ] ; then
    maxheap=$1
    shift
else
    usage
fi

if [ x"$1" != x ] ; then
    range=$1
    shift
else
    usage
fi

if [ x"$1" != x ] ; then
    checkdelay=$1
else
    usage
fi

prev_size=0
while [ true ] ; do

 result="$(ps -ef | grep WebSphere | grep -v grep)"
 if [ x"$result" == x ] ; then        
	 $dir/cb_restart_was.sh
 fi

 mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`

 # calculate in KB
 ((new_size=$maxheap*1024+$range*1024-$mem))

 # convert to MB
 ((new_size=new_size/1024))

 if [ $new_size -le 0 ] ; then
  syslog_netcat "Capping $new_size to zero"
  new_size=0
 fi

 if [ $prev_size != $new_size ] ; then
	if [ $new_size -gt $prev_size ] ; then
		 ((diff=new_size - prev_size))
		 if [ $diff -gt 25 ] ; then
			 ((new_size = prev_size + 25))
			 syslog_netcat "Throttling size to $new_size"
		 fi
	fi
  	syslog_netcat "Setting JBalloon to $new_size"
	exit 1
  	set_jballoon $new_size
  	prev_size=$new_size
 else
	 syslog_netcat "prev $prev_size new $new_size"
 fi

 sleep $checkdelay

done

