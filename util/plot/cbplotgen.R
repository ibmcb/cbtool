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
        make_option(c("-p", "--provisionmetrics"), action="store_true", default=FALSE,
                dest="provisionmetrics", help="Plot provision performance metrics"),
        make_option(c("-r", "--runtimemetrics"), action="store_true", default=FALSE,
                dest="runtimemetrics", help="Plot runtime application performance metrics"),
        make_option(c("-o", "--hostosmetrics"), action="store_true", default=FALSE,
                dest="hostosmetrics", help="Plot HOST os resource usage metrics"),
        make_option(c("-g", "--guestosmetrics"), action="store_true", default=FALSE,
                dest="guestosmetrics", help="Plot VM os resource usage metrics"),
        make_option(c("-c", "--cleanup"), action="store_true", default=FALSE,
                dest="cleanup", help="Cleanup processed files and plots"),
        make_option(c("-z", "--maxvms"), default=9,
                help = "Maximum number of VMs to be included in the provisioning plots [default \"%default\"]", 
                metavar="selected_maxvms"),
        make_option(c("-l", "--layer"), action="store_true", default=FALSE,
                dest="layer", help="Layer provisioning events on top of runtime"),
        make_option(c("-i", "--trace"), action="store_true", default=FALSE,
                dest="trace", help="Plot trace (experiment events and counters)"),        
        make_option(c("-d", "--directory"), default=getwd(),
                help = "Directory where the csv files to be processed are located [default \"%default\"]", 
                metavar="selected_directory"),
        make_option(c("-e", "--expid"), default="all",
                help = "Experiment id of the data to be plotted [default \"%default\"]", 
                metavar="selected_experiment"),
        make_option(c("-m", "--metric"), default="all",
                help = "Metric type to be plotted [default \"%default\"]", 
                metavar="selected_metric"),
        make_option(c("-w", "--window"), default="all",
                help = "Time window to be plotted [default \"%default\"]", 
                metavar="selected_window"),
        make_option(c("-n", "--namedevent"), default="none",
                help = "Named events to be plotted on top of the host OS metrics [default \"%default\"]", 
                metavar="selected_named"),        
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
                metavar="selected_metric_intervals"),
        make_option(c("-u", "--ulatex"), action="store_true", default=FALSE,
                dest="latex", help="Outuput Latex/CSV tables with the plot points"),
		make_option(c("-b", "--breakdown"), default="none",
				help = "List of detailed deployment time breakdown steps [default \"%default\"]", 
				metavar = "selected_breakdown")
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
    
