#!/usr/bin/env python3

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

'''
    Created on Oct 25, 2012

    GUI formatter

    @author: Michael R. Galaxy
'''

import json
import traceback
import os
import re
import shutil
import urllib.request, urllib.error, urllib.parse

from datetime import datetime
from pwd import getpwuid
from copy import deepcopy
from operator import itemgetter
from sys import path
from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web import proxy, server
from twisted.python import log
from webob import Request, Response, exc
from beaker.middleware import SessionMiddleware


cwd = (re.compile(".*\/").search(os.path.realpath(__file__)).group(0)) + "/../../"
path.append(cwd)
path.append(cwd + "3rd_party/StreamProx/streamprox")

from lib.api.api_service_client import *
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.data_ops import is_number, summarize, value_cleanup
from proxy import BufferingProxyFactory
from packet_buffer import PacketBuffer

def prefix(uri) :
    return ""
    #return "/" + re.compile("[^/]*\/([^/]*)").search(uri).group(1)

class Dashboard () :
    def __init__(self, msci, base_uri, time_vars, msattrs, cloud_name) :
        self.time_vars = time_vars 
        self.base_uri = base_uri
        self.start_time = int(self.time_vars["start_time"])
        self.pid = "none"
        self.processid = "none"
        self.cn = cloud_name
        self.msattrs = msattrs
        self.username = self.time_vars["username"]
        self.msci = msci
        assert(msci is not None)
        self.manage_collection = {"VM": "latest_management_VM_" + self.username, \
                                  "HOST" : "management_HOST_" + self.username }
        self.latest_os_collection = {"VM" : "latest_runtime_os_VM_" + self.username, \
                                     "HOST" : "latest_runtime_os_HOST_" + self.username } 
        self.latest_app_collection = {"VM" : "latest_runtime_app_VM_" + self.username}
        self.collections = {
                            's' : "runtime_os_VM_" + self.username,
                            'h' : "runtime_os_HOST_" + self.username,
                            'p' : "management_VM_" + self.username,
                            'a' : "runtime_app_VM_" + self.username,
                            }
        self.reported_app_metrics_collections = {"VM" : "reported_runtime_app_VM_metric_names_" + self.username}

        self.destinations = {}
        self.user_generated_categories = { 'p' : "Provisioning", 'a' : "Application" }
        self.standard_categories = { 's' : "VM", 'h': "HOST" }
        self.categories = dict(list(self.standard_categories.items()) + list(self.user_generated_categories.items()))
        self.owners = { "VM" : ['s', 'p', 'a'], "HOST" : ['h']}
        self.summaries = {"Saved VMs" : [True, "savedvm"], 
                          "Failed VMs" : [True, "failedvm"], 
                          "KB => MB" : [False, "kb2mb"], 
                          "Bytes => MB" : [False, "bytes2mb"], 
                          "bytes/sec => Mbps" : [False, "b2mb"], 
                          "#4K pages => MB" : [False, "4k2mb"]}

        self.labels = ['name', 'size', 'role', 'type', 'cloud_ip', 'age', 'vms',\
                       'state', 'latest_update', 'tenant', 'netname', 'vmc_name',\
                       'host_name', 'ai_name', 'aidrs_name' ]
        
        self.separator = "<p/>\n"
        self.show = {}
        self.base_dict = {}
        for dest in self.categories :
            self.show[dest] = True
            self.base_dict[dest] = []
        self.filters = {}
        
    def is_failed_vm(self, attrs, metrics = None) :
        '''
        TBD
        '''
        if "mgt_999_provisioning_request_failed" in attrs :
            return True
        elif "cloud_ip" in attrs and attrs["cloud_ip"] == "undefined" :
            return False
        elif metrics is not None and "last_known_state" in metrics :
            if metrics["last_known_state"].count("with ip assigned") == 0 and metrics["last_known_state"].count("generic post-boot script executed") == 0:
                return True
            else :
                return False
        else :
            return False

    def makeRow(self, category, row, uuid, labels, name, ip, host, role, current_labels, bold = False, exclude = None) :
        exclude = None
        result = "<tr>\n"
        count = 0
        for cell in row :
            cell = str(cell)
            display = cell
            if category == "p":
                if  display.count("sla_provisioning") :
                    display = "SLA Provisioning?"
                else :
                    if display.count("mgt_") :
                        display = "Step " + str(int(display[4:7])) + ": " + display[8:]
                    
            if bold and (exclude is None or cell not in exclude) :
                cell = "<a href='" + self.prefix() + "/monitor?show=" + category + "&filter=" + category + "-" + cell + "' target='_top'>" + display.replace("_", "<br/>") + "</a>"
            elif bold :
                cell = "<b>" + display.replace("_", "<br/>") + "</b>"
            else :
                cell =  display.replace("_", "<br/>")
                
            title = current_labels[count]
            if cell == "--" : 
                result += "<td>--</td>"
            elif uuid and title not in self.labels :
                result += "<td><a href='d3?uuid=" + uuid + "&category=" + category + "&label=" + labels[count] + "&name=" + name + "&ip=" + ip + "&host=" + host + "&role=" + role + "'>" + str(cell) + "</a></td>"
            else :
                result += "<td>"
                if title == "name" and uuid :
                    active = str(name).split("_")[0]
                    result += "<a class='btn btn-mini btn-info' href='BOOTDEST/provision?object=" + \
                                active + "&explode=" + uuid + "'>" + \
                                "<i class='icon-info-sign icon-white'></i>&nbsp;" + str(name).replace(active + "_", "") + "</a>"
                elif title == "ai_name" and uuid:
                    result += "<a class='btn btn-mini btn-info' href='BOOTDEST/provision?object=app&explode=" + str(display) + "'>" + \
                                "<i class='icon-info-sign icon-white'></i>&nbsp;" + str(display).replace("ai_", "") + "</a>"
                else :
                    result += str(cell)
                result += "</td>"
            count += 1
            
        result += "\n</tr>\n"
        return result

    """
    Generate a visualization of the latest metrics only and write
    the visualization out in HTML format
    """
    def gather_contents(self, expid) :
        '''
        TBD
        '''

        curr_time = int(time())
        #Collections.sort(states);
        reporting = 0
        failed = 0
        accumulate_rows = deepcopy(self.base_dict)
        accumulate_units = {}
        print_labels = {}

        for dest in self.categories :
            accumulate_units[dest] = {}
            print_labels[dest] = {}

        # Go through all the objects in the data store and parse their latest
        # Metrics as reported by ganglia
        #
        # Accumulate those metrics and unit names in a master dictionary
        # For later formatting into HTML
        _obj_list = []

        for _obj_type in list(self.manage_collection.keys()) :
            _obj_list += self.msci.find_document(self.manage_collection[_obj_type], \
                            {'expid' : expid, 'mgt_901_deprovisioning_request_originated' : { "$exists" : False}, \
                             'mgt_903_deprovisioning_request_completed' : { "$exists" : False}}, \
                            allmatches = True, sortkeypairs = [("mgt_001_provisioning_request_originated", 1)])

        for attrs in _obj_list :
            _obj_type = attrs["obj_type"]
            
            if _obj_type == "VM" :
                attrs["age"] = curr_time - int(attrs["mgt_001_provisioning_request_originated"])
            metrics = self.msci.find_document(self.latest_os_collection[_obj_type], {'expid' : expid, "_id" : attrs["uuid"]})

            if metrics is None :
                # Gmetad may not have reported in yet...
                # But we should still show management metrics
                metrics = attrs
            else :
                metrics.update(attrs)
            
            if _obj_type in self.latest_app_collection :
                _app_metrics = self.msci.find_document(self.latest_app_collection[_obj_type], {'expid' : expid, "_id" : attrs["uuid"]})

                if _app_metrics :
                    _reported_app_metrics = self.msci.find_document(self.reported_app_metrics_collections[_obj_type], {"expid" : _app_metrics["expid"]})

                    if _reported_app_metrics :
                        del _reported_app_metrics["_id"]
                        del _reported_app_metrics["expid"]

                        for _metric_name in list(_reported_app_metrics.keys()) :
                            if _metric_name not in _app_metrics :
                                _app_metrics[_metric_name] = {}
                                _app_metrics[_metric_name]["val"] = "NA"
                                _app_metrics[_metric_name]["units"] = " "

                        metrics.update(_app_metrics)

            if _obj_type == "VM" :
                bad = self.is_failed_vm(attrs, metrics)
                
                if bad :
                    failed += 1
                else :
                    reporting += 1
                    
                if not self.summaries["Failed VMs"][0] and bad :
                    continue
                
                if not self.summaries["Saved VMs"][0] and ("state" not in attrs or attrs["state"] == "save") :
                    continue
                
            elif _obj_type == "HOST" :
                attrs['vms'] = self.msci.count_document(self.manage_collection["VM"], \
                            {
                                'last_known_state' : {"$regex": ".*with ip assigned.*"}, \
                                'mgt_999_provisioning_request_failed' : { "$exists" : False}, \
                                'vmc_name' : attrs['cloud_hostname'] })
                
            row_indexer = {}
            label_indexer = {}
            for dest in self.categories :
                if _obj_type == "VM" :
                    if "host_name" in attrs :
                        _hn = attrs['host_name']
                    else :
                        _hn = "none"
                    row_indexer[dest] = {'d3_uuid' : str(attrs['uuid']), 'd3_name' : str(attrs['name']), 'd3_host' : _hn, 'd3_role' : attrs['role'], 'd3_ip' : str(attrs['cloud_ip'])}
                else :
                    row_indexer[dest] = {'d3_uuid' : str(attrs['uuid']), 'd3_name' : str(attrs['name']), 'd3_host' : 'none', 'd3_role' : 'none', 'd3_ip' : str(attrs['cloud_ip'])}
                label_indexer[dest] = {}
                       
            for mkey, mvalue in list(metrics.items()) :

                average = False
                max = False
                min = False
                acc = False
                
                if not isinstance(mvalue, dict):
                    # This path gathers metrics to display on the "Provisioning Performance" Tab                    
                    if not mkey.count("mgt_") and mkey not in ["time", "latest_update"] :
                        continue
                    
                    if _obj_type != "VM" :
                        continue
                    key = mkey
                    value = mvalue

                    if key.count("mgt") :
                        metric_type = 'p'

                        if key.count("originated") :
                            unit = "epoch"
                        elif key.count("sla_provisioning") :
                            unit = ' '
                        else :
                            if key.count("mgt_") :
                                unit = "secs"

                    elif key.count("sla_provisioning") :
                        metric_type = 'p'
                        unit = 'secs'
                        
                    else: 
                        metric_type = 's'
                        unit = 's'

                else :
                    # This path gathers metrics to display on the "* Performance" Tab
                    key = mkey
                    value = mvalue["val"]
                    unit = mvalue['units']

                    if "avg" in mvalue :
                        average = mvalue["avg"]

                    if "max" in mvalue :
                        max = mvalue["max"]

                    if "min" in mvalue :
                        max = mvalue["min"]

                    if "acc" in mvalue :
                        acc = mvalue["acc"]
                                            
                    if _obj_type == "HOST" :
                        metric_type = 'h'
                    else :
                        if key.count("app_") :
                            metric_type = 'a'                         
                        else :
                            metric_type = 's'
                
                # Do not parse metrics if the user does not want to see them
                if metric_type not in self.show or not self.show[metric_type] :
                    continue
                
                if (metric_type + "-" + key) in self.filters :
                    continue
                    
                if _obj_type == "VM" :
                    newkey = key.replace(attrs["role"], "")
                else :
                    newkey = key
                    
                # Perform any necessary summaries if the user requests them
                value, unit = summarize(self.summaries, value, unit)
                                                
                row_indexer[metric_type][newkey] = {}
                row_indexer[metric_type][newkey]["val"] = value
                
                if average :
                    row_indexer[metric_type][newkey]["avg"] = average

                if max :
                    row_indexer[metric_type][newkey]["max"] = max

                if min :
                    row_indexer[metric_type][newkey]["min"] = min

                if acc :
                    row_indexer[metric_type][newkey]["acc"] = acc
                                    
                accumulate_units[metric_type][newkey] = unit 
                    
            # We also want some "common" columns to be at the front of 
            # every category, like name and IP address to make the dashboard
            # easier to follow
            for label in (self.labels) :
                for metric_type in self.owners[_obj_type] :
                    if (metric_type + "-" + label) in self.filters :
                        continue
                    if label in attrs :
                        label_indexer[metric_type][label] = attrs[label]
                        print_labels[metric_type][label] = True
                    else :
                        label_indexer[metric_type][label] = "--"
                        print_labels[metric_type][label] = True
                    
            for metric_type in self.categories :
                # This number > 5 needs to be updated anytime the number of 'd3_*' values are
                # added to the row_indexer array
                if len(row_indexer[metric_type]) > 5 :
                    accumulate_rows[metric_type].append((label_indexer[metric_type], row_indexer[metric_type]))
                
        body = """
                <div class="hero-unit" style="padding: 5px" id='monitorsummary'>
                <h5>
        """
        body += "&nbsp;&nbsp;&nbsp;<b>Reporting</b>: " + str(reporting) + ", <b>Failed</b>: " + str(failed) + ", "
        body += "<b>Start time</b>: " + str(curr_time - self.start_time) + " secs ago. <b>Current Time</b>: " + makeTimestamp() + "\n"
        body += """
                </h5>
                </div>
                <div id='monitordata'>
        """

        # Now, dump the master dictionary according to category
        
        for dest in self.categories :
            unitkeys = list(accumulate_units[dest].keys())
            self.destinations[dest] = ""
            prefix_rows1 = []
            prefix_rows2 = []
            row1 = []
            row2 = []
            for label in (self.labels) :
                if label in print_labels[dest] :
                    prefix_rows1.append(label)
                    prefix_rows2.append("")
                    
            if len(unitkeys) > 0 :
                unitkeys.sort()
                
            for unit in unitkeys :
                row1.append(unit) 
                row2.append(accumulate_units[dest][unit]) 

            # First print the units and their corresponding common labels 
            current_labels = prefix_rows1 + row1
            self.destinations[dest] += self.makeRow(dest, current_labels, False, False, False, False, False, False, current_labels, bold = True, exclude = prefix_rows1)
            self.destinations[dest] += self.makeRow(dest, prefix_rows2 + row2, False, False, False, False, False, False, current_labels)
            
            # Dump the master dictionary into HTML
            for (label_dict, obj_dict) in accumulate_rows[dest] :
                uuid = obj_dict["d3_uuid"]
                name = obj_dict["d3_name"]
                ip = obj_dict["d3_ip"]
                host = obj_dict["d3_host"]
                role = obj_dict["d3_role"]
                del obj_dict["d3_uuid"]
                del obj_dict["d3_name"]
                del obj_dict["d3_host"]
                del obj_dict["d3_ip"]
                del obj_dict["d3_role"]
                row = []
                for label in (self.labels) :
                    if label in label_dict :
                        row.append(label_dict[label])
                                        
                for unit in unitkeys :
                    row.append(value_cleanup(obj_dict, unit))

                self.destinations[dest] += self.makeRow(dest, row, uuid, current_labels, name, ip, host, role, current_labels)
                        
        for dest in ['p', 'h', 's', 'a' ] :
            if not self.show[dest] :
                continue
            
            if dest not in self.destinations :
                continue
            
            if self.destinations[dest].strip() == "" :
                continue
                
            body += "<h3>" + self.categories[dest] + " Performance</h3>"
            body += "<div id='monitor" + dest + "'>"
            body += "<table class='table table-hover table-striped'>\n"
            body += self.destinations[dest]
            body += "</table>\n"
            body += "</div>\n"
        body += "</div>\n"

        self.body = body
        
        self.msci.disconnect()
        
    def prefix(self):
        return prefix(self.base_uri)# + "/monitor?rand=" + str(int(time())) + "&"

    def make_url(self) :
        url = self.prefix() + "/monitor?"

        # Inform the user of the configuration of this dashboard so that they
        # can save it to a configuration file later permanently
        for summ in list(self.summaries.keys()) :
            url += self.summaries[summ][1] + "=" + ("yes" if self.summaries[summ][0] else "no") + "&"

        for dest in ['p', 'h', 's', 'a' ] :
            url += dest + "=" + ("yes" if self.show[dest] else "no") + "&"
            
        if len(self.filters) :
            url += "filter="
            for dest in ['p', 'h', 's', 'a' ] :
                for gfilter in sorted(self.filters.keys()) :
                    if not gfilter.count(dest + "-") :
                        continue
                    url += gfilter + "," 

        return url[:-1]
        
    def build_and_send_header(self):
        output = ""
        output += """
       <div class="accordion" id="accordion2">
                <div class="accordion-group">
                  <div class="accordion-heading">
                    <a class="accordion-toggle" data-toggle="collapse" data-parent="#accordion2" href="#collapseOne">
                      Preferences 
                    </a>
                  </div>
                  <div id="collapseOne" class="accordion-body collapse in">

                    <div class="accordion-inner">
        """
        for dest in self.categories :
            output += " <a class='btn' href='" + self.prefix() + "/monitor?" + dest
            if self.show[dest] :
                output += "=no' target='_top'>Hide " + self.categories[dest] + "</a>"
            else :
                output += "=yes' target='_top'>Show " + self.categories[dest] + "</a>"
                
        for summ in list(self.summaries.keys()) :
            output += " <a class='btn' href='" + self.prefix() + "/monitor?"

            if self.summaries[summ][0] :
                output += self.summaries[summ][1] + "=no' target='_top'>Hide " + summ + "</a>"
            else :
                output += self.summaries[summ][1] + "=yes' target='_top'>Show " + summ + "</a>"
        
        output += """
                    </div>
                  </div>
                </div>
                <div class="accordion-group">
                  <div class="accordion-heading">
                    <a class="accordion-toggle" data-toggle="collapse" data-parent="#accordion2" href="#collapseTwo">
                      Filters 
                    </a>

                  </div>
                  <div id="collapseTwo" class="accordion-body collapse">
                    <div class="accordion-inner">
        """

        if len(self.filters) == 0 :
            output += "None"
        else :
            output += " <a class='btn' href='" + self.prefix() + "/monitor?removeall=1' target='_top'>Remove all filters</a>"
            for dest in ['p', 'h', 's', 'a' ] :
                output += "<br/><b>" + self.categories[dest] + " Filters:</b><br/>"
                for gfilter in sorted(self.filters.keys()) :
                    if not gfilter.count(dest + "-") :
                        continue
                    output += "[<a href='" + self.prefix() + "/monitor?remove=" + gfilter + "' target='_top'>X</a>] " + \
                        gfilter.split("-", 1)[1].replace("_", " ") + "&nbsp;"
            
        output += """
                    </div>
                  </div>
                </div>

                <div class="accordion-group">
                  <div class="accordion-heading">

                    <a class="accordion-toggle" data-toggle="collapse" data-parent="#accordion2" href="#collapseThree">
                      Save Prefs URL 
                    </a>
                  </div>
                  <div id="collapseThree" class="accordion-body collapse">
                    <div class="accordion-inner">
                    <b>Save Configuration URL</b>:<div style="font-size: xx-small">
        """

        output += self.make_url()

        output += """
                      </div>
                    </div>
                  </div>
                </div>
              </div> 
        """

        return output

    def parse_url(self, url):
        if not url.count("?") :
            return None, "nothing to parse"
        
        parameters = url.split("?")
        if len(parameters) != 2 :
            return False, 'We do not understand you!: ' + url
        
        attributes = parameters[1].split("&")
        
        if len(attributes) > 0 :
            for attr in attributes :
                pair = attr.split("=")
                if len(pair) != 2:
                    return False, 'We does not understand you!: ' + url
                key, value = pair 
                if key.strip() == "" or value.strip() == "":
                    return False, 'We does not understand you!: ' + url
                elif key == "remove" :
                    if value in self.filters :
                        del self.filters[value]
                elif key == "removeall" :
                    self.filters = {}
                elif key == "filter" :
                    filters = value.split(",")
                    for gfilter in filters :
                        self.filters[gfilter] = True
                elif key in self.show :
                    self.show[key] = True if value == "yes" else False
                else :
                    for summ in list(self.summaries.keys()) :
                        if key == self.summaries[summ][1] :
                            if value == "yes" :
                                self.summaries[summ][0] = True
                            else :
                                self.summaries[summ][0] = False 
                
        return True, ""
    
