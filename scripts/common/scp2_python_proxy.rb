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

require "xmlrpc/server"
FILEDIR = File.dirname(__FILE__)

conf = nil

require "/iaas/cli/iaas-config.rb"
require "/iaas/cli/deps/client_utils.rb"
require "/iaas/cli/deps/iaas_adapter.rb"

def final_result(read, write, pid)
  write.close
  output = read.read
  Process.wait2(pid)
  return Marshal.load(output.unpack("m")[0])
end

class CloudBenchPythonSCPProxy 
 @isa

 def initialize(conf)
   @isa = IaasAdapter.new(conf)
 end
 
 def describe_serviceregion()
  read, write = IO.pipe
  pid = fork do 
    read.close
        write.puts [Marshal.dump(@isa.describe_serviceregion())].pack("m")
  end
  return final_result(read, write, pid)
 end

 def describe_hyper_nodes()
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.describe_hyper_nodes(nil))].pack("m")
  end
  return final_result(read, write, pid)
 end

 def describe_storage_nodes()
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.describe_storage_nodes(nil))].pack("m")
  end
  return final_result(read, write, pid)
 end

 def describe_images(imageids)
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.describe_images(imageids))].pack("m")
  end
  return final_result(read, write, pid)
 end

 def describe_instances(instance_tag = nil)
  read, write = IO.pipe
  pid = fork do 
	read.close
	if instance_tag != nil
		instance_tag = Client_Utils.encode_input(instance_tag)
	end
    write.puts [Marshal.dump(@isa.describe_instances(nil, instance_tag, nil, "n", nil))].pack("m")
  end
  return final_result(read, write, pid)
 end
 
 def capture_image(instance_id, new_image_name)
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.capture_image(instance_id, nil, new_image_name, nil, nil))].pack("m")
  end
  return final_result(read, write, pid)
 end
 
 def terminate_instances(gid_array)
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.terminate_instances([], gid_array, true))].pack("m")
  end
  return final_result(read, write, pid)
 end
 
 def run_instances(imageid, type, instance_tag)
  read, write = IO.pipe
  pid = fork do 
    read.close
    write.puts [Marshal.dump(@isa.run_instances(imageid, 1, type, nil, nil, nil, Client_Utils.encode_input(instance_tag), nil, nil, nil, "n", nil))].pack("m")
  end
  return final_result(read, write, pid)
 end

end

if ARGV.size != 1 :
	print "Need port number.\n"
	exit(1)
end

XMLRPC::Config.const_set(:ENABLE_NIL_CREATE, true)
s = XMLRPC::Server.new(ARGV[0], "0.0.0.0")
s.add_handler("proxy", CloudBenchPythonSCPProxy.new(conf))
s.serve
