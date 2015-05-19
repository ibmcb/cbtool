#! /usr/bin/Rscript

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

library(reshape2)
library(ggplot2)

time_int_mins <- 5

directory_name <- readline("What is the directory name where the csv files are located? (Just press enter for \".\"): ")

if (directory_name == "") {
  directory_name <- getwd()
} else {
  setwd(directory_name)
}

file_list <- list.files()
file_list <- file_list[grep("trace_", file_list)]
experiment_list <- gsub(".csv", "", gsub("trace_", "", file_list))

cat(paste("The following experiments where found on the directory \"", directory_name, "\":", sep=''), sep='\n')
options(width = 10)
print(experiment_list)

options(width = 130)

msg <- paste("What is the experiment number? (Just press enter for the first experiment): ")

selected_experiment_index <- readline(msg)

if (selected_experiment_index == "") {
	selected_experiment_index <- 1
}

experiment_name <- experiment_list[as.numeric(selected_experiment_index)]

msg <- paste("Select experiment was \"", experiment_name, "\". Proceeding to extract files...", sep='')
cat(msg, sep='\n')

mgt_file_name <- paste("VM_management_", experiment_name, ".csv", sep='')
msg <- paste("Loading file \"", mgt_file_name, "\" onto data frame \"mgt_metrics\"", sep='')
cat(msg, sep='\n')

mgt_metrics <- read.csv(file=mgt_file_name, head=TRUE, comment.char="#", blank.lines.skip="true")

rapp_file_name <- paste("VM_runtime_app_", experiment_name, ".csv", sep='')
msg <- paste("Loading file \"", rapp_file_name, "\" onto data frame \"rapp_metrics\"", sep='')
cat(msg, sep='\n')

rapp_metrics <- read.csv(file=rapp_file_name, head=TRUE, comment.char="#", blank.lines.skip="true")

vros_file_name <- paste("VM_runtime_os_", experiment_name, ".csv", sep='')
msg <- paste("Loading file \"", vros_file_name, "\" onto data frame \"vros_metrics\"", sep='')
cat(msg, sep='\n')

vros_metrics <- read.csv(file=vros_file_name, head=TRUE, comment.char="#", blank.lines.skip="true")

hros_file_name <- paste("HOST_runtime_os_", experiment_name, ".csv", sep='')
msg <- paste("Loading file \"", hros_file_name, "\" onto data frame \"hros_metrics\"", sep='')
cat(msg, sep='\n')

hros_metrics <- read.csv(file=hros_file_name, head=TRUE, comment.char="#", blank.lines.skip="true")

trace_file_name <- paste("trace_", experiment_name, ".csv", sep='')
msg <- paste("Loading file \"", trace_file_name, "\" onto data frame \"trace_metrics\"", sep='')
cat(msg, sep='\n')

trace_metrics <- read.csv(file=trace_file_name, head=TRUE, comment.char="#", blank.lines.skip="true")
	
#names(mgt_metrics)
#names(trace_data)

# Reorder everything based on the timestamp, since metrics are written on the 
# metric store out of order
mgt_metrics <- mgt_metrics[order(mgt_metrics$mgt_001_provisioning_request_originated), ]
trace_metrics <- trace_metrics[order(trace_metrics$command_originated), ]
rapp_metrics <- rapp_metrics[order(rapp_metrics$time), ]
vros_metrics <- vros_metrics[order(vros_metrics$time), ]
hros_metrics <- hros_metrics[order(hros_metrics$time), ]

# Create a new column, combining "name" and "role", but only for mgt_metrics, rapp, vros and hros
mgt_metrics <- within(mgt_metrics, "vm_name" <- paste(mgt_metrics$name, mgt_metrics$role, sep=' | '))
rapp_metrics <- within(rapp_metrics, "vm_name" <- paste(rapp_metrics$name, rapp_metrics$role, sep=' | '))
vros_metrics <- within(vros_metrics, "obj_name" <- paste(vros_metrics$name, vros_metrics$role, sep=' | '))
hros_metrics <- within(hros_metrics, "obj_name" <- paste(hros_metrics$name, hros_metrics$role, sep=' | '))

