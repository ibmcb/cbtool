#!/usr/bin/env ruby

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

require "xmlrpc/client"
require "rubygems"
require "mongo"

FILEDIR = File.dirname(__FILE__)

class APIException < Exception
end

class APINoSuchMetricException < Exception
end

class APIClient < XMLRPC::Client
 @msattrs = false 
 @msci = false
 @vms = {}
 @username = false

 def initialize(address, port)
  super address, "/RPC2", port
  @functions = self.call("get_functions")["result"]
 end
 
 def find(collection, criteria)
  return @msci.db("metrics").collection(collection).find(criteria)
 end

 def method_missing(m, *args, &block)
   name = "#{m}"
   if @functions[name]
     begin
	resp = self.call(m, *args)
     rescue XMLRPC::FaultException => e
 	raise APIException, "Invalid arguments to API: #{e.message}"
     end
     if resp["status"].to_i != 0
	raise APIException, "Error (#{name}, #{resp['status']}): #{resp["msg"]}"
     end
     return resp["result"]
   else
     return APIException, "No such API function: #{name}. Open the API in a browser to verify compatibility."
   end
 end 

 def dashboard_conn_check(cloud_name, msattrs = false, username = false)
   if not @msattrs
     if not msattrs
       @msattrs = self.cldshow(cloud_name, "metricstore")
     end
     @msci = Mongo::Connection.new(@msattrs["host"], @msattrs["port"])
     if not @username
       if not username
	 @username = self.cldshow(cloud_name, "time")["username"]
       end
     end end
 end
 def get_latest_data(cloud_name, uuid, type)
   self.dashboard_conn_check(cloud_name)
   metrics = self.find("latest_#{type}_#{@username}", {"uuid" => uuid})
   if not metrics :
      raise APINoSuchMetricException, "No #{type} data available for uuid #{uuid}, cloud #{cloud_name}"
   end
   return metrics
 end
end

XMLRPC::Config.const_set(:ENABLE_NIL_CREATE, true)
XMLRPC::Config::ENABLE_NIL_PARSER = true
