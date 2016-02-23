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
library(sciplot)
library(xtable)

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

output_table <- function(ed, en, pd, pn = '', latexout = TRUE) {
	
	if (en == "all") {
		en <- '/'
	} else {
		en <- paste('/', en, '/', sep = '')
	}
	
	if (pn == '') {
		file_name <- as.character(deparse(substitute(pd)))
	} else {
		file_name <- pn
	}
	
	file_location_csv <- paste(ed, en, file_name, "_table.csv", sep = '')
	file_location_tex <- paste(ed, en, file_name, "_table.tex", sep = '')
	
	write.table(pd, file_location_csv, sep=",", row.names = FALSE, col.names =TRUE)	
	
	if (latexout) {
		sink(file_location_tex)
		cat("\\documentclass{article}\n")
		
		cat("\\usepackage{graphics}\n")
		cat("\\usepackage[table]{xcolor}\n")
		cat("\\definecolor{lightray}{gray}{0.9}\n")
		cat("\\begin{document}\n")
		cat("\\scalebox{0.45}{\n")
		
		cat("\\rowcolors{1}{}{lightray}\n")
		
		invisible(print(xtable(pd),floating="FALSE",latex.environments=NULL))
		cat("}\n")
		cat("\\end{document}\n")
		sink()
	}
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
		determined_width <- round(vmn * 1)		
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
		x_end <- round(max(gdf$relative_time, na.rm=TRUE))
	} else {
		x_start <- round(min(gdf$app_load_level))
		x_end <- round(max(gdf$app_load_level, na.rm=TRUE))
	}
	
	x_limits <- c(x_start, x_end)
	
	x_step <- round((x_end - x_start)/xati)
	if (x_step < 1) {
		x_step <- 1
	}
	
	x_breaks <- seq(x_start, x_end, x_step)
	
	#y_start = min(gdf$value)
	y_start = 0
	
	if ("value" %in% column_names) {		
		y_end = round(max(gdf$value, na.rm=TRUE))
	} else {
		y_end = round(max(gdf$avg, na.rm=TRUE))
	}
	y_limits = c(y_start, y_end)
	
	y_step <- round((y_end - y_start)/yati)
	if (y_step < 1) {
		y_step <- 1
	}
	
	y_breaks <- seq(y_start, y_end, y_step)
	
	xy_limits <- list(x_limits, x_breaks, y_limits, y_breaks)
	
	return(xy_limits)
}

cleanup_files <- function(ednl) {
	msg <- paste("Cleaning up previously created \"processed\" files and ", 
			"plots...", sep = '')
	cat(msg, sep='\n')
	
	processed_file_list <- c(list.files(path = ednl, pattern = "processed_", 
					recursive = TRUE, full.name = TRUE))
	
#	plot_file_list <- c(list.files(path = ednl, pattern = "pdf", 
#					recursive = TRUE, full.name = TRUE))
	
#	tex_file_list <- c(list.files(path = ednl, pattern = "tex", 
#					recursive = TRUE, full.name = TRUE))
	
	produced_file_list <- c(list.files(path = ednl, 
					pattern = "^[0-9][0-9][0-9]_", recursive = TRUE, 
					full.name = TRUE))
	
#	table_file_list <- c(list.files(path = ednl, pattern = "_table", 
#					recursive = TRUE, full.name = TRUE))
	
#	file_list <- c(processed_file_list, plot_file_list, tex_file_list, table_file_list)
	file_list <- c(processed_file_list, produced_file_list)
	
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
		
		experiment_file_list <- get_experiment_file_list(experiment_name, 
				fp2df_dict)
		
		for (experiment_file in experiment_file_list) {
			
			full_experiment_file_name <- paste(experiment_directory_name, '/', 
					experiment_file, sep = '')
			
			processed_experiment_file_name <- paste(experiment_directory_name, 
					"/processed_", experiment_file, sep = '')
			
			if (file.exists(processed_experiment_file_name)){		
				msg <- paste("File \"", processed_experiment_file_name, 
						"\" already exists. Skipping pre-processing...", sep = '')
				cat(msg, sep='\n')
				
			} else {
				msg <- paste("Creating file \"", processed_experiment_file_name,
						"\"...", sep = '')
				cat(msg, sep='\n')
				
				file_contents <- read.csv(file = full_experiment_file_name, 
						head = TRUE, comment.char = "#", blank.lines.skip = "true")

				experiment_name_hash <- digest(object = experiment_name, algo = "crc32", serialize = FALSE)
				
				# Create a new column, containing the experiment id				
				file_contents <- within(file_contents, "expid" <- experiment_name_hash)
				file_contents <- within(file_contents, "experiment_name" <- experiment_name)
				
				if ("name" %in% names(file_contents) & 
						"role" %in% names(file_contents)) {
					
					# Create another column, containing a combined string for "full_obj_name"
					file_contents <- within(file_contents, 
							"full_obj_name" <- paste(
									file_contents$name, 
									file_contents$role, 
									file_contents$host_name, 
									file_contents$aidrs_name, 
									file_contents$expid, 
									sep = '|'))
					
					file_contents <- within(file_contents, 
							"partial_obj_name1" <- paste(
									file_contents$role, 
									file_contents$aidrs_name,
									file_contents$expid, 
									sep = '|'))
					
				}

				if ("name" %in% names(file_contents) & 
						"host_name" %in% names(file_contents)) {				
					
					file_contents <- within(file_contents, 
							"partial_obj_name2" <- paste(
									file_contents$role, 
									file_contents$host_name,
									file_contents$expid, 
									sep = '|'))					
				}
					
				# The "relative time" column is created only for "trace" files.
				if ("command_originated" %in% names(file_contents)) {
					file_contents <- within(file_contents, 
							"relative_time" <- (file_contents$command_originated 
										- file_contents$command_originated[1]) /
									time_unit)
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
							"vm_arrival_start" <- 
									(file_contents$mgt_001_provisioning_request_originated /
										time_unit))				
					
					file_contents <- within(file_contents, 
							"vm_arrival_end" <- ((file_contents$mgt_001_provisioning_request_originated + 
											file_contents$mgt_002_provisioning_request_sent +
											file_contents$mgt_003_provisioning_request_completed +
											file_contents$mgt_004_network_acessible + 
											file_contents$mgt_005_file_transfer +
											file_contents$mgt_006_instance_preparation +											
											file_contents$mgt_007_application_start) / time_unit))
					
					file_contents <- within(file_contents, 
							"vm_arrival_diff" <- ((file_contents$vm_arrival_end - 
											file_contents$vm_arrival_start) * time_unit))
					
					file_contents <- within(file_contents, 
							"vm_departure_start" <- 
									(file_contents$mgt_901_deprovisioning_request_originated /
										time_unit))				
					
					file_contents <- within(file_contents, 
							"vm_departure_end" <- ((file_contents$mgt_901_deprovisioning_request_originated + 
											file_contents$mgt_902_deprovisioning_request_sent +
											file_contents$mgt_903_deprovisioning_request_completed) /
										time_unit))
					
					file_contents <- within(file_contents, 
							"vm_departure_diff" <- ((file_contents$vm_departure_end - 
											file_contents$vm_departure_start) * 
										time_unit))
					
					file_contents <- within(file_contents, 
							"vm_capture_start" <- 
									(file_contents$mgt_101_capture_request_originated / 
										time_unit))	
					
					file_contents <- within(file_contents, 
							"vm_capture_end" <- ((file_contents$mgt_101_capture_request_originated + 
											file_contents$mgt_102_capture_request_sent +
											file_contents$mgt_103_capture_request_completed) /
										time_unit))
					
					file_contents <- within(file_contents, 
							"vm_capture_diff" <- ((file_contents$vm_capture_end - 
											file_contents$vm_capture_start) * 
										time_unit))
					
				}					
				
				# Drop some unneeded columns before writing to file
				if ("time_h" %in% names(file_contents)) {
					drop_columns <- c("time_h","uuid")
					file_contents <- file_contents[,!(names(file_contents) 
										%in% drop_columns)]
				}
				
				write.table(file_contents, processed_experiment_file_name, 
						sep=",", row.names = FALSE, col.names =TRUE) 
			}
		}	
	}
}

