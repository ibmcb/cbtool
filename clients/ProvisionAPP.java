//******************************************************************************
//Copyright (c) 2012 IBM Corp.
//
//Licensed under the Apache License, Version 2.0 (the "License");
//you may not use this file except in compliance with the License.
//You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
//Unless required by applicable law or agreed to in writing, software
//distributed under the License is distributed on an "AS IS" BASIS,
//WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//See the License for the specific language governing permissions and
//limitations under the License.
//******************************************************************************

import java.util.HashMap;
import api.APIServiceClient;
import api.APIException;
import api.APINoSuchDataException;

public class ProvisionAPP {
	@SuppressWarnings("unchecked")
	public static void main(String[] args) {
		 try {
			 APIServiceClient api = new APIServiceClient("172.16.1.222", 7070);
			 
			 // Create an APP
			 HashMap<String, String> app = (HashMap<String, String>) api.perform("appattach", "SIM1", "nullworkload");
			 System.out.println("Created application: " + app.get("uuid")); 
			 
			 // Lookup some data from the monitoring system
			 for(String vm : app.get("vms").split(",")) {
				 String [] components = vm.split("|");
				 String uuid = components[0];
				 //String role = components[1];
				 //String name = components[2];
				 Object data = api.get_latest_data("SIM1", uuid, "runtime_app_VM");
				 System.out.println("Looked up data for VM " + uuid + ": " + data);
			 }
			 
    		 for(String key : app.keySet()) {
    			 System.out.println(key + " = " + String.valueOf(app.get(key)));
    		 }
    		 
    		 // Destroy the Application
    		 api.perform("appdetach",  "SIM1", app.get("uuid"));
    		 System.out.println("Application destroyed.");
    		 
		 } catch (APIException e) {
		     System.err.println("APIServiceClient failure: " + e);
		 } catch (APINoSuchDataException e) {
		     System.err.println("APIServiceClient failure: " + e);
		 }
	}

}
