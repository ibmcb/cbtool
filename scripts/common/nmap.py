#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2015 DigitalOcean, inc. 

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

'''
    Created on Oct 31st, 2015

    @author: Michael R. Hines
'''

import socket
import struct
import IN
import sys
from subprocess import PIPE,Popen
from platform import system
from socket import gethostbyname, gethostbyaddr
from fcntl import ioctl

class Nethashget :
    def __init__(self, hostname, port = None) :
        self.hostname = hostname

        if self.hostname.count('@') :
            self.hostname = self.hostname.split('@')[1]

        if port :
            self.port = int(port)
        else :
            self.port = None
        self.socket = None
        
    def connect(self) :
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, int(self.port)))

    def path_mtu_discover(self, port = False) :
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.hostname, (port if port else (self.port if self.port is not None else 9999))))
        self.socket.setsockopt(socket.IPPROTO_IP, IN.IP_MTU_DISCOVER, IN.IP_PMTUDISC_DO)
        return self.socket.getsockopt(socket.IPPROTO_IP, getattr(IN, 'IP_MTU', 14))

    def nmap(self, port = None, protocol = "TCP", reverse = False) :
        try :
            if protocol.lower() == "tcp" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif protocol.lower() == "udp" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5)
            self.socket.connect((self.hostname, self.port if port is None else port))

            if not reverse :
                return True
            else :
                _msg = protocol + " port " + str(port) + " on host " 
                _msg += self.hostname + " is NOT free"
                print(_msg)
                return False

        except socket.error, msg :
            if not reverse :
                _msg = "Unable to connect to " + protocol + " port " + str(port)
                _msg += " on host " + self.hostname + ": " + str(msg)
                print(_msg)
                return False
            else :
                _msg = protocol + " port " + str(port) + " on host " 
                _msg += self.hostname + ": " + str(msg) + "is free"
                print(_msg)
                return True

            self.socket.close()
            self.socket = None

nm = Nethashget(sys.argv[1], sys.argv[2])
if nm.nmap(protocol = sys.argv[3]) :
    print "open"
    exit(0)
else :
    print "closed"
    exit(1)
