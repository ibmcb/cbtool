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

cd ~
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

set_load_gen $@

LOAD_PROFILE=$(echo ${LOAD_PROFILE} | tr '[:upper:]' '[:lower:]')
LINPACK_VERSION=`get_my_ai_attribute_with_default linpack_version 2.3`

# Use version 2.3 if specified
if [[ $LINPACK_VERSION == "2.3" ]]; then
	NR_CPUS=`cat /proc/cpuinfo | grep processor | wc -l`
        if [[ $NR_CPUS -eq 1 ]]; then
           P=1
           Q=1
        else
           P=$((NR_CPUS / 2))
           Q=2
        fi

	# Build BLIS
	cpu_model=$(lscpu | grep Vendor | awk '{print $3}')
	echo $cpu_model
	if [[ $cpu_model == "AuthenticAMD" ]]; then
	   LADIR="blis_amd"
	   echo "Using AMD Zeon CPU Model"
	elif [[ $cpu_model == "GenuineIntel" ]]; then
	   LADIR="blis_intel"
	   echo "Using Intel CPU Model"
	else
	   echo "Unknown CPU Model"
	   exit 1
	fi

	# Build HPL
	HPLBUILDFILE="./linpack_${LINPACK_VERSION}/hpl-2.3/Make.Linux_BLIS"
	echo '        SHELL        = /bin/sh
        CD           = cd
        CP           = cp
        LN_S         = ln -s
        MKDIR        = mkdir
        RM           = /bin/rm -f
        TOUCH        = touch
        ARCH         = Linux_BLIS
        TOPdir       = /home/cbuser/linpack_2.3/hpl-2.3
        INCdir       = $(TOPdir)/include
        BINdir       = $(TOPdir)/bin/$(ARCH)
        LIBdir       = $(TOPdir)/lib/$(ARCH)
        HPLlib       = $(LIBdir)/libhpl.a
        MPdir        = /opt/openmpi
        MPinc        = -I$(MPdir)/include
        MPlib        = $(MPdir)/lib/libmpi.so
        LAlib        = $(LAdir)/lib/libblis-mt.a
        F2CDEFS      = -DAdd__ -DF77_INTEGER=int -DStringSunStyle
        HPL_INCLUDES = -I$(INCdir) -I$(INCdir)/$(ARCH) $(LAinc) $(MPinc)
        HPL_LIBS     = $(HPLlib) $(LAlib) $(MPlib) -lm
        HPL_OPTS     = -DHPL_CALL_CBLAS
        HPL_DEFS     = $(F2CDEFS) $(HPL_OPTS) $(HPL_INCLUDES)
        CC           = /usr/bin/gcc
        CCNOOPT      = $(HPL_DEFS)
        CCFLAGS      = $(HPL_DEFS) -std=c99 -march=native -fomit-frame-pointer -O3 -funroll-loops -W -Wall -fopenmp
        LINKER       = /usr/bin/gcc
        LINKFLAGS    = $(CCFLAGS)
        ARCHIVER     = ar
        ARFLAGS      = r
        RANLIB       = echo' > $HPLBUILDFILE
        echo "        LAdir        = /opt/${LADIR}" >> $HPLBUILDFILE

        HPL_BUILDCMD="cd ~/linpack_${LINPACK_VERSION}/hpl-2.3; make arch=Linux_BLIS"
        if [ ! -d "./linpack_${LINPACK_VERSION}/hpl-2.3/bin/Linux_BLIS" ]; then
                execute_load_generator "$HPL_BUILDCMD"
        fi

        LINPACK=`get_my_ai_attribute_with_default linpack ~/linpack_${LINPACK_VERSION}/hpl-2.3/bin/Linux_BLIS/xhpl`
        eval LINPACK=${LINPACK}
        sudo ls ${LINPACK} 2>&1 > /dev/null
        if [[ $? -ne 0 ]]
        then
                LINPACK=$(sudo find ~/linpack_${LINPACK_VERSION} | grep xhpl)
        fi

	# Run Linpack
	LINPACK_DAT='./HPL.dat'
	echo "HPLinpack benchmark input file
	Innovative Computing Laboratory, University of Tennessee
	HPL.out      output file name (if any)
	6            device out (6=stdout,7=stderr,file)
	1            # of problems sizes (N)
	10240        Ns
	1            # of NBs
	240           NBs
	0            PMAP process mapping (0=Row-,1=Column-major)
	1            # of process grids (P x Q)
	${P}            Ps
	${Q}            Qs
	16.0         threshold
	1            # of panel fact
	2            PFACTs (0=left, 1=Crout, 2=Right)
	1            # of recursive stopping criterium
	4            NBMINs (>= 1)
	1            # of panels in recursion
	2            NDIVs
	1            # of recursive panel fact.
	2            RFACTs (0=left, 1=Crout, 2=Right)
	1            # of broadcast
	2            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)
	1            # of lookahead depth
	1            DEPTHs (>=0)
	1            SWAP (0=bin-exch,1=long,2=mix)
	64           swapping threshold
	0            L1 in (0=transposed,1=no-transposed) form
	0            U  in (0=transposed,1=no-transposed) form
	1            Equilibration (0=no,1=yes)
	8            memory alignment in double (> 0)" > ${LINPACK_DAT}

	CMDLINE="/opt/openmpi/bin/mpirun --allow-run-as-root -np $NR_CPUS --report-bindings ${LINPACK} > ${RUN_OUTPUT_FILE}"
	execute_load_generator "$CMDLINE"
	AVERAGE=$(cat ${RUN_OUTPUT_FILE} | grep -A 2 Gflops | awk '{print $7}' | tail -n1)
        ~/cb_report_app_metrics.py \
        throughput:$AVERAGE:gflops \
        $(common_metrics)