class Params(object) :
    def __init__(self, environ):
        self.pid = "none"
        self.http = Request(environ)  
        self.action = self.http.path[1:] if len(self.http.path) > 0 else None
        if self.action is None or self.action == "":
            self.action = "index"

        self.session = environ['beaker.session']
        if 'connected' not in self.session :
            self.session['connected'] = False
            if 'cloud_name' in self.session :
                del self.session['cloud_name']
                
        self.session.save()
        self.unparsed_uri = self.http.url
        self.uri = self.http.path
        self.active = None 
        self.active_obj = None 
        self.skip_show = False
        
        cbdebug("Request: " + self.unparsed_uri + " action: " + self.action)

class GUI(object):
    def __init__(self, apiport, apihost, branding):
        self.heromsg = "<div class='hero-unit' style='padding: 5px'>"
        self.spinner = "<img src='CBSTRAP/spinner.gif' width='15px'/>&nbsp;"
        brandparts = branding.split(",")
        self.branding = brandparts[0]
        self.brandurl = brandparts[2]
        self.brandiconsize = brandparts[1]
        self.apihost = apihost
        self.apiport = apiport
        self.pid = "none"
        self.data_links = {'vm' : 's', 'vmc' : 'h', "host" : 'h', "app" : 'a', 'appdrs' : 'p'}
        self.data_names = {'vm' : 'System', 'vmc' : 'System', "host" : 'System', "app" : 'App', 'appdrs' : 'Provision'}

        if self.apihost == "0.0.0.0" :
            self.apihost = "127.0.0.1"

        self.api_access = "http://" + self.apihost + ":" + str(self.apiport)
        self.api = APIClient(self.api_access)
            
        self.keys = [ "name", "size", "role", "type", "cloud_ip", "age", "state", "vmc_name", "host_name", "ai_name", "aidrs_name" ]
        self.menu = [ 
             ("provision" , ("/provision", "<i class='icon-home'></i>Provisioning")), 
             ("monitor" , ("/monitor", "<i class='icon-heart'></i>&nbsp;Dashboard")),
             ("stats" , ("/stats", "<i class='icon-list-alt'></i>&nbsp;Statistics")),
             ("config" , ("/config", "<i class='icon-wrench'></i>&nbsp;Configure")),
             ("d3" , ("/d3", "<i class='icon-picture'></i>&nbsp;Graphs")),
        ]
        
        # Replacements must be in this order
        
        self.replacement_keys = [ 
                "BOOTNAV", "BOOTCLOUDNAME", "BOOTCLOUDS", "BOOTAVAILABLECLOUDS", "BOOTBODY", "BOOTSHOWPOPOVER", \
                "BOOTSPINNER", "BOOTDEST", "BOOTACTIVE", "BOOTOBJECTNAME", \
                "BOOTSTRAP", "CBSTRAP", "BOOTBRAND", "BOOTICON", "BOOTCOMPANY" \
        ]
        
    def keyfunc(self, x):
        return int(x["counter"])
    
    def trackingfunc(self, x):
        return float(x["order"])

    def __call__(self, environ, start_response):
        # Hack to make WebOb work with Twisted
        setattr(environ['wsgi.input'], "readline", environ['wsgi.input']._wrapped.readline)

        req = Params(environ)
        req.dest = prefix(req.unparsed_uri)
        
        try:
            resp = self.common(req)
        except exc.HTTPTemporaryRedirect as e :
            resp = e
            resp.location = req.dest + resp.location + req.active
        except exc.HTTPException as e:
            resp = e
        except Exception as e :
