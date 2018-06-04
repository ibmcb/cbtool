#!/usr/bin/env bash

# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

linux_distribution

ln -sf ${dir}/cbtool/3rd_party/byte-unixbench ~/

UNIXBENCH_DIR="~/byte-unixbench/UnixBench"
eval UNIXBENCH_DIR=${UNIXBENCH_DIR}

CBUSERLOGIN=`get_my_ai_attribute login`
sudo chown -R ${CBUSERLOGIN}:${CBUSERLOGIN} ${UNIXBENCH_DIR}

UNIXBENCH_IP=`get_ips_from_role unixbench`

CPUS=$(lscpu -p | grep -v "#" | wc -l)

if [[ $LOAD_PROFILE == "test" ]]
then
    execute_load_generator "cat ./test_output.txt" ${RUN_OUTPUT_FILE}
else
    cd ${UNIXBENCH_DIR}
	make
    if [ $LOAD_LEVEL == "auto" ]
    then
        execute_load_generator "./Run -c $CPUS" ${OUTPUT_FILE}
    else
        execute_load_generator "./Run -c $LOAD_LEVEL $LOAD_PROFILE" ${RUN_OUTPUT_FILE}
    fi
    cd -
fi

NUM_CORES=`grep -P -m1 "CPUs? in system" ${RUN_OUTPUT_FILE} | cut -d' ' -f1`

# --------------------- START Aggregate metrics -------------------------------- #
TMP=$(mktemp)
grep -m 1 -A 14 "System Benchmarks .* INDEX" ${RUN_OUTPUT_FILE} > $TMP

# Dhrystone 2 using register variables
DHRY_RESULT=$(grep "Dhrystone 2 using register variables" $TMP | awk '{print $(NF-1)}')
DHRY_INDEX=$(grep "Dhrystone 2 using register variables" $TMP | awk '{print $NF}')
# Double-Precision Whetstone
WHET_RESULT=$(grep "Double-Precision Whetstone" $TMP | awk '{print $(NF-1)}')
WHET_INDEX=$(grep "Double-Precision Whetstone" $TMP | awk '{print $NF}')
# Execl Throughput
EXECL_RESULT=$(grep "Execl Throughput" $TMP | awk '{print $(NF-1)}')
EXECL_INDEX=$(grep "Execl Throughput" $TMP | awk '{print $NF}')
# File Copy 1024 bufsize 2000 maxblocks
FC1024_RESULT=$(grep "File Copy 1024 bufsize 2000 maxblocks" $TMP | awk '{print $(NF-1)}')
FC1024_INDEX=$(grep "File Copy 1024 bufsize 2000 maxblocks" $TMP | awk '{print $NF}')
# File Copy 256 bufsize 500 maxblocks
FC256_RESULT=$(grep "File Copy 256 bufsize 500 maxblocks" $TMP | awk '{print $(NF-1)}')
FC256_INDEX=$(grep "File Copy 256 bufsize 500 maxblocks" $TMP | awk '{print $NF}')
# File Copy 4096 bufsize 8000 maxblocks
FC4096_RESULT=$(grep "File Copy 4096 bufsize 8000 maxblocks" $TMP | awk '{print $(NF-1)}')
FC4096_INDEX=$(grep "File Copy 4096 bufsize 8000 maxblocks" $TMP | awk '{print $NF}')
# Pipe Throughput
PIPE_RESULT=$(grep "Pipe Throughput" $TMP | awk '{print $(NF-1)}')
PIPE_INDEX=$(grep "Pipe Throughput" $TMP | awk '{print $NF}')
# Pipe-based Context Switching
CTXT_RESULT=$(grep "Pipe-based Context Switching" $TMP | awk '{print $(NF-1)}')
CTXT_INDEX=$(grep "Pipe-based Context Switching" $TMP | awk '{print $NF}')
# Process Creation
PROC_RESULT=$(grep "Process Creation" $TMP | awk '{print $(NF-1)}')
PROC_INDEX=$(grep "Process Creation" $TMP | awk '{print $NF}')
# Shell Scripts (1 concurrent)
SH1_RESULT=$(grep "Shell Scripts (1 concurrent)" $TMP | awk '{print $(NF-1)}')
SH1_INDEX=$(grep "Shell Scripts (1 concurrent)" $TMP | awk '{print $NF}')
# Shell Scripts (8 concurrent)
SH8_RESULT=$(grep "Shell Scripts (8 concurrent)" $TMP | awk '{print $(NF-1)}')
SH8_INDEX=$(grep "Shell Scripts (8 concurrent)" $TMP | awk '{print $NF}')
# System Call Overhead
SYSO_RESULT=$(grep "System Call Overhead" $TMP | awk '{print $(NF-1)}')
SYSO_INDEX=$(grep "System Call Overhead" $TMP | awk '{print $NF}')
# System Benchmarks Index Score
TOTAL_INDEX=$(grep "System Benchmarks Index Score" $TMP | awk '{print $NF}')

