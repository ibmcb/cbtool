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
import os
import re
import urllib2
import platform

from lib.remote.process_management import ProcessManagement

def deps_file_parser(depsdict, username, options, hostname, process_manager = None) :
    '''
    TBD
    '''

    _path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../"

    _file_name_list = []

    _file_name_list.append(options.defdir + "/dependencies.txt")

    _workloads_list = options.wks.split(',')

    _cleanup_repos = False
    if len(_workloads_list) :
        for _workload in _workloads_list :
            _file_name_list.append(options.wksdir + '/'  + _workload + "/dependencies.txt")
        _cleanup_repos = True
        
    if len(options.custom) :
        _file_name_list.append(options.cusdir + '/' + options.custom)

    for _file in _file_name_list :
        if os.access(_file, os.F_OK) :
            try:
                _fd = open(_file, 'r')
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
                _msg = "###### Error reading file \"" + _file  + "\":" + str(e)
                print _msg
                exit(4)

    if not len(depsdict) :
        _msg = "Error: None of the files on the list \"" + str(_file_name_list)
        _msg += "\" contained configuration statements"
        print _msg
        exit(9)

    if _cleanup_repos :
        if not process_manager :
            process_manager = ProcessManagement(hostname)
        
        process_manager.run_os_command("rm -rf /tmp/repoupdated", False)

    return True
 
def get_linux_distro() :
    '''
    TBD
    '''
    _linux_distro_name, _linux_distro_ver, _x = platform.linux_distribution()
    if _linux_distro_name.count("Red Hat") :
        _distro = "rhel"
    elif _linux_distro_name.count("CentOS") :
        _distro = "rhel"        
    elif _linux_distro_name.count("Ubuntu") :
        _distro = "ubuntu"
    else :
        _msg = "Unsupported distribution (" + _linux_distro_name + ")"
        raise Exception(_msg)

    _arch = platform.processor()

    if _distro == "ubuntu" and _arch == "x86_64" :
        _arch = "amd64"
        
    return _distro, _linux_distro_ver,_arch

def get_cmdline(depkey, depsdict, operation) :
    '''
    TBD
    '''

    if depsdict[depkey + '-' + operation] == "man" :        
        _urls_key = depsdict["cdist"] + '-' + depkey + '-' + depsdict["carch"] + "-urls-" + depsdict[depkey + '-' + operation]
    else :
        _urls_key = depsdict["cdist"] + '-' + depkey + "-urls-" + depsdict[depkey + '-' + operation]

    if _urls_key in depsdict :
        
        _actual_url = False
        for _url in depsdict[_urls_key].split(',') :
            if check_url(_url, depsdict) :
                _actual_url = _url
                break

        if not _actual_url :
            _msg = "None of the urls indicated to install \"" + depkey + "\" (" 
            _msg += depsdict[_urls_key] + ") seem to be functional."
            raise Exception(_msg)
    else :
        _actual_url = False

    _actual_cmdline = ""

    if operation == "install" :
        for _sub_step in [ "preinstall", "install", "postinstall"] :
            _commandline_key = depsdict["cdist"] + '-' + depkey + '-' + _sub_step + '-' + depsdict[depkey + '-' + operation]

            _actual_cmdline += get_actual_cmdline(_commandline_key, depsdict, _actual_url) + ';'

        if depkey == "repo" :
            build_repository_files(depsdict) 

        if depsdict["cdist"] == "ubuntu" and _actual_cmdline.count("apt-get install") :
            _actual_cmdline += "sudo apt-get -f install"
            
    else :
        _commandline_key = depkey + '-' + operation
        _actual_cmdline += get_actual_cmdline(_commandline_key, depsdict, _actual_url)

    if _actual_cmdline[0] == ';' :
        _actual_cmdline = _actual_cmdline[1:]

    if _actual_cmdline[-1] == ';' :
        _actual_cmdline = _actual_cmdline[0:-1]
        
    _actual_cmdline = _actual_cmdline.replace(";;",';')
    
    return _actual_cmdline

def check_url(url, depsdict) :
    '''
    TBD
    '''
    try:
        if len(url) :
            _url = url.replace("ARCH", depsdict["carch"].strip())
            urllib2.urlopen(urllib2.Request(_url), timeout = 3)
        return True
        
    except:
        return False