#            exc_type, exc_value, exc_traceback = sys.exc_info()
            resp = "<h4>Exception:</h4>"
            for line in traceback.format_exc().splitlines() :
                cberr(line)
                resp += "<br>" + line

        if isinstance(resp, str) or isinstance(resp, str):
            return Response(resp)(environ, start_response)
        else :
            return resp(environ, start_response)
        
    def list_objects(self, req, active, objs, link = True, icon = 'icon-refresh', label = 'label-info') :
        output = "\n<table>"
        mod = 10 if active not in ["vmc", "host"] else 1
        if len(objs) == 0 :
            output += "\n<tr><td>No data.</td></tr>"
        else :
            if "counter" in objs[0] :
                objs.sort(key=self.keyfunc)
            for idx in range(0, len(objs)) :
                obj = objs[idx]
                # appinit()/vminit() was used
                init_pending = True if ("tracking" in obj and str(obj["tracking"]).lower().count("paused waiting for run command")) else False 
                    
                if link :
                    if idx != 0 and (idx % mod) == 0 :
                        output += "\n<tr><td></td></tr>"
                    if idx == 0 :
                            output += "<tr>"
                    output += "<td>"
                else :
                    output += "\n<tr><td>"
    
                if link :
                    output += "<a class='btn btn-mini btn-info' href='BOOTDEST/provision?object=" + active + "&explode=" + obj["uuid"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;"
                else :
                    if not init_pending :
                        if not icon :
                            output += "BOOTSPINNER&nbsp;"
                        output += "<span class='label " + label + "'>"
                        if icon :
                            output += "<i class='" + icon + " icon-white'></i>" + "&nbsp;&nbsp;"
    
                if not init_pending :
                    output += obj["name"]
                    
                    if link :
                        output += "</a>&nbsp;" 
                    else :
                        output += "</span>&nbsp;" 
    
                if not link  :
                    if init_pending :
                        output += "<a class='btn btn-mini btn-info' href='BOOTDEST/provision?object=" + active + "&operation=runstate&keywords=4&keyword1=" + obj["uuid"] + "&keyword2=attached&keyword3=run&keyword4=nosync'><i class='icon-play icon-white'></i>&nbsp;" + obj["name"] + "</a>&nbsp;&nbsp;"
                    if "order" in obj :
                        order = datetime.utcfromtimestamp(int(obj["order"].split(".")[0])).strftime('%m/%d %H:%M')
                    act = ((("[" + order + "] ")) if "order" in obj else "") + obj["tracking"] if "tracking" in obj else None
                    output += (str(act) if (act is not None and act != "None") else "")
                output += "</td>"
   
        output += "</tr>\n"
        output += "</table>"
        return output
        
    def make_alter_form(self, req, uuid, obj, key, value) :
        output = "<form id='alter_form_" + key + "' style='margin: 0' action='BOOTDEST/provision' method='get'>"
        output += """
            <table><tr><td width='300px'>
                <button type="submit" class="btn btn-default">
                  <i class="icon-arrow-right icon-black"></i>&nbsp;<b>
        """
        output += key + "</b></button></td><td>"
        output += "<input type='hidden' name='alter' value='1'/>"
        output += "<input type='hidden' name='object' value='" + obj  + "'/>"
        output += "<input type='hidden' name='explode' value='" + uuid + "'/>"
        output += "<input type='hidden' name='key' value='" + key   + "'/>"
        output += "Value: <input id='alter_" + key + "' style='margin-top: 9px' type='text' name='value' value='" + value + "'/>"
        
        if value.lower() == "true" or value.lower() == "false" :
            togg = "True"
            if value.lower() == "true" :
                togg = "False"
            output += "<a id='alter_toggle_" + key + "' class=\"btn btn-default\">"
            output += "\n<script>\n"
            output += "$(\"#alter_toggle_" + key + "\").click(function() { \n$(\"#alter_" + key + "\").val(\"" + togg + "\");\n\n"
            output += "$(\"#alter_form_" + key + "\").submit();\n"
            output += " });\n</script>"
            output += """
                  <i class="icon-arrow-left icon-black"></i>&nbsp;<b>toggle</b></a>
            """
        output += "</td></tr></table></form>"
        return output
    
    def make_config_form(self, req, category, name, label, default) :
        output = ""
        output += "<form id=\"config_form_" + label + "\" style='margin: 0' action='BOOTDEST/config' method='get'>"
        output += """
            <table><tr><td width='300px'>
                <button type="submit" class="btn btn-default">
                  <i class="icon-arrow-right icon-black"></i>&nbsp;<b>
        """
        output += label + "</b></button></td><td>"
        
        
        output += "Value: <input id='config_" + label + "' style='margin-top: 9px' type='text' name='value' value='" + default + "'/>"
        output += "<input type='hidden' name='category' value='" + category + "'/>"
        output += "<input type='hidden' name='name' value='" + name  + "'/></td>"
        
        if default.lower() == "true" or default.lower() == "false" :
            togg = "True"
            if default.lower() == "true" :
                togg = "False"
            output += "<td><a id='config_toggle_" + label + "' class=\"btn btn-default\">"
            output += "<script>\n"
            output += "$(\"#config_toggle_" + label + "\").click(function() { \n$(\"#config_" + label + "\").val(\"" + togg + "\");\n\n"
            output += "$(\"#config_form_" + label + "\").submit();\n"
            output += " });</script>"
            output += """
                  <i class="icon-arrow-left icon-black"></i>&nbsp;<b>toggle</b></a></td>
            """
            
        output += "</tr></table></form>"
        
        return output
        
    def repopulate_views(self, session) :
        session['discover_hosts'] = self.api.cldshow(session['cloud_name'], "vmc_defaults")["discover_hosts"].strip().lower()
        session['networks'] = ['default']
        ai_templates = self.api.cldshow(session['cloud_name'], "ai_templates")
        for key in ai_templates :
            if key.count("virtnet_template") :
                for network in ai_templates[key].strip().split(",") :
                    if network not in session['networks'] :
                        session['networks'].append(network)
                
        session["attach_params"] = {
                    "vm" : { 
                              "keyword1" : { "label" : "Role", "values" : [x.strip() for x in self.api.rolelist(session['cloud_name'])] } ,
                              "keyword2" : { "label" : "Pool / Host", "values" : ["auto"] + [x.strip() for x in self.api.poollist(session['cloud_name'])] \
                                                            + ([x["name"].replace("host_", "") for x in self.api.hostlist(session['cloud_name'])] if session["discover_hosts"] == "true" else [])},
                              "keyword3" : { "label" : "Meta Tags", "values" : "empty" },
                              "keyword4" : { "label" : "Size", "values" : "default" } ,
                              "keyword5" : { "label" : "Pause Step", "values" : [["continue" , "None"], 
                                                                                 ["pause_provision_started", "Pause at the end of step 2 (Provision Started)"], 
                                                                                 ["execute_provision_started", "Execute script at the end of step 2 (Provision Started)"],
                                                                                 ["pause_provision_complete", "Pause at the end of step 3 (Provision Complete)"], 
                                                                                 ["execute_provision_started", "Execute script at the end of step 3 (Provision Complete)"],
                                                                                 ["pause_all_vms_booted", "Pause at the beginning of step 5 (Application Start)"],
                                                                                 ["execute_all_vms_booted", "Execute script at the beginning of step 5 (Application Start)"]
                                                                                 ] } ,
                              "keyword6" : { "label" : "Temporary Attributes", "values" : "" } ,
                              "keyword7" : { "label" : "Mode", "values" : "nosync" }
                           },
                    "app" : { 
                              "keyword1" : { "label" : "Type", "values" : [x.strip() for x in self.api.typelist(session['cloud_name'])] } ,
                              "keyword2" : { "label" : "Load Level", "values" : "default" } ,
                              "keyword3" : { "label" : "Load Duration", "values" : "default" } ,
                              "keyword4" : { "label" : "Lifetime", "values" : "none" } ,
                              "keyword5" : { "label" : "Submitter", "values" : "none" } ,
                              "keyword6" : { "label" : "Pause Step", "values" : [["continue" , "None"], 
                                                                                 ["pause_provision_started", "Pause at the end of step 2 (Provision Started)"], 
                                                                                 ["execute_provision_started", "Execute script at the end of step 2 (Provision Started)"],
                                                                                 ["pause_provision_complete", "Pause at the end of step 3 (Provision Complete)"], 
                                                                                 ["execute_provision_started", "Execute script at the end of step 3 (Provision Complete)"],
                                                                                 ["pause_all_vms_booted", "Pause at the beginning of step 5 (Application Start)"],
                                                                                 ["execute_all_vms_booted", "Execute script at the beginning of step 5 (Application Start)"],
                                                                                 ] } ,
                              "keyword7" : { "label" : "Temporary Attributes", "values" : "" } ,
                              "keyword8" : { "label" : "Mode", "values" : "nosync" } ,
                            },
                    "vmc" : { 
                             "keyword1" : { "label" : "Name", "values" : "" } ,
                             "keyword2" : { "label" : "Temporary Attributes", "values" : "" },
                             "keyword3" : { "label" : "Mode", "values" : "nosync" },
                             }, 
                    "appdrs" : { "keyword1" : { "label" : "Pattern", "values" : [x.strip() for x in self.api.patternlist(session['cloud_name'])] },
                                "keyword2" : { "label" : "Temporary Attributes", "values" : "" }
                            },
        }
        session['views'] = self.api.viewlist(session['cloud_name'])
        session['views']['appdrs'] = session['views']['aidrs']
        session.save()
        
    def d3_process(self, mon, data, result, category, label):
        fin = 0
        for document in data:
            if fin % 500 == 0 :
                print(("finished " + str(fin) + " records so far"))
            fin += 1
            if(category == 'p' and mon.is_failed_vm(document)) :
                continue
            #del documents["_id"]
            if category == 'p' :
                record = {label : document[label], "mgt_001_provisioning_request_originated" : document["mgt_001_provisioning_request_originated"]}
            else :
                record = {label : document[label], "time" : document["time"]}

            result.append(record)

    def common(self, req) :
        try :
            if req.http.params.get("connect") :
                if req.http.params.get("available") or req.http.params.get("definition_contents") :
                    requested_cloud_name = req.http.params.get("available").lower()
                    if req.http.params.get("definition_contents") :
                        definitions = req.http.params.get("definition_contents")
                    else :
                        definitions = req.session["definitions"]
                    available_result = self.api.cldparse(definitions)
                    available_clouds = available_result["clouds"]
                    uni_attrs = available_result["attributes"]
                    for cloud_name in available_clouds :
                        cloud_name = cloud_name.lower()
                        if cloud_name == requested_cloud_name :
                            for command in available_clouds[cloud_name] :
                                kwargs = {}
                                if command.count("nosync") :
                                    kwargs["nosync"] = True
                                    command.replace("nosync", "")
                                    
                                parts = command.split()
                                
                                if parts[0] == "clddefault" :
                                    continue
                                
                                if len(parts) < 2 :
                                    return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>", error = True)
                                    
                                try :
                                    func = getattr(self.api, parts[0])
                                except AttributeError as msg :
                                    return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>", error = True)
                                
                                if parts[0] != "cldattach" and 'cloud_name' in req.session and not command.lower().count(req.session['cloud_name'].lower()) :
                                    fixed = [parts[0], req.session['cloud_name']] + parts[1:]
                                else :
                                    fixed = parts
                                
                                if fixed[0] == "vmcattach" and fixed[2] == "all" :
                                    if len(fixed) < 2 :
                                        return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>", error = True)
                                    if not command.count("nosync") :
                                        kwargs["nosync"] = "nosync"
                                if fixed[0] == "cldattach" :
                                    if len(fixed) < 3 :
                                        return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>", error = True)
                                    if len(fixed) == 3 :
                                        fixed.append(definitions)
                                    kwargs["uni_attrs"] = uni_attrs
                                    
                                func(*fixed[1:], **kwargs)
                                
                                if fixed[0] == "cldattach" :
                                    req.session['model'] = fixed[1]
                                    req.session['cloud_name'] = fixed[2]
                                    req.session.save()
                            break
                             
                elif req.http.params.get("running") :
                    req.session['model'], req.session['cloud_name'] = req.http.params.get("running").split(",")
                    req.session.save()
                else :
                    fh = req.http.params.get("definitions")
                    definitions = fh.file.read()
                        
                    available_clouds = self.api.cldparse(definitions)["clouds"]
                    if not len(available_clouds) :
                        req.skip_show = True
                        response_fd = open(cwd + "/gui_files/response_template.html", "r")
                        response = response_fd.read().replace(" ", "&nbsp;")
                        response_fd.close()
                        return self.bootstrap(req, self.heromsg + "\n<h4>" + response + "</h4></div>", error = True)
                    
                    req.session["available_clouds"] = available_clouds
                    req.session["definitions"] = definitions
                    req.session.save()
                    return self.bootstrap(req, self.heromsg + "\n<h4>Configuration uploaded and ready.<br>Please select from an available cloud.</h4></div>")
                    
                    
                req.session["dashboard_parameters"] = self.api.cldshow(req.session['cloud_name'], "dash_defaults")["dashboard_parameters"]
                req.session['time_vars'] = self.api.cldshow(req.session['cloud_name'], "time")
                req.session['msattrs'] = self.api.cldshow(req.session['cloud_name'], "metricstore")
                req.session["liststates"] = { 
                                            "save" : [0, "Saved"], 
                                            "fail" : [1, "Suspended"], 
                                            "attached": [2, "Running"], 
                                            "all" : [3, "All"]
                                        }
    
                self.repopulate_views(req.session)
    
                req.session["operations"] = {
                    "attach" : [0, {"operations" : [ "vm", "vmc", "app", "appdrs"], "icon" : "play", "state" : "any" } ], 
                    "detach" : [1, {"operations" : [ "vm", "vmc", "app", "appdrs"], "icon" : "trash", "state" : "any" } ], 
                    "save" : [2, {"operations" : [ "vm", "vmc", "app"], "icon" : "stop", "state" : "attached" } ], 
                    "restore" : [3, {"operations" : [ "vm", "vmc", "app"], "icon" : "play", "state" : "save" } ], 
                    "suspend" : [4, {"operations" : [ "vm", "vmc", "app"], "icon" : "pause", "state" : "attached" } ], 
                    "resume" : [5, {"operations" : [ "vm", "vmc", "app"], "icon" : "play", "state" : "fail" } ], 
                    "runstate" : [6, {"operations" : [ "vm", "app"], "icon" : "play", "state" : "any" } ],
                    "migrate" : [7, {"operations" : [ "vm" ], "icon" : "share-alt" , "state" : "attached" } ], 
                    "protect" : [8, {"operations" : [ "vm" ], "icon" : "star" , "state" : "attached" } ], 
                    "unprotect" : [9, {"operations" : [ "vm" ], "icon" : "ok" , "state" : "protected"} ], 
                    "fail" : [10, {"operations" : [ "vm" ], "icon" : "fire", "state" : "protected" } ], 
                }
                
                for operation in list(req.session["operations"].keys()) :
                    req.session["operations"][operation][1]["label"] = operation[0].upper() + operation[1:]
    
                req.session["objects"] = { 
                     "vmc": [ 0, "Regions" ],
                     "host": [ 1, "Hypervisors" ],
                     "app": [ 2, "Virtual Applications" ],
                     "vm": [ 3, "Virtual Machines" ],
                     "appdrs": [ 4, "Application Submitters" ],
                     #"vmcrs": [ 5, "Capture Submitters" ],
                } 
    
                req.action = "provision"
                req.active = "vmc"
                req.session['connected'] = True 
                req.session['last_active'] = "app"
                req.session['dash_active'] = "a"
                req.session["last_refresh"] = str(time())
                req.session.save()
    
            if req.session['connected'] :
                req.cloud_name = req.session['cloud_name']
                req.model = req.session['model']
            else :
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                if not req.action.count("wizard") :
                    return self.bootstrap(req, self.heromsg + "\n<h4>You need to connect, first.</h4></div>")

            expid = self.api.cldshow(req.cloud_name, "time")["experiment_id"]
                
            if req.action == "monitor" : 
                if req.http.params.get("show") is not None :
                    req.session['dash_active'] = req.http.params.get("show")
                    req.session.save()
                self.api.dashboard_conn_check(req.cloud_name, msattrs = req.session['msattrs'], username = req.session['time_vars']['username'])
                
                mon = Dashboard(self.api.msci, req.unparsed_uri, req.session['time_vars'], req.session['msattrs'], req.cloud_name)
                orig_url = req.session["dashboard_parameters"]
                success, msg = mon.parse_url(orig_url)
    
                if success or success is None :
                    success, msg = mon.parse_url(req.unparsed_uri)
                    if success and success is not None :
                            new_url = mon.make_url()
                            if new_url != orig_url :
                                self.api.cldalter(req.cloud_name, "dash_defaults", "dashboard_parameters", new_url)
                                req.session["dashboard_parameters"] = new_url
                                req.session.save()
    
                monitor_fd = open(cwd + "/gui_files/monitor_template.html", "r")
                output = monitor_fd.read()
                monitor_fd.close()
                output = output.replace("BOOTMONITOR", mon.build_and_send_header())
    
                tabs = ""
                for category in mon.categories :
                    tabs += "<li><a data-toggle='tab' href=\"#tab" + category + "\">" + mon.categories[category] + " Performance</a></li>" 
                tabs += "</ul>\n"
                
                tabs += """
                    <div class='tab-content'>
                    <div class='tab-pane' id='taball'></div>
                """
    
                for category in mon.categories :
                    tabs += "<div class='tab-pane' id='tab" + category + "'>BOOTSPINNER&nbsp;Loading...</div>"
                output = output.replace("BOOTTABS", tabs)
                output = output.replace("BOOTSHOW", req.session["dash_active"])
                
                return self.bootstrap(req, output if (success or success is None) else msg)
    
            elif req.action == "config" :
                result = ""
                if req.http.params.get("category") is not None :
                    result += self.heromsg + "\n<h4>"
                    msg = "object: " + req.http.params.get("category") + ": " + req.http.params.get("name") + "=" + req.http.params.get("value")
                    try :
                        self.api.cldalter(req.cloud_name, req.http.params.get("category"), req.http.params.get("name"), req.http.params.get("value"))
                        result  += "Successfully altered " + msg
                    except APIException as obj :
                        result += "Failed to alter " + msg + ": " + obj.msg
                    result += "</h4></div>"
                        
                output = """
                    <div class='span10'>
                    <div class='row'>
                    <div class="span3 bs-docs-sidebar">
                        <ul data-spy='affix' class="pager nav nav-list bs-docs-sidenav">
                """
                
                settings = self.api.cldshow(req.cloud_name, "all")
                for category in sorted(settings.keys()) :
                    printable = " ".join(category.upper().split("_")).replace("DEFAULTS", "defaults").replace("TEMPLATES", "templates")
                    output += "<li align='left'><a href='#" + category + "'><i class='icon-chevron-right'></i>" + printable + "</a></li>"
                output += """
                        </ul>
                      </div><div class='span9'>
                """            
                
                output += result
                
                for category in sorted(settings.keys()) :
                    printable = " ".join(category.upper().split("_")).replace("DEFAULTS", "defaults").replace("TEMPLATES", "templates")
                    output += "<section id='" + category + "'>"
                    output += "<div class='page-header'>"
                    output += "<h1 class='anchor'>" + printable + "</h1>"
                    output += "</div>"
                    output += "<div class='accordion' id='config" + category + "'>"
                    
                    single = True if len(settings[category]) == 1 else False
                    
                    for subkey in sorted(settings[category].keys()) :
                        sub = settings[category][subkey]
                        collapse = isinstance(sub, list)
                        
                        if collapse and not single:
                            output += """
                                    <div class="accordion-group">
                                        <div class="accordion-heading">
                            """
                            output += "<a class='accordion-toggle' data-toggle='collapse' data-parent='#config" + category + "' href='#collapse" + category + subkey + \
                                        "'><i class='icon icon-arrow-down'></i>" + subkey  + "</a>"
                            output += "</div>\n"
                            output += "<div id='collapse" + category + subkey  + "' class='accordion-body collapse'>"
                            output += "<div class='accordion-inner'>"
                        
                        if collapse : 
                            for (suffix, value) in sub :
                                output += self.make_config_form(req, category, subkey + "_" + suffix, suffix, value)
                        else :
                            output += self.make_config_form(req, category, subkey, subkey, sub)
                            
                        if collapse and not single:
                            output += """
                                      </div>
                                    </div>
                                  </div>
                            """
                            
                    output += """
                            </div>
                    """
                    output += "</section>"
                output += "</div><!--span9-->"
                output += "</div><!--row-->"
                output_fd = open(cwd + "/gui_files/cli_template.html", "r")
                output += output_fd.read()
                output_fd.close()
                return self.bootstrap(req, output)
            elif req.action == "data" :
                uuid = req.http.params.get("uuid")
                category = req.http.params.get("category")
                label = req.http.params.get("label")
                name = req.http.params.get("name")
                ip = req.http.params.get("ip")
                host = req.http.params.get("host")
                role = req.http.params.get("role")
                self.api.dashboard_conn_check(req.cloud_name, msattrs = req.session['msattrs'], username = req.session['time_vars']['username'])
                mon = Dashboard(self.api.msci, req.unparsed_uri, req.session['time_vars'], req.session['msattrs'], req.session['cloud_name'])
                result = []
                if category != 'p' :
                    data = mon.msci.find_document(mon.collections[category], {"expid": expid, "uuid" : uuid, label : { "$exists" : True} }, True)
                else :
                    data = mon.msci.find_document(mon.collections[category], {"expid": expid}, True)
#                p = multiprocessing.Process(target = self.d3_process, args = (mon, data, result, category, label))
#                p.start()
#                p.join()
                self.d3_process(mon, data, result, category, label)
                result[0]["d3_label"] = label
                result[0]["d3_category"] = category 
                result[0]["d3_uuid"] = uuid 
                result[0]["d3_name"] = name 
                result[0]["d3_ip"] = ip 
                result[0]["d3_host"] = host 
                result[0]["d3_role"] = role 
                return self.bootstrap(req, str(json.dumps(result, skipkeys=True)), now = True)
            elif req.action == "d3" :
                if req.http.params.get("clear") :
                    req.session["graphs"] = []
                    req.session.save()
                    return self.bootstrap(req, self.heromsg + "\n<h4>Graphs cleared.</h4></div>", error = True)
                    
                if "graphs" not in req.session :
                    req.session["graphs"] = []
                    
                d3_fd = open(cwd + "/gui_files/d3_template.html", "r")
                d3_html = d3_fd.read()
                d3_fd.close()
                uuid = req.http.params.get("uuid")
                category = req.http.params.get("category")
                label = req.http.params.get("label")
                name = req.http.params.get("name")
                ip = req.http.params.get("ip")
                host = req.http.params.get("host")
                role = req.http.params.get("role")
               
                graphs = len(req.session["graphs"]) 
                
                if uuid and category and label and name and ip and host and type:
                    d3data = "uuid=" + str(uuid) + "&category=" + str(category) + "&label=" + str(label) + "&name=" + str(name) + "&ip=" + str(ip) + "&host=" + str(host) + "&role=" + str(role)
                    if d3data not in req.session["graphs"] :
                        if graphs == 4 :
                            req.session["graphs"] = req.session["graphs"][1:]
                            graphs -= 1
                            
                        req.session["graphs"].append(d3data)
                        graphs += 1
                     
                if graphs:
                    req.session.save()
                    array_string = ""
                    for x in range(0, int(graphs)) :
                        array_string += "\"" + req.session["graphs"][x] + "\","
                    array_string = array_string[:-1]
                    d3_html = d3_html.replace("D3DATA", array_string)
                else :
                    return self.bootstrap(req, self.heromsg + "\n<h4>No graphs requests yet:<p>Add graphs to this screen by choosing a *specific* data cell from the dashboard! Do not click on the columns or you will accidentally filter that column from view. Click on a specific cell to graph that metric over time for a specific host or specific VM and it will be added here.</h4></div>", error = True)
                return self.bootstrap(req, d3_html)
            elif req.action == "wizard" :
                wizard_fd = open(cwd + "/gui_files/wizard_template.html", "r")
                wizard_html = wizard_fd.read()
                wizard_fd.close()
                return self.bootstrap(req, wizard_html) 
            
            elif req.action == "wizard_options" :
                '''
                Return raw JSON and deal with it in the browser.
                '''
                return self.bootstrap(req, json.dumps(self.api.cldparse('')['attributes'], sort_keys = True, indent = 4), now = True)
    
            elif req.action == "monitordata" :

                self.api.dashboard_conn_check(req.cloud_name, msattrs = req.session['msattrs'], username = req.session['time_vars']['username'])
                mon = Dashboard(self.api.msci, req.unparsed_uri, req.session['time_vars'], req.session['msattrs'], req.session['cloud_name'])
                mon.parse_url(req.session["dashboard_parameters"])
                mon.gather_contents(expid)
                output_fd = open(cwd + "/gui_files/cli_template.html", "r")
                cli_html = output_fd.read()
                output_fd.close()
                return self.bootstrap(req, "<div class='span10'>" + mon.body + cli_html)

            elif req.action == "stats" :
                try :
                    stats = self.api.stats(req.cloud_name)
                    output = "<div class='span10'>"
                    output += self.heromsg + "\n<h4>&nbsp;&nbsp;Runtime Summary Statistics:</h4></div>\n"
                    output += "<div class='accordion' id='statistics'>\n"
                    
                    cbdebug(str(stats))
                    for group_key in list(stats.keys()) :
                        group = group_key.replace("_", " ")
                        output += """
                                <div class="accordion-group">
                                <div class="accordion-heading">
                        """
                        output += "<a class='accordion-toggle' data-toggle='collapse' data-parent='#statistics' href='#collapse" + group_key + "'>" + group + "</a>"
                        output += "</div>\n"
                        output += "<div id='collapse" + group_key + "' class='accordion-body collapse'>"
                        output += "<div class='accordion-inner'>"
                        for label, stat in list(stats[group_key].items()) :
                            output += "<table class='table table-hover table-striped'>\n"
                            output += "<tr><td><b>" + label + "</b></td></tr>\n"
                            for name, value in list(stats[group_key].items()) :
                                output += "<tr><td>" + name + "</td><td>" + str(value) + "</td></tr>\n"
                            output  += "</table>"
                    
                        output += """
                            </div>
                           </div>
                         </div>
                        """
                    output += """
                        </div>
                    """
                    output_fd = open(cwd + "/gui_files/cli_template.html", "r")
                    cli_html = output_fd.read()
                    output_fd.close()
                    output += cli_html
                    return self.bootstrap(req, output)
                except Exception as e:
                    for line in traceback.format_exc().splitlines() :
                        cbdebug(line)
                    return self.bootstrap(req, str(e))
            elif req.action == "commands" :
                self.api.dashboard_conn_check(req.cloud_name, msattrs = req.session['msattrs'], username = req.session['time_vars']['username'])
                contents = """
                    <div id='commandcontent'>
                            <table class='table table-hover table-striped'>
                    """
                    
                result = []
                commands = self.api.msci.find_document("trace_" + req.session['time_vars']["username"], criteria = {"expid": expid}, sortkeypairs = [("command_originated" , -1)], allmatches = True, limitdocuments = 10, documentfields = ["command"], disconnect_finish = True)
                for command in commands :
                    command = command["command"].replace(req.cloud_name, "")
                    contents += "<tr><td style='word-break: break-all;'>" + command.replace("default", "").replace("none", "").strip() + "</td></tr>"
    
                contents += """
                        </table></div>
                """
                return self.bootstrap(req, contents)
            elif req.action in ["provision", "index"] :
                req.action = "home"
                output_fd = open(cwd + "/gui_files/cli_template.html", "r")
                cli_html = output_fd.read()
                output_fd.close()
                tmp = self.default(req, \
                                   req.http.params, \
                                   req.session["attach_params"], \
                                   req.session['views'], \
                                   req.session["operations"], \
                                   req.session["objects"], \
                                   req.session["liststates"], \
                                   req.session["last_active"])
                                   
                return self.bootstrap(req, "<div class='span10'>" + tmp + cli_html) 
                                              
            elif req.action == "disconnect" :
                req.session['connected'] = False
                del req.session['cloud_name']
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                return self.bootstrap(req, self.heromsg + "\n<h4>Disconnected from API @ " + self.api_access + "</h4></div>")
            
            elif req.action == "detach" :
                output = ""
                output_fd = open(cwd + "/gui_files/detach_template.html", "r")
                output += output_fd.read()
                output_fd.close()
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                return self.bootstrap(req, self.heromsg + "\n<h4>" + output + "</h4></div>", pretend_disconnected = True)
                
            elif req.action == "detach_actual" :
                cn = req.session['cloud_name']
                req.session['connected'] = False
                del req.session['cloud_name']
                result = self.api.clddetach(req.cloud_name) 
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                return self.bootstrap(req, self.heromsg + "\n<div id='detachresponse'><h4>Detached from Cloud: " + cn + " successfully.</h4></div></div>")
            elif req.action.count("broadway") :
                return self.bootstrap(req, self.heromsg + "\n<h4>Broadway GTK request missing 'port' parameter in URL line. Try again.</h4></div>", error = True)
            elif req.action.count("gtk") :
                uuid = req.http.params.get("uuid")
                operation = req.http.params.get("operation")
                if uuid and operation :
                    if operation == "login" :
                        portinfo = self.api.vmlogin(req.cloud_name, uuid)
                    elif operation == "display" :
                        portinfo = self.api.vmdisplay(req.cloud_name, uuid)
                    return self.bootstrap(req, self.heromsg + "\n<div id='gtkresponse'>" + \
                                          "<h4>GTK broadway request success: Port</h4></div></div><div id='gtkport'>" + str(portinfo["gtk_" + operation + "_port"]) + "</div>")
                else :
                    return self.bootstrap(req, self.heromsg + "\n<h4>Broadway GTK request missing parameters. Try again.</h4></div>", error = True)
            
            return self.bootstrap(req, self.heromsg + "\n<h4>We do not understand you! Try again...</h4></div>", error = True)
    
        except APIException as obj :
            return self.bootstrap(req, self.heromsg + "\n<h4 id='gerror'>Error: API Service says:" + str(obj.status) + ": " + obj.msg.replace("<", "&lt;").replace(">", "&gt;").replace("\\n", "<br>").replace("\n", "<br>") + "</h4></div>", error = True)
        except IOError as msg : 
            return self.bootstrap(req, self.heromsg + "\n<h4 id='gerror'>Error: API Service (" + self.api_access + ") is not responding: " + str(msg) + "</h4></div>", error = True)
        except socket.error as v:
            return self.bootstrap(req, self.heromsg + "\n<h4 id='gerror'>Error: API Service (" + self.api_access + ") is not responding: " + str(v) + "</h4></div>", error = True)
        except exc.HTTPTemporaryRedirect as e :
            raise e
        except Exception as msg:
            for line in traceback.format_exc().splitlines() :
                cbdebug(line)
            print(("Exception: " + str(msg)))
            _msg = self.heromsg + "\n<h4 id='gerror'>Error: Something bad "
            _msg += "happened while executing the action " + str(req.action) + ": " + str(msg) + "</h4></div>"
            for line in traceback.format_exc().splitlines() :
                _msg += "<br>" + line
            return self.bootstrap(req, _msg)
        
    def default(self, req, params, attach_params, views, operations, objects, liststates, last_active):
        if not req.active : 
            req.active = params.get("object", last_active)
        if req.active != last_active :
            req.session['last_active'] = req.active
            req.session.save()
        req.active_obj = ""
        active_list = getattr(self.api, req.active + "list")
        liststate = params.get("liststate", "all")
        view = params.get("view", "")
    
        output = """
            <script>active = 'BOOTACTIVE';</script>
            <div>
            <ul id='one' class="nav nav-tabs">
        """
    
        for obj, label in sorted(iter(list(objects.items())), key=itemgetter(1)) :
            output += "<li "
            if req.active == obj :
                    output += "class='active'"
                    req.active_obj = label[1] 
            output += "><a href='BOOTDEST/provision?object=" + obj + "'>" + label[1] + "</a> </li>"
    
        output += """
            </ul>
            </div>
            <div class="row-fluid">
             <div class="span1">
        """
    
        if req.active in views :
            found_view = False
            if req.active != "host" :
                output += """
                    <a id='attachpop' class='btn btn-success' style='padding: 3px' href='#'><i class='icon-play icon-white'></i>&nbsp;Create</a>
                    <p/>
                    <p/>
                """
                output += "<a class='btn btn-danger' style='padding: 3px' href='BOOTDEST/provision?object=" + req.active \
                    + "&operation=detach&keywords=3&keyword1=all&keyword2=true&keyword3=nosync'><i class='icon-trash icon-white'></i>&nbsp;Detach All</a>"
                
            output += """
                <p/>
                <div class='tabbable tabs-left'>
                <ul id='two' class="nav nav-tabs">
            """
    
            for obj, attrs in sorted(iter(list(views[req.active].items())), key=itemgetter(1)) :
                criterion = attrs[1]["criterion"].strip()
                expressions = attrs[1]["expression"]
                dropdown = isinstance(expressions, list)
                liclass = ''
                if dropdown :
                    liclass += 'dropdown'
    
                if view == obj :
                        found_view = True
                        liclass += ' active'
    
                if liclass.strip() != '' :
                    output += "<li class='" + liclass + "'>"
                else :
                    output += "<li>"
    
                output += "<a "
    
                if dropdown :
                    output += "class='dropdown-toggle' data-toggle='dropdown' href='#'"
                else :
                    output += "href='BOOTDEST/provision?view=" + obj + "&criterion=" + criterion + "&expression=" + expressions.strip() + "&object=BOOTACTIVE'"
    
                output += ">" + attrs[1]["label"] 
    
                if dropdown :
                    output += "<b class='caret'></b>"
    
                output += "</a>"
    
                if dropdown :
                    output += """
                            <ul class="dropdown-menu">
                    """
                    for expression in expressions :
                        expression = expression.strip()
                        output += "<li><a href='BOOTDEST/provision?view=" + obj + "&criterion=" + criterion + "&expression=" + expression + "&object=BOOTACTIVE'>" + expression + "</a></li>"
                    output += """
                            </ul>
                    """
                output += "</li>\n"
                
            for tempstate, state_attrs in sorted(iter(list(liststates.items())), key=itemgetter(1)) :
                output += "<li"
                if not found_view and liststate == tempstate : 
                    output += " class='active'"
                output += "><a href='BOOTDEST/provision?liststate=" + tempstate + "&object=BOOTACTIVE'>" + state_attrs[1] + "</a></li>" 
            output += """
                </ul>
                <p>
            """
            output +=  "<a id='showdata' class='btn btn-success' style='padding: 3px; align: center' href='BOOTDEST/monitor?show=" + self.data_links[req.active] + "'>"
            output += "<i class='icon-list-alt icon-white'></i>&nbsp;" + self.data_names[req.active] + " Data</a>"
            output += "</div>"
        else :
            output += "<h4>No Views Available</h4>"
    
        output += """
            </div>
            <div class='span11'>
            <table>
            <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>
        """
    
        if params.get("explode") is not None :
            uuid = params.get("explode")
            
            if params.get("alter") :
                try :
                    getattr(self.api, req.active + "alter")(req.cloud_name, uuid, params.get("key"), params.get("value"))
                    output += self.heromsg + "\n<h4>Successfully altered BOOTOBJECTNAME " + uuid  + " attribute " + params.get("key") + "=" + params.get("value") + "</h4></div>"
                except APIException as obj :
                    output += self.heromsg + "\n<h4>&nbsp;&nbsp;Error: Could not alter BOOTOBJECTNAME " + uuid + " attribute " + params.get("key") + " = " + params.get("value") + ": " + obj.msg + "</h4></div>"
                
            attrs = getattr(self.api, req.active + "show")(req.cloud_name, uuid)
            output += "<h2>BOOTOBJECTNAME: " + attrs["name"] + "</h2>"
            
            migrate_operations = []
            for operation, operation_attrs in sorted(iter(list(operations.items())), key=itemgetter(1)) :
                        
                keywords = {}
                label = operation_attrs[1]["label"]
                icon = operation_attrs[1]["icon"]
                
                if operation in ["migrate", "protect" ] and req.active == "vm" :
                    if attrs[operation + "_supported"].lower() == "true" :
                        migrate_operations.append(operation)
                        output += "&nbsp;&nbsp;<a id='" + operation + "pop' class='btn btn-success' style='padding: 3px' href='#'>"
                        output += "<i class='icon-" + icon + " icon-white'></i>&nbsp;" + label + "</a>"
                    continue
                
                keywords["keyword" + str(len(keywords) + 1)] = attrs["uuid"]
                
                if operation == "attach" or req.active not in operation_attrs[1]["operations"] :
                    continue
                elif operation == "detach" :
                    force = False
                    if "ai" in attrs and attrs["ai"] != "none" : 
                        force = True
                    elif "aidrs" in attrs and attrs["aidrs"] != "none" :
                        force = True
                    elif "mc_supported" in attrs and attrs["mc_supported"].lower() == "true" :
                        force = True
                    if force :
                        label = "Force " + label
                    keywords["keyword" + str(len(keywords) + 1)] = str(force).lower() 
                elif operation in [ "unprotect", "fail" ] :
                    if "mc_supported" not in attrs or attrs["mc_supported"].lower() != "true" :
                        continue
                elif operation in [ "runstate" ] :
                    continue
                elif operation == "protect" :
                    if "mc_supported" in attrs and attrs["mc_supported"].lower() == "true" :
                        continue
                elif operation  in [ "save", "suspend", "restore", "resume" ] :
                    if "mc_supported" in attrs and attrs["mc_supported"].lower() == "true" :
                        continue
                required = operation_attrs[1]["state"]
                if required != "any" and attrs["state"] != required  :
                    continue
                    
                keywords["keyword" + str(len(keywords) + 1)] = "nosync" 
                
                output += "&nbsp;&nbsp;<a Class='btn btn-danger btn-small' href='BOOTDEST/provision?object=" + req.active
                output += "&operation=" + operation
                
                output += "&keywords=" + str(len(keywords))
                for keyidx in range(1, len(keywords) + 1) :
                    key = "keyword" + str(keyidx)
                    output += "&" + key + "=" + keywords[key]
                output += "'><i class='icon-" + icon + " icon-white'></i>&nbsp;&nbsp;" + label + "&nbsp;&nbsp;</a>"
                
            if req.active == "vm" :
                output += """
                    <a id='loginClick' href="#loginModal" role="button" class="btn btn-success" data-toggle="modal"><i class="icon-white icon-hand-right"></i>&nbsp;&nbsp;Login</a>
                    <a id='displayClick' href="#displayModal" role="button" class="btn btn-success" data-toggle="modal"><i class="icon-white icon-facetime-video"></i>&nbsp;&nbsp;Display</a>
                    """
            
            for operation in migrate_operations :
                hosts =  self.api.hostlist(req.cloud_name)
                dest_choices = "<input type='hidden' name='keyword1' value='" + attrs["uuid"] + "'>"

                dest_choices += """
                        <tr><td>Destination</td>
                            <td><select name='keyword2'>
                    """
                    
                for host in hosts :
                    if host["uuid"] != attrs["host"] :
                        dest_choices += "<option value='" + host["name"] + "'>" + host["cloud_hostname"] + " (Iface: " + host[operation + "_interface"] + ")</option>"
                    
                dest_choices += """
                                </select>
                            </td>
                        </tr>
                       """
                       
                dest_choices += """
                      <tr><td>Protocol: </td>
                          <td><select name='keyword3'>
                    """
                    
                choices = attrs[operation + "_protocol_supported"].split(",")
                    
                for proto in choices :
                    dest_choices += "<option value='" + proto + "'"
                    if attrs[operation + "_protocol"].lower() == proto.lower() :
                        dest_choices += "selected"
                    dest_choices += ">" + proto.upper() + "</option>"
                    
                dest_choices += """
                                </select>
                            </td>
                        </tr>
                    """
                    
                operation_fd = open(cwd + "/gui_files/" + operation + "_template.html", "r")
                output += operation_fd.read().replace("BOOT" + operation.upper(), dest_choices)
                operation_fd.close()
                
            if req.active == "vm" :
                gtk_fd = open(cwd + "/gui_files/gtk_template.html", "r")
                gtk = gtk_fd.read()
                gtk = gtk.replace("BOOTID", attrs["uuid"])
                gtk_fd.close()
                output += gtk
                
            if req.active in ["app", "vmc", "host"] :
                output += """
                    <h3>Children: 
                """
                objs = []
    
                if req.active == "app" :
                    for vm in attrs["vms"].split(",") :
                        splitparts = vm.split("|")
                        uuid = splitparts[0]
                        name = splitparts[2]
                        objs.append({"name" : name, "uuid" : uuid}) 
                elif req.active == "vmc" :
                    for host in self.api.viewshow(req.cloud_name, "HOST", "VMC", attrs["uuid"]) :
                        objs.append(host) 
                elif req.active == "host" :
                    for vm in self.api.viewshow(req.cloud_name, "VM", "HOST", attrs["uuid"]) :
                        objs.append(vm) 
    
                output += self.list_objects(req, "host" if req.active == "vmc" else "vm", objs) + "</h3>"
    
            if req.active == "vm":
                output += "<h3>Region: <a class='btn btn-info' href='BOOTDEST/provision?object=vmc&explode=" + attrs["vmc"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["vmc_name"] + "</a></h3>" 
                if "host" in attrs and "host_name" in attrs :
                    output += "<h3>Hypervisor: <a class='btn btn-info' href='BOOTDEST/provision?object=host&explode=" + attrs["host"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["host_name"] + "</a></h3>" 
    
                if attrs["ai"] != "none" :
                    output += "<h3>Parent: <a class='btn btn-info' href='BOOTDEST/provision?object=app&explode=" + attrs["ai"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["ai_name"] + "</a></h3>" 
    
            output += """
                    <h3>Details:</h3>
            """
    
            for key in self.keys :
                if key in attrs :
                    output += self.make_alter_form(req, attrs["uuid"], req.active, key, attrs[key]) 
            output += "<p/></p><hr width='100%'>"
            for key in sorted(attrs.keys()) :
                if key not in self.keys :
                    output += self.make_alter_form(req, attrs["uuid"], req.active, key, attrs[key]) 
    
        elif params.get("pending") :
            output += "<div id='pendingresult'>"
            sr = False
            
            if not params.get("force") :
                sr = self.api.should_refresh(req.cloud_name, req.session["last_refresh"])
            
            if params.get("force") or sr :
                req.session["last_refresh"] = str(time())
                req.session.save()
                self.repopulate_views(req.session)
                try :
                    objs = active_list(req.cloud_name, "pending")
                    if len(objs) > 0 :
                        output += "<h4>" + str(len(objs)) + " Pending Request(s):</h4>"
                        output += self.list_objects(req, req.active, objs, link = False, icon = False, label = 'label-warning')
                    else :
                        output += "No Pending Objects"
                except APIException as obj :
                    for line in traceback.format_exc().splitlines() :
                        cbdebug(line)
                    output += "Failed to list pending objects!: " + obj.msg
            else :
                output += "unchanged"
    
            output += "</div>"
    
        else :
            success = True
            if params.get("operation") :
                operation_attrs = operations[params.get("operation")][1]
                func = getattr(self.api, req.active + params.get("operation"))
                args = []
                keywords = int(params.get("keywords"))
                for keyidx in range(1, keywords + 1) :
                    args.append(params.get("keyword"+ str(keyidx)))
                    
                '''
                TODO: the API supports keyword arguments now.
                Start utilizing them so that future API changes
                don't brake the GUI.
                '''
                try :
                    func(req.cloud_name, *args)
                    if params.get("sync") :
                        output += self.heromsg + "\n<h4>Successfully " + (operation_attrs["label"] + "ed: ").replace("ee", "e") + "BOOTOBJECTNAME: " + params.get("keyword1")
                        output += "</h4></div>"
                    else :
                        raise exc.HTTPTemporaryRedirect(location = "/provision?object=")
                        
                except APIException as obj :
                    success = False
                    output += self.heromsg + "\n<h4>Error: BOOTOBJECTNAME " + params.get("keyword1") + " not " + operation_attrs["label"] + "ed: " + obj.msg
                    output += "</h4></div>"
                    
            if not success :
                return self.bootstrap(req, output, error = True)
    
            output += """
                <div id='pendingstatus'></div>
                <div id='pendingcount2'>BOOTSPINNER&nbsp;Checking for pending requests...</div>
                <div id='pendingcount'></div>
                <div id='pendingtest'></div>
                <script>
                setTimeout("check_pending()", 1000);
                go('#allstate', bootdest + '/provision?allstate=1&liststate=' + liststate + '&object=' + active, '#allstate', unavailable, true, false, true);
                </script>
                <div id='allstate'>
            """
    
            if params.get("allstate") is not None :
                if params.get("criterion") and params.get("view") :
                    objs = self.api.viewshow(req.cloud_name, req.active if req.active != 'app' else 'ai', params.get("criterion"), params.get("expression"))
                else :
                    try :
                        objs = active_list(req.cloud_name, liststate)
                    except :
                        objs = []
    
                finished = active_list(req.cloud_name, "finished")
                finished.sort(key=self.trackingfunc, reverse = True)
                failed = active_list(req.cloud_name, "failed")
                failed.sort(key=self.trackingfunc, reverse = True)
    
                if len(objs) > 0 :
                    output += "<h4>" + str(len(objs))
                    output += (" Provisioned  " if liststate == "all" else " ")
                    output += "BOOTOBJECTNAMEs:</h4>"
                    output += self.list_objects(req, req.active, objs, icon = False)
                else :
                    output += self.heromsg + "\n<p><h4>&nbsp;No Objects</h4>"
                    
                if len(failed) > 0 :
                    output += "<h4>" + str(len(failed)) + " Failed Request(s):</h4>" + self.list_objects(req, req.active, failed, link = False, icon = 'icon-remove', label = 'label-important')
                if len(finished) > 0 :
                    output += "<h4>" + str(len(finished)) + " Finished Requests(s):</h4>" + self.list_objects(req, req.active, finished, link = False, icon = 'icon-ok', label = '')
                
            else :
                output += "BOOTSPINNER&nbsp;Loading Object State..."
                 
            output += "</div>"
    
        if not params.get("pending") and req.active != "host" :
            attach_fd = open(cwd + "/gui_files/attach_template.html", "r")
            output += attach_fd.read()
            attach_fd.close()
            attach = ""
            keywords = attach_params[req.active] if req.active in attach_params else []
    
            for idx in range(1, len(keywords) + 1) :
                keyword = "keyword" + str(idx)
                options = keywords[keyword]
                values = options["values"]
                attach += """
                    <tr>
                    <td>&nbsp;
                """
                attach += options["label"] + ": &nbsp;" 
                attach += """
                    </td>
                    <td>
                """
                if values == "vmcpool" :
                    values = ["auto"]
                    for poolinfo in self.api.vmclist(req.cloud_name) :
                        values.append(poolinfo["name"])
                elif values == "vms" :
                    values = []
                    for vminfo in self.api.vmlist(req.cloud_name) :
                        values.append(vminfo["name"])
    
                if values == "default" :
                    # convert to list to use drop-down instead of textbox
                    # append additional sizes here when available
                    pass
    
                if isinstance(values, list) and len(values) > 0 :
                    attach += "<select name='" + keyword + "'>"
                        
                    for option in values :
                            if isinstance(option, list) and len(option) == 2 :
                                name = option[0]
                                value = option[1] 
                                attach += "<option value='" + name + "'>" + value  + "</option>"
                            else :
                                attach += "<option>" + str(option) + "</option>"
    
                    attach += """
                        </select>
                    """
                else :
                    attach += "<input type='text' name='" + keyword + "' value='" + str(values) + "'/>"
    
                attach += "</td></tr>"
    
            output = output.replace("BOOTATTACH", attach)
            output = output.replace("BOOTKEYWORDS", str(len(keywords)))
        
        output += """
            </div>
            </td></tr></table>
            </div><!--2nd nav tab -->
            </div><!--row fluid-->
        """
        return output 
    
    def bootstrap(self, req, body, now = False, error = False, pretend_disconnected = False) :
        navcontents = ""
        cloudcontents = "None Available"
        availablecontents = "None Available"
        popoveractivate = """
                    <script>
                    $('#connectpop').popover('show');
                    </script>
                    """
            
        if now :
            contents = body
        else :
            contents_fh = open(cwd + "/gui_files/head_template.html", "r")
            contents = contents_fh.read()
            contents_fh.close()
            
            navactive = req.action
            if navactive == 'home' or navactive == 'index' :
                navactive = 'provision'
            for (key, value) in self.menu :
                navcontents += "<li"
                if navactive == key :
                    navcontents += " class='active'"
                navcontents += "><a href=\"BOOTDEST" + value[0] + "\">" + value[1] + "</a></li>\n"
        
            if req.session['connected'] and not pretend_disconnected :
                navcontents += "&nbsp;&nbsp;<a class='btn' href=\"BOOTDEST/disconnect\"><i class='icon-resize-small'></i>&nbsp;Disconnect</a>\n"
                navcontents += "&nbsp;&nbsp;<a class='btn' href=\"BOOTDEST/detach\"><i class='icon-resize-small'></i>&nbsp;Detach</a>\n"
            else :
                navcontents += """
                    &nbsp;&nbsp;<a href="#" id='connectpop' class="btn">Connect!</a>
                """
    
            if not req.session["connected"] or pretend_disconnected :
                if "clouds" in req.session :
                    cloudcontents = "<select name='running'>"
                    for cloud in req.session["clouds"] :
                        if pretend_disconnected and req.cloud_name.lower() == cloud["name"].lower() :
                            continue
                        cloudcontents += "<option value='" + cloud["model"] + "," + cloud["name"] + "'>" + cloud["name"] + " (" + cloud["description"] + ")</option>"
                    cloudcontents += "</select>"
                if "available_clouds" in req.session :
                    available_clouds = deepcopy(req.session['available_clouds'])
                    if "clouds" in req.session :
                        for cloud in req.session['clouds'] :
                            if cloud['name'].lower() in available_clouds and not (pretend_disconnected and req.cloud_name.lower() == cloud['name'].lower()):
                                del available_clouds[cloud['name'].lower()]
                    availablecontents = "<select name='available'>"
                    for cloud in available_clouds :
                        availablecontents += "<option>" + cloud.upper() + "</option>"
                    availablecontents += "</select>"
    
        if req.action == "index" :
            cbpath = req.uri + "gui_files"
            bootstrappath = req.uri + "3rd_party/bootstrap/docs/assets"
        else :
            cbpath = req.uri + "../../gui_files"
            bootstrappath = req.uri + "../../3rd_party/bootstrap/docs/assets"
    
        replacements = [    
                         navcontents, 
                         ("CB: [" + req.cloud_name + "," + req.model + "]") if req.session['connected'] else "Disconnected",
                         cloudcontents,
                         availablecontents,
                         body,
                         popoveractivate if (not req.session["connected"] and not req.skip_show and not req.action.count("wizard") and not error) else "",
                         self.spinner,
                         req.dest,
                         req.active if req.active else "",
                         req.active_obj[:-1] if req.active_obj else "",
                         bootstrappath,
                         cbpath,
                         self.branding,
                         self.brandiconsize,
                         self.brandurl,
                      ]
    
        for idx in range(0, len(self.replacement_keys)) :
            x = replacements[idx]
            y = self.replacement_keys[idx]
            contents = contents.replace(y, x)
    
        return contents

def parse_bufdata(bufdata):
    verb = ""
    path = ""
    version = ""
    port = "0" 

    import re

    if bufdata == None:
        raise Exception("empty buffer data handed to parse_bufdata")

    data = ""
    for item in bufdata :
        data += item.decode('utf-8')
    prefix, rest = data.split('\r\n', 1)

    # log.msg("dispatcher: prefix:%s" % prefix)

    prefix = prefix.strip().rstrip()
    if prefix != "":
        verb, pathversion = prefix.split(" ", 1)
        pathversion = pathversion.strip().rstrip()
        if pathversion != "":
            path, version = pathversion.split(" ", 1)
    
        if path.count("?") and path.count("=") == 1:
            params = path.split("?")[1]
            if params.count("=") :
                port = params.split("=")[1]
                
        log.msg("dispatcher: verb/path/version::%s:%s:%s" % (verb, path, version))

        return verb, path, version, port
    
class BroadwayRedirectResource(Resource):
    def render_GET(self, request):
        name = request.path[1:]
        
        if "port" not in request.args :
            return "Error: Port not listed in GTK broadway URL line! Try again"
        
        try :
            port = int(request.args["port"][0])
            
            if name == "broadway" :
                return urllib.request.urlopen("http://localhost:" + str(port)).read().replace("broadway.js", "broadway.js?port=" + str(port))
            
            elif name == "broadway.js" :
                return urllib.request.urlopen("http://localhost:" + str(port) + "/" + name).read().replace("/socket", "/socket?port=" + str(port))
            
            else :
                return "Error: Unknown GTK broadway URL request! Try again"
        except urllib.error.URLError as msg :
            return "Error: Display not available: " + request.uri + ": " + str(msg)
        except ValueError as msg :
            return "Error: Display not available: " + request.uri + ": " + str(msg)

        
class GUIDispatcher(Resource) :
    def __init__(self, keepsession, apiport, apihost, branding) :

        Resource.__init__(self)
        self.third_party = File(cwd + "/3rd_party")
        self.files = File(cwd + "/gui_files")
        self.fdrs = File(cwd + "/../driver")
        self.hfdrs = File(cwd + "/../osgcloud/driver")
        self.icon = File(cwd + "/gui_files/favicon.ico")
        self.git = File(cwd + "/.git")
        self.git.indexNames = ["test.rpy"]
        self.dashboard = GUI(apiport, apihost, branding)
        self.broadway = BroadwayRedirectResource()
        
        session_opts = {
            'session.data_dir' : '/tmp/dashboard_sessions_' + getpwuid(os.getuid())[0] + 'data',
            'session.type' : 'file',
            }
        
        if not keepsession :
            try :
                shutil.rmtree(session_opts['session.data_dir'])
            except OSError :
                pass
            
        self.app = WSGIResource(reactor, reactor.threadpool, SessionMiddleware(self.dashboard, session_opts))

    def getChild(self, name, request) :
        # Hack to make WebOb work with Twisted
        request.content.seek(0,0)
        request.setHeader
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods', 'GET')
        request.setHeader('Access-Control-Allow-Headers', 'x-prototype-version,x-requested-with')
        request.setHeader('Access-Control-Max-Age', "2520")

        if name.count(b"3rd_party") :
            return self.third_party
        elif name.count(b"gui_files") :
            return self.files
        elif name.count(b"hfdrs") :
            return self.hfdrs
        elif name.count(b"fdrs") :
            return self.fdrs
        elif name.count(b"favicon.ico"):
            return self.icon
        elif name.count(b"git"):
            return self.git
        elif name.count(b"broadway"):
            return self.broadway

        else :
            return self.app

class WebsocketsDispatcher:
    site = None

    def __init__(self, bufdata):
        self.bufdata = bufdata

        # Parse the packet buffer and save the important components
        verb, path, version, port = parse_bufdata(self.bufdata)
        self.verb = verb
        self.path = path
        self.version = version
        self.port = port

    def isLocal(self):
        if self.path.count("socket") :
            return False
        return True

    def localFactory(self):
        if self.path.count("socket") :
            return None
        else :
            return self.site
    
    def connectClient(self, clientCreator):
        log.msg("connectClient: %s/%s/%s" % (self.verb, self.path, self.version))
        
        # This URL is what the GTK3 broadway backend uses to transmit
        # the actual display, which we passthrough to broadway.js
        # which has already been fetched by the browser and issues
        # the actual websocket traffic to draw the application
        if self.path.count("/socket"):
            reactor.connectTCP("localhost", int(self.port), clientCreator)
            return True

        return False

    # We have to rewrite the Host: header to match what the GTK websocket expects

    def outgoingData(self):

        if self.path == "/":
            # Replace the Host: header
            x = re.sub(r'Host: (\S*)', 'Host: localhost', self.bufdata[0].decode('utf-8'))
            log.msg("replace:%s" % x)
            self.bufdata[0] = str.encode(x) 

        return self.bufdata
    
'''
 The GUI handles 3 different kinds of traffic using twisted:

 1. WSGI resources returns HTML for the main user interfaces
 2. FILE resoucres return static content
 3. Websocket traffic gets proxied through this process to other locations

 In order to handle #3, we use 'StreamProx' to first examine (earlier than
 twisted) what the is the requested URL.

 If the URL refers to a websocket URL, then we proxy that traffic.

 Otherwise, we return control to this process to handle the rest of the UI
 events.

'''

def gui(options) :
    reactor._initThreadPool()

    use_ssl = False
    if options.guisslcert and options.guisslcert.lower() != "false" and options.guisslkey and options.guisslkey != "false" :
        use_ssl = True

    cbdebug("Will use API Service @ http://" + options.apihost + ":" + str(options.apiport))

    cbdebug("Point your browser to: http", True)
    cbdebug("https" if use_ssl else "http", True)
    cbdebug(" port: " + str(options.guiport) + ". (Bound to interface: " + options.guihost + ")", True)

    site = Site(GUIDispatcher(options.keepsession, options.apiport, options.apihost, options.guibranding))

    PacketBuffer.delimiter = "\r\n\r\n"
    factory = BufferingProxyFactory()
    factory.buffer_factory = PacketBuffer
    WebsocketsDispatcher.site = site
    factory.dispatcher_factory = WebsocketsDispatcher

    if use_ssl : 
        from twisted.internet import ssl
        from OpenSSL import SSL

        class ChainedOpenSSLContextFactory(ssl.DefaultOpenSSLContextFactory):
            def __init__(self, privateKeyFileName, certificateChainFileName, sslmethod=SSL.SSLv23_METHOD):
                self.privateKeyFileName = privateKeyFileName
                self.certificateChainFileName = certificateChainFileName
                self.sslmethod = sslmethod
                self.cacheContext()
            
            def cacheContext(self):
                ctx = SSL.Context(self.sslmethod)
                ctx.use_certificate_chain_file(self.certificateChainFileName)
                ctx.use_privatekey_file(self.privateKeyFileName)
                self._context = ctx

        # If your certificate is actually trusted and signed by a real CA
        # (as it should be), your certificate file should have the full
        # certificate chain included in the file, not only yours.

        reactor.listenSSL(int(options.guiport), factory, ChainedOpenSSLContextFactory(privateKeyFileName=options.guisslkey, certificateChainFileName=options.guisslcert, sslmethod = SSL.SSLv3_METHOD), interface = options.guihost)

        #reactor.listenSSL(int(options.guiport), factory, ssl.DefaultOpenSSLContextFactory(options.guisslkey, options.guisslcert), interface = options.guihost)
    else :
        cbdebug("Your dashboard does not use SSL. You are warned.", True)
        reactor.listenTCP(int(options.guiport), factory, interface = options.guihost)
    reactor.run()

