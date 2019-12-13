#! /usr/bin/env Rscript

#/*****************************************************************************
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
#/*****************************************************************************

required_libraries <- c("optparse", "reshape2", "ggplot2", "hash", "data.table", "xtable", "sciplot", "digest")

for (required_library in required_libraries) {
    is_loaded <- suppressPackageStartupMessages(library(required_library, character.only=TRUE, logical.return=TRUE, quietly=TRUE))
    if (!(is_loaded)) {
        install.packages(required_library, repos = 'http://cran.us.r-project.org', dependencies = TRUE)
        suppressPackageStartupMessages(library(required_library, character.only=TRUE, logical.return=TRUE, quietly=TRUE))
    }
}