else
	# Older Linpack
	LINPACK=`get_my_ai_attribute_with_default linpack ~/compilers_and_libraries_2016.0.038/linux/mkl/benchmarks/linpack/xlinpack_xeon64`
	eval LINPACK=${LINPACK}

	sudo ls ${LINPACK} 2>&1 > /dev/null
	if [[ $? -ne 0 ]]
	then
		LINPACK=$(sudo find ~ | grep xlinpack_xeon64)
	fi
	LOAD_FACTOR=`get_my_ai_attribute_with_default load_factor 5000`
	LINPACK_DAT='~/linpack.dat'
	eval LINPACK_DAT=${LINPACK_DAT}

	PROBLEM_SIZES=$((${LOAD_LEVEL}*${LOAD_FACTOR}))
	LEADING_DIMENSIONS=$((${LOAD_LEVEL}*${LOAD_FACTOR}))

	LINPACK_IP=`get_ips_from_role linpack`

	linux_distribution
	export OMP_NUM_THREADS=$NR_CPUS
	echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
	echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
	echo "1 # number of tests" >> ${LINPACK_DAT}
	echo "$PROBLEM_SIZES # problem sizes" >> ${LINPACK_DAT}
	echo "$LEADING_DIMENSIONS # leading dimensions" >> ${LINPACK_DAT}
	echo "${LOAD_DURATION} # times to run a test " >> ${LINPACK_DAT}
	echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}

	CMDLINE="${LINPACK} ${LINPACK_DAT}"

	execute_load_generator "$CMDLINE" ${RUN_OUTPUT_FILE} ${LOAD_DURATION}
	RESULTS=$(cat ${RUN_OUTPUT_FILE} | grep -A 1 Average | grep $PROBLEM_SIZES)
	AVERAGE=$(echo $RESULTS | awk '{print $4}')
	MAX=$(echo $RESULTS | awk '{print $5}')
    
	~/cb_report_app_metrics.py \
	throughput_max:$MAX:gflops \
	throughput:$AVERAGE:gflops \
	$(common_metrics)
fi
unset_load_gen

exit 0