# multi-core results (when available)
NUM_RESULTS=`grep -c "System Benchmarks .* INDEX" ${RUN_OUTPUT_FILE}`
if [ "$NUM_RESULTS" -gt 1 ]
then
   TMP=$(mktemp)
   grep -m 2 -A 14 "System Benchmarks .* INDEX" ${RUN_OUTPUT_FILE} | tail -n 15 > $TMP

   # Dhrystone 2 using register variables
   MC_DHRY_RESULT=$(grep "Dhrystone 2 using register variables" $TMP | awk '{print $(NF-1)}')
   MC_DHRY_INDEX=$(grep "Dhrystone 2 using register variables" $TMP | awk '{print $NF}')
   # Double-Precision Whetstone
   MC_WHET_RESULT=$(grep "Double-Precision Whetstone" $TMP | awk '{print $(NF-1)}')
   MC_WHET_INDEX=$(grep "Double-Precision Whetstone" $TMP | awk '{print $NF}')
   # Execl Throughput
   MC_EXECL_RESULT=$(grep "Execl Throughput" $TMP | awk '{print $(NF-1)}')
   MC_EXECL_INDEX=$(grep "Execl Throughput" $TMP | awk '{print $NF}')
   # File Copy 1024 bufsize 2000 maxblocks
   MC_FC1024_RESULT=$(grep "File Copy 1024 bufsize 2000 maxblocks" $TMP | awk '{print $(NF-1)}')
   MC_FC1024_INDEX=$(grep "File Copy 1024 bufsize 2000 maxblocks" $TMP | awk '{print $NF}')
   # File Copy 256 bufsize 500 maxblocks
   MC_FC256_RESULT=$(grep "File Copy 256 bufsize 500 maxblocks" $TMP | awk '{print $(NF-1)}')
   MC_FC256_INDEX=$(grep "File Copy 256 bufsize 500 maxblocks" $TMP | awk '{print $NF}')
   # File Copy 4096 bufsize 8000 maxblocks
   MC_FC4096_RESULT=$(grep "File Copy 4096 bufsize 8000 maxblocks" $TMP | awk '{print $(NF-1)}')
   MC_FC4096_INDEX=$(grep "File Copy 4096 bufsize 8000 maxblocks" $TMP | awk '{print $NF}')
   # Pipe Throughput
   MC_PIPE_RESULT=$(grep "Pipe Throughput" $TMP | awk '{print $(NF-1)}')
   MC_PIPE_INDEX=$(grep "Pipe Throughput" $TMP | awk '{print $NF}')
   # Pipe-based Context Switching
   MC_CTXT_RESULT=$(grep "Pipe-based Context Switching" $TMP | awk '{print $(NF-1)}')
   MC_CTXT_INDEX=$(grep "Pipe-based Context Switching" $TMP | awk '{print $NF}')
   # Process Creation
   MC_PROC_RESULT=$(grep "Process Creation" $TMP | awk '{print $(NF-1)}')
   MC_PROC_INDEX=$(grep "Process Creation" $TMP | awk '{print $NF}')
   # Shell Scripts (1 concurrent)
   MC_SH1_RESULT=$(grep "Shell Scripts (1 concurrent)" $TMP | awk '{print $(NF-1)}')
   MC_SH1_INDEX=$(grep "Shell Scripts (1 concurrent)" $TMP | awk '{print $NF}')
   # Shell Scripts (8 concurrent)
   MC_SH8_RESULT=$(grep "Shell Scripts (8 concurrent)" $TMP | awk '{print $(NF-1)}')
   MC_SH8_INDEX=$(grep "Shell Scripts (8 concurrent)" $TMP | awk '{print $NF}')
   # System Call Overhead
   MC_SYSO_RESULT=$(grep "System Call Overhead" $TMP | awk '{print $(NF-1)}')
   MC_SYSO_INDEX=$(grep "System Call Overhead" $TMP | awk '{print $NF}')
   # System Benchmarks Index Score
   MC_TOTAL_INDEX=$(grep "System Benchmarks Index Score" $TMP | awk '{print $NF}')
