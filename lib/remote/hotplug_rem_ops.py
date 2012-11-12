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

'''
    Created on Jan 29, 2011

    Hotplug remote operations class

    @author: msilva
'''

from time import sleep
from subprocess import PIPE,Popen

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit


class HotplugMgdConn :
    '''
    TBD
    '''
    
    @trace
    def __init__(self, pid, host, login, priv_key) :
        '''
        TBD
        '''
        self.pid = pid
        self.host = host
        self.login = login
        self.priv_key = priv_key

    class HotplugMgdConnException(Exception):
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
    def get_cpus_state(self):
        '''
        TBD
        '''
        _cpu_state = []
        _cpu_state.append("1")
        
        _cmd = "ssh"
        if self.priv_key :
            _cmd += " -i " + self.priv_key
        _cmd += " -o StrictHostKeyChecking=no "
        _cmd += self.login + '@' + self.host + ' '
        _cmd += "\"grep \[0-1\] /sys/devices/system/cpu/*/online\""
        
        _proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
        if not _proc_h :
            _msg = "Failed to create subprocess with command " + _cmd
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)
        else :
            _msg = "Successfully created subprocess with command " + _cmd
            cbdebug(_msg)
        
        _stdout = None
        _stderr = None
        _stdout, _stderr = _proc_h.communicate()
                
        #if _stderr :
        #    _msg = " - Failed to access guest \"" + self.host + "\""
        #    cberr(self.procid + " - " + _msg)
        #    cbdebug(self.procid + " - Exit point")
        #    raise HotplugMgdConnException(_msg, "3")
        
        for _line in _stdout.split('\n') :
            if len(_line) > 0 :
                _fields = _line.split('/')
                _cpu_state.append(_fields[6].split(':')[1])
        
        return _cpu_state

    @trace
    def set_cpu_state(self, cpu_nr, state) :
        '''
        TBD
        '''        
        _cmd = "ssh"
        if self.priv_key :
            _cmd += " -i " + self.priv_key
        _cmd += " -o StrictHostKeyChecking=no "
        _cmd += self.login + '@' + self.host + ' '
        if state == "active" :
            _cmd += "\"/bin/echo 1 > /sys/devices/system/cpu/cpu" + str(cpu_nr)
            _cmd += "/online\""
        elif state == "inactive" :
            _cmd += "\"/bin/echo 0 > /sys/devices/system/cpu/cpu" + str(cpu_nr)
            _cmd += "/online\""
        else :
            _msg = "Invalid state (" + state + ") for cpu " + str(cpu_nr)
            _msg = " on the guest \"" + self.host + "\"."
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 4)

        _proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
        if not _proc_h :
            _msg = "Failed to create subprocess with command " + _cmd
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)
        else :
            _msg = "Successfully created subprocess with command " + _cmd
            cbdebug(_msg)
                    
        _stdout = None
        _stderr = None
        _stdout, _stderr = _proc_h.communicate()

        sleep(6)
        
        _cmd = "ssh"
        if self.priv_key :
            _cmd += " -i " + self.priv_key
        _cmd += " -o StrictHostKeyChecking=no "
        _cmd += self.login + '@' + self.host + ' '
        _cmd += "cat /sys/devices/system/cpu/cpu" + str(cpu_nr) + "/online"
        
        _proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
        if not _proc_h :
            _msg = "Failed to create subprocess with command " + _cmd
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)
        else :
            _msg = "Successfully created subprocess with command " + _cmd
            cbdebug(_msg)
        
        _stdout = None
        _stderr = None
        _stdout, _stderr = _proc_h.communicate()        
        
        if state == "active" and _stdout.split('\n')[0].count('1') :
            return True
        elif state == "inactive" and _stdout.split('\n')[0].count('0') :
            return True
        else :
            _msg = "Failed to set cpu " + str(cpu_nr) + " state to " + state
            _msg += " on guest " + self.host + '.'
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)

    @trace
    def set_active_cpus(self, active_cpus_tgt_nr):
        '''
        TBD
        '''        
        _cpu_state = self.get_cpus_state()
        
        _total_cpus = len(_cpu_state)
        
        _active_cpus = []
        _inactive_cpus = []
        for _cpu_number, _cpu_state in enumerate(_cpu_state) :
            if _cpu_state == '1' and _cpu_number > 0 :
                _active_cpus.append(_cpu_number)
            elif _cpu_state == '0' :
                _inactive_cpus.append(_cpu_number)
        
        active_cpus_tgt_nr = int(active_cpus_tgt_nr)
        
        if active_cpus_tgt_nr > _total_cpus :
            _msg = "Unable to activate " + str(active_cpus_tgt_nr) + " CPUs on "
            _msg += "the guest \"" + self.host + "\" (maximum number of CPUs "
            _msg += "for this guest is " + str(_total_cpus) + ")."
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)

        elif active_cpus_tgt_nr < 1 :
            _msg = "At least 1 CPU must be active on the guest "
            _msg += "\"" + self.host + "\"."
            cberr(_msg)
            raise self.HotplugMgdConnException(_msg, 3)
        
        active_cpus_tgt_nr -= 1 #CPU0 is always active
        
        _active_cpus_nr = len(_active_cpus)
        if active_cpus_tgt_nr > _active_cpus_nr :
            while _active_cpus_nr < active_cpus_tgt_nr :
                _cpu_nr = _inactive_cpus.pop()
                try :
                    self.set_cpu_state(_cpu_nr, "active")
                    _active_cpus_nr += 1
                    sleep(3)
                except self.HotplugMgdConnException :
                    _msg = "Error while checking active cpus"
                    raise self.HotplugMgdConnException(_msg, 3) 
        elif active_cpus_tgt_nr < _active_cpus_nr :
            while _active_cpus_nr > active_cpus_tgt_nr :
                _cpu_nr = _active_cpus.pop()
                try :
                    self.set_cpu_state(_cpu_nr, "inactive")
                    _active_cpus_nr -= 1
                    sleep(3)
                except self.HotplugMgdConnException :
                    _msg = "Error while checking active cpus"
                    raise self.HotplugMgdConnException(_msg, 3)
        else :
            _msg = "The number of active CPUs is equal the number of "
            _msg += " targeted active CPUs. There is nothing to be done."
            cbdebug(_msg)
        
        return True