# Create a new columun, "relative_time, but only for trace, rapp, vros and hros"
trace_metrics <- within(trace_metrics, "relative_time" <- (trace_metrics$command_originated - trace_metrics$command_originated[1])/60)
rapp_metrics <- within(rapp_metrics, "relative_time" <- (rapp_metrics$time - rapp_metrics$time[1])/60)
vros_metrics <- within(vros_metrics, "relative_time" <- (vros_metrics$time - vros_metrics$time[1])/60)
hros_metrics <- within(hros_metrics, "relative_time" <- (hros_metrics$time - hros_metrics$time[1])/60)

object_type <- toupper(readline("Do you want to plot the VM or HOST os metrics? (Just press enter to use HOST) : "))
if (object_type != "HOST" & object_type != "VM" ) {
	cat("Will use \"HOST\" as the object type", sep = '\n') 
	object_type <- "HOST"
} else {
	msg <- paste("Will use \"", object_type, "\" as the object type", sep = '')
	cat(msg, sep = '\n') 
}

if (object_type == "HOST") {
	name_list <- levels(hros_metrics$name)
} else {
	name_list <- levels(mgt_metrics$name)
}

msg <- paste("The following ", object_type, "s are listed were found: ", sep='')
cat(msg, sep='\n')
options(width = 10)
print(name_list)

msg <- paste(" What is the ", object_type, "'s name? (for VMs, just press return for \"all\") :", sep="")

options(width = 130)
selected_obj_index <- readline(msg)

if ((object_type == "VM") && (selected_obj_index == "")) {
	selected_obj_name <- "all"
	msg <- "Plotting management and runtime application data for all VMs...." 
	cat(msg, sep = '\n')

	# Timeline for all VMs
	timeline_data <- melt(subset(trace_metrics, select = c("vm_arrived", "vm_departed", "relative_time")), id.vars="relative_time")

	# Provisioning latency for all VMs
	prov_lat_data <- melt(subset(mgt_metrics, select = c("vm_name", "mgt_002_provisioning_request_sent", "mgt_003_provisioning_request_completed", "mgt_004_network_acessible", "mgt_005_file_transfer", "mgt_007_application_start")), id.vars="vm_name")

	# Latency for all VMs
	vm_lat_data <- melt(subset(rapp_metrics, select = c("relative_time", "vm_name", "app_latency")), id=c("relative_time", "vm_name"))

	# Throughput for all VMs
	vm_tput_data <- melt(subset(rapp_metrics, select = c("relative_time", "vm_name", "app_throughput")), id=c("relative_time", "vm_name"))

} else if ((object_type == "VM") && (selected_obj_index != "")) {
	selected_obj_name <- name_list[as.numeric(selected_obj_index)]
	msg <- paste("Plotting management, runtime application and runtime os data for VM \"", selected_obj_name, "\" ....", sep = '')
	cat(msg, sep = '\n')

	# Timeline for all VMs
	timeline_data <- melt(subset(trace_metrics, select = c("vm_arrived", "vm_departed", "relative_time")), id.vars="relative_time")
	
	# Provisioning latency for all VMs
	prov_lat_data <- melt(subset(mgt_metrics, name == selected_obj_name, select = c("vm_name", "mgt_002_provisioning_request_sent", "mgt_003_provisioning_request_completed", "mgt_004_network_acessible", "mgt_005_file_transfer", "mgt_007_application_start")), id.vars="vm_name")
	
	# Latency for all VMs
	vm_lat_data <- melt(subset(rapp_metrics, name == selected_obj_name, select = c("relative_time", "vm_name", "app_latency")), id=c("relative_time", "vm_name"))
	
	# Throughput for all VMs
	vm_tput_data <- melt(subset(rapp_metrics, name == selected_obj_name, select = c("relative_time", "vm_name", "app_throughput")), id=c("relative_time", "vm_name"))
	
} else if ((object_type == "HOST") && (selected_obj_index == "")) {
	selected_obj_name <- name_list[1]	
	msg <- paste("Plotting runtime os data for HOST \"", selected_obj_name, "\" ....", sep = '')
	cat(msg, sep = '\n')
} else {
	selected_obj_name <- name_list[as.numeric(selected_obj_index)]
	msg <- paste("Plotting runtime os data for HOST \"", selected_obj_name, "\" ....", sep = '')
	cat(msg, sep = '\n')
}

