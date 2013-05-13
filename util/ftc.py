#!/usr/bin/env python

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

import sys, os, threading, SocketServer, signal, inspect, xmlrpclib, libxml2
from libvirt import *
from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO, WARN, CRITICAL
from logging.handlers import SysLogHandler
from optparse import OptionParser
from os import getuid
from pwd import getpwuid
from platform import node
from hashlib import sha256
from sys import stdout, path
from DocXMLRPCServer import DocXMLRPCServer
from socket import gethostbyname
from daemon import DaemonContext
from re import split, compile, MULTILINE
from uuid import uuid5, NAMESPACE_DNS
from random import randint
from time import sleep
path.append('/'.join(path[0].split('/')[0:-1]))
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

__all__ = []

import socket
import struct
import hmac
import random
import operator
try:
    from cStringIO import StringIO
except ImportError:
    import StringIO

sysrand = random.SystemRandom()

try :
    # Provided by RHEL 6.2
    from libvirt_qemu import qemuMonitorCommand
except ImportError:
    pass

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit, VerbosityFilter, MsgFilter

options = None

@trace
def actuator_cli_parsing() :
    # Do command line parsing
    usage = '''usage: %prog [options] 
    '''
    
    parser = OptionParser(usage)
    
    parser.add_option("-d", "--debug_host", dest = "debug_host", default = None, \
                      help = "Point CloudBench to a remote debugger")
    
    # Process options
    parser.add_option("--display", dest = "display", metavar = "display", \
                      default = "vnc", help = "Set the remote display type, Options: (vnc|spice)")
    
    parser.add_option("--hypervisor", dest = "hypervisor", metavar = "hypervisor", \
                      default = "kvm", help = "Set the hypervisor, Options: (kvm|xen|pv)")
    
    parser.add_option("--procid", dest = "processid", metavar = "processid", \
                      default = "TEST_" + getpwuid(getuid())[0], \
                      help = "Set the processid")

    parser.add_option("--loghost", dest = "loghost", metavar = "loghost", \
                      default = "127.0.0.1", \
                      help = "Set the syslog host to loghost")

    parser.add_option("--logport", dest = "logport", metavar = "logport", \
                      default = "5114", \
                      help = "Set the syslog port to logport")

    parser.add_option("--dhcp_omapi_server", dest = "dhcp_omapi_server", metavar = "dhcp_omapi_server", \
                      default = "127.0.0.1", \
                      help = "Set the OMAPI dhcp address to get IP addresses")

    parser.add_option("--dhcp_omapi_port", dest = "dhcp_omapi_port", metavar = "dhcp_omapi_port", \
                      default = "9991", \
                      help = "Set the port to dhcp OMAPI service")

    parser.add_option("--hyp", dest = "hypervisors", metavar = "hyp", \
                      default = "127.0.0.1", \
                      help = "Set the comma-separated list of hypervisors to hyp")
    parser.add_option("--port", dest = "port", metavar = "port", \
                      default = "6060", \
                      help = "Set the REST port for FTC to be port")
    
    parser.add_option("--daemon", dest = "daemon", action = "store_true", \
                  default = False, \
                  help ="Execute operation in daemonized mode")

    parser.add_option("--bridge", dest = "bridge", metavar = "bridge", \
                      default = "br0", \
                      help = "Set the software bridge name on each node")

    parser.add_option("--base_storage", dest = "base_storage", metavar = "base_storage", default = "/kvm_repo", \
                      help = "Set the qcow base file location on each node")

    parser.add_option("--snapshot_storage", dest = "snapshot_storage", metavar = "snapshot_storage", default = "/kvm_repo", \
                      help = "Set the qcow snapshot location on each node")
    
    parser.add_option("--lvm_storage", dest = "lvm_storage", metavar = "lvm_storage", default = "cb", \
                      help = "Set the LVM location on each node")

    parser.add_option("--cache_mode", dest = "cache_mode", metavar = "cache_mode", default = "none", \
                      help = "")

    parser.add_option("--disk_mode", dest = "disk_mode", metavar = "disk_mode", default = "virtio", \
            help = "Options: virtio, ide, scsi")

    parser.add_option("--net_mode", dest = "net_mode", metavar = "net_mode", default = "virtio", \
            help = "Options: virtio, pci")

    parser.add_option("--qemu_binary", dest = "qemu_binary", metavar = "qemu_binary", default = "/usr/libexec/qemu-kvm", \
              help = "Location of qemu binary program")

    parser.add_option("--mac_prefix", dest = "mac_prefix", metavar = "mac_prefix", default = "12:34", \
              help = "Global 2-byte prefix for FTC mac addresses")

    parser.add_option("--disable_vhost_net", dest = "disable_vhost_net", metavar = "disable_vhost_net", default = False, \
              help = "Disable libvirt/qemu use of vhost network system")
    
    parser.add_option("--cloud_name", dest = "cloud_name", metavar = "cloud_name", default = "ftc_default_name", \
              help = "Name this cloud...")
    
    # Verbosity Options
    parser.add_option("-v", "--verbosity", dest = "verbosity", metavar = "LV", \
                      default = 3, help = "Set verbosity level to LV")

    parser.add_option("-q", dest = "quiet", action = "store_true", \
                      help = "Set quiet output.")
    
    parser.set_defaults()
    (options, _args) = parser.parse_args()

    if options.debug_host is not None :
        import debug
        print str(sys.path)
        import pydevd
        pydevd.settrace(host=options.debug_host)

    return options

def unwrap_kwargs(func, spec):
    def wrapper(*args, **kwargs):
        if args and isinstance(args[-1], list) and len(args[-1]) == 2 and "kwargs" == args[-1][0]:
            return func(*args[:-1], **args[-1][1])
        else:
            return func(*args, **kwargs)
        
    wrapper.__doc__ = str(spec)
    if func.__doc__ is not None :
        wrapper.__doc__ +=  "\n\n" + func.__doc__
    return wrapper

