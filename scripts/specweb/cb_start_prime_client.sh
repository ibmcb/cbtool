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

# Copyright (c) 2009 Standard Performance Evaluation Corporation (SPEC)
#               All rights reserved.
# 
# This source code is provided as is, without any express or implied warranty.
#

cd ~/specweb2009/Prime_Client
#JAVA=specweb2009/ibm-java-i386-60/bin/java
JAVA=~/jre1.6.0_20/bin/java
MEM=128

# start SPECweb2009 prime client
$JAVA $1 -Xmx${MEM}m -classpath .:lib/jcommon-1.0.15.jar:lib/jfreechart-1.0.12.jar:bin/specweb.jar specweb

if [ $? -gt 0 ] ; then
	echo "problem running specweb prime client on $(hostname)"
	exit 1
fi
