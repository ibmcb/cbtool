package api;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.UnknownHostException;
import java.util.HashMap;
import java.util.Vector;

import org.apache.xmlrpc.XmlRpcException;
import org.apache.xmlrpc.client.XmlRpcClient;
import org.apache.xmlrpc.client.XmlRpcClientConfigImpl;

import com.mongodb.BasicDBObject;
import com.mongodb.DB;
import com.mongodb.Mongo;

public class APIServiceClient {
    XmlRpcClient server = new XmlRpcClient(); 
    HashMap<String, String> msattrs = null; 
    Mongo msci = null;
    String username = null;
    DB db = null;
   
	public APIServiceClient(String address, int port) throws APIException {
		 XmlRpcClientConfigImpl config = new XmlRpcClientConfigImpl();
		 String url = "http://" + address + ":" + port;
		 try {
			 config.setServerURL(new URL(url + "/RPC2"));
		 } catch(MalformedURLException e) {
			throw new APIException("Failed to connect to API @ " + url + ": " + e); 
		 }
	     server.setConfig(config);
	}
	
	@SuppressWarnings("unchecked")
	public void dashboard_conn_check(String cloud_name) throws APIException {
		if(msattrs == null) {
			msattrs = (HashMap<String, String>) perform("cldshow", cloud_name, "metricstore");
			String host = msattrs.get("host");
			int port = Integer.parseInt(msattrs.get("port"));
			
			try {
				msci = new Mongo(host, port);
			} catch(UnknownHostException e) {
				throw new APIException("Could not connect to mongodb @ hostname: " + host + ", port: " + port);
			}
			
			db = msci.getDB("metrics");
			username = ((HashMap<String, String>) perform("cldshow", cloud_name, "time")).get("username");
		}
	}
	
	public Object find(String collection, BasicDBObject criteria) {
	  return db.getCollection(collection).find(criteria);
	}
	
	public Object get_latest_data(String cloud_name, String uuid, String type) throws APIException, APINoSuchDataException {
		BasicDBObject criteria = new BasicDBObject();
		dashboard_conn_check(cloud_name);
		criteria.put("uuid", uuid);
		Object metrics = find("latest_" + type + "_" + username, criteria);
		if(metrics == null)
			throw new APINoSuchDataException("No " + type + " data available for uuid " + uuid + " cloud " + cloud_name);
		return metrics;
	}
	
	@SuppressWarnings("unchecked")
	private Object go(String function, Vector<String> parameters) throws APIException {
		try {
			HashMap<Object, Object> resp = (HashMap<Object, Object>) server.execute(function, parameters);
			 Integer status = (Integer) resp.get("status");
		     if(status == 0) {
		    	 return resp.get("result");
		     } else
		    	 throw new APIException("Function " + function + " failed: " + status + ": " + resp.get("msg"));
		} catch (XmlRpcException e) {
	    	 throw new APIException("Function " + function + " failed: " + e);
		}
	}

	
	public Object perform(String function, String p1) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 return go(function, params);
	}	
	public Object perform(String function, String p1, String p2) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 return go(function, params);
	}
	public Object perform(String function, String p1, String p2, String p3) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 params.addElement(p3);
		 return go(function, params);
	}	
	
	public Object perform(String function, String p1, String p2, String p3, String p4) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 params.addElement(p3);
		 params.addElement(p4);
		 return go(function, params);
	}
	
	public Object perform(String function, String p1, String p2, String p3, String p4, String p5) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 params.addElement(p3);
		 params.addElement(p4);
		 params.addElement(p5);
		 return go(function, params);
	}
	
	public Object perform(String function, String p1, String p2, String p3, String p4, String p5, String p6) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 params.addElement(p3);
		 params.addElement(p4);
		 params.addElement(p5);
		 params.addElement(p6);
		 return go(function, params);
	}
	
	public Object perform(String function, String p1, String p2, String p3, String p4, String p5, String p6, String p7) throws APIException {
		 Vector<String> params = new Vector<String>();
		 params.addElement(p1);
		 params.addElement(p2);
		 params.addElement(p3);
		 params.addElement(p4);
		 params.addElement(p5);
		 params.addElement(p6);
		 params.addElement(p7);
		 return go(function, params);
	}
	
	public static void main(String[] args) throws MalformedURLException {
		System.out.println("Include this jar in your classpath to write code against CloudBench.");
	}
}