class Ftc :
    @trace
    def ftcraise(self, host, status, msg) :
        # We try to keep connections open as long as possible, but if there is an
        # error, make sure we close it and don't attempt to reused an old one
        if host in self.lvt_cnt and self.lvt_cnt[host] :
            try :
                self.lvt_cnt[host].close()
            except :
                pass
        self.lvt_cnt[host] = False
        msg = msg.replace(" __request failed:", "")
        cberr(msg, True)
        raise xmlrpclib.Fault(3, 'FTCException;%s;%s' % (msg, str(status)))

    @trace    
    def global_error(self, ctx, error) :
        cbdebug("libvirt global error: " + error)

    @trace
    def success(self, msg, result) :
        cbdebug(msg)
        return {"status" : 0, "msg" : msg, "result" : result }

    @trace
    def error(self, status, msg, result) :
        cberr(msg)
        return {"status" : status, "msg" : msg, "result" : result }

    @trace
    def conn_check(self, host) :
        if host not in self.lvt_cnt or not self.lvt_cnt[host] :
            try :
                if options.hypervisor in [ "xen", "pv" ] :
                    self.lvt_cnt[host] = open("xen+tcp://" + host)
                elif options.hypervisor == "kvm" :
                    self.lvt_cnt[host] = open("qemu+tcp://" + host + "/system")
                cbdebug("Libvirt connection to " + host + " successfully established.")
                #registerErrorHandler(self.global_error, "blah")
                self.lvt_cnt[host].host = host
            except libvirtError, msg :
                self.ftcraise(host, 394, str(msg))
                
        return self.lvt_cnt[host]

    @trace
    def test(self, node_name) :
        self.conn_check(node_name)
        return self.success("Libvirt connection to " + node_name + " successful", None)

    @trace
    def __init__ (self, hypervisors) :
        self.pid = "" 
        self.hypervisors = hypervisors
        self.lvt_cnt = {}
        self.dhcp_omap_pkey = "d+y8yPwtC0nJ0C0uRC5cxYREYGPBkJwhJYjHbb1LkoW0FF6gYr3SiVi6 HRQUcl4Y7gdzwvi0hgPV+Gdy1wX9vg==" 
        self.dhcp_omap_keyn = "omapi_key"
        self.vhw_config = {}
        self.vhw_config["pico32"] = { "vcpus" : "1", "vmemory" : "192", "vstorage" : "2048", "vnics" : "1" }
        self.vhw_config["nano32"] = { "vcpus" : "1", "vmemory" : "512", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["micro32"] = { "vcpus" : "1", "vmemory" : "1024", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["copper32"] = { "vcpus" : "1", "vmemory" : "2048", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze32"] = { "vcpus" : "1", "vmemory" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["iron32"] = { "vcpus" : "2", "vmemory" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["silver32"] = { "vcpus" : "4", "vmemory" : "2048", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["gold32"] = { "vcpus" : "8", "vmemory" : "4096", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["cooper64"] = { "vcpus" : "2", "vmemory" : "4096", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze64"]  = { "vcpus" : "2", "vmemory" : "4096", "vstorage" : "870400", "vnics" : "1" }
        self.vhw_config["silver64"] = { "vcpus" : "2", "vmemory" : "8192", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["gold64"] = { "vcpus" : "8", "vmemory" : "16384", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["platinum64"] = { "vcpus" : "16", "vmemory" : "16384", "vstorage" : "2097152", "vnics" : "1" }

        self.vhw_config["premium"] = { "cpu_upper" : "1000", "cpu_lower" : "1000", "memory_upper" : "100", "memory_lower" : "100" }
        self.vhw_config["standard"] = { "cpu_upper" : "1000", "cpu_lower" : "500", "memory_upper" : "100", "memory_lower" : "50" }
        self.vhw_config["value"] = { "cpu_upper" : "-1", "cpu_lower" : "0", "memory_upper" : "100", "memory_lower" : "0" }

        self.counter = 0

    @trace
    def get_libvirt_vm_templates(self, num_ids, disk_format, qemu_debug_port) :

        _xml_templates = {}
        if options.hypervisor in [ "xen", "pv" ] :
            _xml_templates["vm_template"] = "<domain type='xen' "
        else :
            _xml_templates["vm_template"] = "<domain type='kvm' "
        
        if options.hypervisor == "kvm" and (qemu_debug_port):
            _xml_templates["vm_template"] += "xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'"
             
        _xml_templates["vm_template"] += ">\n"
        _xml_templates["vm_template"] += "\t<name>TMPLT_LIBVIRTID</name>\n"
        _xml_templates["vm_template"] += "\t<memory>TMPLT_MEMORY</memory>\n"
        _xml_templates["vm_template"] += "\t<currentMemory>TMPLT_MEMORY</currentMemory>\n"
        _xml_templates["vm_template"] += "\t<vcpu>TMPLT_VCPUS</vcpu>\n"

        if options.hypervisor == "pv" :
            _xml_templates["vm_template"] += "\t<bootloader></bootloader>\n"

        _xml_templates["vm_template"] += "\t<os>\n"

        if options.hypervisor == "xen" :
            _xml_templates["vm_template"] += "\t\t<type arch='x86_64' machine='xenfv'>hvm</type>\n"
        elif options.hypervisor == "pv" :
            _xml_templates["vm_template"] += "\t\t<type>linux</type>\n"
        else :
            _xml_templates["vm_template"] += "\t\t<type machine='pc'>hvm</type>\n"
        if options.hypervisor == "xen" :
            _xml_templates["vm_template"] += "\t\t<loader>/usr/lib/xen/boot/hvmloader</loader>\n"
        _xml_templates["vm_template"] += "\t\t<boot dev='hd'/>\n"
        _xml_templates["vm_template"] += "\t</os>\n"

        if options.hypervisor != "pv" :
            _xml_templates["vm_template"] += "\t<features>\n"
            _xml_templates["vm_template"] += "\t\t<acpi/>\n"
            _xml_templates["vm_template"] += "\t\t<apic/>\n"
            _xml_templates["vm_template"] += "\t\t<pae/>\n"
            _xml_templates["vm_template"] += "\t</features>\n"

        _xml_templates["vm_template"] += "\t<devices>\n"
        _xml_templates["vm_template"] += "\t\t<emulator>" + options.qemu_binary + "</emulator>\n"
        
        for _idx in range(0, num_ids) :
            if disk_format == "lvm" :
                if options.hypervisor == "pv" :
                    _xml_templates["vm_template"] += "\t\t<disk type='file' device='disk'>\n"
                else :
                    _xml_templates["vm_template"] += "\t\t<disk type='block' device='disk'>\n"

                if options.hypervisor == "pv" :
                    _xml_templates["vm_template"] += "\t\t\t<source file='/dev/" + options.lvm_storage + "/TMPLT_POOLBASE" + str(_idx) + "'/>\n"
                else :
                    _xml_templates["vm_template"] += "\t\t\t<source dev='/dev/" + options.lvm_storage + "/TMPLT_POOLBASE" + str(_idx) + "'/>\n"
                
                if options.hypervisor == "kvm" :
                    _xml_templates["vm_template"] += "\t\t\t<driver name='qemu' type='raw' cache='" + options.cache_mode + "'/>\n"
                elif options.hypervisor == "pv" :
                    _xml_templates["vm_template"] += "\t\t\t<driver name='tap2' type='aio'/>\n"
            else :
                _xml_templates["vm_template"] += "\t\t<disk type='file' device='disk'>\n"
                _xml_templates["vm_template"] += "\t\t\t<source file='" + options.snapshot_storage + "/cb/TMPLT_POOLBASE" + str(_idx) + "'/>\n"
                if options.hypervisor == "kvm" :
                    _xml_templates["vm_template"] += "\t\t\t<driver name='qemu' type='" + disk_format + "' cache='" + options.cache_mode + "'/>\n"

            _xml_templates["vm_template"] += "\t\t\t<target dev='"
            if options.hypervisor in [ "xen", "pv" ] :
                _xml_templates["vm_template"] += "xv"
            elif options.disk_mode == "virtio" :
                _xml_templates["vm_template"] += "v"
            elif options.disk_mode == "ide" :
                _xml_templates["vm_template"] += "h" 
            elif options.disk_mode == "scsi" :
                _xml_templates["vm_template"] += "s"
                
            if options.hypervisor in ["pv", "xen"] :
                _xml_templates["vm_template"] += "d" + chr(ord('a') + _idx) + "' bus='xen'/>\n"
            else :
                _xml_templates["vm_template"] += "d" + chr(ord('a') + _idx) + "' bus='" + options.disk_mode + "'/>\n"
                 
            _xml_templates["vm_template"] += "\t\t</disk>\n"
            
        _xml_templates["vm_template"] += "\t\t<interface type='bridge'>\n"
        _xml_templates["vm_template"] += "\t\t\t<source bridge='" + options.bridge + "'/>\n"
        _xml_templates["vm_template"] += "\t\t\t<mac address='TMPLT_MACADDRESS'/>\n"
        if options.hypervisor == "kvm" and options.net_mode == "virtio" :
            _xml_templates["vm_template"] += "\t\t\t<model type='virtio'/>\n"
            if options.disable_vhost_net :
                _xml_templates["vm_template"] += "\t\t\t<driver name='qemu'/>\n"
        _xml_templates["vm_template"] += "\t\t</interface>\n"
        _xml_templates["vm_template"] += "\t\t<serial type='pty'>\n"
        _xml_templates["vm_template"] += "\t\t\t<target port='0'/>\n"
        _xml_templates["vm_template"] += "\t\t</serial>\n"

        _xml_templates["vm_template"] += "\t\t<console type='pty'>\n"

        if options.hypervisor == "pv" :
            _xml_templates["vm_template"] += "\t\t\t<target type='xen' port='0'/>\n"
        else :
            _xml_templates["vm_template"] += "\t\t\t<target port='0'/>\n"

        _xml_templates["vm_template"] += "\t\t</console>\n"

        if options.hypervisor == "pv" :
            _xml_templates["vm_template"] += "\t\t<input type='mouse' bus='xen'/>\n"
        else :
            _xml_templates["vm_template"] += "\t\t<input type='tablet' bus='usb'>\n"
            _xml_templates["vm_template"] += "\t\t\t<alias name='input0'/>\n"
            _xml_templates["vm_template"] +=  "\t\t</input>\n"
            _xml_templates["vm_template"] += "\t\t<input type='mouse' bus='ps2'/>\n"
        
        _xml_templates["vm_template"] += "\t\t<graphics type='" + options.display + "' port='-1' autoport='yes' listen='0.0.0.0' keymap='en-us'/>\n"
        _xml_templates["vm_template"] += "\t\t<video>\n"
        _xml_templates["vm_template"] += "\t\t\t<model type='cirrus' vram='9216' heads='1'/>\n"
        _xml_templates["vm_template"] += "\t\t</video>\n"
        if options.hypervisor == "xen" :
            _xml_templates["vm_template"] += "\t\t<memballoon model='xen'/>\n"
        else :
            _xml_templates["vm_template"] += "\t\t<memballoon model='virtio'/>\n"
        _xml_templates["vm_template"] += "\t</devices>\n"
        
        if qemu_debug_port :
            _xml_templates["vm_template"] += "\t<qemu:commandline>\n"
            
            # Primary gdb debugging port 
            if qemu_debug_port :
                _xml_templates["vm_template"] += "\t\t<qemu:arg value='-gdb'/>\n"
                _xml_templates["vm_template"] += "\t\t<qemu:arg value='tcp::" + str(qemu_debug_port) + "'/>\n"
                
            _xml_templates["vm_template"] += "\t</qemu:commandline>\n"

        _xml_templates["vm_template"] += "</domain>\n"
        
        for _idx in range(0, num_ids) :
            xml_key = "disk_template" + str(_idx)
            _xml_templates[xml_key] = ""
            _xml_templates[xml_key] += "\t<volume>\n"
            _xml_templates[xml_key] += "\t<name>TMPLT_POOLBASE" + str(_idx) + "</name>\n"
            if disk_format == "lvm" :
                # Make a 2GB snapshot, by default - will make configurable later
                _xml_templates[xml_key] += "\t<capacity>2013265920</capacity>\n"
            else :
                _xml_templates[xml_key] += "\t<capacity>TMPLT_CAPACITY" + str(_idx) + "</capacity>\n"
            _xml_templates[xml_key] += "\t<target>\n"
            if disk_format == "lvm" :
                _xml_templates[xml_key] += "\t\t<path>TMPLT_POOLBASE" + str(_idx) + "</path>\n"
            else :
                _xml_templates[xml_key] += "\t\t<path>" + options.snapshot_storage + "/cb/TMPLT_POOLBASE" + str(_idx) + "</path>\n"
                _xml_templates[xml_key] += "\t\t<format type='" + disk_format + "'/>\n"
            _xml_templates[xml_key] += "\t</target>\n"
            _xml_templates[xml_key] += "\t<backingStore>\n"
            if disk_format == "lvm" :
                _xml_templates[xml_key] += "\t\t<path>/dev/" + options.lvm_storage + "/TMPLT_BASE" + str(_idx) + "</path>\n"
            else :
                _xml_templates[xml_key] += "\t\t<path>" + options.base_storage + "/TMPLT_BASE" + str(_idx) + "</path>\n"
                _xml_templates[xml_key] += "\t\t<format type='" + disk_format + "'/>\n"
            _xml_templates[xml_key] += "\t</backingStore>\n"
            _xml_templates[xml_key] += "\t</volume>\n"
    
        return _xml_templates

        
    @trace
    def get_mac_addr(self):
        '''
        This function is designed to pseudo-determinstically generate MAC addresses.
        
        The standard 6-byte MAC address is splitup as follows:
        
        | prefix (X bytes long) | selector byte | suffix (Y bytes long) |
        
        For example:
        1. The user sets an X-byte long 'mac_prefix' == '12:34'. This is used to 
           represent all experiments in a shared cluster controlled by FTCloud.
           For each shared cluster, this prefix should never need to change.
           This prefix is also used in the DHCP server configuration to ensure
           that requests from outside VMs are not answered to VMs that do not
           belong to this cluster. If there is more than one private DHCP server
           in the cluster, then, this mac_prefix should be changed, otherwise not.
        
        2. The selector byte is generated automatically to provide additional
           uniqueness and predictability in the MAC address to prevent
           collisions among users of the same shared cluster. It is a hash of 
           the username of the benchmark combined with the hostname of the VM 
           running the benchmark.
           
        3. The remaining Y-byte suffix is generated at provisioning time. This is done
           by having the datastore maintain a counter that represents the last used
           MAC address. An increasing counter ensures that collisions never happen
           but only requires a small amount of memory even when the number of Y
           bytes in the suffix is very large.
        '''

        # Form the 1st two parts of the MAC address 
        self.counter = self.counter + 1
        counter = self.counter

        bytes_needed = (17 - len(options.mac_prefix)) / 3 - 1
        unique_mac_selector_key = node() + getpwuid(getuid())[0] + options.cloud_name + "ftc"
        selector_byte = sha256(unique_mac_selector_key).hexdigest()[-2:]
        mac = options.mac_prefix + ":" + selector_byte 
        
        for x in range(0, bytes_needed) :
            byte = ((counter >> (8 * ((bytes_needed - 1) - x))) & 0xff)
            mac += (":%02x" % (byte)) 
        
        return mac.replace('-', ':')

    @trace
    def node_cleanup(self, node_name, image_filter, disk_format = "qcow2" ) :
        lvt_cnt = self.conn_check(node_name)
        graceful = False
        
        try :
            _domains = self.list_domains(lvt_cnt, False, image_filter)
            _imsg = "All domains on libvirt host " + lvt_cnt.host
            _smsg = _imsg + " were successfully destroyed."
            _fmsg = _imsg + " could not be destroyed: "

            if len(_domains) > 0:
                _msg = "Issuing shutdowns to " + str(len(_domains))
                _msg += " running VMs on host " + lvt_cnt.host
                cbdebug(_msg, True)

                if not graceful :
                    for name in _domains :
                        _domains[name].destroy()
                        _msg = "domain id " + name + " destroyed on "
                        _msg += lvt_cnt.host
                        cbdebug(_msg, True)
            else :

                tries = 40 

                # First issue shutdowns to them all
                stall_secs = 15
                for name in _domains :
                    if _domains[name].isActive() :
                        _domains[name].shutdown()
                        _msg = "Iterative shutdown issued to domain id "
                        _msg += name + " on " + lvt_cnt.host
                        cbdebug(_msg, True)

                        if len(_domains) > 10 :
                            _msg = "> 10 domains: shuting down in "
                            _msg += str(stall_secs) + "-second intervals to"
                            _msg += " not starve disk."
                            cbdebug(_msg, True)
                            sleep(stall_secs)

                while tries > 0 :
                    active = 0 
                    for name in _domains :
                        if _domains[name].isActive() :
                            try :
                                _domains[name].shutdown()
                            except :
                                True
                            active += 1

                    if not active :
                        break

                    tries -= 1

                    _msg = "(" + str(tries) + " chances left) for "
                    _msg += str(active) + " domains on " + lvt_cnt.host
                    cbdebug(_msg, True)
                    sleep(10)

                for _name in _domains :
                    if _domains[_name].isActive() :
                        _msg = "domain id " + _name + " shutdown failed. "
                        _msg += "Will have to destroy it."
                        cbdebug(_msg, True)
                        _domains[name].destroy()

            # Now undefine all VMs on the host                    
            _domains = self.list_domains(lvt_cnt, True, "cb")
    
            for _name in _domains :
                self.destroy_and_undefine_domain(lvt_cnt, _domains[_name].name(), False)
                          
            cbdebug(_smsg)
                
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
            
        
        snapshot_template = ""
        basestorage_template = ""
        snapshot_poolname = "ftc-snapshots"
        basestorage_poolname = "ftc-basestorage"
        
        if disk_format == "lvm" : 
            snapshot_poolname += "-lvm"
            basestorage_poolname += "-lvm"
            snapshot_template += "<pool type='logical'>"
            snapshot_template += "  <name>" + snapshot_poolname + "</name>"
            snapshot_template += "  <source>"
            snapshot_template += "    <name>" + options.lvm_storage + "</name>"
            snapshot_template += "    <format type='lvm2'/>"
            snapshot_template += "  </source>"
            snapshot_template += "  <target>"
            snapshot_template += "    <path>/dev/" + options.lvm_storage + "</path>"
            snapshot_template += "  </target>"
            snapshot_template += "</pool>"
            
            basestorage_template += "<pool type='logical'>"
            basestorage_template += "  <name>" + basestorage_poolname + "</name>"
            basestorage_template += "  <source>"
            basestorage_template += "    <name>" + options.lvm_storage  + "</name>"
            basestorage_template += "    <format type='lvm2'/>"
            basestorage_template += "  </source>"
            basestorage_template += "  <target>"
            basestorage_template += "    <path>/dev/" + options.lvm_storage  + "</path>"
            basestorage_template += "  </target>"
            basestorage_template += "</pool>"
        else :
            snapshot_template += "<pool type='dir'>\n" 
            snapshot_template += "<name>" + snapshot_poolname + "</name>\n"
            snapshot_template += "<target>\n"
            snapshot_template += "<path>" + options.snapshot_storage + "/cb</path>\n"
            snapshot_template += "</target>\n"
            snapshot_template += "</pool>" 
            
            basestorage_template += "<pool type='dir'>\n" 
            basestorage_template += "<name>" + basestorage_poolname + "</name>\n"
            basestorage_template += "<target>\n"
            basestorage_template += "<path>" + options.base_storage + "</path>\n"
            basestorage_template += "</target>\n"
            basestorage_template += "</pool>\n"

        for (xml, poolname) in [(snapshot_template, snapshot_poolname), \
                                (basestorage_template, basestorage_poolname)] :
            _imsg = poolname + " pool on libvirt host " + lvt_cnt.host
            _smsg = _imsg + " was successfully created."
            _fmsg = _imsg + " could not be created: "
                
            recreate_pool = True 
            try : 
                _poolnames = lvt_cnt.listDefinedStoragePools()
                _poolnames += lvt_cnt.listStoragePools()
                for _name in _poolnames :
                    if _name == poolname :
                        cbdebug("Pool " + poolname + " already created.")
                        _pool = lvt_cnt.storagePoolLookupByName(_name)
                        try :
                            self.activate_pool_if_inactive(lvt_cnt, _pool)
                            if disk_format == "lvm" :
                                recreate_pool = False
                                break
                            _pool.destroy()
                        except libvirtError, err :
                            # This happens when an old storage pool was tampered with,
                            # such as underlying directories were deleted incorrectly
                            # OK to ignore - because we are about to destroy it and
                            # re-create it anyway
                            if err.err[0] == VIR_FROM_STREAMS :
                                cberr("Invalid defined storage pool: " + _name + ". Will destroy and re-create...")
                            else :
                                # Just throw exception back to the main handler
                                raise err
                            
                        _pool = lvt_cnt.storagePoolLookupByName(_name)
                        if _pool.isPersistent() :
                            _pool.undefine()
                        break
                    
                if recreate_pool :
                    _pool = lvt_cnt.storagePoolDefineXML(xml, 0)
                    _pool.setAutostart(1)
                    if disk_format != "lvm" :
                        _pool.build(0)
                    _pool.create(0)
                    cbdebug(_smsg)
            except libvirtError, msg :
                self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
                
        self.snapshot_volume_destroy(lvt_cnt, image_filter, disk_format = disk_format)
        
        return self.success("Node " + node_name + " was successfully cleaned up.", None)

    @trace
    def node_register(self, node_name) :
        lvt_cnt = self.conn_check(node_name)
        attr_list = {}
        attr_list["cloud_ip"] = gethostbyname(node_name)
        
        _host_info_dict = {}   
        _imsg = "Information about libvirt host " + lvt_cnt.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            cpu_info = lvt_cnt.getInfo()
        except libvirtError, msg : 
            self.ftcraise(lvt_cnt.host, 3, _fmsg + ": " + str(msg))
            
        _host_info_dict["cores_arch"] = cpu_info[0]
        _host_info_dict["memory_size"] = cpu_info[1] 
        _host_info_dict["cores"] = int(cpu_info[2])
        _host_info_dict["core_freq"] = cpu_info[3]
        _host_info_dict["threads_per_core"] = cpu_info[4]
        _host_info_dict["sockets"] = cpu_info[5]
        _host_info_dict["cores_per_socket"] = cpu_info[6]
        _host_info_dict["numa_cells"] = cpu_info[7]
        _host_info_dict["uuid"] = False
           
        try :
            _system_info = lvt_cnt.getSysinfo(0)
            for key in _system_info.split('\n') :
                if key.count("uuid") :
                    _host_info_dict["uuid"] = split('<|>', key)[2]
            cbdebug(_smsg)

        # START HACK ALERT    
        except libvirtError, msg:
            _msg = "Unable to get asset information about the host "
            _msg += lvt_cnt.host + ": " + str(msg)
            cbwarn(_msg)
         
        except AttributeError:
            _msg = "Libvirt bindings too old for getSysinfo"
            cbwarn(_msg)
        
        if not _host_info_dict["uuid"] :    
            _host_info_dict["uuid"] = str(uuid5(NAMESPACE_DNS, "fakeuuid" + str(randint(0,100000000000))))
            _msg = "Libvirt too old. Returning fake uuid."
            _msg += _smsg
            cbdebug(_msg)
        # END HACK ALERT
        
        attr_list["hostextra"] = _host_info_dict
        attr_list["cloud_uuid"] = _host_info_dict["uuid"]
        del attr_list["hostextra"]["uuid"]
        
        return self.success("Node " + node_name + " was successfully registered.", attr_list)

    @trace
    def get_ip_address(self, mac) :
        ip = None
        try:
            _status = 100
            o = Omapi(options.dhcp_omapi_server, int(options.dhcp_omapi_port), \
                      self.dhcp_omap_keyn, self.dhcp_omap_pkey, debug=False)
            _msg = "ip found"
            ip = o.lookup_ip(mac)
            
        except Exception:
            _msg = "ip not found"
            pass
        
        return self.success(_msg, ip)
    
    @trace
    def get_display_ports(self, lvt_cnt, dom):
        xmlstr = dom.XMLDesc(0)
        doc = libxml2.parseDoc(xmlstr)
        ctx = doc.xpathNewContext()
        nodelist = ctx.xpathEval("/domain/devices/graphics[1]/@port")
        port = nodelist and nodelist[0].content or None
        nodelist = ctx.xpathEval("/domain/devices/graphics[1]/@type")
        protocol = nodelist and nodelist[0].content or None          
        if not protocol :
            self.ftcraise(lvt_cnt.host, 4, "CB internal error! display is missing in XML!")
        if not port :
            self.ftcraise(lvt_cnt.host, 6, "CB internal error! port is missing in XML!")
        
        return port, protocol
        
    @trace
    def run_instances(self, imageids, tag, hypervisor_ip, \
            size = "micro32", vmclass = "standard", 
            eclipsed_size = None, eclipsed = False, \
            qemu_debug_port = None, \
            cloud_mac = None, disk_format = None) :

        result = {}

        _num_ids = len(imageids)

        lvt_cnt = self.conn_check(hypervisor_ip)
        _graceful = False
        
        try :
            cbdebug("Going to check if domain \"" + tag + "\" is defined...")

            for _tag in lvt_cnt.listDefinedDomains() :
                if _tag == tag :
                    self.destroy_and_undefine_domain(lvt_cnt, tag, _graceful)
            for _dom_id in lvt_cnt.listDomainsID() :
                if lvt_cnt.lookupByID(_dom_id).name() == tag :
                    self.destroy_and_undefine_domain(lvt_cnt, tag, _graceful)
        except libvirtError, msg:
            cbdebug(" \"" + tag + "\" is not defined.... continuing")

        result["cloud_mac"] = self.get_mac_addr() if cloud_mac is None else cloud_mac
        result["size"] = size 
        result["class"] = vmclass
                
        if eclipsed and eclipsed_size is not None :
            result["size"] = eclipsed_size 
            result["configured_size"] = size 
            result["vcpus_configured"] = self.vhw_config[result[size]]["vcpus"]
            result["vmemory_configured"] = self.vhw_config[result[size]]["vmemory"]
            
        result.update(self.vhw_config[result["size"]])
        result.update(self.vhw_config[result["class"]])

        for _idx in range(0, _num_ids) :
            result["poolbase" + str(_idx)] = imageids[_idx] + "-" + tag
        
            try :
                pool_name = "ftc-basestorage" + ("-lvm" if disk_format == "lvm" else "")
                cbdebug("Looking up pool: " + pool_name)
                _pool = lvt_cnt.storagePoolLookupByName(pool_name)
                if not _pool.isActive() :
                    _pool.create(0)
                result["poolcapacity" + str(_idx)] = str(_pool.storageVolLookupByName(imageids[_idx]).info()[1])
            
            except libvirtError, msg:
                self.ftcraise(lvt_cnt.host, 2, "Problem looking up pool information: " + str(msg))
                
        _xml_templates = self.get_libvirt_vm_templates(_num_ids, disk_format, qemu_debug_port)

        _tmplt_find = []
        _tmplt_replace = []

        _tmplt_find.append(compile("TMPLT_LIBVIRTID", MULTILINE))
        _tmplt_replace.append(tag)

        for _idx in range(0, _num_ids) :
            _tmplt_find.append(compile("TMPLT_POOLBASE" + str(_idx), MULTILINE))
            _tmplt_replace.append(result["poolbase" + str(_idx)])
            _tmplt_find.append(compile("TMPLT_BASE" + str(_idx), MULTILINE))
            _tmplt_replace.append(imageids[_idx])
            _tmplt_find.append(compile("TMPLT_CAPACITY" + str(_idx), MULTILINE))
            _tmplt_replace.append(result["poolcapacity" + str(_idx)])

        _tmplt_find.append(compile("TMPLT_MEMORY", MULTILINE))
        _tmplt_replace.append(str(int(result["vmemory"]) * 1024))
        _tmplt_find.append(compile("TMPLT_VCPUS", MULTILINE))
        _tmplt_replace.append(result["vcpus"])
        _tmplt_find.append(compile("TMPLT_MACADDRESS", MULTILINE))
        _tmplt_replace.append(result["cloud_mac"])
        _tmplt_find.append(compile("TMPLT_VMC_HOSTNAME", MULTILINE))
        _tmplt_replace.append(hypervisor_ip)

        cbdebug("Going to change newly created libvirt configuration templates...")
        
        for _template_name in _xml_templates.keys() :
            _f_c = _xml_templates[_template_name]

            for _idx in range (0, len(_tmplt_replace)) :
                _f_c = _tmplt_find[_idx].sub(_tmplt_replace[_idx], _f_c)
            _xml_templates[_template_name] = _f_c
        
        cbdebug("libvirt configuration files successfully altered.")
        
        for _idx in range(0, _num_ids) :
            try : 
                lvt_cnt.storagePoolLookupByName("ftc-snapshots" + ("-lvm" if disk_format == "lvm" else "")).createXML(_xml_templates["disk_template" +  str(_idx)], 0)
            except libvirtError, msg:
                self.ftcraise(lvt_cnt.host, 2, "Snapshot creation failed: " + str(msg))
                
            cbdebug("Volume snapshot #" + str(_idx) + " created for VM " + tag)

        _imsg = tag + " domain on libvirt host " + lvt_cnt.host
        _smsg = _imsg + " was successfully created."
        _fmsg = _imsg + " could not be created: "
        
        try :
            print _xml_templates["vm_template"]
            _dom = lvt_cnt.defineXML(_xml_templates["vm_template"])
            
            _dom.create()
            
            result["display_port"], result["display_protocol"] = self.get_display_ports(lvt_cnt, _dom)
        except libvirtError, msg: 
            if disk_format == "lvm" :
                try :
                    for _idx in range(0, _num_ids) :
                        self.snapshot_volume_destroy(lvt_cnt, tag, imageids[_idx], disk_format)
                    _dom.undefine()
                except :
                    pass
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
        
        cbdebug(_smsg)

        return self.success(tag + " was successfully created on cloud " + options.cloud_name, result)

    @trace        
    def destroy_instances(self, storage_keys, tag, hypervisor_ip, disk_format = None) :
        lvt_cnt = self.conn_check(hypervisor_ip)
        _graceful = False
        self.destroy_and_undefine_domain(lvt_cnt, tag, _graceful)
        for key in storage_keys :
            self.snapshot_volume_destroy(lvt_cnt, tag, key, disk_format)

        _msg = tag + " successfully destroyed on cloud " + options.cloud_name 
        return self.success(_msg, None)

    @trace
    def list_domains(self, lvt_cnt, all_domains, gfilter) :
        _domains = {}
        _imsg = "Domain list for libvirt host " + lvt_cnt.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            if all_domains :
                for _tag in lvt_cnt.listDefinedDomains() :
                    if gfilter is not None :
                        if not _tag.count(gfilter) :
                            continue
                    _dom = lvt_cnt.lookupByName(_tag)
                    _domains[_dom.name()] = _dom
            else :
                for _dom_id in lvt_cnt.listDomainsID() :
                    _dom = lvt_cnt.lookupByID(_dom_id)
                    if gfilter is not None :
                        if not _dom.name().count(gfilter) :
                            continue
                    _domains[_dom.name()] = _dom
        except libvirtError, msg : 
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
            
        cbdebug(_smsg)
        return _domains
    
    @trace
    def ft_status(self, tag, primary_host_cloud_ip, hypervisor_ip) :
        lvt_cnt = self.conn_check(primary_host_cloud_ip)
        _imsg = "Replication performance for VM " + tag + " on libvirt host " + lvt_cnt.host
        _smsg = _imsg + " "
        _fmsg = _imsg + " could not be retrieved: "
        
        try :
            _dom = lvt_cnt.lookupByName(tag)
            return self.success("qemu result", qemuMonitorCommand(_dom, 'info migrate', 1))
        except libvirtError, msg: 
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
        
    @trace
    def ft_stop(self, tag, primary_host_cloud_ip, hypervisor_ip) :
        lvt_cnt = self.conn_check(primary_host_cloud_ip)
        _imsg = "Replication for " + tag + " domain on libvirt host " + lvt_cnt.host
        _smsg = _imsg + " has stopped. "
        _fmsg = _imsg + " could not be stopped: "
        
        try :
            _dom = lvt_cnt.lookupByName(tag)
            qemuMonitorCommand(_dom, 'migrate_cancel', 1)
            sleep(5)
            _dom.resume()
        except libvirtError, msg: 
            return self.error(2, _fmsg + str(msg), None)
        return self.success(_smsg, True)
        
    @trace    
    def get_domain_full_info(self, tag, hypervisor_ip) :
        lvt_cnt = self.conn_check(hypervisor_ip)

        _imsg = tag + " domain information libvirt host " + lvt_cnt.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        _dom_info = {}
        
        _dom_info["os_type"] = "NA"
        _dom_info["scheduler_type"] = "NA"
        _dom_info["uuid"] = "NA"
        _dom_info["max_memory"] = "NA"
        _dom_info["current_memory"] = "NA"        
        _dom_info["vcpus_period"] = "NA"
        _dom_info["vcpus_quota"] = "NA"        
        _dom_info["vcpus_hard_limit"] = "NA"
        _dom_info["mem_hard_limit"] = "NA"
        _dom_info["mem_hard_limit"] = "NA"
        _dom_info["mem_swap_hard_limit"] = "NA"
        _dom_info["diskio_soft_limit"] = "NA" 

        try :
            _dom = lvt_cnt.lookupByName(tag)

            _dom_info["os_type"] = _dom.OSType()
            _dom_info["scheduler_type"] = _dom.schedulerType()[0]
            _dom_info["uuid"] = _dom.UUIDString()

            _g_dom_info = _dom.info()

            _vcpu_info = _dom.vcpus()
            
            _dom_info["vcpus"] = str(_g_dom_info[3])
            for _vcpu_nr in range(0, int(_dom_info["vcpus"])) :
                _dom_info["vcpu_" + str(_vcpu_nr) + "_pcpu"] = str(_vcpu_info[0][_vcpu_nr][3])
                _dom_info["vcpu_" + str(_vcpu_nr) + "_time"] =  str(_vcpu_info[0][_vcpu_nr][2])
                _dom_info["vcpu_" + str(_vcpu_nr) + "_state"] =  str(_vcpu_info[0][_vcpu_nr][1])
                _dom_info["vcpu_" + str(_vcpu_nr) + "_map"] = str(_vcpu_info[1][_vcpu_nr])
            
            _dom_info["max_memory"] = str(_g_dom_info[1])
            _dom_info["current_memory"] = str(_g_dom_info[2])
            
            _dom = lvt_cnt.lookupByName(tag)
            _sched_info = _dom.schedulerParameters()
            
            _dom_info["vcpus_soft_limit"] = str(_sched_info["cpu_shares"])
            
            if "vcpu_period" in _sched_info :
                _dom_info["vcpus_period"] = str(float(_sched_info["vcpu_period"]))
                _dom_info["vcpus_quota"] = str(float(_sched_info["vcpu_quota"]))
                _dom_info["vcpus_hard_limit"] = str(float(_dom_info["vcpus_quota"]) / float(_dom_info["vcpus_period"]))

            # For Libvirt version < 0.9.4, comment out the following lines
            #_mem_info = _dom.memoryParameters(0)

            #_dom_info["mem_hard_limit"] = int(_mem_info["hard_limit"])
            #_dom_info["mem_hard_limit"] = int(_mem_info["soft_limit"])
            #_dom_info["mem_swap_hard_limit"] = int(_mem_info["swap_hard_limit"])
            
            #_diskio_info = _dom.blkioParameters(0)
            
            #_dom_info["diskio_soft_limit"] = _diskio_info["weight"]
            
            #tree = ElementTree.fromstring(_dom.XMLDesc(0))
  
            #_dom_info["virtual_volumes"] = []

#            for target in tree.findall("devices/disk/target"):
#                _volume_name = target.get("dev")
#                if not _volume_name in _dom_info["virtual_volumes"]:
#                    _dom_info["virtual_volumes"].append(_volume_name)
            
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))
            
        return self.success(_smsg, _dom_info)

    @trace
    def statically_balance_vcpu_domains(self, hypervisor_ip) :
        lvt_cnt = self.conn_check(hypervisor_ip)
        try :
            pcpu_nr  = int(lvt_cnt.getInfo()[2])
        except libvirtError, msg : 
            self.ftcraise(lvt_cnt.host, 3, "Couldn't determine number of cores: " + str(msg))
                
        try :
            _max_pcpu_nr = pcpu_nr - 1
            _curr_pcpu_nr = 0
            _pcpu_pin_list = [False] * pcpu_nr
            _tag = "None"
            for _tag in self.list_domains(lvt_cnt, False, None).keys() :
                _vcpu_count = int(self.get_domain_full_info(_tag, hypervisor_ip)[2]["vcpus"])
                _dom = lvt_cnt.lookupByName(_tag)
                
                for _vcpu in range(0, _vcpu_count) :
                    _msg = " - Pinning " + _tag + "'s vcpu " + str(_vcpu)
                    _msg += " to pCPU " + str(_curr_pcpu_nr)
                    cbdebug(_msg)
                    _pcpu_pin_list[_curr_pcpu_nr] = True
                    _dom.pinVcpu(_vcpu, tuple(_pcpu_pin_list))
                    _pcpu_pin_list = [False] * pcpu_nr            

                    if _curr_pcpu_nr < _max_pcpu_nr :
                        _curr_pcpu_nr += 1
                    else :
                        _curr_pcpu_nr = 0
        except libvirtError, msg :
            _msg = " - Libvirt error while accessing domain "
            _msg += _tag + " on " + lvt_cnt.host + ": " + str(msg)
            cberr(_msg)
            self.ftcraise(lvt_cnt.host, 2, _msg)
        
        except self.LibvirtMgdConnException, obj :
            self.ftcraise(lvt_cnt.host, 3, obj.msg)
            
        return self.success(_msg, True)
 
    @trace    
    def set_domain_memory(self, tag, mem_param, value, hypervisor_ip) :
        value = int(value)
        lvt_cnt = self.conn_check(hypervisor_ip)
        try :
            _dom = lvt_cnt.lookupByName(tag)
            tries = 10
            while True and tries > 0:
                _dom.setMemory(value)
                sleep(10)
                current = int(_dom.info()[2])
                if current != value :
                    cbdebug("Balloon not reached yet: " + str(current) + ", " + str(value) + "...", True)
                else :
                    cbdebug("Balloons are equal: " + str(current) + " " + str(value))
                    break
                tries -= 1
               
            if tries == 0 :
                self.ftcraise(lvt_cnt.host, 4, "Failed to resize memory for domain - ran out of tries. Made it to : " + str(current) + " while trying to reach " + str(value))
                      
            _msg = " - Successfully set the memory parameter for the "
            _msg += "domain " + tag + " running on the host "
            _msg += lvt_cnt.host
        except libvirtError, msg : 
            _msg = " - Unable to set the memory parameter for the "
            _msg += "domain " + tag + " on "
            _msg += lvt_cnt.host + str(msg)
            self.ftcraise(lvt_cnt.host, 2, _msg)
        
        return self.success(_msg, True)

    @trace
    def set_domain_diskio(self, tag, diskio_param, value, hypervisor_ip) :
        lvt_cnt = self.conn_check(hypervisor_ip)
        _diskio_param = {}
            
        try :
            _dom = lvt_cnt.lookupByName(tag)
            _diskio_param[diskio_param] = value
            _dom.setBlkioParameters(_diskio_param,0)
            _msg = " - Successfully set the " + diskio_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvt_cnt.host
            cbdebug(_msg)
        except libvirtError, msg : 
            _msg = " - Unable to set the " + diskio_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvt_cnt.host + ": " + str(msg)
            self.ftcraise(lvt_cnt.host, 2, _msg)
        return self.success(_msg, True)
    
    @trace
    def set_domain_cpu(self, tag, cpu_param, value, hypervisor_ip) :
        value = int(value)
        lvt_cnt = self.conn_check(hypervisor_ip)
        _cpu_param = {}
        
        try :
            _dom = lvt_cnt.lookupByName(tag)
            _cpu_param[cpu_param] = value
            _dom.setSchedulerParameters(_cpu_param)
            _msg = "Successfully set the " + cpu_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvt_cnt.host
            cbdebug(_msg)
        except libvirtError, msg : 
            _msg = "Unable to set the " + cpu_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvt_cnt.host + ": " + str(msg)
            self.ftcraise(lvt_cnt.host, 2, _msg)
            
        return self.success(_msg, True)

    @trace
    def is_domain_active(self, tag, hypervisor_ip) :
        lvt_cnt = self.conn_check(hypervisor_ip)
        result = False
        _msg = "Going to check if domain \"" + tag + "\" is defined..."
        cbdebug(_msg)
        
        try :
            _dom = lvt_cnt.lookupByName(tag)
            if _dom.isActive() :
                _msg = " \"" + tag + "\" is running.... continuing"
                result = True
            else :
                _msg = " \"" + tag + "\" is not running.... continuing"

        except libvirtError:
            _msg = " \"" + tag + "\" is not defined... continuing"
            cbdebug(_msg)
            
        return self.success(_msg, result)

    @trace
    def destroy_and_undefine_domain(self, lvt_cnt, tag, graceful = True) :
        _imsg = tag + " domain libvirt host " + lvt_cnt.host
        _smsg = _imsg + " was successfully destroyed and undefined."
        _fmsg = _imsg + " could not be destroyed and undefined: "
        _dom = None
        
        try :
            _msg = "Going to check if domain \"" + tag + "\" is defined..."
            cbdebug(_msg)
            _dom = lvt_cnt.lookupByName(tag)
        
        except libvirtError, msg:
            _msg = _smsg + " (Domain not defined)"
            cbdebug(_msg)
            return True
        
        _op_tries = 5

        while _op_tries > 0 :
            _op_tries -= 1

            try :
                if _dom.isActive() :
                    # In order to provide some filesystem sanity to virtual machines,
                    # try to shut them down first instead of just destroying them
                    tries = 40 
                    _msg = "Waiting for domain " +tag 
                    _msg += " to be shutdown first."
                    cbdebug(_msg)
                    
                    while tries > 0 :
                        tries -= 1
                        if _dom.isActive() :
                            if graceful :
                                _dom.shutdown()
                                _msg = "(" + str(tries) + " chances left). " 
                                _msg += "Domain id " + _dom.name() + " still "
                                _msg += "alive..."
                                cbdebug(_msg)
                                sleep(10)
                            else :
                                _dom.destroy()
                                _msg = "Domain id " + _dom.name() + " destroyed"
                        else :
                            _msg = "Domain id "  +  _dom.name() + " shutdown "
                            _msg += "successfully."
                            cbdebug(_msg)
                            break

                    if _dom.isActive() :
                        _msg = "Domain id " + _dom.name() + " failed to "
                        _msg += "shutdown cleanly."
                        _msg += " Will have to destroy it."
                        cbdebug(_msg)
                        _dom.destroy()

                # After destruction or shutdown, we lose the object for some
                # reason, so we have to lookup again
                _msg = "Going to undefine " +tag 
                cbdebug(_msg)
                _dom = lvt_cnt.lookupByName(tag)
                
                if options.hypervisor == "kvm" and _dom.hasManagedSaveImage(0) :
                    cbdebug("Domain " + tag + " has managed save state. Clearing...")
                    _dom.managedSaveRemove(0)
                
                _dom.undefine()

                cbdebug(_smsg)
                break

            except libvirtError, msg : 
                _retry_destroy_secs = 30
                _msg = _fmsg + str(msg)
                cberr(_msg)
                if _op_tries > 0 :
                    _msg = "Oops. Going to try destroy again in " + str(_retry_destroy_secs) + " secs..."
                    cbdebug(_msg, True)
                    sleep(_retry_destroy_secs)
                    self.lvt_cnt[lvt_cnt.host] = False
                    

        if _op_tries < 0 :
            _msg = _fmsg + "Ran out of tries. Failure is permanent."
            self.ftcraise(lvt_cnt.host, 2, _msg)
        else :
            return True

    @trace
    def activate_pool_if_inactive(self, lvt_cnt, pool) :
        pool.setAutostart(1)
        
        if not pool.isActive() :
            try :
                pool.build()
            except :
                True
            pool.create(0)

    @trace
    def save(self, tag, hypervisor_ip):
        lvt_cnt = self.conn_check(hypervisor_ip)
        _imsg =  "Domain " + tag 
        _smsg = _imsg + " was successfully saved."
        _fmsg = _imsg + " could not be saved: "
        try :
            dom = lvt_cnt.lookupByName(tag)
            cbdebug("Issuing Managed Save on VM " + tag + "...")
            dom.managedSave(0)
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 3, _fmsg + str(msg))
        return self.success(_smsg, None)
    
    @trace
    def migrate(self, tag, hypervisor_ip, destination_ip, protocol, interface, operation):
        lvt_cnt = self.conn_check(hypervisor_ip)
        _imsg =  "Domain " + tag 
        _smsg = _imsg + " was successfully " + operation + "ed."
        _fmsg = _imsg + " could not be saved: "
        try :
            if options.hypervisor in [ "xen", "pv" ] :
                uri = "xen+tcp://" + destination_ip
            elif options.hypervisor == "kvm" :
                uri = "qemu+tcp://" + destination_ip + "/system"
            dom = lvt_cnt.lookupByName(tag)
            miguri = protocol + ":" + interface 
            cbdebug("Opening connection to destination uri: " + uri)
            dconn = open(uri)
            cbdebug("Issuing " + operation + " on VM " + tag + " to " + uri + " with interface " + miguri + "...")
            dom.migrate(dconn, VIR_MIGRATE_LIVE | VIR_MIGRATE_PERSIST_DEST | VIR_MIGRATE_UNDEFINE_SOURCE, None, miguri, 0)
            dconn.close()
        except libvirtError, msg :
            _msg = str(msg).replace("migration", operation)
            self.ftcraise(lvt_cnt.host, 3, _fmsg + msg)
        return self.success(_smsg, None)
    
    @trace
    def restore(self, tag, hypervisor_ip, savefile = None) :
        lvt_cnt = self.conn_check(hypervisor_ip)
        _imsg =  "Domain " + tag 
        _smsg = _imsg + " was successfully restored."
        _fmsg = _imsg + " could not be restored: "
        result = {}
        try :
            cbdebug("Issuing Restore on VM " + tag + "...")
            dom = lvt_cnt.lookupByName(tag)
            if dom.hasManagedSaveImage(0) :
                dom.create()
            else :
                if savefile is None :
                    self.ftcraise(lvt_cnt.host, 7, "Must specify restore file " + \
                        "name for non-managed save domain: " + tag)
                    
                dom.restore(savefile)
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 4, _fmsg + str(msg))
            
        result["display_port"], result["display_protocol"] = self.get_display_ports(lvt_cnt, dom)
        
        return self.success(_smsg, result)
    
    @trace
    def suspend(self, tag, hypervisor_ip):
        lvt_cnt = self.conn_check(hypervisor_ip)
        _imsg =  "Domain " +tag 
        _smsg = _imsg + " was successfully suspended."
        _fmsg = _imsg + " could not be suspended: "
        try :
            dom = lvt_cnt.lookupByName(tag)
            cbdebug("Suspending VM " + tag + "...")
            dom.suspend()
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 5, _fmsg + str(msg))
            
        return self.success(_smsg, None)
    
    @trace
    def resume(self, tag, hypervisor_ip):
        lvt_cnt = self.conn_check(hypervisor_ip)
        _imsg =  "Domain " +tag 
        _smsg = _imsg + " was successfully resumed."
        _fmsg = _imsg + " could not be resumed: "
        try :
            dom = lvt_cnt.lookupByName(tag)
            cbdebug("Resuming VM " + tag + "...")
            dom.resume()
        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 6, _fmsg + str(msg))
        return self.success(_smsg, None)

    @trace
    def snapshot_volume_destroy(self, lvt_cnt, gfilter = None, vol_name = None, disk_format = None) :
        _imsg =  "old snapshots on " + lvt_cnt.host
        _smsg = _imsg + " were successfully destroyed."
        _fmsg = _imsg + " could not be destroyed: "
        
        try :
            _pool = lvt_cnt.storagePoolLookupByName("ftc-snapshots" + ("-lvm" if disk_format == "lvm" else ""))
            self.activate_pool_if_inactive(lvt_cnt, _pool)
            if vol_name and not gfilter:
                count = 1
                # used during steady-state
                _pool.storageVolLookupByName(vol_name).delete(0)
            else :
                count = 0
                # Used by vmccleanup()
                _volumes = _pool.listVolumes()
                for _volname in _volumes :
                    if (gfilter and not _volname.count(gfilter)) or (vol_name and not _volname.count(vol_name)):
                        continue
                    v = _pool.storageVolLookupByName(_volname)
                    '''
                    deleting LVM volums in linux is broken.
                    Deal with it later.... 
                    '''
                    try : 
                        v.delete(0)
                    except libvirtError, msg :
                        if disk_format == "lvm":
                            pass
                        else :
                            self.ftcraise(lvt_cnt.host, 3, _fmsg + str(msg))
                    count += 1
                    
            cbdebug(str(count) + " " + _smsg, True)

        except libvirtError, msg :
            self.ftcraise(lvt_cnt.host, 2, _fmsg + str(msg))

    @trace
    def get_signature(self, name):
        return self.success("signature", self.signatures[name])

