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
    Created on Oct 25, 2012

    Dependency Checker/Installer

    @author: Marcio A. Silva, Michael R. Hines
'''
from sys import path
from os import access, F_OK
import re
import sys
import platform

from lib.remote.process_management import ProcessManagement

def deps_file_parser(depsdict, username, file_name = None) :
    '''
    TBD
    '''
    
    if not file_name :
        _fn = path[0] + "/configs/" + username + "_dependencies.txt"
    
        if not access(_fn, F_OK) :
            _fn = path[0] + "/configs/templates/dependencies.txt"
    else :
        _fn = file_name

    try:
        _fd = open(_fn, 'r')
        _fc = _fd.readlines()
        _fd.close()
        
        for _line in _fc :
            _line = _line.strip()

            if _line.count("#",0,2) :
                _sstr = None
            elif len(_line) < 3 :
                _sstr = None
            elif _line.count(" = ") :
                _sstr = " = "
            elif _line.count(" =") :
                _sstr = " ="
            elif _line.count("= ") :
                _sstr = "= "
            elif _line.count("=") :
                _sstr = "="
            else :
                _sstr = None

            if _sstr :
                _key, _value = _line.split(_sstr)
                _key = _key.strip()
                depsdict[_key] = _value

    except Exception, e :
        _msg = "###### Error reading file \"" + _fn  + "\":" + str(e)
        print _msg
        exit(4)
    
    return True
 
def get_linux_distro() :
    '''
    TBD
    '''
    _linux_distro_name, _linux_distro_ver, _x = platform.linux_distribution()
    if _linux_distro_name.count("Red Hat") :
        _distro = "rhel"
    elif _linux_distro_name.count("Ubuntu") :
        _distro = "ubuntu"
    else :
        print "Unsupported distribution (" + _linux_distro_name + ")"
        exit(191)

    if len('%x'%sys.maxint) == 8 :
        _arch = "i686"
    else :
        _arch = "x86_64"
        
    return _distro, _arch

def get_cmdline(depkey, depsdict, operation) :
    '''
    TBD
    '''
    if operation == "inst" :
        commandline_key = depsdict["cdist"] + '-' + depkey + '-' + depsdict[depkey + '-' + operation]
    else :
        commandline_key = depkey + '-' + operation

    commandline = depsdict[commandline_key]
    commandline = commandline.replace("3RPARTYDIR", depsdict["3rdpartydir"].strip().replace("//",'/'))
    commandline = commandline.replace("GITURL", depsdict["giturl"].strip())
    commandline = commandline.replace("RSYNCURL", depsdict["rsyncurl"].strip())
    commandline = commandline.replace("ARCH", depsdict["carch"].strip())
    commandline = commandline.replace("DISTRO", depsdict["cdist"].strip())
    commandline = commandline.replace("USERNAME", depsdict["username"].strip())
    return commandline

def inst_conf_msg(depkey, depsdict) :
    '''
    TBD
    '''
    
    msg = " Please install/configure \"" + depkey + "\" by issuing the following command: \""
    msg += get_cmdline(depkey, depsdict, "inst") + "\"\n"
    
    return msg

def execute_command(operation, depkey, depsdict, hostname = "127.0.0.1", username = None, process_manager = None) :
    '''
    TBD
    '''
    try :
        _cmd = {}
        _cmd["test"] = get_cmdline(depkey, depsdict, "test")
        _cmd["inst"] = get_cmdline(depkey, depsdict, "inst")

        if not process_manager :
            process_manager = ProcessManagement(hostname)

        if depkey != "sudo" and operation == "test" :
            _msg = "Checking \"" + depkey + "\" version by executing the command \""
            _msg += _cmd[operation] + "\"..."
        
        elif depkey == "sudo" and operation == "test" :
            _msg = "Checking passwordless sudo for the user \"" + username + "\" "
            _msg += "by executing the command \"" + _cmd[operation] + "\"..."

        else :
            _msg = "    Installing \"" + depkey + "\" by executing the command \""
            _msg += _cmd[operation] + "\"..."

        _status, _result_stdout, _result_stderr = process_manager.run_os_command(_cmd[operation])

        if not _status :
            if operation == "inst" :
                _msg += "DONE OK."
            else :
                _msg += compare_versions(depkey, depsdict, _result_stdout.strip())
        else :
            _msg += "NOT OK."

        if _msg.count("NOT OK") :
            _status = 701

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _msg += "NOT OK. "

    except Exception, e :
        _status = 23
        _msg += "NOT OK (" + str(e) + ")."

    finally :
        if _status :

            if operation == "inst" :
                _msg += "There was an error while installing \"" + depkey + "\"."
            else :
                _msg += inst_conf_msg(depkey, depsdict)

        return _status, _msg        

def compare_versions(depkey, depsdict, version_b) :
    '''
    TBD
    '''
    try :
        version_a = depsdict[depkey + "-ver"]
        if version_a.lower() == "any" :
            _result = 0
            version_a = "ANY"
            version_b = "ANY"
        else :
            _non_decimal = re.compile(r'[^\d.]+')
            version_a = _non_decimal.sub('', version_a)
            version_b = _non_decimal.sub('', version_b)
            _version_a = map(int, re.sub('(\.0+)+\Z','', version_a).split('.'))
            _version_b = map(int, re.sub('(\.0+)+\Z','', version_b).split('.'))
            _result = cmp(_version_a,_version_b)

    except Exception, e :
        _result = -1000000

    finally :
        if _result > 0 :
            return str(version_b) + " < " + str(version_a) + " NOT OK." 
        elif _result <= -1000000 :
            return " NOT OK."
        else :
            return str(version_b) + " >= " + str(version_a) + " OK."

def dependency_checker_installer(hostname, username, trd_party_dir, operation) :
    '''
    TBD
    '''
    _depsdict = {}
    
    deps_file_parser(_depsdict, username)
    
    _depsdict["cdist"], _depsdict["carch"] = get_linux_distro()
    _depsdict["3rdpartydir"] = trd_party_dir
    _depsdict["username"] = username

    _proc_man =  ProcessManagement()

    for _dep in [ "sudo" ]:
        _status, _msg = execute_command("test", _dep, _depsdict, hostname = "127.0.0.1", username = username, process_manager = _proc_man)
        print _msg
        if _status :
            _dep_missing = 1
            _fmsg = _dep
            break

    try :
        if not _status :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
    
            _fmsg = ": "
            _missing_dep = []
            _dep_list = []
 
            for _key in _depsdict.keys() :
                if _key.count("-test") and not _key.count("sudo") :
                    _dep_list.append(_key.replace("-test",''))
            _dep_list.remove("git")
            _dep_list.sort()
            _dep_list.insert(0, "git")

            _dep_missing = 0
            for _dep in _dep_list :
                _status, _msg = execute_command("test", _dep, _depsdict, hostname = "127.0.0.1", username = username, process_manager = _proc_man)
                print _msg

                if _status :
                    _dep_missing += 1
                    _missing_dep.append(_dep)
    
                    if operation == "inst" :
                        _status, _msg = execute_command("inst", _dep, _depsdict, hostname = "127.0.0.1", username = username, process_manager = _proc_man)
                        print _msg
                        if not _status :
                            _dep_missing -= 1
                            _missing_dep.remove(_dep)

            _status = _dep_missing
            _fmsg += ','.join(_missing_dep)

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _fmsg = str(obj.msg)

    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "There are " + str(_dep_missing) + " dependencies missing " + _fmsg

        else :
            _msg = "All dependencies are in place"
        return _status, _msg
