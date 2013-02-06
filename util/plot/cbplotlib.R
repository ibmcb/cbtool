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

get_experiment_file_list <- function(en, fp2df_dict) {
	
	file_names <- keys(fp2df_dict)
	
	experiment_file_list <- paste(file_names, en, ".csv", sep = '')
	
	return(experiment_file_list)
	}
	
get_experiment_name_list <- function(ednl) {
	
	experiment_list <- c('')
	
	for (experiment_directory_name in ednl) {
		experiment_name <- strsplit(experiment_directory_name, '\\/', 
				fixed = FALSE, perl = FALSE, useBytes = FALSE)
		experiment_name <- tail(experiment_name[[1]], n=1)
		experiment_list <- c(experiment_list, experiment_name)
		}
	return(experiment_list[-1])
	}

output_pdf_plot <- function(ed, en, po, pn = '', sps = 15, vmn = -1) {

	if (en == "all") {
		en <- '/'
		} else {
		en <- paste('/', en, '/', sep = '')
		}

	if (pn == '') {
		file_name <- as.character(deparse(substitute(po)))
		} else {
			file_name <- pn
		}

	file_name <- paste(file_name, ".pdf", sep = '')

	file_location <- paste(ed, en, file_name, sep = '')

	if (vmn > 0) {
		determined_width <- round(vmn * 3)		
		if (determined_width < sps) {
			determined_width <- sps
			}
		} else {
		determined_width <- sps
		}

	ggsave(po, file = file_location, width = determined_width, limitsize = FALSE)	
	}

plot_get_x_y_limits <- function(en, gdf, xati, yati) {
		
		column_names <- c(names(gdf))
		
		if ("relative_time" %in% column_names) {
#		x_start <- round(min(gdf$relative_time))
			x_start <- 0
			x_end <- round(max(gdf$relative_time))
		} else {
			x_start <- round(min(gdf$app_load_level))
			x_end <- round(max(gdf$app_load_level))
		}
		
		x_limits <- c(x_start, x_end)
		
		x_step <- round((x_end - x_start)/xati)
		if (x_step < 1) {
			x_step <- 1
		}
		
		x_breaks <- seq(x_start, x_end, x_step)
		
		#y_start = min(perf_vs_time_data$value)
		y_start = 0
		y_end = round(max(gdf$value)*1.2)
		
		y_limits = c(y_start, y_end)
		
		y_step <- round((y_end - y_start)/yati)
		
		xy_limits <- list(x_limits, x_breaks, y_limits, y_step)
		
		return(xy_limits)
	}

cleanup_files <- function(ednl) {
	msg <- paste("Cleaning up previously created \"processed\" files and plots...", sep = '')
	cat(msg, sep='\n')

	processed_file_list <- c(list.files(path = ednl, pattern = "processed_", recursive = TRUE))

	plot_file_list <- c(list.files(path = ednl, pattern = "pdf", recursive = TRUE))

	file_list <- c(processed_file_list, plot_file_list)

	file.remove(file_list)
	}

