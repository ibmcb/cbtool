#!/usr/bin/python
'''
 Copyright (c) 2012 IBM Corp.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
'''
import ast, json
import traceback
import os
import re
import socket
import errno
import optparse
import shutil

from pwd import getpwuid
from time import time, sleep
from copy import deepcopy
from operator import attrgetter, itemgetter
from sys import path
from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web import wsgi
from webob import Request, Response, exc
from beaker.middleware import SessionMiddleware
from optparse import OptionParser

cwd = (re.compile(".*\/").search(os.path.realpath(__file__)).group(0)) + "/../../"
path.append(cwd)

from lib.api.api_service_client import *
from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

def prefix(uri) :
    return ""
    #return "/" + re.compile("[^/]*\/([^/]*)").search(uri).group(1)

class Dashboard () :
    def __init__(self, msci, base_uri, time_vars, msattrs, cloud_name) :
        self.time_vars = time_vars 
        self.base_uri = base_uri
        self.start_time = int(self.time_vars["start_time"])
        self.processid = "none"
        self.cn = cloud_name
        self.msattrs = msattrs
        self.username = self.time_vars["username"]
        self.msci = msci
        self.manage_collection = {"VM": "latest_management_VM_" + self.username, \
                                  "HOST" : "latest_management_HOST_" + self.username }
        self.latest_os_collection = {"VM" : "latest_runtime_os_VM_" + self.username, \
                                     "HOST" : "latest_runtime_os_HOST_" + self.username } 
        self.latest_app_collection = {"VM" : "latest_runtime_app_VM_" + self.username} 

        self.destinations = {}
        self.user_generated_categories = { 'p' : "Provisioning", 'a' : "Application" }
        self.standard_categories = { 's' : "VM", 'h': "HOST" }
        self.categories = dict(self.standard_categories.items() + self.user_generated_categories.items())
        self.owners = { "VM" : ['s', 'p', 'a'], "HOST" : ['h']}
        self.summaries = {"Saved VMs" : [True, "savedvm"], "Failed VMs" : [True, "failedvm"], "KB => MB" : [False, "kb2mb"], "bytes/sec => Mbps" : [False, "b2mb"], "#4K pages => MB" : [False, "4k2mb"]}
        self.labels = ['name', 'size', 'role', 'type', 'cloud_ip', 'age', 'vms', 'state', 'latest_update', 'vmc_name', 'host_name', 'ai_name', 'aidrs_name']
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
        elif attrs["cloud_ip"] == "undefined" :
            return False
        elif metrics is not None and "last_known_state" in metrics :
            if metrics["last_known_state"].count("with ip assigned") == 0 :
                return True
            else :
                return False
        else :
            return False

    def makeRow(self, category, row, bold = False, exclude = None) :
        exclude = None
        result = "<tr>\n"
        for cell in row :
            cell = str(cell)
            display = cell
            if category == "p" and display.count("mgt_") :
                display = "Step " + str(int(display[4:7])) + ": " + display[8:]
                    
            if bold and (exclude is None or cell not in exclude) :
                cell = "<a href='" + self.prefix() + "/monitor?filter=" + category + "-" + cell + "' target='_top'>" + display.replace("_", "<br/>") + "</a>"
            elif bold :
                cell = "<b>" + display.replace("_", "<br/>") + "</b>"
            else :
                cell =  display.replace("_", "<br/>")
            result += "<td>" + str(cell) + "</td>"
            
        result += "\n</tr>\n"
        return result

    """
    Generate a visualization of the latest metrics only and write
    the visualization out in HTML format
    """
    def gather_contents(self):
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
        for _obj_type in self.manage_collection.keys() :
            _obj_list += self.msci.find_document(self.manage_collection[_obj_type], {}, True, [("mgt_001_provisioning_request_originated", 1)])

        for attrs in _obj_list :
            _obj_type = attrs["obj_type"]
            
            if _obj_type == "VM" :
                attrs["age"] = curr_time - int(attrs["mgt_001_provisioning_request_originated"])
            metrics = self.msci.find_document(self.latest_os_collection[_obj_type], {"_id" : attrs["uuid"]})

            if metrics is None :
                # Gmetad may not have reported in yet...
                # But we should still show management metrics
                metrics = attrs
            else :
                metrics.update(attrs)
            
            if _obj_type in self.latest_app_collection :
                _app_metrics = self.msci.find_document(self.latest_app_collection[_obj_type], {"_id" : attrs["uuid"]})
                if _app_metrics :
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
                                'last_known_state' : {"$regex": "with ip assigned"}, \
                                'mgt_999_provisioning_request_failed' : { "$exists" : False}, \
                                'vmc_name' : attrs['cloud_hostname'] })
                
            row_indexer = {}
            label_indexer = {}
            for dest in self.categories :
                row_indexer[dest] = {}
                label_indexer[dest] = {}
            
            for mkey, mvalue in metrics.iteritems() :
                if not isinstance(mvalue, dict):
                    if not mkey.count("mgt_") and mkey not in ["time", "latest_update"] :
                        continue
                    
                    if _obj_type != "VM" :
                        continue
                    key = mkey
                    value = mvalue
                    metric_type = 'p' if key.count("mgt_") else 's'
                    unit = "epoch" if key.count("originated") else ("secs" if key.count("mgt_") else 's')
                else :
                    key = mkey
                    value = mvalue['val']
                    unit = mvalue['units']
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
                if self.summaries["KB => MB"][0] :
                    if unit == "KB" or unit == "KiB" :
                        value = "%.2f" % (float(value) / 1024)
                        unit = "MB"
                if self.summaries["bytes/sec => Mbps"][0] :
                    if unit == "bytes/sec" :
                        value = "%.2f" % (float(value) / 1024 / 1024 * 8)
                        unit = "mbps"
                        
                if self.summaries["#4K pages => MB"][0] :
                    if unit == "#4K pages" :
                        value = "%.2f" % (float(value) * 4094 / 1024 / 1024)
                        unit = "MB"
                row_indexer[metric_type][newkey] = value
                accumulate_units[metric_type][newkey] = unit 
                    
            # We also want some "common" columns to be at the front of 
            # every category, like name and IP address to make the dashboard
            # easier to follow
            for label in self.labels :
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
                if len(row_indexer[metric_type]) > 0 :
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
            unitkeys = accumulate_units[dest].keys()
            self.destinations[dest] = ""
            prefix_rows1 = []
            prefix_rows2 = []
            row1 = []
            row2 = []
            for label in self.labels :
                if label in print_labels[dest] :
                    prefix_rows1.append(label)
                    prefix_rows2.append("")
                    
            if len(unitkeys) > 0 :
                unitkeys.sort()
                
            for unit in unitkeys :
                row1.append(unit) 
                row2.append(accumulate_units[dest][unit]) 
                    
            # First print the units and their corresponding common labels 
            self.destinations[dest] += self.makeRow(dest, prefix_rows1 + row1, bold = True, exclude = prefix_rows1)
            self.destinations[dest] += self.makeRow(dest, prefix_rows2 + row2)
            
            # Dump the master dictionary into HTML
            for (label_dict, obj_dict) in accumulate_rows[dest] :
                row = []
                for label in self.labels :
                    if label in label_dict :
                        row.append(label_dict[label])
                for unit in unitkeys :
                    if unit in obj_dict :
                        val = obj_dict[unit]
                        
                        # Some float values are zero. Get rid of the decimal
                        # if they are zero and only print integer to save
                        # screen space
                        
                        if  str(val).count(":") == 0 :  
                            val = str(float(val))
                            if "." in val :
                                integer, decimal = val.split(".") 
                                if decimal == "0" :
                                    val = integer 
                        row.append(val) 
                    else :
                        row.append("--")
                        
                self.destinations[dest] += self.makeRow(dest, row)
            
            
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
        for summ in self.summaries.keys() :
            url += self.summaries[summ][1] + "=" + ("yes" if self.summaries[summ][0] else "no") + "&"

        for dest in ['p', 'h', 's', 'a' ] :
            url += dest + "=" + ("yes" if self.show[dest] else "no") + "&"
            
        if len(self.filters) :
            url += "filter="
            for dest in ['p', 'h', 's', 'a' ] :
                for filter in sorted(self.filters.keys()) :
                    if not filter.count(dest + "-") :
                        continue
                    url += filter + "," 

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
                
        for summ in self.summaries.keys() :
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
                for filter in sorted(self.filters.keys()) :
                    if not filter.count(dest + "-") :
                        continue
                    output += "[<a href='" + self.prefix() + "/monitor?remove=" + filter + "' target='_top'>X</a>] " + \
                        filter.split("-")[1].replace("_", " ") + "&nbsp;"
            
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
                    <b>Save Configuration URL</b>:
        """

        output += self.make_url()

        output += """
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
                    for filter in filters :
                        self.filters[filter] = True
                elif key in self.show :
                    self.show[key] = True if value == "yes" else False
                else :
                    for summ in self.summaries.keys() :
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
    def __init__(self, apiport, apihost):
        self.heromsg = "<div class='hero-unit' style='padding: 5px'>"
        self.spinner = "<img src='CBSTRAP/spinner.gif' width='15px'/>&nbsp;"
        self.apihost = apihost
        self.apiport = apiport
        self.pid = "none"

        if self.apihost == "0.0.0.0" :
                self.apihost = "127.0.0.1"

        self.api_access = "http://" + self.apihost + ":" + str(self.apiport)
        self.api = APIClient(self.api_access)
            
        self.keys = [ "name", "size", "role", "type", "cloud_ip", "age", "state", "vmc_name", "host_name", "ai_name", "aidrs_name" ]
        self.menu = [ 
             ("provision" , ("/provision", "<i class='icon-home'></i>&nbsp;Provisioning")), 
             ("monitor" , ("/monitor", "<i class='icon-heart'></i>&nbsp;Dashboard")),
             ("stats" , ("/stats", "<i class='icon-list-alt'></i>&nbsp;Statistics")),
             ("config" , ("/config", "<i class='icon-wrench'></i>&nbsp;Configure")),
        ]
        
        # Replacements must be in this order
        
        self.replacement_keys = [ 
                "BOOTNAV", "BOOTCLOUDNAME", "BOOTCLOUDS", "BOOTAVAILABLECLOUDS", "BOOTBODY", "BOOTSHOWPOPOVER", \
                "BOOTSPINNER", "BOOTDEST", "BOOTACTIVE", "BOOTOBJECTNAME", "BOOTSTRAP", "CBSTRAP" \
        ]
        
    def keyfunc(self, x):
        return int(x["counter"])

    def __call__(self, environ, start_response):
        # Hack to make WebOb work with Twisted
        setattr(environ['wsgi.input'], "readline", environ['wsgi.input']._wrapped.readline)

        req = Params(environ)
        req.dest = prefix(req.unparsed_uri)
        
        try:
            resp = self.common(req)
        except exc.HTTPTemporaryRedirect, e :
            resp = e
            resp.location = req.dest + resp.location + req.active
        except exc.HTTPException, e:
            resp = e
        except Exception, e :
            exc_type, exc_value, exc_traceback = sys.exc_info()
            resp = "<h4>Exception:</h4>"
            for line in traceback.format_exc().splitlines() :
                resp += "<br>" + line

        if isinstance(resp, str) or isinstance(resp, unicode):
            return Response(resp)(environ, start_response)
        else :
            return resp(environ, start_response)
        
    def list_objects(self, req, active, objs, link = True, icon = 'icon-refresh', label = 'label-info') :
        output = "<table>"
        mod = 10 if active not in ["vmc", "host"] else 1
        if len(objs) == 0 :
            output += "<tr><td>No data.</td></tr>"
        else :
            if "counter" in objs[0] :
                objs.sort(key=self.keyfunc)
            for idx in range(0, len(objs)) :
                obj = objs[idx]
                # appinit()/vminit() was used
                init_pending = True if ("tracking" in obj and str(obj["tracking"]).lower().count("paused waiting for run command")) else False 
                    
                if link :
                    if idx != 0 and (idx % mod) == 0 :
                        output += "<tr><td></td></tr>"
                    if idx == 0 :
                            output += "<tr>"
                    output += "<td>"
                else :
                    output += "<tr><td>"
    
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
                        output += "<a class='btn btn-mini btn-info' href='BOOTDEST/provision?object=" + active + "&operation=runstate&keywords=4&keyword1=" + obj["uuid"] + "&keyword2=attached&keyword3=run&keyword4=async'><i class='icon-play icon-white'></i>&nbsp;" + obj["name"] + "</a>&nbsp;&nbsp;"
                    act = obj["tracking"] if "tracking" in obj else None
                    output += (str(act) if (act is not None and act != "None") else "")
                output += "</td>"
    
        output += "</table>"
        return output
        
    def make_alter_form(self, req, uuid, object, key, value) :
        output = ""
        output += "<form style='margin: 0' action='BOOTDEST/provision' method='get'>"
        output += """
            <table><tr><td width='300px'>
                <button type="submit" class="btn btn-default">
                  <i class="icon-arrow-right icon-black"></i>&nbsp;<b>
        """
        output += key + "</b></button></td><td>"
        output += "Value: <input style='margin-top: 9px' type='text' name='value' value='" + value + "'/>"
        output += "<input type='hidden' name='alter' value='1'/>"
        output += "<input type='hidden' name='object' value='" + object  + "'/>"
        output += "<input type='hidden' name='explode' value='" + uuid + "'/>"
        output += "<input type='hidden' name='key' value='" + key   + "'/></td></tr></table></form>"
        return output
    
    def make_config_form(self, req, category, name, label, default) :
        output = ""
        output += "<form style='margin: 0' action='BOOTDEST/config' method='get'>"
        output += """
            <table><tr><td width='300px'>
                <button type="submit" class="btn btn-default">
                  <i class="icon-arrow-right icon-black"></i>&nbsp;<b>
        """
        output += label + "</b></button></td><td>"
        output += "Value: <input style='margin-top: 9px' type='text' name='value' value='" + default + "'/>"
        output += "<input type='hidden' name='category' value='" + category + "'/>"
        output += "<input type='hidden' name='name' value='" + name  + "'/></td></tr></table></form>"
        return output
        
    def repopulate_views(self, session) :
        session["attach_params"] = {
                    "vm" : { 
                              "keyword1" : { "label" : "Role", "values" : [x.strip() for x in self.api.rolelist(session['cloud_name'])] } ,
                              "keyword2" : { "label" : "Pool", "values" : ["auto"] + [x.strip() for x in self.api.poollist(session['cloud_name'])] } ,
                              "keyword3" : { "label" : "Size", "values" : "default" } ,
                              "keyword4" : { "label" : "Pause Step", "values" : [["continue" , "None"], ["prepare_provision_complete", "Step 3: Provision Complete"], ["network_ready", "Step 4: Network Accessible"]] } ,
                              "keyword5" : { "label" : "Mode", "values" : "async" } ,
                           },
                    "app" : { 
                              "keyword1" : { "label" : "Type", "values" : [x.strip() for x in self.api.typelist(session['cloud_name'])] } ,
                              "keyword2" : { "label" : "Load Level", "values" : "default" } ,
                              "keyword3" : { "label" : "Load Duration", "values" : "default" } ,
                              "keyword4" : { "label" : "Lifetime", "values" : "none" } ,
                              "keyword5" : { "label" : "Submitter", "values" : "none" } ,
                              "keyword6" : { "label" : "Pause Step", "values" : [["continue" , "None"], ["prepare_provision_complete", "Step 3: Provision Complete"], ["network_ready", "Step 4: Network Accessible"]] } ,
                              "keyword7" : { "label" : "Mode", "values" : "async" } ,
                            },
                    "vmc" : { "keyword1" : { "label" : "Name", "values" : "" } },
                    "svm" : { "keyword1" : { "label" : "Identifier", "values" : "vms" } },
                    "aidrs" : { "keyword1" : { "label" : "Pattern", "values" : [x.strip() for x in self.api.patternlist(session['cloud_name'])] } },
        }
        session['views'] = self.api.viewlist(session['cloud_name'])
        session.save()

    def common(self, req) :
        vmcattachallfound = False
    
        try :
            if req.http.params.get("connect") :
                if req.http.params.get("available") :
                    requested_cloud_name = req.http.params.get("available").lower()
                    definitions = req.session["definitions"]
                    available_clouds = self.api.cldparse(definitions)
                    for cloud_name in available_clouds :
                        cloud_name = cloud_name.lower()
                        if cloud_name == requested_cloud_name :
                            for command in available_clouds[cloud_name] :
                                parts = command.split()
                                
                                if parts[0] == "clddefault" :
                                    continue
                                
                                if len(parts) < 2 :
                                    return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>")
                                    
                                try :
                                    func = getattr(self.api, parts[0])
                                except AttributeError, msg :
                                    return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>")
                                
                                if parts[0] != "cldattach" and 'cloud_name' in req.session and not command.lower().count(req.session['cloud_name'].lower()) :
                                    fixed = [parts[0], req.session['cloud_name']] + parts[1:]
                                else :
                                    fixed = parts
                                
                                if fixed[0] == "vmcattach" and fixed[2] == "all" :
                                    if len(fixed) < 2 :
                                        return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>")
                                    if not command.count("async") :
                                        fixed.append("async")
                                if fixed[0] == "cldattach" :
                                    if len(fixed) < 3 :
                                        return self.bootstrap(req, self.heromsg + "\n<h4>Malformed command in your STARTUP_COMMAND_ LIST in your config file: " + command + "</h4></div>")
                                    if len(fixed) == 3 :
                                        fixed.append(definitions)
                                    
                                func(*fixed[1:])
                                
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
                    available_clouds = self.api.cldparse(definitions)
                    if not len(available_clouds) :
                        req.skip_show = True
                        response_fd = open(cwd + "/gui_files/response_template.html", "r")
                        response = response_fd.read().replace(" ", "&nbsp;")
                        response_fd.close()
                        return self.bootstrap(req, self.heromsg + "\n<h4>" + response + "</h4></div>")
                    
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
                    "attach" : [0, {"operations" : [ "vm", "vmc", "app", "svm", "aidrs"], "icon" : "play", "state" : "any" } ], 
                    "detach" : [1, {"operations" : [ "vm", "vmc", "app", "svm", "aidrs"], "icon" : "trash", "state" : "any" } ], 
                    "save" : [2, {"operations" : [ "vm", "vmc", "app"], "icon" : "stop", "state" : "attached" } ], 
                    "restore" : [3, {"operations" : [ "vm", "vmc", "app"], "icon" : "play", "state" : "save" } ], 
                    "suspend" : [4, {"operations" : [ "vm", "vmc", "app"], "icon" : "pause", "state" : "attached" } ], 
                    "resume" : [5, {"operations" : [ "vm", "vmc", "app"], "icon" : "play", "state" : "fail" } ], 
                    "protect" : [6, {"operations" : [ "vm" ], "icon" : "star" , "ft" : "attach", "state" : "attached" } ], 
                    "unprotect" : [7, {"operations" : [ "vm" ], "icon" : "ok" , "ft" : "detach", "state" : "attached"} ], 
                    "fail" : [8, {"operations" : [ "vm" ], "icon" : "fire", "ft" : "fail", "state" : "attached" } ], 
                    "runstate" : [9, {"operations" : [ "vm", "app"], "icon" : "play", "state" : "any" } ],
                }
                
                for operation in req.session["operations"].keys() :
                    req.session["operations"][operation][1]["label"] = operation[0].upper() + operation[1:]
    
                req.session["objects"] = { 
                     "vmc": [ 0, "Regions" ],
                     "host": [ 1, "Hypervisors" ],
                     "app": [ 2, "Virtual Applications" ],
                     "vm": [ 3, "Virtual Machines" ],
                     "aidrs": [ 4, "Application Submitters" ],
                     "svm": [ 5, "FTVM Stubs" ],
                     #"vmcrs": [ 5, "Capture Submitters" ],
                } 
    
                req.action = "provision"
                req.active = "vmc"
                req.session['connected'] = True 
                req.session.save()
    
            if req.session['connected'] :
                req.cloud_name = req.session['cloud_name']
                req.model = req.session['model']
            else :
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                return self.bootstrap(req, self.heromsg + "\n<h4>You need to connect, first.</h4></div>")
    
            if req.action == "monitor" : 
                self.api.dashboard_conn_check(req.cloud_name, req.session['msattrs'], req.session['time_vars']['username'])
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
                
                return self.bootstrap(req, output if (success or success is None) else msg)
    
            elif req.action == "config" :
                result = ""
                if req.http.params.get("category") is not None :
                    result += self.heromsg + "\n<h4>"
                    msg = "object: " + req.http.params.get("category") + ": " + req.http.params.get("name") + "=" + req.http.params.get("value")
                    try :
                        self.api.cldalter(req.cloud_name, req.http.params.get("category"), req.http.params.get("name"), req.http.params.get("value"))
                        result  += "Successfully altered " + msg
                    except APIException, obj :
                        result += "Failed to alter " + msg + ": " + obj.msg
                    result += "</h4></div>"
                        
                output = """
                    <div class='span10'>
                    <div class='row'>
                    <div class="span3 bs-docs-sidebar">
                        <ul data-spy='affix' class="pager nav nav-list bs-docs-sidenav">
                """
                
                settings = self.api.cldshow(req.cloud_name)
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
                            output += "<a class='accordion-toggle' data-toggle='collapse' data-parent='#config" + category + "' href='#collapse" + category + subkey + "'>" + subkey  + "</a>"
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
                self.api.dashboard_conn_check(req.cloud_name, req.session['msattrs'], req.session['time_vars']['username'])
                try :
                    expid = self.api.cldshow(req.cloud_name, "time")["experiment_id"]
                except APIException, obj :
                    return self.bootstrap(req, self.heromsg + "<h4>Could not retrieve current experiment ID from the API</h4></div>")
                        
                mon = Dashboard(self.api.msci, req.unparsed_uri, req.session['time_vars'], req.session['msattrs'], req.session['cloud_name'])
                result = []
                for record in mon.msci.find_document(mon.manage_collection["VM"], {"expid": expid}, True, [("mgt_001_provisioning_request_originated", 1)]) :
                    if mon.is_failed_vm(record) :
                        continue
                    result.append(record)
                return self.bootstrap(req, str(json.dumps(result)), now = True)
            elif req.action == "d3" :
                d3_fd = open(cwd + "/gui_files/d3_template.html", "r")
                d3_html = d3_fd.read()
                d3_fd.close()
                return self.bootstrap(req, d3_html)
            elif req.action == "monitordata" :
                self.api.dashboard_conn_check(req.cloud_name, req.session['msattrs'], req.session['time_vars']['username'])
                mon = Dashboard(self.api.msci, req.unparsed_uri, req.session['time_vars'], req.session['msattrs'], req.session['cloud_name'])
                mon.parse_url(req.session["dashboard_parameters"])
                mon.gather_contents()
    
                output_fd = open(cwd + "/gui_files/cli_template.html", "r")
                cli_html = output_fd.read()
                output_fd.close()
                return self.bootstrap(req, "<div class='span10'>" + mon.body + cli_html)
            elif req.action == "stats" :
                stats = self.api.stats(req.cloud_name)
                output = "<div class='span10'>"
                output += self.heromsg + "\n<h4>&nbsp;&nbsp;Runtime Summary Statistics:</h4></div>\n"
                output += "<div class='accordion' id='statistics'>\n"
                
                for group, label, unit, data in stats :
                    group_key = group.replace(" ", "_")
                    output += """
                            <div class="accordion-group">
                                <div class="accordion-heading">
                    """
                    output += "<a class='accordion-toggle' data-toggle='collapse' data-parent='#statistics' href='#collapse" + group_key + "'>" + group + "</a>"
                    output += "</div>\n"
                    output += "<div id='collapse" + group_key + "' class='accordion-body collapse'>"
                    output += "<div class='accordion-inner'>"
                    output += "<table class='table table-hover table-striped'>\n"
                    output += "<tr><td><b>" + label + "</b></td><td><b>" + unit + "</b></td></tr>\n"
                    for name, value in data :
                        output += "<tr><td>" + name + "</td><td>" + value + "</td></tr>\n"
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
            elif req.action == "commands" :
                self.api.dashboard_conn_check(req.cloud_name, req.session['msattrs'], req.session['time_vars']['username'])
                contents = """
                    <div id='commandcontent'>
                            <table class='table table-hover table-striped'>
                    """
                    
                result = []
                commands = self.api.msci.find_document("trace_" + req.session['time_vars']["username"], None, True, [("command_originated" , -1)], 10, ["command"], disconnect_finish = True)
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
                return self.bootstrap(req, "<div class='span10'>" + self.default(req, req.http.params, req.session["attach_params"], \
                                                           req.session['views'], \
                                                           req.session["operations"], \
                                                           req.session["objects"], \
                                                           req.session["liststates"]) + cli_html)
            elif req.action == "disconnect" :
                req.session['connected'] = False
                del req.session['cloud_name']
                req.session['clouds'] = self.api.cldlist() 
                req.session.save()
                return self.bootstrap(req, self.heromsg + "\n<h4>Disconnected from API @ " + self.api_access + "</h4></div>")
            
            return self.bootstrap(req, self.heromsg + "\n<h4>We do not understand you! Try again...</h4></div>")
    
        except APIException, obj :
            return self.bootstrap(req, self.heromsg + "\n<h4>Error: API Service says: " + str(obj.status) + ": " + obj.msg + "</h4></div>")
        except IOError, msg :
            return self.bootstrap(req, self.heromsg + "\n<h4>Error: API Service (" + self.api_access + ") is not responding: " + str(msg) + "</h4></div>")
        except socket.error, v:
            return self.bootstrap(req, self.heromsg + "\n<h4>Error: API Service (" + self.api_access + ") is not responding: " + str(v) + "</h4></div>")
        #except Exception, msg:
        #    return self.bootstrap(req, self.heromsg + "\n<h4>Error: Something bad happened: " + str(msg) + "</h4></div>")
        
    def default(self, req, params, attach_params, views, operations, objects, liststates):
        if not req.active : 
            req.active = params.get("object", "app")
        req.active_obj = ""
        active_list = getattr(self.api, req.active + "list")
        liststate = params.get("liststate", "all")
        view = params.get("view", "")
        active_view = None
    
        output = """
            <script>active = 'BOOTACTIVE';</script>
            <div>
            <ul id='one' class="nav nav-tabs">
        """
    
        for obj, label in sorted(objects.iteritems(), key=itemgetter(1)) :
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
                    <p>
                """
            
            output += """
                <div class='tabbable tabs-left'>
                <ul id='two' class="nav nav-tabs">
            """
    
            for obj, attrs in sorted(views[req.active].iteritems(), key=itemgetter(1)) :
                criterion = attrs[1]["criterion"].strip()
                expressions = attrs[1]["expression"]
                dropdown = isinstance(expressions, list)
                liclass = ''
                if dropdown :
                    liclass += 'dropdown'
    
                if view == obj :
                        found_view = True
                        active_view = attrs[1]
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
                
            for tempstate, state_attrs in sorted(liststates.iteritems(), key=itemgetter(1)) :
                output += "<li"
                if not found_view and liststate == tempstate : 
                    output += " class='active'"
                output += "><a href='BOOTDEST/provision?liststate=" + tempstate + "&object=BOOTACTIVE'>" + state_attrs[1] + "</a></li>" 
            output += """
                </ul>
                </div>
            """
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
                except APIException, obj :
                    output += self.heromsg + "\n<h4>&nbsp;&nbsp;Error: Could not alter BOOTOBJECTNAME " + uuid + " attribute " + params.get("key") + " = " + params.get("value") + ": " + obj.msg + "</h4></div>"
                
            attrs = getattr(self.api, req.active + "show")(req.cloud_name, uuid)
            output += "<h2>BOOTOBJECTNAME: " + attrs["name"] + "</h2>"
            
            for operation, operation_attrs in sorted(operations.iteritems(), key=itemgetter(1)) :
                keywords = {}
                label = operation_attrs[1]["label"]
                if "svm_stub_vmc" in attrs and attrs["svm_stub_vmc"] != "none" and operation in ["unprotect", "fail"] :
                    keywords["keyword" + str(len(keywords) + 1)] = attrs["svm_stub_uuid"]
                else :
                    keywords["keyword" + str(len(keywords) + 1)] = attrs["uuid"]
                
                if operation == "attach" or req.active not in operation_attrs[1]["operations"] :
                    continue
                elif operation == "detach" :
                    force = False
                    if "ai" in attrs and attrs["ai"] != "none" : 
                        force = True
                    elif "aidrs" in attrs and attrs["aidrs"] != "none" :
                        force = True
                    elif "svm_stub_vmc" in attrs and attrs["svm_stub_vmc"] != "none" :
                        force = True
                    if force :
                        label = "Force " + label
                        #keywords["keyword" + str(len(keywords) + 1)] = "force" 
                elif operation in [ "unprotect", "fail" ] :
                    if "svm_stub_vmc" not in attrs or attrs["svm_stub_vmc"] == "none" :
                        continue
                elif operation in [ "runstate" ] :
                    continue
                elif operation == "protect" :
                    if "svm_stub_vmc" in attrs and attrs["svm_stub_vmc"] != "none" :
                        continue
                elif operation  in [ "save", "suspend", "restore", "resume" ] :
                    if "svm_stub_vmc" in attrs and attrs["svm_stub_vmc"] != "none" :
                        continue
                required = operation_attrs[1]["state"]
                if required != "any" and attrs["state"] != required  :
                    continue
                    
                keywords["keyword" + str(len(keywords) + 1)] = "async" 
                
                output += "&nbsp;&nbsp;<a Class='btn btn-danger btn-small' href='BOOTDEST/provision?object=" 
                if "ft" in operation_attrs[1] :
                    output += "svm"
                else :
                    output += req.active
                    
                output += "&operation=" + operation
                
                output += "&keywords=" + str(len(keywords))
                for keyidx in range(1, len(keywords) + 1) :
                    key = "keyword" + str(keyidx)
                    output += "&" + key + "=" + keywords[key]
                output += "'><i class='icon-" + operation_attrs[1]["icon"] + " icon-white'></i>&nbsp;&nbsp;" + label + "&nbsp;&nbsp;</a>"
                
            if req.active in ["app", "vmc", "host"] :
                output += """
                    <h3>Children: 
                """
                objs = []
    
                if req.active == "app" :
                    for vm in attrs["vms"].split(",") :
                        uuid, type, name = vm.split("|") 
                        objs.append({"name" : name, "uuid" : uuid}) 
                elif req.active == "vmc" :
                    for host in self.api.viewshow(req.cloud_name, "HOST", "VMC", attrs["uuid"]) :
                        objs.append(host) 
                elif req.active == "host" :
                    for vm in self.api.viewshow(req.cloud_name, "VM", "HOST", attrs["uuid"]) :
                        objs.append(vm) 
    
                output += self.list_objects(req, "host" if req.active == "vmc" else "vm", objs) + "</h3>"
    
            if req.active in ["vm", "svm"] :
                output += "<h3>Region: <a class='btn btn-info' href='BOOTDEST/provision?object=vmc&explode=" + attrs["vmc"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["vmc_name"] + "</a></h3>" 
                if "host" in attrs :
                    output += "<h3>Hypervisor: <a class='btn btn-info' href='BOOTDEST/provision?object=host&explode=" + attrs["host"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["host_name"] + "</a></h3>" 
    
                if attrs["ai"] != "none" :
                    output += "<h3>Parent: <a class='btn btn-info' href='BOOTDEST/provision?object=app&explode=" + attrs["ai"] + "'><i class='icon-info-sign icon-white'></i>&nbsp;" + attrs["ai_name"] + "</a></h3>" 
    
            output += """
                    <h3>Details:</h3>
            """
    
            for key in self.keys :
                if key in attrs :
                    output += self.make_alter_form(req, attrs["uuid"], req.active, key, attrs[key]) 
                    #output += "<tr><td>" + key + "</td><td>" + str(attrs[key]) + "</td></tr>"
            output += "<p/></p><hr width='100%'>"
            for key in sorted(attrs.keys()) :
                if key not in self.keys :
                    output += self.make_alter_form(req, attrs["uuid"], req.active, key, attrs[key]) 
                    #output += "<tr><td>" + key + "</td><td>" + str(attrs[key]) + "</td></tr>"
    
        elif params.get("pending") :
            output += "<div id='pendingresult'>"
            if params.get("force") or self.api.should_refresh(req.cloud_name) :
                self.repopulate_views(req.session)
                self.api.reset_refresh(req.cloud_name)
                objs = active_list(req.cloud_name, "pending")
    
                if len(objs) > 0 :
                    output += "<h4>" + str(len(objs)) + " Pending Request(s):</h4>"
                    output += self.list_objects(req, req.active, objs, link = False, icon = False, label = 'label-warning')
                else :
                    output += "No Pending Objects"
            else :
                output += "unchanged"
    
            output += "</div>"
    
        else :
            success = True
            if params.get("operation") :
                operation_attrs = operations[params.get("operation")][1]
                funcname = req.active + (params.get("operation") if "ft" not in operation_attrs else operation_attrs["ft"])
                func = getattr(self.api, funcname)
                args = []
                keywords = int(params.get("keywords"))
                for keyidx in range(1, keywords + 1) :
                    args.append(params.get("keyword"+ str(keyidx)))
                    
                try :
                    func(req.cloud_name, *args)
                    if params.get("sync") :
                        output += self.heromsg + "\n<h4>Successfully " + (operation_attrs["label"] + "ed: ").replace("ee", "e") + "BOOTOBJECTNAME: " + params.get("keyword1")
                        output += "</h4></div>"
                    else :
                        raise exc.HTTPTemporaryRedirect(location = "/provision?object=")
                        
                except APIException, obj :
                    success = False
                    output += self.heromsg + "\n<h4>Error: BOOTOBJECTNAME " + params.get("keyword1") + " not " + operation_attrs["label"] + "ed: " + obj.msg
                    output += "</h4></div>"
                    
            if not success :
                return self.bootstrap(req, output)
    
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
                failed = active_list(req.cloud_name, "failed")
    
                if len(failed) > 0 :
                    output += "<h4>" + str(len(failed)) + " Failed Request(s):</h4>" + self.list_objects(req, req.active, failed, link = False, icon = 'icon-remove', label = 'label-important')
                if len(finished) > 0 :
                    output += "<h4>" + str(len(finished)) + " Finished Requests(s):</h4>" + self.list_objects(req, req.active, finished, link = False, icon = 'icon-ok', label = '')
                
                if len(objs) > 0 :
                    output += "<h4>" + str(len(objs))
                    output += (" Provisioned  " if liststate == "all" else " ")
                    output += "BOOTOBJECTNAMEs:</h4>"
                    output += self.list_objects(req, req.active, objs, icon = False)
                else :
                    output += self.heromsg + "\n<h4>&nbsp;No Objects</h4>"
            else :
                output += "BOOTSPINNER&nbsp;Loading Object State..."
                 
            output += "</div>"
    
            if req.active != "host" :
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
    
    def bootstrap(self, req, body, now = False) :
        replacements = []
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
        
            if req.session['connected'] :
                navcontents += "&nbsp;&nbsp;<a class='btn' href=\"BOOTDEST/disconnect\"><i class='icon-resize-small'></i>&nbsp;Disconnect</a>\n"
            else :
                navcontents += """
                    &nbsp;&nbsp;<a href="#" id='connectpop' class="btn">Connect!</a>
                """
    
            if not req.session["connected"] :
                if "clouds" in req.session :
                    cloudcontents = "<select name='running'>"
                    for cloud in req.session["clouds"] :
                        cloudcontents += "<option value='" + cloud["model"] + "," + cloud["name"] + "'>" + cloud["name"] + " (" + cloud["description"] + ")</option>"
                    cloudcontents += "</select>"
                if "available_clouds" in req.session :
                    available_clouds = deepcopy(req.session['available_clouds'])
                    if "clouds" in req.session :
                        for cloud in req.session['clouds'] :
                            if cloud['name'].lower() in available_clouds :
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
                         (req.cloud_name + "[" + req.model + "]") if req.session['connected'] else "Disconnected",
                         cloudcontents,
                         availablecontents,
                         body,
                         popoveractivate if (not req.session["connected"] and not req.skip_show) else "",
                         self.spinner,
                         req.dest,
                         req.active if req.active else "",
                         req.active_obj[:-1] if req.active_obj else "",
                         bootstrappath,
                         cbpath,
                      ]
    
        for idx in range(0, len(self.replacement_keys)) :
            x = replacements[idx]
            y = self.replacement_keys[idx]
            contents = contents.replace(y, x)
    
        return contents

class GUIDispatcher(Resource) :
    def __init__(self, keepsession, apiport, apihost) :

        Resource.__init__(self)
        self.third_party = File(cwd + "/3rd_party")
        self.files = File(cwd + "/gui_files")
        self.icon = File(cwd + "/gui_files/favicon.ico")
        self.dashboard = GUI(apiport, apihost)
        
        session_opts = {
            'session.data_dir' : '/tmp/dashboard_sessions_' + getpwuid(os.getuid())[0] + 'data',
            'session.type' : 'file',
            }
        
        if not keepsession :
            try :
                shutil.rmtree(session_opts['session.data_dir'])
            except OSError, obj :
                pass
            
        self.app = WSGIResource(reactor, reactor.threadpool, SessionMiddleware(self.dashboard, session_opts))

    def getChild(self, name, request) :
        # Hack to make WebOb work with Twisted
        request.content.seek(0,0)

        if name.count("3rd_party") :
                return self.third_party
        elif name.count("gui_files") :
                return self.files
        elif name.count("favicon.ico"):
                return self.icon
        else :
            return self.app

def gui(options) :
    reactor._initThreadPool()

    cbdebug("Will use API Service @ http://" + options.apihost + ":" + str(options.apiport))
    cbdebug("Point your browser at port: " + str(options.guiport) + ". (Bound to interface: " + options.guihost + ")")

    reactor.listenTCP(  int(options.guiport), \
                        Site(GUIDispatcher(options.keepsession, options.apiport, options.apihost)), \
                        interface = options.guihost)
    reactor.run()