class AsyncDocXMLRPCServer(SocketServer.ThreadingMixIn,DocXMLRPCServer): pass

class FTCService ( threading.Thread ):
    @trace
    def __init__(self, port, hypervisors, dhcp_omapi_server, dhcp_omapi_port, debug) :
        super(FTCService, self).__init__()
        self._stop = threading.Event()
        self.pid = ""
        self.port = port
        self.dhcp_omapi_server = dhcp_omapi_server
        self.dhcp_omapi_port = int(dhcp_omapi_port)
        self.dhcp_omap_pkey = "d+y8yPwtC0nJ0C0uRC5cxYREYGPBkJwhJYjHbb1LkoW0FF6gYr3SiVi6 HRQUcl4Y7gdzwvi0hgPV+Gdy1wX9vg==" 
        self.dhcp_omap_keyn = "omapi_key"
        self.ftc = Ftc(hypervisors)
        cbdebug("Initializing API Service on port " + str(self.port))
        if debug is None :
            self.server = AsyncDocXMLRPCServer(("0.0.0.0", int(self.port)), allow_none = True)
        else :
            self.server = DocXMLRPCServer(("0.0.0.0", int(self.port)), allow_none = True)
        self.server.set_server_title(options.cloud_name + ": Thin Agile Cloud Service (FTC xmlrpc)")
        self.server.set_server_name(options.cloud_name + ": Thin Agile Cloud Service (FTC xmlrpc)")
        self.ftc.signatures = {}
        for methodtuple in inspect.getmembers(self.ftc, predicate=inspect.ismethod) :
            name = methodtuple[0]
            func = getattr(self.ftc, name)
            argspec = inspect.getargspec(func) 
            spec = argspec[0]
            defaults = [] if argspec[3] is None else argspec[3]
            self.ftc.signatures[name] = spec[1:] # ignore 'self'
            #setattr(self.ftc, name, self.ftc.unwrap_kwargs(func))
            #self.server.register_function(func, name)
            if "lvt_cnt" not in spec and len(spec) > 1 and \
                name not in ["__init__", "conn_check", "error", "success", "global_error", "ftcraise", "get_libvirt_vm_templates", "get_display_ports"]:
                num_spec = len(spec)
                num_defaults = len(defaults)
                diff = num_spec - num_defaults
                doc = "Usage: "
                for x in range(1, diff) :
                    doc += spec[x] + ", "
                for x in range(diff, num_spec) :
                    doc += spec[x] + " = " + str(defaults[x - diff]) + ", "
                doc = doc[:-2]
                    
                self.server.register_function(unwrap_kwargs(func, doc), name)
            
