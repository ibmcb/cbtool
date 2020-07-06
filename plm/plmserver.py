#!/usr/bin/env python
'''
Created on Aug 3, 2012

Parallel Libvirt Manager

@author: Michael R. Galaxy, Marcio A. Silva
'''

import sys, os, tty, termios, atexit, threading, SocketServer, signal, inspect, xmlrpclib, resource, socket
import libxml2

from libvirt import *
from logging import getLogger, StreamHandler, Formatter, Filter, DEBUG, ERROR, INFO, WARN, CRITICAL
from logging.handlers import logging, SysLogHandler, RotatingFileHandler
from optparse import OptionParser
from os import getuid
from pwd import getpwuid
from platform import node
from hashlib import sha256
from sys import stdout, path
from time import sleep
from DocXMLRPCServer import DocXMLRPCServer
from DocXMLRPCServer import DocXMLRPCRequestHandler
from daemon import DaemonContext
from re import split, sub, compile, MULTILINE
from uuid import uuid5, NAMESPACE_DNS
from random import choice, randint

try :
    # Provided by RHEL 6.2
    from libvirt_qemu import qemuMonitorCommand
    from libvirt import virEventRegisterDefaultImpl
    from libvirt import virEventAddHandle
    from libvirt import virEventRunDefaultImpl
except ImportError:
    pass

path.append('/'.join(path[0].split('/')[0:-1]))
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit, VerbosityFilter, MsgFilter
from lib.auxiliary.data_ops import plm_parse_host_groups
from lib.remote.network_functions import hostname2ip
from lib.remote.process_management import ProcessManagement
from lib.stores.redis_datastore_adapter import RedisMgdConn
from pypureomapi import Omapi

options = None

