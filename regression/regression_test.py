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
    Created on Jun 11, 2012

    Regression Test Generator and Validator

    @author: Marcio A. Silva
'''

from sys import argv, path
from time import time, strftime, strptime, localtime
from datetime import datetime
from subprocess import Popen, PIPE

import os
import HTML
import re
import sys

def make_regression_test(reg_tst_f_contents, reg_tst_expl_fn, override_cb_dir) :
    '''
    TBD
    '''
    _msg = "Experiment plan directives will be"
    _msg += " written to experiment plan file \"" + path[0] + '/' + reg_tst_expl_fn + "\"."
    print _msg

    _counter = 0
    _reg_tst_expl_fh = open(path[0] + '/' + reg_tst_expl_fn, 'w', 0)

    if not override_cb_dir :
        _cb_dir = path[0] + "/../"
    else :
        _cb_dir = override_cb_dir

    for _nr in range(0,2) :
        for _line_number, _line_contents in enumerate(reg_tst_f_contents) :
            _line_contents = _line_contents.strip('\n')
            _line_contents = _line_contents.replace("CB_DIRECTORY", 
                                _cb_dir)
    
            if _line_contents == "DNRTT" :
                _line_contents = False
                _cutoff_line_number = _line_number
    
            if _nr == 1 :
                if _line_number <= _cutoff_line_number :
                    _line_contents = False
                elif _line_contents.count("cldlist\; clddefault none\; clddefault") :
                    _line_contents = _line_contents.replace("clddefault none\;",'')
                elif _line_contents.count("cldattach sim TESTCLOUD") :
                    True
                else :
                    _line_contents = _line_contents.replace(" TESTCLOUD", '')

            if _line_contents :
                _counter += 1
                if not _line_contents.count("\;") :
                    _line_contents = _line_contents + "\;"
        
                _sublines = _line_contents.split("\;")
                for _subline_number, _subline_contents in enumerate(_sublines) :
                    if _subline_number == 0 :
                        _aux = _subline_contents
                        _reg_tst_expl_fh.write("echo " + (" [TEST] " + str(_counter) + ": START " + _aux + ' ').center(160,"#") + '\n')
                    if len(_subline_contents) :
                        _reg_tst_expl_fh.write(_subline_contents.lstrip() + '\n')
                if _counter > 100000 :
                    _reg_tst_expl_fh.write("pause " + '\n')                     
                _reg_tst_expl_fh.write("echo " + (" [TEST] " + str(_counter) + ": END " + _aux + ' ').center(160,"#") + '\n')
                _reg_tst_expl_fh.write("echo " + '\n')
    _reg_tst_expl_fh.write("echo " + (" [TEST] " + str(_counter + 1) + ": START exit ").center(80,"#") + '\n')
    _reg_tst_expl_fh.write("exit\n")
    _reg_tst_expl_fh.write("echo " + (" [TEST] " + str(_counter + 1) + ": END exit ").center(80,"#") + '\n')
    _reg_tst_expl_fh.close()
    
    _msg = str(_counter) + " test cases written to the experiment plan file."
    _msg += " Now run it with the command \"./cloudbench/cloudbench.py --trace regression/"
    _msg += reg_tst_expl_fn + " 2>&1 > regression_test_output.txt\""
    print _msg

ignore_strings = [
                  "Used Memory", 
                  "Uptime (in seconds)", 
                  "Total Connections Received",
                  "Total Commands Processed",
                  "Number of Keys",
                  "Storage Size",
                  "Data Size",
                  "Index Size",
                  "Average Object Size",
                  "Collections",
                  ") VM RESERVATIONS|",
                  ") was sucessfully detached",
                  " Sending a termination request for ",
                  " Bypassing the sending of a copy of the code tree to ",
                  "drwxrwxr-x",
                  "-rw-rw-r--",
                  " seconds... (",
                  ]                          


percent_inc = 1
def show_percent(num, contents, phase) :
    '''
    TBD
    '''
    clen = len(contents)
    percent = int((float(num) / float(clen)) * 100.0)
    if int(num) == 0 :
        print "Starting phase: " + phase
    elif int(num) == (clen - 1) :
        print "\r100%    "
    elif (int(percent) % percent_inc) == 0 :
        sys.stdout.write("\r" + str(percent) + "%...")
        sys.stdout.flush()

def mask_contents(contents, which) :
    '''
    TBD
    '''
    for _line_number, _line_contents in enumerate(contents) :
            
        for istring in ignore_strings :
            if _line_contents.count(istring) :
                _line_contents = "ignored"
                break

        _line_contents = re.sub("\|counter +\|[0-9]+", "|counter |XX", _line_contents)
        _line_contents = re.sub("cloudoption_[a-z]+_[a-z]+:[a-z,0-9,\.]+,", "", _line_contents)
        _line_contents = re.sub("[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+ *", 'xxx.xxx.xxx.xxx ', _line_contents)
        _line_contents = re.sub("EXP-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[A-Z]+-[A-Z]+", 'exp_identifier', _line_contents)
        _line_contents = re.sub(": [0-9]+,", ": xxxxxxxxxx,", _line_contents)
        _line_contents = re.sub("\|13[0-9]+", "|xxxxxxxxxx", _line_contents)
        _line_contents = re.sub("port:[0-9]+", "port:xxxx", _line_contents)
        _line_contents = re.sub("simhost[a-z]+[0-9]+", "simhostX", _line_contents)
        _line_contents = re.sub("vm_[0-9]+ \(cloud-assigned", "vm_XXX (cloud-assigned", _line_contents)
        _line_contents = re.sub("simzone_[a-z]+", "simzone_X", _line_contents)
        _line_contents = re.sub("\|mgt_([0-9,_,a-z,A-Z])+ +\|[0-9]+", "\|mgt_\\1 \|X", _line_contents)
        _line_contents = re.sub("is equal to [0-9]+ \(currently it is equal to [0-9]+\)", "is equal to XX (currently it is equal to XX)", _line_contents)
        _line_contents = re.sub("after [0-9]+ seconds", "after X seconds", _line_contents)
        _line_contents = re.sub("Waited [0-9]+ seconds until ", "Waited X seconds until", _line_contents)
        _line_contents = re.sub("The process id is [0-9]+", "The process id is xxxx", _line_contents)
        _line_contents = re.sub("\|vm_[0-9]+ *\|[a-z_0-9]+ *\|[a-z]+(32|64) *", "|vm_XX |type |sizeXX ", _line_contents)
        _line_contents = re.sub("\|(LG|SUT) *", "|POOL ", _line_contents)
        _line_contents = re.sub("\|ai_[0-9]+ *\|[0-9,_,a-z,>,-]+ +\|[0-9,_,a-z,>,-]+ +", "|ai_XX |N_x_foo->M_x_bar |A_x_foo->B_x_bar ", _line_contents)
        _line_contents = re.sub("vm_[0-9]+_at_[0-9]+", "vm_XX_at_XX", _line_contents)
        _line_contents = re.sub("\"vm_[0-9]+\"\)", "\"vm_XX\")", _line_contents)
        _line_contents = re.sub("\"ai_[0-9]+\"\)", "\"ai_XX\")", _line_contents)
        _line_contents = re.sub("\|[0-9,A-Z,a-z]+:[0-9,A-Z,a-z]+:[0-9,A-Z,a-z]+:[0-9,A-Z,a-z]+:[0-9,A-Z,a-z]+:[0-9,A-Z,a-z]+", "|XX:XX:XX:XX:XX:XX", _line_contents)
        _line_contents = re.sub("\|[a-z,A-Z]+ +[a-z,A-Z]+ +[0-9]+ +[0-9]+:[0-9]+:[0-9]+ +[0-9]+ +\([0-9]+.[0-9]+\)", "DAY MONTH NUMDAY HH:MM:SS YEAR (EPOCH)", _line_contents)
        _line_contents = re.sub("[a-z,A-Z]+ +[a-z,A-Z]+ +[0-9]+ +[0-9]+:[0-9]+:[0-9]+ +[A-Z]+ +[0-9]+", "DAY MONTH NUMDAY HH:MM:SS TIMEZONE YEAR", _line_contents)
        _line_contents = re.sub("\|[a-z,_,0-9]+\|vm_[0-9]+", "role|vm_XX", _line_contents)
        _line_contents = re.sub("\|[0-9]+ +\|REGRESSION_B", "|AGE |REGRESSION_B", _line_contents)
        _line_contents = re.sub("^ total [0-9]+", " total XXXX", _line_contents)
        _line_contents = re.sub(" equals [0-9]+ after X seconds \(", " equals XX after X secdons (", _line_contents)
        _line_contents = re.sub("--oop=[A-Za-z]+,vm_[0-9]+,none", "--oop=XXXCLOUD,vm_XX,none", _line_contents)
        _line_contents = re.sub("\|ai_[0-9]+ +\|", "|ai_XX |", _line_contents)
        _line_contents = re.sub("\|vm_[0-9]+ +\|", "|vm_XX |", _line_contents)
        _line_contents = re.sub("\|POOL +\|\(orphan\)", "|POOL |none ", _line_contents)
        _line_contents = re.sub("\|none *\|", "|none |", _line_contents)
        _line_contents = re.sub("\|(norole|willfail) +\|", "|foorole |", _line_contents)
        _line_contents = re.sub("/home/[^/]+/[^/]+", "/path/to/tool", _line_contents)
        _line_contents = re.sub(" +", " ", _line_contents)
        contents[_line_number] = \
                re.sub("[a-zA-Z0-9_]+-[a-zA-Z0-9_]+-[a-zA-Z0-9_]+-[a-zA-Z0-9_]+-[a-zA-Z0-9_]+", 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', _line_contents)

def validate_regression_test(reg_tst_expl_f_contents, reg_tst_gold_f_contents, reg_tst_sup_out_fn, reg_tst_val_fn) :
    '''
    TBD
    '''
    reg_tst_val_fh = open(path[0] + '/' + reg_tst_val_fn, 'w', 0)

    _outputs_directory = "output_samples"
    _inputs_directory = "input_samples"
    _test_date = "Unknown"
    _test_list = []
    
    _regression_test_commands = {}
    _golden_output_results = {}
    _received_output_results = {}
    
    _current_test = False
    test_idx = 0
    for _line_number, _line_contents in enumerate(reg_tst_expl_f_contents) :
        show_percent(_line_number, reg_tst_expl_f_contents, "loading experiment plan")

        if _line_contents.count("[TEST]") and _line_contents.count("START") and not _line_contents.count("exit") :
            #_current_test = _line_contents.split(':')[0].split()[-1]
            _current_test = test_idx
            _test_list.append(str(_current_test))
            _regression_test_commands[str(_current_test)] = ""

        elif _line_contents.count("[TEST]") and _line_contents.count("END") and not _line_contents.count("exit") :
            _test_input_fh = open(path[0] + '/' + _inputs_directory + '/test' + str(_current_test) + ".txt", 'w', 0)
            _test_input_fh.write(_regression_test_commands[str(_current_test)])
            _test_input_fh.close()
            _current_test = False
            test_idx += 1

        else :
            if _current_test :
                _regression_test_commands[str(_current_test)] += _line_contents
                    
    test_idx = 0
    for _line_number, _line_contents in enumerate(reg_tst_gold_f_contents) :
        show_percent(_line_number, reg_tst_gold_f_contents, "loading golden output")
        if _line_contents.count("[TEST]") and _line_contents.count("START") and not _line_contents.count("exit") :
            #_current_test = _line_contents.split(':')[0].split()[-1]            
            _current_test = test_idx
            _golden_output_results[str(_current_test)] = {}
            _golden_output_results[str(_current_test)]["contents"] = ""            

        elif _line_contents.count("[TEST]") and _line_contents.count("END") and not _line_contents.count("exit") :
            try :
                _golden_output_results[str(_current_test)]["size"] = str(len(_golden_output_results[str(_current_test)]["contents"].split('\n')))
            except KeyError, e:
                print "Failed, current is false on test idx " + str(test_idx) + ": " + str(e) + " test: " + _line_contents
                exit(1)

            _golden_output_fh = open(path[0] + '/' + _outputs_directory + '/golden/test' + str(_current_test) + ".txt", 'w', 0)
            _golden_output_fh.write(_golden_output_results[str(_current_test)]["contents"])
            _golden_output_fh.close()
            _current_test = False
            test_idx += 1

        else :
            if _current_test :
                _golden_output_results[str(_current_test)]["contents"] += _line_contents

    test_idx = 0
    for _line_number, _line_contents in enumerate(reg_tst_sup_out_fn) :
        show_percent(_line_number, reg_tst_sup_out_fn, "loading results")

        if _line_contents.count("[TEST]") and _line_contents.count("START") and not _line_contents.count("exit") :
            #_current_test = _line_contents.split(':')[0].split()[-1]
            _current_test = test_idx
            _received_output_results[str(_current_test)] = {}
            _received_output_results[str(_current_test)]["contents"] = ""

        elif _line_contents.count("[TEST]") and _line_contents.count("END") and not _line_contents.count("exit") :
            _received_output_results[str(_current_test)]["size"] = str(len(_received_output_results[str(_current_test)]["contents"].split('\n')))
            _test_output_fh = open(path[0] + '/' + _outputs_directory + '/received/test' + str(_current_test) + ".txt", 'w', 0)
            _test_output_fh.write(_received_output_results[str(_current_test)]["contents"])
            _test_output_fh.close()
            _current_test = False
            test_idx += 1

        else :
            if _current_test :
                if _line_contents.count(':') == 2 and len(_line_contents.split()) == 6 :
                    _test_date = _line_contents
                _received_output_results[str(_current_test)]["contents"] += _line_contents

    _diff_sizes_list = {}
    _actual_diff_size_list = {}
    
    for _test_num, _test in enumerate(_test_list) :
        _gold_output_fh = open(path[0] + '/' + _outputs_directory + '/golden/test' + str(_test) + ".txt", 'r')
        _gold_contents = _gold_output_fh.readlines()
        _gold_output_fh.close()
        
        _test_output_fh = open(path[0] + '/' + _outputs_directory + '/received/test' + str(_test) + ".txt", 'r')
        _test_contents = _test_output_fh.readlines()
        _test_output_fh.close()

        show_percent(_test_num, _test_list, "masking output")
        mask_contents(_gold_contents, "golden")
        mask_contents(_test_contents, "results")

        _diff = ''
        _diff_size = 0

        if len(_gold_contents) == len(_test_contents) :
            for _gold_line, _test_line in zip(_gold_contents, _test_contents) :
                if _test_line != _gold_line :
                    _diff += _test_line
                    _diff_size += 1
            _diff_sizes_list[str(_test)] = _diff_size
            _actual_diff_size_list[str(_test)] = 0

        elif len(_test_contents) > len(_gold_contents) :
            for _test_line in _test_contents :
                _equal_line = False
                for _golden_line in _gold_contents :
                    if _golden_line == _test_line :
                        _equal_line = True
                        break
                if not _equal_line :
                    _diff += _test_line
                    _diff_size += 1
            _diff_sizes_list[str(_test)] = _diff_size
            _actual_diff_size_list[str(_test)] = len(_test_contents) - len(_gold_contents)

        else :
            for _golden_line in _gold_contents :
                _equal_line = False
                for _test_line in _test_contents :
                    if  _test_line == _golden_line :
                        _equal_line = True
                        break
                if not _equal_line :
                    _diff += _test_line
                    _diff_size += 1
            _diff_sizes_list[str(_test)] = _diff_size
            _actual_diff_size_list[str(_test)] = len(_gold_contents) - len(_test_contents)

        _diff_output_fh = open(path[0] + '/' + _outputs_directory + '/diffs/test' + str(_test) + ".txt", 'w', 0)

        if len(_diff) :
            _diff_output_fh.write(''.join(_diff))
        _diff_output_fh.close()

    _table = HTML.Table(header_row=["TEST NUMBER", "GOLDEN OUTPUT LENGTH (LINES)", "RECEIVED OUTPUT LENGTH (LINES)", "RESULT", "DIFFERENCE"], width="200")

    _failures = 0
    _failure_list = ""
    _warnings = 0
    _warning_list = ""
    _infos = 0
    _info_list = ""

    for _test in _test_list :

        # Adding new tests is difficult, because the test #s do not match up
        # We need a cleaner solution for adding new tests with old golden output
        if str(_test) not in _golden_output_results :
            continue
        _test_number = HTML.TableCell("<a href=\"" + _inputs_directory + "/test" + str(_test) + ".txt\">" + str(_test) + "</a>", width='10')
        _golden_output = HTML.TableCell("<a href=\"" + _outputs_directory + "/golden/test" + str(_test) + ".txt\">" + _golden_output_results[str(_test)]["size"] + "</a>", width='10')
        _received_output =  HTML.TableCell("<a href=\"" + _outputs_directory + "/received/test" + str(_test) + ".txt\">" + _received_output_results[str(_test)]["size"] + "</a>", width='90')
        _diff_size = abs(int(_golden_output_results[str(_test)]["size"]) - int(_received_output_results[str(_test)]["size"]))

        _failure_string = _received_output_results[str(_test)]["contents"].count("unable") \
        or _received_output_results[str(_test)]["contents"].count(" failure") \
        or _received_output_results[str(_test)]["contents"].count(" error") \
        or _received_output_results[str(_test)]["contents"].count("could not be detached") \
        or _received_output_results[str(_test)]["contents"].count("could not be retrieved")

        _supposed_to_fail_string = _received_output_results[str(_test)]["contents"].count("norole") \
        or _received_output_results[str(_test)]["contents"].count("willfail") or \
        _received_output_results[str(_test)]["contents"].count("notype")

        if int(_received_output_results[str(_test)]["size"]) == 0 :
            _result = HTML.TableCell("MISSING", bgcolor='Brown')
            _failures += 1
            _failure_list += str(_test) + ','

        else :
            if _diff_sizes_list[str(_test)] == 0 :
                _result = HTML.TableCell("PASS", bgcolor='Green')
    
            elif _diff_sizes_list[str(_test)] :
    
                if not _failure_string or (_failure_string and _supposed_to_fail_string) :
                    if _actual_diff_size_list[str(_test)] :
                        _result = HTML.TableCell("WARNING", bgcolor='Orange')
                        _warnings += 1
                        _warning_list += str(_test) + ','
                    else :
                        _result = HTML.TableCell("INFO", bgcolor='Yellow')
                        _infos += 1
                        _info_list += str(_test) + ','
                else :
                    _result = HTML.TableCell("FAIL", bgcolor='Red')
                    _failures += 1
                    _failure_list += str(_test) + ','

        _difference = HTML.TableCell("<a href=\"" + _outputs_directory + "/diffs/test" + str(_test) + ".txt\">" + str(_diff_sizes_list[str(_test)]) + "</a>", width='90')
        _table.rows.append([_test_number, _golden_output, _received_output, _result, _difference])

    _htmlcode = "<strong><span style=\"font-size: 20px;\">CloudBench nightly"
    _htmlcode += " regression test (" + _test_date + ") FAILURES : "
    _htmlcode += str(_failures) + " WARNINGS: " + str(_warnings) + " INFOS: "
    _htmlcode += str(_infos) + str(_table) + "</span></strong>"

    reg_tst_val_fh.write(_htmlcode)
    reg_tst_val_fh.close()

    _msg = "Regression test validation concluded. File " + path[0] 
    _msg += '/' + reg_tst_val_fn + " written. There are " + str(_failures)
    _msg += " failures detected (" + _failure_list[0:-1] + "), "
    _msg += str(_warnings) + " warnings detected (" + _warning_list[0:-1]
    _msg += ") and " + str(_infos) + " infos detected."
    print _msg

    _check_list = _failure_list + ',' + _warning_list

    if len(_check_list) :
        if os.uname()[0] == "Darwin" :
            _cmd_binary = "opendiff "
        else :
            _cmd_binary = "meld "

        for _test in _check_list[0:-1].split(',') :
            _cmd = "opendiff " + path[0] + '/' + _outputs_directory + '/golden/test' + str(_test) + ".txt" + ' ' 
            _cmd += path[0] + '/' + _outputs_directory + '/received/test' + str(_test) + ".txt"
            _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)

def main() :
    '''
    TBD
    '''
    _reg_tst_fn = "regression_test_tests.txt"
    _reg_tst_expl_fn = "regression_test_experiment_plan.txt"
    _reg_tst_gold_fn = "regression_test_golden_output.txt"
    _reg_tst_val_fn = "main.html"

    if len(argv) < 2 :
        print "Usage: regression_test make|validate [regression test output filename]"
        exit(1)

    else :
        if argv[1] in [ 'make', 'validate' ] :

            _file_list = [_reg_tst_fn, _reg_tst_expl_fn,  _reg_tst_gold_fn]
            _file_contents = {}
        
            for _file in _file_list :
                _msg = "Opening file \"" + _file + "\".........."
                print _msg
        
                try : 
                    with open(path[0] + '/' + _file, 'r'): pass
                    _file_fh = open(path[0] + '/' + _file, 'r')
                    _file_contents[_file] = _file_fh.readlines()
                    _file_fh.close()
                except IOError :
                    if argv[1] == "make" and _file == _reg_tst_expl_fn :
                        print "Will make " + _file + " from scratch..."
                        _file_contents[_file] = ""
                    else :
                        raise IOError
            
            if argv[1] == "make" :
                if len(argv) > 2 :
                    _override_cb_dir = argv[2]
                else :
                    _override_cb_dir = None
                globals()[argv[1] + "_regression_test"](_file_contents[_reg_tst_fn], _reg_tst_expl_fn, _override_cb_dir)

            elif argv[1] == "validate" :
                if len(argv) == 3 :
                    _reg_tst_out_fn = argv[2]
                else :
                    _reg_tst_out_fn = path[0] + "/regression_test_output.txt"

                _msg = "Preparing to validate regression test. Regression test output file "
                _msg += "used is \"" + path[0] + '/' + _reg_tst_out_fn + "\""
                _msg = "Going to start the regression test validation comparing the file \""
                _msg += _reg_tst_out_fn + "\" against the golden file \"" + path[0]
                _msg += '/' + _reg_tst_gold_fn + "."
              
                print _msg
    
                _reg_tst_out_fh = open(_reg_tst_out_fn, 'r')
                _reg_tst_out_contents = _reg_tst_out_fh.readlines()
                _reg_tst_out_fh.close()
    
                globals()[argv[1] + "_regression_test"](_file_contents[_reg_tst_expl_fn], \
                                                        _file_contents[_reg_tst_gold_fn], \
                                                        _reg_tst_out_contents, \
                                                        _reg_tst_val_fn)
    
        else :
            print "Unknown operation: " + argv[1]
            exit(1)

main()
