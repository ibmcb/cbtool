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
    Created on Nov 06, 2011

    Value Generation Functions

    @author: Marcio A. Silva
'''

from random import expovariate, uniform, gauss, gammavariate
from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit


class ValueGeneration :
    '''
    TBD
    '''

    @trace
    def __init__ (self, pid) :
        '''
        TBD
        '''
        self.pid = pid

    class ValueGenerationException(Exception):
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
    def get_value(self, parameters, previous_value = False) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "Failure while trying to generate value."
            
            if parameters.count('|') :
                parameters = parameters.replace('|','I')
                
            if parameters.count('I') :
                _value = self.rand_dist_gen(parameters)
            elif parameters.count('+') or parameters.count('-') or parameters.count('*') :
                _value = self.monotonic_variation(previous_value, parameters)
            elif parameters.count('d') or parameters.count('h') or parameters.count('m') or parameters.count('s') :
                _value = self.time2seconds(parameters)
            else :
                _value = float(parameters)
            _status = 0
                
        except ValueError as msg :
            _status = 10
            _fmsg = str(msg)
                    
        finally :
            if _status :
                _msg = "Value generation failure: " + _fmsg
                cberr(_msg)
                raise self.ValueGenerationException(_msg, _status)
            else :
                _msg = "Value generation success."
                cbdebug(_msg)
                return _value

    @trace
    def rand_dist_gen(self, parameters) :
        '''
        TBD
        '''
        try :
            _status = 100
            _max_tries = 10000
            _fmsg = "Failure while parsing the distribution parameters"            
            parameters = parameters.split('I')
            
            if len(parameters) == 5 :
                _distribution = str(parameters[0])
                for _idx in range(1,5) :
                    if parameters[_idx] != "X" :
                        parameters[_idx] = float(parameters[_idx])
                _mean = parameters[1]
                _stdev = parameters[2]
                _min = parameters[3]
                _max = parameters[4]
            else :  
                _msg = "Missing parameters for generator with a random "
                _msg += "distribution. All 4 parameters (mean, standard deviation, min,"
                _msg += "max) needs to be specified for every distribution (even if "
                _msg += "some of those gets ignored later)."
                raise self.ValueGenerationException (_msg, 27)

            if _mean == 0.0 :
                _mean = 1.0
            elif _mean == "X" :
                _mean = _max/2
            else :
                True

            if _stdev == 0.0 :
                _stdev = 1.0
            elif _stdev == "X" :
                _stdev = 1.0
            else :
                True

            if _min >= _max :
                _max = _min + 1

            if _max <= _mean:
                _mean = _max/2

            _fmsg = "Failure while generating values according to the distribution"
            _fmsg += " \"" + _distribution + "\" with parameters " + str(_mean)
            _fmsg += " (mean) " + str(_stdev) + " (stdev) " + str(_min) + " (min)"
            _fmsg += str(_max) + " (max)"

            _distributions = {}
            _distributions["exponential"] = "expovariate(1/_mean)"
            _distributions["uniform"] = "uniform(_min, _max)"
            _distributions["gamma"] = "gammavariate((_mean * _mean) / (_stdev * _stdev), (_stdev * _stdev) / _mean)"
            _distributions["normal"] = "gauss(_mean, _stdev)"

            if _distribution in _distributions :        
                _tries = 0
                _value = _min - 1.0

                while (_value < _min or _value > _max) and _tries < _max_tries :

                    _value = eval(_distributions[_distribution])

                    _tries += 1

                _status = 0

            else :
                _fmsg = _distribution + " distribution generators are not supported."
                _fmsg += "Supported random distribution generators are: \n"
                for _key in list(_distributions.keys()) :
                    _msg = _msg + _key + '\n'
                _status = 30

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Random distribution generation failure: " + _fmsg
                cberr(_msg)
                raise self.ValueGenerationException(_msg, _status)                
            else :
                _msg = "The " + _distribution + " distribution generator "
                _msg += "completed successfully."
                cbdebug(_msg)
                return _value

    @trace
    def monotonic_variation(self, previous_value, parameters) :
        '''
        TBD
        '''
        try :
            _sum = False
            _subtract = False
            _multiply = False
            _divide = False
            if parameters.count('+') :
                parameters = parameters.split('+')
                _sum = True
            elif parameters.count('-') :
                parameters = parameters.split('-')
                _subtract = True
            elif parameters.count('*') :
                parameters = parameters.split('*')
                _multiply = True
            elif parameters.count('/') :
                parameters = parameters.split('/')
                _divide = True
            else :
                _msg = "Missing parameters for generation of monotonic variation"
                raise self.ValueGenerationException (_msg, 27)
            
            if not previous_value :
                previous_value = int(parameters[0])
            _factor = int(parameters[1])
            
            if _sum :
                _value = int(previous_value) + int(_factor)
            elif _subtract :
                _value = int(previous_value) - int(_factor)
            elif _multiply :
                _value = int(previous_value) * int(_factor)
            else :
                _value = int(previous_value) / int(_factor)

            _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Monotonic variation generation failure: " + _fmsg
                cberr(_msg)
                raise self.ValueGenerationException(_msg, _status)                
            else :
                _msg = "Monotonic variation generation success."
                cbdebug(_msg)
                return _value

    def value_suffix(self, value, in_kilobytes) :
        '''
        TBD
        '''
        _units = {}
        _units['K'] = 1024
        _units['M'] = 1024*1024
        _units['G'] = 1024*1024*1204
    
        if value[-1] in _units :
            _value = int(value[:-1]) * _units[value[-1]]
            if in_kilobytes :
                _value = _value/1024
        else :
            _value = int(value)
    
        return _value

    @trace
    def time2seconds(self, time_string) :
        '''
        TBD
        '''
        try :
            _status = 100
            _total_time = 0
            
            _rest = "Undefined"
            
            time_string = time_string.strip()
            
            if time_string.count('d') :
                _days, _rest = time_string.split('d')
                _total_time = _total_time + int(_days) * 86400
            else :
                _rest = time_string

            if _rest.count('h') :
                _hours, _rest = _rest.split('h')
                _total_time = _total_time + int(_hours) * 3600
            else :
                _rest = time_string

            if _rest.count('m') :
                _minutes, _rest = _rest.split('m')
                _total_time = _total_time + int(_minutes) * 60
            else :
                _rest = time_string

            if _rest.count('s') :
                _seconds, _rest = _rest.split('s')
                _total_time = _total_time + int(_seconds)
                _rest = time_string
            
            if _rest == "Undefined" :
                _fmsg = "Unable to identifiy time string. Please add the suffix"
                _fmsg += "d (day), h (hour), m (minute) and s (seconds) to each"
                _fmsg += "number (e.g., XdYhZmWs)"
            else :
                _status = 0

        except Exception as e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Time to seconds conversion failure: " + _fmsg
                cberr(_msg)
                raise self.ValueGenerationException(_msg, _status)                
            else :
                _msg = "Time to seconds conversion success."
                cbdebug(_msg)
                return _total_time