#        self.server.register_introspection_functions()
        cbdebug("FTC Service started")
        
    @trace
    def run(self):
        cbdebug("FTC Service waiting for requests...")
        self.server.serve_forever()
        cbdebug("FTC Service shutting down...")
        
    @trace
    def stop (self) :
        cbdebug("Calling FTC Service shutdown....")
        self._stop.set()
        self.server.shutdown()

@trace
def wait_for_port_ready(hostname, port) :
    '''
    TBD
    '''
    while True :
        try:
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
            s.bind((hostname, int(port)))
            s.close()
            break
        except socket.error, (value, message) :
            if value == 98 : 
                cbwarn("Previous port " + str(port) + " still shutting down! Trying again later...")
                sleep(30)
                continue
            else :
                cberr("Could not test port " + str(port) + " liveness: " +  message)
                raise
        
@trace
def main(options) :
    try :
        ftcservice = None
        _status = 100
        _fmsg = "Unknown Error"
        _verbosity = int(options.verbosity)

        logger = getLogger('')
        hdlr = SysLogHandler(address = (options.loghost, int(options.logport)), \
                                        facility=SysLogHandler.LOG_LOCAL0)

        formatter = Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.addHandler(StreamHandler(stdout))

        if _verbosity :
            if int(_verbosity) >= 2 :
                logger.setLevel(DEBUG)
            elif int(_verbosity) == 1 :
                # Used to filter out all function calls from the "auxiliary"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("auxiliary"))
                # Used to filter out all function calls from the "remote"
                # subdirectory.
                hdlr.addFilter(VerbosityFilter("remote"))
                logger.setLevel(DEBUG)
        else :
            logger.setLevel(INFO)

        if options.quiet :
            logger.setLevel(ERROR)

        wait_for_port_ready("0.0.0.0", options.port)
        ftcservice = FTCService(options.port, options.hypervisors, options.dhcp_omapi_server, options.dhcp_omapi_port, options.debug_host)
        if options.debug_host is None :
            ftcservice.start()
        else :
            ftcservice.run()

        while True :
            sleep(10)

        _status = 0
    except KeyboardInterrupt :
        _status = 0
        cbdebug("CTRL-C exiting...")

    except Exception, e :
        _status = 23
        _fmsg = str(e)

    finally :
        if ftcservice is not None :
            ftcservice.stop()
            ftcservice.join()

        if _status :
            cberr("FTC failure: " + _fmsg)
            exit(2)
        else :
            cbdebug("FTC exiting.")
            os.kill(os.getpid(), signal.SIGKILL)