create_data_frame <- function(ed, expid, file_prefix) {
	
	if (expid == "all") {
		actual_path <- paste(ed)
	} else {
		actual_path <- paste(ed, '/', expid, sep = '')
	}
	
	actual_pattern <- paste("processed_", file_prefix, sep = '')
	
	processed_experiment_file_list <- list.files(path = actual_path, 
			pattern = actual_pattern, recursive = TRUE, full.names = TRUE)
	
	aggregate_data_frame <- ''
	
	for (processed_experiment_file_name in processed_experiment_file_list) {
		partial_data_frame <- read.csv(file = processed_experiment_file_name, 
				head = TRUE, comment.char = "#", blank.lines.skip = "true")
		
		if (length(aggregate_data_frame) > 1) {
			aggregate_data_frame <- rbind(partial_data_frame, 
					aggregate_data_frame)
		} else {
			aggregate_data_frame <- partial_data_frame
		}
	}
	
	return(aggregate_data_frame)
}

plot_trace_data <- function(tdf, ed, en, sps) {
	
	if (en == "all") {
		selected_expid = c(levels(tdf$expid))
		selected_expname = c(levels(tdf$experiment_name))
	} else {
		selected_expid = digest(object = en, algo = "crc32", serialize = FALSE)
		selected_expname = c(en)		
	}
	
	################## START Provisioning vs VM ##################
	trace_data <- subset(tdf, (expid %in% selected_expid), 
			select = c("vm_reservations", "vm_failed", "ai_reservations", 
					"ai_failed", "relative_time"))
	
	trace_data <- within(trace_data, "ai_reservations" <- 
					ifelse(is.na(trace_data$ai_reservations), 0, 
							trace_data$ai_reservations))
	trace_data <- within(trace_data, "ai_failed" <- 
					ifelse(is.na(trace_data$ai_failed), 0, 
							trace_data$ai_failed))		
	trace_data <- within(trace_data, "ai_arriving" <- 
					ifelse(is.na(trace_data$ai_arriving), 0, 
							trace_data$ai_arriving))	
	trace_data <- within(trace_data, "vm_reservations" <- 
					ifelse(is.na(trace_data$vm_reservations), 0, 
							trace_data$vm_reservations))
	trace_data <- within(trace_data, "vm_failed" <- 
					ifelse(is.na(trace_data$vm_failed), 0, 
							trace_data$vm_failed))
	trace_data <- within(trace_data, "vm_arriving" <- 
					ifelse(is.na(trace_data$vm_arriving), 0, 
							trace_data$vm_arriving))
	
	if (sum(trace_data$ai_reservations) > 0) {
		columns <- c("ai_reservations", "ai_failed", "ai_arriving", 
				"relative_time")
	} else {
		if (sum(trace_data$vm_reservations) > 0) {
			columns <- c("vm_reservations", "vm_failed", "vm_arriving", 
					"relative_time")
		} else {
			columns <- c("vmc_reservations", "vmc_failed", "relative_time")
		}
	}
	
	trace_data <- subset(trace_data, relative_time > 0, 
			select = columns)
	
	output_table(ed, en, trace_data, "001_operations_vs_time")
	
	trace_data <- melt(trace_data, id.vars="relative_time")
	
	trace_plot_title <- paste("Trace data for experiment \"", selected_expname,
			"\" (", selected_expid, ")", sep = '')
	cat(trace_plot_title, sep='\n')
	
	cat(paste(round(max(trace_data$relative_time, na.rm=TRUE))), sep = '\n')
	cat(paste(round(max(trace_data$value, na.rm=TRUE))), sep = '\n')
	
	trace_data_plot <- ggplot(trace_data, 
					aes(x=relative_time, y=value, fill=variable)) + 
			geom_bar(stat='identity', position = "dodge") + 
			xlab("Time (minutes)") +
			ylab("Number of Objects") + 
			labs(title = trace_plot_title)
	
	output_pdf_plot(ed, en, trace_data_plot, "001_operations_vs_time", sps)
	################## END Provisioning vs VM ##################
}

