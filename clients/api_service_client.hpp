#ifndef API_SERVICE_CLIENT
#define API_SERVICE_CLIENT

#include <xmlrpc-c/girerr.hpp>
#include <xmlrpc-c/base.hpp>
#include <xmlrpc-c/client_simple.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string.hpp>
#include <mongo/client/dbclient.h>

typedef xmlrpc_c::value APIValue;
typedef xmlrpc_c::value_string APIString;
typedef xmlrpc_c::value_int APIInteger;
typedef std::map<std::string, APIValue>::iterator APIIterator;

const int API_INT_TYPE = xmlrpc_c::value::TYPE_INT;
const int API_STRING_TYPE = xmlrpc_c::value::TYPE_STRING;
const int API_CHAR_TYPE = xmlrpc_c::value::TYPE_I8;
const int API_BOOLEAN_TYPE = xmlrpc_c::value::TYPE_BOOLEAN;
const int API_DOUBLE_TYPE = xmlrpc_c::value::TYPE_DOUBLE;
const int API_DATE_TYPE = xmlrpc_c::value::TYPE_DATETIME;
const int API_BYTESTRING_TYPE = xmlrpc_c::value::TYPE_BYTESTRING;
const int API_STRUCT_TYPE = xmlrpc_c::value::TYPE_STRUCT;
const int API_ARRAY_TYPE = xmlrpc_c::value::TYPE_ARRAY;
const int API_NULL_TYPE = xmlrpc_c::value::TYPE_NIL;


class APIException : public std::exception
{
	public:
	APIException(std::string m ="exception!") : msg(m) {}
	~APIException() throw() {}
	const char* what() const throw() { return msg.c_str(); }

	private:
		std::string msg;
};

class APINoSuchDataException : public std::exception
{
	public:
	APINoSuchDataException(std::string m ="exception!") : msg(m) {}
	~APINoSuchDataException() throw() {}
	const char* what() const throw() { return msg.c_str(); }

	private:
		std::string msg;
};

class APIArray {
	public :
	std::vector<APIValue> values;
	APIArray(APIValue toconvert) {
		values = xmlrpc_c::value_array(toconvert).vectorValueValue();
	}

	APIValue operator[](const long idx) {
		return values[idx];
	}

	int size() {
		return values.size();
	}
};

class APIDictionary  {
	public :

	std::map<std::string, APIValue> values;

	APIDictionary(APIValue toconvert) {
		values = xmlrpc_c::value_struct(toconvert);
	}

	APIValue operator[](const std::string key) {
		return values[key];
	}

	int size() {
		return values.size();
	}

	APIIterator begin() {
		return values.begin();
	}
	APIIterator end() {
		return values.end();
	}
};


class APIClient
{
	private :
		xmlrpc_c::clientSimple client;
		std::string service_url;
		mongo::DBClientConnection msci;
		int msattrs;
		std::string host, port, username;

		APIValue check_result(APIValue answer, std::string function, std::string cloud_name) {
			APIDictionary response(answer);
			std::string msg = APIString(response["msg"]);
			int status = APIInteger(response["status"]);
			if(status)
				throw APIException("API Returned error for function " + function + ": (" + boost::lexical_cast<std::string>(status) + "): " + msg);
			return response["result"];
		}
	public :
		APIClient(std::string address, long long port) {
		   msattrs = 0;
		   service_url = "http://" + address + ":" + boost::lexical_cast<std::string>(port) + "/RPC2";
		}

		void dashboard_conn_check(std::string cloud_name) {
			if(!msattrs) {
				APIDictionary result(perform("cldshow", cloud_name, "metricstore"));
				host = APIString(result["hostname"]);
				port = APIString(result["port"]);
				msci.connect(host + ":" + port + "/metrics");
				result = APIDictionary(perform("cldshow", cloud_name, "time"));
				username = APIString(result["username"]);
				msattrs = 1;
			}	
		} 	

		mongo::auto_ptr<mongo::DBClientCursor> find(std::string collection, mongo::BSONObj criteria) {
			return msci.query("db." + collection, criteria); 
		}

		mongo::auto_ptr<mongo::DBClientCursor> get_latest_data(std::string cloud_name, std::string uuid, std::string type) {
			dashboard_conn_check(cloud_name);
			mongo::BSONObjBuilder b;
			b.append("uuid", uuid);
			mongo::BSONObj obj = b.obj();
			return find("latest_" + type + "_" + username, obj);
		}

		APIValue perform(std::string function, std::string cloud_name) {
			APIValue answer;
			try { client.call(service_url, function, "s", &answer, cloud_name.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1) {
			APIValue answer;
			try { client.call(service_url, function, "ss", &answer, cloud_name.c_str(), p1.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2) {
			APIValue answer;
			try { client.call(service_url, function, "sss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}
		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2, std::string p3) {
			APIValue answer;
			try { client.call(service_url, function, "ssss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str(), p3.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2, std::string p3, std::string p4) {
			APIValue answer;
			try { client.call(service_url, function, "sssss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str(), p3.c_str(), p4.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2, std::string p3, std::string p4, std::string p5) {
			APIValue answer;
			try { client.call(service_url, function, "ssssss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str(), p3.c_str(), p4.c_str(), p5.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2, std::string p3, std::string p4, std::string p5, std::string p6) {
			APIValue answer;
			try { client.call(service_url, function, "sssssss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str(), p3.c_str(), p4.c_str(), p5.c_str(), p6.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		APIValue perform(std::string function, std::string cloud_name, std::string p1, std::string p2, std::string p3, std::string p4, std::string p5, std::string p6, std::string p7) {
			APIValue answer;
			try { client.call(service_url, function, "ssssssss", &answer, cloud_name.c_str(), p1.c_str(), p2.c_str(), p3.c_str(), p4.c_str(), p5.c_str(), p6.c_str(), p7.c_str()); } 
			catch(std::exception const& e) { throw APIException("API Returned error for function " + function + ": " + e.what()); }
			return check_result(answer, cloud_name, function);
		}

		/* Simple helper string to split strings */
		std::vector<std::string> split(std::string content, std::string separator) {
			std::vector<std::string> result;
			boost::split(result, content, boost::is_any_of(separator));
			return result;
		}
};

#endif //API_SERVICE_CLIENT
