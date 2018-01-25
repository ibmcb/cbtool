/*******************************************************************************
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
*******************************************************************************/

/*
    CloudBench API Service XML-RPC Relay bindings for golang.

    @author: Michael R. Hines
 */
package api_service_client

import (
    "errors"
    "encoding/json"

    "gopkg.in/mgo.v2"
    "github.com/ibmcb/go-xmlrpc/src/net/rpc/xmlrpc"
)

type APIClient struct {
	Address string
	mongo *mgo.Session
        msattrs map[string]interface{}
        cloud_name string
	username string
	expid string
}

func (api *APIClient) Call(method string, args ...interface{}) (result map[string]interface{}, err error) {
    if api.Address == "" {
		return nil, errors.New("Failed to provide CloudBench URL.")
    }

    response, err := xmlrpc.Request(api.Address, method, args...)

    if err == nil {
        if response == nil || len(response) == 0 {
	    return nil, errors.New("Error: empty response")
       }
    } else {
       return nil, err
    }
    j, err := json.Marshal(response[0])
    var f map[string]interface{}
    if err == nil {
	    err := json.Unmarshal([]byte(j), &f)
	    if err == nil {
		f["status"] = int(f["status"].(float64))
		if f["status"] != 0 {
			return f, errors.New("Error: " + f["msg"].(string))
		}
	    } else {
		return nil, err
	    }
    } else {
	return nil, err
    }
    return f, nil
}


func (api *APIClient) Close() {
	if api.mongo != nil {
		defer api.mongo.Close()
		api.mongo = nil
	}
	api.msattrs = nil
	api.Address = ""
	api.cloud_name = ""
	api.username = ""
	api.expid = ""
}

func (api *APIClient) Get_performance_data(cloud_name string, uuid string, metric_class string, object_type string, metric_type string, latest bool, samples int, expid string, check_for_vpn bool) (result *mgo.Iter, err error) {
	var r map[string]interface{}

	if api.msattrs == nil {
		r, err = api.Call("cldshow", cloud_name, "metricstore")
		if err == nil {
			api.msattrs = r["result"].(map[string]interface{})
			r, err = api.Call("cldshow", cloud_name, "time")
			if err == nil {
				time := r["result"].(map[string]interface{})
				api.username = time["username"].(string)
				api.expid = time["experiment_id"].(string)
				if check_for_vpn {
					r, err = api.Call("cldshow", cloud_name, "vm_defaults")
					if err == nil {
						use_vpn_ip := (r["result"].(map[string]interface{}))["use_vpn_ip"]
						vpn_only := (r["result"].(map[string]interface{}))["vpn_only"]
						if (use_vpn_ip == "True" && vpn_only == "True") || (use_vpn_ip == true && vpn_only == true) {
							r, err = api.Call("cldshow", cloud_name, "vpn")
							if err == nil {
								api.msattrs["host"] = (r["result"].(map[string]interface{}))["server_bootstrap"].(string)
							}
						}
					}
				}
			}
		}
	}

	if api.msattrs != nil && api.mongo == nil && err == nil {
		api.mongo, err = mgo.Dial(api.msattrs["host"].(string) + ":" + api.msattrs["port"].(string))
	}

	if api.msattrs != nil && api.mongo != nil && err == nil {
			var allmatches bool
			var limitdocuments int
			var collection string

			if metric_class == "runtime" {
				object_type = metric_class + "_" + metric_type + "_" + object_type
			} else {
				object_type = metric_class + "_" + object_type
			}
			if latest {
				allmatches = true
				collection = "latest_" + object_type + "_" + api.username
				limitdocuments = 0
			} else {
				if samples != 0 {
					allmatches = false
					limitdocuments = samples
				} else {
					allmatches = true
					limitdocuments = 0
				}
				collection = object_type + "_" + api.username
			}

			c := api.mongo.DB("metrics").C(collection)

			criteria := map[string]string{}

			if expid != "auto" {
				criteria["expid"] = expid
			}

			if uuid != "all" {
				criteria["uuid"] = uuid
			}

			if allmatches {
				data := c.Find(criteria).Limit(limitdocuments)//.One(&result)
				return data.Iter(), err
			} else {
				data := c.Find(criteria)//.One(&result)
				return data.Iter(), err
			}

	}

	if err != nil {
		api.Close()
	}
	return nil, err
}

func (api *APIClient) Get_latest_app_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "runtime", "VM", "app", true, 0, expid, false)
}

func (api *APIClient) Get_latest_system_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "runtime", "VM", "os", true, 0, expid, false)
}

func (api *APIClient) Get_latest_management_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "management", "VM", "os", true, 0, expid, false)
}

func (api *APIClient) Get_app_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "runtime", "VM", "app", false, 0, expid, false)
}

func (api *APIClient) Get_system_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "runtime", "VM", "os", false, 0, expid, false)
}

func (api *APIClient) Get_management_data(cloud_name string, uuid string, expid string) (result *mgo.Iter, err error) {
	return api.Get_performance_data(cloud_name, uuid, "management", "VM", "os", false, 0, expid, false)
}
