#! /usr/bin/Rscript

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

library(reshape2)
library(ggplot2)
library(hash)
library(data.table)

initial.options <- commandArgs(trailingOnly = FALSE)
file.arg.name <- "--file="
script.name <- sub(file.arg.name, "", initial.options[grep(file.arg.name, initial.options)])
script.basename <- dirname(script.name)

source(paste(script.basename, "/cbplotlib.R", sep = ''))

args <- commandArgs(TRUE)

if (length(args) > 0) {
	selected_directory <- args[1]
} else {
	selected_directory <- getwd()
}

if (length(args) > 1) {
	selected_experiment <- args[2]
} else {
	selected_experiment <- "all"
}

if (length(args) > 2) {
	selected_metric_type <- args[3]
} else {
	selected_metric_type <- "all"
}

if (length(args) > 3) {
	selected_plot_size <- args[4]
} else {
	selected_plot_size <- 15
}

if (length(args) > 4) {
	selected_time_unit <- args[5]
} else {
	selected_time_unit <- "minutes"
}

if (length(args) > 5) {
	selected_time_intervals <- args[6]
} else {
	selected_time_intervals <- 5
}

if (length(args) > 6) {
	selected_metric_intervals <- args[7]
} else {
	selected_metric_intervals <- 10
}

if (selected_time_unit == "minutes") {
	time_unit <- 60
} else if (selected_time_unit == "hours") {
	time_unit <- 3600
} else {
	selected_time_unit <- "seconds"
	time_unit <- 1
}
file_prefixes <- c("HOST_runtime_os_","VM_runtime_os_", "VM_runtime_app_", 
		"VM_management_", "trace_")

data_frame_names <- c("hros_metrics", "vros_metrics", "rapp_metrics", 
		"mgt_metrics", "trace_metrics")

file_prefix2data_frame_name <- hash(file_prefixes, data_frame_names)

msg <- paste("Directory selected is \"", selected_directory, "\":", sep= '')
cat(msg, sep='\n')

experiment_directories <- list.dirs(path = selected_directory, 
		full.names = FALSE, recursive = FALSE)

experiment_list <- get_experiment_name_list(experiment_directories)

msg <- paste("################################## START PHASE 1 - Pre-processing", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

pre_process_files(experiment_directories, file_prefix2data_frame_name)

msg <- paste("################################## END PHASE 1 - Pre-processing", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

for (file_prefix in file_prefixes) {
	assign(file_prefix2data_frame_name[[ file_prefix ]], 
			create_data_frame(selected_directory, file_prefix))
}

msg <- paste("################################## START PHASE 2 - Plotting Graph", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

msg <- paste("Generating aggregated management metrics plot for all ", 
		"experiments....", sep = '')
cat(msg, sep='\n')

plot_management_data(mgt_metrics, selected_directory, "all", "all", 
		selected_plot_size)

msg <- paste("Generating aggregated runtime application metrics plot for all ", 
		"experiments....", sep = '')
cat(msg, sep='\n')

plot_runtime_application_data(rapp_metrics, selected_directory, "all", "all", 
		"none", selected_time_intervals, selected_metric_intervals, 
		selected_plot_size)

for (experiment in experiment_list) {

	msg <- paste("Generating management metrics plot for experiment ", 
			"\"", experiment, "\"....", sep = '')
	cat(msg, sep='\n')	
	plot_management_data(mgt_metrics, selected_directory, experiment, "all", 
			selected_plot_size)
	
	msg <- paste("Generating runtime application metrics plot for experiment ", 
			"\"", experiment, "\"....", sep = '')
	cat(msg, sep='\n')
	
	vm_arrivals <- subset(mgt_metrics, expid == experiment, 
					select = c("vm_arrival_start", "vm_arrival_end"))

	vm_arrivals <- unique(vm_arrivals)

	plot_runtime_application_data(rapp_metrics, selected_directory, experiment, "all", vm_arrivals, 
			selected_time_intervals, selected_metric_intervals, selected_plot_size)
	
	msg <- paste("Generating runtime VM os resource usage plot for experiment ", 
			"\"", experiment, "\"....", sep = '')
	cat(msg, sep='\n')

	plot_runtime_os_data(vros_metrics, selected_directory, experiment, "all", 
			selected_time_intervals, selected_metric_intervals, 
			selected_plot_size)	

	experiment_host_list <- subset(mgt_metrics, expid == experiment, select = c("host_name", "expid"))
	experiment_host_list <- experiment_host_list[experiment_host_list$host_name != "unknown",]

	if (length(experiment_host_list$host_name) > 1 ) {
		experiment_host_list <- c(levels(factor(experiment_host_list$host_name)))
		experiment_host_list <- paste("host_", experiment_host_list, sep = '')

		msg <- paste("Generating runtime HOST os resource usage plot for experiment ", 
				"\"", experiment, "\"....", sep = '')
		cat(msg, sep='\n')
	
		plot_runtime_os_data(hros_metrics, selected_directory, experiment, 
				experiment_host_list, selected_time_intervals, 
				selected_metric_intervals, selected_plot_size)
		}
	}
msg <- paste("################################## END PHASE 2 - Plotting Graph", 
		" files ##################################", sep = '')
cat(msg, sep='\n')