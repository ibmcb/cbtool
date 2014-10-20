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

from sys import argv, path
from subprocess import PIPE,Popen

import re
import os
import fnmatch

_home = os.environ["HOME"]

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from scripts.common.cb_common import get_my_ip, get_uuid_from_ip, report_app_metrics

pat = re.compile('(?P<name>[^=]+)="(?P<value>[^"]*)" *')
counterPat = re.compile('(?P<name>[^:]+):(?P<value>[^,]*),?')

def parse(tail) :
    result = {}
    for n,v in re.findall(pat, tail):
        result[n] = v
    return result

def file_list(hadoop_bin, location) :
    _cmd = hadoop_bin + " fs -ls " + location   
    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (_output_stdout, _output_stderr) = proc_h.communicate()
    
    if proc_h.returncode > 0 :
        _msg = "Hadoop log file listing failed: " + _output_stderr
#        print _msg
#        exit(1)
        return False
    else :
        for _file in _output_stdout.split('\n') :
            if _file.count(location) and not _file.count("xml") :
                return _file.split()[-1]
    return False

def read_file(hadoop_bin, filenam) :
    _cmd = hadoop_bin + " fs -text " + filenam   
    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output_stdout, output_stderr) = proc_h.communicate()
    
    if proc_h.returncode > 0 :
        _msg = "Hadoop log file extraction failed: " + output_stderr
#        print _msg
#        exit(1)
        return False
    else :
        return output_stdout.split('\n')[0:-1]
    
def parsefile(file_contents) :
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
    
    for line in file_contents :
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
    
    jobSubmitTime = jobSubmitTimeAbs/1
    jobFinishTime = jobFinishTimeAbs/1

    _mrlatency = (endTime - startTime) * 1000 #latency of map/reduce only
    _totlatency = jobFinishTime - jobSubmitTime #including all setup times
    
    return _mrlatency, _totlatency

def main() :
    
    _mr_latency = False
    _hadoop_log_file_name = file_list(argv[1], argv[2])
    if _hadoop_log_file_name :
        _hadoop_file_contents = read_file(argv[1], _hadoop_log_file_name)
        if _hadoop_file_contents :
            _mr_latency, _totlatency = parsefile(_hadoop_file_contents)

    _my_ip = get_my_ip()

    _my_uuid = get_uuid_from_ip(_my_ip)
    
    _metric_list = ''
    
    for _arg in argv :
        if _arg.count(":") == 2 :
            _metric_list += _arg + ' '
    
    if _mr_latency:
        _metric_list += "latency:" + str(_totlatency) + ":msec latency_mr:" + str(_mr_latency) + ":msec"

    report_app_metrics(_my_uuid, _metric_list)

main()