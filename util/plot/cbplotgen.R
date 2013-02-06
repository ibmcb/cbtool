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

suppressPackageStartupMessages(library(optparse))
suppressPackageStartupMessages(library(reshape2))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(hash))
suppressPackageStartupMessages(library(data.table))

initial.options <- commandArgs(trailingOnly = FALSE)
file.arg.name <- "--file="
script.name <- sub(file.arg.name, "", initial.options[grep(file.arg.name, initial.options)])
script.basename <- dirname(script.name)

option_list <- list(
		make_option(c("-v", "--verbose"), action="store_true", default=TRUE,
				help="Print extra output [default]"),
		make_option(c("-q", "--quietly"), action="store_false",
				dest="verbose", help="Print little output"),
		make_option(c("-a", "--aggregate"), action="store_true", default=FALSE,
				dest="aggregate", help="Plot aggregate (all experiments) metrics"),
		make_option(c("-r", "--runtime"), action="store_true", default=FALSE,
				dest="runtime", help="Plot runtime application performance metrics"),
		make_option(c("-o", "--hostosmetrics"), action="store_true", default=FALSE,
				dest="hostosmetrics", help="Plot HOST os resource usage metrics"),
		make_option(c("-g", "--guestosmetrics"), action="store_true", default=FALSE,
				dest="guestosmetrics", help="Plot VM os resource usage metrics"),
		make_option(c("-c", "--cleanup"), action="store_true", default=FALSE,
				dest="cleanup", help="Cleanup processed files and plots"),
		make_option(c("-d", "--directory"), default=getwd(),
				help = "Directory where the csv files to be processed are located [default \"%default\"]", 
				metavar="selected_directory"),
		make_option(c("-e", "--expid"), default="all",
				help = "Experiment id of the data to be plotted [default \"%default\"]", 
				metavar="selected_experiment"),
		make_option(c("-m", "--metric"), default="all",
				help = "Metric type to be plotted [default \"%default\"]", 
				metavar="selected_metric"),
		make_option(c("-s", "--size"), type="integer", default=15,
				help = "Plot size [default \"%default\"]", 
				metavar="selected_plot_size"),
		make_option(c("-t", "--time"), default="minutes",
				help = "Time unit [default \"%default\"]", 
				metavar="selected_time_unit"),		
		make_option(c("-x", "--xint"), type="integer", default=10,
				help = "Time unit intervals [default \"%default\"]", 
				metavar="selected_time_intervals"),
		make_option(c("-y", "--yint"), type="integer", default=10,
				help = "Metric unit intervals [default \"%default\"]", 
				metavar="selected_metric_intervals")
)

opt <- parse_args(OptionParser(option_list=option_list))

source(paste(script.basename, "/cbplotlib.R", sep = ''))

if (opt$time == "minutes") {
	time_unit <- 60
} else if (opt$time == "hours") {
	time_unit <- 3600
} else {
	opt$time <- "seconds"
	time_unit <- 1
}

file_prefixes <- c("HOST_runtime_os_","VM_runtime_os_", "VM_runtime_app_", 
		"VM_management_", "trace_")

data_frame_names <- c("hros_metrics", "vros_metrics", "rapp_metrics", 
		"mgt_metrics", "trace_metrics")

file_prefix2data_frame_name <- hash(file_prefixes, data_frame_names)

msg <- paste("Directory selected is \"", opt$directory, "\"", sep= '')
cat(msg, sep='\n')

if (opt$cleanup) {
	cleanup_files(opt$directory)
	}

experiment_directories <- list.dirs(path = opt$directory, 
		full.names = FALSE, recursive = FALSE)