def get_actual_cmdline(commandline_key, depsdict, _actual_url) :
    '''
    TBD
    '''
    _commandline = ''
    if commandline_key in depsdict :
        _commandline = depsdict[commandline_key]
        _commandline = _commandline.replace("3RPARTYDIR", depsdict["3rdpartydir"].strip().replace("//",'/'))
        if _actual_url :
            _commandline = _commandline.replace("URL", _actual_url.strip())
        _commandline = _commandline.replace("ARCH", depsdict["carch"].strip())
        _commandline = _commandline.replace("DISTRO", depsdict["cdist"].strip())
        _commandline = _commandline.replace("USERNAME", depsdict["username"].strip())    

    return _commandline

def select_repository_url(depsdict) :
    '''
    TBD
    '''
    depsdict["repo_addr_list"] = []

    depsdict["repo_addr"] = False

    _msg = "Selecting package repository address...." 
    print _msg
    
    for _key in sorted(depsdict.keys()) :
        if _key.count("repo-addr") :
            _index = int(_key.replace("repo-addr",''))
            depsdict["repo_addr_list"].insert(_index, depsdict[_key])
 
    for _repo_addr in depsdict["repo_addr_list"] :
        if check_url("http://" + _repo_addr, depsdict) :
            depsdict["repo_addr"] = _repo_addr
    
    if len(depsdict["repo_addr_list"]) :
        if depsdict["repo_addr"] :
            _msg = "A package repository in \"" + depsdict["repo_addr"] + "\" seems to be up"
            depsdict["repo_dropbox"] = "http://" + depsdict["repo_addr"] + "/dropbox"
            depsdict["repo_credentials_url"] = "http://" + depsdict["repo_addr"] + "/dropbox/ssh_keys"
        else :
            _msg = "None of the selected repositories was available. Will ignore"
            _msg += " any repository URL that has the keyword REPO_ADDR..."
    else :
        _msg = "No package repository specified. Will ignore any repository URL"
        _msg += " that has the keyword REPO_ADDR..."

    print _msg
    
    return True

def build_repository_file_contents(depsdict, repo_name) :
    '''
    TBD
    '''
    
    _file_contents = ""

    if "local_url" in depsdict["repo_contents"][repo_name] :
        if len(depsdict["repo_contents"][repo_name]["local-url"]) :
            if not depsdict["repo_addr"] and \
            depsdict["repo_contents"][repo_name]["local-url"].count("REPO_ADDR") :
                _actual_url = depsdict["repo_contents"][repo_name]["original-url"]
            else :
                _actual_url = depsdict["repo_contents"][repo_name]["local-url"]
        _actual_url = depsdict["repo_contents"][repo_name]["original-url"]
    else :
        _actual_url = depsdict["repo_contents"][repo_name]["original-url"]

    if depsdict["repo_addr"] :
        _actual_url = _actual_url.replace("REPO_ADDR", depsdict["repo_addr"])

    if not check_url(_actual_url, depsdict) :
        _actual_url = depsdict["repo_contents"][repo_name]["original-url"]
        if not check_url(_actual_url, depsdict) :
            _msg = "Error: No URLs available for repository \"" + repo_name + "\""
            raise Exception(_msg)
            
    if depsdict["cdist"] == "ubuntu" :
        for _dist in depsdict["repo_contents"][repo_name]["dists"].split(',') :
            for _component in depsdict["repo_contents"][repo_name]["dists"].split(',') :
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

    if depsdict["cdist"] == "ubuntu" :
        _file_extension = ".list"
        _repo_dir = "/etc/apt/sources.list.d/"
        _file_lines = []
    else :
        _file_extension = ".repo"
        _repo_dir = "/etc/yum.repos.d/"
    
    for _repo in depsdict["repos_" + depsdict["cdist"]] :
        
        _file_contents = build_repository_file_contents(depsdict, _repo)
        
        try:
            _file_name = "/tmp/" + _repo + _file_extension
            _file_descriptor = file(_file_name, 'w')
            _file_descriptor.write(_file_contents)
            _file_descriptor.close()
            os.chmod(_file_name, 0755)

        except IOError, msg :
            _msg = "######## Error writing file \"" + _file_name  + "\":" + str(msg)
            print _msg
            exit(4)

        except OSError, msg :
            _msg = "######## Error writing file \"" + _file_name  + "\":" + str(msg)
            print _msg
            exit(4)

        except Exception, e :
            _msg = "######## Error writing file \"" + _file_name  + "\":" + str(e)
            print _msg
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
    for _key in depsdict.keys() :
        if _key.count("name") and not _key.count("username") :
            _distro, _repo_name, _x = _key.split('-')
            _tmp_list.append(_distro + '-' + _repo_name)
            depsdict["repo_contents"][_distro + '-' + _repo_name] = {}
            depsdict["repo_contents"][_distro + '-' + _repo_name] = {}
            depsdict["repos_" + _distro].append(_distro + '-' + _repo_name)

    for _key in depsdict.keys() :
        for _repo_name in _tmp_list :
            for _repo_attr in [ "local-url", "original-url", "enabled", \
                               "skip_if_unavailable", "priority", "gpgcheck", \
                               "gpgkey", "dists", "components"] :
                if _key.count(_repo_name + '-' + _repo_attr) :
                    depsdict["repo_contents"][_repo_name][_repo_attr] = \
                    depsdict[_key].replace("REPO_ARCH", depsdict["carch"]).replace("REPO_RELEASE", depsdict["cdistver"])

    return True

