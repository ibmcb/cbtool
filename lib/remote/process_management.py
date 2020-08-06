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

    Process management (local and remote) primitives for CloudBench

    @author: Michael R. Galaxy, Marcio A. Silva
'''

from subprocess import PIPE,Popen
from time import sleep, time

from lib.auxiliary.thread_pool import ThreadPool
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

class ProcessManagement :
    '''
    TBD
    '''
    @trace
    def __init__(self, hostname = "127.0.0.1", port = "22", username = None, \
                 cloud_name = None, priv_key = None, config_file = None, \
                 connection_timeout = None, osci = None) :
        '''
        TBD
        '''
        self.pid = "process_management"
        self.hostname = hostname
        self.port = int(port)
        self.username = username
        self.cloud_name = cloud_name
        self.priv_key = priv_key
        self.config_file = config_file
        self.connection_timeout = connection_timeout
        self.osci = osci
        self.thread_pools = {}

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
    def run_os_command(self, cmdline, override_hostname = None, really_execute = True, \
                       debug_cmd = False, raise_exception = True, step = None, \
                       tell_me_if_stderr_contains = False, port = None, check_stderr_len = True, ssh_keepalive = True) :
        '''
        TBD
        '''
        if override_hostname :
            _hostname = override_hostname
        else :
            _hostname = self.hostname

        if _hostname == "127.0.0.1" or _hostname == "0.0.0.0" :
            _local = True
        else :
            _local = False

        if port :
            _port = port
        else :
            _port = self.port
        
        if _local :
            # This is causing problems, but generally seems kind of wierd anyway.
            # For whatever the original problem was, let's try to find a better solution.
            # Seems to work fine without it.
            #if self.username == "root" :
            #    _cmd = "sudo su -c \"" + cmdline + "\""
            #else :
            _cmd = cmdline
        else :
            if self.username :
                _username = " -l " + self.username + ' '
            else :
                _username = ''

            if self.priv_key :
                _priv_key = " -i " + self.priv_key + ' '
            else :
                _priv_key = ''

            if self.config_file :
                _config_file = " -F " + self.config_file + ' '
            else:
                _config_file = ''

            if self.connection_timeout :
                _connection_timeout = " -o ConnectTimeout=" + str(self.connection_timeout) + ' '
                if ssh_keepalive :
                    _established_timeout = " -o ServerAliveCountMax=1 -o ServerAliveInterval=" + str(self.connection_timeout) + ' '
                else :
                    _established_timeout = ""
            else :
                _connection_timeout = ''
                _established_timeout = ''

            _cmd = "ssh "
            _cmd += " -p " + str(_port) + ' ' 
            _cmd += _priv_key 
            _cmd += _config_file 
            _cmd += _connection_timeout            
            _cmd += _established_timeout
            _cmd += " -o StrictHostKeyChecking=no"
            _cmd += " -o UserKnownHostsFile=/dev/null "
            _cmd += " -o BatchMode=yes " 
            _cmd += _username
            
            self.rsync_conn = _cmd
            
            _cmd += _hostname + " \"" + cmdline + "\""
        
        if str(really_execute).lower() != "false" and str(really_execute).lower() != "pseudotrue" :
            _msg = "running os command: " + _cmd
            cbdebug(_msg);
            _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)

            if _proc_h.pid :

                if not cmdline.count("--debug_host=localhost") :

                    _result = _proc_h.communicate()

                    if check_stderr_len :
                        _stderr_len = len(_result[1].decode('utf-8'))
                    else :
                        _stderr_len = 1
                    
                    if _proc_h.returncode and _stderr_len :
                        _msg = "Error while executing the command line "
                        _msg += "\"" + cmdline + "\" (returncode = "
                        _msg += str(_proc_h.returncode) + ") :" + str(_result[1].decode('utf-8')) + str(_result[0].decode('utf-8'))
                        cbdebug(_msg)
                        if tell_me_if_stderr_contains is not False and _result[1].decode('utf-8').count(tell_me_if_stderr_contains) :
                            cbdebug("Command failed with: " + tell_me_if_stderr_contains, True)
                            raise self.ProcessManagementException(str(_msg), "90001")
                        elif raise_exception :
                            raise self.ProcessManagementException(str(_msg), "81918")
                        
                        else :
                            _status = _proc_h.returncode
                            _result_stdout = _result[0].decode('utf-8')
                            _result_stderr = _result[1].decode('utf-8')
                    else :
                        _status = 0
                        _result_stdout = _result[0].decode('utf-8')
                        _result_stderr = _result[1].decode('utf-8')
                else :
                    _status = 0
                    _result_stdout = " "
                    _result_stderr = " "
            else :
                _msg = "Error running the command \"" + cmdline + "\"."
                cbdebug(_msg)
                _status = 81713
                _result_stdout = ""
                _result_stderr = ""
        else :
            _msg = "This is the command that would have been executed "
            _msg += "from the orchestrator"

            if step :
                _msg += " on STEP " + str(step)
            _msg += " : \n         "  + _cmd

            if str(debug_cmd).lower() == "true" :
                cbdebug(_msg, True)
            else :
                cbdebug(_msg)

            _status = 0
            _result_stdout = " "
            _result_stderr = " "

        return _status, _result_stdout, _result_stderr

    '''
        This function has been modified to optionally take a VM's uuid instead
        of the hostname/IP addresses. This is because the IP can change between
        invocations (particularly if VPN ip addresses change). By taking
        a UUID, we can lookup the IP from the object store on-the-fly if
        the IP changes and survive errors in remote execution after the
        SSH command times out.

        The field `override_hostname` will be a UUID instead of an IP address
        if and only if the field `osci` is not False and holds a reference
        the currently used osci object and the field 'get_hostname_using_key`
        indicates whether or not the key 'prov_cloud_ip` or `run_cloud_ip`
        should be used when looking up the VM object from the object store.
    '''
    def retriable_run_os_command(self, cmdline, override_hostname_or_uuid = None, \
                                 total_attempts = 2, retry_interval = 3,
                                 really_execute = True, \
                                 debug_cmd = False, \
                                 raise_exception_on_error = False, \
                                 step = None,
                                 tell_me_if_stderr_contains = False, \
                                 port = 22, \
                                 remaining_time = 100000, \
                                 osci = False, \
                                 get_hostname_using_key = False,
                                 ssh_keepalive = True):
        '''
        TBD
        '''
        _attempts = 0

        _abort = "no"

        _start = int(time())
        _spent_time = 0
        
        _override_hostname = "x.x.x.x-invalid"

        while _attempts < int(total_attempts) and _abort != "yes" :
            try :
                if osci is not False and get_hostname_using_key is not False :
                    _obj_attr_list = osci.get_object(self.cloud_name, "VM", False, override_hostname_or_uuid, False)                        
                    _override_hostname = _obj_attr_list[get_hostname_using_key]
                else :
                    _override_hostname = override_hostname_or_uuid
                _status, _result_stdout, _result_stderr = self.run_os_command(cmdline, \
                                                                              _override_hostname, \
                                                                              really_execute, \
                                                                              debug_cmd, \
                                                                              raise_exception_on_error, \
                                                                              step = step,
                                                                              tell_me_if_stderr_contains = tell_me_if_stderr_contains, \
                                                                              port = port,
                                                                              ssh_keepalive = ssh_keepalive)

            except ProcessManagement.ProcessManagementException as obj :
                if obj.status == "90001" :
                    raise obj
                _status = obj.status
                _result_stdout = "NOK"
                _result_stderr = obj.msg

            if _status and len(_result_stderr) :
                _msg = "Command \"" + cmdline + "\" failed to execute on "
                _msg += "hostname " + str(_override_hostname) + ", port " + str(port) + " after attempt "
                _msg += str(_attempts) + ". Will try " + str(total_attempts - _attempts)
                _msg += " more times."
                cbdebug(_msg, True)
                _attempts += 1
                sleep(retry_interval)
                _spent_time = int(time()) - _start
                
                if _spent_time > remaining_time :
                    _abort = "yes"
            else :
                break

        if _attempts >= int(total_attempts) :
            _status = 17368
            _fmsg = "Giving up on executing command \"" + cmdline + "\" on hostname "
            _fmsg += str(_override_hostname) + ". Too many attempts (" + str(_attempts) + ").\n"
            #_fmsg += "STDOUT is :\n" + str(_result_stdout) + '\n'
            #_fmsg += "STDERR is :\n" + str(_result_stderr) + '\n'
            cberr(_fmsg)
            if raise_exception_on_error :
                raise self.ProcessManagementException(str(_fmsg), _status)

            return _status, _fmsg, {"status" : _status, "msg" : _fmsg, "result" : _status}
        
        else :
            if _abort != "yes" :
                _status = 0
                _msg = "Command \"" + cmdline + "\" executed on hostname "
                _msg += str(_override_hostname) + " successfully."
                cbdebug(_msg)
                return _status, _msg, {"status" : _status, "msg" : _msg, "result" : _status}
            else :
                _status = 8167
                _fmsg = "Execution of command \"" + cmdline + "\", on hostname "
                _fmsg += str(_override_hostname) + " was aborted."
                #_fmsg += "STDOUT is :\n" + str(_result_stdout) + '\n'
                #_fmsg += "STDERR is :\n" + str(_result_stderr) + '\n'
                cberr(_fmsg)
                if raise_exception_on_error :
                    raise self.ProcessManagementException(str(_fmsg), _status)
    
                return _status, _fmsg, {"status" : _status, "msg" : _fmsg, "result" : _status}

    def parallel_run_os_command(self, cmdline_list, override_hostname_or_uuid_list, port_list, \
                                total_attempts, retry_interval, \
                                execute_parallelism, really_execute = True, \
                                debug_cmd = False, step = None, remaining_time = 100000, osci = False, get_hostname_using_key = False, ssh_keepalive = True) :
        '''
        TBD
        '''

        _status = 100
        _xfmsg = "An error has occurred, but no error message was captured"
        _thread_pool = None
        _child_failure = False

        try :
            for _index in range(0, len(override_hostname_or_uuid_list)) :
                serial_mode = False # only used for debugging

                if not _thread_pool and not serial_mode :
                    pool_key = 'ai_execute_with_parallelism_' + str(execute_parallelism)
                    if pool_key not in self.thread_pools :
                        _thread_pool = ThreadPool(int(execute_parallelism))
                        self.thread_pools[pool_key] = _thread_pool
                    else :
                        _thread_pool = self.thread_pools[pool_key]

                if serial_mode :
                    if len(cmdline_list[_index]) > 0:
                        _status, _fmsg, _object = \
                        self.retriable_run_os_command(cmdline_list[_index], \
                                                      override_hostname_or_uuid_list[_index], \
                                                      total_attempts, \
                                                      retry_interval, \
                                                      really_execute, \
                                                      debug_cmd, \
                                                      False, \
                                                      step, \
                                                      False, \
                                                      port_list[_index], \
                                                      remaining_time,
                                                      osci = osci,
                                                      get_hostname_using_key = get_hostname_using_key,
                                                      ssh_keepalive = ssh_keepalive
                                                      )
                    else :
                        _status = 0
                        _xfmsg = "OK"

                    if _status :
                        _xfmsg = _fmsg
                        _child_failure = True
                        break
                else :
                    if len(cmdline_list[_index]) > 0:
                        _thread_pool.add_task(self.retriable_run_os_command, \
                                              cmdline_list[_index], \
                                              override_hostname_or_uuid_list[_index], \
                                              total_attempts, \
                                              retry_interval, \
                                              really_execute, \
                                              debug_cmd, \
                                              False, \
                                              step, \
                                              False, \
                                              port_list[_index], \
                                              remaining_time, \
                                              osci = osci, \
                                              get_hostname_using_key = get_hostname_using_key,
                                              ssh_keepalive = ssh_keepalive)

            if _thread_pool and not serial_mode:
                _xfmsg = ''
                _results = _thread_pool.wait_completion()

                if len(_results) :
                    for (_status, _fmsg, _object) in _results :
                        if int(_status) :
                            _xfmsg += _fmsg
                            _child_failure = True
                            break

                if _child_failure :
                    _status = 81717
                else :
                    _status = 0
    
        except KeyboardInterrupt :
            _status = 42
            _xfmsg = "CTRL-C interrupt"
            cbdebug("Signal children to abort...", True)
            if _thread_pool :
                _thread_pool.abort()

        except Exception as e :
            _status = 23
            _xfmsg = str(e)
            if _thread_pool :
                _thread_pool.abort()
        finally :
            if _status :
                _msg = "Parallel run os command operation failure: " + _xfmsg
                cberr(_msg, True)
            else :
                _msg = "Parallel run os command success."
                cbdebug(_msg)

            return _status, _msg

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

    def get_port_from_pid(self, pid) :
        '''
        TBD
        '''
        _cmd = "sudo netstat -tulpn | grep '" + str(pid) + "/*' | sort"
        _status, _result_stdout, _result_stderr = self.run_os_command(_cmd)
        if not _status :
            if len(_result_stdout) :
                '''
                Some daemons (e.g., mongod) listen to more than one port
                simultenously. Here we are assuming that the first port is the 
                one that matters
                '''
                _result_stdout = _result_stdout.split('\n')[0]
                _result_stdout = _result_stdout.split()[3]
                if _result_stdout.count(':') :
                    _port = _result_stdout.split(':')[1]
                    return _port
                else :
                    return False
            else: 
                return False

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
    def get_pid_from_cmdline(self, cmdline, extra = False) :
        '''
        TBD
        '''
        _pid_list = []
        
        _cmd = "sudo ps aux | tr '[:upper:]' '[:lower:]' | grep \"" + cmdline.replace("'", "").lower() + "\" | grep -i \"" + (extra if extra else "") + "\""
        
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
            raise self.ProcessManagementException(str(_msg), "81919")
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
        return [ _pid ]

    @trace
    def kill_process(self, cmdline, kill_options = False, port = False) :
        '''
        TBD
        '''
        _pid = ['X']
        _old_pid = False 
        _msg = "none"

        while len(_pid) and _pid[0] :

            if kill_options :
                _pid = self.get_pid_from_cmdline(cmdline, kill_options)
            elif port :
                pid, username = self.get_pid_from_port(port)
                _pid = [pid]
            else :
                _pid = self.get_pid_from_cmdline(cmdline)

            if len(_pid) and _pid[0] :
                _pid = _pid[0]

                if self.hostname == "127.0.0.1" :
                    # Not using SIGKILL is insufficient for threaded python processes
                    # You need to hard-kill them.

                    _pid = _pid.replace(self.cloud_name,'')
                    _cmd = "kill -9 " + str(_pid)

                self.run_os_command(_cmd)

                sleep(1)
                _old_pid = _pid

        _msg = "A process with the command line \"" + cmdline + "\" (pid "
        _msg += str(_old_pid) + ") was killed successfully."
        cbdebug(_msg)
        return _old_pid