msg <- paste("################################## START PHASE 1 - Pre-processing", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

pre_process_files(experiment_directories, file_prefix2data_frame_name)

msg <- paste("################################## END PHASE 1 - Pre-processing", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

for (file_prefix in file_prefixes) {
	assign(file_prefix2data_frame_name[[ file_prefix ]], 
			create_data_frame(opt$directory, file_prefix))
}

msg <- paste("################################## START PHASE 2 - Plotting Graph", 
		" files ##################################", sep = '')
cat(msg, sep='\n')

if (opt$aggregate) {

	msg <- paste("### Generating aggregate management metrics plot for all ", 
			"experiments.... ###", sep = '')
	cat(msg, sep='\n')
	
	plot_management_data(mgt_metrics, opt$directory, "all", "all", 
			opt$size)
	
	msg <- paste("### Done ###", sep = '')
	cat(msg, sep='\n')

	msg <- paste("Generating aggregate runtime application metrics plot for all ", 
			"experiments....", sep = '')
	cat(msg, sep='\n')
	
	plot_runtime_application_data(rapp_metrics, opt$directory, "all", "all", 
			"none", opt$xint, opt$yint, 
			opt$size)
	
	msg <- paste("### Done ###", sep = '')
	cat(msg, sep='\n')

	} else {
		msg <- paste("### BYPASSING aggregate metrics plotting for all experiments ###", 
				sep = '')
		cat(msg, sep='\n')		
	}
	
experiment_list <- get_experiment_name_list(experiment_directories)

for (experiment in experiment_list) {

	msg <- paste("### Generating management metrics plot for experiment ", 
			"\"", experiment, "\".... ###", sep = '')
	cat(msg, sep='\n')

	plot_management_data(mgt_metrics, opt$directory, experiment, "all", 
			opt$size)
	
	msg <- paste("### Done ###", sep = '')
	cat(msg, sep='\n')
	
	if (opt$runtime) {
		msg <- paste("### Generating VM runtime application metrics plot for experiment ", 
				"\"", experiment, "\"....###", sep = '')
		cat(msg, sep='\n')
		
		vm_arrivals <- subset(mgt_metrics, expid == experiment, 
				select = c("vm_arrival_start", "vm_arrival_end"))
		
		vm_arrivals <- unique(vm_arrivals)
		
		plot_runtime_application_data(rapp_metrics, opt$directory, experiment, "all", vm_arrivals, 
				opt$xint, opt$yint, opt$size)

		msg <- paste("### Done ###", sep = '')
		cat(msg, sep='\n')

		} else {
			msg <- paste("### BYPASSING runtime application metrics plotting for experiment ", 
					"\"", experiment, "\" ###", sep = '')
			cat(msg, sep='\n')	
			}

	if (opt$guestosmetrics) {
		
		number_of_vms <- length(mgt_metrics$name)
	
		if (number_of_vms < 100) {
			msg <- paste("### Generating runtime VM OS resource usage plot for experiment ", 
					"\"", experiment, "\".... ###", sep = '')
			cat(msg, sep='\n')
			
			plot_runtime_os_data(vros_metrics, opt$directory, experiment, "all", 
					opt$xint, opt$yint, 
					opt$size)

			msg <- paste("### Done ###", sep = '')
			cat(msg, sep='\n')

				} else {
				msg <- paste("### Too many VMs (", number_of_vms, ") bypassing runtime VM ",
						"OS resource usage plot ###", sep = '')
				cat(msg, sep='\n')		
				}

			} else {
				msg <- paste("### BYPASSING VM runtime OS resource usage plotting", 
						" for experiment ", "\"", experiment, "\" ###", sep = '')
				cat(msg, sep='\n')			
			}

	if (opt$hostosmetrics) {

		experiment_host_list <- subset(mgt_metrics, expid == experiment, select = c("host_name", "expid"))
		experiment_host_list <- experiment_host_list[experiment_host_list$host_name != "unknown",]
	
		if (length(experiment_host_list$host_name) > 1 ) {
	
			experiment_host_list <- c(levels(factor(experiment_host_list$host_name)))
			experiment_host_list <- paste("host_", experiment_host_list, sep = '')
	
			msg <- paste("### Generating runtime HOST os resource usage plot for experiment ", 
					"\"", experiment, "\".... ###", sep = '')
			cat(msg, sep='\n')
	
			plot_runtime_os_data(hros_metrics, opt$directory, experiment, 
					experiment_host_list, opt$xint, 
					opt$yint, opt$size)

			msg <- paste("### Done ###", sep = '')
			cat(msg, sep='\n')
			
			}

		} else {
			msg <- paste("### BYPASSING HOST runtime OS resource usage plotting", 
					" for experiment ", "\"", experiment, "\" ###", sep = '')
			cat(msg, sep='\n')			
		}
	}

msg <- paste("################################## END PHASE 2 - Plotting Graph", 
		" files ##################################", sep = '')
cat(msg, sep='\n')