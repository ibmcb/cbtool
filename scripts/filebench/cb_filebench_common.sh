#!/usr/bin/env bash

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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

#FB_BINARY_PATH=~/3rd_party/_filebench-1.4.9.1/experimental_low_overhead/filebench
#FB_BINARY_NAME=filebench_elo
FB_BINARY_PATH=/usr/local/bin
FB_BINARY_NAME=filebench
FILEBENCH_DATA_DIR=$(get_my_ai_attribute_with_default filebench_data_dir /fbtest)
FILEBENCH_DATA_FSTYP=$(get_my_ai_attribute_with_default filebench_data_fstyp ext4)