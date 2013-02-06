# Welcome to the Cloud Rapid Experimentation and Analysis Toolkit

Cloud Rapid Experimentation and Analysis Tool is a framework that automates IaaS cloud benchmarking through the running of controlled experiments.

## To get started:

1. [Perform the initial installation](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Initial-Installation)
2. [Run the tool for the first time](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Running-the-tool-for-the-first-time)
3. [Prepare a VM image to be used with the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-a-VM-to-be-used-with-CBTOOL-on-a-real-cloud)
4. [Run simple experiments](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-simple-experiments)
5. Read our latest paper (to appear in IC2E 2013).
6. Try to get connected with the [Graphical Wizard](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Wizard-for-first-time-connection)
7. Try administrating the tool with the [Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Graphical-Environment)
8. Then try [monitoring your experiments with the Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Monitoring-with-the-Graphical-Environment)
9. Try to [save experimental results to CSV files on the commandline](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Save-Monitoring-Data-on-the-Command-Line)

## Features:
- Automatic deployment and controlled execution of multiple multi-tier applications.
Each individual application can have a specific load profile using probability distributions.
- Adapters for multiple clouds (EC2 and OpenStack, among others), with a plugin structure that allows new cloud models to be added incrementally.
- Can orchestrate different arrival rates and lifetimes for VMs using probability distributions.
- Collects application and system (OS) performance data from hosts and guests in real time.
- It is designed from the ground up to be highly scalable and parallel.

## Supported Clouds:

1. Amazon EC2
2. OpenStack
3. IBM SCP and IBM SCE
4. "pure" Libvirt+KVM or Libvirt+XEN (soon)
5. VMWare vCloud (in progress)

Contact:

Marcio Silva marcios@us.ibm.com

Michael R. Hines mrhines@us.ibm.com