def repr_opcode(opcode):
    """
    @type opcode: int
    @rtype: str
    """
    opmap = {1: "open", 2: "refresh", 3: "update", 4: "notify", 5: "status",
            6: "delete"}
    return opmap.get(opcode, "unknown")

__all__.append("OmapiError")
class OmapiError(Exception):
    """OMAPI exception base class."""

__all__.append("OmapiSizeLimitError")
class OmapiSizeLimitError(OmapiError):
    """Packet size limit reached."""
    def __init__(self):
        OmapiError.__init__(self, "Packet size limit reached.")

__all__.append("OmapiErrorNotFound")
class OmapiErrorNotFound(OmapiError):
    """Not found."""
    def __init__(self):
        OmapiError.__init__(self, "not found")

class OutBuffer:
    """Helper class for constructing network packets."""
    sizelimit = 65536
    def __init__(self):
        self.buff = StringIO()

    def add(self, data):
        """
        @type data: str
        @returns: self
        @raises OmapiSizeLimitError:
        """
        self.buff.write(data)
        if self.buff.tell() > self.sizelimit:
            raise OmapiSizeLimitError()
        return self

    def add_net32int(self, integer):
        """
        @type integer: int
        @param integer: a 32bit unsigned integer
        @returns: self
        @raises OmapiSizeLimitError:
        """
        if integer < 0 or integer >= (1 << 32):
            raise ValueError("not a 32bit unsigned integer")
        return self.add(struct.pack("!L", integer))

    def add_net16int(self, integer):
        """
        @type integer: int
        @param integer: a 16bit unsigned integer
        @returns: self
        @raises OmapiSizeLimitError:
        """
        if integer < 0 or integer >= (1 << 16):
            raise ValueError("not a 16bit unsigned integer")
        return self.add(struct.pack("!H", integer))

    def add_net32string(self, string):
        """
        @type string: str
        @param string: maximum length must fit in a 32bit integer
        @returns: self
        @raises OmapiSizeLimitError:
        """
        if len(string) >= (1 << 32):
            raise ValueError("string too long")
        return self.add_net32int(len(string)).add(string)

    def add_net16string(self, string):
        """
        @type string: str
        @param string: maximum length must fit in a 16bit integer
        @returns: self
        @raises OmapiSizeLimitError:
        """
        if len(string) >= (1 << 16):
            raise ValueError("string too long")
        return self.add_net16int(len(string)).add(string)

    def add_bindict(self, items):
        """
        >>> OutBuffer().add_bindict(dict(foo="bar")).getvalue()
        '\\x00\\x03foo\\x00\\x00\\x00\\x03bar\\x00\\x00'

        @type items: [(str, str)] or {str: str}
        @returns: self
        @raises OmapiSizeLimitError:
        """
        if not isinstance(items, list):
            items = items.items()
        for key, value in items:
            self.add_net16string(key).add_net32string(value)
        return self.add("\x00\x00") # end marker

    def getvalue(self):
        """
        @rtype: str
        """
        return self.buff.getvalue()

    def consume(self, length):
        """
        @type length: int
        @returns: self
        """
        self.buff = StringIO(self.getvalue()[length:])
        return self

