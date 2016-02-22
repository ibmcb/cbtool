# Welcome to the Cloud Rapid Experimentation and Analysis Toolkit

Cloud Rapid Experimentation and Analysis Tool (aka CBTOOL) is a framework that automates IaaS cloud benchmarking through the running of controlled experiments.

Subscribe to our mailing list:

Users: https://groups.google.com/forum/#!forum/cbtool-users

Development: https://groups.google.com/forum/#!forum/cbtool-devel

## To get started:

1. [Learn more about the tool](https://github.com/ibmcb/cbtool/wiki/DOC:-Table-of-Contents)

2. [Perform the initial installation](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Initial-Installation)

3. [Run the tool for the first time](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Running-the-tool-for-the-first-time)

4. [Prepare your cloud to be driven by the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-your-cloud-to-be-driven-by-CBTOOL)

5. [Prepare a VM image to be used with the tool](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Preparing-a-VM-to-be-used-with-CBTOOL-on-a-real-cloud)

6. [Run simple experiments](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-simple-experiments)

7. [Configure CBTOOL to run outside of the cloud (or with multiple tenant networks)] (https://github.com/ibmcb/cbtool/wiki/HOWTO:-Run-the-CloudBench-orchestrator-outside-of-the-cloud-(or-with-multiple-tenant-networks))

    1. [Detailed instructions on how to use OpenVPN support](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Use-VPN-support-with-your-benchmarks)
    
8. Look at some [auto generated plots](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Save-Monitoring-Data-on-the-Command-Line) made from the data collected.

9. Read our latest paper [IC2E 2013](http://dl.acm.org/citation.cfm?id=2497243).

10. Try to get connected with the [Graphical Wizard](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Wizard-for-first-time-connection)

11. Try administrating the tool with the [Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Using-the-Graphical-Environment)

12. Then try [monitoring your experiments with the Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Monitoring-with-the-Graphical-Environment)

13. Try to [customize your dashboard monitoring data with filters in the Graphical Environment](https://github.com/ibmcb/cbtool/wiki/HOWTO:-Customize-Dashboard-Monitoring-in-the-Graphical-Environment)

14. Read the [Frequently Asked Questions](https://github.com/ibmcb/cbtool/wiki/FAQ)

## Features:
- Automatic deployment and controlled execution of multiple multi-tier applications.
Each individual application can have a specific load profile using probability distributions.
- Adapters for multiple clouds (EC2 and OpenStack, among others), with a plugin structure that allows new cloud models to be added incrementally.
- Can orchestrate different arrival rates and lifetimes for VMs using probability distributions.
- Collects application and system (OS) performance data from hosts and guests in real time.
- It is designed from the ground up to be highly scalable and parallel.

## [Supported Clouds](https://github.com/ibmcb/cbtool/wiki/DOC:-Supported-Clouds):

1. Amazon EC2
2. OpenStack (and RackSpace)
3. DigitalOcean
4. IBM SCP and IBM SCE
5. "pure" Libvirt+KVM or Libvirt+XEN (soon)
6. VMWare vCloud (in progress)
7. CloudStack
8. SoftLayer

Contacts:

Marcio Silva marcios@us.ibm.com
Michael R. Hines mhines@digitalocean.com 

