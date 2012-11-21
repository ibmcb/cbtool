import java.util.HashMap;
import api.APIServiceClient;
import api.APIException;
import api.APINoSuchDataException;

public class ProvisionVM {
	@SuppressWarnings("unchecked")
	public static void main(String[] args) {
		 try {
			 APIServiceClient api = new APIServiceClient("172.16.1.222", 7070);
			 
			 // Create a VM
			 HashMap<String, String> vm = (HashMap<String, String>) api.perform("vmattach", "SIM1", "tinyvm");
			 
			 System.out.println("Created VM: " + vm.get("uuid"));
			 
			 // Lookup some data from the monitoring system
			 System.out.println(api.get_latest_data("SIM1", vm.get("uuid"), "runtime_os_VM"));
			 
    		 for(String key : vm.keySet()) {
    			 System.out.println(key + " = " + String.valueOf(vm.get(key)));
    		 }
    		 
    		 // Destroy the VM
    		 System.out.println("Destroying VM...");
    		 api.perform("vmdetach",  "SIM1", vm.get("uuid"));
    		 
		 } catch (APIException e) {
		     System.err.println("APIServiceClient failure: " + e);
		 } catch (APINoSuchDataException e) {
		     System.err.println("APIServiceClient failure: " + e);
		 }
	}

}
