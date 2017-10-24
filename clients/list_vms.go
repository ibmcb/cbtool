/*
# Copyright (c) 2017 DigitalOcean, Inc. 

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/

/*
    Example use of the CloudBench golang bindings.

    @author: Michael R. Hines
 */
package main

import (
    "fmt"
    "github.com/ibmcb/cbtool/lib/api"
)

func main() {
	api := api_service_client.APIClient{Address: "http://localhost:7070"}
	r, err := api.Call("vmlist", "MYSIMCLOUD")

	if err == nil && r["result"] != nil {
		vms := r["result"].([]interface{})
		for idx := range vms {
			vm := vms[idx].(map[string]interface{})

			iter, err := api.Get_latest_management_data("MYSIMCLOUD", vm["uuid"].(string), vm["experiment_id"].(string))
			if err != nil {
				fmt.Printf("ERROR! %s\n", err)
			}

			var data map[string]interface{}

			for iter.Next(&data) {
				fmt.Printf("VM: %s Provisioning time: %d\n", vm["name"], data["mgt_003_provisioning_request_completed"].(int))
			}
		}
	}

	api.Close()
}
