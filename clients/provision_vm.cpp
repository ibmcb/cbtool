#include "../lib/api/api_service_client.hpp"
#include <string>
#include <iostream>
#include <cstdlib>

/*
 * Compile this with: g++ provision_vm.cpp -lxmlrpc++ -lxmlrpc_client++ -lmongoclient -lboost_filesystem -lboost_thread-mt -o test 
 */ 

using namespace std;

int main() {
    try {
	APIClient api("172.16.1.222", 7070);

	cout << "Creating VM..."<< endl;

	APIValue answer = api.perform("vmattach", "SIM1", "tinyvm"); 

	APIDictionary vm(answer);
	string uuid = APIString(vm["uuid"]);

	cout<< "VM created: " << uuid << endl;

	for(APIIterator it = vm.begin(); it != vm.end(); it++) {
	   string key = it->first;
	   APIValue value = it->second;
	   if(value.type() == API_STRING_TYPE)
		   cout<<"key: " + key + " value: " << (string) APIString(value) << endl;
	   else if(value.type() == API_STRING_TYPE)
		   cout<<"key: " + key + " value: " << (int) APIInteger(value) << endl;
	   else
		   cout<<"key: " + key + " unused value type: " << value.type() << endl;
	}

	/* Get some data from the monitoring system */
	mongo::auto_ptr<mongo::DBClientCursor> data = api.get_latest_data("SIM1", uuid, "runtime_os_VM");  
	while(data->more())
		cout<< data->next() << endl;

	cout<< "Destroying VM..." << endl;

	api.perform("vmdetach", "SIM1", uuid); 

    } catch (APIException const& e) {
	cerr << "Client threw unexpected error:" << e.what() << endl;
    }

    return 0;
}
