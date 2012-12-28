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
def str2dic(input_string) :
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
            raise DataOpsException(_status, _msg)
        else :
            return _dictionary

@trace
def dic2str(input_dictionary) :
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
            raise DataOpsException(_status, _msg)
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
        _now = datetime.now()
    else :
        _now = datetime.fromtimestamp(supplied_epoch_time)
        
    _date = _now.date()

    result = ("%02d" % _date.month) + "/" + ("%02d" % _date.day) + "/" + ("%04d" % _date.year)
        
    result += strftime(" %I:%M:%S %p", 
                        strptime(str(_now.hour) + ":" + str(_now.minute) + ":" + \
                                 str(_now.second), "%H:%M:%S"))
        
    result += strftime(" %Z", localtime(time())) 
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