class OmapiAuthenticatorBase:
    """Base class for OMAPI authenticators."""
    authlen = -1 # must be overwritten
    algorithm = None
    authid = -1 # will be an instance attribute
    def __init__(self):
        pass
    def auth_object(self):
        """
        @rtype: {str: str}
        @returns: object part of an omapi authentication message
        """
        raise NotImplementedError
    def sign(self, message):
        """
        @type message: str
        @rtype: str
        @returns: a signature of length self.authlen
        """
        raise NotImplementedError()

class OmapiNullAuthenticator(OmapiAuthenticatorBase):
    authlen = 0
    authid = 0 # always 0
    def __init__(self):
        OmapiAuthenticatorBase.__init__(self)
    def auth_object(self):
        return {}
    def sign(self, _):
        return ""

class OmapiHMACMD5Authenticator(OmapiAuthenticatorBase):
    authlen = 16
    algorithm = "hmac-md5.SIG-ALG.REG.INT."
    def __init__(self, user, key):
        """
        @type user: str
        @type key: str
        @param key: base64 encoded key
        @raises binascii.Error: for bad base64 encoding
        """
        OmapiAuthenticatorBase.__init__(self)
        self.user = user
        self.key = key.decode("base64")

    def auth_object(self):
        return dict(name=self.user, algorithm=self.algorithm)

    def sign(self, message):
        return hmac.HMAC(self.key, message).digest()

