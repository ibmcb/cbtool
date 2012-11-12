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
    Created on Nov 15, 2011

    Network primitives for CloudBench

    @author: Michael R. Hines, Marcio A. Silva
'''

from subprocess import PIPE,Popen
from time import sleep
from platform import system

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
     
class ProcessManagement :
    '''
    TBD
    '''
    @trace
    def __init__(self, hostname = "127.0.0.1", port = "22", username = None, cloud_name = None) :
        '''
        TBD
        '''
        self.pid = "process_management"
        self.hostname = hostname
        self.port = int(port)
        self.username = username
        self.cloud_name = cloud_name

    @trace
    class ProcessManagementException(Exception):
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
    def run_os_command(self, cmdline) :
        '''
        TBD
        '''
        if self.hostname == "127.0.0.1" or self.hostname == "0.0.0.0" :
            _cmd = cmdline

        cbdebug("starting daemon: " + _cmd);
        _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)

        if _proc_h.pid :
            if not cmdline.count("--debug_host=localhost") :
                _result = _proc_h.communicate()
                if _proc_h.returncode and len(_result[1]) :
                    _msg = "Error while checking for a pid for a process with the "
                    _msg += "command line \"" + cmdline + "\" (returncode = "
                    _msg += str(_proc_h.pid) + ") :" + str(_result[1])
                    raise self.ProcessManagementException(str(_msg), "81918")
                else :
                    _status = 0
                    _result_stdout = _result[0]
                    _result_stderr = _result[1]
            else :
                _status = 0
                _result_stdout = ""
                _result_stderr = ""
        else :
            _msg = "Error running the command \"" + cmdline + "\"."
            _status = 81713
            _result_stdout = ""
            _result_stderr = ""
        return _status, _result_stdout, _result_stderr

    @trace
    def get_pid_from_port(self, port, protocol = "tcp") :
        '''
        TBD
        '''
        _cmd = "sudo fuser -u " + str(port) + '/' + protocol.lower()
        _status, _result_stdout, _result_stderr = self.run_os_command(_cmd)
        if not _status :
            if len(_result_stdout) :
                _pid = _result_stdout
                _username = _result_stderr.split()[1].replace('(','').replace(')','')
                return _pid, _username
            else: 
                return False, False

    @trace
    def get_free_port(self, starting_port, protocol = "tcp") :
        '''
        TBD
        '''
        _port = int(starting_port)
        _pid, _username = self.get_pid_from_port(_port, protocol)
        while _pid :
            _port += 1
            _pid, _username = self.get_pid_from_port(_port, protocol)
        return str(_port)

    @trace
    def get_pid_from_cmdline(self, cmdline) :
        '''
        TBD
        '''
        _pid_list = []
        
        _cmd = "sudo ps aux | tr '[:upper:]' '[:lower:]' | grep \"" + cmdline.replace("'", "").lower() + "\""
        
        if self.cloud_name :
            _cmd = _cmd + " |  grep \"" + self.cloud_name.lower() + "\""
        if self.username :
            _cmd = _cmd + " |  grep \"" + self.username + "\""
            
        _cmd = _cmd + " | grep -v grep" 

        if self.hostname != "127.0.0.1" and self.hostname != "localhost" :
            _cmd = "ssh " + self.hostname + ' ' + _cmd

        _status, _result_stdout, _result_stderr = self.run_os_command(_cmd)

        if _status :
            _msg = "Error while checking for a pid for a process with the "
            _msg += "command line \"" + cmdline + "\" (pid)"
            raise self.ProcessManagementException(str(_msg), "81918")
        else :
            _result_lines = _result_stdout.split('\n')
            for _line in _result_lines :
                if len(_line) :
                    if self.username == "" :
                        _pid = _line.split()[1]
                        _pid_list.append(_pid)
                    else :
                        if _line.count(self.username) :
                            _pid = _line.split()[1]
                            _pid_list.append(_pid)
            
            if len(_pid_list) :
                _msg = "A pid list for the process with the command line \""
                _msg += cmdline + "\" was found."
            else :
                _msg = "A pid list for the process with the command line \""
                _msg += cmdline + "\" was not found."
            cbdebug(_msg)
    
            return _pid_list
        
    @trace
    def start_daemon(self, cmdline, port = None, protocol = None, conditional = False, search_keywords = None) :
        '''
        TBD
        '''
        if self.hostname == "127.0.0.1" :
            _cmd = cmdline

        if port :
            _pid, _username = self.get_pid_from_port(port, protocol)
            if _pid :
                if _username != self.username :
                    return [ "pnf-" + _pid + '-' + _username ]

        if conditional :
            _pid = self.get_pid_from_cmdline(_cmd if not search_keywords else search_keywords)
            if not _pid :
                _status, _a, _b = self.run_os_command(_cmd)
                # The process could be a daemon, so there is no point in waiting
                # for its completion. However, we do wait a little bit just to be 
                # able to get the pid of the process, because a daemon would fork 
                # a new process.
                sleep(3)
        else :
            _status, _a, _b = self.run_os_command(_cmd)        
            # Same comment
            sleep(3)

        _pid = self.get_pid_from_cmdline(cmdline if not search_keywords else search_keywords)
        
        _msg = "A process with the command line \"" + cmdline + "\" (pid "
        _msg += str(_pid) + ") was started succesfully."
        cbdebug(_msg)
        return _pid

    @trace
    def kill_process(self, cmdline, kill_options = "") :
        '''
        TBD
        '''
        _pid = ['X']
        
        while len(_pid) :

            _pid = self.get_pid_from_cmdline(cmdline)
    
            if len(_pid) :
                _pid = _pid[0]

                if self.hostname == "127.0.0.1" :
                    # Not using SIGKILL is insufficient for threaded python processes
                    # You need to hard-kill them.
                    _cmd = "kill -9 " + kill_options + ' ' + str(_pid)
    
                self.run_os_command(_cmd)
                sleep(1)
                _old_pid = _pid

        _msg = "A process with the command line \"" + cmdline + "\" (pid "
        _msg += str(_old_pid) + ") was killed successfully."
        cbdebug(_msg)
        return _old_pid