if (object_type == "VM") {

	# Obtain the X and Y limits for timeline plot
	actual_xlim <- max(timeline_data$relative_time[nrow(timeline_data)], vm_lat_data$relative_time[nrow(vm_lat_data)])
	actual_ylim_timeline <- max(timeline_data$value)

	# Plot timeline for all VMs
	timeline_plot_title <- paste("Timeline for all VMs on experiment", experiment_name)
	timeline_plot <- ggplot(timeline_data, aes(x=relative_time, y=value, color=variable)) + geom_line() + geom_point() + xlab("Time (minutes)") + ylab("Number of VMs") + labs(title = timeline_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim, time_int_mins))

	# Plot provisioning latency for all VMs
	prov_lat_plot_title <- paste("Provisioning Latency for all VMs on experiment", experiment_name)
	prov_lat_plot <- ggplot(prov_lat_data, aes(x=vm_name, y=value, fill=variable)) + geom_bar() + xlab("VM name") + ylab("Provisioning Latency (seconds)") + labs(title = prov_lat_plot_title)
	
	# Plot application latency for all VMs
	vm_lat_plot_title <- paste("Application Latency for all VMs on experiment", experiment_name)
	vm_lat_plot <- ggplot(vm_lat_data, aes(x=relative_time, y=value, colour=vm_name)) + geom_line() + geom_point()  + xlab("Time (minutes)") + ylab("Latency (milliseconds)") + labs(title = vm_lat_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	# Plot application througput for all VMs
	vm_tput_plot_title <- paste("Application Throughput for all VMs on experiment", experiment_name)
	vm_tput_plot <- ggplot(vm_tput_data , aes(x=relative_time, y=value, colour=vm_name)) + geom_line() + geom_point() + xlab("Time (minutes)") + ylab("Throughput (ops)") + labs(title = paste("Application Throughput for all VMs on experiment", experiment_name)) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))	

	metrics_data <- vros_metrics
} else {
	metrics_data <- hros_metrics
}

actual_xlim <- metrics_data$relative_time[nrow(metrics_data)]