pre_process_files <- function(ednl, fp2df_dict) {

	for (experiment_directory_name in ednl) {
		experiment_name <- strsplit(experiment_directory_name, '\\/', 
				fixed = FALSE, perl = FALSE, useBytes = FALSE)
		experiment_name <- tail(experiment_name[[1]], n=1)
		
		msg <- paste("Pre-processing data files from experiment \"", 
				experiment_name, "\"...", sep = '')
		cat(msg, sep='\n')
	
		experiment_file_list <- get_experiment_file_list(experiment_name, fp2df_dict)

		for (experiment_file in experiment_file_list) {
	
			full_experiment_file_name <- paste(experiment_directory_name, '/', 
					experiment_file, sep = '')
	
			processed_experiment_file_name <- paste(experiment_directory_name, "/processed_", 
					experiment_file, sep = '')
	
			if (file.exists(processed_experiment_file_name)){		
				msg <- paste("File \"", processed_experiment_file_name, 
						"\" already exists. Skipping pre-processing...", sep = '')
				cat(msg, sep='\n')
	
				} else {
				msg <- paste("Creating file \"", processed_experiment_file_name, "\"...", sep = '')
				cat(msg, sep='\n')
				file_contents <- read.csv(file = full_experiment_file_name, 
						head = TRUE, comment.char = "#", blank.lines.skip = "true")

				# Create a new column, containing the experiment id
				file_contents <- within(file_contents, "expid" <- experiment_name)
				if ("name" %in% names(file_contents) & 
						"role" %in% names(file_contents)) {

					# Create another column, containing a combined string for "full_obj_name"
					file_contents <- within(file_contents, 
							"full_obj_name" <- paste(file_contents$name, 
									file_contents$role, file_contents$aidrs_name, 
									file_contents$expid, sep = '|'))
					}
	
				# The "relative time" column is created only for "trace" files.
				if ("command_originated" %in% names(file_contents)) {
					file_contents <- within(file_contents, 
							"relative_time" <- (file_contents$command_originated - file_contents$command_originated[1])/60)	
					} 

				# For all other files (VM_runtime_app, VM_runtime_os, 
				# VM_management and HOST_runtime_os) the time is already relative.
				# All that has to be done is divide the relative time by the selected
				# time unit (e.g., minutes)
				if ("time" %in% names(file_contents)) {
					file_contents <- within(file_contents, 
							"relative_time" <- (file_contents$time/time_unit))				
					}
				
				# These columns, only for "VM_management" files, are later used
				# to create the vertical bars plotted on top of the VM_runtime_app
				# metrics.
				if ("mgt_001_provisioning_request_originated" %in% names(file_contents)) {

					file_contents <- within(file_contents, 
							"vm_arrival_start" <- (file_contents$mgt_001_provisioning_request_originated / time_unit))				

					file_contents <- within(file_contents, 
							"vm_arrival_end" <- ((file_contents$mgt_001_provisioning_request_originated + 
											file_contents$mgt_002_provisioning_request_sent +
											file_contents$mgt_003_provisioning_request_completed +
											file_contents$mgt_004_network_acessible + 
											file_contents$mgt_005_file_transfer +
											file_contents$mgt_006_application_start) / time_unit))

					file_contents <- within(file_contents, 
							"vm_arrival_diff" <- ((file_contents$vm_arrival_end - file_contents$vm_arrival_start) * time_unit))

					file_contents <- within(file_contents, 
							"vm_departure_start" <- (file_contents$mgt_901_deprovisioning_request_originated / time_unit))				
					
					file_contents <- within(file_contents, 
							"vm_departure_end" <- ((file_contents$mgt_901_deprovisioning_request_originated + 
											file_contents$mgt_902_deprovisioning_request_sent +
											file_contents$mgt_903_deprovisioning_request_completed) / time_unit))
					
					file_contents <- within(file_contents, 
							"vm_departure_diff" <- ((file_contents$vm_departure_end - file_contents$vm_departure_start) * time_unit))
					
					file_contents <- within(file_contents, 
								"partial_obj_name" <- paste(file_contents$role, 
										file_contents$aidrs_name, file_contents$expid, 
										sep = '|'))
					}					

				# Drop some unneeded columns before writing to file
				if ("time_h" %in% names(file_contents)) {
					drop_columns <- c("time","time_h","uuid")
					file_contents <- file_contents[,!(names(file_contents) %in% drop_columns)]
					}
	
				write.table(file_contents, processed_experiment_file_name, 
						sep=",", row.names = FALSE, col.names =TRUE) 
					}
				}	
			}
		}

create_data_frame <- function(ed, file_prefix) {
	
	actual_pattern <- paste("processed_", file_prefix, sep = '')
	processed_experiment_file_list <- list.files(path = ed, 
			pattern = actual_pattern, recursive = TRUE)
	
	aggregate_data_frame <- ''

	for (processed_experiment_file_name in processed_experiment_file_list) {
		partial_data_frame <- read.csv(file = processed_experiment_file_name, 
				head = TRUE, comment.char = "#", blank.lines.skip = "true")

		if (length(aggregate_data_frame) > 1) {
			aggregate_data_frame <- rbind(partial_data_frame, aggregate_data_frame)
			} else {
			aggregate_data_frame <- partial_data_frame
			}
		}

	return(aggregate_data_frame)
	}

