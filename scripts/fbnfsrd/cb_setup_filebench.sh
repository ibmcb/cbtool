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

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_filebench_common.sh

SHORT_HOSTNAME=$(uname -n| cut -d "." -f 1)

syslog_netcat "Setting up the linking to the appropriate filebench binary at ${SHORT_HOSTNAME} (filebench VM)"
sudo rm -f /usr/local/bin/${FB_BINARY_NAME}
sudo ln -s ${FB_BINARY_PATH} /usr/local/bin/${FB_BINARY_NAME}
syslog_netcat "Filebench binary setup - OK"
exit 0