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
    Created on Oct 25, 2012

    Dependency Checker/Installer

    @author: Marcio A. Silva, Michael R. Galaxy
'''
from sys import path
import sys
import os
import re
import platform
import traceback

from os.path import expanduser
home = expanduser("~")

from json import dumps
from lib.remote.process_management import ProcessManagement
from lib.auxiliary.data_ops import cmp
from lib.auxiliary.code_instrumentation import  VerbosityFilter, MsgFilter, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import check_url

try:
    import distro
except ModuleNotFoundError as e:
    if sys.version_info.major > 2 and sys.version_info.minor >= 7:
        _msg = (
            "Python version 3.7 and higher require `distro` package to be installed. "
            "Version: %s" % platform.python_version()
        )
        cberr(_msg)
        raise e
    pass

def deps_file_parser(depsdict, username, options, hostname, process_manager = False) :
    '''
    TBD
    '''

    _file_name_list = []

    _file_name_list.append(options.defdir + "/PUBLIC_dependencies.txt")

    _cleanup_repos = False
    if len(options.wks) > 1 :
        _workloads_list = options.wks.split(',')        
        for _workload in _workloads_list :
            _file_name_list.append(options.wksdir + '/'  + _workload + "/dependencies.txt")
        _cleanup_repos = True

    _file_name_list.append(options.defdir + "/IBM_dependencies.txt")
    _file_name_list.append(options.defdir + "/SPEC_dependencies.txt")
    
    if len(options.custom) :
        _file_name_list.append(options.cusdir + '/' + options.custom)

    print('\n')
    
    for _file in _file_name_list :
        if os.access(_file, os.F_OK) :

            try:
                _fd = open(_file, 'r')
                _fc = _fd.readlines()
                _fd.close()
                _msg = "##### File \"" + _file + "\" opened and loaded...."
                cbinfo(_msg)

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
        
            except Exception as e :
                _msg = "##### Error reading file \"" + _file  + "\":" + str(e)
                cberr(_msg)
                exit(4)

        else :
            _msg = "##### File \"" + _file + "\" IGNORED...."
            cbwarn(_msg)

    if not len(depsdict) :
        _msg = "##### None of the files on the list \"" + str(_file_name_list)
        _msg += "\" contained configuration statements"
        cberr(_msg)
        exit(9)

    if _cleanup_repos :
        if not process_manager :
            process_manager = ProcessManagement(hostname)
        
        process_manager.run_os_command("sudo rm -rf /tmp/repoupdated", False)

    return True

def get_dep_key_from_docker_file(line, key_prefix, depsdict) :
    '''
    TBD
    '''
    if line.count("#") and line.count("-install-") : 
        if line.count("ARCH") :
            if line.split('-')[1].replace("ARCH",'') == depsdict["carch"] :
                return key_prefix + '-' + line.replace("#",'').replace("-ARCH" + depsdict["carch"],'').strip()
            else :
                return False
        else :
            return key_prefix + '-' + line.replace("#",'').strip()

def docker_file_parser(depsdict, username, options, hostname, process_manager = False) :
    '''
    TBD
    '''
    _workloads_list = []
    
    if options.role.count("orchestrator") :
        _workloads_list = [ "orchestrator", "orchprereqs" ]
        _role_list = [ options.role, "orchprereqs" ]
        
    if len(options.wks) > 1 :
        _workloads_list = options.wks.split(',')
        _role_list = [ options.role ]

    print('\n')

    for _role in _role_list :    
        for _path, _dirs, _files in os.walk(options.dfdir + '/' + _role) :
            for _fnam in _files:
                _full_fnam = os.path.join(_path, _fnam)
                if not _fnam.count("._processed_") and _fnam.count("Dockerfile-") and os.access(_full_fnam, os.F_OK) :            
    
                    _x_fnam = _fnam.replace("Dockerfile-",'').split('_')
                    _key_prefix = _x_fnam[0]
                    _f_workload = _x_fnam[2]
    
                    if len(_x_fnam) > 3 :
                        _f_workload += '_' + _x_fnam[3]
                    
                    if _f_workload in _workloads_list :
                        try:
                            _fd = open(_full_fnam, 'r')
                            _fc = _fd.readlines()
                            _fd.close()
                            _msg = "##### Parsing Dockerfile \"" + _full_fnam + "\"...."
                            cbinfo(_msg)
        
                            _current_key = None
                            
                            for _line in _fc :
                                _line = _line.strip()
            
                                if _current_key :
                                    
                                    _detected_key = get_dep_key_from_docker_file (_line, _key_prefix, depsdict) 
                                    if _detected_key :
                                        depsdict[_current_key] = depsdict[_current_key][0:-1]

                                        if _current_key.count("centos-") :
                                            depsdict[_current_key.replace("centos-","rhel-")] = depsdict[_current_key]
                                            depsdict[_current_key.replace("centos-","fedora-")] = depsdict[_current_key]                                                                                
                                        _current_key = None
    
                                    else :
                                        if _line.count("#") and _line.count("RUN") :
                                            True
                                        else :
                                            _line = _line.replace("RUN apt-get install -y","package_install")
                                            _line = _line.replace("RUN yum install -y","package_install")
                                            _line = _line.replace("RUN pip3 install --upgrade", "sudo pip3 install --upgrade INDEXURL")
                                            _line = _line.replace("RUN git", "git")
                                            _line = _line.replace("; apt install", "; sudo apt install")                                            
                                            _line = _line.replace("; apt-get install", "; sudo apt-get install")
                                            _line = _line.replace("; apt-get update", "; sudo apt-get update")                                    
                                            _line = _line.replace("; add-apt-repository", "; sudo add-apt-repository")                                    
                                            _line = _line.replace("; dpkg", "; sudo dpkg")
                                            _line = _line.replace("; sed", "; sudo sed")                                            
                                            _line = _line.replace("; yum install", "; sudo yum install")
                                            _line = _line.replace("; rpm", "; sudo rpm")
                                            _line = _line.replace("; chown", "; sudo chown")
                                            _line = _line.replace("; make install", "; sudo make install")
                                            _line = _line.replace("RUN mkdir -p /home/REPLACE_USERNAME/cbtool/3rd_party", "mkdir -p 3RPARTYDIR")
                                            _line = _line.replace("RUN ", "sudo ")
                                            _line = _line.replace("ENV ", "export ")                                  
                                            _line = _line.replace("sudo cd ", "cd ")
                                            _line = _line.replace("sudo export", "export ")
                                            _line = _line.replace("sudo sudo ", "sudo ")
                                            _line = _line.replace("sudo if ", "if ")
                                            _line = _line.replace("sudo REPLACE_RSYNC", "REPLACE_RSYNC")
                                            _line = _line.replace("apt-get update", "apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update")
                                            _line = _line.replace("WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party", "cd 3RPARTYDIR")
                                            _line = _line.replace("# service_stop_disable", "service_stop_disable")
                                            _line = _line.replace("# /tmp/cb_is_java_installed.sh", "/tmp/cb_is_java_installed.sh")
                                            _line = _line.replace("# echo", "echo")
                                            _line = _line.replace("/home/root", "/root")
                                            _line = _line.replace("____",' ')
                                            depsdict[_current_key] += _line + "; "
            
                                else :
                                    _detected_key = get_dep_key_from_docker_file (_line, _key_prefix, depsdict) 
                                    if _detected_key :
                                        _current_key = _detected_key
                                        depsdict[_current_key] = ''
            
                        except Exception as e :
                            _msg = "##### Error reading file \"" + _full_fnam  + "\":" + str(e)
                            cberr(_msg)
                            exit(4)

    return True

def preparation_file_parser(depsdict, username, options, hostname, process_manager = False) :
    '''
    TBD
    '''
    _file = home + "/cb_prepare_parameters.txt"

    print('\n')

    if os.access(_file, os.F_OK) :

        _msg = "##### Parsing CB file \"" + _file + "\"...."
        cbinfo(_msg)
        
        _fd = open(_file, 'r')
        _fc = _fd.readlines()
        _fd.close()

        if "stores" not in depsdict :
            depsdict["stores"] = []

        for _line in _fc :
            _line = _line.strip()

            _store, _store_ip, _store_port, _store_protocol, _store_username = _line.split()
                        
            _cmd = "nc -z -w 3 -" + _store_protocol[0].lower() + ' ' + _store_ip + ' ' + _store_port

            if _store not in depsdict["stores"] :
                depsdict["stores"].append(_store) 

            depsdict[_store + "_ip"] = _store_ip
            depsdict[_store + "_port"] = _store_port
            depsdict[_store + "_protocol"] = _store_protocol
            depsdict[_store + "_username"] = _store_username                                                 
            depsdict[_store + "_command_check"] = _cmd

    return True
    
def get_linux_distro() :
    '''
    TBD
    '''
    try:
        _linux_distro_kind, _linux_distro_ver, _linux_distro_name = platform.linux_distribution()
    except AttributeError:
        _linux_distro_kind = distro.name()
        _linux_distro_ver = distro.version()
        _linux_distro_name = distro.id()

    if _linux_distro_kind.count("Red Hat") :
        _linux_distro_kind = "rhel"
    elif _linux_distro_kind.count("Scientific Linux") :
        _linux_distro_kind = "rhel"        
    elif _linux_distro_kind.count("CentOS") :
        _linux_distro_kind = "rhel"        
    elif _linux_distro_kind.count("Ubuntu") :
        _linux_distro_kind = "ubuntu"
    elif _linux_distro_kind.count("Fedora") :
        _linux_distro_kind = "fedora"
    else :
        _msg = "\nUnsupported distribution (" + _linux_distro_kind + ")\n"
        raise Exception(_msg)

    _linux_distro_name = _linux_distro_name.lower()

    _linux_major_ver = _linux_distro_ver.split('.')[0]
       
    _arch = platform.processor()

#    if _linux_distro_kind == "ubuntu" and _arch == "x86_64" :
#        _arch = "amd64"

    return _linux_distro_kind, _linux_distro_ver, _linux_major_ver, _linux_distro_name, _arch

def get_cmdline(depkey, depsdict, operation, process_manager = False, exception_if_no_url = False) :
    ''' 
    TBD
    '''

    if operation != "configure" :
        if depsdict[depkey + '-' + operation] == "man" :

            _urls_key = depsdict["cdistnam"] + '-' + depkey + '-' + depsdict["carch"] + "-urls-" + depsdict[depkey + '-' + operation]            

            if _urls_key not in depsdict :
                _urls_key = depsdict["cdistkind"] + '-' + depkey + '-' + depsdict["carch"] + "-urls-" + depsdict[depkey + '-' + operation]

                if _urls_key not in depsdict :            
                    _urls_key = "common-" + depkey + '-' + depsdict["carch"] + "-urls-" + depsdict[depkey + '-' + operation]
                            
                    if _urls_key not in depsdict :
                        _urls_key = False
        else :

            _urls_key = depsdict["cdistnam"] + '-' + depkey + "-urls-" + depsdict[depkey + '-' + operation]            

            if _urls_key not in depsdict :            
                _urls_key = depsdict["cdistkind"] + '-' + depkey + "-urls-" + depsdict[depkey + '-' + operation]            

                if _urls_key not in depsdict :               
                    _urls_key = "common-" + depkey + "-urls-" + depsdict[depkey + '-' + operation]

                    if _urls_key not in depsdict :
                        _urls_key = False                

    else :
        _urls_key = False
    
    if _urls_key :
        if len(depsdict[_urls_key]) > 7 :
            _tested_urls = ''
            _actual_url = False
            for _url in depsdict[_urls_key].split(',') :
    
                if depsdict["repo_addr"] :
                    _url = _url.replace("REPO_ADDR", depsdict["repo_addr"])
    
                _url = _url.replace("REPO_RELEASE", depsdict["cdistver"])
                _url = _url.replace("REPO_MAJOR_RELEASE", depsdict["cdistmajorver"])                
                _url = _url.replace("REPO_ARCH", depsdict["carch"])            
                _url = _url.replace("ARCH", depsdict["carch"].strip())
                _url = _url.replace("DISTRO", depsdict["cdistkind"].strip())
                _url = _url.replace("USERNAME", depsdict["username"].strip())
                
                if check_url(_url, "ARCH", depsdict["carch"]) :
                    _actual_url = _url
                    break
                else :
                    if not _tested_urls.count(_url) :
                        _tested_urls += _url + ','
    
            if not _actual_url :
                _msg = "##### None of the urls indicated to install \"" + depkey + "\" (" 
                _msg += _tested_urls + ") seem to be functional."

                if exception_if_no_url :
                    raise Exception(_msg)
                else :
                    cbwarn(_msg)
        else :
            _actual_url = False                
    else :
        _actual_url = False

    _actual_cmdline = ""
    _actual_cmdline_keys = ''
    
    if operation == "install" :
        for _sub_step in [ "preinstall", "install", "postinstall"] :

            _commandline_keys = []

            _commandline_keys.append(depsdict["cdistnam"] + '-' + depkey + '-' + _sub_step + '-' + depsdict[depkey + '-' + operation])
            _commandline_keys.append(depsdict["cdistkind"] + '-' + depkey + '-' + _sub_step + '-' + depsdict[depkey + '-' + operation])
            _commandline_keys.append("common-" + depkey + '-' + _sub_step + '-' + depsdict[depkey + '-' + operation])

            _x, _y = get_actual_cmdline(_commandline_keys, depsdict, _actual_url)

            _actual_cmdline_keys += _x + ','
            
            _actual_cmdline += _y + ';'

    else :
        _commandline_keys = [ depkey + '-' + operation ]
        
        _x, _y = get_actual_cmdline(_commandline_keys, depsdict, _actual_url)

        _actual_cmdline_keys += _x + ','
        _actual_cmdline += _y + ';'

    if _actual_cmdline_keys[0] == ',' :
        _actual_cmdline_keys = _actual_cmdline_keys[1:]
        
    if _actual_cmdline_keys[-1] == ',' :
        _actual_commandline_keys = _actual_cmdline_keys[0:-1]
        
    if _actual_cmdline[0] == ';' :
        _actual_cmdline = _actual_cmdline[1:]

    if _actual_cmdline[-1] == ';' :
        _actual_cmdline = _actual_cmdline[0:-1]

    _actual_cmdline = expand_command(_actual_cmdline, depsdict, process_manager)

    _actual_cmdline_keys = _actual_cmdline_keys.replace(",,",',')
    _actual_cmdline_keys = _actual_cmdline_keys.replace(",,",',')    
    _actual_cmdline_keys = _actual_cmdline_keys.replace("_equal_",'=')

    _actual_cmdline = _actual_cmdline.replace(";;",';')
    _actual_cmdline = _actual_cmdline.replace(";;",';')
    _actual_cmdline = _actual_cmdline.replace(";;",';')
    _actual_cmdline = _actual_cmdline.replace("; ;",';')

    if len(_actual_cmdline) == 1 :
        _msg = "######## Error! The command to  " + operation + " the dependency " +  depkey + " is empty!"
        cberr(_msg)
        exit(4)

    while _actual_cmdline[0] == ';' :
        _actual_cmdline = _actual_cmdline[1:]

    _actual_cmdline = _actual_cmdline.replace("_equal_",'=')

    return _actual_commandline_keys, _actual_cmdline

def expand_command(cmdline, depsdict, process_manager = False) :
    '''
    TBD
    '''
    _actual_cmdline = ''

    for _command in cmdline.split(';') :
            
        if _command.count("package_install") :
            _packages = _command.replace("package_install",'')
            
            if depsdict["cdistkind"] == "ubuntu" :
                if _packages.count(".deb") :
                    _command = "sudo dpkg -i PACKAGES; sudo apt-get -f install --yes --allow-unauthenticated "
                else :
                    _command = "sudo DEBIAN_FRONTEND=noninteractive apt-get -q --yes --allow-unauthenticated -o Dpkg::Options::=\"--force-confnew\" install PACKAGES"
                    
            elif depsdict["cdistkind"] == "rhel" or depsdict["cdistkind"] == "fedora"  :
                if _packages.count(".rpm") :
                    _command = "sudo rpm -i PACKAGES"
                else :
                    _command = "sudo yum -y install PACKAGES"
                                    
            _command = _command.replace("PACKAGES", _packages)

        if _command.count("sudo pip3 ") :
            if depsdict["indocker"] :
                _command = _command.replace("sudo pip3", "export LC_ALL=C; sudo pip3") 

        if _command.count("IF DOCKER") :
            if depsdict["indocker"] :
                _command = "/bin/true"            
            else :
                _command = _command.replace("IF DOCKER", '') 
                                
        if _command.count("service_restart_enable") or _command.count("service_stop_disable") :

            if not process_manager :
                process_manager = ProcessManagement()            
            
            if _command.count("service_restart_enable") :
                _services = _command.replace("service_restart_enable",'')
    
            if _command.count("service_stop_disable") :
                if depsdict["indocker"] :
                    _services = ''
                else :
                    _services = _command.replace("service_stop_disable",'')

            _command = ''    
            for _service in _services.split() :

                _status = 20000
                _result_stdout = "NA"
                _result_stderr = "NA"

                _status, _result_stdout, _result_stderr = \
                process_manager.run_os_command("sudo systemctl status " + _service, \
                                               raise_exception = False)

                if not _status :
                    if cmdline.count("service_restart_enable") :            
                        _service_cmd="sudo systemctl restart SERVICE; sudo systemctl enable SERVICE"
        
                    if cmdline.count("service_stop_disable") :            
                        _service_cmd="sudo systemctl stop SERVICE; sudo systemctl disable SERVICE"
                else :
                    if cmdline.count("service_restart_enable") :
                        _service_cmd="sudo service SERVICE restart;"
                        
                        if depsdict["cdistkind"] == "rhel" or depsdict["cdistkind"] == "fedora" :
                            _service_cmd += "sudo chkconfig SERVICE on;"
        
                        elif depsdict["cdistkind"] == "ubuntu" :
                            if os.access("/etc/init/" + _service + ".conf", os.F_OK) :
                                _service_cmd += "sudo rm -rf /etc/init/SERVICE.override"
                            else :
                                _service_cmd += "sudo update-rc.d -f SERVICE defaults"
                                                        
                    if cmdline.count("service_stop_disable") :            
                        _service_cmd="sudo systemctl SERVICE stop; sudo chkconfig SERVICE off;"            
        
                        if depsdict["cdistkind"] == "rhel" or depsdict["cdistkind"] == "fedora" :
                            _service_cmd = "sudo chkconfig SERVICE off;"
                            
                        elif depsdict["cdistkind"] == "ubuntu" :
                            if os.access("/etc/init/" + _service + ".conf", os.F_OK) :
                                _service_cmd = "sudo sh -c 'echo manual > /etc/init/SERVICE.override'"
                            else :
                                _service_cmd = "sudo update-rc.d -f SERVICE remove"

                _service_cmd = _service_cmd.replace("SERVICE", _service) + ';'
                
                _command += _service_cmd

        _actual_cmdline += _command + ';'        
    
    return _actual_cmdline

def get_actual_cmdline(commandline_keys, depsdict, _actual_url) :
    '''
    TBD
    '''
    _commandline = ''

    for _commandline_key in commandline_keys :
        if _commandline_key in depsdict :

            _commandline = depsdict[_commandline_key]
            _commandline = _commandline.replace("3RPARTYDIR", depsdict["3rdpartydir"].strip().replace("//",'/'))
            _commandline = _commandline.replace("SCRIPTSDIR", depsdict["scriptsdir"].strip().replace("//",'/'))        
            _commandline = _commandline.replace("CREDENTIALSDIR", depsdict["credentialsdir"].strip().replace("//",'/'))
            if _actual_url :
                _commandline = _commandline.replace("URL", _actual_url.strip())
            _commandline = _commandline.replace("REPLACE_ARCH1", depsdict["carch1"].strip())
            _commandline = _commandline.replace("REPLACE_ARCH2", depsdict["carch2"].strip())
            _commandline = _commandline.replace("REPLACE_ARCH3", depsdict["carch3"].strip())
            _commandline = _commandline.replace("REPLACE_ARCH4", depsdict["carch4"].strip())            
            _commandline = _commandline.replace("ARCH", depsdict["carch"].strip())            
            _commandline = _commandline.replace("DISTRO", depsdict["cdistkind"].strip())
            _commandline = _commandline.replace("REPLACE_USERNAME", depsdict["username"].strip())            
            _commandline = _commandline.replace("/home/root", "/root")       
            _commandline = _commandline.replace("USERNAME", depsdict["username"].strip())
            _commandline = _commandline.replace("REPLACE_RSYNC", "rsync --inplace -a rsync://" + depsdict["Filestore_ip"] + ':' + depsdict["Filestore_port"] + '/' + depsdict["Filestore_username"] + "_cb/3rd_party/workload/")

            if depsdict["pip_addr"] :
                _commandline = _commandline.replace("INDEXURL", "--index-url=http://" + depsdict["pip_addr"] + " --trusted-host " + depsdict["pip_addr"].split('/')[0] + ' ')
            else :
                _commandline = _commandline.replace("INDEXURL", '')
            return _commandline_key, _commandline
        
    return '', _commandline

def select_url(source, depsdict) :
    '''
    TBD
    '''
    depsdict[source + "_addr_list"] = []

    depsdict[source + "_addr"] = False

    if source == "repo" :
        _element = "package repository"
    else :
        _element = "python pip repository"

    print('\n')
    _msg = "Selecting " + _element + " address...." 
    cbinfo(_msg)
    
    for _key in sorted(depsdict.keys()) :
        if _key.count(source + "-addr") :
            _index = int(_key.replace(source + "-addr",''))
            depsdict[source + "_addr_list"].insert(_index, depsdict[_key])

    for _repo_addr in depsdict[source + "_addr_list"] :
        if check_url("http://" + _repo_addr, "ARCH", depsdict["carch"]) :
            depsdict[source + "_addr"] = _repo_addr
    
    if len(depsdict[source + "_addr_list"]) :
        if depsdict[source + "_addr"] :
            _msg = "A " + _element + " in \"" + depsdict[source + "_addr"] + "\" seems to be up"
            depsdict[source + "_dropbox"] = "http://" + depsdict[source + "_addr"] + "/dropbox"
            depsdict[source + "_credentials_url"] = "http://" + depsdict[source + "_addr"] + "/dropbox/ssh_keys"
            cbinfo(_msg)
        else :
            _msg = "##### None of the indicated " + _element + " was available. ".replace("repository","repositories")
            if source == "repo" :
                _msg += "Will ignore any repository URL that has the keyword REPO_ADDR..."
            cbwarn(_msg)
    else :
        _msg = "##### No " + _element + " specified. ".replace("repository","repositories")
        if source == "repo" :
            _msg += "Will ignore any repository URL that has the keyword REPO_ADDR..."
        cbwarn(_msg)
    
    return True

def build_repository_file_contents(depsdict, repo_name) :
    '''
    TBD
    '''
    _msg = "Configuring repository \"" + repo_name +"\"..."
    cbinfo(_msg)
    
    _file_contents = ""

    if "local-url" in depsdict["repo_contents"][repo_name] :
        
        if len(depsdict["repo_contents"][repo_name]["local-url"]) :
            
            if not depsdict["repo_addr"] and \
            depsdict["repo_contents"][repo_name]["local-url"].count("REPO_ADDR") :

                _actual_url = depsdict["repo_contents"][repo_name]["original-url"]

            else :

                _actual_url = depsdict["repo_contents"][repo_name]["local-url"]
    else :
        _actual_url = depsdict["repo_contents"][repo_name]["original-url"]

    if depsdict["repo_addr"] :
        _actual_url = _actual_url.replace("REPO_ADDR", depsdict["repo_addr"])
        _actual_url = _actual_url.replace("REPO_RELEASE", depsdict["cdistver"])
        _actual_url = _actual_url.replace("REPO_MAJOR_RELEASE", depsdict["cdistmajorver"])
        _actual_url = _actual_url.replace("REPO_ARCH", depsdict["carch"])
        
    if not check_url(_actual_url, "ARCH", depsdict["carch"]) :
        _tested_urls = _actual_url

        _actual_url = depsdict["repo_contents"][repo_name]["original-url"]

        if not check_url(_actual_url, "ARCH", depsdict["carch"]) :
            if not _tested_urls.count(_actual_url) :
                _tested_urls += ',' + _actual_url
            _actual_url = False

    if _actual_url :            
        _msg = "Valid URL found: " + _actual_url + "."
        cbinfo(_msg)
    else :
        _msg = "No URLs available for repository \"" + repo_name 
        _msg += "\" (" + _tested_urls + ")." + " Will ignore this repository"
        _msg += ", but this might cause installation errors due to a lacking on certain dependencies"        
        cbwarn(_msg)
        return False

    if depsdict["cdistkind"] == "ubuntu" :
        for _dist in depsdict["repo_contents"][repo_name]["dists"].split(',') :
            for _component in depsdict["repo_contents"][repo_name]["components"].split(',') :
                _file_contents += "deb " + _actual_url + ' ' + _dist + ' ' + _component + "\n"
    else :
        _file_contents += "[" + repo_name + "]\n"
        _file_contents += "name = " + repo_name + "\n"        
        _file_contents += "baseurl = " + _actual_url + "\n"

        for _attr in [ "enabled", "skip_if_unavailable", "priority", "gpgcheck" ] :
            _file_contents += _attr + " = " + depsdict["repo_contents"][repo_name][_attr] + "\n"

        if  depsdict["repo_contents"][repo_name]["gpgcheck"] == "0" :
            True
        else :
            _file_contents += "gpgkey = " + depsdict["repo_contents"][repo_name]["gpgkey"] + "\n"


    return _file_contents

def build_repository_files(depsdict) :
    '''
    TBD
    '''
    build_repository_contents(depsdict)

    if depsdict["cdistkind"] == "ubuntu" :
        _file_extension = ".list"
        _repo_dir = "/etc/apt/sources.list.d/"
        _file_lines = []
    else :
        _file_extension = ".repo"
        _repo_dir = "/etc/yum.repos.d/"

    if "repos_" + depsdict["cdistkind"] in depsdict :        
        _repo_list = depsdict["repos_" + depsdict["cdistkind"]]
    else :
        _repo_list = []

    for _repo in _repo_list :
        
        _file_contents = build_repository_file_contents(depsdict, _repo)
        
        if _file_contents :
            try:
                _file_name = "/tmp/" + _repo + _file_extension
                _file_descriptor = file(_file_name, 'w')
                _file_descriptor.write(_file_contents)
                _file_descriptor.close()
                os.chmod(_file_name, 0o755)

            except IOError as msg :
                _msg = "######## Error writing file \"" + _file_name  + "\":" + str(msg)
                cberr(_msg)
                exit(4)

            except OSError as msg :
                _msg = "######## Error writing file \"" + _file_name  + "\":" + str(msg)
                cberr(_msg)
                exit(4)

            except Exception as e :
                _msg = "######## Error writing file \"" + _file_name  + "\":" + str(e)
                cberr(_msg)
                exit(4)
         
    return True
        
def build_repository_contents(depsdict) :
    '''
    TBD
    '''

    depsdict["repo_contents"] = {}
    depsdict["repos_ubuntu"] = []
    depsdict["repos_rhel"] = []

    _tmp_list = []
    for _key in list(depsdict.keys()) :
        if _key.count("name") and not _key.count("username") :
            _distro, _repo_name, _x = _key.split('-')
            _tmp_list.append(_distro + '-' + _repo_name)
            depsdict["repo_contents"][_distro + '-' + _repo_name] = {}
            depsdict["repo_contents"][_distro + '-' + _repo_name] = {}
            depsdict["repos_" + _distro].append(_distro + '-' + _repo_name)

    for _key in list(depsdict.keys()) :
        for _repo_name in _tmp_list :
            for _repo_attr in [ "local-url", "original-url", "enabled", \
                               "skip_if_unavailable", "priority", "gpgcheck", \
                               "gpgkey", "dists", "components"] :
                if _key.count(_repo_name + '-' + _repo_attr) :
                    depsdict["repo_contents"][_repo_name][_repo_attr] = \
                    depsdict[_key].replace("REPO_ARCH", depsdict["carch"]).replace("REPO_RELEASE", depsdict["cdistver"]).replace("REPO_MAJOR_RELEASE", depsdict["cdistmajorver"])

    return True

def inst_conf_msg(depkey, depsdict) :
    '''
    TBD
    '''
    msg = " Please install/configure \"" + depkey + "\" by issuing the following command: \""
    msg += str(get_cmdline(depkey, depsdict, "install")[1]) + "\"\n"

    return msg

def execute_command(operation, depkey, depsdict, hostname = "127.0.0.1", username = None, process_manager = None, venv = False, raise_exception = False):
    '''
    TBD
    '''
    try :
        _status = 100        
        _msg = "Obtaining command to be executed...."

        _status = 20000
        _result_stdout = "NA"
        _result_stderr = "NA"
        
        if not process_manager :
            process_manager = ProcessManagement(hostname)

        _cmd = {}

        _cmd["configure-keys"], _cmd["configure"] = get_cmdline(depkey, depsdict, "configure", process_manager, raise_exception)
        _cmd["install-keys"], _cmd["install"] = get_cmdline(depkey, depsdict, "install", process_manager, raise_exception)

        _order = depsdict[depkey + "-order"]

        if depkey != "sudo" and operation == "configure" :
            _msg = "(" + _order + ") Checking \"" + depkey + "\" version by executing the command \""
            _msg += _cmd[operation] + "\" (" + _cmd[operation + "-keys"] + ")..."
        
        elif depkey == "sudo" and operation == "configure" :
            _msg = "(" + _order + ") Checking passwordless sudo for the user \"" + username + "\" "
            _msg += "by executing the command \"" + _cmd[operation] + "\" (" + _cmd[operation + "-keys"] + ")..."

        else :

            if venv :
                _cmd["install"] = _cmd["install"].replace("sudo pip3", "pip3")
            
            _msg = "(" + _order + ") Installing \"" + depkey + "\" by executing the command \""
            _msg += _cmd[operation] + "\" (" + _cmd[operation + "-keys"] + ")..."

        cbinfo(_msg)

        _msg = "(" + _order + ") RESULT for command \"" + _cmd[operation] + "\" : "

        if depkey == "repo" and operation == "install" :
            build_repository_files(depsdict)
                
        _status, _result_stdout, _result_stderr = process_manager.run_os_command(_cmd[operation], False, True, False, True, None, False, 22, False)
                
        if not _status :
            if operation == "install" :
                _msg += "DONE OK (exit code " + str(_status) + ", std out "  + str(_result_stdout) + ", std err " + str(_result_stderr) + " ). \n"
            else :
                _msg += compare_versions(depkey, depsdict, _result_stdout.strip())
        else :
            _msg += "NOT OK (exit code " + str(_status) + ", std out "  + str(_result_stdout) + ", std err " + str(_result_stderr) + " ). "

        if _msg.count("NOT OK") :
            _status = 701

    except ProcessManagement.ProcessManagementException as obj :
        _status = str(obj.status)
        _result_stderr = str(obj.msg)
        
        _msg += "NOT OK (PMgr Exception, exit code " + str(_status) + ", " + str(_result_stderr) + " ). "

    except Exception as e :
        _status = 23
        _msg += "NOT OK (" + str(e) + ")."

    finally :
        if _status :

            if operation == "install" :
                _msg += "There was an error while installing \"" + depkey + "\".: "
                _msg += _result_stderr + "\n"
            else :
                _msg += " CORRECTIVE ACTION: " + inst_conf_msg(depkey, depsdict)
                if depkey == "sudo" :
                    _msg = "Before proceeding further: " + inst_conf_msg("sudo", depsdict)
                    _msg += " *AS ROOT*"
                    cberr(_msg)
                    exit(20)
                else :
                    cbinfo(_msg)

        return _status, _msg

def compare_versions(depkey, depsdict, version_b) :
    '''
    TBD
    '''
    try :
        _msg = ''
        version_a = depsdict[depkey + "-ver"]
        if version_a.lower() == "any" :
            _result = 0
            version_a = "ANY"
            version_b = "ANY"
        else :
            _non_decimal = re.compile(r'[^\d.]+')
            version_a = _non_decimal.sub('', version_a)
            version_b = _non_decimal.sub('', version_b)
            _version_a = list(map(int, re.sub('(\.0+)+\Z','', version_a).split('.')))
            _version_b = list(map(int, re.sub('(\.0+)+\Z','', version_b).split('.')))
            _result = cmp(_version_a,_version_b)

    except KeyError as e:
        _msg = "( exception: " + str(e) + ")"
        _result = -1100000
        
    except Exception as e :
        _msg = "( exception: " + str(e) + ")"
        _result = -1000000

    finally :
        if _result > 0 :
            return str(version_b) + " < " + str(version_a) + " NOT OK." 
        elif _result <= -1100000 :
            return " NOT OK. Unable to find minimum required version for \"" + depkey + "\"" + _msg        
        elif _result <= -1000000 :
            return " NOT OK. Version mismatch (wanted: " + str(version_a) + ", provided: " + str(version_b) + ")" + _msg
        else :
            return str(version_b) + " >= " + str(version_a) + " OK.\n"

def dependency_checker_installer(hostname, depsdict, username, operation, options) :
    '''
    TBD
    '''
    try :    
        _status = 100
        _dep_missing = -1        
        _fmsg = "An error has occurred, but no error message was captured"

        if len(options.wks) > 1 :
            if options.wks.count("_ycsb") :
                options.wks += ",ycsb"

            if options.wks.count(",ycsb") :
                options.wks += ",mongo_ycsb,cassandra_ycsb,redis_ycsb"

            if options.wks.count(",acmeair") :
                options.wks += ",mongo_acmeair"

        if "Filestore_ip" not in depsdict :
            depsdict["Filestore_ip"], depsdict["Filestore_port"], depsdict["Filestore_username"] = options.filestore.split('-')
        
        depsdict["cdistkind"], depsdict["cdistver"], depsdict["cdistmajorver"], depsdict["cdistnam"], depsdict["carch"] = get_linux_distro()
        depsdict["3rdpartydir"] = options.tpdir
        depsdict["scriptsdir"] = options.wksdir
        depsdict["credentialsdir"] = options.creddir
        depsdict["username"] = username

        if options.addr :
            depsdict["repo-addr1"] = options.addr
            depsdict["pip-addr1"] = options.addr

        if depsdict["carch"] == "x86_64" :
            depsdict["carch1"] = "x86_64"           
            depsdict["carch2"] = "x86-64"
            depsdict["carch3"] = "amd64"
            depsdict["carch4"] = "x64"
            depsdict["carch5"] = "amd64"

        elif depsdict["carch"] == "ppc64le" :
            depsdict["carch1"] = "ppc64le"           
            depsdict["carch2"] = "ppc64"
            depsdict["carch3"] = "ppc64el"
            depsdict["carch4"] = "ppc64le"
            depsdict["carch5"] = "ppc64le"

        else:
            depsdict["carch1"] = "aarch64"
            depsdict["carch2"] = "aarch64"
            depsdict["carch3"] = "aarch64"
            depsdict["carch4"] = "aarch64"
            depsdict["carch5"] = "aarch64"

        deps_file_parser(depsdict, username, options, "127.0.0.1")
        docker_file_parser(depsdict, username, options, "127.0.0.1")
        preparation_file_parser(depsdict, username, options, "127.0.0.1")     

        _missing_dep = []
        _dep_list = [0] * 5000

        if str(options.addr) != "bypass" :
            select_url("repo", depsdict)
            select_url("pip", depsdict)
            _raise_exception = True
        else :
            depsdict["pip_addr"] = None
            depsdict["repo_addr"] = None
            _raise_exception = False
            
        for _key in list(depsdict.keys()) :
            if _key.count("-order")  :
                _dependency = _key.replace("-order",'')
                _order = int(depsdict[_key]) * 20
                _dep_list.insert(_order, _dependency)

        _dep_list = [x for x in _dep_list if x != 0]

        print('\n') 
        if options.role.count("workload") :

            options.tag = "base," + options.role
                
            _msg = "##### This node will be used to play a role in the Virtual Applications"
            _msg += " (AIs) \"" + str(options.wks) + "\". Only a subset of the depedencies"
            _msg += " will be " + operation + "ed. This node cannot be used as an Orchestrator Node\n"
            _msg += "\n"
            cbinfo(_msg)

        else :

            options.tag = "base," + options.role + ',' + options.clouds
                        
            _msg = "##### This node will be prepared as an Orchestration Node."
            _msg += " The full set of dependencies will be " + operation + "ed. "
            _msg += "\n"            
            cbinfo(_msg)
            
        options.tag = options.tag.split(',')
            
        _selected_dep_list = []
        
        for _dep in _dep_list :
            for _tag in options.tag :
                if _dep + "-tag" in depsdict :
                    _dep_tag_list = depsdict[_dep + "-tag"].split(',')
                else :
                    _dep_tag_list = [ "workload" ]

                if _tag in _dep_tag_list :
                    if _dep not in _selected_dep_list :
                        _selected_dep_list.append(_dep)

        _dep_list = _selected_dep_list

        _process_manager = ProcessManagement(hostname)

        _status, _std_out, _y = _process_manager.run_os_command("sudo cat /proc/1/cgroup | grep -c docker", raise_exception = False)
        if _status :
            depsdict["indocker"] = False
        else :
            if str(_std_out.replace("\n",'')) == '0' :
                depsdict["indocker"] = False            
            else :
                depsdict["indocker"] = True
        
        _msg = "##### DETECTED OPERATING SYSTEM KIND: " + depsdict["cdistkind"]
        cbinfo(_msg)

        _msg = "##### DETECTED OPERATING SYSTEM VERSION: " + depsdict["cdistver"] + " (" + depsdict["cdistmajorver"] + ')'
        cbinfo(_msg)

        _msg = "##### DETECTED OPERATING SYSTEM NAME: " + depsdict["cdistnam"]
        cbinfo(_msg)

        _msg = "##### DETECTED ARCHITECTURE: " + depsdict["carch"]
        cbinfo(_msg)

        _msg = "##### DETECTED RUNNING INSIDE DOCKER: " + str(depsdict["indocker"])
        cbinfo(_msg)

        print('\n') 

        if operation == "configure" :
            if "repo" in _dep_list :
                _dep_list.remove("repo")

        if depsdict["cdistkind"] == "AMI" :
            _msg = "This node runs the \"" + depsdict["cdistkind"] + "\" Linux "
            _msg += "distribution. Will treat it as \"rhel\", but will disable"
            _msg += "  the repository manipulation."
            cbinfo(_msg)
            
            depsdict["cdistkind"] = "rhel"
            if "repo" in _dep_list :
                _dep_list.remove("repo")

        if depsdict["carch"].count("ppc") and "mongdob" in _dep_list :
            _msg = "##### The processors on this node have a \"Power\" architecture."
            _msg += "Removing MongoDB and Chef (client) from the dependency list"
            cbwarn(_msg)
            _dep_list.remove("mongodb")
            _dep_list.remove("chef-client")

        if "java" in _dep_list and "oraclejava" in _dep_list :
            _msg = "Since both \"java\" and \"oraclejava\" are listed as dependencies"
            _msg += ", only \"oraclejava\" will be used"
            cbinfo(_msg)
            _dep_list.remove("java")
            _dep_list.remove("java-home")

        _fmsg = ""
        _dep_missing = 0

        for _dep in _dep_list :
            _status, _msg = execute_command("configure", _dep, depsdict, \
                                            hostname = "127.0.0.1", \
                                            username = username, \
                                            venv = options.venv, \
                                            raise_exception = _raise_exception)
            if _status :
                _dep_missing += 1
                _missing_dep.append(_dep)
                cberr(_msg)
                
                if operation == "install" :

                    _status, _msg = execute_command("install", _dep, depsdict, \
                                                    hostname = "127.0.0.1", \
                                                    username = username, \
                                                    venv = options.venv, \
                                                    raise_exception = _raise_exception)

                    if not _status :
                        _dep_missing -= 1
                        _missing_dep.remove(_dep)
                        cbinfo(_msg)
                    else :
                        cberr(_msg)
            else :
                cbinfo(_msg)

        _status = _dep_missing
        _fmsg += ','.join(_missing_dep)

    except KeyError as e:
        _status = 22
        _fmsg = "Unable to find entry " + str(e) + " in dependencies dictionary. Check you dependencies configuration file(s)"

    except Exception as e :
        for line in traceback.format_exc().splitlines() :
            print(line)
        _status = 23
        _fmsg = str(e)
    
    finally :

        if _status :
            if _dep_missing :
                _msg = "There are " + str(_dep_missing) + " dependencies missing: " + _fmsg + '\n'
                _msg += "Please add the missing dependency(ies) and re-run " + operation +  " again."
            else :
                _msg = _fmsg + '\n'
                _msg += "Please fix the reported problems re-run " + operation +  " again."               
        else :
            _process_manager = ProcessManagement(hostname)
            _cmd = "sudo chown -R " + depsdict["username"] + ':' + depsdict["username"] + " /home/" + depsdict["username"] + '/'
            _cmd = _cmd.replace("/home/root", "/root")

            if options.cleanupimageid :
                _cmd += "; sudo truncate -s 0 /etc/machine-id; sudo rm -rf /var/lib/dbus/machine-id; sudo ln -s /etc/machine-id /var/lib/dbus/machine-id"
                            
            _status, _x, _y = _process_manager.run_os_command(_cmd, raise_exception = False)            
            _msg = "All dependencies are in place"
                
            if len(options.wks) :
                _msg += " for workload(s) \"" + str(options.wks) + "\""

            if options.cleanupimageid :
                _msg += " (imageid cleanup was invoked)"

        return _status, _msg

def instance_preparation(hostname, depsdict, options) :
    '''
    TBD
    '''
    try :    
        _status = 100
        _store = False
        _process_manager = False
        _cleanup = False
        
        _fmsg = "An error has occurred, but no error message was captured"
        
        if "stores" in depsdict :
            
            for _store in depsdict["stores"] :
    
                _process_manager = ProcessManagement(hostname)
    
                _cmd = depsdict[_store + "_command_check"]
                
                _msg = "Checking accesss from this instance to the CB"
                _msg += " Orchestrator's " + _store.capitalize() + " with"
                _msg += " \"" + _cmd + "\"..."
                cbinfo(_msg)
    
                _status, _x, _y = _process_manager.run_os_command(_cmd)
    
                _msg = "This instance was able to access CB Orchestrator's " + _store.capitalize()
                _msg += " with \"" + _cmd + "\" (OK)"
                cbinfo(_msg)

                if _store.lower() == "filestore" :
                    print('\n')
                    _msg = "rsync rsync://" + depsdict["Filestore_ip"] + ':' + depsdict["Filestore_port"] + '/' + depsdict["Filestore_username"] + "_cb"
                    print(_msg)

                    print('\n')
                    _msg = "--filestore " + depsdict["Filestore_ip"] + '-' + depsdict["Filestore_port"] + '-' + depsdict["Filestore_username"]
                    print(_msg)
                    print('\n')
                    
            if str(options.addr) != "bypass" :
                _cmd = options.wksdir + "/common/cb_cleanup.sh"
                _msg = "Running the instance cleanup script \"" + _cmd + "\"..." 
                cbinfo(_msg)
        
                _process_manager.run_os_command(_cmd)
    
                _cleanup = True

        _status = 0

    except Exception as e :
        _status = 23
        _fmsg = str(e)
    
    finally :

        if _status :
            if _store and not _cleanup :
                _msg = "ERROR while checking accesss from this instance to the CB"
                _msg += " Orchestrator's " + _store.capitalize() + ": " + _fmsg
                _msg += " (make sure that the " + depsdict[_store + "_protocol"] 
                _msg += " port " + depsdict[_store + "_port"]
                _msg += " is open at IP address " + depsdict[_store + "_ip"]
            if not _store and not _cleanup :
                _msg = "ERROR while preparing to check access from this instance "
                _msg += "to the CB Orchestrator's stores:" + _fmsg
            if _store and _cleanup :
                _msg = "ERROR while cleaning up instance."
            cberr(_msg)
        else :
            _msg = ''
            if _process_manager :
                _msg += "Sucessfully checked this instance's ability to connect"
                _msg += " to the Orchestrator's stores."
            if _cleanup and str(options.addr).lower() != "bypass" :
                _msg += "Sucessfully cleaned up this instance."
            cbinfo(_msg)
        return _status, _msg