plot_management_data <- function(mmdf, ed, en, vmn, sps) {
	
	if (en == "all") {
		selected_expid = c(levels(mmdf$expid))
		} else {
		selected_expid = c(en)
		}

	if (vmn == "all") {
		selected_vm_name = c(levels(mmdf$name))
		} else {
		selected_vm_name = c(vm)
		}

	################## START Provisioning vs VM ##################
	prov_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("full_obj_name", 
					"mgt_002_provisioning_request_sent", 
					"mgt_003_provisioning_request_completed", 
					"mgt_004_network_acessible", 
					"mgt_005_file_transfer", 
					"mgt_006_application_start", 
					"name", "vm_arrival_diff"))

	prov_lat_data <- prov_lat_data[!is.na(prov_lat_data$vm_arrival_diff),]

	number_of_vms <- length(prov_lat_data$name)

	selected_vms <- c(c("1", "2", "3"), seq(number_of_vms - 2, number_of_vms))

	if (number_of_vms > 6 ) {
		msg <- paste("WARNING: The number of VMs is too large (", number_of_vms, 
				"). Will", " plot only the 3 smallest and the 3 largest ", 
				"provisioning time", sep = '')
		cat(msg, sep='\n')

		prov_lat_data <- prov_lat_data[order(prov_lat_data$vm_arrival_diff), ]
		rownames(prov_lat_data) <- NULL
		prov_lat_data <- prov_lat_data[selected_vms,]
		number_of_vms <- length(prov_lat_data$name)		
		}

	columns_remove <- c("name", "vm_arrival_diff")
	prov_lat_data <- prov_lat_data[,!(names(prov_lat_data) %in% columns_remove)]
	prov_lat_data <- melt(prov_lat_data, id.vars="full_obj_name")

	# Plot provisioning latency
	prov_lat_plot_title <- paste("Provisioning Latency for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expid, "\"", sep = '')
	cat(prov_lat_plot_title, sep='\n')

	prov_lat_plot <- ggplot(prov_lat_data, 
					aes(x=full_obj_name, y=value, fill=variable)) + 
			geom_bar(stat='identity') + xlab("VM name") + 
			ylab("Provisioning Latency (seconds)") + 
			labs(title = prov_lat_plot_title)

	output_pdf_plot(ed, en, prov_lat_plot, '', sps, number_of_vms)
	################## END Provisioning vs VM ##################

	################## START Provisioning vs VApp Submitter ##################
	agg_prov_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("partial_obj_name", 
					"vm_arrival_diff"))

	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$vm_arrival_diff),]

	agg_prov_lat_data <- data.table(agg_prov_lat_data)
	
	agg_prov_lat_data <- agg_prov_lat_data[,list(avg = mean(vm_arrival_diff)), by = "partial_obj_name"]

	agg_prov_lat_data <- melt(agg_prov_lat_data, id.vars="partial_obj_name")

	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$value),]
	
	agg_prov_lat_data <- agg_prov_lat_data[as.numeric(agg_prov_lat_data$value) > 0,]	
	
	# Plot provisioning latency
	agg_prov_lat_plot_title <- paste("Average Provisioning Latency for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expid, "\"", sep = '')
	cat(agg_prov_lat_plot_title, sep='\n')

	agg_prov_lat_plot <- ggplot(agg_prov_lat_data, 
					aes(x = partial_obj_name, y = value, fill = variable)) + 
			geom_bar(stat='identity') + xlab("VM role|submitter|expid") + 
			ylab("Average Provisioning Latency (seconds)") + 
			labs(title = agg_prov_lat_plot_title)

	output_pdf_plot(ed, en, agg_prov_lat_plot, '', sps, number_of_vms)
	################## END Provisioning vs VApp Submitter ##################	

	################## START Provisioning Failures vs VApp Submitter ##################
	agg_prov_fail_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("partial_obj_name", 
					"vm_arrival_diff", "vm_departure_diff"))

	#### START Arrival Failure count ####
	tmp_vms_arrival_fail <- agg_prov_fail_data
	
	tmp_vms_arrival_fail[!is.na(tmp_vms_arrival_fail$vm_arrival_diff), ]$vm_arrival_diff <- 0

	if (is.na(tmp_vms_arrival_fail$vm_arrival_diff)) {

		tmp_vms_arrival_fail[is.na(tmp_vms_arrival_fail$vm_arrival_diff), ]$vm_arrival_diff <- 1
		}
		
	tmp_vms_arrival_fail <- data.table(tmp_vms_arrival_fail)

	tmp_vms_arrival_fail <- tmp_vms_arrival_fail[,list(total_arrival_failures = sum(vm_arrival_diff)), by = "partial_obj_name"]
	#### END Arrival Failure count ####
	
	#### START Arrival Success count ####
	tmp_vms_arrival_success <- agg_prov_fail_data

	tmp_vms_arrival_success[!is.na(tmp_vms_arrival_success$vm_arrival_diff), ]$vm_arrival_diff <- 1

	if (is.na(tmp_vms_arrival_success$vm_arrival_diff)) {
		tmp_vms_arrival_success[is.na(tmp_vms_arrival_success$vm_arrival_diff), ]$vm_arrival_diff <- 0
	}

	tmp_vms_arrival_success <- data.table(tmp_vms_arrival_success)
	
	tmp_vms_arrival_success <- tmp_vms_arrival_success[,list(total_arrival_successes = sum(vm_arrival_diff)), by = "partial_obj_name"]
	#### END Arrival Success count ####
	
	#### START Departure Failure count ####
	tmp_vms_departure_fail <- subset(agg_prov_fail_data, 
			!is.na(vm_arrival_diff), select = c("partial_obj_name", 
					"vm_arrival_diff", "vm_departure_diff"))
	
	tmp_vms_departure_fail[!is.na(tmp_vms_departure_fail$vm_departure_diff), ]$vm_departure_diff <- 0
	
	if (is.na(tmp_vms_departure_fail$vm_departure_diff)) {
		
		tmp_vms_departure_fail[is.na(tmp_vms_departure_fail$vm_departure_diff), ]$vm_departure_diff <- 1
	}
	
	tmp_vms_departure_fail <- data.table(tmp_vms_departure_fail)
	
	tmp_vms_departure_fail <- tmp_vms_departure_fail[,list(total_departure_failures = sum(vm_departure_diff)), by = "partial_obj_name"]
	#### END Departure Failure count ####

	#### START Departure Success count ####

	tmp_vms_departure_success <- subset(agg_prov_fail_data, 
			!is.na(vm_arrival_diff), select = c("partial_obj_name", 
					"vm_arrival_diff", "vm_departure_diff"))

	tmp_vms_departure_success[!is.na(tmp_vms_departure_success$vm_departure_diff), ]$vm_departure_diff <- 1
	
	if (is.na(tmp_vms_departure_success$vm_departure_diff)) {
		tmp_vms_departure_success[is.na(tmp_vms_departure_success$vm_departure_diff), ]$vm_departure_diff <- 0
	}
	
	tmp_vms_departure_success <- data.table(tmp_vms_departure_success)
	
	tmp_vms_departure_success <- tmp_vms_departure_success[,list(total_departure_successes = sum(vm_departure_diff)), by = "partial_obj_name"]	
	#### START Departure Failure count ####

	arrivals <- merge(tmp_vms_arrival_fail, tmp_vms_arrival_success, by="partial_obj_name")
	departures <- merge(tmp_vms_departure_fail, tmp_vms_departure_success, by="partial_obj_name")
	
	agg_prov_fail_data <- merge(arrivals, departures, by="partial_obj_name")
	
	agg_prov_fail_data <- melt(agg_prov_fail_data, id.vars="partial_obj_name")

	# Plot provisioning latency
	agg_prov_fail_plot_title <- paste("Provisioning Successes + Failures for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expid, "\"", sep = '')
	cat(agg_prov_fail_plot_title, sep='\n')

	agg_prov_fail_plot <- ggplot(agg_prov_fail_data, 
					aes(x = partial_obj_name, y = value, fill = variable)) + 
			geom_bar(stat='identity', position = "dodge") + xlab("VM role|submitter|expid") + 
			ylab("Number of Provisioning Successes + Failures") + 
			labs(title = agg_prov_fail_plot_title)

	output_pdf_plot(ed, en, agg_prov_fail_plot, '', sps, number_of_vms)	
	################## END Provisioning Failures vs VApp Submitter ##################
	}

