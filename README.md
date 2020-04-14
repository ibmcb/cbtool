# Welcome to the Cloud Rapid Experimentation and Analysis Toolkit

Cloud Rapid Experimentation and Analysis Tool (aka CBTOOL) is a framework that automates IaaS cloud benchmarking through the running of controlled experiments.

[![Gitter](https://badges.gitter.im/ibmcb-project/community.svg)](https://gitter.im/ibmcb-project/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

Subscribe to our mailing list:

- Users: https://groups.google.com/forum/#!forum/cbtool-users

- Development: https://groups.google.com/forum/#!forum/cbtool-devel


## New! CloudBench is now released as a component of [SPEC Cloud IaaS 2018](http://spec.org/cloud_iaas2018)

## To get started:

1. [Learn more about the tool](https://github.com/ibmcb/cbtool/wiki/DOC:-Table-of-Contents)

2. [Perform the initial installation](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Initial-Installation)

3. [Run the tool for the first time](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Running-the-tool-for-the-first-time)

4. [Prepare your cloud to be driven by the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-your-cloud-to-be-driven-by-CBTOOL)

5. [Prepare a VM image to be used with the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-a-VM-to-be-used-with-CBTOOL-on-a-real-cloud)

6. [Deploy your first Virtual Application](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Deploy-your-first-virtual-application)

7. [Run simple experiments](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-simple-experiments)

8. [If needed, debug the initial setup](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Debug-initial-setup)

9. [Configure CBTOOL to run outside of the cloud (or with multiple tenant networks)](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-the-CloudBench-orchestrator-outside-of-the-cloud-(or-with-multiple-tenant-networks))

    1. [Detailed instructions on how to use OpenVPN support](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Use-VPN-support-with-your-benchmarks)
    
10. Look at some [auto generated plots](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Save-Monitoring-Data-on-the-Command-Line) made from the data collected.

11. Read our latest paper [IC2E 2013](http://dl.acm.org/citation.cfm?id=2497243).

12. Try administrating the tool with the [Graphical Environment](https://github.ibm.com/marcios/cbtool/wiki/HOWTO:-Using-the-Graphical-Environment)

    1. Then try [monitoring your experiments with the Graphical Environment](https://github.ibm.com/marcios/cbtool/wiki/HOWTO:-Monitoring-with-the-Graphical-Environment)

    2. Try to [customize your dashboard monitoring data with filters in the Graphical Environment](https://github.ibm.com/marcios/cbtool/wiki/HOWTO:-Customize-Dashboard-Monitoring-in-the-Graphical-Environment)

    3. You can also try to use the [Graphical Wizard](https://github.ibm.com/marcios/cbtool/wiki/HOWTO:-Using-the-Wizard-for-first-time-connection) for a first-time connection.

16. Read the [Frequently Asked Questions](https://github.com/ibmcb/cbtool/wiki/FAQ)

## Features:
- Automatic deployment and controlled execution of multiple multi-tier applications.
Each individual application can have a specific load profile using probability distributions.
- Adapters for multiple clouds (EC2 and OpenStack, among others), with a plugin structure that allows new cloud models to be added incrementally.
- Can orchestrate different arrival rates and lifetimes for VMs using probability distributions.
- Collects application and system (OS) performance data from hosts and guests in real time.
- It is designed from the ground up to be highly scalable and parallel.

## <a name="adapters">[Supported Clouds](https://github.com/ibmcb/cbtool/wiki/DOC:-Supported-Clouds):

1. Amazon EC2
2. OpenStack (and RackSpace)
3. Google Compute Engine 
4. DigitalOcean
5. Docker/Swarm
6. LXD/LXC
7. Kubernetes
8. Libvirt+KVM
9. VMWare vCloud (NOT actively maintained)
10. CloudStack (NOT actively maintained)
11. SoftLayer

Want to add support for a new Cloud? Take a look at our [Frequently Asked Questions](https://github.com/ibmcb/cbtool/wiki/FAQ#development-)

## <a name="workloads">[Supported Workloads](https://github.com/ibmcb/cbtool/wiki/DOC:-Supported-Virtual-Applications)

To get the most current list, start CBTOOL and type ```typelist``` on the CLI. To get more information about a given workload, ```typeshow <workload name>```:

```
(MYCLOUD) typelist
AIs with the following types can be attached to to this experiment (Cloud MYSIMCLOUD) :

synthetic:
  bonnie (default, full)
  btest (default)
  coremark (default)
  ddgen (default)
  filebench (fileserver, oltp_noism, varmail, videoserver, webproxy)
  fio (default)
  iperf (tcp, udp)
  mlg (default)
  netperf (tcp_stream, tcp_maerts, udp_stream, tcp_rr, tcp_cc, tcp_crr, udp_rr)
  nuttcp (tcp, udp)
  postmark (default)
  unixbench (arithmetic, dhrystone, whetstone, load, misc, speed, oldsystem, system, fs, shell, index)
  xping (icmp)

application-stress:
  memtier (default)
  oldisim (default)
  wrk (default)

scientific:
  hpcc (default)
  linpack (default)
  multichase (simple, work:N, t0-2, nta, movdqa, mvntdqa, parallel2-10, critword:N, critword2:N)
  parboil (histo, bfs, stencil, mri-q, mri-gridding, lbm, tpacf, sad, spmv, sgemm, cutcp)
  scimark (default)

transactional:
  cassandra_ycsb (workloada, workloadb, workloadc, workloadd, workloade, workloadf)
  ibm_daytrader (default)
  mongo_ycsb (workloada, workloadb, workloadc, workloadd, workloade, workloadf)
  open_daytrader (default)
  redis_ycsb (workloada, workloadb, workloadc, workloadd, workloade, workloadf)
  specjbb (preset, hbir)
  sysbench (simple, complex, nontrx, sp)

data-centric:
  giraph (pagerank, topkpagerank)
  hadoop (sort, wordcount, terasort, dfsioe, nutchindexing, pagerank, bayes, kmeans, hivebench)

fake:
  nullworkload (default)
```
Contacts:

Marcio Silva marcios@us.ibm.com
Michael R. Hines mrhines@digitalocean.com
