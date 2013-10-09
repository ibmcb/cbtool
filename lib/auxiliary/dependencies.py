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

def deps_file_parser(depsdict, username) :
    '''
    TBD
    '''
    
    _fn = path[0] + "/configs/" + username + "_dependencies.txt"
    
    if not access(_fn, F_OK) :
        _fn = path[0] + "/configs/dependencies.txt"

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

    except Exception :
        _msg = "###### Error reading file \"" + _fn  + "\""
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

def inst_conf_msg(depkey, depsdict) :
    '''
    TBD
    '''
    commandline_key = depsdict["cdist"] + '-' + depkey + '-' + depsdict[depkey + "-inst"]
    commandline = depsdict[commandline_key]
    commandline = commandline.replace("3RPARTYDIR", depsdict["3rdpartydir"].strip().replace("//",'/'))
    commandline = commandline.replace("GITURL", depsdict["giturl"].strip())
    commandline = commandline.replace("RSYNCURL", depsdict["rsyncurl"].strip())
    commandline = commandline.replace("ARCH", depsdict["carch"].strip())
    commandline = commandline.replace("DISTRO", depsdict["cdist"].strip())
    
    msg = " Please install/configure \"" + depkey + "\" by issuing the following command: \""
    msg += commandline + "\"\n"
    
    return msg

def compare_versions(depkey, depsdict, version_b) :
    '''
    TBD
    '''
    version_a = depsdict[depkey + "-ver"]
    _non_decimal = re.compile(r'[^\d.]+')
    version_a = _non_decimal.sub('', version_a)
    version_b = _non_decimal.sub('', version_b)
    _version_a = map(int, re.sub('(\.0+)+\Z','', version_a).split('.'))
    _version_b = map(int, re.sub('(\.0+)+\Z','', version_b).split('.'))
    _result = cmp(_version_a,_version_b)
    if _result > 0 :
        return str(version_b) + " < " + str(version_a) + " NOT OK" 
    else :
        return str(version_b) + " >= " + str(version_a) + " OK"