plot_runtime_application_data <- function(ramdf, ed, en, vmn, vmadl, xati, yati,
		sps) {

	if (en == "all") {
		selected_expid = c(levels(ramdf$expid))
		} else {
		selected_expid = c(en)
		}
	
	if (vmn == "all") {
		selected_vm_name = c(levels(ramdf$name))
		} else {
		selected_vm_name = c(vm)
		}

	if (vmadl == "none") {
		vmasl <- c(0)
		vmael <- c(0)
	    } else {
		vmasl <- c(vmadl$vm_arrival_start)
		vmael <- c(vmadl$vm_arrival_end)
		}

	metric_types <- c("app_latency","app_throughput", "app_bandwidth")
	
	metric_names <- c("Latency (ms)", "Throughput (tps)", "Bandwidth (Mbps)")
	
	metric_types2metric_names <- hash(metric_types, metric_names)	

	vapp_types = c(levels(ramdf$type))

	for (vapp_type in vapp_types) {

		for (metric_type in metric_types) {
			
			################## START Performance vs Time ##################
			perf_vs_time_data <- subset(ramdf, (expid %in% selected_expid) & 
							(name %in% selected_vm_name) & type == vapp_type, 
					select = c("relative_time", "full_obj_name", metric_type))

			perf_vs_time_data <- melt(perf_vs_time_data, id=c("relative_time", "full_obj_name"))

			# This cleanup will be improved later

			perf_vs_time_data <- perf_vs_time_data[!is.na(perf_vs_time_data$value),]		

			perf_vs_time_data <- perf_vs_time_data[as.numeric(perf_vs_time_data$value) > 0,]

			if (length(perf_vs_time_data$full_obj_name) > 1 ) {
				
				msg <- paste(metric_types2metric_names[[metric_type]], 
						" versus time for VM(s) \"", vmn, "\" on experiment \"", 
						en, "\"", sep = '')
				cat(paste(msg, "...", sep = ''), sep='\n')

				perf_vs_time_plot_title <- msg

				xy_lims <- plot_get_x_y_limits(en, perf_vs_time_data, xati, yati)
				
				perf_vs_time_plot <- ggplot(perf_vs_time_data, aes(x=relative_time, y=value, 
										colour=full_obj_name)) + geom_line() + 
						geom_point()  + 
						geom_vline(xintercept = vmasl, linetype=4, colour="black") +
						geom_vline(xintercept = vmael, linetype=1, colour="black") +
						xlab("Time (minutes)") + 
						ylab(metric_types2metric_names[[metric_type]]) + 
						labs(title = perf_vs_time_plot_title) + 
						scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]])

#				+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])

				output_pdf_plot(ed, en, perf_vs_time_plot, paste("vm_", 
								metric_type, "_vs_time_plot_", vapp_type, 
								sep = ''))

				} else {
					msg <- paste("No \"", metric_type, "\" versus time data found ",
					"for VApp type \"", vapp_type, "\" . Plot will not be generated",
					sep = '')
					cat(msg, sep='\n')
				}
				################## END Performance vs Time ##################
				
				################## START Performance vs Load ##################				
				perf_vs_load_data <- subset(ramdf, (expid %in% selected_expid) & 
								(name %in% selected_vm_name) & type == vapp_type, 
						select = c("full_obj_name", "app_load_level", metric_type))

				perf_vs_load_data <- data.table(perf_vs_load_data)
				
				perf_vs_load_data <- perf_vs_load_data[,list(avg = mean(get(metric_type))), 
						by = "app_load_level,full_obj_name"]

				perf_vs_load_data <- melt(perf_vs_load_data, id=c("app_load_level", "full_obj_name"))
			
				# This cleanup will be improved later
				
				perf_vs_load_data <- perf_vs_load_data[!is.na(perf_vs_load_data$value),]
				
				perf_vs_load_data <- perf_vs_load_data[as.numeric(perf_vs_load_data$value) > 0,]

				if (length(perf_vs_load_data$full_obj_name) > 1 ) {
					msg <- paste(metric_types2metric_names[[metric_type]], 
							" versus load for VM(s) \"", vmn, "\" on experiment \"",
							en, "\"", sep = '')

					cat(paste(msg, "...", sep = ''), sep='\n')

					perf_vs_load_plot_title <- msg

					xy_lims <- plot_get_x_y_limits(en, perf_vs_load_data, xati, yati)	
					
					perf_vs_load_plot <- ggplot(perf_vs_load_data, aes(x=app_load_level, 
											y=value, colour=full_obj_name)) + geom_line() + 
							geom_point()  + 
							xlab("Load Level") + 
							ylab(metric_types2metric_names[[metric_type]]) + 
							labs(title = perf_vs_load_plot_title) + 
							scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]]) 
