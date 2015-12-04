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

FIO_DATA_DIR=$(get_my_ai_attribute_with_default fio_data_dir /fiotest)
FIO_DATA_FSTYP=$(get_my_ai_attribute_with_default fio_data_fstyp ext4)
FIO_DATA_VOLUME=$(get_my_ai_attribute_with_default fio_data_volume NONE)

FIO_ENGINE=$(get_my_ai_attribute_with_default fio_engine sync)
FIO_BS=$(get_my_ai_attribute_with_default fio_bs 64k) 
FIO_DIRECT=$(get_my_ai_attribute_with_default fio_direct 1)
FIO_FILE_SIZE=$(get_my_ai_attribute_with_default fio_file_size 1g)
FIO_RATE_IOPS=$(get_my_ai_attribute_with_default fio_rate_iops 100) 