def actuator_cli_parsing() :
    '''
    TBD
    '''
    # Do command line parsing
    usage = '''usage: %prog [options] 
    '''

    parser = OptionParser(usage)

    parser.add_option("--debug_host", dest = "debug_host", default = None, \
                      help = "Point PLM to a remote debugger")

    # Process options
    parser.add_option("--procid", dest = "processid", metavar = "processid", \
                      default = "TEST_" + getpwuid(getuid())[0], \
                      help = "Set the processid")

    # Log Options
    parser.add_option("--loghost", dest = "loghost", metavar = "loghost", \
                      default = "127.0.0.1", \
                      help = "Set the syslog host to loghost")

    parser.add_option("--logport", dest = "logport", metavar = "logport", \
                      default = "5114", \
                      help = "Set the syslog port to logport")

    # Regis Options
    parser.add_option("--redis_host", dest = "redis_host", metavar = "REDIS_HOST", \
                      default = "127.0.0.1", \
                      help = "TBD")

    parser.add_option("--redis_port", dest = "redis_port", metavar = "REDIS_PORT", \
                      default = 6379, \
                      help = "TBD")
    
    parser.add_option("--redis_dbid", dest = "redis_dbid", metavar = "REDIS_DBID", \
                  default = 15, \
                  help = "TBD")

    # DHCP Options
    parser.add_option("--dhcp_omapi_server", dest = "dhcp_omapi_server", metavar = "dhcp_omapi_server", \
                      default = "127.0.0.1", \
                      help = "Set the OMAPI dhcp address to get IP addresses")

    parser.add_option("--dhcp_omapi_port", dest = "dhcp_omapi_port", metavar = "dhcp_omapi_port", \
                      default = "9991", \
                      help = "Set the port to dhcp OMAPI service")

    # Group Options
    parser.add_option("--groups", dest = "groups", metavar = "hyp", \
                      default = None, \
                      help = "Set the list of Host Groups in the format HostGroup1:Host1,...,Host2")

    parser.add_option("--port", dest = "port", metavar = "port", \
                      default = "6060", \
                      help = "Set the REST port for PLM")

    parser.add_option("--daemon", dest = "daemon", action = "store_true", \
                  default = False, \
                  help ="Execute operation in daemonized mode")

    # Instance Options
    parser.add_option("--bridge", dest = "bridge", metavar = "bridge", \
                      default = "br0", \
                      help = "Set the software bridge name on each node")

    parser.add_option("--file_base_storage", dest = "file_base_storage", \
                      metavar = "file_base_storage", default = "/kvm_repo/plmfbase", \
                      help = "Set the qcow base file location on each node")

    parser.add_option("--file_base_storagepool", dest = "file_base_storagepool", \
                      metavar = "file_base_storagepool", default = "plm-filebasestorage", \
                      help = "Set the qcow base storage pool on each node")

    parser.add_option("--volume_base_storage", dest = "volume_base_storage", \
                      metavar = "volume_base_storage", default = "vgplm", \
                      help = "Set the qcow base file location on each node")

    parser.add_option("--volume_base_storagepool", dest = "volume_base_storagepool", \
                      metavar = "volume_base_storagepool", default = "plm-volumebasestorage", \
                      help = "Set the dm snapshot read storage pool on each node")

    parser.add_option("--file_snapshot_storage", dest = "file_snapshot_storage", \
                      metavar = "file_snapshot_storage", default = "/kvm_repo/plmfsnap", \
                      help = "Set the qcow snapshot location on each node")

    parser.add_option("--file_snapshot_storagepool", dest = "file_snapshot_storagepool", \
                      metavar = "file_snapshot_storagepool", default = "plm-filesnapshotstorage", \
                      help = "Set the qcow snapshot storage pool on each node")

    parser.add_option("--volume_snapshot_storage", dest = "volume_snapshot_storage", \
                      metavar = "volume_snapshot_storage", default = "vgplm", \
                      help = "Set the dm snapshot write location on each node")

    parser.add_option("--volume_snapshot_storagepool", dest = "volume_snapshot_storagepool", \
                      metavar = "volume_snapshot_storagepool", default = "plm-volumesnapshotstorage", \
                      help = "Set the dm snapshot write storage pool on each node")

    parser.add_option("--state_save_storage", dest = "state_save_storage", \
                      metavar = "state_save_storage", default = "/kvm_repo/statesave", \
                      help = "Set the instance state save location on each node")

    parser.add_option("--cache_mode", dest = "cache_mode", metavar = "cache_mode", default = "none", \
                      help = "")

    parser.add_option("--disk_mode", dest = "disk_mode", metavar = "disk_mode", default = "virtio", \
            help = "Options: virtio, ide, scsi")

    parser.add_option("--net_mode", dest = "net_mode", metavar = "net_mode", default = "virtio", \
            help = "Options: virtio, pci")

    parser.add_option("--qemu_binary", dest = "qemu_binary", metavar = "qemu_binary", default = "/usr/bin/kvm", \
              help = "Location of qemu binary program")

    parser.add_option("--mac_prefix", dest = "mac_prefix", metavar = "mac_prefix", default = "12:34", \
              help = "Global 2-byte prefix for PLM mac addresses")

    parser.add_option("--disable_vhost_net", dest = "disable_vhost_net", metavar = "disable_vhost_net", default = False, \
              help = "Disable libvirt/qemu use of vhost network system")

    parser.add_option("--hypervisor", dest = "hypervisor", metavar = "hypervisor", \
                      default = "kvm", help = "Set the hypervisor, Options: (kvm|xen)")

    parser.add_option("--cluster_name", dest = "cluster_name", metavar = "cluster_name", default = "PLM", \
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

def unwrap_kwargs(func, spec) :
    '''
    TBD
    '''
    def wrapper(*args, **kwargs) :
        '''
        TBD
        '''
        if args and isinstance(args[-1], list) and len(args[-1]) == 2 and "kwargs" == args[-1][0]:
            return func(*args[:-1], **args[-1][1])
        else:
            return func(*args, **kwargs)

    wrapper.__doc__ = str(spec)
    if func.__doc__ is not None :
        wrapper.__doc__ +=  "\n\n" + func.__doc__
    return wrapper

class Plm :
    '''
    TBD
    '''
    @trace
    def __init__ (self, groups, oscp) :
        '''
        TBD
        '''
        self.pid = "PLMd" 
        self.groups = plm_parse_host_groups(self.pid, groups)

        self.lvirt_conn = {}
        self.oscp = oscp
        self.PLMd_restarted = True
        self.redis_conn = False
        
        self.dhcp_omap_pkey = "d+y8yPwtC0nJ0C0uRC5cxYREYGPBkJwhJYjHbb1LkoW0FF6gYr3SiVi6 HRQUcl4Y7gdzwvi0hgPV+Gdy1wX9vg==" 
        self.dhcp_omap_keyn = "omapi_key"
        
        self.vhw_config = {}
        self.vhw_config["pico32"] = { "vcpus" : "1", "vmem" : "192", "vstorage" : "2048", "vnics" : "1" }
        self.vhw_config["nano32"] = { "vcpus" : "1", "vmem" : "512", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["micro32"] = { "vcpus" : "1", "vmem" : "1024", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["copper32"] = { "vcpus" : "1", "vmem" : "2048", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze32"] = { "vcpus" : "1", "vmem" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["iron32"] = { "vcpus" : "2", "vmem" : "2048", "vstorage" : "179200", "vnics" : "1" }
        self.vhw_config["silver32"] = { "vcpus" : "4", "vmem" : "2048", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["gold32"] = { "vcpus" : "8", "vmem" : "4096", "vstorage" : "358400", "vnics" : "1" }
        self.vhw_config["cooper64"] = { "vcpus" : "2", "vmem" : "4096", "vstorage" : "61440", "vnics" : "1" }
        self.vhw_config["bronze64"]  = { "vcpus" : "2", "vmem" : "4096", "vstorage" : "870400", "vnics" : "1" }
        self.vhw_config["silver64"] = { "vcpus" : "4", "vmem" : "8192", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["gold64"] = { "vcpus" : "8", "vmem" : "16384", "vstorage" : "1048576", "vnics" : "1" }
        self.vhw_config["platinum64"] = { "vcpus" : "16", "vmem" : "16384", "vstorage" : "2097152", "vnics" : "1" }

        self.vhw_config["premium"] = { "cpu_upper" : "1000", "cpu_lower" : "1000", "memory_upper" : "100", "memory_lower" : "100" }
        self.vhw_config["standard"] = { "cpu_upper" : "1000", "cpu_lower" : "500", "memory_upper" : "100", "memory_lower" : "50" }
        self.vhw_config["value"] = { "cpu_upper" : "-1", "cpu_lower" : "0", "memory_upper" : "100", "memory_lower" : "0" }

        self.populate_object_store()

        self.state_refresh()

    def PLMraise(self, host, status, msg) :
        '''
        TBD
        '''
        # We try to keep connections open as long as possible, but if there is an
        # error, make sure we close it and don't attempt to reused an old one
        if host in self.lvirt_conn and self.lvirt_conn[host] :
            try :
                self.lvirt_conn[host].close()
            except :
                pass
            self.lvirt_conn[host] = False
        cberr(msg, True)
        raise xmlrpclib.Fault(3, 'PLMException;%s;%s' % (msg, str(status)))

    @trace    
    def global_error(self, ctx, error) :
        '''
        TBD
        '''
        cbdebug("libvirt global error: " + error)

    def success(self, msg, result) :
        '''
        TBD
        '''
        cbdebug(msg)
        return {"status" : 0, "msg" : msg, "result" : result }

    def error(self, status, msg, result) :
        '''
        TBD
        '''
        cberr(msg)
        return {"status" : status, "msg" : msg, "result" : result }

    '''
    Connection methods, used to establish communication with both libvirt and Redis#
    '''

    @trace
    def redis_conn_check(self) :
        '''
        TBD
        '''
        try :
            if not self.redis_conn :
                self.redis_conn = RedisMgdConn(self.oscp)

        except RedisMgdConn.ObjectStoreMgdConnException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            self.PLMraise("local", 396, str(_msg))

    def lock (self, obj_type, obj_id, id_str):
        '''
        TBD
        '''
        try:
            self.conn_check()
            _lock = self.osci.acquire_lock(obj_type, obj_id, id_str, 1)
            return _lock

        except RedisMgdConn.ObjectStoreMgdConnException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            return False

    def unlock (self, obj_type, obj_id, lock) :
        '''
        TBD
        '''
        try:
            self.conn_check()
            self.osci.release_lock(obj_type, obj_id, lock)
            return True

        except RedisMgdConn.ObjectStoreMgdConnException, obj :
            _msg = str(obj.msg)
            cberr(_msg)
            return False

    @trace
    def lvirt_conn_check(self, host) :
        '''
        TBD
        '''
        if host not in self.lvirt_conn or not self.lvirt_conn[host] :
            try :
                if options.hypervisor == "xen" :
                    cbdebug("Attempting to connect to libvirt daemon running on hypervisor (Xen) \"" + host + "\"....")
                    self.lvt_cnt[host] = open("xen+tcp://" + host)
                elif options.hypervisor == "kvm" :
                    cbdebug("Attempting to connect to libvirt daemon running on hypervisor (KVM) \"" + host + "\"....")
                    self.lvirt_conn[host] = open("qemu+tcp://" + host + "/system")
                cbdebug("Connection to libvirt daemon running on hypervisor \"" + host + "\" successfully established.")
                #registerErrorHandler(self.global_error, "blah")
                self.lvirt_conn[host].host = host
            except libvirtError, msg :
                self.PLMraise(host, 394, str(msg))
                
        return self.lvirt_conn[host]

    # Reduce the amount of attribute sharing between VM and VMC objects
    # in the template configuration files by having two template functions
    # instead of one.....

    '''
    Support methods, dealing mostly with data (XML content, MAC and IP addresses)
    '''

    def generate_libvirt_vm_template(self, imageid_list, instance_attr_list) :
        '''
        TBD
        '''

        if options.hypervisor == "xen" :
            _xml_template = "<domain type='xen' "
        else :
            _xml_template = "<domain type='kvm' "
        
        if instance_attr_list["replication_port"] or \
        instance_attr_list["qemu_debug_port"] is not None or \
        instance_attr_list["svm_qemu_debug_port"] is not None:
            _xml_template += "xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'"
             
        _xml_template += ">\n"
        _xml_template += "\t<name>" + str(instance_attr_list["cloud_lvid"]) + "</name>\n"
        _xml_template += "\t<uuid>" + str(instance_attr_list["cloud_uuid"]) + "</uuid>\n"
        _xml_template += "\t<memory>" + str(int(instance_attr_list["vmem"]) * 1024) + "</memory>\n"
        _xml_template += "\t<currentMemory>" + str(int(instance_attr_list["vmem"]) * 1024) + "</currentMemory>\n"
        _xml_template += "\t<vcpu>" + str(instance_attr_list["vcpus"]) + "</vcpu>\n"
        _xml_template += "\t<os>\n"
        
        if options.hypervisor == "xen" :
            _xml_template += "\t\t<type arch='x86_64' machine='xenfv'>hvm</type>\n"
        else :
            _xml_template += "\t\t<type machine='pc'>hvm</type>\n"

        if options.hypervisor == "xen" :
            _xml_template += "\t\t<loader>/usr/lib/xen/boot/hvmloader</loader>\n"
        
        _xml_template += "\t\t<boot dev='hd'/>\n"
        _xml_template += "\t</os>\n"
        _xml_template += "\t<features>\n"
        _xml_template += "\t\t<acpi/>\n"
        _xml_template += "\t\t<apic/>\n"
        _xml_template += "\t\t<pae/>\n"
        _xml_template += "\t</features>\n"
        _xml_template += "\t<devices>\n"
        _xml_template += "\t\t<emulator>" + options.qemu_binary + "</emulator>\n"
        
        for _imageid in imageid_list :
            _xml_template += "\t\t<disk type='file' device='disk'>\n"
            _xml_template += "\t\t\t<driver name='qemu' type='" + instance_attr_list["root_disk_format"] + "' cache='" + options.cache_mode + "'/>\n"
            _xml_template += "\t\t\t<source file='" + _imageid + "'/>\n"
            _xml_template += "\t\t\t<target dev='"
            if options.disk_mode == "virtio" :
                _xml_template += "v"
            elif options.disk_mode == "ide" :
                _xml_template += "h" 
            elif options.disk_mode == "scsi" :
                _xml_template += "s"
                
            _xml_template += "d" + chr(ord('a') + imageid_list.index(_imageid)) + "' bus='" + options.disk_mode + "'/>\n"
                 
            _xml_template += "\t\t</disk>\n"
       
        _xml_template += "\t\t<interface type='bridge'>\n"
        _xml_template += "\t\t\t<source bridge='" + options.bridge + "'/>\n"
        _xml_template += "\t\t\t<mac address='" + str(instance_attr_list["cloud_mac"]) + "'/>\n"
        if options.net_mode == "virtio" :
            _xml_template += "\t\t\t<model type='virtio'/>\n"
            # Currently, vhost-net is not compatible with kemari. Revert to vanilla virtio
            if options.disable_vhost_net :
                _xml_template += "\t\t\t<driver name='qemu'/>\n"
        _xml_template += "\t\t</interface>\n"
        _xml_template += "\t\t<serial type='pty'>\n"
        _xml_template += "\t\t\t<target port='0'/>\n"
        _xml_template += "\t\t</serial>\n"
        _xml_template += "\t\t<console type='pty'>\n"
        _xml_template += "\t\t\t<target port='0'/>\n"
        _xml_template += "\t\t</console>\n"
        _xml_template += "\t\t<input type='tablet' bus='usb'>\n"
        _xml_template += "\t\t\t<alias name='input0'/>\n"
        _xml_template +=  "\t\t</input>\n"
        _xml_template += "\t\t<input type='mouse' bus='ps2'/>\n"
        
        _xml_template += "\t\t<graphics type='vnc' port='-1' autoport='yes' listen='" + instance_attr_list["host_ip"] + "' keymap='en-us'/>\n"
        _xml_template += "\t\t<video>\n"
        _xml_template += "\t\t\t<model type='cirrus' vram='9216' heads='1'/>\n"
        _xml_template += "\t\t</video>\n"
        
        if options.hypervisor == "xen" :
            _xml_template += "\t\t<memballoon model='xen'/>\n"
        else :
            _xml_template += "\t\t<memballoon model='virtio'/>\n"
        
        _xml_template += "\t</devices>\n"
        
        if instance_attr_list["replication_port"] is not None or \
        instance_attr_list["qemu_debug_port"] is not None or \
        instance_attr_list["svm_qemu_debug_port"] is not None:
            _xml_template += "\t<qemu:commandline>\n"
            if instance_attr_list["replication_port"] is not None :
                _xml_template += "\t\t<qemu:arg value='-incoming'/>\n"
                _xml_template += "\t\t<qemu:arg value='kemari:tcp:TMPLT_SVM_STUB_IP:" + str(instance_attr_list["svm_stub_ip"]) + "'/>\n"
                
            if instance_attr_list["qemu_debug_port"] is not None and \
            instance_attr_list["replication_port"] is None :
                _xml_template += "\t\t<qemu:arg value='-gdb'/>\n"
                _xml_template += "\t\t<qemu:arg value='tcp::" + str(instance_attr_list["qemu_debug_port"]) + "'/>\n"
                
            if instance_attr_list["svm_qemu_debug_port"] is not None and \
            instance_attr_list["replication_port"] is not None :
                _xml_template += "\t\t<qemu:arg value='-gdb'/>\n"
                _xml_template += "\t\t<qemu:arg value='tcp::" + str(instance_attr_list["svm_qemu_debug_port"]) + "'/>\n"
            _xml_template += "\t</qemu:commandline>\n"

        _xml_template += "</domain>\n"
    
        return _xml_template

    @trace
    def generate_mac_addr(self, userid) :
        '''
        This function is designed to pseudo-determinstically generate MAC addresses.
        
        The standard 6-byte MAC address is splitup as follows:
        
        | prefix (X bytes long) | selector byte | suffix (Y bytes long) |
        
        For example:
        1. The user sets an X-byte long 'mac_prefix' == '12:34'. This is used to 
           represent all experiments in a shared cluster controlled by PLMloud.
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
        self.redis_conn_check()
        counter = self.redis_conn.update_counter(self.oscp["cluster_name"], "COUNTER", "INSTANCES", "increment")

        bytes_needed = (17 - len(options.mac_prefix)) / 3 - 1
        unique_mac_selector_key = node() + userid + options.cluster_name + "plm"
        selector_byte = sha256(unique_mac_selector_key).hexdigest()[-2:]
        mac = options.mac_prefix + ":" + selector_byte 
        
        for x in range(0, bytes_needed) :
            byte = ((counter >> (8 * ((bytes_needed - 1) - x))) & 0xff)
            mac += (":%02x" % (byte)) 
        
        return mac.replace('-', ':')

    @trace
    def get_ip_address(self, mac) :
        '''
        TBD
        '''
        ip = None
        try:
            _status = 100
            o = Omapi(options.dhcp_omapi_server, int(options.dhcp_omapi_port), \
                      self.dhcp_omap_keyn, self.dhcp_omap_pkey, debug=False)
            _msg = "ip found"
            ip = o.lookup_ip(mac)
            return ip
        
        except Exception, e :
            _msg = "ip not found"
            return False

    '''
    Upper-level core methods, manipulating nodes, instances and pools/volumes #
    '''

    def populate_object_store(self) :
        '''
        TBD
        '''
        self.redis_conn_check()
        _object_store_data = {}
        _object_store_data["query"] = {}
        _object_store_data["time"] = {}
        _object_store_data["setup"] = {}
        _object_store_data["ai_templates"] = {}
        _object_store_data["aidrs_templates"] = {}
        _object_store_data["vmcrs_templates"] = {}
        _object_store_data["firs_templates"] = {}                
        _object_store_data["vm_templates"] = {}

#        _object_store_data["query"]["mandatory_tags"] = "cloud_hostname,cloud_ip,cloud_lvid"
        _object_store_data["query"]["mandatory_tags"] = "cloud_lvid"
        _object_store_data["query"]["cloud_attributes"] = "name,description,client_should_refresh"
        _object_store_data["query"]["object_type_list"] = "GROUP,COMPUTENODE,INSTANCE,VOLUME,STORAGEPOOL"
        _object_store_data["query"]["group"] = ""
        _object_store_data["query"]["computenode"] = ""
        _object_store_data["query"]["instance"] = ""
        _object_store_data["query"]["volume"] = ""
        _object_store_data["query"]["storagepool"] = ""
        _object_store_data["time"]["experiment_id"] = "doesnotmatter"
        _object_store_data["setup"]["global_object_list"] = "setup,time,query"
        _object_store_data["name"] = options.cluster_name
        _object_store_data["description"] = "Parallel Libvirt Manager"
        _object_store_data["client_should_refresh"] = "yes"

        self.redis_conn.initialize_object_store(self.oscp["cluster_name"], _object_store_data, True)

        return True

    def state_refresh(self) :
        '''
        TBD
        '''
        if self.PLMd_restarted :
            _msg = "PLM was just restarted. Proceeding to refresh cloud state"
            cbdebug(_msg)
            self.redis_conn_check()
            if self.PLMd_restarted :
                _group_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], "GROUP")
            if _group_uuids :
                for _group_uuid in _group_uuids :
                    _group_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                  "GROUP", False, \
                                                                  _group_uuid, False)

                    for _node_name in _group_attr_list["computenodes"].split(',') :
                        self.node_register(_node_name, "COMPUTENODE", _group_attr_list["cloud_hostname"]) 
                    self.PLMd_restarted = False
            return True

    def group_cleanup(self, group_name, tag, userid) :
        '''
        TBD
        '''
        if group_name in self.groups :
            for _node_name in self.groups[group_name].split(',') :
                self.node_cleanup(_node_name, tag, userid)
        _msg = "Group \"" + group_name + "\" was successfully purged from all"
        _msg += " instance names containing the string \"" + tag + "\"."
        return self.success(_msg, None)

    def group_register(self, group_name) :
        '''
        TBD
        '''
        attr_list = {}
        attr_list["notification"] = "False"

        if group_name in self.groups :

            self.populate_object_store()

            attr_list["cloud_uuid"] = str(uuid5(NAMESPACE_DNS,group_name)).upper()
            attr_list["uuid"] = attr_list["cloud_uuid"]
            
            attr_list["cloud_hostname"] = group_name
            attr_list["cloud_lvid"] = attr_list["cloud_hostname"]
            attr_list["name"] = group_name
            attr_list["computenodes"] = self.groups[group_name]
            for _node_name in attr_list["computenodes"].split(',') :
                _node_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], "COMPUTENODE", _node_name, True)
                if not _node_uuid :
                    self.node_register(_node_name, "computenode", group_name)

            self.redis_conn_check()

            _group_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], "GROUP", attr_list["cloud_uuid"], False)

            if not _group_uuid :
                self.redis_conn.create_object(self.oscp["cluster_name"], "GROUP", attr_list["cloud_uuid"], attr_list, False, False)
                _msg = "Group \"" + group_name + "\" was successfully registered."
            else :
                _attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                        "GROUP", False, \
                                                        _group_uuid, False)

                _msg = "Group \"" + group_name + "\" was already registered."

            return self.success(_msg, attr_list)
        else :
            _msg = "Group \"" + group_name + "\" not defined!"
            return self.error(819, _msg, None)

    def groups_describe(self, group_name = "all") :
        '''
        TBD
        '''
        self.redis_conn_check()
        
        _attr_list = {}
        _group_uuids = False

        if group_name != "all" :
            _group_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], "GROUP", group_name, True)
            if _group_uuid :
                _group_uuids = [_group_uuid]
            else :
                _msg = "Host Group \"" + group_name + "\" was not registered on this Parallel Libvirt Manager"
        else :
            _group_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], "GROUP")

        if _group_uuids :
            for _group_uuid in _group_uuids :
                _attr_list[_group_uuid] = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                     "GROUP", \
                                                                     False, \
                                                                     _group_uuid, \
                                                                     False)
            _msg = "Group data found."
        else :
            if group_name == "all" :
                _msg = "Group data not found"
                
        return self.success(_msg, _attr_list)

    def group_unregister(self, group_name) :
        '''
        TBD
        '''
        attr_list = {}
        if group_name in self.groups :
            #FIX ME
            attr_list["cloud_uuid"] = str(uuid5(NAMESPACE_DNS,group_name)).upper()
            attr_list["cloud_hostname"] = group_name
            attr_list["computenodes"] = self.groups[group_name]

            for _node_name in attr_list["computenodes"].split(',') :
                self.node_unregister(_node_name, "computenode")
   
            self.redis_conn_check()

            _obj_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], "GROUP", attr_list["cloud_uuid"], False)
            
            if _obj_uuid :
                _attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                        "GROUP", False, \
                                                        attr_list["cloud_uuid"], \
                                                        False)

                self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                               "GROUP", \
                                               _attr_list["cloud_uuid"], \
                                               _attr_list, \
                                               False)

                _msg = "Group \"" + group_name + "\" was successfully unregistered."
            else :
                _attr_list ={}
                _msg = "Group \"" + group_name + "\" was already unregistered."

        return self.success(_msg, attr_list)

    def node_cleanup(self, node_name, tag, userid) :
        '''
        TBD
        '''
        _node_name, _node_ip = hostname2ip(node_name)
        
        _lvt_conn = self.lvirt_conn_check(_node_ip)
        _registered_instances = self.redis_conn.get_list(self.oscp["cluster_name"], "INSTANCELIST", _node_name)        

        # First the "registered" instances are terminated through the proper
        # method (i.e., updating the data store).
        for _instance_id in _registered_instances :
            _instance_uuid, _instance_tag = _instance_id.split('|')
            if _instance_tag.count(userid) :
                self.instance_destroy(_instance_tag)

        # Now, the rest of instances is destroyed.
        self.destroy_all_domains(_lvt_conn, False, userid)

        _msg = "Hypervisor node \"" + node_name
        _msg += "\" was successfully purged from all instance whose names "
        _msg += "contain the string \"" + userid + "\"."
        return self.success(_msg, None)

    def node_register(self, node_name, function, group = None) :
        '''
        TBD
        '''
        _node_attr_list = {}
        _node_attr_list["notification"] = "False"

        if group :
            _node_attr_list["group"] = group
        else :
            _node_attr_list["group"] = "NA"

        _node_attr_list["function"] = function

        _node_attr_list["cloud_hostname"], _node_attr_list["cloud_ip"] = hostname2ip(node_name)

        _ip = _node_attr_list["cloud_ip"]
        _name = _node_attr_list["cloud_hostname"]
        
        _defined_instances = self.list_domains(self.lvirt_conn_check(_ip), True)

        _defined_storage_pools = self.list_storage_pools(self.lvirt_conn_check(_ip), True)

        self.redis_conn_check()

        _obj_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], function.upper(), _node_attr_list["cloud_hostname"], True)

        if not _obj_uuid :
        
            _temp_dict = self.get_host_info(self.lvirt_conn_check(_ip))

            _node_attr_list["instances"] = 0
            _node_attr_list["cloud_uuid"] = _temp_dict["uuid"]
            _node_attr_list["cloud_lvid"] = _node_attr_list["cloud_hostname"]
            _node_attr_list.update(_temp_dict)
            _node_attr_list["vcpus"] = 0
            _node_attr_list["vmem"] = 0
            _node_attr_list["name"] = _name

            self.redis_conn.create_object(self.oscp["cluster_name"], function.upper(), _node_attr_list["cloud_uuid"], _node_attr_list, False, False)
            self.redis_conn.add_to_list(self.oscp["cluster_name"], "NODELIST", _node_attr_list["group"], _node_attr_list["cloud_uuid"])

            _msg = "Proceeding to discover storage pools and volumes on "
            _msg += "hypervisor node \"" + _node_attr_list["cloud_ip"]
            _msg += "\" (" + _node_attr_list["cloud_uuid"] + ")..."
            cbdebug(_msg)
            
            if not options.file_base_storagepool in _defined_storage_pools :
                self.storagepool_create(options.file_base_storagepool, _name, "directory", options.file_base_storage)
    
            if not options.file_snapshot_storagepool in _defined_storage_pools :
                self.storagepool_create(options.file_snapshot_storagepool, _name, "directory", options.file_snapshot_storage)

            if not options.volume_base_storagepool in _defined_storage_pools :
                self.storagepool_create(options.volume_base_storagepool, _name, "logical", None, options.volume_base_storage, False, True)
   
            if not options.volume_snapshot_storagepool in _defined_storage_pools :
                self.storagepool_create(options.volume_snapshot_storagepool, _name, "logical", None, options.volume_snapshot_storage, False, True)

            _defined_storage_pools = self.list_storage_pools(self.lvirt_conn_check(_ip), True)

            for _storage_pool in _defined_storage_pools :
                _storage_pool_lvirt_obj = _defined_storage_pools[_storage_pool]

                _storagepool_attr_list = self.get_storage_pool_info(self.lvirt_conn_check(_ip), \
                                                                _storage_pool, \
                                                                _storage_pool_lvirt_obj)
                _storagepool_attr_list["notification"] = "False"

                _storagepool_attr_list["host_name"] = _node_attr_list["cloud_hostname"]
                _storagepool_attr_list["host_ip"] = _node_attr_list["cloud_ip"]
                _storagepool_attr_list["host_uuid"] = _node_attr_list["cloud_uuid"]
                _storagepool_attr_list["cloud_lvid"] = _storagepool_attr_list["host_name"]  + '.' + _storage_pool

                if _storagepool_attr_list["cloud_lvid"].count("plm-") :
                    _storagepool_attr_list["creator"] = "PLM"
                else :
                    _storagepool_attr_list["creator"] = "other"   

                _storagepool_attr_list["name"] = _storagepool_attr_list["cloud_lvid"]

                if not self.redis_conn.object_exists(self.oscp["cluster_name"], "STORAGEPOOL", \
                                                 _storagepool_attr_list["cloud_uuid"], \
                                                 False) :

                    self.redis_conn.create_object(self.oscp["cluster_name"], "STORAGEPOOL", \
                                                  _storagepool_attr_list["cloud_uuid"], \
                                                  _storagepool_attr_list, \
                                                  False, \
                                                  False)
                                    
                _created_volumes = self.list_volumes(self.lvirt_conn_check(_ip), \
                                                                           _storage_pool)

                for _volume in _created_volumes :
                    _volume_lvirt_obj = _created_volumes[_volume]
                    self.volume_create(_volume, _ip, _storage_pool, False, _volume_lvirt_obj)

            _msg = "Proceeding to discover instances on "
            _msg += "hypervisor node \"" + _node_attr_list["cloud_ip"]
            _msg += "\" (" + _node_attr_list["cloud_uuid"] + ")..."
            cbdebug(_msg)

            for _instance in _defined_instances :
                _instance_lvirt_obj = _defined_instances[_instance]
                
                _node = _node_attr_list["cloud_hostname"] + '|' + _node_attr_list["cloud_uuid"]
                _instance_attr_list = self.instance_run(None, \
                                                        _instance, \
                                                        None, \
                                                        group, \
                                                        _instance_lvirt_obj, \
                                                        _node)["result"]

                _node_attr_list["vcpus"], _node_attr_list["vmem"] = \
                self.node_resource_update(_node_attr_list["cloud_uuid"], \
                                          _node_attr_list["cloud_ip"], \
                                          "increased", \
                                          _instance_attr_list["vcpus"], \
                                          int(_instance_attr_list["vmem"])/1024)

            _proc_man = ProcessManagement(hostname = _ip)
            _create_save_state_cmd = "mkdir -p " + options.state_save_storage + "; chmod 777 " + options.state_save_storage

            _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_create_save_state_cmd)

            _msg = "Hypervisor node \"" + _node_attr_list["cloud_ip"] + "\" ("
            _msg += _node_attr_list["cloud_uuid"] + ") was successfully registered."        
                    
        else :
            _node_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                         function.upper(), \
                                                         False, _obj_uuid, \
                                                         False)
            
            # In case the node was previously registered, just make sure that there
            # are no "stale" instances on the datastore (i.e., instances manually
            # deleted while plm was inactive)
            _msg = "Proceeding to remove \"stale\" instances on compute node \""
            _msg += _node_attr_list["cloud_ip"] + "\" (" + _node_attr_list["cloud_uuid"] + ")...."
            cbdebug(_msg)

            _registered_instances = self.redis_conn.get_list(self.oscp["cluster_name"], \
                                                             "INSTANCELIST", \
                                                             _node_attr_list["cloud_hostname"])
            for _instance in _registered_instances :
                _instance_uuid, _instance_lvid = _instance.split('|')
                if _instance_lvid not in _defined_instances :
                    _instance_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                     "INSTANCE", \
                                                                     False, \
                                                                     _instance_uuid, \
                                                                     False)
                                    
                    self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                                   "INSTANCE", \
                                                   _instance_uuid,\
                                                    _instance_attr_list, \
                                                    False)

                    self.redis_conn.remove_from_list(self.oscp["cluster_name"], \
                                                     "INSTANCELIST", \
                                                     _node_attr_list["cloud_hostname"], \
                                                     _instance_uuid + '|' + _instance_lvid)

                    _node_attr_list["vcpus"], _node_attr_list["vmem"] = \
                    self.node_resource_update(_node_attr_list["cloud_uuid"], \
                                              _node_attr_list["cloud_ip"], \
                                              "decreased", \
                                              _instance_attr_list["vcpus"], \
                                              int(_instance_attr_list["vmem"])/1024)

            _msg = "Compute node \"" + _node_attr_list["cloud_ip"] 
            _msg += "\" (" + _node_attr_list["cloud_uuid"] + ") was already registered."  

        return self.success(_msg, _node_attr_list)

    def nodes_describe(self, function, node_name) :
        '''
        TBD
        '''
        self.redis_conn_check()
        attr_list = {}

        if node_name != "all" :
            _node_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                       "COMPUTENODE", \
                                                       node_name, \
                                                       True)
            if _node_uuid :
                _node_uuids = [_node_uuid]
            else :
                _node_uuids = False
                _msg = "Node \"" + node_name + "\" was not registered on this Parallel Libvirt Manager"
        else :
            _node_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], \
                                                          function.upper())
            if not _node_uuids :
                _msg = "No nodes currently registered on this Parallel Libvirt Manager"

        if _node_uuids :
            for _node_uuid in _node_uuids :
                attr_list[_node_uuid] = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                   function.upper(), \
                                                                   False, \
                                                                   _node_uuid, \
                                                                   False)
            _msg = "Node data found"

        return self.success(_msg, attr_list)

    def node_unregister(self, node_name, function) :
        '''
        TBD
        '''
        self.redis_conn_check()

        _obj_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                  function.upper(), \
                                                  node_name, \
                                                  True)
        
        if _obj_uuid :
            _attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                    function.upper(), \
                                                    True, \
                                                    node_name, \
                                                    False)

            self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                           function.upper(), \
                                           _attr_list["cloud_uuid"], \
                                           _attr_list, \
                                           False)

            self.redis_conn.remove_from_list(self.oscp["cluster_name"], \
                                             "NODELIST", \
                                             _attr_list["group"], \
                                             _attr_list["cloud_uuid"])

            _msg = "Hypervisor node \"" + _attr_list["cloud_ip"] + "\" (" + _attr_list["cloud_uuid"] + ") was successfully unregistered."
        else :
            _attr_list ={}
            _msg = "This hypervisor (" + node_name + ") was already unregistered."

        return self.success(_msg, _attr_list)

    def node_resource_update(self, node_uuid, node_hostname, kword, vcpus, vmem) :
        '''
        TBD
        '''
        self.redis_conn_check()
        _vcpus = self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                         "COMPUTENODE", \
                                                         node_uuid, \
                                                         False, \
                                                         "vcpus", \
                                                         vcpus, \
                                                         True)

        _vmem = self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                        "COMPUTENODE", \
                                                        node_uuid, \
                                                        False, \
                                                        "vmem", \
                                                        vmem, \
                                                        True)

        if kword == "increased" :
            _instances = 1
        elif kword == "decreased" :
            _instances = -1   

        self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                "COMPUTENODE", \
                                                node_uuid, \
                                                False, \
                                                "instances", \
                                                _instances, \
                                                True)

        _msg = "Resource usage updated (" + kword + ") on compute node \""
        _msg += node_hostname + "\""
        cbdebug(_msg)

        return _vcpus, _vmem
        
    @trace
    def instance_placement(self, group, computenode_name, operation, vcpus, vmem) :
        '''
        TBD
        '''
        self.redis_conn_check()

        if operation == "run" :
            if not computenode_name :
                _group_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                            "GROUP", \
                                                            group, \
                                                            True)

                if _group_uuid :
                    _group_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                  "GROUP", \
                                                                  False, \
                                                                  _group_uuid, \
                                                                  False)

                    computenode_name = choice(_group_attr_list["computenodes"].split(','))
                else :
                    _msg = "Group \"" + group + "\" data not found." 
                    self.PLMraise("localhost", 998, _msg)
            _kword = "increased"
        else :
            vcpus = -int(vcpus)
            vmem = -int(vmem)
            _kword = "decreased"

        _computenode_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                          "COMPUTENODE", \
                                                          computenode_name, \
                                                          True)
    
        if _computenode_uuid :
            _msg = "A suitable compute node (" + computenode_name + ") was selected"
            cbdebug(_msg)

            _computenode_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                "COMPUTENODE", \
                                                                False, \
                                                                _computenode_uuid, \
                                                                False)
        else :
            _msg = "Hypervisor node \"" + computenode_name + "\" not found."
            self.PLMraise("localhost", 997, _msg)    
        
        self.node_resource_update(_computenode_uuid, \
                                  _computenode_attr_list["cloud_hostname"], \
                                  _kword, vcpus, vmem)

        return _computenode_attr_list["cloud_hostname"], _computenode_attr_list["cloud_ip"], _computenode_attr_list["group"]

    def instance_run(self, imageids, tag, userid, group, instance_lvirt_obj = False, \
                     host_name = None, size = "micro32", \
                     vmclass = "standard", eclipsed_size = None, \
                     eclipsed = False, qemu_debug_port = None, \
                     svm_qemu_debug_port = None, \
                     replication_port = None, svm_stub_ip = None, \
                     cloud_mac = None, root_disk_format = "qcow2") :
        '''
        TBD
        '''

        _instance_attr_list = {}
        _instance_attr_list["notification"] = "False"
        _instance_attr_list["cloud_ip"] = "NA"
        _instance_attr_list["cloud_hostname"] = "NA"
        _instance_attr_list["root_disk_format"] = root_disk_format
        _instance_attr_list["hypervisor"] = options.hypervisor

        if instance_lvirt_obj :
            _node_name, _node_uuid = host_name.split('|')
            _instance_attr_list["host_name"], \
            _instance_attr_list["host_ip"] = hostname2ip(_node_name)
                
            _instance_attr_list["cloud_ip"] = "NA"
            _instance_attr_list["host_uuid"] = _node_uuid
            _instance_attr_list["group"] = group
            _instance_attr_list["size"] = "NA"
            _instance_attr_list["class"] = "NA"
            _instance_attr_list["cloud_lvid"] = tag
            if _instance_attr_list["cloud_lvid"].count("plm-") :
                _instance_attr_list["creator"] = "PLM"
                self.redis_conn.update_counter(self.oscp["cluster_name"], \
                                               "COUNTER", \
                                               "INSTANCES", \
                                               "increment")
            else :
                _instance_attr_list["creator"] = "other"              

        else :
            _instance_attr_list["group_name"] = group
            _instance_attr_list["size"] = size
            _instance_attr_list["class"] = vmclass
            _instance_attr_list["userid"] = userid
            
            if not cloud_mac :
                _instance_attr_list["cloud_mac"] = self.generate_mac_addr(_instance_attr_list["userid"])
            else : 
                _instance_attr_list["cloud_mac"] = cloud_mac
            _instance_attr_list["cloud_lvid"] = tag + '-' + _instance_attr_list["cloud_mac"].replace(':','')
            _instance_attr_list["cloud_uuid"] = str(uuid5(NAMESPACE_DNS, \
                                                          _instance_attr_list["cloud_lvid"])).upper()
            _instance_attr_list["creator"] = "PLM"
            
            if svm_stub_ip is None :
                if eclipsed and eclipsed_size is not None :
                    _instance_attr_list["size"] = eclipsed_size 
                    _instance_attr_list["configured_size"] = size 
                    _instance_attr_list["vcpus_configured"] = self.vhw_config[_instance_attr_list[size]]["vcpus"]
                    _instance_attr_list["vmemory_configured"] = self.vhw_config[_instance_attr_list[size]]["vmemory"]
    
            _instance_attr_list.update(self.vhw_config[_instance_attr_list["size"]])
            _instance_attr_list.update(self.vhw_config[_instance_attr_list["class"]])
                
            _instance_attr_list["host_name"], \
            _instance_attr_list["host_ip"], \
            _instance_attr_list["group"] = \
            self.instance_placement(group, \
                                    host_name, \
                                    "run", \
                                    _instance_attr_list["vcpus"], \
                                    _instance_attr_list["vmem"])

            _instance_attr_list["imageids"] = len(imageids)
            
            _instance_attr_list["replication_port"] = replication_port
            _instance_attr_list["qemu_debug_port"] = qemu_debug_port
            _instance_attr_list["svm_qemu_debug_port"] = svm_qemu_debug_port
            _instance_attr_list["svm_stub_ip"] = svm_stub_ip
            
            # cpython thread is serial, so this is OK
            if svm_stub_ip is not None:
                try :
                    import libvirt_qemu
                except ImportError:
                    self.PLMraise(_instance_attr_list["host_ip"], 100, \
                         "The 'libvirt_qemu' python client-side bindings " + \
                         "(RHEL 6.2 and higher) are not available. " + \
                         "Cannot perform FT replication.")                

            lvt_cnt = self.lvirt_conn_check(_instance_attr_list["host_ip"])
            _graceful = False
    
            if self.is_domain_defined(lvt_cnt, _instance_attr_list["cloud_lvid"]) :
                self.destroy_and_undefine_domain(lvt_cnt, _instance_attr_list["cloud_lvid"], _graceful)

            _volume_paths = []

            ## FIX ME
            if svm_stub_ip is not None :
                self.restart_pool(lvt_cnt, options.file_snapshot_storagepool)
            ## FIX ME
            
            if root_disk_format == "qcow2" :
                _storage_pool = options.file_base_storagepool
            elif root_disk_format == "raw" :
                _storage_pool = options.volume_base_storagepool

            for _imageid in imageids :
                _external_imageid = _instance_attr_list["host_name"] + '.'
                _external_imageid += _storage_pool + '.' + _imageid

                _volume_attr_list = self.volume_create(tag, \
                                                       _instance_attr_list["host_ip"], \
                                                       _storage_pool, \
                                                       _external_imageid)["result"]

                _volume_paths.append(_volume_attr_list["path"])

            _xml_template = self.generate_libvirt_vm_template(_volume_paths, _instance_attr_list)

            self.create_domain(lvt_cnt, _xml_template, \
                               _instance_attr_list["cloud_lvid"], \
                               True if svm_stub_ip is not None else False)

        _extra_attr = self.get_domain_info(self.lvirt_conn_check(_instance_attr_list["host_ip"]),\
                                            _instance_attr_list["cloud_lvid"])

        _instance_attr_list.update(_extra_attr)
    
        self.redis_conn_check()

        for _volcount in range(0,_instance_attr_list["volumes"]) :
            _vol_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                      "VOLUME", \
                                                      _instance_attr_list["volume_uuid" + str(_volcount)], \
                                                      False)

            if _vol_uuid :
                _vol_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                            "VOLUME", \
                                                            False, \
                                                            _vol_uuid, \
                                                            False)

                _instance_attr_list["volume_lvid" + str(_volcount)] = _vol_attr_list["cloud_lvid"]

                self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                        "VOLUME", \
                                                        _vol_uuid, \
                                                        False, \
                                                        "instance_uuid", \
                                                        _instance_attr_list["cloud_uuid"])

                self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                        "VOLUME", \
                                                        _vol_uuid, \
                                                        False, \
                                                        "instance_lvid", \
                                                        _instance_attr_list["cloud_lvid"])
        
        _instance_attr_list["name"] = _instance_attr_list["cloud_lvid"]

        self.redis_conn.create_object(self.oscp["cluster_name"], \
                                      "INSTANCE", \
                                      _instance_attr_list["cloud_uuid"], \
                                      _instance_attr_list, 
                                      False, \
                                      False)

        self.redis_conn.add_to_list(self.oscp["cluster_name"], \
                                    "INSTANCELIST", _instance_attr_list["host_name"], \
                                    _instance_attr_list["cloud_uuid"] + '|' +\
                                     _instance_attr_list["cloud_lvid"])

        _msg = "Instance \"" + _instance_attr_list["cloud_lvid"] + "\" ("
        _msg += _instance_attr_list["cloud_uuid"] + ") was successfully "
        _msg += "started (on compute node \"" + _instance_attr_list["host_name"] + "\")."

        return self.success(_msg, _instance_attr_list)

    def instances_describe(self, tag = "all") :
        '''
        TBD
        '''
        self.redis_conn_check()
        _instances_attr_list = {}

        if tag != "all" :
            _instance_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                           "INSTANCE", \
                                                           tag, \
                                                           True)

            if _instance_uuid :
                _instance_uuids = [_instance_uuid]
            else :
                _instance_uuids = False
                _msg = "Instance \"" + tag + "\" was not provisioned on this Parallel Libvirt Manager"
        else :
            _instance_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], \
                                                              "INSTANCE")
            if not _instance_uuids :
                _msg = "No instances currently provisioned on this Parallel Libvirt Manager"

        if _instance_uuids :
            for _instance_uuid in _instance_uuids :
                _instances_attr_list[_instance_uuid] = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                                  "INSTANCE", \
                                                                                  False, \
                                                                                  _instance_uuid, \
                                                                                  False)

                if _instances_attr_list[_instance_uuid]["cloud_ip"] == "NA" \
                and "cloud_mac" in _instances_attr_list[_instance_uuid] and \
                 _instances_attr_list[_instance_uuid]["cloud_mac"] != "NA" :
                    _msg = "Updating IP address on instance \"" + _instances_attr_list[_instance_uuid]["cloud_lvid"] + "\"..."
                    cbdebug(_msg)
                    _instance_ip = self.get_ip_address(_instances_attr_list[_instance_uuid]["cloud_mac"])
                    if _instance_ip :
                        self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                                "INSTANCE", \
                                                                _instance_uuid, \
                                                                False, \
                                                                "cloud_ip", \
                                                                _instance_ip)

                        self.redis_conn.tag_object(self.oscp["cluster_name"], \
                                                   "CLOUD_IP", \
                                                   _instance_ip, \
                                                   "INSTANCE", \
                                                   _instance_uuid)
                        
                        _instances_attr_list[_instance_uuid]["cloud_ip"] = _instance_ip
                        _msg = "IP address (" +  _instance_ip + ") for instance "
                        _msg += "\"" + _instances_attr_list[_instance_uuid]["cloud_lvid"] 
                        _msg += "\" updated successfully"
                        cbdebug(_msg)
                    else :
                        _msg = "IP address for instance \"" 
                        _msg += _instances_attr_list[_instance_uuid]["cloud_lvid"] 
                        _msg += "\" still not available"
                        cbdebug(_msg)

            _msg = "Instance data found"

        return self.success(_msg, _instances_attr_list)

    def instance_alter_state(self, tag, target_state) :
        '''
        TBD
        '''
        self.redis_conn_check()

        _instance_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                       "INSTANCE", tag, True)
        
        if _instance_uuid :
            _instance_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                             "INSTANCE", \
                                                             False, \
                                                             _instance_uuid, \
                                                             False)

            lvt_cnt = self.lvirt_conn_check(_instance_attr_list["host_ip"])
            _extra_attr = self.get_domain_info(lvt_cnt, _instance_attr_list["cloud_lvid"])
            
            _current_state = _extra_attr["state"]

            if _current_state == "paused"  and target_state == "resume" :
                self.alterstate_instance(lvt_cnt, tag, target_state)

            elif _current_state == "save" and target_state == "restore" :
                if options.hypervisor == "kvm" :
                    self.alterstate_instance(lvt_cnt, tag, target_state)
                elif options.hypervisor == "xen" :
                    _state_save_file = options.state_save_storage + '/' + tag
                    self.alterstate_instance(lvt_cnt, tag, target_state, _state_save_file)

            elif _current_state == "running" and (target_state == "suspend" or target_state == "save") :
                if options.hypervisor == "kvm" :
                    self.alterstate_instance(lvt_cnt, tag, target_state)
                elif options.hypervisor == "xen" :
                    _state_save_file = options.state_save_storage + '/' + tag
                    self.alterstate_instance(lvt_cnt, tag, target_state, _state_save_file)
            else : 
                _msg = "Instance \"" + _instance_attr_list["cloud_lvid"] + "\" ("
                _msg += _instance_attr_list["cloud_uuid"] + ") could not be changed"
                _msg += "changed from \"" + _current_state + "\" to \"" + target_state
                _msg += "\" (on compute node \"" + _instance_attr_list["host_name"] + "\")."

            _msg = "Instance \"" + _instance_attr_list["cloud_lvid"] + "\" ("
            _msg += _instance_attr_list["cloud_uuid"] + ") had its state successfully"
            _msg += " changed from \"" + _current_state + "\" to \"" + target_state
            _msg += "\" (on compute node \"" + _instance_attr_list["host_name"] + "\")."

            _extra_attr = self.get_domain_info(lvt_cnt, _instance_attr_list["cloud_lvid"])
            
            _instance_attr_list["state"] = _extra_attr["state"]
            self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                    "INSTANCE", \
                                                    _instance_uuid, \
                                                    False, \
                                                    "state", \
                                                    _extra_attr["state"])  

            return self.success(_msg, _instance_attr_list)        
        else :
            _msg = "Instance \"" + tag + "\" data not found."
            return self.error(199, _msg, None)        

    @trace        
    def instance_destroy(self, tag) :
        '''
        TBD
        '''

        self.redis_conn_check()
        
        _instance_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                       "INSTANCE", tag, True)
            
        if _instance_uuid :
            
            _instance_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                             "INSTANCE", \
                                                             False, \
                                                             _instance_uuid, \
                                                             False)

            if _instance_attr_list["creator"] == "PLM" :
                lvt_cnt = self.lvirt_conn_check(_instance_attr_list["host_ip"])
                self.destroy_and_undefine_domain(lvt_cnt, tag, False)
                
                for _volcount in range(0, int(_instance_attr_list["volumes"])) :
                    if "volume_uuid" + str(_volcount) in _instance_attr_list :
                        self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                                "VOLUME", \
                                                                _instance_attr_list["volume_uuid" + str(_volcount)], \
                                                                False, \
                                                                "instance_lvid", \
                                                                "none")

                    if "volume_lvid" + str(_volcount) in _instance_attr_list :
                        self.volume_destroy(_instance_attr_list["volume_lvid" + str(_volcount)])
    
                self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                               "INSTANCE", \
                                               _instance_uuid, \
                                               _instance_attr_list, \
                                               False)

                self.redis_conn.remove_from_list(self.oscp["cluster_name"], \
                                                 "INSTANCELIST", \
                                                 _instance_attr_list["host_name"], \
                                                 _instance_attr_list["cloud_uuid"] + '|' +\
                                                  _instance_attr_list["cloud_lvid"])
    
                self.instance_placement(_instance_attr_list["group"], \
                                        _instance_attr_list["host_name"], \
                                        "terminate", \
                                        _instance_attr_list["vcpus"], \
                                        str(int(_instance_attr_list["vmem"])/1024))

                _msg = "Instance \"" + _instance_attr_list["cloud_lvid"] + "\" ("
                _msg += _instance_attr_list["cloud_uuid"] + ") was successfully "
                _msg += "terminated (on compute node \"" + _instance_attr_list["host_name"] + "\")."
                return self.success(_msg, _instance_attr_list)
            else :
                _msg = "Instance \"" + _instance_attr_list["cloud_lvid"] + "\" ("
                _msg += _instance_attr_list["cloud_uuid"] + ") was not created "
                _msg += "by PLM..... It cannot be terminated by it."
                return self.success(_msg, _instance_attr_list)
        else :
            _msg = "Instance \"" + tag + "\" data not found. There is no need to"
            _msg += " terminate it."
            return self.success(_msg, None)

    def storagepool_create(self, tag, node_name, pool_format, dir_name = None, \
                           dev_name = None, _storage_pool_lvirt_obj = False, pre_existing = False) :
        '''
        TBD
        '''
        self.redis_conn_check()

        _storagepool_attr_list = {}
        _storagepool_attr_list["notification"] = "False"
        
        _storagepool_attr_list["host_name"], _storagepool_attr_list["host_ip"] = \
        hostname2ip(node_name)

        _storage_pool_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                           "STORAGEPOOL", \
                                                           tag, \
                                                           True)

        if _storage_pool_lvirt_obj :

            _actual_storage_pool = tag.replace(_storagepool_attr_list["host_name"] + '.', '')
            
            _storagepool_attr_list.update(self.get_storage_pool_info(self.lvirt_conn_check(_storagepool_attr_list["host_ip"]), \
                                                                 _actual_storage_pool, \
                                                                 _storage_pool_lvirt_obj))

            _create_storagepoold = True
            _storagepool_attr_list["host_uuid"] = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                                                "COMPUTENODE", \
                                                                                _storagepool_attr_list["host_name"], \
                                                                                True)

            _storagepool_attr_list["cloud_lvid"] = _storagepool_attr_list["host_name"]  + '.' + tag

            if _storagepool_attr_list["cloud_lvid"].count("plm-") :
                _storagepool_attr_list["creator"] = "PLM"
                self.redis_conn.update_counter(self.oscp["cluster_name"], \
                                               "COUNTER", \
                                               "STORAGEPOOLS", \
                                               "increment")
            else :
                _storagepool_attr_list["creator"] = "other"   
            
        else :
            _counter = str(self.redis_conn.update_counter(self.oscp["cluster_name"], \
                                                          "COUNTER", \
                                                          "STORAGEPOOLS", \
                                                          "increment"))

            if pool_format == "directory" :          
                if dir_name == options.file_base_storage :
                    _path_xml_file = options.file_base_storage
                elif dir_name == options.file_snapshot_storage :
                    _path_xml_file = options.file_snapshot_storage
                else :
                    tag = tag + _counter
                    dir_name = dir_name + _counter
                    _path_xml_file = options.file_base_storage + "/" + dir_name

                if _storage_pool_uuid :
                    _msg = "Storage Pool \"" + _storagepool_attr_list["cloud_lvid"] + "\" ("
                    _msg += _storage_pool_uuid + ") is already created (on node \""
                    _msg += _storagepool_attr_list["host_name"] + "\"). Please destroy it first."
        
                else :
                    _storagepool_attr_list["cloud_lvid"] = _storagepool_attr_list["host_name"]  + '.' + tag
                    _storage_pool_xml_file = ""
                    _storage_pool_xml_file += "<pool type='dir'>\n" 
                    _storage_pool_xml_file += "<name>" + tag + "</name>\n"
                    _storage_pool_xml_file += "<target>\n"
                    _storage_pool_xml_file += "<path>" + _path_xml_file + "</path>\n"
                    _storage_pool_xml_file += "<permissions>\n"
                    _storage_pool_xml_file += "<mode>0777</mode>\n"
                    _storage_pool_xml_file += "</permissions>"
                    _storage_pool_xml_file += "</target>\n"
                    _storage_pool_xml_file += "</pool>" 

            elif pool_format == "logical" :
                
                if dev_name == options.volume_base_storage :
                    _path_xml_file = options.volume_base_storage
                elif dev_name == options.volume_snapshot_storage :
                    _path_xml_file = options.volume_snapshot_storage
                else :
                    tag = tag + _counter
                    _path_xml_file = dev_name

                if not pre_existing :
                    _proc_man = ProcessManagement(hostname =  _storagepool_attr_list["host_ip"])
    
                    _dev_name_used_cmd = "pvdisplay -c | grep ':' | grep -v orphans_lvm2 | grep -c " + _path_xml_file
                    _status, _dev_name_used, _result_stderr = _proc_man.run_os_command(_dev_name_used_cmd)
    
                    if _dev_name_used.strip() != "0" :
                        _dev_name_belongs_to_vg_cmd = "pvdisplay -c | grep ':' | grep " + tag + " | grep -c " + _path_xml_file
                        _status, _dev_name_belongs_to_vg, _result_stderr = _proc_man.run_os_command(_dev_name_belongs_to_vg_cmd)
                        
                        if _dev_name_belongs_to_vg.strip() != "0" :
                            pre_existing = True
                        else :
                            _msg = "This device (" + _path_xml_file + ") is "
                            _msg += "already part of another Volume Group. Destroy"
                            _msg += " it first."
                            cberr(_msg)
                            self.PLMraise("local", 635, str(_msg)) 
                    else :
                        pre_existing = False
 
                _storagepool_attr_list["cloud_lvid"] = _storagepool_attr_list["host_name"]  + '.' + tag
                _storage_pool_xml_file = ""
                _storage_pool_xml_file += "<pool type='logical'>\n"
                _storage_pool_xml_file += "  <name>" + tag + "</name>\n"
                _storage_pool_xml_file += "  <source>\n"
                if pre_existing :
                    _storage_pool_xml_file += "    <name>" + _path_xml_file + "</name>\n"
                else :
                    _storage_pool_xml_file += "    <device path='" + _path_xml_file + "'/>\n"
                _storage_pool_xml_file += "    <format type='lvm2'/>\n"
                _storage_pool_xml_file += "  </source>\n"
                _storage_pool_xml_file += "  <target>\n"
                if pre_existing :
                    _storage_pool_xml_file += "    <path>/dev/" + _path_xml_file + "</path>\n"
                else :
                    _storage_pool_xml_file += "    <path>/dev/" + tag + "</path>\n"
                _storage_pool_xml_file += "  </target>\n"
                _storage_pool_xml_file += "</pool>\n"

            _storagepool_attr_list["creator"] = "PLM"

            _create_storagepool = self.create_storagepool(self.lvirt_conn_check(_storagepool_attr_list["host_ip"]), \
                                                             tag, \
                                                             _storage_pool_xml_file, \
                                                             pre_existing)
    
            _storagepool_attr_list.update(self.get_storage_pool_info(self.lvirt_conn_check(_storagepool_attr_list["host_ip"]), \
                                                                 tag, \
                                                                 _storage_pool_lvirt_obj))
    
            if _create_storagepool :
                _storagepool_attr_list["instance_lvid"] = "none"

                _storagepool_attr_list["name"] = _storagepool_attr_list["cloud_lvid"]
                                
                self.redis_conn.create_object(self.oscp["cluster_name"], \
                                              "STORAGEPOOL", \
                                              _storagepool_attr_list["cloud_uuid"], \
                                              _storagepool_attr_list, \
                                              False, \
                                              False)
    
                _msg = "Storage Pool \"" + _storagepool_attr_list["cloud_lvid"] + "\" ("
                _msg += _storagepool_attr_list["cloud_uuid"] + ") was successfully created (on node \""
                _msg += _storagepool_attr_list["host_name"] + "\")"
            
        return self.success(_msg, _storagepool_attr_list)

    def storagepools_describe(self, tag = "all") :
        '''
        TBD
        '''
        self.redis_conn_check()
        _storage_pools_attr_list = {}

        if tag != "all" :
            _storage_pool_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                               "STORAGEPOOL", \
                                                               tag, \
                                                               True)
            if _storage_pool_uuid :
                _storage_pool_uuids = [_storage_pool_uuid]
            else :
                _storage_pool_uuids = False
                _msg = "Storage Pool \"" + tag + "\" was not created on this Parallel Libvirt Manager"
        else :
            _storage_pool_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], \
                                                                  "STORAGEPOOL")
            if not _storage_pool_uuids :
                _msg = "No volumes currently created on this Parallel Libvirt Manager"
                
        if _storage_pool_uuids :
            for _storage_pool_uuid in _storage_pool_uuids :
                _storage_pools_attr_list[_storage_pool_uuid] = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                                          "STORAGEPOOL", \
                                                                                          False, \
                                                                                          _storage_pool_uuid, \
                                                                                          False)
            _msg = "Storage pool data found."

        return self.success(_msg, _storage_pools_attr_list)

    def storagepool_destroy(self, tag) :
        '''
        TBD
        '''
        self.redis_conn_check()

        _storage_pool_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                           "STORAGEPOOL", \
                                                           tag, \
                                                           True)

        if _storage_pool_uuid :
            _storagepool_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                "STORAGEPOOL", \
                                                                False, \
                                                                _storage_pool_uuid, \
                                                                False)
            if _storagepool_attr_list["volumes"] == "0" :
                
                _actual_storagepool_tag = tag.replace(_storagepool_attr_list["host_name"] + '.', '')
                
                self.destroy_storagepool(self.lvirt_conn_check(_storagepool_attr_list["host_ip"]), _actual_storagepool_tag)

                _proc_man = ProcessManagement(hostname =  _storagepool_attr_list["host_ip"])

                if _storagepool_attr_list["type"] == "block" :
                    _cleanup_remote_cmd = "vgremove " + _actual_storagepool_tag
                else :
                    _cleanup_remote_cmd = "rm -rf  " + _storagepool_attr_list["path"]
                _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cleanup_remote_cmd)

#                if _status :
#                    _msg = "Error"
#                    cberr(_msg)
#                    self.PLMraise("local", 635, str(_msg)) 

                self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                               "STORAGEPOOL", \
                                               _storage_pool_uuid, \
                                               _storagepool_attr_list, \
                                               False)
                
                _msg = "Storage Pool \"" + _storagepool_attr_list["cloud_lvid"] + "\" ("
                _msg += _storagepool_attr_list["cloud_uuid"] + ") was successfully "
                _msg += "destroyed (on compute node \"" + _storagepool_attr_list["host_name"] + "\")."
                return self.success(_msg, _storagepool_attr_list)

            else :
                _msg = "Storage Pool \"" + _storagepool_attr_list["cloud_lvid"] + "\" ("
                _msg += _storagepool_attr_list["cloud_uuid"] + ") still has volumes"
                _msg += " (" + _storagepool_attr_list["volumes"] + " defined "
                _msg += "please destroy them first."
                return self.success(_msg, _storagepool_attr_list)
        else :
            _msg = "Storage Pool \"" + tag + "\" data not "
            _msg += "found. There is no need to destroy it."
            return self.success(_msg, None)

    def volume_create(self, tag, node_name, storage_pool, snapvol_tag = False, \
                      volume_lvirt_obj = False, volcapacity = "2147483648") :
        '''
        TBD
        '''
        self.redis_conn_check()

        _vol_attr_list = {}
        _vol_attr_list["notification"] = "False"        
        _vol_attr_list["host_name"], _vol_attr_list["host_ip"] = \
        hostname2ip(node_name)

        _volume_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                     "VOLUME", \
                                                     tag, \
                                                     True)

        _actual_storage_pool = storage_pool.replace(_vol_attr_list["host_name"] + '.', '')

        if volume_lvirt_obj :
            _vol_attr_list.update(self.get_volume_info(self.lvirt_conn_check(_vol_attr_list["host_ip"]), \
                                                      tag, _actual_storage_pool, \
                                                      volume_lvirt_obj))
            _volume_created = True

            # Note: obj_exists returns the UUID for existing objects            
            _vol_attr_list["host_uuid"] = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                                        "COMPUTENODE", \
                                                                        _vol_attr_list["host_name"], \
                                                                        True)

            _vol_attr_list["cloud_lvid"] = _vol_attr_list["host_name"]  + '.' + _actual_storage_pool + '.' + tag

            if _vol_attr_list["cloud_lvid"].count("plm-") :

                _vol_attr_list["creator"] = "PLM"
                self.redis_conn.update_counter(self.oscp["cluster_name"], \
                                               "COUNTER", "VOLUMES", "increment")
            else :
                _vol_attr_list["creator"] = "other"   

        else :

            if self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                             "STORAGEPOOL", \
                                             _vol_attr_list["host_name"] + \
                                             '.' + _actual_storage_pool, True) :

                _storagepool_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                    "STORAGEPOOL", \
                                                                    True, \
                                                                    _vol_attr_list["host_name"] +\
                                                                     '.' + _actual_storage_pool, \
                                                                     False)
            else :
                _msg = "The Storage Pool \"" + _actual_storage_pool + "\" does not"
                _msg += "exist in Host \"" + _vol_attr_list["host_name"] + "\""
                self.PLMraise(_vol_attr_list["host_name"], 736, _msg)

            _vol_attr_list["type"] = _storagepool_attr_list["type"]           
            tag = tag + str(self.redis_conn.update_counter(self.oscp["cluster_name"], \
                                                           "COUNTER", \
                                                           "VOLUMES", \
                                                           "increment"))

            if snapvol_tag :
                if self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                 "VOLUME", snapvol_tag, True) :

                    _snapvol_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                    "VOLUME", True,\
                                                                     snapvol_tag, \
                                                                     False)

                    _actual_snapvol_tag = snapvol_tag.replace(_snapvol_attr_list["host_name"] + '.', '')
                    _actual_snapvol_tag = _actual_snapvol_tag.replace(_snapvol_attr_list["storage_pool"] + '.', '')

                    tag = _actual_snapvol_tag + '-' + tag

                    _vol_attr_list["capacity"] = _snapvol_attr_list["capacity"]

                    if _vol_attr_list["type"] == "file" :
                        _vol_attr_list["format"] = "qcow2"
                    else :
                        _vol_attr_list["format"] = "raw"
                else :
                    _msg = "The base volume \"" + snapvol_tag + "\" does not exist"
                    self.PLMraise(_vol_attr_list["host_name"], 898, _msg)            
            else :
                _vol_attr_list["cloud_lvid"] = tag
                _vol_attr_list["capacity"] = volcapacity
                _vol_attr_list["format"] = "raw"

            if snapvol_tag :
                _actual_storage_pool = _actual_storage_pool.replace("base","snapshot")

            _storpool_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                             "STORAGEPOOL", \
                                                             True,\
                                                              _vol_attr_list["host_name"] + '.' + _actual_storage_pool, \
                                                              False)

            _vol_attr_list["cloud_lvid"] = _vol_attr_list["host_name"]  + '.' + _actual_storage_pool + '.' + tag    
            _vol_attr_list["path"] = _storpool_attr_list["path"] + '/' + _vol_attr_list["cloud_lvid"]
                
            _vol_attr_list["storage_pool_uuid"] = _storpool_attr_list["cloud_uuid"]

            if _volume_uuid :
                _msg = "Volume \"" + _vol_attr_list["cloud_lvid"] + "\" ("
                _msg += _volume_uuid + ") is already created (on node \""
                _msg += _vol_attr_list["host_name"] + "\"). Please destroy it first."
    
            else :
                _vol_xml_file = ""
                _vol_xml_file += "\t<volume>\n"
                _vol_xml_file += "\t<name>" + tag + "</name>\n"
                _vol_xml_file += "\t<capacity>" + _vol_attr_list["capacity"] + "</capacity>\n"
                _vol_xml_file += "\t<target>\n"
                _vol_xml_file += "\t\t<permissions>\n"
                _vol_xml_file += "\t\t\t<mode>0777</mode>\n"
                _vol_xml_file += "\t\t</permissions>\n"
                _vol_xml_file += "\t\t<path>" + _vol_attr_list["path"] + "</path>\n"
                _vol_xml_file += "\t\t<format type='" + _vol_attr_list["format"]  + "'/>\n"
                _vol_xml_file += "\t</target>\n"
                if snapvol_tag :
                    _vol_xml_file += "\t<backingStore>\n"
                    _vol_xml_file += "\t\t<path>" + _snapvol_attr_list["path"] + "</path>\n"
                    _vol_xml_file += "\t\t<format type='" + _snapvol_attr_list["format"] + "'/>\n"
                    _vol_xml_file += "\t</backingStore>\n"
                _vol_xml_file += "\t</volume>\n"

            _vol_attr_list["creator"] = "PLM"            
            _volume_created = self.create_volume(self.lvirt_conn_check(_vol_attr_list["host_ip"]), \
                                                 tag, _actual_storage_pool, \
                                                 _vol_xml_file)

            _vol_attr_list.update(self.get_volume_info(self.lvirt_conn_check(_vol_attr_list["host_ip"]), \
                                                       tag, \
                                                       _actual_storage_pool))

        if _volume_created :

            _vol_attr_list["instance_lvid"] = "none"
            if _vol_attr_list["type"] == "directory" and _vol_attr_list["cloud_lvid"].count("cb") :
                True
            else :
                _vol_attr_list["name"] = _vol_attr_list["cloud_lvid"]

                self.redis_conn.create_object(self.oscp["cluster_name"], \
                                              "VOLUME", \
                                              _vol_attr_list["cloud_uuid"], \
                                              _vol_attr_list, \
                                              False, \
                                              False)

                if "storage_pool_uuid" in _vol_attr_list :

                    self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                            "STORAGEPOOL", \
                                                             _vol_attr_list["storage_pool_uuid"], \
                                                             False, \
                                                             "volumes", \
                                                             1, \
                                                             True)

            _msg = "Volume \"" + _vol_attr_list["cloud_lvid"] + "\" ("
            _msg += _vol_attr_list["cloud_uuid"] + ") was successfully created (on node \""
            _msg += _vol_attr_list["host_name"] + "\")"

        return self.success(_msg, _vol_attr_list)

    def volumes_describe(self, tag = "all") :
        '''
        TBD
        '''
        self.redis_conn_check()
        _vols_attr_list = {}

        if tag != "all" :
            _volume_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                         "VOLUME", tag, True)
            if _volume_uuid :
                _volume_uuids = [_volume_uuid]
            else :
                _volume_uuids = False
                _msg = "Volume \"" + tag + "\" was not created on this Parallel Libvirt Manager"
        else :
            _volume_uuids = self.redis_conn.get_object_list(self.oscp["cluster_name"], \
                                                            "VOLUME")
            if not _volume_uuids :
                _msg = "No volumes currently created on this Parallel Libvirt Manager"
                
        if _volume_uuids :
            for _volume_uuid in _volume_uuids :
                _vols_attr_list[_volume_uuid] = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                                           "VOLUME", \
                                                                           False, \
                                                                           _volume_uuid, 
                                                                           False)
            _msg = "Volume data found"

        return self.success(_msg, _vols_attr_list)

    def volume_destroy(self, tag) :
        '''
        TBD
        '''
        self.redis_conn_check()

        _volume_uuid = self.redis_conn.object_exists(self.oscp["cluster_name"], \
                                                     "VOLUME", tag, True)

        if _volume_uuid :

            _vol_attr_list = self.redis_conn.get_object(self.oscp["cluster_name"], \
                                                        "VOLUME", False, \
                                                        _volume_uuid, False)
            
            if _vol_attr_list["instance_lvid"] == "none" :

                _actual_volume_tag = tag.replace(_vol_attr_list["host_name"] + '.', '')
                _actual_volume_tag = _actual_volume_tag.replace(_vol_attr_list["storage_pool"] + '.', '')
                
                self.destroy_volume(self.lvirt_conn_check(_vol_attr_list["host_ip"]), \
                                    _actual_volume_tag, _vol_attr_list["storage_pool"])

                self.redis_conn.destroy_object(self.oscp["cluster_name"], \
                                               "VOLUME", \
                                               _volume_uuid, \
                                               _vol_attr_list, \
                                               False)

                if "storage_pool_uuid" in _vol_attr_list :
                    self.redis_conn.update_object_attribute(self.oscp["cluster_name"], \
                                                            "STORAGEPOOL", \
                                                             _vol_attr_list["storage_pool_uuid"], \
                                                             False, \
                                                             "volumes", -1, True)

                _msg = "Volume \"" + _vol_attr_list["cloud_lvid"] + "\" ("
                _msg += _vol_attr_list["cloud_uuid"] + ") was successfully "
                _msg += "destroyed (on compute node \"" + _vol_attr_list["host_name"] + "\")."
                return self.success(_msg, _vol_attr_list)

            else :
                _msg = "Volume \"" + _vol_attr_list["cloud_lvid"] + "\" ("
                _msg += _vol_attr_list["cloud_uuid"] + ") is atPLMhed to "
                _msg += "instance " + _vol_attr_list["instance_lvid"] + ". "
                _msg += "please terminate it instead. "
                return self.success(_msg, _vol_attr_list)
        else :
            _msg = "Volume \"" + tag + "\" data not "
            _msg += "found. There is no need to destroy it."
            return self.success(_msg, None)

    '''
    Lower-level functions, interacting directly with libvirt
    '''
    
    def get_host_info(self, lvirt_conn) :
        '''
        TBD
        '''
        _host_info_dict = {}   
        _imsg = "Information about libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            cpu_info = lvirt_conn.getInfo()
        except libvirtError, msg : 
            self.PLMraise(lvirt_conn.host, 3, _fmsg + ": " + str(msg))
            
        _host_info_dict["pcpu_arch"] = cpu_info[0]
        _host_info_dict["pmem"] = cpu_info[1] 
        _host_info_dict["pcpus"] = int(cpu_info[2])
        _host_info_dict["pcpu_freq"] = cpu_info[3]
        _host_info_dict["threads_per_pcpu"] = cpu_info[4]
        _host_info_dict["pcpu_sockets"] = cpu_info[5]
        _host_info_dict["pcpus_per_socket"] = cpu_info[6]
        _host_info_dict["numa_cells"] = cpu_info[7]
        _host_info_dict["uuid"] = False
           
        try :
            _system_info = lvirt_conn.getSysinfo(0)
            for key in _system_info.split('\n') :
                if key.count("uuid") :
                    _host_info_dict["uuid"] = split('<|>', key)[2]
            cbdebug(_smsg)
            return _host_info_dict

        # START HACK ALERT    
        except libvirtError, msg:
            _msg = "Unable to get asset information about the host "
            _msg += lvirt_conn.host + ": " + str(msg)
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
            return _host_info_dict

    @trace
    def list_domains(self, lvirt_conn, defined = False, pattern = None) :
        '''
        TBD
        '''
        _domains = {}
        _imsg = "Domain list for libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            if defined :
                for _tag in lvirt_conn.listDefinedDomains() :
                    _dom = lvirt_conn.lookupByName(_tag)
                    if pattern :
                        if not _tag.count(pattern) :
                            continue
                        else :
                            _domains[_dom.name()] = _dom
                    else :
                        _domains[_dom.name()] = _dom

            for _dom_id in lvirt_conn.listDomainsID() :
                _dom = lvirt_conn.lookupByID(_dom_id)
                if pattern :
                    if not _dom.name().count(pattern) :
                        continue
                    else :
                        _domains[_dom.name()] = _dom
                else :
                    _domains[_dom.name()] = _dom

            cbdebug(_smsg)
            return _domains
            
        except libvirtError, msg : 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace    
    def get_domain_info(self, lvirt_conn, tag, instance_data = None) :
        '''
        TBD
        '''
        _imsg = "\"" + tag + "\" instance information on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        _dom_info = {}

        _state_code2value = {}
        _state_code2value["1"] = "running"
        _state_code2value["2"] = "blocked"
        _state_code2value["3"] = "paused"
        _state_code2value["4"] = "shutdown"
        # Temporarily renaming "shutoff" to "save"
        _state_code2value["5"] = "save"
        _state_code2value["6"] = "crashed"

        try :
            if not instance_data :
                instance_data = lvirt_conn.lookupByName(tag)
                
            _dom_info["os_type"] = instance_data.OSType()
            _dom_info["scheduler_type"] = instance_data.schedulerType()[0]
            
            # All object uuids on state store are case-sensitive, so will
            # try to just capitalize the UUID reported by libvirt
            _dom_info["cloud_uuid"] = instance_data.UUIDString().upper()
            _dom_info["uuid"] = _dom_info["cloud_uuid"]
            _dom_info["cloud_lvid"] = instance_data.name()

            _g_dom_info = instance_data.info()

            _dom_info["vmem"] = str(_g_dom_info[1])
            _dom_info["vmem_current"] = str(_g_dom_info[2])
            _dom_info["vcpus"] = str(_g_dom_info[3])

            _state_code = str(_g_dom_info[0])
            if _state_code in _state_code2value :
                _dom_info["state"] = _state_code2value[_state_code]
            else :
                _dom_info["state"] = "unknown"

            if _state_code == "1" :
                _vcpu_info = instance_data.vcpus()
                for _vcpu_nr in range(0, int(_dom_info["vcpus"])) :
                    _dom_info["vcpu_" + str(_vcpu_nr) + "_pcpu"] = str(_vcpu_info[0][_vcpu_nr][3])
                    _dom_info["vcpu_" + str(_vcpu_nr) + "_time"] =  str(_vcpu_info[0][_vcpu_nr][2])
                    _dom_info["vcpu_" + str(_vcpu_nr) + "_state"] =  str(_vcpu_info[0][_vcpu_nr][1])
                    _dom_info["vcpu_" + str(_vcpu_nr) + "_map"] = str(_vcpu_info[1][_vcpu_nr])
            
                _sched_info = instance_data.schedulerParameters()

                _dom_info["vcpus_soft_limit"] = str(_sched_info["cpu_shares"])

                if "vcpu_period" in _sched_info :
                    _dom_info["vcpus_period"] = str(float(_sched_info["vcpu_period"]))
                    _dom_info["vcpus_quota"] = str(float(_sched_info["vcpu_quota"]))
                    _dom_info["vcpus_hard_limit"] = str(float(_dom_info["vcpus_quota"]) / float(_dom_info["vcpus_period"]))

                if "memoryParameters" in dir(instance_data) :
                    _mem_info = instance_data.memoryParameters(0)
    
                    _dom_info["mem_hard_limit"] = str(_mem_info["hard_limit"])
                    _dom_info["mem_hard_limit"] = str(_mem_info["soft_limit"])
                    _dom_info["mem_swap_hard_limit"] = str(_mem_info["swap_hard_limit"])


                if "blkioParameters" in dir(instance_data) :
                    _diskio_info = instance_data.blkioParameters(0)
                    _dom_info["diskio_soft_limit"] = "unknown"
                    if _diskio_info :
                        if "weight" in _diskio_info :
                            _dom_info["diskio_soft_limit"] = str(_diskio_info["weight"])

            _xml_contents = instance_data.XMLDesc(0)
            _xml_doc = libxml2.parseDoc(_xml_contents)
            _xml_ctx = _xml_doc.xpathNewContext()

            _network_device_list = _xml_ctx.xpathEval("/domain/devices/interface[1]/target/@dev")

            if _network_device_list :
                _dom_info["cloud_netif"] = _network_device_list[0].content
            
            _network_mac_address = _xml_ctx.xpathEval("/domain/devices/interface[1]/mac/@address")

            if _network_device_list :
                _dom_info["cloud_mac"] = _network_mac_address[0].content

            _volume_list = _xml_ctx.xpathEval("/domain/devices/disk/source/@file")
            _volcount = 0
            if _volume_list :
                for _volume in _volume_list :
                    _dom_info["volume_path" + str(_volcount)] = _volume.content
                    # Well known hash function allows the volume's UUID to be
                    # derived directly
                    _dom_info["volume_uuid" + str(_volcount)] = str(uuid5(NAMESPACE_DNS, \
                                                                          lvirt_conn.host + \
                                                                          '.' + \
                                                                          _volume.content)).upper()
                    _volcount += 1
            _dom_info["volumes"] = _volcount
            return _dom_info

        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))
    
    @trace
    def destroy_all_domains(self, lvirt_conn, graceful, pattern) :
        '''
        TBD
        '''
        try :
            _domains = self.list_domains(lvirt_conn, False, pattern)
            _imsg = "All domains on libvirt host " + lvirt_conn.host
            _smsg = _imsg + " were successfully destroyed."
            _fmsg = _imsg + " could not be destroyed: "

            if len(_domains) > 0:
                _msg = "Issuing shutdowns to " + str(len(_domains))
                _msg += " running VMs on host " + lvirt_conn.host
                cbdebug(_msg, True)

                if not graceful :

                    for name in _domains :
                        _domains[name].destroy()
                        _msg = "domain id " + name + " destroyed on "
                        _msg += lvirt_conn.host
                        cbdebug(_msg, True)
            else :

                tries = 40 

                # First issue shutdowns to them all
                stall_secs = 15
                for name in _domains :
                    if _domains[name].isActive() :
                        _domains[name].shutdown()
                        _msg = "Iterative shutdown issued to domain id "
                        _msg += name + " on " + lvirt_conn.host
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
                    _msg += str(active) + " domains on " + lvirt_conn.host
                    cbdebug(_msg, True)
                    sleep(10)

                for _name in _domains :
                    if _domains[_name].isActive() :
                        _msg = "domain id " + _name + " shutdown failed. "
                        _msg += "Will have to destroy it."
                        cbdebug(_msg, True)
                        _domains[name].destroy()

            # Now undefine all VMs on the host                    
            _domains = self.list_domains(lvirt_conn, True, "cb")
    
            for _name in _domains :
                _domain = _domains[_name]
                self.destroy_and_undefine_domain(lvirt_conn, _domain.name())
                          
            cbdebug(_smsg)
            return True
                
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))
    
    @trace
    def create_domain(self, lvirt_conn, xml, tag, paused = False) :
        '''
        TBD
        '''
        _imsg = tag + " domain on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully created."
        _fmsg = _imsg + " could not be created: "
        
        try :
            _dom = lvirt_conn.defineXML(xml)
            if paused :
                _dom.createWithFlags(VIR_DOMAIN_START_PAUSED)
            else :
                _dom.create()
            #vm_uuid = dom.UUIDString()
            cbdebug(_smsg)
            return True 
    
        except libvirtError, msg: 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def ft_status(self, tag, primary_host_cloud_ip, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(primary_host_cloud_ip)
        _imsg = "Replication performance for VM " + tag + " on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " "
        _fmsg = _imsg + " could not be retrieved: "
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            return self.success("qemu result", qemuMonitorCommand(_dom, 'info migrate', 1))
        except libvirtError, msg: 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def ft_stop(self, tag, primary_host_cloud_ip, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(primary_host_cloud_ip)
        _imsg = "Replication for " + tag + " domain on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " has stopped. "
        _fmsg = _imsg + " could not be stopped: "
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            qemuMonitorCommand(_dom, 'migrate_cancel', 1)
            sleep(5)
            _dom.resume()
        except libvirtError, msg: 
            return self.error(2, _fmsg + str(msg), None)
        return self.success(_smsg, True)
        
    def ft_resume(self, tag, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(hypervisor_ip)
        _imsg = "Resume of FT stub " + tag + " for takeover on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " has succeeded."
        _fmsg = _imsg + " could not be completed: "
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            qemuMonitorCommand(_dom, 'c', 1)
            _dom.resume()
        except libvirtError, msg: 
            return self.error(3, _fmsg + str(msg), None)
        return self.success(_smsg, True)
        
    def ft_start(self, tag, replication_port, svm_stub_ip, primary_host_cloud_ip, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(primary_host_cloud_ip)
        _imsg = "Replication for " + tag + " domain on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " has started to destination VMC: " + svm_stub_ip + ":" + str(replication_port)
        _fmsg = _imsg + " could not be created: "
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            qemuMonitorCommand(_dom, 'migrate_set_speed 10g', 1)
            qemuMonitorCommand(_dom, 'migrate -d kemari:tcp:' + svm_stub_ip + ':' + str(replication_port), 1)
        except libvirtError, msg: 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))
        return self.success(_smsg, True)

    @trace
    def statically_balance_vcpu_domains(self, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(hypervisor_ip)
        pcpu_nr = self.get_host_info(lvirt_conn)["pcpus"]
                
        try :
            _max_pcpu_nr = pcpu_nr - 1
            _curr_pcpu_nr = 0
            _pcpu_pin_list = [False] * pcpu_nr
            _tag = "None"
            for _tag in self.list_domains(lvirt_conn, False, None).keys() :
                _vcpu_count = int(self.get_domain_info(_tag, hypervisor_ip)[2]["vcpus"])
                _dom = lvirt_conn.lookupByName(_tag)
                
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
            _msg += _tag + " on " + lvirt_conn.host + ": " + str(msg)
            cberr(_msg)
            self.PLMraise(lvirt_conn.host, 2, _msg)
        
        except self.LibvirtMgdConnException, obj :
            self.PLMraise(lvirt_conn.host, 3, obj.msg)
            
        return self.success(_msg, True)
 
    @trace    
    def set_domain_memory(self, tag, mem_param, value, hypervisor_ip) :
        '''
        TBD
        '''
        value = int(value)
        lvirt_conn = self.lvirt_conn_check(hypervisor_ip)
        try :
            _dom = lvirt_conn.lookupByName(tag)
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
                self.PLMraise(lvirt_conn.host, 4, "Failed to resize memory for domain - ran out of tries. Made it to : " + str(current) + " while trying to reach " + str(value))
                      
            _msg = " - Successfully set the memory parameter for the "
            _msg += "domain " + tag + " running on the host "
            _msg += lvirt_conn.host
        except libvirtError, msg : 
            _msg = " - Unable to set the memory parameter for the "
            _msg += "domain " + tag + " on "
            _msg += lvirt_conn.host + str(msg)
            self.PLMraise(lvirt_conn.host, 2, _msg)
        
        return self.success(_msg, True)

    @trace
    def set_domain_diskio(self, tag, diskio_param, value, hypervisor_ip) :
        '''
        TBD
        '''
        lvirt_conn = self.lvirt_conn_check(hypervisor_ip)
        _diskio_param = {}
            
        try :
            _dom = lvirt_conn.lookupByName(tag)
            _diskio_param[diskio_param] = value
            _dom.setBlkioParameters(_diskio_param,0)
            _msg = " - Successfully set the " + diskio_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvirt_conn.host
            cbdebug(_msg)
        except libvirtError, msg : 
            _msg = " - Unable to set the " + diskio_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvirt_conn.host + ": " + str(msg)
            self.PLMraise(lvirt_conn.host, 2, _msg)
        return self.success(_msg, True)
    
    @trace
    def set_domain_cpu(self, tag, cpu_param, value, hypervisor_ip) :
        '''
        TBD
        '''
        value = int(value)
        lvirt_conn = self.lvirt_conn_check(hypervisor_ip)
        _cpu_param = {}
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            _cpu_param[cpu_param] = value
            _dom.setSchedulerParameters(_cpu_param)
            _msg = "Successfully set the " + cpu_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvirt_conn.host
            cbdebug(_msg)
        except libvirtError, msg : 
            _msg = "Unable to set the " + cpu_param + " parameter"
            _msg += " for the domain " + tag + " running on the "
            _msg += "host " + lvirt_conn.host + ": " + str(msg)
            self.PLMraise(lvirt_conn.host, 2, _msg)
            
        return self.success(_msg, True)

    @trace
    def is_domain_defined(self, lvirt_conn, tag) :
        '''
        TBD
        '''
        try :
            _msg = "Going to check if domain \"" + tag + "\" is defined..."
            cbdebug(_msg)

            for _tag in lvirt_conn.listDefinedDomains() :
                if _tag == tag :
                    _msg = " \"Stopped domain " + tag + "\" is defined.... continuing"
                    return True
            for _dom_id in lvirt_conn.listDomainsID() :
                _tag = lvirt_conn.lookupByID(_dom_id).name()
                if _tag == tag :
                    _msg = " \"Running domain " + tag + "\" is defined.... continuing"
                    return True
            return False
        
        except libvirtError, msg:
            _msg = " \"" + tag + "\" is not defined.... continuing"
            cbdebug(_msg)
            return False

    @trace
    def is_domain_active(self, lvirt_conn, tag) :
        '''
        TBD
        '''
        _msg = "Going to check if domain \"" + tag + "\" is defined..."
        cbdebug(_msg)
        
        try :
            _dom = lvirt_conn.lookupByName(tag)
            if _dom.isActive() :
                _msg = " \"" + tag + "\" is running.... continuing"
                return True
            else :
                _msg = " \"" + tag + "\" is not running.... continuing"
                return False
            
        except libvirtError, msg:
            _msg = " \"" + tag + "\" is not defined... continuing"
            cbdebug(_msg)
            return False

    @trace
    def destroy_and_undefine_domain(self, lvirt_conn, tag, graceful = True) :
        '''
        TBD
        '''
        _imsg = tag + " domain libvirt on host " + lvirt_conn.host
        _smsg = _imsg + " was successfully destroyed and undefined."
        _fmsg = _imsg + " could not be destroyed and undefined: "
        _dom = None
        
        try :
            _msg = "Going to check if domain \"" + tag + "\" is defined..."
            cbdebug(_msg)
            _dom = lvirt_conn.lookupByName(tag)
        
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
                _dom = lvirt_conn.lookupByName(tag)
                
                if _dom.hasManagedSaveImage(0) :
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
                    _msg = "Oops. Going to try destroy again in " + _retry_destroy_secs + " secs..."
                    cbdebug(_msg, True)
                    sleep(_retry_destroy_secs)
                    self.lvirt_conn[lvirt_conn.host] = False
                    

        if _op_tries < 0 :
            _msg = _fmsg + "Ran out of tries. Failure is permanent."
            self.PLMraise(lvirt_conn.host, 2, _msg)
        else :
            return True

    @trace
    def alterstate_instance(self, lvirt_conn, tag, state, restorefile = None) :
        '''
        TBD
        '''
        _imsg = tag + " domain libvirt on host " + lvirt_conn.host
        _smsg = _imsg + " was successfully " + state + "d"
        _fmsg = _imsg + " could not be " + state + "d:"

        try :
            _dom = lvirt_conn.lookupByName(tag)

            if state == "save" :
                if restorefile :
                    _msg = "Issuing Non-Managed Save on VM " + tag + "..." 
                    cbdebug(_msg)
                    _dom.Save(restorefile)
                else :
                    _msg = "Issuing Managed Save on VM " + tag + "..." 
                    cbdebug(_msg)
                    _dom.managedSave(0)

            elif state == "restore" :
                if restorefile : 
                    _msg = "Issuing Non-Managed Restore on VM " + tag + "..." 
                    cbdebug(_msg)
                    _dom.restore(restorefile)
                else :
                    _msg = "Issuing Managed Restore on VM " + tag + "..."
                    cbdebug(_msg)                    
                    if _dom.hasManagedSaveImage(0) :
                        _dom.create()

            elif state == "resume" :
                _msg = "Resuming VM " + tag + "..."
                cbdebug(_msg)
                _dom.resume()

            elif state == "suspend" :
                cbdebug("Suspending VM " + tag + "...")
                _dom.suspend()
            else :
                _msg =  "Unknown state (" + state + ")"
                self.PLMraise(lvirt_conn.host, 389, _msg)
    
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 3, _fmsg + str(msg))
        return self.success(_smsg, None)

    @trace
    def list_storage_pools(self, lvirt_conn, defined = False, pattern = None) :
        '''
        TBD
        '''
        _pools = {}
        _imsg = "Pool list for libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            if defined :
                for _tag in lvirt_conn.listDefinedStoragePools() :
                    _pool = lvirt_conn.storagePoolLookupByName(_tag)
                    if pattern :
                        if not _tag.count(pattern) :
                            continue
                        else :
                            _pools[_pool.name()] = _pool
                    else :
                        _pools[_pool.name()] = _pool

            for _tag in lvirt_conn.listStoragePools() :
                _pool = lvirt_conn.storagePoolLookupByName(_tag)
                if pattern :
                    if not _tag.count(pattern) :
                        continue
                    else :
                        _pools[_pool.name()] = _pool
                else :
                    _pools[_pool.name()] = _pool

            cbdebug(_smsg)
            return _pools
            
        except libvirtError, msg : 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace    
    def get_storage_pool_info(self, lvirt_conn, tag, pool_data = None) :
        '''
        TBD
        '''

        _imsg = "\"" + tag + "\" storage pool information on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        _pool_info = {}

        _state_code2value = {}
        _state_code2value["0"] = "inactive"
        _state_code2value["1"] = "building"
        _state_code2value["2"] = "running"
        _state_code2value["3"] = "degraded"
        _state_code2value["4"] = "inaccessible"

        try :
            if not pool_data :
                pool_data = lvirt_conn.storagePoolLookupByName(tag)
                pool_data.refresh(0)
            
            # All object uuids on state store are case-sensitive, so will
            # try to just capitalize the UUID reported by libvirt
            _pool_info["cloud_uuid"] = pool_data.UUIDString().upper()
            _pool_info["uuid"] = _pool_info["cloud_uuid"]
            
            _g_pool_info = pool_data.info()

            _state_code = str(_g_pool_info[0])
            if _state_code in _state_code2value :
                _pool_info["state"] = _state_code2value[_state_code]
            else :
                _pool_info["state"] = "unknown"
            
            _pool_info["capacity"] = str(_g_pool_info[1])
            _pool_info["allocation"] = str(_g_pool_info[2])
            _pool_info["available"] = str(_g_pool_info[3])
            _pool_info["volumes"] = pool_data.numOfVolumes()
            
            _xml_contents = pool_data.XMLDesc(0)
            _xml_doc = libxml2.parseDoc(_xml_contents)
            _xml_ctx = _xml_doc.xpathNewContext()
            
            _path_list = _xml_ctx.xpathEval("/pool/target/path")
            if _path_list :
                _pool_info["path"] = _path_list[0].content

            if "path" in _pool_info :
                if _pool_info["path"].count("/dev") :
                    _pool_info["type"] = "block"
                else :
                    _pool_info["type"] = "file"
            else :
                _pool_info["type"] = "NA"

            return _pool_info
            
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace    
    def create_storagepool(self, lvirt_conn, tag, storage_pool_xml_file, pre_existing = False) :
        '''
        TBD
        '''
        _imsg = tag + " storage pool on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully created."
        _fmsg = _imsg + " could not be created: "
            
        try :
            _poolnames = lvirt_conn.listDefinedStoragePools()
            _poolnames += lvirt_conn.listStoragePools()
            for _name in _poolnames :
                if _name == tag :
                    _msg = "Pool " + tag + " already created."
                    cbdebug(_msg)
                    _pool = lvirt_conn.storagePoolLookupByName(_name)
                    try :
                        self.activate_pool_if_inactive(lvirt_conn, _pool)
                        _pool.destroy()
                    except libvirtError, err :
                        # This happens when an old storage pool was tampered with,
                        # such as underlying directories were deleted incorrectly
                        # OK to ignore - because we are about to destroy it and
                        # re-create it anyway
                        if err.err[0] == VIR_FROM_STREAMS :
                            _msg = "Invalid defined storage pool: " + _name + ". Will destroy and re-create..." 
                            cberr(_msg)
                        else :
                            # Just throw exception back to the main handler
                            raise err
                    _pool = lvirt_conn.storagePoolLookupByName(_name)
                    if _pool.isPersistent() :
                        _pool.undefine()
                    break

            _pool = lvirt_conn.storagePoolDefineXML(storage_pool_xml_file, 0)

            _pool.setAutostart(1)

            if not pre_existing :
                _pool.build(0)

            _pool.create(0)

            self.activate_pool_if_inactive(lvirt_conn, _pool)

            cbdebug(_smsg)
            return True
        
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def activate_pool_if_inactive(self, lvirt_conn, pool) :
        '''
        TBD
        '''
        pool.setAutostart(1)
        
        if not pool.isActive() :
            try :
                pool.build()
            except :
                True
            pool.create(0)

    @trace
    def restart_pool(self, lvirt_conn, poolname) :
        '''
        TBD
        '''
        _imsg = poolname + " pool on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully restarted."
        _fmsg = _imsg + " could not be restarted: "
        try : 
            _pool = lvirt_conn.storagePoolLookupByName(poolname)
            _pool.destroy()
            _pool.create(0)
            cbdebug(_smsg)
            return True
        
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    def destroy_storagepool(self, lvirt_conn, tag) :
        '''
        TBD
        '''
        _imsg = "\"" + tag + "\" storage pool on libvirt host " + lvirt_conn.host
        _smsg = _imsg + " was successfully destroyed."
        _fmsg = _imsg + " could not be destroyed: "
        
        try :
            _msg = "Going to check if storage_pool \"" + tag + "\" is defined..."
            cbdebug(_msg)

            _pool = lvirt_conn.storagePoolLookupByName(tag)
            if _pool.isActive() :
                _pool.destroy()
            _pool.undefine()

        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def create_volume(self, lvirt_conn, tag, storage_pool, vol_xml_file) :
        '''
        TBD
        '''
        _imsg = "\"" + tag + "\" volume on libvirt host " + lvirt_conn.host + " (" + storage_pool + " pool) "
        _smsg = _imsg + " was successfully created."
        _fmsg = _imsg + " could not be created: "
        
        try :
            _pool = lvirt_conn.storagePoolLookupByName(storage_pool)
            self.activate_pool_if_inactive(lvirt_conn, _pool)
            _pool.createXML(vol_xml_file, 0)
            return True

        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def list_volumes(self, lvirt_conn, storage_pool, pattern = None) :
        '''
        TBD
        '''
        _volumes = {}
        _imsg = "Volume list for libvirt host " + lvirt_conn.host + " (" + storage_pool + " pool) "
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        
        try :
            _pool= lvirt_conn.storagePoolLookupByName(storage_pool)
            
            for _tag in _pool.listVolumes() :
                if not _tag.count("lost+found") :
                    _volume = _pool.storageVolLookupByName(_tag)
                    if pattern :
                        if not _tag.count(pattern) :
                            continue
                        else :
                            _volumes[_tag] = _volume
                    else :
                        _volumes[_tag] = _volume

            cbdebug(_smsg)
            return _volumes
            
        except libvirtError, msg : 
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace    
    def get_volume_info(self, lvirt_conn, tag, storage_pool, volume_data = None) :
        '''
        TBD
        '''

        _imsg = "\"" + tag + "\" volume information on libvirt host " + lvirt_conn.host + " (" + storage_pool + " pool) "
        _smsg = _imsg + " was successfully obtained."
        _fmsg = _imsg + " could not be obtained: "
        _volume_info = {}

        _type_code2value = {}
        _type_code2value["0"] = "file"
        _type_code2value["1"] = "block"
        _type_code2value["2"] = "directory"
        _type_code2value["3"] = "network"

        try :
            if not volume_data :
                _pool = lvirt_conn.storagePoolLookupByName(storage_pool)
                _pool.refresh(0)
                volume_data = _pool.storageVolLookupByName(tag)

            _g_volume_info = volume_data.info()
            _volume_type = str(_g_volume_info[0])

            if _volume_type in _type_code2value :
                _volume_info["type"] = _type_code2value[_volume_type]
            else :
                _volume_info["type"] = "unknown"

            _volume_info["capacity"] = str(_g_volume_info[1])
            _volume_info["allocation"] = str(_g_volume_info[2])

            _volume_info["storage_pool"] = storage_pool
            _volume_info["path"] = volume_data.path()

            # Volumes do not have an UUID, so a well-known, well-behaved
            # hash function will be used as the seed for the UUID: the 
            # concatenation of the host ip and the volume path
            _volume_info["cloud_uuid"] = str(uuid5(NAMESPACE_DNS, \
                                                   lvirt_conn.host + '.' + \
                                                   _volume_info["path"])).upper()

            _volume_info["uuid"] = _volume_info["cloud_uuid"]
            
            _xml_contents = volume_data.XMLDesc(0)
            _xml_doc = libxml2.parseDoc(_xml_contents)
            _xml_ctx = _xml_doc.xpathNewContext()
            
            _volume_format = _xml_ctx.xpathEval("/volume/target/format/@type")
            if _volume_format :
                _volume_info["format"] = _volume_format[0].content
            else :
                if _volume_info["type"] == "block" :
                    _volume_info["format"] = "raw"
                else :
                    _volume_info["format"] = "NA"

            _volume_snapshot = _xml_ctx.xpathEval("/volume/backingStore/path")
            if _volume_snapshot :
                _volume_info["snapshot_path"] = _volume_snapshot[0].content
                _volume_info["snapshot_uuid"] = str(uuid5(NAMESPACE_DNS, \
                                                   lvirt_conn.host + '.' + \
                                                   _volume_info["snapshot_path"])).upper()
                _volume_info["snapshot"] = "true"
            else :
                _volume_info["snapshot"] = "false"

            return _volume_info
            
        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))

    @trace
    def destroy_volume(self, lvirt_conn, tag, storage_pool) :
        '''
        TBD
        '''
        _imsg = "\"" + tag + "\" volume on libvirt host " + lvirt_conn.host + " (" + storage_pool + " pool) "
        _smsg = _imsg + " was successfully destroyed."
        _fmsg = _imsg + " could not be destroyed: "
        
        try :
            _msg = "Going to check if volume \"" + tag + "\" is defined..."
            cbdebug(_msg)
            _pool = lvirt_conn.storagePoolLookupByName(storage_pool)
            _pool.refresh(0)
            _pool.storageVolLookupByName(tag)
        
        except libvirtError, msg:
            _msg = _smsg + " (Volume not defined)"
            cbdebug(_msg)
            return True
        
        try :
            self.activate_pool_if_inactive(lvirt_conn, _pool)
            if tag is not None :
                _pool.storageVolLookupByName(tag).delete(0)
            cbdebug(_smsg, True)
            return True

        except libvirtError, msg :
            self.PLMraise(lvirt_conn.host, 2, _fmsg + str(msg))
            
    def get_signature(self, name):
        '''
        TBD
        '''
        return self.success("signature", self.signatures[name])

class AsyncDocXMLRPCServer(SocketServer.ThreadingMixIn,DocXMLRPCServer): pass

class PLMService ( threading.Thread ):
    '''
    TBD
    '''
    def __init__(self, port, groups, dhcp_omapi_server, dhcp_omapi_port, oscp, debug) :
        '''
        TBD
        '''
        super(PLMService, self).__init__()
        self._stop = threading.Event()
        self.pid = ""
        self.port = port
        self.dhcp_omapi_server = dhcp_omapi_server
        self.dhcp_omapi_port = int(dhcp_omapi_port)
        self.dhcp_omap_pkey = "d+y8yPwtC0nJ0C0uRC5cxYREYGPBkJwhJYjHbb1LkoW0FF6gYr3SiVi6 HRQUcl4Y7gdzwvi0hgPV+Gdy1wX9vg==" 
        self.dhcp_omap_keyn = "omapi_key"
        self.plm = Plm(groups, oscp)
        _msg = "Initializing API Service on port " + str(self.port)
        cbdebug(_msg)
        if debug is None :
            self.server = AsyncDocXMLRPCServer(("0.0.0.0", int(self.port)), allow_none = True)
        else :
            self.server = DocXMLRPCServer(("0.0.0.0", int(self.port)), allow_none = True)

        self.server.set_server_title(options.cluster_name + ": Parallel Libvirt Manager Service (PLM xmlrpc)")
        self.server.set_server_name(options.cluster_name + ": Parallel Libvirt Manager Service (PLM xmlrpc)")
        self.plm.signatures = {}

        for methodtuple in inspect.getmembers(self.plm, predicate=inspect.ismethod) :
            name = methodtuple[0]
            func = getattr(self.plm, name)
            argspec = inspect.getargspec(func) 
            spec = argspec[0]
            defaults = [] if argspec[3] is None else argspec[3]
            self.plm.signatures[name] = spec
            #setattr(self.plm, name, self.plm.unwrap_kwargs(func))
            #self.server.register_function(func, name)
            if "lvirt_conn" not in spec and len(spec) > 1 and \
                name not in ["__init__", "lvirt_conn_check", "error", "success", "global_error", "PLMraise", "get_libvirt_vm_templates"]:
                doc = "Parameters: "
                num_spec = len(spec)
                num_defaults = len(defaults)
                diff = num_spec - num_defaults
                for x in range(1, diff) :
                    doc += spec[x] + ", "
                for x in range(diff, num_spec) :
                    doc += spec[x] + " = " + str(defaults[x - diff]) + ", "
                doc = doc[:-2]
                    
                self.server.register_function(unwrap_kwargs(func, doc), name)
            
#        self.server.register_introspection_functions()
        cbdebug("PLM Service started")
        
    def run(self) :
        '''
        TBD
        '''
        cbdebug("PLM Service waiting for requests...")
        self.server.serve_forever()
        cbdebug("PLM Service shutting down...")
        
    def stop (self) :
        '''
        TBD
        '''
        cbdebug("Calling PLM Service shutdown....")
        self._stop.set()
        self.server.shutdown()

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
        
def main(options) :
    '''
    TBD
    '''
    try :
        PLMservice = None
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
            if int(_verbosity) >= 3 :
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 2 :
                hdlr.addFilter(VerbosityFilter("code_instrumentation"))
                hdlr.addFilter(VerbosityFilter("data_ops"))
                hdlr.addFilter(VerbosityFilter("hotplug_rem_ops"))
                hdlr.addFilter(VerbosityFilter("network_functions"))
                hdlr.addFilter(VerbosityFilter("pypureomapi"))
                hdlr.addFilter(VerbosityFilter("value_generation"))
                logger.setLevel(DEBUG)
            elif int(options.verbosity) >= 1 :
                hdlr.addFilter(VerbosityFilter("code_instrumentation"))
                hdlr.addFilter(VerbosityFilter("data_ops"))
                hdlr.addFilter(VerbosityFilter("hotplug_rem_ops"))
                hdlr.addFilter(VerbosityFilter("network_functions"))
                hdlr.addFilter(VerbosityFilter("pypureomapi"))
                hdlr.addFilter(VerbosityFilter("redis_adapter"))
                hdlr.addFilter(VerbosityFilter("value_generation"))
                logger.setLevel(DEBUG)
        else :
            logger.setLevel(INFO)

        if options.quiet :
            logger.setLevel(ERROR)

        _oscp = {}
        _oscp["kind"] = "redis"
        _oscp["protocol"] = "TCP"
        _oscp["cluster_name"] = options.cluster_name
        _oscp["timout"] = "300"
        _oscp["host"] = str(options.redis_host)
        _oscp["port"] = str(options.redis_port)
        _oscp["dbid"] = str(options.redis_dbid)
        _oscp["shared"] = True

        wait_for_port_ready("0.0.0.0", options.port)

        PLMservice = PLMService(options.port, options.groups, options.dhcp_omapi_server, options.dhcp_omapi_port, _oscp, options.debug_host)
        if options.debug_host is None :
            PLMservice.start()
        else :
            PLMservice.run()

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
        if PLMservice is not None :
            PLMservice.stop()
            PLMservice.join()

        if _status :
            cberr("PLM failure: " + _fmsg)
            exit(2)
        else :
            cbdebug("PLM exiting.")
            os.kill(os.getpid(), signal.SIGKILL)

# Executed code
options = actuator_cli_parsing()

if options.daemon :
    with DaemonContext(working_directory="/tmp", pidfile=None) :
        main(options)
else :
    main(options)