def inst_conf_msg(depkey, depsdict) :
    '''
    TBD
    '''
    msg = " Please install/configure \"" + depkey + "\" by issuing the following command: \""
    msg += get_cmdline(depkey, depsdict, "install") + "\"\n"

    return msg

def execute_command(operation, depkey, depsdict, hostname = "127.0.0.1", username = None, process_manager = None):
    '''
    TBD
    '''
    try :
        _status = 100        
        _msg = "Obtaining command to be executed...."

        _cmd = {}
        _cmd["configure"] = get_cmdline(depkey, depsdict, "configure")
        _cmd["install"] = get_cmdline(depkey, depsdict, "install")

        if not process_manager :
            process_manager = ProcessManagement(hostname)

        _order = depsdict[depkey + "-order"]

        if depkey != "sudo" and operation == "configure" :
            _msg = "(" + _order + ") Checking \"" + depkey + "\" version by executing the command \""
            _msg += _cmd[operation] + "\"..."
        
        elif depkey == "sudo" and operation == "configure" :
            _msg = "(" + _order + ") Checking passwordless sudo for the user \"" + username + "\" "
            _msg += "by executing the command \"" + _cmd[operation] + "\"..."

        else :
            _msg = "(" + _order + ") Installing \"" + depkey + "\" by executing the command \""
            _msg += _cmd[operation] + "\"..."

        print _msg

        _msg = "RESULT: "

        _status, _result_stdout, _result_stderr = process_manager.run_os_command(_cmd[operation], False)

        if not _status :
            if operation == "install" :
                _msg += "DONE OK.\n"
            else :
                _msg += compare_versions(depkey, depsdict, _result_stdout.strip())
        else :
            _msg += "NOT OK. "

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

            if operation == "install" :
                _msg += "There was an error while installing \"" + depkey + "\"."
            else :
                _msg += "\nACTION: " + inst_conf_msg(depkey, depsdict)
                if depkey == "sudo" :
                    _msg = "Before proceeding further: " + inst_conf_msg("sudo", depsdict)
                    _msg += " *AS ROOT*"
                    print _msg
                    exit(20)

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
            return str(version_b) + " >= " + str(version_a) + " OK.\n"

def dependency_checker_installer(hostname, username, operation, options) :
    '''
    TBD
    '''
    _depsdict = {}
    
    deps_file_parser(_depsdict, username, options, "127.0.0.1")
    
    _depsdict["cdist"], _depsdict["cdistver"], _depsdict["carch"] = get_linux_distro()
    _depsdict["3rdpartydir"] = options.tpdir
    _depsdict["username"] = username

    try :
        _status = 100
        _fmsg = "An error has occurred, but no error message was captured"

        _missing_dep = []
        _dep_list = [0] * 5000

        select_repository_url(_depsdict)       

        for _key in _depsdict.keys() :
            if _key.count("-order")  :
                _dependency = _key.replace("-order",'')
                _order = int(_depsdict[_key]) * 20
                _dep_list.insert(_order, _dependency)

        _dep_list = [x for x in _dep_list if x != 0]

        _fmsg = ""
        _dep_missing = 0
        
        for _dep in _dep_list :

            _status, _msg = execute_command("configure", _dep, _depsdict, hostname = "127.0.0.1", username = username)
            print _msg

            if _status :
                _dep_missing += 1
                _missing_dep.append(_dep)

                if operation == "install" :

                    _status, _msg = execute_command("install", _dep, _depsdict, hostname = "127.0.0.1", username = username)
                    print _msg
                    if not _status :
                        _dep_missing -= 1
                        _missing_dep.remove(_dep)

        _status = _dep_missing
        _fmsg += ','.join(_missing_dep)

    except KeyError, e:
        _status = 22
        _fmsg = "Unable to find entry " + str(e) + " in dependencies dictionary. Check you dependencies configuration file(s)"

    except Exception, e :
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
            _msg = "All dependencies are in place"
        return _status, _msg