fi
# ---------------------- END Aggregate metrics --------------------------------- #

# --------------------- START Reporting metrics -------------------------------- #
~/cb_report_app_metrics.py \
num_cores:${NUM_CORES}:num \
dhry_result:${DHRY_RESULT}:lps \
dhry_index:${DHRY_INDEX}:num \
whet_result:${WHET_RESULT}:MWIPS \
whet_index:${WHET_INDEX}:num \
execl_result:${EXECL_RESULT}:lps \
execl_index:${EXECL_INDEX}:num \
fc1024_result:${FC1024_RESULT}:KBPs \
fc1024_index:${FC1024_INDEX}:num \
fc256_result:${FC256_RESULT}:KBPs \
fc256_index:${FC256_INDEX}:num \
fc4096_result:${FC4096_RESULT}:KBPs \
fc4096_index:${FC4096_INDEX}:num \
pipe_result:${PIPE_RESULT}:lps \
pipe_index:${PIPE_INDEX}:num \
ctxt_result:${CTXT_RESULT}:lps \
ctxt_index:${CTXT_INDEX}:num \
proc_result:${PROC_RESULT}:lps \
proc_index:${PROC_INDEX}:num \
sh1_result:${SH1_RESULT}:lpm \
sh1_index:${SH1_INDEX}:num \
sh8_result:${SH8_RESULT}:lpm \
sh8_index:${SH8_INDEX}:num \
syso_result:${SYSO_RESULT}:lps \
syso_index:${SYSO_INDEX}:num \
total_index:${TOTAL_INDEX}:num \
mc_dhry_result:${MC_DHRY_RESULT}:lps \
mc_dhry_index:${MC_DHRY_INDEX}:num \
mc_whet_result:${MC_WHET_RESULT}:MWIPS \
mc_whet_index:${MC_WHET_INDEX}:num \
mc_execl_result:${MC_EXECL_RESULT}:lps \
mc_execl_index:${MC_EXECL_INDEX}:num \
mc_fc1024_result:${MC_FC1024_RESULT}:KBPs \
mc_fc1024_index:${MC_FC1024_INDEX}:num \
mc_fc256_result:${MC_FC256_RESULT}:KBPs \
mc_fc256_index:${MC_FC256_INDEX}:num \
mc_fc4096_result:${MC_FC4096_RESULT}:KBPs \
mc_fc4096_index:${MC_FC4096_INDEX}:num \
mc_pipe_result:${MC_PIPE_RESULT}:lps \
mc_pipe_index:${MC_PIPE_INDEX}:num \
mc_ctxt_result:${MC_CTXT_RESULT}:lps \
mc_ctxt_index:${MC_CTXT_INDEX}:num \
mc_proc_result:${MC_PROC_RESULT}:lps \
mc_proc_index:${MC_PROC_INDEX}:num \
mc_sh1_result:${MC_SH1_RESULT}:lpm \
mc_sh1_index:${MC_SH1_INDEX}:num \
mc_sh8_result:${MC_SH8_RESULT}:lpm \
mc_sh8_index:${MC_SH8_INDEX}:num \
mc_syso_result:${MC_SYSO_RESULT}:lps \
mc_syso_index:${MC_SYSO_INDEX}:num \
mc_total_index:${MC_TOTAL_INDEX}:num \
$(common_metrics)
 
# --------------------- END Reporting metrics -------------------------------- #

unset_load_gen

exit 0
