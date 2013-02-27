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

public class DiscoverHosts {
	@SuppressWarnings("unchecked")
	public static void main(String[] args) throws APINoSuchDataException {
		 try {
			 
			 String cloudname = "TESTOPENSTACK";

			 APIServiceClient api = new APIServiceClient("172.16.1.250", 7070);

			 Object[] hostlist = (Object[]) api.perform("hostlist", cloudname);

    		 System.out.println("-----------------------------------------");
			 for (int i = 0; i < hostlist.length; i++) {
				 HashMap<String, String> hostshortdict = (HashMap<String, String>) hostlist[i];
				 String hostname = String.valueOf(hostshortdict.get("name"));
				 HashMap<String, String> hostlongdict = (HashMap<String, String>) api.perform("hostshow", cloudname, hostname);
	    		 for(String key : hostlongdict.keySet()) {
	    		     System.out.println(key + " = " + String.valueOf(hostlongdict.get(key)));
	    		  }
	    		 System.out.println("-----------------------------------------");
			 }

		 } catch (APIException e) {
		     System.err.println("APIServiceClient failure: " + e);
		 }
	}

}
