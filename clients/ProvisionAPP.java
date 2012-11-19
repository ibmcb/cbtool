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
				 String role = components[1];
				 String name = components[2];
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
