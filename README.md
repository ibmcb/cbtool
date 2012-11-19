INTRODUCTION:
=============

Cloud Rapid Experimentation and Analysis Tool is a framework that automates IaaS cloud benchmarking through the running of controlled experiments.

FEATURES:
=========

* Automatic deployment and controlled execution of multiple multi-tier applications.
* Each individual application can have a specific load profile using probability distributions.
* Adapters for multiple clouds (EC2 and OpenStack, among others), with a plugin structure that allows new cloud models to be added incrementally.
* Can orchestrate different arrival rates and lifetimes for VMs using probability distributions.
* Collects application and system (OS) performance data from hosts and guests in real time.
* It is designed from the ground up to be highly scalable and parallel.

CONTACTS:
=========

Marcio A. L. Silva marcios@us.ibm.com

Michael R. Hines mrhines@us.ibm.com

QUICKSTART
=========

If you are running the tool for the first time, please run ```configure``` first. It will check if all dependencies (e.g., Redis, MongoDB) are properly installed and configured.

The tool reads all configuration parameters from a file name ```cloud_definitions.txt``` located on the ```configs``` directory. It is recommended that you make a copy of this file (on the same directory),
naming it ```<you username>_cloud_definitions.txt```.

To run the tool's CLI, use ```cb```. Initially, you will see an empty prompt, ```()```, indicating that there is no
cloud attached to this experiment.

In the tool prompt, try to attach a simulated cloud using the command ```cldattach sim TESTCLOUD```. You will you see that now the prompt changes to ```(TESCLOUD)```.

After that, attach all simulated hosts defined on the configuration file with the command ```vmcattach all```. List all simulated HOSTS on this cloud with the command ```hostlist```.

At this point you can create some simple simulated VMs with the command ```vmattach db2``` or ```vmattach was```. Make sure all simulated VMs are created with the command ```vmlist```.

All ```<object>attach``` commands block the CLI during its execution. Since some commands (e.g., ```aiattach```) can take quite a bit of time to complete, the keyword ```async``` can be appended at the end of the command to allow its execution in background. For instance, while deploying a DayTrader Virtual Application with the command ```aiattach daytrader``` would block the CLI for several minutes (depending on the cloud), the command ```aiattach daytrader async``` would return immediately, leaving a daemon executing the deployment in the background.

The purpose of starting  with a simulated cloud is to make sure that everything is working properly within the tool *before* starting to use the tool against a real cloud.

To exit, use the ```exit``` command. You can exit and restart the tool at any moment; the data/state is stored on an ```Object Store``` (Redis server) that is accessed by the CLI.

Whenever a CLI is started, a web GUI daemon is also started. Just point your browser to the port indicated at the tool's CLI prompt (look for "GUI Service daemon was successfully started"), and then click on the ```Connect``` button on the top.

REPORTING BUGS:
===============

The tools writes all logs to a folder located @ "stores/logs". When you run into a bug, please packup the logs folder and send it to us and we'll work with you to get it fixed.

We would also like to start using github's bug tracking system: You could post all the details of your issue there - that would be very helpful.

USING THE TOOL IN A REAL CLOUD
============================

Currently the tool supports the following Clouds:

* OpenStack
* Amazon EC2
* IBM Smart Cloud Provisioning
* Thin Agile Cloud (barebones tool based on libvirt/KVM, used internally)

All aspects of VApp deployment are automated. The tool will know which VMs to create (based on a VApp template), and will contact the cloud management system directly to carry out the creation.
After the VMs are started, it logins on the VMs (through SSH), configures the applications and starts a load manager daemon. At this point, ```management metrics``` (e.g., image creation time, boot time) are collected.
During the whole VApp lifecycle, application and OS ```runtime metrics``` are collected and stored. If the cloud allows direct access to the hosts, their performance data is also collected.
If the VApp was implicitly deployed by a VApp Submitter, it is automatically removed at the end of its lifetime. If the VApp was explicitly deployed, it has to be removed by the experimenter.

Before using the tool in a real cloud, the following steps must be taken:

1. Add your own pair of ssh keys to the ```credentials``` directory

2. Prepare your own images to be used with the tool.
    1.  Make sure that the VMs can be contacted through passwordless SSH.
    2.  Make sure that the applications are installed/configured on your VM.
    Unfortunately, at this time we cannot provide pre-configured VMs due to
    licensing issues.
    3.  Copy the tool's code to the VM, and then run "configure" there. If the dependencies are installed on the VM, then the VM can be remotely accessed and controlled.
3. Fill out the information required to access the cloud (e.g., account names, credentials) on the configuration file. This file is either ```cloud_definitions.txt``` or preferably ```<your username>_cloud_definitions.txt```

After these steps are taken, go to the section "RUNNING EXPERIMENTS" and try to
run the first experiment (it is short, just type the commands).

GENERAL DESCRIPTION
===================

An ```experiment``` is executed by the deployment and running of a set of ```Virtual Applications``` (VApps). An experiment can be done interactively, having the user typing commands directly on the CLI, or having a series of commands in text format in an ```experiment file```.

A VApp represents a group of VMs, with different ```roles```, logically connected to execute different application types. For instance, a ```DayTrader VApp``` is composed by one VM with the role "load driver", one VM with the role "application server" (either Tomcat or WAS) and one VM with the role "db"
(either DB2 or MySQL). On other hand a ```Hadoop VApp``` is composed by one VM with the role "master" and N VMs with the role "slave". To see a list of available VM roles, use the command ```rolelist``` on the CLI. To see a list of VApp types use the command ```typelist```. To see a description of a particular VApp, use the command ```typeshow <vapp type>```.

