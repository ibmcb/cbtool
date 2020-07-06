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

'''
    Created on Nov 15, 2011

    Network primitives for CloudBench

    @author: Michael R. Galaxy, Marcio A. Silva
'''

import socket
import struct
import urllib.request, urllib.error, urllib.parse

try :
    import IN
except :
    pass

from subprocess import PIPE,Popen
from platform import system
from socket import gethostbyname, gethostbyaddr
from fcntl import ioctl

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

class NetworkException(Exception):
    '''
    TBD
    '''
    def __init__(self, msg, status):
        Exception.__init__(self)
        self.msg = msg
        self.status = status
    def __str__(self):
        return self.msg

@trace
def get_ip_address() :
    '''
    TBD
    '''
    _cmd = "netstat -rn"
    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output_stdout, output_stderr) = proc_h.communicate()
    
    #while True :
    #    try :
    #        proc_h.wait()
    #        if proc_h.returncode != None :
    #            break
    #    except Exception, msg:
    #        _msg = "Error: " + str(msg)
    #        cberr(_msg)
    #        raise NetworkException(str(msg), "1") 
             
    if proc_h.returncode > 0 :
        _msg = "Command \"" + _cmd + "\" execution failed:" + output_stderr
        cberr(_msg)
        raise NetworkException(str(_msg), 1) 
    else :
        _msg = "Command \"" + _cmd + "\" execution succeeded"
        cbdebug(_msg)
    
    _default_if_candidates = []
    for _line in output_stdout.decode("utf-8").split('\n') :
        if len(_line) > 0 :
            if _line.count("default") and system() == "Darwin" :
                if _line.split()[-1] not in _default_if_candidates :
                    _default_if_candidates.append(_line.split()[-1])
            elif _line.split()[0] == "0.0.0.0" and system() == "Linux" :
                if _line.split()[-1] not in _default_if_candidates :
                    _default_if_candidates.append(_line.split()[-1])
    
    _default_if = False            
    if len(_default_if_candidates) == 1 :
        _default_if = _default_if_candidates[0]
    else :
        for _if in _default_if_candidates :
            if _if.count("utun") and system() == "Darwin" :
                _default_if = _if
    
    if not _default_if :
        _msg = "Unable to locate default physical interface of this CloudBench"
        _msg += " host."
        cberr(_msg)        
        raise NetworkException(str(_msg), 1) 
    
    _cmd = "ifconfig " + _default_if

    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output_stdout, output_stderr) = proc_h.communicate()
    
    #while True :
    #    try :
    #        proc_h.wait()
    #        if proc_h.returncode != None :
    #            break
    #    except Exception, msg:
    #        _msg = "Error: " + str(msg)
    #        cberr(_msg)
    #        raise NetworkException(str(msg), "1") 
             
    if proc_h.returncode > 0 :
        _msg = "Command \"" + _cmd + "\" execution failed:" + output_stderr
        cberr(_msg)
        raise NetworkException(str(_msg), 1) 
    else :
        _msg = "Command \"" + _cmd + "\" execution succeeded"
        cbdebug(_msg)
    
    _default_ip = False
    for _line in output_stdout.decode("utf-8").split('\n') :
        if _line.count("inet") and system() == "Darwin" :
            _default_ip = _line.split()[1]
            break
        elif _line.count("inet addr:") and system() == "Linux" :
            _default_ip = _line.split(':')[1]
            _default_ip = _default_ip.split()[0]
            break
        ### This is  centos specific
        elif _line.count("inet") and system() == "Linux" :
            _default_ip = _line.split()[1]
            break
    
    if not _default_ip :
        _msg = "Unable to locate default ip address interface of this "
        _msg += " CloudBench host."
        cberr(_msg)
        raise NetworkException(str(_msg), 1) 
    
    _msg = "Default ip address of this CloudBench host: " + _default_ip
    cbdebug(_msg)
    return _default_ip

@trace
def get_syslog_port(username) :
    '''
    TBD
    '''
    _cmd = "ps aux | grep rsyslog | grep " + username + " | grep -v grep"
    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output_stdout, output_stderr) = proc_h.communicate() 

    if proc_h.returncode > 0 :
        _msg = "Command \"" + _cmd + "\" execution failed:" + output_stderr
        cberr(_msg)
        raise NetworkException(str(_msg), 1) 
    else :
        _msg = "Command \"" + _cmd + "\" execution succeeded"
        cbdebug(_msg)
    
    _syslog_pid = output_stdout.decode("utf-8").split()[1]

    _cmd = "netstat -aunp | grep 0.0.0.0 | grep " + _syslog_pid
    proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output_stdout, output_stderr) = proc_h.communicate() 

    if proc_h.returncode > 0 :
        _msg = "Command \"" + _cmd + "\" execution failed:" + output_stderr
        cberr(_msg)
        raise NetworkException(str(_msg), 1) 
    else :
        _msg = "Command \"" + _cmd + "\" execution succeeded"
        cbdebug(_msg)
    
    try :
        _syslog_udp_assoc = output_stdout.decode("utf-8").split()[3]
        _syslog_port = _syslog_udp_assoc.split(':')[1]
            
        _msg = "Default syslog port for this CloudBench host found: " + _syslog_port
        cbdebug(_msg)
        return _syslog_port
    
    except Exception as e :
        _msg = "Unable to find default syslog port for this CloudBench host: " + _syslog_port
        cberr(_msg)
        raise NetworkException(str(_msg), 1)

