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
    Created on Aug 22, 2011

    Experiment Command Processor Command Line Interface

    @author: Marcio Silva, Michael R. Galaxy
'''

import os
import re
import errno

from time import time
from re import sub, compile
from copy import deepcopy
from pwd import getpwuid
from subprocess import PIPE,Popen

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.remote.network_functions import get_ip_address, NetworkException

@trace
def isbrokenlink(path):
  if not os.path.lexists(path) :
     return 4

  try:
    os.stat(path)
  except os.error as err:
    # broken link
    # "No such file or directory"
    if err.errno == errno.ENOENT:
      return 1
    # circular link
    # "Too many levels of symlinks"
    elif err.errno == errno.ELOOP:
      return 2
    # something else occurred,
    # assume it as invalid anyway
    else:
      return 3

  return 0

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
                raise Exception("configuration error (user auto): " + _orig_string)
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
def parse_cld_defs_file(cloud_definitions, print_message = False, \
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

                # The user-specific configuration file might be buried under a 
                # subdir
                if _file_name.count(_username) :
                    if not os.access(_file_name, os.F_OK) : 
                        for _dirName, _subdirList, _fileList in os.walk(loc + "configs/"):
                            for _fname in _fileList:
                                if _fname == _username + "_cloud_definitions.txt" :
                                    _file_name = _dirName + '/' + _fname                
                
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
            _firsttime = True
            for _template_file_name in  os.listdir(path + "configs/templates/") :
                if not _template_file_name.count("dependencies.txt") : 
                    _fullpath = path + "/configs/templates/" + _template_file_name
                    if os.path.islink(_fullpath) and isbrokenlink(_fullpath) :
                        if _firsttime :
                            print()
                            _firsttime = False
                        print(("WARNING: " + _fullpath + " symlink is invalid. Skipping"))
                        continue
                    _lines += "INCLUDE configs/templates/" + _template_file_name + '\n'

            for _dirName, _subdirList, _fileList in os.walk(path + "scripts"):
                for _fname in _fileList:
                    if _fname.count("virtual_application.txt") :
                        _shortened_dir_name = _dirName.split("scripts")[1]
                        _lines += "INCLUDE scripts" + _shortened_dir_name + '/' + _fname + '\n'         
            
            _lines += cloud_definitions
            _lines = _lines.split("\n")

            # First we pre-process all "INCLUDE" statements on the file

            _include_found = True
            _temp_cloud_definitions_fc = _lines

            while _include_found :

                _include_found = False
                for _line in _temp_cloud_definitions_fc :

                    comment = r.search(_line)
                    if comment is not None :
                        _line = _line.replace(comment.group(0), "").strip()
                        
                    if _line.count("INCLUDE") and not _line.count("#"):
                        _include_tmp = _line.split("INCLUDE")
                        if len(_include_tmp) != 2 :
                            raise Exception("configuration error (include): " + _line + ": " + str(include_tmp))
                            exit(1)
    
                        _include_fn = _include_tmp[1].strip()
                        _include_fh = open(loc + _include_fn, 'r')
                        _include_fc = _include_fh.readlines()
                        _include_fh.close()
                        _cloud_definitions_fc.extend(_include_fc)
                        
                        if _line in _cloud_definitions_fc :                            
                            _cloud_definitions_fc.remove(_line)

                    else :
                        _cloud_definitions_fc.append(_line)

                _temp_cloud_definitions_fc = deepcopy(_cloud_definitions_fc)

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

                    if _key.count('+') and _previous_key :
                        # The pattern "+=" is used when the value of a
                        # particular key needs to continue on the next
                        # line.

                        if _key.replace('+','').strip() == _previous_key :
                            _key = _previous_key
    
                            _multiline = True
                            if _key.count("enema") :
                                print('\n' + _key)
                        else :
                            _msg = "configuration error: variable " + _key.upper()
                            _msg += "= has to be preceded by one occurrence of "
                            _msg += _previous_key.upper() + " = "
                            raise Exception(_msg)
                       
                    else :
                        _previous_key = _key
                        _multiline = False
                    
                    if _global_subsection is not None :
                        if _key == "config" :
                            _key = _global_subsection
                        else :
                            _key = _global_subsection + "_" + _key
                    
                    if not _key.count("description") : 
                        _value = _value.strip()

                    if _curr_global_object != "user-defined" :
                        if _key != "startup_command_list" and not _key.count("description") :
                            _value = _value.replace(' ', '')

                    if _key in _cld_attr_lst[_curr_global_object] and _multiline :
                        _cld_attr_lst[_curr_global_object][_key] += _value
                    else :
                        _cld_attr_lst[_curr_global_object][_key] = _value
                else :
                    True

            v = compile("\${[^\$]*}")
            
            # Go through all the definitions, and evaluate variables
            for _global in list(_cld_attr_lst.keys()) :
                if isinstance(_cld_attr_lst[_global], dict) :
                    for _key in list(_cld_attr_lst[_global].keys()) :
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
                print(_msg)

            return _cld_attr_lst, "\n".join(_cloud_definitions_fc)

        except IOError as msg :
            if _file_names.index(_file_name) == len(_file_names) - 1 :
                _msg = "Unable to open any of the following files: "
                _msg += ','.join(_file_names) + ':' + str(msg)
                raise Exception(_msg)
                exit(1)
        
        except NetworkException as obj :
            raise Exception(str(obj))
            exit(1)
        
        except Exception as e :
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
    fs_func = getattr(_store_ops, cld_attr_lst["filestore"]["kind"] + "_filestore_setup")
    
    return os_func, ms_func, ls_func, fs_func

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
    for key in me.__dict__ :
        if key.lower().count("cloudoption") :
            continue
        value = me.__dict__[key]
        if not key.count("__") and (isinstance(value, str) or isinstance(value, int)) or isinstance(value, float) or isinstance(value, bool): 
            params[key] = value 

    return params

@trace
def set_my_parameters(me, parameters):
    for key, value in parameters.items() :
        if key.lower().count("cloudoption") :
            continue
        try:
            int(value)
            setattr(me, key, int(value))
        except ValueError:
            try :
                float(value)
                setattr(me, key, float(value))
            except ValueError:
                setattr(me, key, value)

@trace
def rewrite_cloudconfig(cld_attr_lst) :
    '''
      At this point in the attachment, the configuration dictionary
      has the configurations of all possible clouds in the form of:
       
        cld_attr_lst[*][model + "_cloudconfig_" + attribute]
     
      Now that we know the model the user actually cares about, we need
      to re-write the configuration so the rest of the operations code
      functions the same way it did before.
    '''
    for _category in list(cld_attr_lst.keys()) :
        if isinstance(cld_attr_lst[_category], dict) :
            for  _attribute in list(cld_attr_lst[_category].keys()) :
                if _attribute.count("_cloudconfig_") :
                    if _attribute.count(cld_attr_lst["model"] + "_cloudconfig_") :
                        _new = _attribute.replace(cld_attr_lst["model"] + "_cloudconfig_", "")
                        cld_attr_lst[_category][_new] = cld_attr_lst[_category][_attribute]
                    # Remove the unneeded ones
                    del cld_attr_lst[_category][_attribute]
                    
    '''
      Next, we need to check the current cloud model's configuration
      for any variables that the User forgot to perform by searching for
      a specific "need_to_be_configured_by_user" keyword
    '''
    for _category in cld_attr_lst :
        if isinstance(cld_attr_lst[_category], dict) and _category != "user-defined" :
            for  _attribute in cld_attr_lst[_category] :
                template_key = cld_attr_lst["model"] + "_" + _attribute
                if cld_attr_lst[_category][_attribute] == "need_to_be_configured_by_user" or \
                    ((template_key + "_doc") in cld_attr_lst["user-defined"] \
                        and (template_key + "_default") in cld_attr_lst["user-defined"]) :
                    # Fixup custom multi-cloud options that 
                    # are pulled in from the templates
                    if template_key in cld_attr_lst["user-defined"] :
                        cld_attr_lst[_category][_attribute] = cld_attr_lst["user-defined"][template_key]
                        '''
                        Have to check it twice =)
                        '''
                        if cld_attr_lst[_category][_attribute] != "need_to_be_configured_by_user" :
                            continue
                    _msg = "Your configuration file is missing the following configuration: \n"
                    _msg += "\t[USER-DEFINED : CLOUDOPTION_" + cld_attr_lst["name"].upper() + "]\n"
                    _msg += "\t" + template_key.upper() + " = XXXXX\n"
                    _msg += "\n"
                    if (template_key + "_doc") in cld_attr_lst["user-defined"] :
                        _msg += "\n" + cld_attr_lst["user-defined"][template_key + "_doc"].replace("\\n", "\n") + "\n\n"
                    _msg += "Please update your configuration and try again.\n"
                    raise Exception(_msg)

@trace
def rewrite_cloudoptions(cld_attr_lst, available_clouds, user_defined_only = True) :
    '''
    First, we have new support in the GUI for single-file configurations
    that are capable of hosting multiple cloud configurations in a single file.
    
    This is done through the use of the "CLOUDOPTION_XXX" user-defined keyword.
    
    For this to work, we need to search through all the keys and re-write the
    keynames so that they look the way they are supposed to before we try
    to attach the cloud. 

    '''
    if len(available_clouds) :
        for cloud_name in available_clouds :
            if cld_attr_lst["cloud_name"].lower() != cloud_name :
                continue
            searchkey = "cloudoption_" + cloud_name
            for _category in list(cld_attr_lst.keys()) :
                if user_defined_only :
                    if _category != "user-defined" :
                        continue
                else :
                    if _category == "user-defined" :
                        continue
                if not isinstance(cld_attr_lst[_category], dict) :
                    continue 
                for  _attribute in list(cld_attr_lst[_category].keys()) :
                    if _attribute.count(searchkey) :
                        # Don't rewrite the cloudoption keyword
                        # indicators themselves
                        if _category == "user-defined" and _attribute.lower() == searchkey :
                            continue
                        _new = _attribute.replace(searchkey + "_", "")
                        cld_attr_lst[_category][_new] = cld_attr_lst[_category][_attribute]
                        # Remove the unneeded ones
                        del cld_attr_lst[_category][_attribute]
            break
        
        '''
        Let's also cleanup the attribute list and remove 'cloudoption' keywords
        for clouds that do not belong to this particular instance:
        '''
        for cloud_name in available_clouds :
            if cld_attr_lst["cloud_name"].lower() == cloud_name :
                continue
            searchkey = "cloudoption_" + cloud_name
            for _category in list(cld_attr_lst.keys()) :
                if user_defined_only :
                    if _category != "user-defined" :
                        continue
                else :
                    if _category == "user-defined" :
                        continue
                if not isinstance(cld_attr_lst[_category], dict) :
                    continue 
                for  _attribute in list(cld_attr_lst[_category].keys()) :
                    if _attribute.count(searchkey) :
                        del cld_attr_lst[_category][_attribute]

def get_version(path) :
    '''
    TBD
    '''
    _proc_h = Popen("cd " + path + "; git log --pretty=format:'%h' -n 1", shell=True, stdout=PIPE, stderr=PIPE)

    (_output_stdout, _output_stderr) = _proc_h.communicate()
    _proc_h.wait()
    
    return _output_stdout
