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

"""
    Library functions periodically making measurements of
    multi-tier servers over the network

    @author: Michael R. Hines, Marcio A. Silva

"""

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from time import time, sleep
from os import getuid, environ
import socket
import sys
from sys import path
import et.ElementTree as ET
import re
import urllib
from subprocess import Popen, PIPE, STDOUT

class NetworkException(Exception) :
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
        
class Nethashget :
    '''
    TBD
    '''
    def __init__(self, hostname, port = None) :
        self.hostname = hostname
        if port :
            self.port = int(port)
        else :
            self.port = None
        self.socket = None

    def connect(self) :
        '''
        TBD
        '''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, int(self.port)))

    def nmap(self, port = None, protocol = "TCP") :
        '''
        TBD
        '''
        try :
            if protocol == "TCP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif protocol == "UDP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5)
            self.socket.connect((self.hostname, self.port if port is None else port))
            return True
        
        except socket.error, msg :
            _msg = "Unable to connect to " + protocol + " port " + str(port)
            _msg += " on host " + self.hostname + ": " + str(msg)
            print(_msg)
            raise NetworkException(str(_msg), "1")
            self.socket.close()
            self.socket = None

    def check_port(self, port = None, protocol = "TCP") :
        '''
        TBD
        '''
        try :
            if protocol == "TCP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif protocol == "UDP" :
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5)
            self.socket.connect((self.hostname, self.port if port is None else port))
            return True
        
        except socket.error, msg :
            _msg = "Unable to connect to " + protocol + " port " + str(port)
            _msg += " on host " + self.hostname + ": " + str(msg)
            print(_msg)
            return False
            self.socket.close()
            self.socket = None

def nmap(port) :
    '''
    TBD
    '''
    if len(sys.argv) < 3 :
        print ("Need ip address and collection frequency")
        exit(1)
        
    app = Nethashget(sys.argv[2])

    _msg = "Application on " + sys.argv[2] + ":" + str(port) + " is not available"
    
    try : 
        if app.nmap(port) is False :
            print(_msg)
            exit(1)
    except NetworkException, msg :
        print(_msg)
        exit(1)
    return sys.argv[1], sys.argv[2]

def get_os_conn() :
    '''
    TBD
    '''
    try :
        _fmsg = ""
        _home = environ["HOME"]        
        _from_file = False
        _fn = _home + "/cb_os_parameters.txt"
        _fh = open(_fn, "r")
        _fc = _fh.readlines()
        _fh.close()

        os_params = {}
        for _line in _fc :
            _line = _line.strip()
            if _line.count("#OSKN-") :
                os_params["kind"] = _line[6:]
            elif _line.count("#OSHN-") :
                os_params["hostname"] = _line[6:]
            elif _line.count("#OSPN-") :
                os_params["port"] = _line[6:]
            elif _line.count("#OSDN-") :
                os_params["database"] = _line[6:]
            elif _line.count("#OSTO-") :
                os_params["timeout"] = _line[6:]
            elif _line.count("#OSCN-") :
                os_params["cloud_name"] = _line[6:]
            elif _line.count("#OSOI-") :
                os_params["instance"] = _line[6:]
            else :
                True

        if "instance" in os_params :
            os_params["processid"] = os_params["instance"].split(':')[0]

        _os_adapter = __import__("stores." + os_params["kind"] + "_datastore_adapter", \
                                 fromlist=[os_params["kind"].capitalize() + "MgdConn"])

        _os_conn_class = getattr(_os_adapter, os_params["kind"].capitalize() + "MgdConn")
        
        _osci = _os_conn_class(os_params["processid"], \
                               os_params["hostname"], \
                               int(os_params["port"]), \
                               int(os_params["database"]), \
                               float(os_params["timeout"]), \
                               os_params["instance"])
        
        _status = 0

    except IOError, msg :
        _status = 10
        _fmsg = str(msg) 
    
    except OSError, msg :
        _status = 20
        _fmsg = str(msg) 

        
    except ImportError, msg :
        _status = 20
        _fmsg = str(msg)

    except AttributeError, msg :
        _status = 20
        _fmsg = str(msg)
    
    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "Failure while setting up object store adapter: " + _fmsg
            print _msg
            exit(2)
        else :
            _msg = "Object store adapter set up successfully."
            return _os_conn_class
            
