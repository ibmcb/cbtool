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

from sys import argv, path
from time import sleep

import os
import fnmatch

if len(argv) < 4 :
    print "Usage: cb_barrier.py <objtype> <channel> <message>"
    exit(1)

_obj_type = argv[1]
_channel = argv[2]
_message = argv[3]

counter_name = False
counter_max = False

if len(argv) > 4 :
    counter_name = argv[4]
    counter_max = int(argv[5])

_home = os.environ["HOME"]

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from scripts.common.cb_common import get_os_conn, get_ms_conn, get_my_ip, get_uuid_from_ip, report_app_metrics

_osci, _uuid, _cn = get_os_conn()

lock = False
leader = False

if counter_name and counter_max :
    lock = _osci.acquire_lock(_cn, _obj_type, "barrier", counter_name, 1)
    counter = int(_osci.update_counter(_cn, _obj_type, counter_name, "increment"))
    if counter == counter_max :
        print "I am leader"
        leader = True
        _osci.update_counter(_cn, _obj_type, counter_name, "decrement")
        _osci.release_lock(_cn, _obj_type, "barrier", lock)
        _osci.publish_message(_cn, _obj_type, _channel, _message, 1, 5.0)
        sleep(1)
        while True :
            counter = int(_osci.get_counter(_cn, _obj_type, counter_name))
            if counter == 0 :
                break
            sleep(0.1)

        print "leader done."
        exit(0)
    print "I am follower"

_sub_channel = _osci.subscribe(_cn, _obj_type, _channel)

if counter_name and counter_max and lock :
    _osci.release_lock(_cn, _obj_type, "barrier", lock)

for message in _sub_channel.listen() :
    if isinstance(message["data"], str) :
        if message["data"].count(_message) :
            _sub_channel.unsubscribe()
            break

lock = False
if not leader :
    if counter_name and counter_max :
        lock = _osci.acquire_lock(_cn, _obj_type, "barrier", counter_name, 1)

    _osci.update_counter(_cn, _obj_type, counter_name, "decrement")

    if counter_name and counter_max and lock :
        _osci.release_lock(_cn, _obj_type, "barrier", lock)

    print "follower done"

exit(0)
