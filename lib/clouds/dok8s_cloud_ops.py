#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2018 DigitalOcean, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on October 10, 2018
    DigitalOcean Kubernetes Object Operations Library
    @author: Michael R. Galaxy
'''

import requests
import copy
from requests.adapters import HTTPAdapter
from json import loads, dumps
from time import sleep, time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from .shared_functions import CldOpsException

from .libcloud_common import LibcloudCmds
from .kub_cloud_ops import KubCmds

import operator
import traceback

try:
    from http.client import HTTPConnection # py3
    from http.client import HTTPSConnection # py3
except ImportError:
    from http.client import HTTPConnection # py2
    from http.client import HTTPSConnection # py2

HTTPConnection.debuglevel = 0
HTTPSConnection.debuglevel = 0

class Dok8sCmds(KubCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        KubCmds.__init__(self, pid, osci, expid = expid)

    @trace
    def get_description(self) :
        return "DigitalOcean Kubernetes Cloud"

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}, diag = False, generate_rc = False) :
        try :
            extra_parms["kubeyaml"] = False
            if not diag :
                if "kubeconfig" in extra_parms and extra_parms["kubeconfig"] :
                    extra_parms["kubeyaml"] = extra_parms["kubeconfig"]

            return KubCmds.connect(self, access, credentials, vmc_name, extra_parms, diag, generate_rc)
        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            raise e

    @trace
    def get_session(self) :
        s = requests.Session()
        s.mount('http', HTTPAdapter(max_retries=3))
        s.mount('https', HTTPAdapter(max_retries=3))
        s.headers.update(self.headers)

        return s

    @trace
    def get_kubeconfig(self, kuuid) :
        cbdebug("Getting kubeconfig for cluster " + kuuid)
        s = self.get_session()
        r = s.get(self.access + "/kubernetes/clusters/" + kuuid + "/kubeconfig")

        if r.status_code != 200 :
            cbdebug("Failed to get kubeconfig: " + str(r.status_code))
            raise CldOpsException("Failed to get kubeconfig: " + str(r.status_code), 460)

        cbdebug("Got kubeconfig")
        return r.text

    @trace
    def create_cluster(self, obj_attr_list) :
        kuuid = False
        kubeconfig = False

        try :
            s = self.get_session()

            kname = "cb-" + obj_attr_list["username"] + '-' + obj_attr_list["cloud_name"].lower() + "-" + obj_attr_list["name"]

            # First make sure there aren't any pre-existing clusters with this name.
            # If so, destroy them.
            r = s.get(self.access + "/kubernetes/clusters")

            if r.status_code == 200 :
                for cluster in r.json()["kubernetes_clusters"] :
                    if cluster["name"] == kname :
                        self.destroy_cluster(obj_attr_list, cluster["id"])
            else :
                cbdebug("Cluster cleanup failed: " + str(r.status_code), True)
                raise CldOpsException("Could not cleanup old clusters.", 470)

            cbdebug("Creating cluster for: " + obj_attr_list["name"], True)
            create = {
                "name": kname,
                "region": obj_attr_list["region"],
                "version" : obj_attr_list["k8s_version"],
                "node_pools": [
                    {
                        "size" : obj_attr_list["k8s_worker_size"],
                        "count" : int(obj_attr_list["nb_workers"]),
                        "name" : kname + "-pool"
                    }
                ]
            }

            cbdebug("Requesting JSON: " + str(create))

            # need tolerate errors, obviously
            r = s.post(self.access + "/kubernetes/clusters", json = create)

            if r.status_code == 201 :
                j = r.json()
                kuuid = j["kubernetes_cluster"]["id"]
                cbdebug("Waiting for ready status uuid: " + kuuid)
            else :
                cbdebug("Create failed: " + str(r.status_code), True)
                raise CldOpsException("No k8s for you. Code: " + str(r.status_code), 459)

            while True :
                r = s.get(self.access + "/kubernetes/clusters/" + kuuid)

                if r.status_code == 200 :
                    if r.json()["kubernetes_cluster"]["status"]["state"] != "provisioning" :
                        cbdebug("Done.")
                        break

                    sleep(5)

            kubeconfig = self.get_kubeconfig(kuuid)

            fwname = "k8s-" + kuuid + "-worker"
            cbdebug("Modifying firewall " + fwname + " for this cluster...")

            if r.status_code == 200 :
                r = s.get(self.access + "/firewalls")
            else :
                cbdebug("Failed to get firewall " + fwname + ": " + str(r.status_code), True)
                raise CldOpsException("No k8s for you.", 461)

            firewalls = r.json()

            fwuuid = False

            for fw in firewalls["firewalls"] :
                if fw['name'] == fwname :
                    fwuuid = fw['id']
                    cbdebug("Firewall found: " + fwuuid)

            # Unfortunately, the DO api has a bug in it where they return that the k8s
            # cluster has been created, when in fact they are still performing operations
            # on it. In this case, the firewall rules needed by k8s itself are not yet
            # installed, and if we install our rules too fast, they get deleted.
            # So, first wait until we "see" that their rules have been installed first
            # before we proceed. (Not more than a few seconds).

            found = False
            while not found :
                r = s.get(self.access + "/firewalls/" + fwuuid)

                cbdebug("Checking for ready firewall rules...")
                if r.status_code == 200 :
                    rules = r.json()
                    for rule in rules["firewall"]["inbound_rules"] :
                        if str(rule["ports"]).count("30000-32767") :
                            cbdebug("Found rule: " + str(rule))
                            found = True
                            break
                else :
                    cbdebug("Error " + str(r.status_code) + " checking on rule update.")
                sleep(5)

            cbdebug("Rules ready. Adding our rule to firewall " + fwuuid)

            vm_defaults = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "vm_defaults", False)
            ports_base = int(vm_defaults["ports_base"])
            ports_range = int(vm_defaults["ports_range"])
            ports_end = ports_base + ports_range

            rule = {
              "inbound_rules": [
                {
                  "protocol": "tcp",
                  "ports": str(ports_base) + "-" + str(ports_end),
                  "sources": {
                        "addresses": [
                          "0.0.0.0/0",
                          "::/0"
                        ]
                  }
                },
                {
                  "protocol": "tcp",
                  "ports": "22",
                  "sources": {
                        "addresses": [
                          "0.0.0.0/0",
                          "::/0"
                        ]
                  }
                }
              ]
            }

            r = s.post(self.access + "/firewalls/" + fwuuid + "/rules", json = rule)

            if r.status_code == 204 :
                cbdebug("Successfully added firewall rule to " + fwuuid)
            else :
                cbdebug("Firewall rule add failed: " + str(r.status_code), True)
                raise CldOpsException("No k8s for you.", 462)

            r = s.get(self.access + "/droplets?tag_name=k8s:" + kuuid)

            if r.status_code == 200 :
                droplets = r.json()["droplets"]
                obj_attr_list["droplets"] = dumps(droplets)
                for droplet in droplets :
                    cbdebug("Droplet ID: " + str(droplet["id"]), True)
                    for network in droplet["networks"]["v4"] :
                        cbdebug(" ==> " + network["type"] + " = " + network["ip_address"], True)
            else :
                cberr("Failed to list droplet IDs: " + str(r.status_code), True)
                raise CldOpsException("No k8s for you.", 463)
        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)

            cberr("Failure to create k8s cluster: " + str(e), True)

            if kuuid :
                self.destroy_cluster(obj_attr_list, kuuid)

            return False, False

        return kuuid, kubeconfig

    @trace
    def destroy_cluster(self, temp_obj_attr_list, kuuid) :
        try :
            obj_attr_list = copy.deepcopy(temp_obj_attr_list) 

            s = self.get_session()

            cbdebug("Destroying Cluster: " + kuuid, True)

            obj_attr_list["kubeconfig"] = self.get_kubeconfig(kuuid)

            KubCmds.vmccleanup(self, obj_attr_list, force_all = True)
            KubCmds.purge_connection(self, obj_attr_list)

            r = s.delete(self.access + "/kubernetes/clusters/" + kuuid)

            if r.status_code not in [202, 204] :
                cbdebug("Failed to delete: " + str(r.status_code), True)
                raise CldOpsException("Destroy cluster failed.", 462)
                
            # Check for delete complete....

            cbdebug("Waiting for delete to finish...")
            while True :
                r = s.get(self.access + "/kubernetes/clusters/" + kuuid)

                if r.status_code == 404 :
                    cbdebug("Done.")
                    break

                sleep(5)
                    
            cbdebug("Deleted " + kuuid)
            return True

        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            cberr("Failure to destroy k8s cluster: " + str(e), True)
            return False

    @trace
    def vmcregister(self, obj_attr_list) :
        status = 0
        msg = ""

        try :
            cluster_list = obj_attr_list["clusters"].lower().strip().split(",")
            region = False
            size = False
            version = False
            worker_size = False
            for cluster in cluster_list :
                name, region, version, worker_size, nb_workers = cluster.split(":")
                if name == obj_attr_list["name"] :
                    cbdebug("VMC " + name + " in " + region + " using version " + version + " and " + nb_workers + " workers each of size " + worker_size, True)
                    break

            if not region :
                return 104, "VMC " + name + " not found in CLUSTERS configuration list. Please correct and try again: " + cluster_list

            obj_attr_list["region"] = region
            obj_attr_list["nb_workers"] = nb_workers
            obj_attr_list["k8s_version"] = version
            obj_attr_list["k8s_worker_size"] = worker_size

            if "kubeconfig" not in obj_attr_list :
                self.access = obj_attr_list["access"]
                self.headers = {"Authorization" : "Bearer " + obj_attr_list["credentials"]}
                obj_attr_list["kuuid"], obj_attr_list["kubeconfig"] = self.create_cluster(obj_attr_list)
                if not obj_attr_list["kuuid"] :
                    return 458, "vmcregister did not find a UUID, No k8s for you."
            status, msg = KubCmds.vmcregister(self, obj_attr_list)
        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            status, msg = self.common_messages("VMC", obj_attr_list, "registered", status, msg)

        return status, msg

    @trace
    def vmcunregister(self, obj_attr_list) :
        status = 0
        msg = "" 
        try :
            self.access = obj_attr_list["access"]
            self.headers = {"Authorization" : "Bearer " + obj_attr_list["credentials"]}
            status, msg = KubCmds.vmcunregister(self, obj_attr_list, force_all = True)
            if status == 0 and "kubeconfig" in obj_attr_list :
                if obj_attr_list["kuuid"] :
                    success = self.destroy_cluster(obj_attr_list, obj_attr_list["kuuid"])
                    if not success :
                        status = 463
                        msg = "Failed to destroy k8s cluster"
        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            status, msg = self.common_messages("VMC", obj_attr_list, "unregistered", status, msg)
        return status, msg 

    @trace
    def vmcreate(self, obj_attr_list) :
        # The only thing we're doing here is recording into MongoDB properly
        # exactly which container maps to which physical k8s node, so that we can
        # track in the database where the container lived.
        status = 0
        msg = "" 
        try :
            # Then just call the original function to actually do the create.
            status, msg = KubCmds.vmcreate(self, obj_attr_list)
            if status == 0 :
                _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, obj_attr_list["vmc"], False)
                for droplet in loads(_vmc_attr_list["droplets"]) :
                    if droplet["name"] == obj_attr_list["node"] :
                        obj_attr_list["host_name"] = droplet["id"]
                        cbdebug("Container " + obj_attr_list["name"] + " sent to Node " + obj_attr_list["node"] + " = " + str(obj_attr_list["host_name"]), True)
                        obj_attr_list["droplet"] = dumps(droplet)
                        break
        except Exception as e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
        finally :
            status, msg = self.common_messages("VM", obj_attr_list, "created", status, msg)
            return status, msg
