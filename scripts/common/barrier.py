#!/usr/bin/env python3

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

import redis
import sys
if len(sys.argv) != 6 :
    print("Usage: barrier.py <host> <port> <db> <channel> <message>")
    exit(2)

redis_conn = redis.Redis(host=sys.argv[1], port=int(sys.argv[2]), db=int(sys.argv[3]), decode_responses=True)
redis_conn_pubsub = redis_conn.pubsub()
redis_conn_pubsub.subscribe(sys.argv[4])
print("Subscribed to channel \"" + sys.argv[4] + "\"")
for message in redis_conn_pubsub.listen() :
    if isinstance(message["data"], str) :
        if message["data"].count(sys.argv[5]) :
            exit(0)
