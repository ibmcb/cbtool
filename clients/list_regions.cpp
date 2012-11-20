#include "api_service_client.hpp"
#include <string>
#include <iostream>
#include <cstdlib>

/*
 * Compile this with: g++ list_regions.cpp -lxmlrpc++ -lxmlrpc_client++ -lmongoclient -lboost_filesystem -lboost_thread-mt -o test 
 */ 

using namespace std;

int main() {
    try {
	APIClient api("172.16.1.222", 7070);
	APIValue answer = api.perform("vmclist", "SIM1"); 
	APIArray vmcs(answer);

	for(int x = 0; x < vmcs.size() ; x++) {
	   APIDictionary dict(vmcs[x]);
           string uuid = APIString(dict["uuid"]);
           string name = APIString(dict["name"]);
	   cout<<"vmc: " + name + " uuid: " + uuid << endl;
	}

    } catch (APIException const& e) {
	cerr << "Client threw unexpected error:" << e.what() << endl;
    }

    return 0;
}