def check_passwordless_sudo(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking passwordless sudo for the user \"" + username + "\" ....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("sudo -S ls < /dev/null")
                
        if not _status :
            _msg += "Passwordless sudo checked OK"
            _status = 0
        else :
            _status = 1728289

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :        
        _cmd = "echo \"" + username + "  ALL=(ALL:ALL) NOPASSWD:ALL\" >> /etc/sudoers;"
        _cmd += "sed -i s/\"Defaults requiretty\"/\"#Defaults requiretty\"/g /etc/sudoers"
        if _status :
            _msg += "This user does not have passwordless sudo capabilities.\n"
            _msg += "Please executed the following commands (as root) \"" + _cmd + "\""
        return _status, _msg

def check_git_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "git"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("git --version")

        if not _status and _result_stdout.count("git version") :
            _version = _result_stdout.replace("git version ",'').strip()
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_ip_utility(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "ip"

        _msg = "Checking \"" + _depkey + "\" utility....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("ip -V")
        if not _status :
            _msg += "OK"
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_ifconfig_utility(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "ifconfig"

        _msg = "Checking \"" + _depkey + "\" utility....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("ifconfig")
        if not _status :
            _msg += "OK"

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_screen_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "screen"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("screen -v")

        if not _status and _result_stdout.count("Screen version") :
            _version = _result_stdout.replace("Screen version",'').strip()
            _version = _version.split()[0]
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_rsync_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "rsync"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("rsync --version | grep version")

        if not _status and _result_stdout.count("protocol") :
            for _word in _result_stdout.split() :
                if _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_gmond_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "gmond"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("gmond --version")

        if not _status and _result_stdout.count("gmond") :
            for _word in _result_stdout.split() :
                if _word.count('.') >= 2 :
                    _parts = _word.split(".")
                    _version = _parts[0] + "." + _parts[1]
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_rsyslogd_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "rsyslog"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("rsyslogd -v")
                
        if not _status and _result_stdout.count("compiled with") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count(".") and not _word.count("//") :
                    _version = _word.replace(',','')
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_python_daemon_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "python-daemon"

        _msg = "Checking \"" + _depkey + "\" version....."
        import daemon

        _version = str(daemon._version).strip()
        del daemon

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0

    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_openvpn_binary(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "openvpn"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("openvpn --version")
                
        if not _status and _result_stdout.count("OpenVPN ") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_redis_binary(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "redis"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("redis-server -v")
                
        if not _status and _result_stdout.count("Redis server") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count("v=") :
                    _version = _word.replace("v=",'')
                    break
                elif _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_redis_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "pyredis"
        
        _msg = "Checking \"" + _depkey + "\" version....."
        import redis
        
        _version = str(redis.VERSION).replace('(','').replace(')','').replace(", ",'.').strip()
        del redis
        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_mongo_binary(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "mongodb"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("mongod --version")
        
        if not _status and _result_stdout.count("db version") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count("v") and not _word.count("version") :
                    _version = _word.replace('v','').replace(',','')
                    break

            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23
        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_python_setuptools(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "python-setuptools"

        _msg = "Checking \"" + _depkey + "\" library....."

        import setuptools 
        from setuptools import sandbox 
        
        del setuptools 

        _msg += "OK" 
        _status = 0
        
    except ImportError, e:
        _status = 7282
        
    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_mongo_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "pymongo"

        _msg = "Checking \"" + _depkey + "\" version....."
        import pymongo

        if pymongo.has_c() is False:
            msg = "WARNING: You do not have the pymongo C extensions " + \
                    "installed. Mongodb performance will be extermely slow. " + \
                     "To resolve this, please make sure you have the " + \
                     "'python-dev' or 'python-devel' development " + \
                     "headers installed and then *remove* and *reinstall* " + \
                     "the mongodb python bindings."
            print(msg)
        _version = str(pymongo.version).strip().replace('+','')
        del pymongo

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
        
    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_python_twisted_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "python-twisted"

        _msg = "Checking \"" + _depkey + "\" library....."
        import twisted
        from twisted.web.wsgi import WSGIResource
        from twisted.internet import reactor
        from twisted.web.static import File
        from twisted.web.resource import Resource
        from twisted.web.server import Site
        from twisted.web import wsgi
        
        _version = str(twisted.__version__).strip()
        del twisted
        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282


    except Exception, e :
        _status = 23


    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_python_webob(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "python-webob"

        _msg = "Checking \"" + _depkey + "\" library....."
        import webob
        from webob import Request, Response, exc
        _msg += "OK"
        #_version = str(webob.__version__).strip()
        del webob 
        #_msg += compare_versions('0.9.6', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_python_beaker(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "python-beaker"

        _msg = "Checking \"" + _depkey + "\" library....."
        import beaker 
        from beaker.middleware import SessionMiddleware
        _msg += "OK"

        #_version = str(beaker.__version__).strip()
        del beaker 
        #_msg += compare_versions('1.3.0', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_custom_gmetad(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "gmetad-python"

        _msg = "Checking \"" + _depkey + "\" library....."

        if access(path[0] + "/3rd_party/monitor-core/gmetad-python/gmetad.py", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_wizard(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "bootstrap-wizard"

        _msg = "Checking \"" + _depkey + "\" library....."

        if access(path[0] + "/3rd_party/Bootstrap-Wizard/README.md", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_streamprox(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "streamprox"

        _msg = "Checking \"" + _depkey + "\" library....."

        if access(path[0] + "/3rd_party/StreamProx/README.md", F_OK) :
            _version = "1.0.0"
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_d3(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "d3"

        _msg = "Checking \"" + _depkey + "\" library....."
        if access(path[0] + "/3rd_party/d3/component.json", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_bootstrap(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "bootstrap"

        _msg = "Checking \"" + _depkey + "\" library....."

        if access(path[0] + "/3rd_party/bootstrap/package.json", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_html_dot_py(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "pyhtml"

        _msg = "Checking \"" + _depkey + "\" library....."
        import HTML
        
        _version = str(HTML.__version__).strip()
        del HTML 

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7288

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_openstack_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "novaclient"

        _msg = "Checking \"" + _depkey + "\" library....."
        import novaclient
        
        _version = str(novaclient.__version__).strip() + ".g7ddc2fd"
        del novaclient

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_ec2_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "boto"

        _msg = "Checking \"" + _depkey + "\" library....."
        import boto
        
        _version = str(boto.__version__).strip().replace("-dev",'')
        del boto

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_omapi_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "pypureomapi"

        _msg = "Checking \"" + _depkey + "\" library....."
        import pypureomapi
        
        _version = str(pypureomapi.__version__).strip()
        del pypureomapi

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_libvirt_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _depkey = "pylibvirt"

        _msg = "Checking \"" + _depkey + "\" library....."
        import libvirt
        
        _version = str(libvirt.getVersion()).strip()
        del libvirt

        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_netcat(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "netcat"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("nc -v -w 1 localhost -z 22")

        if not _status :
            _version = "1.9"
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_libcloud_python_bindings(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "libcloud"

        _msg = "Checking \"" + _depkey + "\" library....."
        import libcloud
        
        _version = str(libcloud.__version__).replace("-dev",'').strip()
        del libcloud
        _msg += compare_versions(_depkey, depsdict, _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def check_R_version(hostname, username, proc_man, depsdict) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _depkey = "R"

        _msg = "Checking \"" + _depkey + "\" version....."
        _status, _result_stdout, _result_stderr = proc_man.run_os_command("R --version | grep version | grep -v GNU")

        if not _status and _result_stdout.count("version") :
            for _word in _result_stdout.split() :
                if _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions(_depkey, depsdict, _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)

    except Exception, e :
        _status = 23

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += inst_conf_msg(_depkey, depsdict)
        return _status, _msg

def dependency_checker(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    
    _func_pointer = {}
    _func_pointer["sudo"] = check_passwordless_sudo
    _func_pointer["git"] = check_git_version
    _func_pointer["screen"] = check_screen_version    
    _func_pointer["python-daemon"] = check_python_daemon_version    
    _func_pointer["python-twisted"] = check_python_twisted_version 
    _func_pointer["python-webob"] = check_python_webob 
    _func_pointer["python-beaker"] = check_python_beaker 
    _func_pointer["rsyslog"] = check_rsyslogd_version 
    _func_pointer["redis"] = check_redis_binary
    _func_pointer["openvpn"] = check_openvpn_binary
    _func_pointer["pyredis"] = check_redis_python_bindings
    _func_pointer["mongodb"] = check_mongo_binary
    _func_pointer["pymongo"] = check_mongo_python_bindings
    _func_pointer["python-setuptools"] = check_python_setuptools
    _func_pointer["gmetad-python"] = check_custom_gmetad
    _func_pointer["bootstrap"] = check_bootstrap
    _func_pointer["d3"] = check_d3
    _func_pointer["bootstrap-wizard"] = check_wizard
    _func_pointer["streamprox"] = check_streamprox
    _func_pointer["novaclient"] = check_openstack_python_bindings
    _func_pointer["pyhtml"] = check_html_dot_py
    _func_pointer["boto"] = check_ec2_python_bindings
    _func_pointer["rsync"] = check_rsync_version
    _func_pointer["gmond"] = check_gmond_version
    _func_pointer["pypureomapi"] = check_omapi_python_bindings
    _func_pointer["netcat"] = check_netcat
    _func_pointer["libcloud"] = check_libcloud_python_bindings
    _func_pointer["R"] = check_R_version
    _func_pointer["pylibvirt"] = check_libvirt_python_bindings
    _func_pointer["ip"] = check_ip_utility
    _func_pointer["ifconfig"] = check_ifconfig_utility
    
    _depsdict = {}
    
    deps_file_parser(_depsdict, username)
    
    _depsdict["cdist"], _depsdict["carch"] = get_linux_distro()
    _depsdict["3rdpartydir"] = trd_party_dir

    _proc_man =  ProcessManagement()

    for _dep in [ "sudo", "git" ]:
        _status, _msg = _func_pointer[_dep](hostname, username, _proc_man, _depsdict)
        print _msg
        if _status :
            _fmsg = _dep
            break

    try :
        if not _status :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
    
            _fmsg = ": "
    
            _dep_list = _func_pointer.keys()
            _dep_list.remove("sudo")
            _dep_list.remove("git")
            _dep_list.sort()
    
            _dep_missing = 0
            for _dep in _dep_list :
                _status, _msg = _func_pointer[_dep](hostname, username, _proc_man, _depsdict)
                print _msg
            
                if _status :
                    _dep_missing = 7181
                    _fmsg += _dep + ' ' 
    
                _status = _dep_missing

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
        _fmsg = str(obj.msg)

    except Exception, e :
        _status = 23
        _fmsg = str(e)
    
    finally :
        if _status :
            _msg = "One more dependencies are missing: " + _fmsg

        else :
            _msg = "All dependencies are in place"
        return _status, _msg