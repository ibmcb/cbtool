# Welcome to the Cloud Rapid Experimentation and Analysis Toolkit
#cloud

Cloud Rapid Experimentation and Analysis Tool (aka CBTOOL) is a framework that automates IaaS cloud benchmarking through the running of controlled experiments.

## To get started:

1. [Learn more about the tool](https://github.com/ibmcb/cbtool/wiki/DOC:-Table-of-Contents)
2. [Perform the initial installation](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Initial-Installation)
3. [Run the tool for the first time](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Running-the-tool-for-the-first-time)
4. [Prepare a VM image to be used with the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-a-VM-to-be-used-with-CBTOOL-on-a-real-cloud)
5. [Run simple experiments](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-simple-experiments)
6. Look at some [auto generated plots](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Save-Monitoring-Data-on-the-Command-Line) made from the data collected.
7. Read our latest paper (to appear in IC2E 2013).
8. Try to get connected with the [Graphical Wizard](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Wizard-for-first-time-connection)
9. Try administrating the tool with the [Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Graphical-Environment)
10. Then try [monitoring your experiments with the Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Monitoring-with-the-Graphical-Environment)
11. Try to [customize your dashboard monitoring data with filters in the Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Customize-Dashboard-Monitoring-in-the-Graphical-Environment)
12. Read the [Frequently Asked Questions](https://github.com/ibmcb/cbtool/wiki/FAQ)

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

Contacts:

Marcio Silva marcios@us.ibm.com
Michael R. Hines mrhines@us.ibm.com