plot_management_data <- function(mmdf, ed, en, vmn, sps, mnv) {

	if (en == "all") {
		selected_expid = c(levels(mmdf$expid))
		selected_expname = c(levels(mmdf$experiment_name))
	} else {
		selected_expid = digest(object = en, algo = "crc32", serialize = FALSE)
		selected_expname = c(en)		
	}
	
	if (vmn == "all") {
		selected_vm_name = c(levels(mmdf$name))
	} else {
		selected_vm_name = c(vm)
	}
	
	################## START Provisioning vs VM ##################
	msg <- paste("# Preparing Provisioning Latency for VMs.... #", sep = '')
	cat(msg, sep='\n')
	
	prov_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("full_obj_name", 
					"mgt_002_provisioning_request_sent", 
					"mgt_003_provisioning_request_completed", 
					"mgt_004_network_acessible", 
					"mgt_005_file_transfer", 
					"mgt_006_instance_preparation", 					
					"mgt_007_application_start", 
					"name", "vm_arrival_diff"))
	
	prov_lat_data <- prov_lat_data[!is.na(prov_lat_data$vm_arrival_diff),]
	
	output_table(ed, en, prov_lat_data, "002_individual_vm_provision_latency")
	
	number_of_vms <- length(prov_lat_data$name)
	
	#if (number_of_vms > mnv ) {
	#	selected_vms <- c(c("1", "2", "3"), seq(number_of_vms - 2, number_of_vms))
	#	msg <- paste("WARNING: The number of VMs is too large (", number_of_vms, 
	#			"). Will", " plot only the 3 smallest and the 3 largest ", 
	#			"provisioning time", sep = '')
	#	cat(msg, sep='\n')
		
	#	prov_lat_data <- prov_lat_data[order(prov_lat_data$vm_arrival_diff), ]
	#	rownames(prov_lat_data) <- NULL
	#	prov_lat_data <- prov_lat_data[selected_vms,]
	#	number_of_vms <- length(prov_lat_data$name)		
	#}

	# Plot provisioning latency
	prov_lat_plot_title <- paste("Provisioning Latency for all VM(s) \"", vmn, 
			"\" on experiment \"", selected_expname, "\" (", selected_expid, ")",
			sep = '')
	cat(prov_lat_plot_title, sep='\n')	
	
	columns_remove <- c("full_obj_name", "vm_arrival_diff")
	prov_lat_data <- prov_lat_data[,!(names(prov_lat_data) %in% columns_remove)]
	
	prov_lat_data <- within(prov_lat_data, 
			"name" <- as.integer(gsub("vm_", '', prov_lat_data$name)))
	prov_lat_data <- prov_lat_data[order(prov_lat_data$name), ]
	setnames(prov_lat_data, "name", "x_axis_id")
	prov_lat_data <- melt(prov_lat_data, id.vars="x_axis_id")		
	prov_lat_plot <- ggplot(prov_lat_data, 
					aes(x=x_axis_id, y=value, fill=variable)) + 
			geom_area(stat='identity') + 
			xlab("VM name") + 
			ylab("Provisioning Latency (seconds)") + 
			labs(title = prov_lat_plot_title)
	output_pdf_plot(ed, en, prov_lat_plot, "002_individual_vm_provision_latency",
			sps)

	#prov_lat_plot_title <- paste("Provisioning Latency for select VM(s) \"", vmn, 
	#		"\" on experiment \"", selected_expname, "\" (", selected_expid, ")",
	#		sep = '')
	#cat(prov_lat_plot_title, sep='\n')		
	
	#columns_remove <- c("name", "vm_arrival_diff")
	#prov_lat_data <- prov_lat_data[,!(names(prov_lat_data) %in% columns_remove)]
	#setnames(prov_lat_data, "full_obj_name", "x_axis_id")
	#prov_lat_data <- melt(prov_lat_data, id.vars="x_axis_id")		
	#prov_lat_plot <- ggplot(prov_lat_data, 
	#				aes(x=x_axis_id, y=value, fill=variable)) + 
	#		geom_bar(stat='identity', width=0.2) + xlab("VM name") + 
	#		ylab("Provisioning Latency (seconds)") +
	#		theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
	#		labs(title = prov_lat_plot_title)		

	#output_pdf_plot(ed, en, prov_lat_plot, "003_individual_vm_provision_latency",
	#		sps, number_of_vms)
	
	################## END Provisioning vs VM ##################

	if("osk_010_authenticate_time" %in% colnames(mmdf)) {
		################## START Provisioning vs VM (Cloud-Specific info) ##################
		msg <- paste("# Preparing Provisioning Latency for VMs (Cloud-Specific", 
				"information) .... #", sep = '')
		cat(msg, sep='\n')
		
		prov_cs_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
						(name %in% selected_vm_name), 
				select = c("full_obj_name", 
						"osk_001_tenant_creation_time",
						"osk_002_quota_update_time",
						"osk_003_user_creation_time",
						"osk_004_security_group_update_time",
						"osk_005_keypair_creation_time",
						"osk_006_net_creation_time",
						"osk_007_subnet_creation_time",
						"osk_008_router_creation_time",
						"osk_009_router_attachment",
						"osk_010_authenticate_time",
						"osk_011_check_existing_instance_time",
						"osk_012_get_flavors_time",
						"osk_013_get_imageid_time",
						"osk_014_get_netid_time",
						"osk_016_instance_creation_time",
						"osk_016_instance_scheduling_time",
						"osk_016_port_creation_time",
						"osk_017_create_fip_time",
						"osk_018_attach_fip_time",
						"name", "vm_arrival_diff"))
		
		prov_cs_lat_data <- prov_cs_lat_data[!is.na(prov_cs_lat_data$vm_arrival_diff),]
		
		output_table(ed, en, prov_lat_data, "003_individual_vm_provision_latency")
		
		number_of_vms <- length(prov_lat_data$name)	
		
		# Plot provisioning latency
		prov_cs_lat_plot_title <- paste("Provisioning Latency for all VM(s) (",
				"Cloud-Specific information\"", vmn, "\" on experiment \"", 
				selected_expname, "\" (", selected_expid, ")", sep = '')
		cat(prov_cs_lat_plot_title, sep='\n')	
		
		columns_remove <- c("full_obj_name", "vm_arrival_diff")
		prov_cs_lat_data <- prov_cs_lat_data[,!(names(prov_cs_lat_data) %in% columns_remove)]
		
		prov_cs_lat_data <- within(prov_cs_lat_data, 
				"name" <- as.integer(gsub("vm_", '', prov_cs_lat_data$name)))
		prov_cs_lat_data <- prov_cs_lat_data[order(prov_cs_lat_data$name), ]
		setnames(prov_cs_lat_data, "name", "x_axis_id")
		prov_cs_lat_data <- melt(prov_cs_lat_data, id.vars="x_axis_id")		
		prov_cs_lat_plot <- ggplot(prov_cs_lat_data, 
						aes(x=x_axis_id, y=value, fill=variable)) + 
				geom_area(stat='identity') + 
				xlab("VM name") + 
				ylab("Provisioning Latency (seconds)") + 
				labs(title = prov_cs_lat_plot_title)
		output_pdf_plot(ed, en, prov_cs_lat_plot, "003_individual_vm_provision_latency",
				sps)
		################## END Provisioning vs VM ##################
	}

	################## START Provisioning vs VApp Submitter ##################
	msg <- paste("# Preparing Average Provisioning Latency for VMs.... #", sep = '')
	cat(msg, sep='\n')
	
	agg_prov_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("partial_obj_name1", 
					"vm_arrival_diff"))

	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$vm_arrival_diff),]
	
	agg_prov_lat_data <- data.table(agg_prov_lat_data)
	
	agg_prov_lat_data <- agg_prov_lat_data[,list(avg = mean(vm_arrival_diff), 
					sd=sd(vm_arrival_diff), se=se(vm_arrival_diff)), by = "partial_obj_name1"]
	
	output_table(ed, en, agg_prov_lat_data, "004_average_vm_provision_latency")
	
	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$avg),]
	
	agg_prov_lat_data <- agg_prov_lat_data[as.numeric(agg_prov_lat_data$avg) > 0,]	
	
	# Plot provisioning latency
	agg_prov_lat_plot_title <- paste("Average Provisioning Latency (per-Submmiter) for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expname, "\" (", selected_expid, ")", sep = '')
	cat(agg_prov_lat_plot_title, sep='\n')
	
	agg_prov_lat_plot <- ggplot(agg_prov_lat_data, aes(x = partial_obj_name1, 
							y = avg, fill=partial_obj_name1)) + 
			geom_bar(stat='identity', width=0.2) + xlab("VM role|submitter|expid") + 
			geom_errorbar(aes(ymin=avg-se, ymax=avg+se), width=.1) +
			ylab("Average Provisioning Latency (seconds)") + 
			labs(title = agg_prov_lat_plot_title)
	
	output_pdf_plot(ed, en, agg_prov_lat_plot, "004_average_vm_provision_latency", 
			sps, number_of_vms)
	################## END Provisioning vs VApp Submitter ##################	

	################## START Provisioning vs Host ##################
	msg <- paste("# Preparing Average Provisioning Latency for VMs.... #", sep = '')
	cat(msg, sep='\n')
	
	agg_prov_lat_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("partial_obj_name2", 
					"vm_arrival_diff"))
	
	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$vm_arrival_diff),]
	
	agg_prov_lat_data <- data.table(agg_prov_lat_data)
	
	agg_prov_lat_data <- agg_prov_lat_data[,list(avg = mean(vm_arrival_diff), 
					sd=sd(vm_arrival_diff), se=se(vm_arrival_diff)), by = "partial_obj_name2"]
	
	output_table(ed, en, agg_prov_lat_data, "005_average_vm_provision_latency_per_host")
	
	agg_prov_lat_data <- agg_prov_lat_data[!is.na(agg_prov_lat_data$avg),]
	
	agg_prov_lat_data <- agg_prov_lat_data[as.numeric(agg_prov_lat_data$avg) > 0,]	
	
	# Plot provisioning latency
	agg_prov_lat_plot_title <- paste("Average Provisioning Latency (per-Host) for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expname, "\" (", selected_expid, ")", sep = '')
	cat(agg_prov_lat_plot_title, sep='\n')
	
	agg_prov_lat_plot <- ggplot(agg_prov_lat_data, aes(x = partial_obj_name2, 
							y = avg, fill=partial_obj_name2)) + 
			geom_bar(stat='identity', width=0.2) + xlab("VM role|host_name|expid") + 
			geom_errorbar(aes(ymin=avg-se, ymax=avg+se), width=.1) +
			ylab("Average Provisioning Latency (seconds)") + 
			theme(axis.text.x = element_text(angle = 45, hjust = 1)) +			
			labs(title = agg_prov_lat_plot_title)
	
	output_pdf_plot(ed, en, agg_prov_lat_plot, "005_average_vm_provision_latency_per_host", 
			sps, number_of_vms)
	################## END Provisioning vs Host ##################		
	
	
	################## START Provisioning Failures vs VApp Submitter ##################
	msg <- paste("# Provisioning Successes + Failures for VMs.... #", sep = '')
	cat(msg, sep='\n')	

	agg_prov_fail_data <- subset(mmdf, (expid %in% selected_expid) & 
					(name %in% selected_vm_name), 
			select = c("partial_obj_name1", 
					"vm_arrival_diff", "vm_departure_diff", "mgt_999_provisioning_request_failed"))

	#### START Arrival Failure count ####
	tmp_vms_arrival_fail <- agg_prov_fail_data
	
	tmp_vms_arrival_fail <- within(tmp_vms_arrival_fail, "vm_arrival_diff" <- 
					ifelse(is.na(tmp_vms_arrival_fail$vm_arrival_diff), 1, 0))
	
	tmp_vms_arrival_fail <- data.table(tmp_vms_arrival_fail)
	
	tmp_vms_arrival_fail <- tmp_vms_arrival_fail[,list(total_arrival_failures = 
							sum(vm_arrival_diff)), by = "partial_obj_name1"]
	
	#### END Arrival Failure count ####

	#### START Arrival Success count ####
	tmp_vms_arrival_success <- agg_prov_fail_data
	
	tmp_vms_arrival_success <- within(tmp_vms_arrival_success, "vm_arrival_diff" <- 
					ifelse(is.na(tmp_vms_arrival_success$vm_arrival_diff), 0, 1))
	
	tmp_vms_arrival_success <- data.table(tmp_vms_arrival_success)
	
	tmp_vms_arrival_success <- tmp_vms_arrival_success[,list(total_arrival_successes = 
							sum(vm_arrival_diff)), by = "partial_obj_name1"]
	#### END Arrival Success count ####

	#### START Departure Failure count ####
	tmp_vms_departure_fail <- subset(agg_prov_fail_data, 
			!is.na(vm_arrival_diff), select = c("partial_obj_name1", 
					"vm_arrival_diff", "vm_departure_diff"))
	
	tmp_vms_departure_fail <- within(tmp_vms_departure_fail, "vm_departure_diff" <- 
					ifelse(is.na(tmp_vms_departure_fail$vm_departure_diff), 1, 0))
	
	tmp_vms_departure_fail <- data.table(tmp_vms_departure_fail)
	
	tmp_vms_departure_fail <- tmp_vms_departure_fail[,list(total_departure_failures = 
							sum(vm_departure_diff)), by = "partial_obj_name1"]
	#### END Departure Failure count ####

	#### START Departure Success count ####
	tmp_vms_departure_success <- subset(agg_prov_fail_data, 
			!is.na(vm_arrival_diff), select = c("partial_obj_name1", 
					"vm_arrival_diff", "vm_departure_diff"))
	
	tmp_vms_departure_success <- within(tmp_vms_departure_success, "vm_departure_diff" <- 
					ifelse(is.na(tmp_vms_departure_success$vm_departure_diff), 0, 1))
	
	tmp_vms_departure_success <- data.table(tmp_vms_departure_success)
	
	tmp_vms_departure_success <- tmp_vms_departure_success[,list(total_departure_successes = 
							sum(vm_departure_diff)), by = "partial_obj_name1"]	
	#### END Departure Success count ####

	arrivals <- merge(tmp_vms_arrival_fail, tmp_vms_arrival_success, by="partial_obj_name1")
	departures <- merge(tmp_vms_departure_fail, tmp_vms_departure_success, by="partial_obj_name1")
	
	agg_prov_fail_data <- merge(arrivals, departures, by="partial_obj_name1")
	
	output_table(ed, en, agg_prov_fail_data, "005_total_vm_provision_failure")
	
	agg_prov_fail_data <- melt(agg_prov_fail_data, id.vars="partial_obj_name1")

	# Plot provisioning latency
	agg_prov_fail_plot_title <- paste("Provisioning Successes + Failures for VM(s) \"", vmn, 
			"\" on experiment \"", selected_expname, "\" (", selected_expid, ")", sep = '')
	cat(agg_prov_fail_plot_title, sep='\n')
	
	agg_prov_fail_plot <- ggplot(agg_prov_fail_data, 
					aes(x = partial_obj_name1, y = value, fill = variable)) + 
			geom_bar(stat='identity', position = "dodge", width=0.2) + xlab("VM role|submitter|expid") + 
			ylab("Number of Provisioning Successes + Failures") +
			theme(axis.text.x = element_text(angle = 45, hjust = 1)) +			
			labs(title = agg_prov_fail_plot_title)
	
	output_pdf_plot(ed, en, agg_prov_fail_plot, "005_total_vm_provision_failure", sps, number_of_vms)	
	################## END Provisioning Failures vs VApp Submitter ##################
}