def verify_and_send(role, rate, latency) :
    #if rate + latency <= 0 :
    #    exit(1)

    script = "~/cb_report_metric.sh "
    Popen(script + " latency " + str(latency) + " int32 millisec 0 " + role, shell=True)
    Popen(script + " throughput " + str(rate) + " int32 tps 0 " + role, shell=True)
    sleep(1)

def wget(url) :
    '''
    TBD
    '''
    try :
        handle = urllib.urlopen(url)
        if handle is None :
            print("Url " + url + " seems unavailable")
            return None
        tree = ET.parse(handle)
        if tree is None :
            print("Tree could not be built from : " + url)
            return None
        return tree
    except Exception, msg :
        print(str(msg))
        return None

def collect_db_one(command) :
    '''
    TBD
    '''
    p = Popen(command, shell=True, stdout=PIPE)
    output = None 
    err = ""
    for line in p.stdout :
        if "Transactions" in line :
            output = line
        err += line    
    p.wait()
    if output is None :
        print("ERROR collecting from database: \n" + err)
        return 0

    result = re.compile('.*Transactions: ([0-9]+)').match(output)
    return int(result.group(1))

def collect_db(role, dbtype, port, auth, query) :
    '''
    TBD
    '''
    delay, ip = nmap(port) 
    rate = 0
    latency = 0
    
    command = "java -Xmx10m -Xms10m -jar ~/sdc.jar " \
        + dbtype + " " + ip + " " + str(port) + " " + auth + " \"" + query + "\""
    
    count1 = collect_db_one(command)
    time1 = time()
    sleep(float(10))
    count2 = collect_db_one(command)
    time2 = time()
    
    if count1 > 0 and count2 > 0 and count2 > count1:
        count = count2 - count1
        secs = time2 - time1
        rate = int(count / secs)
        latency = 0
    verify_and_send(role, rate, latency)

def collect_apache(role, grep) :
    '''
    TBD
    '''
    delay, ip = nmap(80)
    rate = 0
    latency = 0
    url = "http://" + ip + "/tm?" + grep
    print("Requesting URL: " + url)

    handle = urllib.urlopen(url)

    if handle is None :
        print("Url " + url + " seems unavailable")
        return (0, 0)

    for line in handle.readlines() :
        if "AVERAGE" in line :
            latency = int(re.compile('.*<td>([0-9]+)').match(line).group(1))
            continue
        if "HITS" in line :
            rate = int(re.compile('.*<td>([0-9]+)').match(line).group(1))
            rate /= int(delay)
            continue
        
    urllib.urlopen("http://" + ip + "/tm?reset").read()
    verify_and_send(role, rate, latency)

def et_find(path, tree) :
    '''
    TBD
    '''
    elems = tree.find(path)
    if elems is None :
        print("path " + path + " not found")
    return elems

def collect_was(role, port, ejb_name) :
    '''
    TBD
    '''
    delay, ip = nmap(port)
    rate = 0
    latency = 0
    
    path= "Node/Server/Stat/Stat[@name='" + ejb_name + "']"
    url = "http://" + ip + ":" + str(port) + "/wasPerfTool/servlet/perfservlet?module=beanModule"
    tree1 = wget(url)
    if tree1 is None : return (0, 0)
    sleep(5)
    tree2 = wget(url)
    if tree2 is None : return (0, 0)

    countpath = path + "/CountStatistic[@ID='11']"
    totalpath = path + "/TimeStatistic[@ID='12']"

    count1 = et_find(countpath, tree1)
    total1 = et_find(totalpath, tree1)
    count2 = et_find(countpath, tree2)
    total2 = et_find(totalpath, tree2)

    if count1 is None or count2 is None or total1 is None or total2 is None: 
        return (0, 0)
    
    count = int(count2.attrib['count']) - int(count1.attrib['count'])

    if count > 0 :
        total = int(total2.attrib['totalTime']) - int(total1.attrib['totalTime'])
        if total > 0 :
            latency = total / count
            rate = count / 5 

    verify_and_send(role, rate, latency)