OMAPI_OP_OPEN    = 1
OMAPI_OP_REFRESH = 2
OMAPI_OP_UPDATE  = 3
OMAPI_OP_NOTIFY  = 4
OMAPI_OP_STATUS  = 5
OMAPI_OP_DELETE  = 6

class OmapiMessage:
    def __init__(self):
        self.authid = 0
        self.opcode = 0
        self.handle = 0
        self.tid = 0
        self.rid = 0
        self.message = []
        self.obj = []
        self.signature = ""

    def generate_tid(self):
        """Generate a random transmission id for this OMAPI message."""
        self.tid = sysrand.randrange(0, 1<<32)

    def as_string(self, forsigning=False):
        """
        @type forsigning: bool
        @rtype: str
        @raises OmapiSizeLimitError:
        """
        ret = OutBuffer()
        if not forsigning:
            ret.add_net32int(self.authid)
        ret.add_net32int(len(self.signature))
        ret.add_net32int(self.opcode)
        ret.add_net32int(self.handle)
        ret.add_net32int(self.tid)
        ret.add_net32int(self.rid)
        ret.add_bindict(self.message)
        ret.add_bindict(self.obj)
        if not forsigning:
            ret.add(self.signature)
        return ret.getvalue()

    def sign(self, authenticator):
        """Sign this OMAPI message.
        @type authenticator: OmapiAuthenticatorBase
        """
        self.authid = authenticator.authid
        self.signature = "\0" * authenticator.authlen # provide authlen
        self.signature = authenticator.sign(self.as_string(forsigning=True))
        assert len(self.signature) == authenticator.authlen

    @classmethod
    def from_fields(cls, authid, opcode, handle, tid, rid, message, obj,
            signature):
        self = cls()
        self.authid, self.opcode = authid, opcode
        self.handle, self.tid, self.rid = handle, tid, rid
        self.message, self.obj, self.signature = message, obj, signature
        return self

    def verify(self, authenticators):
        """Verify this OMAPI message.
        @type authenticators: {int: OmapiAuthenticatorBase}
        @rtype: bool
        """
        try:
            return authenticators[self.authid]. \
                    sign(self.as_string(forsigning=True)) == \
                    self.signature
        except KeyError:
            return False

    @classmethod
    def open(cls, typename):
        """Create an OMAPI open message with given typename.
        @type typename: str
        @rtype: OmapiMessage
        """
        self = cls()
        self.opcode = OMAPI_OP_OPEN
        self.message.append(("type", typename))
        self.generate_tid()
        return self

    @classmethod
    def delete(cls, handle):
        """Create an OMAPI delete message for given handle.
        @type handle: int
        @rtype: OmapiMessage
        """
        self = cls()
        self.opcode = OMAPI_OP_DELETE
        self.handle = handle
        self.generate_tid()
        return self

    def is_response(self, other):
        """Check whether this OMAPI message is a response to the given
        OMAPI message.
        @rtype: bool
        """
        return self.rid == other.tid

    def update_object(self, update):
        """
        @type update: {str: str}
        """
        self.obj = [(key, value) for key, value in self.obj
                    if key not in update]
        self.obj.extend(update.items())

    def dump(self):
        print "Omapi message attributes:"
        print "authid:\t\t%d" % self.authid
        print "authlen:\t%d" % len(self.signature)
        print "opcode:\t\t%s" % repr_opcode(self.opcode)
        print "handle:\t\t%d" % self.handle
        print "tid:\t\t%d" % self.tid
        print "rid:\t\t%d" % self.rid
        print "message:\t%r" % self.message
        print "obj:\t\t%r" % self.obj
        print "signature:\t%r" % self.signature

def parse_map(filterfun, parser):
    """
    @type filterfun: obj -> obj
    @param parser: parser
    @returns: parser
    """
    for element in parser:
        if element is None:
            yield None
        else:
            yield filterfun(element)
            break

def parse_chain(*args):
    """
    @param args: parsers
    @returns: parser
    """
    items = []
    for parser in args:
        for element in parser(*items):
            if element is None:
                yield None
            else:
                items.append(element)
                break
    yield tuple(items)

