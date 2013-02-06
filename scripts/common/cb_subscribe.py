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

import os
import fnmatch

if len(argv) != 3 :
    print "Usage: cb_barrier.py <channel> <message>"
    exit(2)

_channel = argv[1]
_message = argv[2]

_home = os.environ["HOME"]

for _path, _dirs, _files in os.walk(os.path.abspath(_home)):
    for _filename in fnmatch.filter(_files, "code_instrumentation.py") :
        path.append(_path.replace("/lib/auxiliary",''))
        break

from scripts.common.cb_common import get_os_conn, get_ms_conn, get_my_ip, get_uuid_from_ip, report_app_metrics

_osci, _cn = get_os_conn()

_sub_channel = _osci.subscribe(_cn, "VM", _channel)

print "Subscribed to channel \"" + _channel + "\""
for message in _sub_channel.listen() :
    if isinstance(message["data"], str) :
        if message["data"].count(_channel) :
            _sub_channel.unsubscribe()
            exit(0)