def validIPv4(address) :
    '''
    TBD
    '''
    _parts = address.split(".")
    if len(_parts) != 4:
        return False
    for _octet in _parts:
        if not _octet.isdigit() :
            return False
        else :
            if not 0 <= int(_octet) <= 255:
                return False
    return True

def hostname2ip(hostname, raise_exception = False) :
    '''
    TBD
    '''
    try :
        cbdebug("Looking for host name/IP: " + hostname)

        if validIPv4(hostname) :
            _x = "ip address"
            _hostip = hostname
            hostname = gethostbyaddr(hostname)[0]
            if hostname.count("in-addr.arpa") :
                hostname = hostname.replace(".in-addr.arpa",'')
                hostname = hostname.split('.')[0]
                
        else :
            _x = "host name"
            _hostip = gethostbyname(hostname)

        _status = 0

    except socket.gaierror :
        _status = 1200
        _msg = "Error while attempting to resolve the " + _x + " \"" + hostname + "\"."
        _msg += " Please make sure this name is resolvable either in /etc/hosts or DNS."

    except socket.herror:
        _status = 1200
        _msg = "Error while attempting to resolve the " + _x + " \"" + hostname + "\"."
        _msg += " Please make sure this name is resolvable either in /etc/hosts or DNS."

    except Exception as e :
        _status = 23
        _msg = "Error while attempting to resolve the " + _x + " \"" + hostname + "\":" + str(e)

    finally:
        if _status :
            if raise_exception :
                raise NetworkException(str(_msg), _status)
            else :
                if _x == "host name" :
                    return hostname, "undefined"
                else :
                    return "undefined", hostname
                
        else :
            return hostname, _hostip


SIOCGIFMTU = 0x8921
SIOCSIFMTU = 0x8922

def get_mtu(ifname) :
    '''
    TBD
    '''
    s = socket.socket(type=socket.SOCK_DGRAM)
    
    ifr = ifname + '\x00'*(32-len(ifname))
    try:
        ifs = ioctl(s, SIOCGIFMTU, ifr)
        mtu = struct.unpack('<H',ifs[16:18])[0]
    except Exception as s:
        print('socket ioctl call failed: {0}'.format(s))
        raise
 
    return mtu

def check_url(url, string_to_replace = None, string_replacement = None, tout = 3) :
    '''
    TBD
    '''
    try:
        if len(url) :
            if string_to_replace and string_replacement :
                _url = url.replace(string_to_replace, string_replacement.strip())
            urllib.request.urlopen(urllib.request.Request(_url), timeout = tout)
        return True
        
    except:
        return False

@trace
class Nethashget :
    '''
    TBD
    '''
    @trace
    def __init__(self, hostname, port = None) :
        '''
        TBD
        '''
        self.pid = "nethashget"
        self.hostname = hostname

        if self.hostname.count('@') :
            self.hostname = self.hostname.split('@')[1]

        if port :
            self.port = int(port)
        else :
            self.port = None
        self.socket = None
        

    @trace
    def connect(self) :
        '''
        TBD
        '''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, int(self.port)))

    def path_mtu_discover(self, port = False) :
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.hostname, (port if port else (self.port if self.port is not None else 9999))))
        self.socket.setsockopt(socket.IPPROTO_IP, IN.IP_MTU_DISCOVER, IN.IP_PMTUDISC_DO)
        return self.socket.getsockopt(socket.IPPROTO_IP, getattr(IN, 'IP_MTU', 14))

    @trace        
    def nmap(self, port = None, protocol = "TCP", reverse = False) :
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

            if not reverse :
                self.socket.close()
                self.socket = None
                return True
            else :
                _msg = protocol + " port " + str(port) + " on host " 
                _msg += self.hostname + " is NOT free"
                cberr(_msg)
                raise NetworkException(str(_msg), "1")

        except socket.error as msg :
            self.socket.close()
            self.socket = None

            if not reverse :
                _msg = "Unable to connect to " + protocol + " port " + str(port)
                _msg += " on host " + self.hostname + ": " + str(msg)
                cberr(_msg)
                raise NetworkException(str(_msg), "1")
            else :
                _msg = protocol + " port " + str(port) + " on host " 
                _msg += self.hostname + ": " + str(msg) + "is free"
                cbdebug(_msg)
                return True


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
        
        except socket.error as msg :
            _msg = "Unable to connect to " + protocol + " port " + str(port)
            _msg += " on host " + self.hostname + ": " + str(msg)
            cbinfo(_msg)
            return False
            self.socket.close()
            self.socket = None

    @trace
    def cat(self, reset = True) :
        '''
        TBD
        '''
        result = '';
        
        if(reset and self.socket is not None) :
            try :
                self.socket.close()
            except :
                True
                
        if reset :
            try :
                self.connect()
            except socket.error as msg :
                _msg = "ERROR cannot connect to ganglia gmetad to the port "
                _msg += self.port + " on server " + self.hostname + ": "
                _msg += str(msg) + '.' 
                cbdebug(_msg)
                self.socket = None  
                return None 

        while(1):
            _buffer = ''
            try:                
                _buffer = self.socket.recv(1024)
                while(_buffer != ''):
                    result += _buffer
                    try:
                        _buffer = self.socket.recv(1024)
                    except socket.error as err:
                        print((err, type(err)))
                        _buffer = ''
                if(_buffer == ''):
                    break
            except socket.error as err:
                print((err, type(err)))
            if(_buffer == ''):
                break

        self.socket.close()
        self.socket = None  

        return result

    @trace
    def get(self, key) :
        '''
        TBD
        '''
        self.connect()
        self.socket.send(key)
        result = self.cat(False)
        self.socket = None
        return result
