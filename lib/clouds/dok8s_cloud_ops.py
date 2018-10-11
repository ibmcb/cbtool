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
import pykube
import traceback


class Dok8sCmds(KubCmds) :
    @trace
    def __init__ (self, pid, osci, expid = None) :
        self.kubeconfig = False
        self.kuuid = False
        # change to 'access'
        KubCmds.__init__(self, pid, osci, expid = expid)

    @trace
    def get_description(self) :
        return "DigitalOcean Kubernetes Cloud"

    @trace
    def connect(self, access, credentials, vmc_name, extra_parms = {}, diag = False, generate_rc = False) :
        try :
            if not diag and not self.kubeconn :
                # Move the pykube call into the kub adapter itself so we don't have to import it
                self.kubeconn = pykube.HTTPClient(pykube.KubeConfig(yaml.safe_load(self.kubeconfig)))

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

            create = {
                "kubernetes_cluster": {
                    "name": kname,
                    "region": obj_attr_list["name"],
                    "version":"1.11.1-do.1",
                    "worker_pools": [
                        {
                            "droplet_size" : "s-2vcpu-4gb",
                            "version" : "1.11.1-do.1",
                            "num_nodes" : 2,
                            "name" : kname + "-pool"
                        }
                    ]
                }
            }

            # need tolerate errors, obviously
            r = s.post(self.access + "/kubernetes/clusters", json = create)

            if r.status_code == 201 :
                j = r.json()
                kuuid = j["kubernetes_cluster"]["uuid"]
                cbdebug("Waiting for ready status uuid: " + kuuid)
            else :
                cbdebug("Create failed: " + str(r.status_code), True)
                raise CldOpsException("No k8s for you.", 459)

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

            rule = {
              "inbound_rules": [
                {
                  "protocol": "tcp",
                  "ports": "40000-45000",
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
            if not self.kubeconfig :
                if "kubeconfig" not in obj_attr_list :
                    credentials = "63c4a071ae4795dcbdd424ff403856170bdb4c359a7b9278f0158b501f98ef17"
                    self.access = obj_attr_list["access"]
                    self.headers = {"Authorization" : "Bearer " + credentials}
                    # This really should be in vmcregister()
                    cbdebug("Creating cluster: " + obj_attr_list["name"], True)
                    obj_attr_list["kuuid"], obj_attr_list["kubeconfig"] = self.create_cluster(obj_attr_list)
                    if not obj_attr_list["kuuid"] :
                        raise CldOpsException("vmcregister, No k8s for you.", 458)
                self.kubeconfig = obj_attr_list["kubeconfig"]
                self.kuuid = obj_attr_list["kuuid"]
        except Exception, e :
            for line in traceback.format_exc().splitlines() :
                cbwarn(line, True)
            raise e

        status, msg = KubCmds.vmcregister(self, obj_attr_list)
        return status, msg

    # Store things into the object. kubeconfig. kuuid, etc.
    # This should be vmcunregister, not cleanup
    @trace
    def vmcunregister(self, obj_attr_list) :
        status, msg = KubCmds.vmcunregister(self, obj_attr_list)
        if status == 0 and "kubeconfig" in obj_attr_list :
            success = self.destroy_cluster(obj_attr_list["kuuid"])
            if not success :
                status = 463
                msg = "Failed to destroy k8s cluster"
        return status, msg 
