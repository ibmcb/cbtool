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

from sys import argv, path                                                                                            
import os
import re
            
path.append(re.compile(".*\/").search(os.path.realpath(__file__)).group(0) + "/../../")                               
            
from scripts.common.cb_common import report_app_metrics                                                               
            
_metric_list = ''                                                                                                     
_sla_target_list = ''

for _arg in argv :
    if _arg.count("sla_runtime_target") :
        _sla_target_list = _arg.replace(',',' ')
    else :
        if _arg.count(":") == 2 :                                                                                                 
            _metric_list += _arg + ' '                                                                                    

report_app_metrics(_metric_list, _sla_target_list)