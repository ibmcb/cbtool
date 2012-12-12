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
    Created on Aug 22, 2011

    Experiment Command Processor Command Line Interface

    @author: Marcio Silva, Michael R. Hines
'''

import os
import re

from time import time
from re import sub, compile
from pwd import getpwuid

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import get_ip_address, NetworkException

@trace
def parse_evaluate_variable(_variable, _orig_string, \
                            _curr_global_object, _cld_attr_lst, aux_var) :
    '''
    Evaluates a conf variable by expanding its value
    '''
    path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../.."
    if aux_var in _cld_attr_lst[_curr_global_object] :
        _variable_value = _cld_attr_lst[_curr_global_object][aux_var]
    elif "user-defined" in _cld_attr_lst and aux_var in _cld_attr_lst["user-defined"] :
        _variable_value = _cld_attr_lst["user-defined"][aux_var]
    elif aux_var.count("user_auto") : 
        if len(aux_var) == 9 :
            _variable_value = getpwuid(os.getuid())[0]
        else :
            _aux_tmp = aux_var.split()
            if len(_aux_tmp) < 2 :
                raise Exception("configuration error: " + _orig_string)
                _variable_value = getpwuid(os.getuid())[0] + '_' + _aux_tmp[1]
    elif aux_var.count("processid") and len(aux_var) == 9 :
        _variable_value = getpwuid(os.getuid())[0]
    elif aux_var.count("path_to_tool") and len(aux_var) == 12 :
        _variable_value = path
    elif aux_var.count("empty") and len(aux_var) == 5 :
        _variable_value = " "
    elif aux_var.count("ip_auto") :
        _variable_value = get_ip_address()
    elif aux_var.count("date") :
        _variable_value = str(int(time()))
    elif aux_var.count("true") :
        _variable_value = True
    elif aux_var.count("false") :
        _variable_value = False
    else :
        _msg = "Variable value not found in configuration: " + _orig_string
        raise Exception(_msg)
        exit(1)
                
    if isinstance(_variable_value, str) :
        if len(_variable) == 0 :
            raise Exception("Configuration error: " + _orig_string)
            exit(1)
        if _variable.count("${") :
            _value = sub(r'\${%s}' % _variable[2:-1], _variable_value, _orig_string)
        else :
            _value = sub(r'\$%s' % _variable[1:], _variable_value, _orig_string)
    else :
        _value = _variable_value

    # If we expanded to another expression with a variable, expand once more
    if isinstance(_variable_value, str) and _variable_value.count('$') and not _variable_value.count('${') :
        for _variable in _variable_value.split('/') :
            if _variable.count('$') :
                _value = parse_evaluate_variable(_variable, _value,
                                                      _curr_global_object, \
                                                      _cld_attr_lst, 
                                                      _variable[1:].lower())

    return _value

@trace
def parse_cld_defs_file(cloud_definitions = None, print_message = False, \
                        extra_file = False) :
    '''
    TBD
    '''
    _cld_attr_lst = {}
    _username = getpwuid(os.getuid())[0]
    path = re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../"
    loc = path + '/'
    _file_names = []
    
    if extra_file :
        _file_names.append(extra_file)
        _file_names.append(loc + extra_file)
        _file_names.append(loc + "configs/" + extra_file)
    
    _file_names.append(loc + "configs/" + _username + "_cloud_definitions.txt")
    _file_names.append(loc + "configs/" +"definitions.txt")
    _file_names.append(loc + "configs/" +"cloud_definitions.txt")

    r = compile("(#.*)")
    _cloud_definitions_fc = []

    for _file_name in _file_names :
        try :
            # contents might already be provided
            if not cloud_definitions :
                fh = open(_file_name, 'r')
                cloud_definitions = fh.read()
                fh.close()
            else :
                _file_name = "From Dashboard"

            '''
             Templates are not supposed to be modified
             by the user, and thus, its appropriate for us to import
             them by default.
             
             The only tricky part are the cloud templates - they have to
             all be imported at once.
             
             To allow this, each section in a cloud template is prefixed
             with a subsection, just like VApp templates and Submitter
             templates are so that all the configurations can be loaded
             at the same time.
             
             Then, later, during cldattach(), the appropriate cloud will
             be selected and the unused cloud configurations will be
             thrown away so that all the code functions as it did before.
             
             Note, this does not obviate the use of 'INCLUDE' - we should
             keep that support so that users can import other configuration
             files of their choosing.
            '''

            _lines = ''
            for _template_file_name in  os.listdir(path + "configs/templates/") :
                _lines += "INCLUDE configs/templates/" + _template_file_name + '\n'

            _lines += cloud_definitions
            _lines = _lines.split("\n")

            # First we pre-process all "INCLUDE" statements on the file

            for _line in _lines :
                comment = r.search(_line)
                if comment is not None :
                    _line = _line.replace(comment.group(0), "").strip()
                    
                if _line.count("INCLUDE") and not _line.count("#"):
                    _include_tmp = _line.split("INCLUDE")
                    if len(_include_tmp) != 2 :
                        raise Exception("configuration error: " + _line)
                        exit(1)

                    _include_fn = _include_tmp[1].strip()
                    _include_fh = open(loc + _include_fn, 'r')
                    _include_fc = _include_fh.readlines()
                    _include_fh.close()
                    _cloud_definitions_fc.extend(_include_fc)
                else :
                    _cloud_definitions_fc.append(_line)

            _cld_attr_lst["cloud_filename"] = _file_name

            # Now we can properly process the effective cloud definitions
            # file contents (which has also the contents of the included
            # files).
            _previous_key = False
            _curr_global_object = "None"
            _global_subsection = None 
            for _line in _cloud_definitions_fc :
                _line = _line.strip()
                if len(_line) == 0 :
                    continue
                if _line[0].count('[') :
                    _curr_global_object = _line.strip().lower()
                    _curr_global_object = _curr_global_object[1:-1]
                    
                    # See if this is a subsection
                    # If so, signal that all key/values of this subsection
                    # Will eventually be stored in the parent section's dictionary
                    if _curr_global_object.count(":") :
                        _sec, _subsec = _curr_global_object.split(":")
                        
                        # Support the '>' symbol after the colon to indicate
                        # explicit order of operations:
                       
                        if _subsec.count(">") :
                            _new_subsec = "" 
                            _parts = _subsec.split(">")
                            
                            '''
                            Sanity check:
                            '''
                            if len(_parts) > 3 :
                                raise Exception("\nconfiguration error: too many components listed after the colon: " + _line)
                            if len(_parts) == 3 :
                                if not _parts[0].lower().count("cloudoption") :
                                    raise Exception("\nconfiguration error: order is incorrect: " + _line)
                                if not _parts[1].lower().count("cloudconfig") :
                                    raise Exception("\nconfiguration error: order is incorrect: " + _line)
                                if _parts[2].lower().count("cloudoption") or _parts[0].lower().count("cloudconfig"):
                                    raise Exception("\nconfiguration error: order is incorrect: " + _line)
                            if len(_parts) == 2 :
                                if not _parts[0].lower().count("cloudoption") and not _parts[0].lower().count("cloudconfig"):
                                    raise Exception("\nconfiguration error: order is incorrect: " + _line)
                            
                            for _part in _parts :
                               if _part.strip() == "" :
                                    raise Exception("\nconfiguration error: invalid component listing after colon: " + _line)
                                
                               if _new_subsec != "" :
                                   _new_subsec += "_" 
                               _new_subsec += _part.strip() 
                            
                            _subsec = _new_subsec
                        
                        _global_subsection = _subsec.strip()
                        _curr_global_object = _sec.strip() 
                    else :
                        _global_subsection = None
                    
                    if _curr_global_object not in _cld_attr_lst :
                        _cld_attr_lst[_curr_global_object] = {}
                elif _line[0].count("#") :
                    True
                elif len(_line) > 1 :
                    _tmp = _line.split('=')
                    if len(_tmp) < 2 :
                        raise Exception("configuration error: " + _line)
                        exit(1)
                        
                    _key = _tmp[0]
                    
                    # Some values (like URLs) actually have Equal signs
                    # Try to support this
                    if len(_tmp) > 2 :
                        _value = ""
                        for _x in range(1, len(_tmp)) :
                            _value += _tmp[_x] + "="
                        _value = _value[:-1]
                    else :
                        _value = _tmp[1]
                        
                    _key = _key.strip().lower()
                    if _key.count('+=') and _previous_key :
                        # The pattern "+=" is used when the value of a
                        # particular key needs to continue on the next
                        # line. THIS IS BROKEN!!!!!
                        _key = _previous_key
                    else :
                        _previous_key = _key
                    
                    if _global_subsection is not None :
                        if _key == "config" :
                            _key = _global_subsection
                        else :
                            _key = _global_subsection + "_" + _key
                        
                    _value = _value.strip()
                    
                    if _curr_global_object != "user-defined" and\
                     _key != "startup_command_list" :
                        _value = _value.replace(' ', '')

#                            if _key in _cld_attr_lst[_curr_global_object] :
#                                _cld_attr_lst[_curr_global_object][_key] += _value
#                            else :
                    _cld_attr_lst[_curr_global_object][_key] = _value
                else :
                    True

            v = compile("\${[^\$]*}")
            
            # Go through all the definitions, and evaluate variables
            for _global in _cld_attr_lst.keys() :
                if isinstance(_cld_attr_lst[_global], dict) :
                    for _key in _cld_attr_lst[_global].keys() :
                        _value = _cld_attr_lst[_global][_key]
                        _eval_value = _value
                        
                        # Try to support the old style variable expansion
                        if _value.count('$') == 1 or (_value.count('$') > 1 and _value.count('/')) :
                            for _variable in _value.split('/') :
                                if _variable.count('$') :
                                    _eval_value = parse_evaluate_variable(_variable, _eval_value, \
                                                                           _global, _cld_attr_lst,
                                                                           _variable[1:].lower())

                        # New-style (explicit) variable expansion
                        elif _value.count('${') :
                            while _eval_value.count('$') :
                                _next_variable = v.search(_eval_value)
                                if _next_variable is None :
                                    raise Exception("configuration error: invalid multi-inline variable specification: " + _eval_value)
                                _eval_value = parse_evaluate_variable(_next_variable.group(0), _eval_value, \
                                                                           _global, _cld_attr_lst,
                                                                           _next_variable.group(0)[2:-1].lower())
                        elif _value.count('$') :
                            raise Exception("configuration error: invalid variable specification: " + _value)
                        
                        if _eval_value != _value :
                            _cld_attr_lst[_global][_key] = _eval_value
                        
            _status = 0
            _msg = "\"" +  _file_name + "\" opened and parsed successfully."

            if print_message :
                print _msg

            return _cld_attr_lst, "\n".join(_cloud_definitions_fc)

        except IOError, msg :
            if _file_names.index(_file_name) == len(_file_names) - 1 :
                _msg = "Unable to open any of the following files: "
                _msg += ','.join(_file_names) + ':' + str(msg)
                raise Exception(_msg)
                exit(1)
        
        except NetworkException, obj :
            raise Exception(str(obj))
            exit(1)
        
        except Exception, e :
            raise Exception(str(e))
            exit(1)

    return False

@trace
def load_store_functions(cld_attr_lst) :
    '''
    TBD
    '''
    _store_ops = __import__("lib.stores.stores_initial_setup", fromlist=["*"])

    os_func = getattr(_store_ops, cld_attr_lst["objectstore"]["kind"] + "_objectstore_setup")
    ms_func = getattr(_store_ops, cld_attr_lst["metricstore"]["kind"] + "_metricstore_setup")
    ls_func = getattr(_store_ops, cld_attr_lst["logstore"]["kind"] + "_logstore_setup")

    return os_func, ms_func, ls_func

@trace
def get_available_clouds(cld_attr_lst, return_all_options = False) :
    '''
    TBD
    '''
    if return_all_options :
        commands = {}
        for key in cld_attr_lst["user-defined"] :
            if key.count("cloudoption_") :
                parts = key.split("_")
                if len(parts) < 2 :
                    raise Exception("Configuration error: Malformed CLOUDOPTION: " + key + " = " + str(cld_attr_lst["user-defined"][key]))
                if len(parts) > 2 :
                    continue
                cloud_name = parts[1]
                commands[cloud_name] = []
                for command in cld_attr_lst["user-defined"][key].split(',') :
                    '''
                     Try to simplify the multi-cloud configuration a little bit.
                     Permit the cldattach command to 'omit' the cloud name,
                     since we already know the cloud name in the variable names themselves.
                    '''
                    if command.count("cldattach") and not command.lower().count(cloud_name.lower()) :
                        command += " " + cloud_name.upper()
                    commands[cloud_name].append(command.strip())
    else :
        commands = []
        if "startup_command_list" in cld_attr_lst["user-defined"] :
            for _command in cld_attr_lst["user-defined"]["startup_command_list"].split(',') :
                commands.append(_command.strip())
            
    return commands

@trace
def get_my_parameters(me):
    '''
    Convert class attributes into a dictionary
    Python rocks.
    '''
    params = {}
    for var in me.__dict__ :
        value = me.__dict__[var]
        if not var.count("__") and (isinstance(value, str) or isinstance(value, int)) or isinstance(value, float) or isinstance(value, bool): 
            params[var] = value 

    return params

@trace
def set_my_parameters(me, parameters):
    for key, value in parameters.iteritems() :
        try:
            int(value)
            setattr(me, key, int(value))
        except ValueError:
            try :
                float(value)
                setattr(me, key, float(value))
            except ValueError:
                setattr(me, key, value)
