#include "api_service_client.hpp"
#include <string>
#include <iostream>
#include <cstdlib>

/*
 * Compile this with: g++ provision_application.cpp -lxmlrpc++ -lxmlrpc_client++ -lmongoclient -lboost_filesystem -lboost_thread-mt -o test 
 */ 

using namespace std;

int main() {
    try {
	APIClient api("172.16.1.222", 7070);

	api.dashboard_conn_check("SIM1");

	cout << "Creating Application..."<< endl;

	APIValue answer = api.perform("appattach", "SIM1", "nullworkload"); 

	APIDictionary app(answer);
	string app_uuid = APIString(app["uuid"]);

	cout<< "Application created: " << app_uuid << endl;

	for(APIIterator it = app.begin(); it != app.end(); it++) {
	   string key = it->first;
	   APIValue value = it->second;
	   if(value.type() == API_STRING_TYPE)
		   cout<<"key: " + key + " value: " << (string) APIString(value) << endl;
	   else if(value.type() == API_STRING_TYPE)
		   cout<<"key: " + key + " value: " << (int) APIInteger(value) << endl;
	   else
		   cout<<"key: " + key + " unused value type: " << value.type() << endl;
	}

	vector<string> vms = api.split((string) APIString(app["vms"]), ",");

	/* Get some data from the monitoring system */
	for(int vmidx = 0; vmidx < vms.size(); vmidx++) {
		vector<string> components = api.split(vms[vmidx], "|");
		string uuid = components[0];
		string role = components[1];
		string name = components[2];

		cout << "VM: " + uuid << endl;

		mongo::auto_ptr<mongo::DBClientCursor> data = api.get_latest_data("SIM1", uuid, "runtime_app_VM");  
		while(data->more())
			cout<< data->next() << endl;
	}

	cout<< "Destroying Application..." << endl;

	api.perform("appdetach", "SIM1", app_uuid); 

    } catch (APIException const& e) {
	cerr << "Client threw unexpected error:" << e.what() << endl;
    }

    return 0;
}
