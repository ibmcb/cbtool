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

# This is the JBalloon controller script for WAS 
# It runs in the guest and monitors the amount of memory currently assigned to the VM
# and keeps the amount of memory reserved for the guest OS constant. For example
# if the VM was assigned with 2.0GB, the java heap size is 1.5GB and the
# amount of reserved mem for the OS should be 0.5GB, each time the 
# balloon inflates by X MB, the JBalloon will be inflated by X MB

usage () {
 echo "usage: jballoon_controller [max jvm heap (MB)] [range between jvm heap and vm mem (MB)] [check delay (ms)]"
 exit 1
}

set_jballoon() {
 size=$1
 wget http://localhost:9080/JBalloonWAR/setSize?sizeMB=$size -O /dev/null -o /dev/null        
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
 mem=`cat /proc/meminfo | sed -n 's/MemTotal:[ ]*\([0-9]*\) kB.*/\1/p'`
 # calculate in KB
 ((new_size=$maxheap*1024+$range*1024-$mem))
 # convert to MB
 ((new_size=new_size/1024))

 if [ $new_size -le 0 ] ; then
  new_size=0
 fi

 if [ $prev_size != $new_size ] ; then
  echo Setting JBalloon to $new_size
  set_jballoon $new_size
  prev_size=$new_size
 fi

 sleep $checkdelay

done

