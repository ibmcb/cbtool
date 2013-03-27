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
from lib.remote.process_management import ProcessManagement

def compare_versions(version_a, version_b) :
    '''
    TBD
    '''
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

def check_passwordless_sudo(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking passwordless sudo for the user \"" + username + "\" ....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("sudo -S ls < /dev/null")
                
        if not _status :
            _msg += "Passwordless sudo checked OK"
            _status = 0
        else :
            _status = 1728289

        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status :
            _msg += "This user does not have passwordless sudo capabilities.\n"
            _msg += "Please add the line \"" + username + "           ALL=(ALL)       NOPASSWD: ALL\" "
            _msg += "to the sudoers file. \nAlso comment out the line \""
            _msg += "Defaults    requiretty\""
        return _status, _msg

def check_git_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking git version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("git --version")

        if not _status and _result_stdout.count("git version") :
            _version = _result_stdout.replace("git version ",'').strip()
            _msg += compare_versions('1.6.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status :
            _msg += "Please install git using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"git-core\"\n"
        return _status, _msg

def check_ip_utility(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking \"ip\" utility....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("ip -V")
        if not _status :
            _msg += "OK"
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status :
            _msg += "Please make sure that the \"ip\" utility can be executed (i.e., is the PATH correct?)\n"
        return _status, _msg

def check_ifconfig_utility(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking \"ifconfig\" utility....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("ifconfig")
        if not _status :
            _msg += "OK"

    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status :
            _msg += "Please make sure that the \"ifconfig\" utility can be executed (i.e., is the PATH correct?)\n"
        return _status, _msg

def check_screen_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking GNU screen version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("screen -v")

        if not _status and _result_stdout.count("Screen version") :
            _version = _result_stdout.replace("Screen version",'').strip()
            _version = _version.split()[0]
            _msg += compare_versions('4.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg = str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install screen using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"screen\"\n"
        return _status, _msg

def check_rsync_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking rsync version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("rsync --version | grep version")

        if not _status and _result_stdout.count("protocol") :
            for _word in _result_stdout.split() :
                if _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions('2.6', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg = str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install rsync using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"rsync\"\n"
        return _status, _msg

def check_gmond_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking gmond version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("gmond --version")


        if not _status and _result_stdout.count("gmond") :
            for _word in _result_stdout.split() :
                if _word.count('.') >= 2 :
                    _parts = _word.split(".")
                    _version = _parts[0] + "." + _parts[1]
                    break
            _msg += compare_versions('3.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg = str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install gmond using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"ganglia-monitor\"\n"
        return _status, _msg

def check_rsyslogd_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking rsyslog version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("rsyslogd -v")
                
        if not _status and _result_stdout.count("compiled with") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count(".") and not _word.count("//") :
                    _version = _word.replace(',','')
                    break
            _msg += compare_versions('4.6.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install rsyslogd using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"rsyslog\"\n"
        return _status, _msg

def check_python_daemon_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _msg = "Checking python-daemon library version....."
        import daemon

        _version = str(daemon._version).strip()
        del daemon

        _msg += compare_versions('1.5.1', _version)
        _status = 0

    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install python-daemon using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"python-daemon\"\n"
        return _status, _msg

def check_redis_binary(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking Redis version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("redis-server -v")
                
        if not _status and _result_stdout.count("Redis server") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count("v=") :
                    _version = _word.replace("v=",'')
                    break
                elif _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions('2.5.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install Redis with: cd " + trd_party_dir
            _msg += "; git clone https://github.com/ibmcb/redis.git; "
            _msg += "cd redis; git checkout 2.6; make; sudo make install\n"
        return _status, _msg

def check_redis_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking Redis python bindings version....."
        import redis
        
        _version = str(redis.VERSION).replace('(','').replace(')','').replace(", ",'.').strip()
        del redis
        _msg += compare_versions('2.6.0', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install Redis python bindings with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/redis-py.git;"
            _msg += "cd redis-py; sudo python setup.py install\n"           
        return _status, _msg

def check_mongo_binary(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking MongoDB version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("mongod --version")
        
        if not _status and _result_stdout.count("db version") :
            _version = "N/A"
            for _word in _result_stdout.split() :
                if _word.count("v") and not _word.count("version") :
                    _version = _word.replace('v','').replace(',','')
                    break

            _msg += compare_versions('2.0.0', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg += str(obj.msg)"

    except Exception, e :
        _status = 23
        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            if len('%x'%sys.maxint) == 8 :
                _mongo_url = "http://fastdl.mongodb.org/linux/mongodb-linux-i686-2.2.2.tgz"
            else :
                _mongo_url = "http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-2.2.2.tgz"

            _msg += " Please install MongoDB with: cd " + trd_party_dir
            _msg += "; wget " + _mongo_url + "; tar -zxf mongodb-linux-*.tgz; cd mongodb-linux-*; sudo cp bin/* /usr/bin\n"
            _msg += "If you have a different machine architecture, you will have to download the binaries from http://www.mongodb.org/downloads\n"

        return _status, _msg

def check_python_setuptools(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking for python-setuptools....."
        import setuptools 
        from setuptools import sandbox 
        
        del setuptools 

        _msg += "OK" 
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)
        
    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install setuptools with: This is usually under the package name 'python-setuptools' (yum or apt-get)\n"
        return _status, _msg

def check_mongo_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking MongoDB python bindings version....."
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

        _msg += compare_versions('2.1.1', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)
        
    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install MongoDB python bindings with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/mongo-python-driver.git;"
            _msg += "cd mongo-python-driver; sudo python setup.py install\n"    
        return _status, _msg

def check_python_twisted_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking python-twisted library version....."
        import twisted
        from twisted.web.wsgi import WSGIResource
        from twisted.internet import reactor
        from twisted.web.static import File
        from twisted.web.resource import Resource
        from twisted.web.server import Site
        from twisted.web import wsgi
        
        _version = str(twisted.__version__).strip()
        del twisted
        _msg += compare_versions('8.0.0', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install twisted using you package management system (yum or apt-get)."
            _msg += " The packages are usually called \"python-twisted-web\"\n"       
        return _status, _msg

def check_python_webob(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking python-webob library....."
        import webob
        from webob import Request, Response, exc
        _msg += "OK"
        #_version = str(webob.__version__).strip()
        del webob 
        #_msg += compare_versions('0.9.6', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install python-webob using you package management system (yum or apt-get)."
            _msg += " The packages are usually called \"python-webob\"\n"       
        return _status, _msg

def check_python_beaker(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking python-beaker library..... "
        import beaker 
        from beaker.middleware import SessionMiddleware
        _msg += "OK"

        #_version = str(beaker.__version__).strip()
        del beaker 
        #_msg += compare_versions('1.3.0', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install python-beaker using you package management system (yum or apt-get)."
            _msg += " The packages are usually called \"python-beaker\"\n"       
        return _status, _msg

def check_custom_gmetad(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _proc_man =  ProcessManagement()
        _msg = "Checking custom gmetad version....."

        if access(path[0] + "/3rd_party/monitor-core/gmetad-python/gmetad.py", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions('1.0.0', _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install the custom gmetad with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/monitor-core.git\n"    
        return _status, _msg

def check_wizard(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _proc_man =  ProcessManagement()
        _msg = "Checking wizard version....."

        if access(path[0] + "/3rd_party/Bootstrap-Wizard/README.md", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions('1.0.0', _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install Bootstrap-Wizard with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/Bootstrap-Wizard.git\n"
        return _status, _msg

def check_d3(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _proc_man =  ProcessManagement()
        _msg = "Checking d3 version....."

        if access(path[0] + "/3rd_party/d3/component.json", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions('1.0.0', _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install d3 with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/d3.git\n"
        return _status, _msg

def check_bootstrap(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _proc_man =  ProcessManagement()
        _msg = "Checking bootstrap version....."

        if access(path[0] + "/3rd_party/bootstrap/package.json", F_OK) :
            _version = "1.0.0"

            _msg += compare_versions('1.0.0', _version)
            _status = 0
        else :
            _status = 1728289

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install bootstrap with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/ibmcb/bootstrap.git\n"          
        return _status, _msg

def check_openstack_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking OpenStack python bindings (novaclient) version....."
        import novaclient
        
        _version = str(novaclient.__version__).strip() + ".g7ddc2fd"
        del novaclient

        _msg += compare_versions('2.2.5', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install OpenStack python bindings with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/openstack/python-novaclient.git;"
            _msg += "cd python-novaclient; sudo python setup.py install\n"    
        return _status, _msg

def check_ec2_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking EC2 python bindings (boto) version....."
        import boto
        
        _version = str(boto.__version__).strip().replace("-dev",'')
        del boto

        _msg += compare_versions('2.1.8', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install EC2 python bindings with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/boto/boto.git;"
            _msg += "cd boto; sudo python setup.py install\n"
        return _status, _msg

def check_omapi_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking OMAPI python bindings version....."
        import pypureomapi
        
        _version = str(pypureomapi.__version__).strip()
        del pypureomapi

        _msg += compare_versions('0.2', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install OMAPI python bindings with: cd "
            _msg += trd_party_dir + "; wget http://pypureomapi.googlecode.com/files/pypureomapi-0.3.tar.gz;"
            _msg += " tar -xzvf pypureomapi-0.3.tar.gz; cd pypureomapi-0.3; "
            _msg += "sudo python setup.py install\n"
        return _status, _msg

def check_libvirt_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking libvirt python bindings version....."
        import libvirt
        
        _version = str(libvirt.getVersion()).strip()
        del libvirt

        _msg += compare_versions('9003', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install libvirt python bindings using you package management system (yum or apt-get)."
            _msg += " The packages are usually called \"libvirt-python\" or \"python-libvirt\"\n"       
        return _status, _msg

def check_netcat(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking netcat (openbsd) version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("nc -v -w 1 localhost -z 22")

        if not _status :
            _version = "1.9"
            _msg += compare_versions('1.6', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg = str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install nc using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"netcat-openbsd\", \" netcat \""
            _msg += " or simply \"nc\".\n"
        return _status, _msg

def check_libcloud_python_bindings(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _msg = "Checking libcloud python bindings version....."
        import libcloud
        
        _version = str(libcloud.__version__).replace("-dev",'').strip()
        del libcloud
        _msg += compare_versions('0.11.0', _version)
        _status = 0
        
    except ImportError, e:
        _status = 7282
#        _msg += str(e)

    except Exception, e :
        _status = 23
#        _msg += str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install LibCloud python bindings with: cd "
            _msg += trd_party_dir + "; git clone https://github.com/apache/libcloud.git;"
            _msg += "cd libcloud; sudo python setup.py install\n"           
        return _status, _msg

def check_R_version(hostname, username, trd_party_dir) :
    '''
    TBD
    '''
    try:
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"
        
        _proc_man =  ProcessManagement()
        _msg = "Checking R version....."
        _status, _result_stdout, _result_stderr = _proc_man.run_os_command("R --version | grep version | grep -v GNU")

        if not _status and _result_stdout.count("version") :
            for _word in _result_stdout.split() :
                if _word.count('.') == 2 :
                    _version = _word
                    break
            _msg += compare_versions('2.1', _version)
            _status = 0
        else :
            _status = 1728289
        
    except ProcessManagement.ProcessManagementException, obj :
        _status = str(obj.status)
#        _msg = str(obj.msg)

    except Exception, e :
        _status = 23
#        _msg = str(e)

    finally :
        if _status or _msg.count("NOT OK"):
            _msg += " Please install R using you package management system (yum or apt-get)."
            _msg += " The package is usually called \"R\" or \"r-base\"\n"
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
    _func_pointer["redis-py"] = check_redis_python_bindings
    _func_pointer["mongo"] = check_mongo_binary
    _func_pointer["pymongo"] = check_mongo_python_bindings
    _func_pointer["python-setuptools"] = check_python_setuptools
    _func_pointer["monitor-core"] = check_custom_gmetad
    _func_pointer["bootstrap"] = check_bootstrap
    _func_pointer["d3"] = check_d3
    _func_pointer["wizard"] = check_wizard
    _func_pointer["novaclient"] = check_openstack_python_bindings
    _func_pointer["boto"] = check_ec2_python_bindings
    _func_pointer["rsync"] = check_rsync_version
    _func_pointer["ganglia"] = check_gmond_version
    _func_pointer["pypureomapi"] = check_omapi_python_bindings
    _func_pointer["netcat"] = check_netcat
    _func_pointer["libcloud"] = check_libcloud_python_bindings
    _func_pointer["R"] = check_R_version
    _func_pointer["libvirt"] = check_libvirt_python_bindings
    _func_pointer["ip"] = check_ip_utility
    _func_pointer["ifconfig"] = check_ifconfig_utility
                
    for _dep in [ "sudo", "git" ]:
        _status, _msg = _func_pointer[_dep](hostname, username, trd_party_dir)
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
                _status, _msg = _func_pointer[_dep](hostname, username, trd_party_dir)
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
