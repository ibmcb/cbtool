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

source ~/.bashrc
source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

GMOND_VMS=~/gmond-vms.conf
python_module_path=~/util/python_ganglia_modules
python_modules=~/util/ganglia_conf.d

COLLECTOR_UNICAST_IP=`get_my_ai_attribute_with_default ${my_ai_uuid} metric_aggregator_ip none`
COLLECTOR_MULTICAST_IP=`get_global_sub_attribute mon_defaults collector_multicast_ip`
COLLECTOR_MULTICAST_PORT=`get_global_sub_attribute mon_defaults collector_vm_multicast_port`
COLLECTOR_VM_PORT=`get_global_sub_attribute mon_defaults collector_vm_port`

if [[ $(sudo ifconfig -a | grep -c $COLLECTOR_UNICAST_IP) -eq 0 ]]
then
	COLLECTOR_UNICAST_IP=${my_ip_addr}
fi

cat << EOF > $GMOND_VMS
globals {
  daemonize = yes
    setuid = yes
    user = nobody
    debug_level = 0
    max_udp_msg_len = 1472
    mute = no
    deaf = no
    allow_extra_data = yes
    host_dmax = 300 /*secs */
    cleanup_threshold = 60 /*secs */
    gexec = no
    send_metadata_interval = 20 /*secs */
  }

cluster {
  name = "cb-vms"
  owner = "CB"
  latlong = "unspecified"
  url = "127.0.0.1"
}

EOF

if [[ x"$my_ai_uuid" != x"none" ]]
then
cat << EOF >> $GMOND_VMS
udp_send_channel {
 host = ${COLLECTOR_UNICAST_IP}
 port = ${COLLECTOR_VM_PORT}
}

EOF
else
cat << EOF >> $GMOND_VMS
udp_send_channel {
 host = ${my_ip_addr}
 port = ${COLLECTOR_VM_PORT}
}

EOF
fi

cat << EOF >> $GMOND_VMS
udp_recv_channel {
  port = ${COLLECTOR_VM_PORT}
  bind = ${my_ip_addr} 
}

udp_recv_channel {
  port = ${COLLECTOR_VM_PORT}
  bind = 127.0.0.1 
}

tcp_accept_channel {
  port = ${COLLECTOR_VM_PORT}
}

modules {
  module {
    name = "python_module"
    path = "/usr/lib64/ganglia/modpython.so"
    params = "${python_module_path}"
  }
  module {
    name = "core_metrics"
  }
  module {
    name = "cpu_module"
    path = "/usr/lib64/ganglia/modcpu.so"
  }
  module {
    name = "disk_module"
    path = "/usr/lib64/ganglia/moddisk.so"
  }
  module {
    name = "load_module"
    path = "/usr/lib64/ganglia/modload.so"
  }
  module {
    name = "mem_module"
    path = "/usr/lib64/ganglia/modmem.so"
  }
  module {
    name = "net_module"
    path = "/usr/lib64/ganglia/modnet.so"
  }
  module {
    name = "proc_module"
    path = "/usr/lib64/ganglia/modproc.so"
  }
  module {
    name = "sys_module"
    path = "/usr/lib64/ganglia/modsys.so"
  }
}

include ('${python_modules}/*.conf')

collection_group {
  collect_every = 60
  time_threshold = 60
  metric {
    name = "heartbeat"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "cpu_speed"
    title = "CPU Speed"
  }
  metric {
    name = "boottime"
    title = "Last Boot Time"
  }
  metric {
    name = "machine_type"
    title = "Machine Type"
  }
  metric {
    name = "os_name"
    title = "Operating System"
  }
  metric {
    name = "os_release"
    title = "Operating System Release"
  }
  metric {
    name = "location"
    title = "Location"
  }
}

collection_group {
  collect_every = 60

  metric {
    name = "cpu_user"
    value_threshold = "1.0"
    title = "CPU User"
  }
  metric {
    name = "cpu_system"
    value_threshold = "1.0"
    title = "CPU System"
  }
  metric {
    name = "cpu_idle"
    value_threshold = "5.0"
    title = "CPU Idle"
  }
  metric {
    name = "cpu_nice"
    value_threshold = "1.0"
    title = "CPU Nice"
  }
  metric {
    name = "cpu_aidle"
    value_threshold = "5.0"
    title = "CPU aidle"
  }
  metric {
    name = "cpu_wio"
    value_threshold = "1.0"
    title = "CPU wio"
  }

#  metric {
#    name = "cpu_intr"
#    value_threshold = "1.0"
#    title = "CPU intr"
#  }
#  metric {
#    name = "cpu_sintr"
#    value_threshold = "1.0"
#    title = "CPU sintr"
#  }
}

collection_group {
  collect_every = 60

  metric {
    name = "load_one"
    value_threshold = "1.0"
    title = "One Minute Load Average"
  }
  metric {
    name = "load_five"
    value_threshold = "1.0"
    title = "Five Minute Load Average"
  }
  metric {
    name = "load_fifteen"
    value_threshold = "1.0"
    title = "Fifteen Minute Load Average"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "proc_run"
    value_threshold = "1.0"
    title = "Total Running Processes"
  }
  metric {
    name = "proc_total"
    value_threshold = "1.0"
    title = "Total Processes"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "mem_free"
    value_threshold = "1.0"
    title = "Free Memory"
  }
  metric {
    name = "mem_shared"
    value_threshold = "1.0"
    title = "Shared Memory"
  }
  metric {
    name = "mem_buffers"
    value_threshold = "1.0"
   title = "Memory Buffers"
  }
  metric {
    name = "mem_cached"
    value_threshold = "1.0"
    title = "Cached Memory"
  }
  metric {
    name = "swap_free"
    value_threshold = "1.0"
    title = "Free Swap Space"
  }
  metric {
    name = "cpu_num"
    value_threshold = "1.0"
    title = "CPU Count"
  }
  metric {
    name = "mem_total"
    value_threshold = "1.0"
    title = "Memory Total"
  }
  metric {
    name = "swap_total"
    value_threshold = "1.0"
    title = "Swap Space Total"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "bytes_out"
    value_threshold = 4096
    title = "Bytes Sent"
  }
  metric {
    name = "bytes_in"
    value_threshold = 4096
    title = "Bytes Received"
  }
  metric {
    name = "pkts_in"
    value_threshold = 256
    title = "Packets Received"
  }
  metric {
    name = "pkts_out"
    value_threshold = 256
    title = "Packets Sent"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "disk_total"
    value_threshold = 1.0
    title = "Total Disk Space"
  }
}

collection_group {
  collect_every = 60
  metric {
    name = "disk_free"
    value_threshold = 1.0
    title = "Disk Space Available"
  }
  metric {
    name = "part_max_used"
    value_threshold = 1.0
    title = "Maximum Disk Space Used"
  }
}
EOF