if (opt$maxvms == Inf) {
    opt$maxvms <- 100000
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

if (opt$expid == "all") {
    experiment_directories <- list.dirs(path = opt$directory, 
            full.names = FALSE, recursive = FALSE)
} else {

    expid_list <- unlist(strsplit(opt$expid, split=","))

    experiment_directories <- c(paste(opt$directory, '/', expid_list, sep =''))

    if (length(expid_list) > 1)
        opt$expid <- "all"
}

time_breakdown_list <- unlist(strsplit(opt$breakdown, split=","))
		
msg <- paste("################################## START PHASE 1 - Pre-processing", 
        " files ##################################", sep = '')
cat(msg, sep='\n')

pre_process_files(experiment_directories, file_prefix2data_frame_name)

msg <- paste("################################## END PHASE 1 - Pre-processing", 
        " files ##################################", sep = '')
cat(msg, sep='\n')

for (file_prefix in file_prefixes) {
    assign(file_prefix2data_frame_name[[ file_prefix ]], 
            create_data_frame(opt$directory, opt$expid, file_prefix))
}

msg <- paste("################################## START PHASE 2 - Plotting Graph", 
        " files ##################################", sep = '')
cat(msg, sep='\n')

if (opt$aggregate) {

    msg <- paste("### Generating aggregate management metrics plot for all ", 
            "experiments.... ###", sep = '')
    cat(msg, sep='\n')
    
    plot_management_data(mgt_metrics, opt$directory, "all", "all", 
            opt$size, opt$maxvms)
    
    msg <- paste("### Done ###", sep = '')
    cat(msg, sep='\n')

    if (opt$runtimemetrics) {
        msg <- paste("Generating aggregate runtime application metrics plot for all ", 
                "experiments....", sep = '')
        cat(msg, sep='\n')
        
        plot_runtime_application_data(rapp_metrics, opt$directory, "all", "all", 
                "none", opt$xint, opt$yint, 
                opt$size, time_breakdown_list)
        
        msg <- paste("### Done ###", sep = '')
        cat(msg, sep='\n')
        }        

    } else {
        msg <- paste("### BYPASSING aggregate metrics plotting for all experiments ###", 
                sep = '')
        cat(msg, sep='\n')        
    }

if (opt$expid == "all")    {
    experiment_list <- get_experiment_name_list(experiment_directories)    
} else {
    experiment_list <- c(opt$expid)
}

for (experiment in experiment_list) {

    if (opt$trace) {
        plot_trace_data(trace_metrics, opt$directory, experiment, opt$size)
    }
    
    if (opt$provisionmetrics) {
    
        msg <- paste("### Generating management metrics plot for experiment ", 
                "\"", experiment, "\".... ###", sep = '')
        cat(msg, sep='\n')
    
        plot_management_data(mgt_metrics, opt$directory, experiment, "all", 
                opt$size, opt$maxvms, time_breakdown_list)
        
        msg <- paste("### Done ###", sep = '')
        cat(msg, sep='\n')
        } else {
            msg <- paste("### BYPASSING management application metrics plotting for experiment ", 
                    "\"", experiment, "\" ###", sep = '')
            cat(msg, sep='\n')    
        }

    if (opt$runtimemetrics) {
        msg <- paste("### Generating VM runtime application metrics plot for experiment ", 
                "\"", experiment, "\"....###", sep = '')
        cat(msg, sep='\n')
        
        if (opt$layer) {
            msg <- paste("### Layering provisioning events on top of the runtime",
                    "application metrics plot for experiment", "\"", experiment,
                    "\" ###", sep = '')
            cat(msg, sep='\n')    

            vm_events <- subset(mgt_metrics, expid == experiment, 
                    select = c("vm_arrival_start", "vm_arrival_end", "vm_capture_start", "vm_capture_end"))

            vm_events$vm_arrival_start[is.na(vm_events$vm_arrival_start)] <- -1
            vm_events$vm_arrival_end[is.na(vm_events$vm_arrival_end)] <- -1
            vm_events$vm_capture_start[is.na(vm_events$vm_capture_start)] <- -1
            vm_events$vm_capture_end[is.na(vm_events$vm_capture_end)] <- -1

            vm_events <- unique(vm_events)

            } else {
                vm_events <- "none"
                }

        plot_runtime_application_data(rapp_metrics, opt$directory, experiment, 
                "all", vm_events, opt$xint, opt$yint, opt$size)

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

        if (opt$namedevent != "none") {
            named_events <- trace_metrics[grep(opt$namedevent, trace_metrics$command), ]
            named_events <- subset(named_events, select = c("relative_time"))
            } else {
                named_events <- "none"
                }

		actual_expid <- paste("K", toString(digest(object = experiment, algo = "crc32", serialize = FALSE)), sep='')
		
        if (opt$layer && opt$namedevent == "none") {
            msg <- paste("### Layering provisioning events on top of the runtime",
                    "host metrics plot for experiment", "\"", experiment,
                    "\" ###", sep = '')
            cat(msg, sep='\n')    
            
            vm_events <- subset(mgt_metrics, expid == actual_expid , 
                    select = c("host_name", "vm_arrival_start", "vm_arrival_end", "vm_capture_start", "vm_capture_end"))

            vm_events$vm_arrival_start[is.na(vm_events$vm_arrival_start)] <- -1
            vm_events$vm_arrival_end[is.na(vm_events$vm_arrival_end)] <- -1
            vm_events$vm_capture_start[is.na(vm_events$vm_capture_start)] <- -1
            vm_events$vm_capture_end[is.na(vm_events$vm_capture_end)] <- -1
            
            named_events <- unique(vm_events)
            }

	    experiment_host_list <- subset(mgt_metrics, expid == actual_expid, select = c("host_name", "expid"))

        experiment_host_list <- experiment_host_list[experiment_host_list$host_name != "unknown",]

        if (length(experiment_host_list$host_name) > 0 ) {

            experiment_host_list <- c(levels(factor(experiment_host_list$host_name)))

            experiment_host_list <- paste("host_", experiment_host_list, sep = '')

            msg <- paste("### Generating runtime HOST os resource usage plot for experiment ", 
                    "\"", experiment, "\".... ###", sep = '')
            cat(msg, sep='\n')
    
            plot_runtime_os_data(hros_metrics, opt$directory, experiment, 
                    experiment_host_list, opt$xint, 
                    opt$yint, opt$size, named_events)

            msg <- paste("### Done ###", sep = '')
            cat(msg, sep='\n')
            
            }

        } else {
            msg <- paste("### BYPASSING HOST runtime OS resource usage plotting", 
                    " for experiment ", "\"", experiment, "\" ###", sep = '')
            cat(msg, sep='\n')            
        }

        pdf_dir <- paste(opt$directory, '/', experiment, sep = '')
        
                system(paste("rm -rf ", pdf_dir, "/Rplots.pdf", sep = ''))
        tex_files <- c(list.files(path = opt$directory, pattern = "tex", recursive = TRUE))
		
		if (opt$latex) {
	        if (length(tex_files) > 1) {
	            command <- paste("pdflatex -output-directory=", pdf_dir, ' ', pdf_dir, "/*.tex", sep = '')
	                        print(command)
	            system(command)
	        }
	        
	        command <- paste("rm -rf ", pdf_dir, "/all_plots.pdf; pdftk ", pdf_dir, "/*.pdf cat output ", pdf_dir, "/all_plots.pdf", sep = '')
	                print(command)
	        system(command)
		}        
    }

pdf_dir <- paste(opt$directory, sep = '')
system(paste("rm -rf ", pdf_dir, "/Rplots.pdf", sep = ''))
system(paste("rm -rf ", pdf_dir, "/texput.log", sep = ''))

if (opt$aggregate) {
    
    tex_files <- c(list.files(path = opt$directory, pattern = "tex", recursive = TRUE))
	if (opt$latex) {       
	    if (length(tex_files) > 1) {
	        command <- paste("pdflatex -output-directory=", pdf_dir, ' ', pdf_dir, "/*.tex", sep = '')
	                print(command)
	                system(command)
	    }
	}
    command <- paste("rm -rf ", pdf_dir, "/all_plots.pdf; pdftk ", pdf_dir, "/*.pdf cat output ", pdf_dir, "/all_plots.pdf", sep = '')
    print(command)
    system(command)
}

msg <- paste("################################## END PHASE 2 - Plotting Graphs", 
        " files ##################################", sep = '')
cat(msg, sep='\n')