Each VApp has its own ```load profile```, with independent load level and load duration. The values for load level and load duration can be set as random distributions, fixed numbers or monotonically increasing/decreasing sequences. The ```load level```, has a meaning that is specific to each VApp type. For
instance, for a DayTrader Vapp, it represents the number of simultaneous clients on the load generator, while for Hadoop it represents the size of dataset to be sorted.

VApps can be deployed explicitly by the experimenter or implicitly through one or more ```VApp Submitters```. A submitter deploys Vapps with a given ```pattern```, represented by a certain inter-arrival time and a lifetime (also fixed, distributions or sequences). To see a list of available patterns, use the command ```patternlist``` on the CLI. To see a description of a particular pattern, use the command ```patternshow <submitter pattern>```.

RUNNING EXPERIMENTS
====================

For instance, the following experiment file will create three VMs on an
OpenStack cloud, without generating any application load on it:

    cldattach osk TESTCLOUD
    clddefault TESTCLOUD
    expid exp1
    vmcattach all
    vmclist
    hostlist
    vmattach db2
    vmattach netperf
    vmlist
    waitfor 4m
    vmdetach all
    monextract all
    clddetach
    exit

This second experiment will deploy a single DayTrader VApp on EC2, and will vary
the load level with a normal distribution with average 10, standard deviation 5,
and maximum and minimal values 1 and 20. It will select a new load level each
minute, and will run for 5 hours.

    cldattach ec2 TESTCLOUD
    clddefault TESTCLOUD
    expid exp2
    vmcattach all
    vmclist
    typealter daytrader load_level=normalI10I5I1I20
    typealter daytrader load_duration=60
    aiattach daytrader
    waitfor 5h
    aidetach all
    monextract all
    clddetach
    exit

Finally this third experiment will keep generating new DayTrader and Hadoop
VApps, with a specific arrival rate for each VApp Type. DayTrader VApps will
arrive with an inter-arrival time according to an exponential distribution with
an average of 600 seconds (with maximum and minimum values of 200 and 2000
seconds), while Hadoop VApps will arrive with an inter-arrival time according to
a uniform distribution with values between 200 and 900 seconds. Also the load
level of the VApp Hadoop is set to be fixed in 9, while the lifetime is fixed to
be 7200 seconds. Finally, no more than 40 DayTrader VApps should be created,
and we should wait until the number of created VApps is equal to 100, and the
wait for 5 more hours.

    cldattach scp TESTCLOUD
    clddefault TESTCLOUD
    expid exp3
    vmcattach all
    vmclist
    patternlist
    patternshow simpledt
    patternalter simpledt iait=exponentialI600IXI200I2000
    patternalter simpledt max_ais=40
    patternshow simpledt
    patternshow simplehd
    patternalter simplehd iait=uniformIXIXI200I900
    patternalter simplehd load_level=9
    patternshow simplehd lifetime=7200
    patternshow simplehd
    aidrsattach simpledt
    aidrsattach simplehd
    waituntil AI ARRIVED=100
    aidrsdetach all
    waituntil AI ARRIVING=0
    ailist
    waitfor 5h
    aidetach all
    monextract all
    clddetach
    exit

DATA EXTRACTION AND ANALYSIS
============================

The command "monextract all" will create four different comma-separated value
files:

1. ```VM_management_<experiment id>.csv```: contains information regarding the provisioning time, capture time, among others, all extracted directly from the cloud management system.
2. ```VM_runtime_app_<experiment id>.csv```: contains information regarding the application performance, such as latency, throughput and bandwidth, all generated directly from the VM.
3. ```VM_runtime_os_<experiment id>.csv```: contains OS metrics (CPU, memory, disk I/O, network I/O) all generated by the VM.
4. ```HOST_runtime_os_<experiment id>.csv```: contains OS metrics (CPU, memory, disk I/O, network I/O) all generated by the HOSTS. It can only be used on  Clouds where there is direct access to the hosts (this means that this data cannot be collected on EC2, for instance), and where the Ganglia monitoring tool was manually configured on the hosts.

A small script (called cbp.R), written in the R language, is available in the ```util/plot``` directory, and can be used to quickly and automatically produce plots using the data supplied by the csv files.

Write Client code against the tool's API
=========================================

This toolkit provides API for client programming in 3 different languages using XML-RPC to be used to direct benchmarks and algorithms against the API for maximum flexibility.

Additionally, these bindings also provide accessor methods for retrieving data from the mongodb database which the tool uses to store monitoring data.

Typically, upon starting up the tool, an "API Service" (xmlrpc server) is started on port 7070.

In order to use it, you would choose a language:

1. Python: from import api_service_client import *
2. Java: import api.*;
3. Ruby: require 'api_service_client'

API Client Examples in each language:
=========
1. Python: clients/provision_vm.py, clients/provision_app.py
2. Java: clients/ProvisionVM.java, clients/ProvisionAPP.java
3. Ruby: clients/provision_vm.rb, clients/provision_app.rb

These examples are fairily self-explanatory. If you help or would like bindings written in a new language, don't hesitate to contact us and we'll try to accomodate you.