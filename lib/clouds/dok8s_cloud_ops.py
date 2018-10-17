#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2015 DigitalOcean, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************

'''
    Created on October 10, 2018
    DigitalOcean Kubernetes Object Operations Library
    @author: Michael R. Hines
'''

import requests
import yaml
from requests.adapters import HTTPAdapter
from json import loads
from time import sleep, time

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from shared_functions import CldOpsException

from libcloud_common import LibcloudCmds
from kub_cloud_ops import KubCmds

import operator
import traceback

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
                if "kubeconfig" in extra_parms :
                    extra_parms["kubeyaml"] = yaml.safe_load(extra_parms["kubeconfig"])

            return KubCmds.connect(self, access, credentials, vmc_name, extra_parms, diag, generate_rc)
        except Exception, e :
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
                        self.destroy_cluster(cluster["uuid"])
            else :
                cbdebug("Cluster cleanup failed: " + str(r.status_code), True)
                raise CldOpsException("Could not cleanup old clusters.", 470)

            cbdebug("Creating cluster for: " + obj_attr_list["name"], True)
            create = {
                "kubernetes_cluster": {
                    "name": kname,
                    "region": obj_attr_list["region"],
                    "version" : obj_attr_list["k8s_version"],
                    "worker_pools": [
                        {
                            "droplet_size" : obj_attr_list["k8s_worker_size"],
                            "version" : obj_attr_list["k8s_version"],
                            "num_nodes" : int(obj_attr_list["nb_workers"]),
                            "name" : kname + "-pool"
                        }
                    ]
                }
            }

            cbdebug("Requesting JSON: " + str(create))

            # need tolerate errors, obviously
            r = s.post(self.access + "/kubernetes/clusters", json = create)

            if r.status_code == 201 :
                j = r.json()
                kuuid = j["kubernetes_cluster"]["uuid"]
                cbdebug("Waiting for ready status uuid: " + kuuid)
            else :
                cbdebug("Create failed: " + str(r.status_code), True)
                raise CldOpsException("No k8s for you. Code: " + str(r.status_code), 459)

            while True :
                r = s.get(self.access + "/kubernetes/clusters/" + kuuid)

                if r.status_code == 200 :
                    if not r.json()["kubernetes_cluster"]["pending"] :
                        cbdebug("Done.")
                        break

                    sleep(5)
                    continue

            cbdebug("Getting kubeconfig for cluster " + kuuid)
            r = s.get(self.access + "/kubernetes/clusters/" + kuuid + "/kubeconfig")

            if r.status_code == 200 :
                kubeconfig = r.text
                cbdebug("Got kubeconfig")
            else :
                cbdebug("Failed to get kubeconfig: " + str(r.status_code))
                raise CldOpsException("Failed to get kubeconfig: " + str(r.status_code), 460)

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

            cbdebug("Adding rule to firewall " + fwuuid)

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
                }
              ]
            }

            r = s.post(self.access + "/firewalls/" + fwuuid + "/rules", json = rule)

            if r.status_code == 204 :
                cbdebug("Successfully added firewall rule to " + fwuuid)
            else :
                cbdebug("Firewall rule add failed: " + str(r.status_code), True)
        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)

            cberr("Failure to create k8s cluster: " + str(e), True)

            if kuuid :
                self.destroy_cluster(kuuid)

            return False, False

        return kuuid, kubeconfig

    @trace
    def destroy_cluster(self, kuuid) :
        try :
            s = self.get_session()

            cbdebug("Destroying Cluster: " + kuuid, True)

            r = s.delete(self.access + "/kubernetes/clusters/" + kuuid)

            if r.status_code != 202 :
                cbdebug("Failed to delete: " + str(r.status_code), True)
                raise CldOpsException("Destroy cluster failed.", 462)
                
            # Check for delete complete....

            cbdebug("Waiting for delete to finish...")
            while True :
                r = s.get(self.access + "/kubernetes/clusters/" + kuuid)

                if r.status_code == 404 or (r.status_code == 200 and not r.json()["kubernetes_cluster"]["pending"]) :
                    cbdebug("Done.")
                    break

                sleep(5)
                continue
                    
            cbdebug("Deleted " + kuuid)
            return True

        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            cberr("Failure to destroy k8s cluster: " + str(e), True)
            return False

    @trace
    def vmcregister(self, obj_attr_list) :
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
        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            raise e

        status, msg = KubCmds.vmcregister(self, obj_attr_list)
        return status, msg

    @trace
    def vmcunregister(self, obj_attr_list) :
        status, msg = KubCmds.vmcunregister(self, obj_attr_list)
        if status == 0 and "kubeconfig" in obj_attr_list :
            success = self.destroy_cluster(obj_attr_list["kuuid"])
            if not success :
                status = 463
                msg = "Failed to destroy k8s cluster"
        return status, msg 