#				+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])

					output_pdf_plot(ed, en, perf_vs_load_plot, paste("vm_", 
									metric_type, "_vs_load_plot_", vapp_type, 
									sep = ''))	

					} else {
					msg <- paste("No \"", metric_type, "\" versus load data found ",
							"for VApp type \"", vapp_type, "\" . Plot will not be generated",
							sep = '')
					cat(msg, sep='\n')					
					}
				################## END Performance vs Load ##################
				}		
			}
		}

plot_runtime_os_data <- function(rosmdf, ed, en, nnl, xati, yati, sps) {

	data_frame_name <- deparse(substitute(rosmdf))
	if (data_frame_name == "hros_metrics") {
		node_type <- "HOST"
		} else {
		node_type <- "VM"	
		}

	experiment_node_list <- subset(rosmdf, expid == en, select = c("name"))

	if (nnl == "all") {
		experiment_node_list <- c(levels(factor(experiment_node_list$name)))
		} else {
		experiment_node_list <- c(nnl)
		}

	for (experiment_node in experiment_node_list) {

		experiment_node_name <- gsub("host_", '', experiment_node)

		################## START CPU Usage vs Time ##################
		os_cpu_data <- subset(rosmdf, (name %in% experiment_node_list), 
				select = c("relative_time", "cpu_user", "cpu_system", "cpu_wio"))

		os_cpu_data <- melt(os_cpu_data, id.vars="relative_time")

		os_cpu_data <- os_cpu_data[!is.na(os_cpu_data$value),]

		msg <- paste("CPU usage for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", en, sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_cpu_vs_time_plot_title <- msg

		xy_lims <- plot_get_x_y_limits(en, os_cpu_data, xati, yati)	

		os_cpu_vs_time_plot <- ggplot(os_cpu_data, aes(x = relative_time, y = value, 
								colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("CPU usage (%)") + 
				labs(title = os_cpu_vs_time_plot_title) + 
				scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]]) 
#				+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])

	
		output_pdf_plot(ed, en, os_cpu_vs_time_plot, '', sps)
		################## END CPU Usage vs Time ##################
		
		################## START Memory Usage vs Time ##################
		os_mem_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "mem_cached", 
						"mem_buffers", "mem_shared"))
		os_mem_data <- within(os_mem_data, 
				"mem_cached" <- abs(os_mem_data$mem_cached / (1024)))
		os_mem_data <- within(os_mem_data, 
				"mem_buffers" <- abs(os_mem_data$mem_buffers / (1024)))
		os_mem_data <- within(os_mem_data, 
				"mem_shared" <- abs(os_mem_data$mem_shared / (1024)))
		os_mem_data <- melt(os_mem_data, id.vars="relative_time")

		os_mem_data <- os_mem_data[!is.na(os_mem_data$value),]

		msg <- paste("Memory usage for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", en, sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_mem_plot_title <- msg

		xy_lims <- plot_get_x_y_limits(en, os_mem_data, xati, yati)
	
		os_mem_plot <- ggplot(os_mem_data, aes(x = relative_time, y = value, 
								colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("Mem usage (Megabytes)") + 
				labs(title = os_mem_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
	#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
	
		output_pdf_plot(ed, en, os_mem_plot, '', sps)
		################## END Memory Usage vs Time ##################

		# For network and disk, differences need to be calculated
		os_net_bw_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "bytes_out", 
						"bytes_in"))
	
		os_net_bw_data$bytes_out_delta <- c(NA, diff(os_net_bw_data$bytes_out))
		os_net_bw_data$bytes_in_delta <- c(NA, diff(os_net_bw_data$bytes_in))
		os_net_bw_data$time_delta <- c(1, diff(os_net_bw_data$relative_time))
		os_net_bw_data <- within(os_net_bw_data, 
				"Mbps_out" <- abs(os_net_bw_data$bytes_out_delta *
								8/ (1024 * 1024)/(os_net_bw_data$time_delta * 60)))
		os_net_bw_data <- within(os_net_bw_data, 
				"Mbps_in" <- abs(os_net_bw_data$bytes_in_delta *
								8 / (1024 * 1024)/(os_net_bw_data$time_delta * 60)))
		
		os_net_tput_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "pkts_out", "pkts_in"))
		os_net_tput_data$pkts_out_delta <- c(NA, diff(os_net_tput_data$pkts_out))
		os_net_tput_data$pkts_in_delta <- c(NA, diff(os_net_tput_data$pkts_in))
		os_net_tput_data$time_delta <- c(1, diff(os_net_tput_data$relative_time))
		os_net_tput_data <- within(os_net_tput_data, 
				"Pps_out" <- abs(os_net_tput_data$pkts_out_delta/(os_net_tput_data$time_delta * 60)))
		os_net_tput_data <- within(os_net_tput_data, 
				"Pps_in" <- abs(os_net_tput_data$pkts_in_delta/(os_net_tput_data$time_delta * 60)))
		
		os_dsk_bw_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "ds_KB_read", 
						"ds_KB_write"))
		os_dsk_bw_data$ds_KB_read_delta <- c(NA, diff(os_dsk_bw_data$ds_KB_read))
		os_dsk_bw_data$ds_KB_write_delta <- c(NA, diff(os_dsk_bw_data$ds_KB_write))
		os_dsk_bw_data$time_delta <- c(1, diff(os_dsk_bw_data$relative_time))
		os_dsk_bw_data <- within(os_dsk_bw_data, 
				"MBps_read" <- abs(os_dsk_bw_data$ds_KB_read_delta / 
								(1024)) / (os_dsk_bw_data$time_delta * 60))
		os_dsk_bw_data <- within(os_dsk_bw_data, 
				"MBps_write" <- abs(os_dsk_bw_data$ds_KB_write_delta / 
								(1024)) / (os_dsk_bw_data$time_delta * 60))
		
		os_dsk_tput_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "ds_ios_read", 
						"ds_ios_write"))
		os_dsk_tput_data$ds_ios_read_delta <- c(NA, diff(os_dsk_tput_data$ds_ios_read))
		os_dsk_tput_data$ds_ios_write_delta <- c(NA, diff(os_dsk_tput_data$ds_ios_write))
		os_dsk_tput_data$time_delta <- c(1, diff(os_dsk_tput_data$relative_time))
		os_dsk_tput_data <- within(os_dsk_tput_data, 
				"IOps_read" <- abs(os_dsk_tput_data$ds_ios_read_delta) / 
						(os_dsk_tput_data$time_delta * 60))
		os_dsk_tput_data <- within(os_dsk_tput_data, 
				"IOps_write" <- abs(os_dsk_tput_data$ds_ios_write_delta) / 
						(os_dsk_tput_data$time_delta * 60))
		
		# Some samples need to be discarded
		os_net_bw_data <- subset(os_net_bw_data, 
				Mbps_in < (1024 * 1024) | Mbps_out < (1024 * 1024), 
				select = c("relative_time", "Mbps_out", "Mbps_in"))
		os_net_tput_data <- subset(os_net_tput_data, 
				Pps_in < (1024 * 10) | Pps_out < (1024 * 10), 
				select = c("relative_time", "Pps_out", "Pps_in"))
		os_dsk_bw_data <- subset(os_dsk_bw_data, 
				MBps_read < (1024 * 1024) | MBps_write < (1024 * 10), 
				select = c("relative_time", "MBps_write", "MBps_read"))
		os_dsk_tput_data <- subset(os_dsk_tput_data, 
				IOps_read < (1024 * 1024) | IOps_write < (1024 * 10), 
				select = c("relative_time", "IOps_write", "IOps_read"))

		################## START Network Bandwidth vs Time ##################
		os_net_bw_data <- melt(os_net_bw_data, id.vars="relative_time")

		msg <- paste("Network bandwidth for ", node_type, " \"", experiment_node_name,
				"\" on experiment ", en, sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_net_bw_plot_title <- msg

		xy_lims <- plot_get_x_y_limits(en, os_net_bw_data, xati, yati)
		
		os_net_bw_plot <- ggplot(os_net_bw_data, aes(x = relative_time, y = value, 
								colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("Network bandwidth (Mbps)") + 
				labs(title = os_net_bw_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
	#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
	
		output_pdf_plot(ed, en, os_net_bw_plot, '', sps)
		################## END Network Bandwidth vs Time ##################

		################## START Network Throughput vs Time ##################			
		os_net_tput_data <- melt(os_net_tput_data, id.vars="relative_time")

		msg <- paste("Network throughput for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", en, sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_net_tput_plot_title <- msg

		xy_lims <- plot_get_x_y_limits(en, os_net_tput_data, xati, yati)
	
		os_net_tput_plot <- ggplot(os_net_tput_data, aes(x = relative_time, 
								y = value, 
								colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("Network throughput (packets/s)") + 
				labs(title = os_net_tput_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
	#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
	
		output_pdf_plot(ed, en, os_net_tput_plot, '', sps)
		################## END Network Throughput vs Time ##################

		################## START Disk Bandwidth vs Time ##################		
		os_dsk_bw_data <- melt(os_dsk_bw_data, id.vars="relative_time")

		msg <- paste("Disk bandwidth for ", node_type, "  \"", experiment_node_name, 
				"\" on experiment ", en, sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_dsk_bw_data_plot_title <- msg
		
		xy_lims <- plot_get_x_y_limits(en, os_dsk_bw_data, xati, yati)
		
		os_dsk_bw_plot <- ggplot(os_dsk_bw_data, aes(x = relative_time, y = value, 
								colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("Disk bandwidth (MB/s)") + 
				labs(title = os_dsk_bw_data_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
	#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
	
		output_pdf_plot(ed, en, os_dsk_bw_plot, '', sps)
		################## END Disk Bandwidth vs Time ##################

		################## START Disk Throughput vs Time ##################		
		os_dsk_tput_data <- melt(os_dsk_tput_data, id.vars="relative_time")

		msg <- paste("Disk throughput for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", en, sep='')
		cat(paste(msg, "...", sep = ''), sep='\n')

		os_dsk_tput_data_plot_title <- msg

		xy_lims <- plot_get_x_y_limits(en, os_dsk_tput_data, xati, yati)
		
		os_dsk_tput_plot <- ggplot(os_dsk_tput_data, aes(x = relative_time, 
								y = value, colour = variable)) + 
				geom_point() + 
				xlab("Time (minutes)") + 
				ylab("Disk throughput (IO/s)") + 
				labs(title = os_dsk_bw_data_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
	#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
	
		output_pdf_plot(ed, en, os_dsk_tput_plot, '', sps)
		################## END Disk Throughput vs Time ##################	
		}
	}