if (selected_obj_name != "all") {
	#	os_cpu_data <- melt(subset(metrics_data, name==selected_obj_name, select = c("relative_time", "cpu_user", "cpu_system", "cpu_wio", "cpu_intr", "cpu_sintr")), id.vars="relative_time")
	os_cpu_data <- melt(subset(metrics_data, name==selected_obj_name, select = c("relative_time", "cpu_user", "cpu_system", "cpu_wio")), id.vars="relative_time")
	os_cpu_plot_title <- paste("CPU usage for ", object_type, " ", selected_obj_name, " on experiment ", experiment_name, sep="")
	os_cpu_plot <- ggplot(os_cpu_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("CPU usage (%)") + labs(title = os_cpu_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	os_mem_data <- subset(metrics_data, name==selected_obj_name, select = c("relative_time", "mem_cached", "mem_buffers", "mem_shared"))
	os_mem_data <- within(os_mem_data, "mem_cached" <- abs(os_mem_data$mem_cached / (1024)))
	os_mem_data <- within(os_mem_data, "mem_buffers" <- abs(os_mem_data$mem_buffers / (1024)))
	os_mem_data <- within(os_mem_data, "mem_shared" <- abs(os_mem_data$mem_shared / (1024)))
	os_mem_data <- melt(os_mem_data, id.vars="relative_time")
	os_mem_plot_title <- paste("Memory usage for ", object_type, " ", selected_obj_name, " on experiment ", experiment_name, sep="")
	os_mem_plot <- ggplot(os_mem_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("Mem usage (Megabytes)") + labs(title = os_mem_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	# For network and disk, differences need to be calculated
	os_net_bw_data <- subset(metrics_data, name==selected_obj_name, select = c("relative_time", "bytes_out", "bytes_in"))
	os_net_bw_data$bytes_out_delta <- c(NA,diff(os_net_bw_data$bytes_out))
	os_net_bw_data$bytes_in_delta <- c(NA,diff(os_net_bw_data$bytes_in))
	os_net_bw_data$time_delta <- c(1,diff(os_net_bw_data$relative_time))
	os_net_bw_data <- within(os_net_bw_data, "Mbps_out" <- abs(os_net_bw_data$bytes_out_delta * 8/ (1024 * 1024)/(os_net_bw_data$time_delta * 60)))
	os_net_bw_data <- within(os_net_bw_data, "Mbps_in" <- abs(os_net_bw_data$bytes_in_delta * 8 / (1024 * 1024)/(os_net_bw_data$time_delta * 60)))
	
	os_net_tput_data <- subset(metrics_data, name==selected_obj_name, select = c("relative_time", "pkts_out", "pkts_in"))
	os_net_tput_data$pkts_out_delta <- c(NA,diff(os_net_tput_data$pkts_out))
	os_net_tput_data$pkts_in_delta <- c(NA,diff(os_net_tput_data$pkts_in))
	os_net_tput_data$time_delta <- c(1,diff(os_net_tput_data$relative_time))
	os_net_tput_data <- within(os_net_tput_data, "Pps_out" <- abs(os_net_tput_data$pkts_out_delta/(os_net_tput_data$time_delta * 60)))
	os_net_tput_data <- within(os_net_tput_data, "Pps_in" <- abs(os_net_tput_data$pkts_in_delta/(os_net_tput_data$time_delta * 60)))
	
	os_dsk_bw_data <- subset(metrics_data, name==selected_obj_name, select = c("relative_time", "ds_KB_read", "ds_KB_write"))
	os_dsk_bw_data$ds_KB_read_delta <- c(NA,diff(os_dsk_bw_data$ds_KB_read))
	os_dsk_bw_data$ds_KB_write_delta <- c(NA,diff(os_dsk_bw_data$ds_KB_write))
	os_dsk_bw_data$time_delta <- c(1,diff(os_dsk_bw_data$relative_time))
	os_dsk_bw_data <- within(os_dsk_bw_data, "MBps_read" <- abs(os_dsk_bw_data$ds_KB_read_delta/(1024))/(os_dsk_bw_data$time_delta * 60))
	os_dsk_bw_data <- within(os_dsk_bw_data, "MBps_write" <- abs(os_dsk_bw_data$ds_KB_write_delta/(1024))/(os_dsk_bw_data$time_delta * 60))
	
	os_dsk_tput_data <- subset(metrics_data, name==selected_obj_name, select = c("relative_time", "ds_ios_read", "ds_ios_write"))
	os_dsk_tput_data$ds_ios_read_delta <- c(NA,diff(os_dsk_tput_data$ds_ios_read))
	os_dsk_tput_data$ds_ios_write_delta <- c(NA,diff(os_dsk_tput_data$ds_ios_write))
	os_dsk_tput_data$time_delta <- c(1,diff(os_dsk_tput_data$relative_time))
	os_dsk_tput_data <- within(os_dsk_tput_data, "IOps_read" <- abs(os_dsk_tput_data$ds_ios_read_delta)/(os_dsk_tput_data$time_delta * 60))
	os_dsk_tput_data <- within(os_dsk_tput_data, "IOps_write" <- abs(os_dsk_tput_data$ds_ios_write_delta)/(os_dsk_tput_data$time_delta * 60))
	
	# Some samples need to be discarded
	os_net_bw_data <- subset(os_net_bw_data, Mbps_in < (1024 * 1024) | Mbps_out < (1024 * 1024), select = c("relative_time", "Mbps_out", "Mbps_in"))
	os_net_tput_data <- subset(os_net_tput_data, Pps_in < (1024 * 10) | Pps_out < (1024 * 10), select = c("relative_time", "Pps_out", "Pps_in"))
	os_dsk_bw_data <- subset(os_dsk_bw_data, MBps_read < (1024 * 1024) | MBps_write < (1024 * 10), select = c("relative_time", "MBps_write", "MBps_read"))
	os_dsk_tput_data <- subset(os_dsk_tput_data, IOps_read < (1024 * 1024) | IOps_write < (1024 * 10), select = c("relative_time", "IOps_write", "IOps_read"))
	
	os_net_bw_data <- melt(os_net_bw_data, id.vars="relative_time")
	os_net_bw_plot_title <- paste("Network bandwidth for ", object_type, " \"", selected_obj_name, "\" on experiment ", experiment_name, sep="")
	os_net_bw_plot <- ggplot(os_net_bw_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("Network bandwidth (Mbps)") + labs(title = os_net_bw_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	os_net_tput_data <- melt(os_net_tput_data, id.vars="relative_time")
	os_net_tput_plot_title <- paste("Network throughput for ", object_type, " \"", selected_obj_name, "\" on experiment ", experiment_name, sep="")
	os_net_tput_plot <- ggplot(os_net_tput_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("Network throughput (packets/s)") + labs(title = os_net_tput_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	os_dsk_bw_data <- melt(os_dsk_bw_data, id.vars="relative_time")
	os_dsk_bw_data_plot_title <- paste("Disk bandwidth for ", object_type, "  \"", selected_obj_name, "\" on experiment ", experiment_name, sep="")
	os_dsk_bw_plot <- ggplot(os_dsk_bw_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("Disk bandwidth (MB/s)") + labs(title = os_dsk_bw_data_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
	
	os_dsk_tput_data <- melt(os_dsk_tput_data, id.vars="relative_time")
	os_dsk_tput_data_plot_title <- paste("Disk throughput for ", object_type, " \"", selected_obj_name, "\" on experiment ", experiment_name, sep="")
	os_dsk_tput_plot <- ggplot(os_dsk_tput_data, aes(x=relative_time, y=value, colour=variable)) + geom_point() + xlab("Time (minutes)") + ylab("Disk throughput (IO/s)") + labs(title = os_dsk_bw_data_plot_title) + scale_x_continuous(limits=c(0, actual_xlim), breaks=seq(0,actual_xlim,time_int_mins))
}
	
cat("The following plots are available:", sep = '\n')

# Need to improve later
options(width = 10)
plot_list <- ls()
plot_list <- plot_list[grep("plot", plot_list)]
plot_list <- plot_list[!grepl("title",plot_list)]
plot_list <- plot_list[!grepl("multiplot",plot_list)]
cat(plot_list, sep = '\n')
options(width = 130)

#ggsave(prov_lat_plot, file="os_cpu_plot.pdf", width=15)
#ggsave(timeline_plot, file="os_mem_plot.pdf", width=15)
#ggsave(vm_lat_plot, file="os_cpu_plot.pdf", width=15)
#ggsave(vm_tput_plot, file="os_net_bw_plot.pdf", width=15)
#ggsave(os_cpu_plot, file="os_cpu_plot.pdf", width=15)
#ggsave(os_mem_plot, file="os_mem_plot.pdf", width=15)
#ggsave(os_net_bw_plot, file="os_net_bw_plot.pdf", width=15)
#ggsave(os_net_tput_plot, file="os_net_tput_plot.pdf", width=15)
#ggsave(os_dsk_bw_data_plot, file="os_dsk_bw_data_plot.pdf", width=15)
#ggsave(os_dsk_tput_data, file="os_dsk_tput_data.pdf", width=15)

#multiplot(vm_lat_plot, timeline_plot, vm_tput_plot, timeline_plot, cols=2)
#multiplot(os_cpu_plot, os_mem_plot, os_net_bw_plot, os_net_tput_plot, os_dsk_bw_plot, os_dsk_tput_plot, cols=3)