plot_runtime_application_data <- function(ramdf, ed, en, vmn, vmel, xati, yati,
		sps) {
	
	if (en == "all") {
		selected_expid = c(levels(ramdf$expid))
		selected_expname = c(levels(ramdf$experiment_name))
	} else {
		selected_expid = digest(object = en, algo = "crc32", serialize = FALSE)
		selected_expname = c(en)		
	}
	
	if (vmn == "all") {
		selected_vm_name = c(levels(ramdf$name))
	} else {
		selected_vm_name = c(vm)
	}
	
	if (vmel == "none") {
		vmasl <- c(-1)
		vmael <- c(-1)
		vmcsl <- c(-1)
		vmcel <- c(-1)
	} else {
		vmasl <- c(vmel$vm_arrival_start)
		vmael <- c(vmel$vm_arrival_end)
		vmcsl <- c(vmel$vm_capture_start)
		vmcel <- c(vmel$vm_capture_end)		
	}
	
	metric_types <- c("app_latency","app_throughput", "app_bandwidth")
	
	metric_names <- c("Latency (ms)", "Throughput (tps)", "Bandwidth (Mbps)")
	
	metric_types2metric_names <- hash(metric_types, metric_names)	
	
	vapp_types = c(levels(ramdf$type))
	
	for (vapp_type in vapp_types) {
		
		for (metric_type in metric_types) {
			
			if (metric_type == "app_latency") {
				prefix = "007_"
			} else if (metric_type == "app_throughput") {
				prefix = "008_"
			} else {
				prefix = "009_"
			}
			
			################## START Performance vs Time ##################
			perf_vs_time_data <- subset(ramdf, (expid %in% selected_expid) & 
							(name %in% selected_vm_name) & type == vapp_type, 
					select = c("relative_time", "full_obj_name", metric_type))
			
			output_table(ed, en, perf_vs_time_data, paste(prefix, "vm_",
							metric_type, "_vs_time_data_", vapp_type,
							sep = ''))
			
			perf_vs_time_data <- melt(perf_vs_time_data, id=c("relative_time", "full_obj_name"))
			
			# This cleanup will be improved later
			
			perf_vs_time_data <- perf_vs_time_data[!is.na(perf_vs_time_data$value),]		
			
			perf_vs_time_data <- perf_vs_time_data[as.numeric(perf_vs_time_data$value) > 0,]
			
			if (length(perf_vs_time_data$full_obj_name) > 1 ) {
				
				msg <- paste(metric_types2metric_names[[metric_type]], 
						" versus time for VM(s) \"", vmn, "\" on experiment \"", 
						selected_expname, "\" (", selected_expid, ")", sep = '')

				cat(paste(msg, "...", sep = ''), sep='\n')
				
				perf_vs_time_plot_title <- msg
				
				xy_lims <- plot_get_x_y_limits(en, perf_vs_time_data, xati, yati)
				
				perf_vs_time_plot <- ggplot(perf_vs_time_data, aes(x=relative_time, y=value, 
										colour=full_obj_name)) + geom_line() + 
						geom_point()  + 
						geom_vline(xintercept = vmasl, linetype=4, colour="black") +
						geom_vline(xintercept = vmael, linetype=1, colour="black") +
						geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
						geom_vline(xintercept = vmcel, linetype=5, colour="black") +						
						xlab("Time (minutes)") + 
						ylab(metric_types2metric_names[[metric_type]]) + 
						labs(title = perf_vs_time_plot_title) + 
						scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]])
				
#				+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])
				
				output_pdf_plot(ed, en, perf_vs_time_plot, paste(prefix, "vm_", 
								metric_type, "_vs_time_plot_", vapp_type, 
								sep = ''))
				
			} else {
				msg <- paste("No \"", metric_type, "\" versus time data found ",
						"for VApp type \"", vapp_type, "\". Plot will not be generated",
						sep = '')
				cat(msg, sep='\n')
			}
			################## END Performance vs Time ##################
			
			################## START Performance vs Load ##################				
			perf_vs_load_data <- subset(ramdf, (expid %in% selected_expid) & 
							(name %in% selected_vm_name) & type == vapp_type, 
					select = c("full_obj_name", "app_load_level", metric_type))
			
			perf_vs_load_data <- data.table(perf_vs_load_data)
			
			perf_vs_load_data <- perf_vs_load_data[,list(avg = mean(get(metric_type)), 
							sd = sd(get(metric_type)), se = se(get(metric_type))),
					by = "app_load_level,full_obj_name"]
			
			output_table(ed, en, perf_vs_load_data, paste(prefix, "vm_", 
							metric_type, "_vs_load_data_", vapp_type, sep = ''))
			
			total_load_levels <- length(levels(factor(perf_vs_load_data$app_load_level)))
			
			valid_values <- !all(is.na(perf_vs_load_data$avg))
			
			if (total_load_levels > 0 & valid_values) {
#				perf_vs_load_data <- melt(perf_vs_load_data, id=c("app_load_level", "full_obj_name"))
				
				# This cleanup will be improved later
				
#				perf_vs_load_data <- perf_vs_load_data[!is.na(perf_vs_load_data$value),]
				
				perf_vs_load_data <- perf_vs_load_data[as.numeric(perf_vs_load_data$avg) > 0,]					
			} else {
				msg <- paste(metric_types2metric_names[[metric_type]], 
						" has only one load level for VM(s) \"", vmn, "\" on experiment \"",
						en, "\". Will not produce a plot for this metric", sep = '')
				cat(paste(msg, "...", sep = ''), sep='\n')
			}
			
			total_load_samples <- length(perf_vs_load_data$full_obj_name)
			
			if (valid_values) {

				msg <- paste(metric_types2metric_names[[metric_type]], 
						" versus load for VM(s) \"", vmn, "\" on experiment \"",
						selected_expname, "\" (", selected_expid, ")", sep = '')
				
				cat(paste(msg, "...", sep = ''), sep='\n')
				
				perf_vs_load_plot_title <- msg
				
				xy_lims <- plot_get_x_y_limits(en, perf_vs_load_data, xati, yati)	
				
				perf_vs_load_plot <- ggplot(perf_vs_load_data, aes(x=app_load_level, 
										y=avg, colour=full_obj_name, fill = full_obj_name)) + 
						geom_point(size = 3)  + 
						geom_line() +
						geom_errorbar(aes(ymin=avg-se, ymax=avg+se), width=.1) +
						#						geom_bar(stat='identity', position = "dodge", width=.5) +
						xlab("Load Level") + 
						ylab(metric_types2metric_names[[metric_type]]) + 
						labs(title = perf_vs_load_plot_title) + 
						scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]]) 
				#			+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])
				
				output_pdf_plot(ed, en, perf_vs_load_plot, paste(prefix, "vm_", 
								metric_type, "_vs_load_plot_", vapp_type, 
								sep = ''))	
					
				if (total_load_samples > 1 & total_load_levels == 1) {
					
					msg <- paste(metric_types2metric_names[[metric_type]], 
							" versus VM for VM(s) \"", vmn, "\" on experiment \"",
							selected_expname, "\" (", selected_expid, ")", sep = '')
					
					cat(paste(msg, "...", sep = ''), sep='\n')
					
					perf_vs_load_plot_title <- msg
					
					xy_lims <- plot_get_x_y_limits(en, perf_vs_load_data, xati, yati)	
					
					perf_vs_load_data$obj_name <- unlist(lapply(strsplit(as.character(perf_vs_load_data$full_obj_name), "|", fixed=TRUE), "[", 1))
					
					perf_vs_load_plot <- ggplot(perf_vs_load_data, aes(x=obj_name, 
											y=avg, colour=full_obj_name, fill = full_obj_name)) + 
							geom_point(size = 3)  + 
							geom_line() +
							geom_errorbar(aes(ymin=avg-se, ymax=avg+se), width=.1) +
							#						geom_bar(stat='identity', position = "dodge", width=.5) +
							xlab("VM name") + 
							ylab(metric_types2metric_names[[metric_type]]) + 
							labs(title = perf_vs_load_plot_title) 
#							scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]]) 
					#			+ scale_y_continuous(limits = xy_lims[[3]], breaks = xy_lims[[4]])
					
					output_pdf_plot(ed, en, perf_vs_load_plot, paste(prefix, "vm_", 
									metric_type, "_vs_vm_plot_", vapp_type, 
									sep = ''))	
				}
			}
			################## END Performance vs Load ##################
		}		
	}
}

