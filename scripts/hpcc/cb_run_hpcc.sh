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
source ~/.bashrc

check_container

set_load_gen $@

FEN_HPC_IP=`get_ips_from_role fen_hpc`
CN_HPC_IPS=`get_ips_from_role cn_hpc`
CN_HPC_IPS_CSV=`echo ${CN_HPC_IPS} | sed ':a;N;$!ba;s/\n/, /g'`

cluster_hosts_file=~/cluster.hosts
eval cluster_hosts_file=${cluster_hosts_file}

#bench_app_dir=$(find ~ | grep hpccinf.txt.template | sed 's^hpccinf.txt.template^^g')
#eval bench_app_dir=${bench_app_dir}

bench_app_dir=~
eval bench_app_dir=${bench_app_dir}
bench_app_bin=./hpcc
infile=~/hpccinf.txt
outfile=~/hpccoutf.txt

#Create a file with the list of nodes in the cluster that will run the job (getting info from /etc/hosts)
grep -v "localhost\|just_for_lost" /etc/hosts |grep "fen_hpc" |cut -d " " -f 1 >  $cluster_hosts_file
grep -v "localhost\|just_for_lost" /etc/hosts |grep "cn_hpc"  |cut -d " " -f 1 >> $cluster_hosts_file

#Calculate the number of MPI processes (as a function of the number of nodes and processes per node)
NUM_NODES=`cat $cluster_hosts_file | wc -l`

PROCESSES_PER_NODE=`get_my_ai_attribute_with_default processes_per_node 3`

let NUM_PROCESSES=$NUM_NODES*$PROCESSES_PER_NODE

#Calculate the problem size as a function of the load level (and the maximum size per node and number of nodes)
MAX_N_SIZE_PER_NODE=`get_my_ai_attribute_with_default max_n_size_per_node 40`

LOAD_LEVEL_FUNCTION=`get_my_ai_attribute load_level`
MAX_LOAD_LEVEL=`echo $LOAD_LEVEL_FUNCTION | cut -d "I" -f 5`
N_SIZE_FLOAT=`echo "$MAX_N_SIZE_PER_NODE * $NUM_NODES * ($LOAD_LEVEL / ($MAX_LOAD_LEVEL - 1))" | bc -l`
N_SIZE=`echo "($N_SIZE_FLOAT + 0.5) / 1" | bc` #rounding the number

#Get the block size from the AI
NB_SIZE=`get_my_ai_attribute_with_default nb_size 4`

# -----------------------------------------------------------------------------------------------
# Script modified by GA - calculate HPL size based on available RAM in the system
# -----------------------------------------------------------------------------------------------
# Figure out the total RAM we have - memory size x # nodes
# WARNING - we are assuming that the compute nodes have at least as much RAM as the FEN
TOTALRAM=$((MEM_SIZE_KB*1024*NUM_NODES))
syslog_netcat "   => TOTALRAM=$((TOTALRAM/1024/1024)) MBytes (Total available RAM in AI)"
# Dimension HPCC to use 1/3rd of the total amount of RAM
LURAM=$((TOTALRAM/3))
syslog_netcat "   => LURAM= $((LURAM/1024/1024)) MBytes (1/3rd of available RAM)"
# calculate the matrix size based on LURAM, assumin 8-byte words
N2=$((LURAM/8))
N_SIZE=$(bc <<< "scale=0; sqrt(($N2))")
syslog_netcat "   => derived N_SIZE=${N_SIZE} (assuming 1/3rd RAM utilization)"
# re-confirm that we are using the right amount of RAM
syslog_netcat "   => Memory used = $((N_SIZE*N_SIZE*8/1024/1024)) MBytes"
TOTALOPS=$((N_SIZE*N_SIZE*N_SIZE*2/3))
syslog_netcat "   => Total operations = $((TOTALOPS/1024/1024/1024)) gigaops"
syslog_netcat "   => Expected HPL duration (assuming 1GFlop/process) = $((TOTALOPS/NUM_PROCESSES/1024/1024/1024)) seconds"

syslog_netcat "Parameters: np=$NUM_PROCESSES, processes-per-node=$PROCESSES_PER_NODE, Ns=$N_SIZE, NBs=$NB_SIZE."

syslog_netcat "Parameters: np=$NUM_PROCESSES, processes-per-node=$PROCESSES_PER_NODE, Ns=$N_SIZE, NBs=$NB_SIZE."

cd $bench_app_dir

#Create input file
cp "${infile}.template" $infile
#Replace values from template with the current ones
sed -i s/"<Ns>"/"$N_SIZE"/g        $infile
sed -i s/"<NBs>"/"$NB_SIZE"/g      $infile
sed -i s/"<Ps>"/"1"/g              $infile
sed -i s/"<Qs>"/"$NUM_PROCESSES"/g $infile

CMDLINE="mpirun --allow-run-as-root -np $NUM_PROCESSES --machinefile $cluster_hosts_file --mca btl tcp,self $bench_app_bin"

execute_load_generator "${CMDLINE}" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}

cd ~

tp1=`cat ${outfile} | grep -a HPL_Tflops | cut -d "=" -f 2`
tp2=`cat ${outfile} | grep -a PTRANS_GBs | cut -d "=" -f 2`
tp3=`cat ${outfile} | grep -a MPIRandomAccess_GUPs | cut -d "=" -f 2`
tp4=`cat ${outfile} | grep -a MPIFFT_Gflops | cut -d "=" -f 2`
tp5=`cat ${outfile} | grep -a StarSTREAM_Triad | cut -d "=" -f 2`
tp6=`cat ${outfile} | grep -a StarDGEMM_Gflops | cut -d "=" -f 2`
tp7=`cat ${outfile} | grep -a RandomlyOrderedRingBandwidth_GBytes | cut -d "=" -f 2`
lat=`cat ${outfile} | grep -a RandomlyOrderedRingLatency_usec | cut -d "=" -f 2`
lat=`echo "scale=8;  ${lat} / 1000" | bc`

~/cb_report_app_metrics.py \
throughput_G_HPL:$tp1:Tflops \
bandwidth_G_PTRANS:$tp2:GBps \
throughput_G_RandomAccess:$tp3:Gups \
throughput_G_FFTE:$tp4:Gflops \
throughput_EP_STREAM_Triad:$tp5:GBps \
throughput_EP_DGEMM:$tp6:Gflops \
bandwidth_RandomRing:$tp7:GBps \
lat_RandomRing:$lat:usec \
bandwidth:$tp7:GBps \
latency:$lat:usec \
throughput:$tp3:Gups \
$(common_metrics)    
    
unset_load_gen
rm ${outfile}

exit 0
