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
    Created on Jul 06, 2011

    Data transformation functions

    @author: Marcio A. Silva, Michael R. Hines
'''
from time import time, strftime, strptime, localtime
from os import chmod
from random import random
from datetime import datetime

from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

class DataOpsException(Exception):
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
def selective_dict_update(maindict, extradict) :
    '''
    This function performs a "reverse" maindict.update(extradict) method, where
    the keys already present on maindict will not be overwritten by the values
    of the same keys on extradict
    '''
    try :
        _status = 100
        for _key,_value in extradict.iteritems() :
            if _key in maindict and maindict[_key] != "default":
                True
            else :
                maindict[_key] = _value
        _status = 0

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Selective update failure: " + _fmsg
            cberr(_msg)
            raise DataOpsException(_status, _msg)
        else :
            _msg = "Selective update success."
            cbdebug(_msg)
            return True 

@trace
def str2dic(input_string, raise_exception = True) :
    '''
    String needs to be in the form KEY1:VALUE1,KEY2:VALUE2,...,KEYN:VALUEN
    '''
    try :
        _status = 100
        _dictionary = {}
        for _kv_pair in input_string.split(',') :
            _kv_pair = _kv_pair.split(':')
            _dictionary[_kv_pair[0]] = _kv_pair[1]
        _status = 0

    except IndexError, msg:
        _status = 110
        _fmsg = "Input string was not properly formatted ("
        _fmsg += ':'.join(_kv_pair) + "): " + str(msg)
 
    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "String to dictionary conversion failure: " + _fmsg
            cberr(_msg)
            if raise_exception :
                raise DataOpsException(_status, _msg)
            else :
                return None
        else :
            return _dictionary

@trace
def dic2str(input_dictionary, raise_exception = True) :
    '''
    String will be output in the form KEY1:VALUE1,KEY2:VALUE2,...,KEYN:VALUEN
    '''
    try :
        _status = 100
        _string = ''
        for _key,_value in input_dictionary.iteritems() :
            _string = str(_key) + ':' + str(_value) + ',' + _string
        _string = _string[0:-1]  
        _status = 0

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Dictionary to string conversion failure: " + _fmsg
            cberr(_msg)
            if raise_exception :
                raise DataOpsException(_status, _msg)
            else :
                return None
        else :
            return _string

def is_valid_temp_attr_list(input_string) :
    '''
    TBD
    '''
    try :
        _status = 100
        _input_string = input_string.split(',')
        _is_temp_attr_list = True
        for _sub_string in _input_string :
            if len(_sub_string.split('=')) == 2 :
                True
            else :
                _is_temp_attr_list = False
                break  
        _status = 0

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if _status :
            _msg = "Dictionary to string conversion failure: " + _fmsg
            cberr(_msg)
            raise DataOpsException(_status, _msg)
        else :
            return _is_temp_attr_list

@trace
def wait_on_process(processid, proc_h, output_list) :
    '''
    TBD
    '''

    (output_stdout, output_stderr) = proc_h.communicate()

    if output_list is not None :
        if len(str(output_stdout)) > 0 :
            output_list.append(str(output_stdout))
        elif len(str(output_stdout) + str(output_stderr)) > 0 :
            output_list.append(str(output_stdout) + str(output_stderr))
    if proc_h.returncode > 1 :
        _msg = "There was an execution error: "
        _msg += str(output_stdout) + str(output_stderr)
        cberr(_msg)
        return False
    else :
        return True

@trace
def message_beautifier(message) :
    '''
    TBD
    '''
    _new_message = ''
    if message.count("Usage") :
        _hide = True
        for _word in message.split() :
            if not _hide :
                _new_message += _word + ' '
            elif _word.count("Usage") :
                _new_message += _word + ' '
                _hide = False
            else :
                True
    else :
        _new_message = message
    
    _new_message = _new_message.replace("unknown object initialization failure:", '')
    return _new_message

def makeTimestamp(supplied_epoch_time = False) :
    '''
    TBD
    '''
    if not supplied_epoch_time :
        _now = datetime.utcnow()
    else :
        _now = datetime.utcfromtimestamp(float(supplied_epoch_time))
        
    _date = _now.date()

    result = ("%02d" % _date.month) + "/" + ("%02d" % _date.day) + "/" + ("%04d" % _date.year)
        
    result += strftime(" %I:%M:%S %p", 
                        strptime(str(_now.hour) + ":" + str(_now.minute) + ":" + \
                                 str(_now.second), "%H:%M:%S"))
        
    result += " UTC"
    return result

@trace
def plm_message_beautifier(processid, obj_type, obj_list) :
    '''
    TBD
    '''    
    if obj_type == "group" :
        _fields = []
        _fields.append("|cloud_hostname    ")
        _fields.append("|computenodes                                                                          ")

    elif obj_type == "node" :
        _fields = []
        _fields.append("|cloud_hostname ")
        _fields.append("|cloud_ip       ")
        _fields.append("|function       ")
        _fields.append("|group         ")
        _fields.append("|pcpu_arch ")  
        _fields.append("|pcpu_freq ")
        _fields.append("|pcpus")
        _fields.append("|vcpus")
        _fields.append("|pmem      ")
        _fields.append("|vmem      ")
        _fields.append("|instances")

    elif obj_type == "instance" :
        _fields = []
        _fields.append("|cloud_lvid                       ")
        _fields.append("|cloud_ip       ")
        _fields.append("|host_name      ")
        _fields.append("|group         ")
        _fields.append("|size         ")
        _fields.append("|class         ")
        _fields.append("|vcpus ")
        _fields.append("|vmem      ")
        _fields.append("|volumes ")
        _fields.append("|root_disk_format ")
        _fields.append("|hypervisor ")                
        _fields.append("|state      ")
        _fields.append("|creator ")

    elif obj_type == "storagepool" :
        _fields = []
        _fields.append("|cloud_lvid                          ")
        _fields.append("|type      ")
        _fields.append("|capacity      ")
        _fields.append("|available     ")
        _fields.append("|path                                 ")
        _fields.append("|volumes  ")
        _fields.append("|state    ")
        _fields.append("|creator ")        

    elif obj_type == "volume" :
        _fields = []
        _fields.append("|cloud_lvid                                                            ")
        _fields.append("|type      ")
        _fields.append("|format      ")
        _fields.append("|capacity      ")
        _fields.append("|allocation     ")
        _fields.append("|path                                                                ")
        _fields.append("|instance_lvid                   ")
        _fields.append("|snapshot  ")
        _fields.append("|creator ")

    else :
        _msg = "Unknown object: " + obj_type
        return _msg

    _header = ''.join(_fields)
    _fmt_obj_list = _header + '\n'
    _fmt_obj_list += '-'.rjust(len(_header),'-') + '\n'

    for _obj in obj_list.keys() :
        _obj_attrs = obj_list[_obj]
        for _field in _fields :
            _af = _field[1:].strip()
            if _af in _obj_attrs :
                _display_value = str(_obj_attrs[_af])
            else :
                _display_value = "NA"
            _fmt_obj_list += ('|' + _display_value).ljust(len(_field))
        _fmt_obj_list += '\n'

    return _fmt_obj_list

def plm_parse_host_groups(processid, group_string) :
    '''
    TBD
    '''
    _groups_list = {}
    for _group in group_string.split('/') :
        _group_name, _host_list = _group.split(':')
        _groups_list[_group_name] = _host_list

    _msg = str(len(_groups_list)) + " Host Group(s) found: "
    _msg += ','.join(_groups_list.keys())
    cbdebug(_msg)
    return _groups_list

def value_suffix(value, in_kilobytes = False) :
    '''
    TBD
    '''
    _units = {}
    _units['K'] = 1024
    _units['M'] = 1024*1024
    _units['G'] = 1024*1024*1024

    if value[-1] in _units :
        _value = int(value[:-1]) * _units[value[-1]]
        if in_kilobytes :
            _value = _value/1024
    else :
        _value = int(value)
    return _value

def get_rdir_fullp(obj_attr_list) :
    '''
    TBD
    '''
    _rdn = obj_attr_list["remote_dir_name"]

    if obj_attr_list["login"] != "root" :
        _rln = "/home/" + obj_attr_list["login"]
    else :
        _rln = "/root"

    _rdir_full_path = _rln + '/' + obj_attr_list["remote_dir_name"]
    
    return _rln, _rdir_full_path

def get_boostrap_command(obj_attr_list, osci) :
    '''
    TBD
    '''
    
    _rdh, _rdfp = get_rdir_fullp(obj_attr_list)
    
    _bcmd = "mkdir -p " + _rdfp + ';'

    if obj_attr_list["role"] != "check" :
        _rbf = _rdh + "/cb_os_parameters.txt"        
        _bcmd += "echo '#OSKN-redis' > " + _rbf + ';'
        
        if obj_attr_list["vpn_only"].lower() != "false" :
            _bcmd += "echo '#OSHN-" + obj_attr_list["vpn_server_bootstrap"] + "' >> " + _rbf + ';'
        else :
            _bcmd += "echo '#OSHN-" + osci.host + "' >> " + _rbf + ';'
    
        _bcmd += "echo '#OSPN-" + str(osci.port) + "' >>  " + _rbf + ';'
        _bcmd += "echo '#OSDN-" + str(osci.dbid) + "' >>  " + _rbf + ';'
        _bcmd += "echo '#OSTO-" + str(osci.timout) + "' >>  " + _rbf + ';'
        _bcmd += "echo '#OSCN-" + obj_attr_list["cloud_name"] + "' >>  " + _rbf + ';'
        _bcmd += "echo '#OSMO-" + obj_attr_list["mode"] + "' >>  " + _rbf + ';'
        _bcmd += "echo '#OSOI-" + "TEST_" + obj_attr_list["username"] + ":" + obj_attr_list["cloud_name"] + "' >>  " + _rbf + ';'
        _bcmd += "echo '#VMUUID-" + obj_attr_list["uuid"] + "' >>  " + _rbf + ';'
        _bcmd += "sudo chown -R " +  obj_attr_list["login"] + ':' + obj_attr_list["login"] + ' ' + _rbf + ';'    
    
    else :
        
        _rbf = _rdh + "/cb_prepare_parameters.txt"        
        _store_list = [ "objectstore", "metricstore", "logstore", "filestore" ]
        for _store in _store_list :
            _bcmd += "echo '" + _store.capitalize() + ' ' +  obj_attr_list[_store + "_host"] + ' ' + str(obj_attr_list[_store + "_port"]) + ' ' + obj_attr_list[_store + "_protocol"] + "' >>" + _rbf + ';'
            
    if obj_attr_list["login"] == "root" :
        obj_attr_list["remote_dir_full_path"] = " /root/" + obj_attr_list["remote_dir_name"]
    else :
        obj_attr_list["remote_dir_full_path"] = " /home/" + obj_attr_list["login"] + '/' + obj_attr_list["remote_dir_name"]                    
            
    _bcmd += "sudo chown -R " +  obj_attr_list["login"] + ':' + obj_attr_list["login"] + ' ' + obj_attr_list["remote_dir_full_path"]
                
    return _bcmd
                
def create_user_data_contents(obj_attr_list, osci) :
    '''
    TBD
    '''

    _attempts = str(5)
    _sleep = str(2)
    
    _fshn = obj_attr_list["filestore_hostname"]
    _fspn = obj_attr_list["filestore_port"]
    _fsun = obj_attr_list["filestore_username"]
    _ldn = obj_attr_list["local_dir_name"]

    _rdh, _rdfp = get_rdir_fullp(obj_attr_list)
    _rln = obj_attr_list["login"] 
    
    _ohn = osci.host 
    _opn = osci.port
    _odb = osci.dbid
    _cn = obj_attr_list["cloud_name"]

    if obj_attr_list["vpn_only"].lower() != "false" :
        _ohn = obj_attr_list["vpn_server_bootstrap"]
        _fshn = obj_attr_list["vpn_server_bootstrap"]

    _userdata_contents = "#!/bin/bash\n\n"
    _userdata_contents += "# This VM is part of experiment id \"" + obj_attr_list["experiment_id"] + "\""
    _userdata_contents += "\n"            
    _userdata_contents += "mkdir -p /var/log/cloudbench\n"    
    _userdata_contents += "\n"        
    _userdata_contents += "chmod 777 /var/log/cloudbench\n"
    _userdata_contents += "\n"

    _userdata_contents += get_boostrap_command(obj_attr_list, osci).replace(';','\n')

    if obj_attr_list["use_vpn_ip"].lower() != "false" :    
        _userdata_contents += "\nsudo cp " + obj_attr_list["remote_dir_full_path"] + "/util/openvpn/client_connected.sh /etc/openvpn\n"
        _userdata_contents += "sudo sed 's/USER/" + obj_attr_list["username"] + "/g' /etc/openvpn/client_connected.sh\n"
        _userdata_contents += "sudo sed 's/CLOUD_NAME/" + obj_attr_list["cloud_name"] + "/g' /etc/openvpn/client_connected.sh\n"
        _userdata_contents += "sudo sed 's/SERVER_BOOTSTRAP/" + _ohn  + "/g' /etc/openvpn/client_connected.sh\n"
        _userdata_contents += "sudo sed 's/UUID/" + obj_attr_list["uuid"]  + "/g' /etc/openvpn/client_connected.sh\n"
        _userdata_contents += "sudo sed 's/OSCI_PORT/" + str(_opn)  + "/g' /etc/openvpn/client_connected.sh\n"
        _userdata_contents += "sudo sed 's/OSCI_DBID/" + str(_odb)  + "/g' /etc/openvpn/client_connected.sh\n"

        _userdata_contents += "\nmkdir /var/log/openvpn\n"
        _userdata_contents += "chmod 777 /var/log/openvpn\n"
        _file_fd = open(obj_attr_list["vpn_config_file"], 'r')
        _file_contents = _file_fd.read()
        _userdata_contents += "cat << EOF > /etc/openvpn/" + _cn.upper() + "_client-cb-openvpn.conf\n"
        _userdata_contents += _file_contents
        _userdata_contents += "EOF"
        _userdata_contents += "\n"

        _userdata_contents += "# INSERT OPENVPN COMMAND\n"
        _userdata_contents += "counter=0\n"        
        _userdata_contents += "\nwhile [[ \"$counter\" -le " + _attempts + " ]]\n"
        _userdata_contents += "do\n"
        _userdata_contents += "    ifconfig tun0\n"
        _userdata_contents += "    if [[ $? -eq 0 ]]\n"
        _userdata_contents += "    then\n"
        _userdata_contents += "        VPNIP=$(ifconfig tun0 | grep inet[[:space:]] | sed 's/addr://g' | awk '{ print $2 }' | tr -d '\\n')\n"
        _userdata_contents += "        redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " hset TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:PENDING:" + obj_attr_list["uuid"] + " cloud_init_vpn $VPNIP\n"
        _userdata_contents += "        break\n"    
        _userdata_contents += "    else\n"    
        _userdata_contents += "        sleep " + _sleep + "\n"
        _userdata_contents += "        counter=\"$(( $counter + 1 ))\"\n"    
        _userdata_contents += "    fi\n"
        _userdata_contents += "done\n"

    _userdata_contents += "\nif [[ $(cat " + _rdh + "/cb_os_parameters.txt | grep -c \"#OSOI-" + "TEST_" + obj_attr_list["username"] + ":" + obj_attr_list["cloud_name"] + "\") -ne 0 ]]\n"
    _userdata_contents += "then\n"
    _userdata_contents += "    redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " hset TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:PENDING:" + obj_attr_list["uuid"] + " cloud_init_bootstrap  true\n"
    _userdata_contents += "fi\n"
    _userdata_contents += "\n"
    _userdata_contents += "counter=0\n"    
    _userdata_contents += "\nwhile [[ \"$counter\" -le " + _attempts + " ]]\n"
    _userdata_contents += "do\n"
    _userdata_contents += "    rsync -az --delete --no-o --no-g --inplace rsync://" + _fshn + ':' + _fspn + '/' + _fsun + "_cb" + "/exclude_list.txt /tmp/exclude_list\n"
    _userdata_contents += "    if [[ $? -eq 0 ]]\n"
    _userdata_contents += "    then\n"
    _userdata_contents += "        break\n"
    _userdata_contents += "    else\n"    
    _userdata_contents += "        sleep " + _sleep + "\n"
    _userdata_contents += "        counter=\"$(( $counter + 1 ))\"\n"        
    _userdata_contents += "    fi\n"
    _userdata_contents += "done\n"
    _userdata_contents += "counter=0\n"        
    _userdata_contents += "\nwhile [[ \"$counter\" -le " + _attempts + " ]]\n"
    _userdata_contents += "do\n"
    _userdata_contents += "    rsync -az --exclude-from '/tmp/exclude_list' --delete --no-o --no-g --inplace rsync://" + _fshn + ':' + _fspn + '/' + _fsun + "_cb/ " + _rdfp + "/\n"
    _userdata_contents += "    if [[ $? -eq 0 ]]\n"
    _userdata_contents += "    then\n"
    _userdata_contents += "        redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " hset TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:PENDING:" + obj_attr_list["uuid"] + " cloud_init_rsync true\n"    
    _userdata_contents += "        break\n"    
    _userdata_contents += "    else\n"    
    _userdata_contents += "        sleep " + _sleep + "\n"
    _userdata_contents += "        counter=\"$(( $counter + 1 ))\"\n"    
    _userdata_contents += "    fi\n"
    _userdata_contents += "done\n"
    _userdata_contents += "chown -R " + _rln + ':' + _rln + ' ' + _rdfp + "/\n" 
            
    _userdata_contents += "\n"        
    _userdata_contents += "\n"                    
    _userdata_contents += "VMUUID=$(grep -ri " + obj_attr_list["experiment_id"] + " /var/lib/cloud/ | grep user-data | cut -d '/' -f 6 | head -n 1)\n"
    _userdata_contents += "redis-cli -h " + _ohn + " -n " + str(_odb) + " -p " + str(_opn) + " publish TEST_" + _fsun + ':' + obj_attr_list["cloud_name"] + ":VM:BOOT " + "\"VM $VMUUID is booted\"\n"
    _userdata_contents += "exit 0\n"    
        
    return _userdata_contents

def create_restart_script(scriptname, cmdline, username, searchcmd, objectname = '', uuid = '', scriptpath="/tmp", vtycmd = None) :
    '''
    TBD
    '''
    _fn = scriptpath + '/' + scriptname + '_' + username + '-' + objectname + '--' + uuid

    _fn = _fn.replace('---','')
            
    _fc = "#!/bin/bash\n\n"
    _fc += "PID=$(sudo pgrep -u " + username + " -f " + searchcmd + ")\n"
    _fc += "if [[ ${PID} ]]\n"
    _fc += "then\n"        
    _fc += "    echo \"Killing current \\\"" + searchcmd + "\\\" process (PID is $PID)\"\n"
    _fc += "    sudo pkill -u " + username + " -9 -f " + searchcmd + "\n"
    _fc += "    if [[ $? -eq 0 ]]\n"
    _fc += "    then\n"
    _fc += "        echo \"Process killed\"\n"
    _fc += "    else\n"
    _fc += "        echo \"Failure while killing the process!\"\n"
    _fc += "        exit 1\n"
    _fc += "    fi\n"
    _fc += "fi\n\n" 
    _fc += "echo \"Starting a new \\\"" + searchcmd + "\\\" process\"\n\n"
    _fc += "if [[ -z $1 ]]\n"
    _fc += "then\n"
    if not vtycmd :
        _fc += "    " + cmdline + "\n"
    else :
        _session_name=scriptname.replace("restart_",'').replace("cb_","cb")
        _cmdline = "screen -d -m -S " + _session_name + username + " bash -c '" + cmdline + "'"
        _fc += "    " + _cmdline + "\n"    
    _fc += "else\n"
    _fc += "    if [[ $1 == \"debug\" ]]\n"
    _fc += "    then\n"
    if not vtycmd :
        if cmdline.count("--daemon") :
            _fc += "        " + cmdline.replace("--daemon","--logdest=console") + '\n'
        elif cmdline.count("-d 4") :
            _fc += "        " + cmdline.replace("-d 4","-d 5") + '\n'
        else :
            _fc += "        " + cmdline + " --logdest=console" + '\n'
    else :
        _fc += "        " + cmdline + " --logdest=console" + '\n'
    _fc += "    fi\n"    
    _fc += "fi\n\n"
    _fc += "\nif [[ $? -eq 0 ]]\n"
    _fc += "then\n"
    _fc += "    sleep 5\n"    
    _fc += "    echo \"Process started successfully, with new PID $(sudo pgrep -u " + username + " -f " + searchcmd + ")\"\n"
    _fc += "else\n"
    _fc += "    echo \"Failure while restarting process!\"\n"
    _fc += "    exit 1\n"
    _fc += "fi\n"
    
    _fh = open(_fn, "w")
    _fh.write(_fc)
    _fh.close()
    chmod(_fn, 0755)
    
    return True

def is_number(val, hexa = False) :
    '''
    TBD
    '''
    try:
        if not hexa :
            _val = float(val)
        else :
            _val = int(val, 16)
        return _val
    
    except ValueError:
        return False

# Thannks to Eli Bendersky
def weighted_choice(weights):
    '''
    TBD
    '''
    totals = []
    running_total = 0

    for w in weights:
        running_total += w
        totals.append(running_total)

    rnd = random() * running_total
    for i, total in enumerate(totals):
        if rnd < total:
            return i

def selectively_print_message(step, obj_attr_list) :
    '''
    TBD
    '''        
    if obj_attr_list["role"] == "check": 
        if obj_attr_list[step].lower() == "false" :
            return False

        if obj_attr_list[step].lower() == "pseudotrue" :
            return True
        
    elif obj_attr_list["force_msg_print"].lower() == "true" :
        return True
    
    else :
        
        if "ai" in obj_attr_list and obj_attr_list["ai"] != "none" and \
        obj_attr_list["debug_remote_commands"].lower() == "false" :
            return False
                
        if "ai" in obj_attr_list and obj_attr_list["ai"] != "none" and \
        obj_attr_list["debug_remote_commands"].lower() == "true" :
            return True

        if obj_attr_list["debug_remote_commands"].lower() == "false" :
            if obj_attr_list[step].lower() == "false" :
                return False
        
    return True
    
def summarize(summaries_dict, value, unit) :
    '''
    TBD
    '''
    if summaries_dict["KB => MB"][0] :
        if unit == "KB" or unit == "KiB" :
            value = "%.2f" % (float(value) / 1024)
            unit = "MB"            
            return value, unit
        
    if summaries_dict["Bytes => MB"][0] :
        if unit.lower() == "bytes" or unit == "b" :
            value = "%.2f" % (float(value) / 1024 / 1024)
            unit = "MB"
            return value, unit
                    
    if summaries_dict["bytes/sec => Mbps"][0] :
        if unit == "bytes/sec" :
            value = "%.2f" % (float(value) / 1024 / 1024 * 8)
            unit = "mbps"
            return value, unit
                    
    if summaries_dict["#4K pages => MB"][0] :
        if unit == "#4K pages" :
            value = "%.2f" % (float(value) * 4094 / 1024 / 1024)
            unit = "MB"
            return value, unit
    
    return value, unit

def add_ip_address(subnet, delta) :
    '''
    TBD
    '''
    _octects, _mask = subnet.split('/')
    _octects = _octects.split('.')
    
    for _index in xrange(len(_octects)) :
        _oav = int(_octects[- _index - 1]) + delta
        _oqn = float(float(_oav) / float(256))
        _orn = (_oav % 256)
        
        if _oqn >= 1 :
            delta = int(_oqn)
            _octects[- _index - 1] = str(_orn)            
        else :
            _octects[- _index - 1] = str(_oav)
            break
        
    return '.'.join(_octects), _mask
    
def value_cleanup(object_dict, unit) :
    '''
    TBD
    '''
    _values = []
    if unit in object_dict :

        _value_types = [ "val" ]        
        if "acc" in object_dict[unit] :
            _value_types = [ "val", "acc" ]
        if "avg" in object_dict[unit] :
            _value_types = [ "val", "avg" ]
        
        for _value_type in _value_types : 
            if _value_type in object_dict[unit] :
                _values.append(object_dict[unit][_value_type])
                
    _val_string = ''
    for _value in _values :
        if str(_value).count(":") == 0 :          
            if is_number(_value) :
                _value = str(float(_value))
                if "." in _value :
                    _integer, _decimal = _value.split(".") 
                    if _decimal == "0" :
                        _value = _integer
                    else :
                        _value = str(_integer) + '.' + str(_decimal[0:3])
        else :
            _value = "--"
            
        _val_string += str(_value) + " / "

    _val_string = _val_string[0:-3]
            
    return _val_string