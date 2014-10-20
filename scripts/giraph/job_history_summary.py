#!/usr/bin/env python

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

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import sys
import csv

pat = re.compile('(?P<name>[^=]+)="(?P<value>[^"]*)" *')
counterPat = re.compile('(?P<name>[^:]+):(?P<value>[^,]*),?')

def parse(tail):
    result = {}
    for n,v in re.findall(pat, tail):
        result[n] = v
    return result

mapStartTime = {}
mapEndTime = {}
reduceStartTime = {}
reduceShuffleTime = {}
reduceSortTime = {}
reduceEndTime = {}
reduceBytes = {}
#added
hostName = {}
taskStatus = {}
jobId = None
jobName = None
jobSubmitTimeAbs = None
jobLaunchTimeAbs = None
jobFinishTimeAbs = None
jobStatus = None

isReduceStarted = 0
isReduceFinished = 0


for line in sys.stdin:
  words = line.split(" ",1)
  event = words[0]
  attrs = parse(words[1])
  if event == 'MapAttempt':
    if attrs.has_key("START_TIME"):
      mapStartTime[attrs["TASKID"]] = int(attrs["START_TIME"])/1000
    elif attrs.has_key("FINISH_TIME"):
      taskStatus[attrs["TASKID"]] = attrs["TASK_STATUS"]
      if taskStatus[attrs["TASKID"]] == "SUCCESS": 
        mapEndTime[attrs["TASKID"]] = int(attrs["FINISH_TIME"])/1000
        if attrs.has_key("HOSTNAME"):    
          hostName[attrs["TASKID"]] = attrs["HOSTNAME"]
  elif event == 'ReduceAttempt':
    if attrs.has_key("START_TIME"):
      isReduceStarted = 1;
      reduceStartTime[attrs["TASKID"]] = int(attrs["START_TIME"]) / 1000
    elif attrs.has_key("FINISH_TIME"):
      isReduceFinished = 1;
      taskStatus[attrs["TASKID"]] = attrs["TASK_STATUS"]
      if taskStatus[attrs["TASKID"]] == "SUCCESS": 
        reduceShuffleTime[attrs["TASKID"]] = int(attrs["SHUFFLE_FINISHED"])/1000
        reduceSortTime[attrs["TASKID"]] = int(attrs["SORT_FINISHED"])/1000
        reduceEndTime[attrs["TASKID"]] = int(attrs["FINISH_TIME"])/1000
        hostName[attrs["TASKID"]] = attrs["HOSTNAME"]
  elif event == 'Task':
    if attrs["TASK_TYPE"] == "REDUCE" and attrs.has_key("COUNTERS"):
      for n,v in re.findall(counterPat, attrs["COUNTERS"]):
        if n == "File Systems.HDFS bytes written":
          reduceBytes[attrs["TASKID"]] = int(v)
  elif event == 'Job':
    if attrs.has_key("JOBID"):
      jobId = attrs["JOBID"]
    if attrs.has_key("JOBNAME"):
      jobName = attrs["JOBNAME"]
    if attrs.has_key("SUBMIT_TIME"):
      jobSubmitTimeAbs = int(attrs["SUBMIT_TIME"]) 
    if attrs.has_key("LAUNCH_TIME"):
      jobLaunchTimeAbs = int(attrs["LAUNCH_TIME"]) 
    if attrs.has_key("FINISH_TIME"):
      jobFinishTimeAbs = int(attrs["FINISH_TIME"]) 
    if attrs.has_key("JOB_STATUS"):
      jobStatus = attrs["JOB_STATUS"]  

if isReduceStarted == 1 : 
    startTime = reduce(min, reduceStartTime.values()) 
else : 
    startTime = reduce(min,mapStartTime.values()) 
startTime = min(reduce(min, mapStartTime.values()), startTime )

if isReduceFinished == 1 : 
    endTime =  reduce(max, reduceEndTime.values())
else : 
    endTime = reduce(max, mapEndTime.values()) 
endTime = max(reduce(max, mapEndTime.values()), endTime)

jobSubmitTime = jobSubmitTimeAbs/1000
jobFinishTime = jobFinishTimeAbs/1000

print "mrlatency ", endTime - startTime #latency of map/reduce only
print "totlatency ", jobFinishTime - jobSubmitTime #including all setup times