class InBuffer:
    sizelimit = 65536
    def __init__(self):
        self.buff = ""
        self.totalsize = 0
        self.parsing = None

    def feed(self, data):
        """
        @type data: str
        @raises OmapiSizeLimitError:
        """
        self.buff += data
        self.totalsize += len(data)
        if self.totalsize > self.sizelimit:
            raise OmapiSizeLimitError()

    def resetsize(self):
        """This method is to be called after handling a packet to
        reset the total size to be parsed at once and that way not
        overflow the size limit.
        """
        self.totalsize = len(self.buff)

    def parse_fixedbuffer(self, length):
        """
        @type length: int
        """
        while len(self.buff) < length:
            yield None
        result = self.buff[:length]
        self.buff = self.buff[length:]
        yield result

    def parse_net16int(self):
        return parse_map(lambda data: struct.unpack("!H", data)[0],
                self.parse_fixedbuffer(2))

    def parse_net32int(self):
        return parse_map(lambda data: struct.unpack("!L", data)[0],
                self.parse_fixedbuffer(4))

    def parse_net16string(self):
        return parse_map(operator.itemgetter(1),
                parse_chain(self.parse_net16int, self.parse_fixedbuffer))

    def parse_net32string(self):
        return parse_map(operator.itemgetter(1),
                parse_chain(self.parse_net32int, self.parse_fixedbuffer))

    def parse_bindict(self):
        entries = []
        try:
            while True:
                key = None
                for key in self.parse_net16string():
                    if key is None:
                        yield None
                    elif not key:
                        raise StopIteration()
                    else:
                        break
                assert key is not None
                value = None
                for value in self.parse_net32string():
                    if value is None:
                        yield None
                    else:
                        break
                assert value is not None
                entries.append((key, value))
        # Abusing StopIteration here, since nothing should be throwing
        # it at us.
        except StopIteration:
            yield entries

    def parse_startup_message(self):
        # results in (version, headersize)
        return parse_chain(self.parse_net32int, lambda _: self.parse_net32int())

    def parse_message(self):
        parser = parse_chain(self.parse_net32int, # authid
                lambda *_: self.parse_net32int(), # authlen
                lambda *_: self.parse_net32int(), # opcode
                lambda *_: self.parse_net32int(), # handle
                lambda *_: self.parse_net32int(), # tid
                lambda *_: self.parse_net32int(), # rid
                lambda *_: self.parse_bindict(), # message
                lambda *_: self.parse_bindict(), # object
                lambda *args: self.parse_fixedbuffer(args[1])) # signature
        return parse_map(lambda args: # skip authlen in args:
                OmapiMessage.from_fields(*(args[0:1] + args[2:])), parser)

def pack_ip(ipstr):
    """Converts an ip address given in dotted notation to a four byte
    string in network byte order.

    >>> len(pack_ip("127.0.0.1"))
    4
    >>> pack_ip("foo")
    Traceback (most recent call last):
    ...
    ValueError: given ip address has an invalid number of dots

    @type ipstr: str
    @rtype: str
    @raises ValueError: for badly formatted ip addresses
    """
    if not isinstance(ipstr, str):
        raise ValueError("given ip address is not a string")
    parts = ipstr.split('.')
    if len(parts) != 4:
        raise ValueError("given ip address has an invalid number of dots")
    parts = map(int, parts) # raises ValueError
    parts = map(chr, parts) # raises ValueError
    return "".join(parts) # network byte order

def unpack_ip(fourbytes):
    """Converts an ip address given in a four byte string in network
    byte order to a string in dotted notation.

    >>> unpack_ip("dead")
    '100.101.97.100'
    >>> unpack_ip("alive")
    Traceback (most recent call last):
    ...
    ValueError: given buffer is not exactly four bytes long

    @type fourbytes: str
    @rtype: str
    @raises ValueError: for bad input
    """
    if not isinstance(fourbytes, str):
        raise ValueError("given buffer is not a string")
    if len(fourbytes) != 4:
        raise ValueError("given buffer is not exactly four bytes long")
    return ".".join(map(str, map(ord, fourbytes)))

def pack_mac(macstr):
    """Converts a mac address given in colon delimited notation to a
    six byte string in network byte order.

    >>> pack_mac("30:31:32:33:34:35")
    '012345'
    >>> pack_mac("bad")
    Traceback (most recent call last):
    ...
    ValueError: given mac addresses has an invalid number of colons


    @type macstr: str
    @rtype: str
    @raises ValueError: for badly formatted mac addresses
    """
    if not isinstance(macstr, str):
        raise ValueError("given mac addresses is not a string")
    parts = macstr.split(":")
    if len(parts) != 6:
        raise ValueError("given mac addresses has an invalid number of colons")
    parts = [int(part, 16) for part in parts] # raises ValueError
    parts = map(chr, parts) # raises ValueError
    return "".join(parts) # network byte order

def unpack_mac(sixbytes):
    """Converts a mac address given in a six byte string in network
    byte order to a string in colon delimited notation.

    >>> unpack_mac("012345")
    '30:31:32:33:34:35'
    >>> unpack_mac("bad")
    Traceback (most recent call last):
    ...
    ValueError: given buffer is not exactly six bytes long

    @type sixbytes: str
    @rtype: str
    @raises ValueError: for bad input
    """
    if not isinstance(sixbytes, str):
        raise ValueError("given buffer is not a string")
    if len(sixbytes) != 6:
        raise ValueError("given buffer is not exactly six bytes long")
    return ":".join(map("%2.2x".__mod__, map(ord, sixbytes)))

__all__.append("Omapi")
class Omapi:
    protocol_version = 100

    def __init__(self, hostname, port, username=None, key=None, debug=False):
        """
        @type hostname: str
        @type port: int
        @type username: str or None
        @type key: str or None
        @type debug: bool
        @param key: if given, it must be base64 encoded
        @raises binascii.Error: for bad base64 encoding
        @raises socket.error:
        @raises OmapiError:
        """
        self.hostname = hostname
        self.port = port
        self.authenticators = {0: OmapiNullAuthenticator()}
        self.defauth = 0
        self.debug = debug

        newauth = None
        if username is not None and key is not None:
            newauth = OmapiHMACMD5Authenticator(username, key)

        self.connection = socket.socket()
        self.inbuffer = InBuffer()
        self.connection.connect((hostname, port))

        self.send_protocol_initialization()
        self.recv_protocol_initialization()

        if newauth:
            self.initialize_authenticator(newauth)

    def close(self):
        """Close the omapi connection if it is open."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def check_connected(self):
        """Raise an OmapiError unless connected.
        @raises OmapiError:
        """
        if not self.connection:
            raise OmapiError("not connected")

    def recv_conn(self, length):
        self.check_connected()
        try:
            return self.connection.recv(length)
        except socket.error:
            self.close()
            raise

    def send_conn(self, data):
        self.check_connected()
        try:
            self.connection.sendall(data)
        except socket.error:
            self.close()
            raise

    def fill_inbuffer(self):
        """
        @raises OmapiError:
        @raises socket.error:
        """
        data = self.recv_conn(2048)
        if not data:
            self.close()
            raise OmapiError("connection closed")
        try:
            self.inbuffer.feed(data)
        except OmapiSizeLimitError:
            self.close()
            raise

    def send_protocol_initialization(self):
        """
        @raises OmapiError:
        @raises socket.error:
        """
        self.check_connected()
        buff = OutBuffer()
        buff.add_net32int(self.protocol_version)
        buff.add_net32int(4*6) # header size
        self.send_conn(buff.getvalue())

    def recv_protocol_initialization(self):
        """
        @raises OmapiError:
        @raises socket.error:
        """
        for result in self.inbuffer.parse_startup_message():
            if result is None:
                self.fill_inbuffer()
            else:
                self.inbuffer.resetsize()
                protocol_version, header_size = result
                if protocol_version != self.protocol_version:
                    self.close()
                    raise OmapiError("protocol mismatch")
                if header_size != 4*6:
                    self.close()
                    raise OmapiError("header size mismatch")

    def receive_message(self):
        """Read the next message from the connection.
        @rtype: OmapiMessage
        @raises OmapiError:
        @raises socket.error:
        """
        for message in self.inbuffer.parse_message():
            if message is None:
                self.fill_inbuffer()
            else:
                self.inbuffer.resetsize()
                if not message.verify(self.authenticators):
                    self.close()
                    raise OmapiError("bad omapi message signature")
                return message

    def receive_response(self, message, insecure=False):
        """Read the response for the given message.
        @type message: OmapiMessage
        @type insecure: bool
        @rtype: OmapiMessage
        @raises OmapiError:
        @raises socket.error:
        """
        response = self.receive_message()
        if self.debug:
            print "debug recv"
            response.dump()
        if not response.is_response(message):
            raise OmapiError("received message is not the desired response")
        # signature already verified
        if response.authid != self.defauth and not insecure:
            raise OmapiError("received message is signed with wrong " +
                        "authenticator")
        return response

    def send_message(self, message, sign=True):
        """Sends the given message to the connection.
        @type message: OmapiMessage
        @type sign: bool
        @param sign: whether the message needs to be signed
        @raises OmapiError:
        @raises socket.error:
        """
        self.check_connected()
        if sign:
            message.sign(self.authenticators[self.defauth])
        if self.debug:
            print "debug send"
            message.dump()
        self.send_conn(message.as_string())

    def query_server(self, message):
        """Send the message and receive a response for it.
        @type message: OmapiMessage
        @rtype: OmapiMessage
        @raises OmapiError:
        @raises socket.error:
        """
        self.send_message(message)
        return self.receive_response(message)
        

    def initialize_authenticator(self, authenticator):
        """
        @type authenticator: OmapiAuthenticatorBase
        @raises OmapiError:
        @raises socket.error:
        """
        msg = OmapiMessage.open("authenticator")
        msg.update_object(authenticator.auth_object())
        response = self.query_server(msg)
        if response.opcode != OMAPI_OP_UPDATE:
            raise OmapiError("received non-update response for open")
        authid = response.handle
        if authid == 0:
            raise OmapiError("received invalid authid from server")
        self.authenticators[authid] = authenticator
        authenticator.authid = authid
        self.defauth = authid

    def lookup_ip(self, mac):
        """
        @type mac: str
        @rtype: str or None
        @raises ValueError:
        @raises OmapiError:
        @raises socket.error:
        """
        msg = OmapiMessage.open("lease")
        msg.obj.append(("hardware-address", pack_mac(mac)))
        response = self.query_server(msg)
        if response.opcode != OMAPI_OP_UPDATE:
            raise OmapiErrorNotFound()
        try:
            return unpack_ip(dict(response.obj)["ip-address"])
        except KeyError: # ip-address
            raise OmapiErrorNotFound()

    def lookup_host(self, mac):
        """
        @type mac: str
        @rtype: str or None
        @raises ValueError:
        @raises OmapiError:
        @raises socket.error:
        """
        msg = OmapiMessage.open("host")
        msg.obj.append(("hardware-address", pack_mac(mac)))
        response = self.query_server(msg)
        if response.opcode != OMAPI_OP_UPDATE:
            raise OmapiErrorNotFound()
        try:
            return unpack_ip(dict(response.obj)["ip-address"])
        except KeyError: # ip-address
            raise OmapiErrorNotFound()

# Executed code
options = actuator_cli_parsing()

if options.daemon :
    with DaemonContext(working_directory="/tmp", pidfile=None) :
        main(options)
else :
    main(options)