plot_runtime_os_data <- function(rosmdf, ed, en, nnl, xati, yati, sps, nel) {
	
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
		
		if (nel == "none") {
			lnel <- c(-1)
			vmasl <- c(-1)
			vmael <- c(-1)
			vmcsl <- c(-1)
			vmcel <- c(-1)
		} else {
			if ("vm_arrival_start" %in% names(nel)) {
				lnel <- subset(nel, host_name == experiment_node_name , 
						select = c("vm_arrival_start", "vm_arrival_end", "vm_capture_start", "vm_capture_end"))
				vmasl <- c(lnel$vm_arrival_start)
				vmael <- c(lnel$vm_arrival_end)
				vmcsl <- c(lnel$vm_capture_start)
				vmcel <- c(lnel$vm_capture_end)
				lnel <- c(-1)
			} else {
				vmasl <- c(-1)
				vmael <- c(-1)
				vmcsl <- c(-1)
				vmcel <- c(-1)
				lnel <- c(nel$relative_time)
			}
		}
		
		################## START CPU Usage vs Time ##################
		os_cpu_data <- subset(rosmdf, (name == experiment_node), 
				select = c("relative_time", "cpu_user", "cpu_system", "cpu_wio"))
		
		output_table(ed, en, os_cpu_data, paste("010_os_cpu_vs_time_data_", 
						experiment_node_name, sep = ''), FALSE)
		
		os_cpu_data <- melt(os_cpu_data, id.vars="relative_time")
		
		os_cpu_data <- os_cpu_data[!is.na(os_cpu_data$value),]
		
		msg <- paste("CPU usage for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')
		
		os_cpu_vs_time_plot_title <- msg
		
		xy_lims <- plot_get_x_y_limits(en, os_cpu_data, xati, yati)	
		
		os_cpu_vs_time_plot <- ggplot(os_cpu_data, aes(x = relative_time, y = value, 
								colour = variable, fill = variable)) + 
				geom_bar(stat='identity') + 
				geom_vline(xintercept = lnel, linetype=7, colour="black") +
				geom_vline(xintercept = vmasl, linetype=4, colour="black") +
				geom_vline(xintercept = vmael, linetype=1, colour="black") +
				geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
				geom_vline(xintercept = vmcel, linetype=5, colour="black") +					
				xlab("Time (minutes)") + 
				ylab("CPU usage (%)") + 
				labs(title = os_cpu_vs_time_plot_title) + 
				scale_x_continuous(limits = xy_lims[[1]], breaks = xy_lims[[2]])
		#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
		
		output_pdf_plot(ed, en, os_cpu_vs_time_plot, paste("008_os_cpu_vs_time_plot_",
						experiment_node_name, sep = ''), sps)
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
		
		output_table(ed, en, os_mem_data, paste("011_os_mem_vs_time_data_", 
						experiment_node_name, sep = ''), FALSE)
		
		os_mem_data <- melt(os_mem_data, id.vars="relative_time")
		
		os_mem_data <- os_mem_data[!is.na(os_mem_data$value),]
		
		msg <- paste("Memory usage for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')
		
		os_mem_vs_time_plot_title <- msg
		
		xy_lims <- plot_get_x_y_limits(en, os_mem_data, xati, yati)
		
		os_mem_vs_time_plot <- ggplot(os_mem_data, aes(x = relative_time, y = value, 
								colour = variable, fill = variable)) + 
				geom_bar(stat='identity') + 
				geom_vline(xintercept = lnel, linetype=7, colour="black") +
				geom_vline(xintercept = vmasl, linetype=4, colour="black") +
				geom_vline(xintercept = vmael, linetype=1, colour="black") +
				geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
				geom_vline(xintercept = vmcel, linetype=5, colour="black") +
				xlab("Time (minutes)") + 
				ylab("Mem usage (Megabytes)") + 
				labs(title = os_mem_vs_time_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
		#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
		
		output_pdf_plot(ed, en, os_mem_vs_time_plot, paste("009_os_mem_vs_time_plot_", 
						experiment_node_name, sep = ''), sps)
		################## END Memory Usage vs Time ##################
		
		# For network, swap and disk, differences need to be calculated
		###
		os_net_bw_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "bytes_out", "bytes_in"))
		
		os_net_bw_data$bytes_out_delta <- c(NA, diff(os_net_bw_data$bytes_out))
		os_net_bw_data$bytes_in_delta <- c(NA, diff(os_net_bw_data$bytes_in))
		
		os_net_bw_data <- within(os_net_bw_data, 
				"Mbps_out" <- abs((os_net_bw_data$bytes_out * 8) / (1024 * 1024)))
		os_net_bw_data <- within(os_net_bw_data, 
				"Mbps_in" <- abs((os_net_bw_data$bytes_in * 8) / (1024 * 1024)))
		
		####
		os_net_tput_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "pkts_out", "pkts_in"))
		
		os_net_tput_data <- within(os_net_tput_data, 
				"Pps_out" <- abs(os_net_tput_data$pkts_out))
		os_net_tput_data <- within(os_net_tput_data, 
				"Pps_in" <- abs(os_net_tput_data$pkts_in))
		
		os_net_bw_data <- subset(os_net_bw_data, 
				Mbps_in < (1024 * 1024) | Mbps_out < (1024 * 1024), 
				select = c("relative_time", "Mbps_out", "Mbps_in"))
		os_net_tput_data <- subset(os_net_tput_data, 
				Pps_in < (1024 * 10) | Pps_out < (1024 * 10), 
				select = c("relative_time", "Pps_out", "Pps_in"))
		
		###
		os_swap_bw_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "swap_KB_read", 
						"swap_KB_write"))
		os_swap_bw_data$swap_KB_read_delta <- c(NA, diff(os_swap_bw_data$swap_KB_read))
		os_swap_bw_data$swap_KB_write_delta <- c(NA, diff(os_swap_bw_data$swap_KB_write))
		
		os_swap_bw_data <- subset(os_swap_bw_data, 
				swap_KB_read_delta > 0 | swap_KB_write_delta > 0, 
				select = c("relative_time", "swap_KB_read_delta", "swap_KB_write_delta"))
		
		if (length(os_swap_bw_data$relative_time) > 0 ){
			###
			os_swap_bw_data$time_delta <- c(1, diff(os_swap_bw_data$relative_time))
			os_swap_bw_data <- within(os_swap_bw_data, 
					"MBps_read" <- abs(os_swap_bw_data$swap_KB_read_delta / 
									(1024 * os_swap_bw_data$time_delta * time_unit)))
			os_swap_bw_data <- within(os_swap_bw_data, 
					"MBps_write" <- abs(os_swap_bw_data$swap_KB_write_delta / 
									(1024 * os_swap_bw_data$time_delta * time_unit)))
			###
			os_swap_tput_data <- subset(rosmdf, name == experiment_node, 
					select = c("relative_time", "swap_ios_read", 
							"swap_ios_write"))
			os_swap_tput_data$swap_ios_read_delta <- c(NA, 
					diff(os_swap_tput_data$swap_ios_read))
			os_swap_tput_data$swap_ios_write_delta <- c(NA, 
					diff(os_swap_tput_data$swap_ios_write))
			
			os_swap_tput_data <- subset(os_swap_tput_data, 
					swap_ios_read_delta > 0 | swap_ios_write_delta > 0, 
					select = c("relative_time", "swap_ios_read_delta", 
							"swap_ios_write_delta"))
			
			os_swap_tput_data$time_delta <- c(1, diff(os_swap_tput_data$time))
			
			os_swap_tput_data <- within(os_swap_tput_data, 
					"IOps_read" <- abs(os_swap_tput_data$swap_ios_read_delta) / 
							(os_swap_tput_data$time_delta))
			os_swap_tput_data <- within(os_swap_tput_data, 
					"IOps_write" <- abs(os_swap_tput_data$swap_ios_write_delta) / 
							(os_swap_tput_data$time_delta))
			
			## Cleanup
			os_swap_bw_data <- subset(os_swap_bw_data, 
					MBps_read < (1024 * 1024) | MBps_write < (1024 * 1024), 
					select = c("relative_time", "MBps_write", "MBps_read"))		
			os_swap_tput_data <- subset(os_swap_tput_data, 
					IOps_read < (1024 * 1024) | IOps_write < (1024 * 10), 
					select = c("relative_time", "IOps_write", "IOps_read"))
			
			swap_activity <- TRUE
		} else {
			swap_activity <- FALSE
			msg <- paste("No Swap activity for ", node_type, " \"", 
					experiment_node_name, "\" on experiment ", en, 
					". Will not produce plots for swap", sep = '')
			cat(msg, sep='\n')
		}
		
		###
		os_dsk_bw_data <- subset(rosmdf, name == experiment_node, 
				select = c("relative_time", "ds_KB_read", 
						"ds_KB_write"))
		os_dsk_bw_data$ds_KB_read_delta <- c(NA, diff(os_dsk_bw_data$ds_KB_read))
		os_dsk_bw_data$ds_KB_write_delta <- c(NA, diff(os_dsk_bw_data$ds_KB_write))
		os_dsk_bw_data <- subset(os_dsk_bw_data, 
				ds_KB_read_delta > 0 | ds_KB_write_delta > 0, 
				select = c("relative_time", "ds_KB_read_delta", "ds_KB_write_delta"))
		
		if (length(os_dsk_bw_data$relative_time) > 0 ){
			
			os_dsk_bw_data$time_delta <- c(1, diff(os_dsk_bw_data$relative_time))
			
			os_dsk_bw_data <- within(os_dsk_bw_data, 
					"MBps_read" <- abs(os_dsk_bw_data$ds_KB_read_delta / 
									(1024 * os_dsk_bw_data$time_delta * time_unit)))
			
			os_dsk_bw_data <- within(os_dsk_bw_data, 
					"MBps_write" <- abs(os_dsk_bw_data$ds_KB_write_delta / 
									(1024 * os_dsk_bw_data$time_delta * time_unit)))
			
			###
			os_dsk_tput_data <- subset(rosmdf, name == experiment_node, 
					select = c("relative_time", "ds_ios_read", 
							"ds_ios_write"))
			os_dsk_tput_data$ds_ios_read_delta <- c(NA, 
					diff(os_dsk_tput_data$ds_ios_read))
			os_dsk_tput_data$ds_ios_write_delta <- c(NA, 
					diff(os_dsk_tput_data$ds_ios_write))
			os_dsk_tput_data <- subset(os_dsk_tput_data, 
					ds_ios_read_delta > 0 | ds_ios_write_delta > 0, 
					select = c("relative_time", "ds_ios_read_delta", 
							"ds_ios_write_delta"))
			
			os_dsk_tput_data$time_delta <- c(1, diff(os_dsk_tput_data$time))
			os_dsk_tput_data <- within(os_dsk_tput_data, 
					"IOps_read" <- abs(os_dsk_tput_data$ds_ios_read_delta) / 
							(os_dsk_bw_data$time_delta * time_unit))
			os_dsk_tput_data <- within(os_dsk_tput_data, 
					"IOps_write" <- abs(os_dsk_tput_data$ds_ios_write_delta) / 
							(os_dsk_bw_data$time_delta * time_unit))
			
			## Cleanup
			os_dsk_bw_data <- subset(os_dsk_bw_data, 
					MBps_read < (1024 * 1024) | MBps_write < (1024 * 1024), 
					select = c("relative_time", "MBps_write", "MBps_read"))
			os_dsk_tput_data <- subset(os_dsk_tput_data, 
					IOps_read < (1024 * 1024) | IOps_write < (1024 * 10), 
					select = c("relative_time", "IOps_write", "IOps_read"))
			
			disk_activity <- TRUE
			
		} else {
			disk_activity <- FALSE
			msg <- paste("No Disk activity for ", node_type, " \"", experiment_node_name, 
					"\" on experiment ", en, ". Will not produce plots for disk", sep = '')
			cat(msg, sep='\n')
		}
		
		################## START Network Bandwidth vs Time ##################
		
		output_table(ed, en, os_net_bw_data, paste("012_os_net_bw_vs_time_data_", 
						experiment_node_name, sep = ''), FALSE)
		
		os_net_bw_data <- melt(os_net_bw_data, id.vars="relative_time")
		
		msg <- paste("Network bandwidth for ", node_type, " \"", experiment_node_name,
				"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')
		
		os_net_bw_vs_time_plot_title <- msg
		
		xy_lims <- plot_get_x_y_limits(en, os_net_bw_data, xati, yati)
		
		os_net_bw_vs_time_plot <- ggplot(os_net_bw_data, aes(x = relative_time, y = value, 
								colour = variable, fill = variable)) + 
				geom_bar(stat = "identity", position = "dodge") + 
				geom_vline(xintercept = lnel, linetype=7, colour="black") +
				geom_vline(xintercept = vmasl, linetype=4, colour="black") +
				geom_vline(xintercept = vmael, linetype=1, colour="black") +
				geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
				geom_vline(xintercept = vmcel, linetype=5, colour="black") +
				xlab("Time (minutes)") + 
				ylab("Network bandwidth (Mbps)") + 
				labs(title = os_net_bw_vs_time_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
		#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
		
		output_pdf_plot(ed, en, os_net_bw_vs_time_plot, paste("010_os_net_bw_vs_time_plot_",
						experiment_node_name, sep = ''), sps)
		################## END Network Bandwidth vs Time ##################
		
		################## START Network Throughput vs Time ##################
		
		output_table(ed, en, os_net_tput_data, paste("011_os_net_tput_vs_time_data_", 
						experiment_node_name, sep = ''), FALSE)
		
		os_net_tput_data <- melt(os_net_tput_data, id.vars="relative_time")
		
		msg <- paste("Network throughput for ", node_type, " \"", experiment_node_name, 
				"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
		cat(paste(msg, "...", sep = ''), sep='\n')
		
		os_net_tput_vs_time_plot_title <- msg
		
		xy_lims <- plot_get_x_y_limits(en, os_net_tput_data, xati, yati)
		
		os_net_tput_vs_time_plot <- ggplot(os_net_tput_data, aes(x = relative_time, 
								y = value, colour = variable, fill = variable)) + 
				geom_bar(stat = "identity", position = "dodge") + 
				geom_vline(xintercept = lnel, linetype=7, colour="black") +
				geom_vline(xintercept = vmasl, linetype=4, colour="black") +
				geom_vline(xintercept = vmael, linetype=1, colour="black") +
				geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
				geom_vline(xintercept = vmcel, linetype=5, colour="black") +	
				xlab("Time (minutes)") + 
				ylab("Network throughput (packets/s)") + 
				labs(title = os_net_tput_vs_time_plot_title) + 
				scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
		#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
		
		output_pdf_plot(ed, en, os_net_tput_vs_time_plot, paste("011_os_net_tput_vs_time_plot_", 
						experiment_node_name, sep = ''), sps)
		################## END Network Throughput vs Time ##################
		
		if (swap_activity) {
			################## START Swap Bandwidth vs Time ##################
			
			output_table(ed, en, os_swap_bw_data, paste("013_os_swap_vs_time_data_", 
							experiment_node_name, sep = ''), FALSE)
			
			os_swap_bw_data <- melt(os_swap_bw_data, id.vars="relative_time")
			
			msg <- paste("Swap bandwidth for ", node_type, "  \"", experiment_node_name, 
					"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
			cat(paste(msg, "...", sep = ''), sep='\n')
			
			os_swap_bw_vs_time_data_plot_title <- msg
			
			xy_lims <- plot_get_x_y_limits(en, os_swap_bw_data, xati, yati)
			
			os_swap_bw_vs_time_plot <- ggplot(os_swap_bw_data, aes(x = relative_time, y = value, 
									colour = variable, fill = variable)) + 
					geom_bar(stat = "identity", position = "dodge") + 
					geom_vline(xintercept = lnel, linetype=7, colour="black") +
					geom_vline(xintercept = vmasl, linetype=4, colour="black") +
					geom_vline(xintercept = vmael, linetype=1, colour="black") +
					geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
					geom_vline(xintercept = vmcel, linetype=5, colour="black") +	
					xlab("Time (minutes)") + 
					ylab("Swap bandwidth (MB/s)") + 
					labs(title = os_swap_bw_vs_time_data_plot_title) + 
					scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
			#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
			
			output_pdf_plot(ed, en, os_swap_bw_vs_time_plot, paste("012_os_swap_bw_vs_time_plot_", 
							experiment_node_name, sep = ''), sps)
			################## END Swap Bandwidth vs Time ##################
			
			################## START Swap Throughput vs Time ##################
			
			output_table(ed, en, os_swap_tput_data, paste("014_os_swap_tput_vs_time_data_", 
							experiment_node_name, sep = ''), FALSE)
			
			os_swap_tput_data <- melt(os_swap_tput_data, id.vars="relative_time")
			
			msg <- paste("Swap throughput for ", node_type, " \"", experiment_node_name, 
					"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
			cat(paste(msg, "...", sep = ''), sep='\n')
			
			os_swap_tput_vs_time_data_plot_title <- msg
			
			xy_lims <- plot_get_x_y_limits(en, os_swap_tput_data, xati, yati)
			
			os_swap_tput_vs_time_plot <- ggplot(os_swap_tput_data, aes(x = relative_time, 
									y = value, colour = variable, fill = variable)) + 
					geom_bar(stat = "identity", position = "dodge") + 
					geom_vline(xintercept = lnel, linetype=7, colour="black") +
					geom_vline(xintercept = vmasl, linetype=4, colour="black") +
					geom_vline(xintercept = vmael, linetype=1, colour="black") +
					geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
					geom_vline(xintercept = vmcel, linetype=5, colour="black") +	
					xlab("Time (minutes)") + 
					ylab("Swap throughput (IO/s)") + 
					labs(title = os_swap_tput_vs_time_data_plot_title) + 
					scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
			#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
			
			output_pdf_plot(ed, en, os_swap_tput_vs_time_plot, paste("013_os_swap_tput_vs_time_plot_", 
							experiment_node_name, sep = ''), sps)
			################## END Swap Throughput vs Time ##################
		}
		
		if (disk_activity) {
			################## START Disk Bandwidth vs Time ##################
			
			output_table(ed, en, os_dsk_bw_data, paste("015_os_dsk_bw_vs_time_data_", 
							experiment_node_name, sep = ''), FALSE)
			
			os_dsk_bw_data <- melt(os_dsk_bw_data, id.vars="relative_time")
			
			msg <- paste("Disk bandwidth for ", node_type, "  \"", experiment_node_name, 
					"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
			cat(paste(msg, "...", sep = ''), sep='\n')
			
			os_dsk_bw_vs_time_data_plot_title <- msg
			
			xy_lims <- plot_get_x_y_limits(en, os_dsk_bw_data, xati, yati)
			
			os_dsk_bw_vs_time_plot <- ggplot(os_dsk_bw_data, aes(x = relative_time, y = value, 
									colour = variable, fill = variable)) + 
					geom_bar(stat = "identity", position = "dodge") + 
					geom_vline(xintercept = lnel, linetype=7, colour="black") +
					geom_vline(xintercept = vmasl, linetype=4, colour="black") +
					geom_vline(xintercept = vmael, linetype=1, colour="black") +
					geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
					geom_vline(xintercept = vmcel, linetype=5, colour="black") +	
					xlab("Time (minutes)") + 
					ylab("Disk bandwidth (MB/s)") + 
					labs(title = os_dsk_bw_vs_time_data_plot_title) + 
					scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
			#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
			
			output_pdf_plot(ed, en, os_dsk_bw_vs_time_plot, paste("014_os_dsk_bw_vs_time_plot_", 
							experiment_node_name, sep = ''), sps)
			################## END Disk Bandwidth vs Time ##################
			
			################## START Disk Throughput vs Time ##################
			
			output_table(ed, en, os_dsk_tput_data, paste("016_os_dsk_tput_vs_time_data_", 
							experiment_node_name, sep = ''), FALSE)
			
			os_dsk_tput_data <- melt(os_dsk_tput_data, id.vars="relative_time")
			
			msg <- paste("Disk throughput for ", node_type, " \"", experiment_node_name, 
					"\" on experiment ", selected_expname, "\" (", selected_expid, ")", sep = '')
			cat(paste(msg, "...", sep = ''), sep='\n')
			
			os_dsk_tput_vs_time_data_plot_title <- msg
			
			xy_lims <- plot_get_x_y_limits(en, os_dsk_tput_data, xati, yati)
			
			os_dsk_tput_vs_time_plot <- ggplot(os_dsk_tput_data, aes(x = relative_time, 
									y = value, colour = variable, fill = variable)) + 
					geom_bar(stat = "identity", position = "dodge") + 
					geom_vline(xintercept = lnel, linetype=7, colour="black") +
					geom_vline(xintercept = vmasl, linetype=4, colour="black") +
					geom_vline(xintercept = vmael, linetype=1, colour="black") +
					geom_vline(xintercept = vmcsl, linetype=3, colour="black") +
					geom_vline(xintercept = vmcel, linetype=5, colour="black") +	
					xlab("Time (minutes)") + 
					ylab("Disk throughput (IO/s)") + 
					labs(title = os_dsk_tput_vs_time_data_plot_title) + 
					scale_x_continuous(limits =  xy_lims[[1]], breaks =  xy_lims[[2]]) 
			#				+ scale_y_continuous(limits =  xy_lims[[3]], breaks =  xy_lims[[4]])
			
			output_pdf_plot(ed, en, os_dsk_tput_vs_time_plot, paste("015_os_dsk_tput_vs_time_plot_", 
							experiment_node_name, sep = ''), sps)
			################## END Disk Throughput vs Time ##################
		}
	}
}

multiplot <- function(..., plotlist=NULL, file, cols=1, layout=NULL) {
	require(grid)
	
	# Make a list from the ... arguments and plotlist
	plots <- c(list(...), plotlist)
	
	numPlots = length(plots)
	
	# If layout is NULL, then use 'cols' to determine layout
	if (is.null(layout)) {
		# Make the panel
		# ncol: Number of columns of plots
		# nrow: Number of rows needed, calculated from # of cols
		layout <- matrix(seq(1, cols * ceiling(numPlots/cols)),
				ncol = cols, nrow = ceiling(numPlots/cols))
	}
	
	if (numPlots==1) {
		print(plots[[1]])
		
	} else {
		# Set up the page
		grid.newpage()
		pushViewport(viewport(layout = grid.layout(nrow(layout), ncol(layout))))
		
		# Make each plot, in the correct location
		for (i in 1:numPlots) {
			# Get the i,j matrix positions of the regions that contain this subplot
			matchidx <- as.data.frame(which(layout == i, arr.ind = TRUE))
			
			print(plots[[i]], vp = viewport(layout.pos.row = matchidx$row,
							layout.pos.col = matchidx$col))
		}
	}
}