#!/usr/bin/env bash
#/*******************************************************************************
# Copyright (c) 2019 DigitalOcean, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0
#
#/*******************************************************************************
#    Created on October 10, 2018
#    VPN-support for k8s within CloudBench 
#    @author: Michael R. Hines
#
#   We take a completely different approach with using OpenVPN with Kubernetes.
#   We make exclusive use of the 'helm' k8s package manager, which comes with a ready-to-use
#   OpenVPN server running directly within the k8s cluster itself.
#
#   We connect to it without any need to run OpenVPN inside the containers like we do with
#   VMs. After the server is running, we setup iptables port forwarding rules that allow
#   the containers to report their telemetry and logs back to CloudBench over the VPN.
#   Everything works transparently and is setup for the user by this script.
#
#   Usage:
#   $ ./cb -f exit
#   $ util/setuphelm.sh
#
#   At the end of the script, we have preliminary support to also setup a helm-based
#   Docker registry (based on Object Storage), which is extremely convenient. This doesn't
#   fully work yet, however, because it requires the Docker daemon on each k8s node
#   to be modified to support access to insecure private docker registries. This is not possible
#   with public "aaS" k8s clusters because we don't have access to the k8s hosts.
#   Thus, it will only work with pre-existing clusters until we find a workaround.
#
#   Dependencies:
#   Install kubectl
#   Install helm
#/*******************************************************************************

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

if [ x"$(which kubectl)" == x ] ; then
	echo "kubectl is required. Please install it and try again."
	exit 1
fi

if [ x"$(which helm)" == x ] ; then
	echo "helm is required. Please install it and try again."
	exit 1
fi

function check_error {
	if [ $1 -gt 0 ] ; then
		echo "Command failed ($1): $2"
		exit $1
	fi
}

function check_ready {
	while true ; do
		notready="$(kubectl get pods --all-namespaces -o json  | jq -r '.items[] | select(.status.phase != "Running" or ([ .status.conditions[] | select(.type == "Ready" and .state == false) ] | length ) == 1 ) | .metadata.namespace + "/" + .metadata.name')"

		if [ x"$notready" == x ] ; then
			echo "All pods ready."
			notready="$(kubectl get svc --all-namespaces | grep -v NAMESPACE | grep pending)"
			if [ x"$notready" == x ] ; then
				echo "All services ready."
				break
			else
				echo "Services still not ready:"
			fi
		else
			echo "Pods or still not ready:"
		fi

		echo "$notready"
		sleep 10
		
		
	done
}

pushd ${dir}/../
cldid=$(./cb cldlist | grep MY | cut -d "|" -f 2 | grep "^MY" | sed "s/ \+//g")
PREFIX="from lib.api.api_service_client import APIClient; from lib.auxiliary.data_ops import str2dic; api = APIClient('http://localhost:7070');"
vmcname=$(python -c "$PREFIX print api.vmclist('${cldid}')[0]['name']")
echo "Exporting kubeconfig for VMC $vmcname $cldid ..."
python -c "$PREFIX print api.vmcshow('${cldid}', '${vmcname}')['kubeconfig']" > /tmp/kubeconfig.yaml
popd

export KUBECONFIG=/tmp/kubeconfig.yaml

echo "Installing helm in the cluster..."
rm -rf ~/.helm/
kubectl -n kube-system create serviceaccount tiller
check_error $? "tiller account"
check_ready
kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller
check_error $? "tiller cluster-admin"
check_ready
helm init --service-account tiller
check_error $? "tiller service account"
check_ready

vpn_network=$(python -c "$PREFIX print api.cldshow('${cldid}', 'vpn')['network'].lower()")

cat << EOF > /tmp/helm_openvpn_values.yaml 
replicaCount: 1

updateStrategy: {}
image:
  repository: jfelten/openvpn-docker
  tag: 1.1.0
  pullPolicy: IfNotPresent
service:
  type: LoadBalancer
  externalPort: 443
  internalPort: 443
  externalIPs: []
  nodePort: 32085
  annotations: {}
podAnnotations: {}

resources:
  limits:
    cpu: 1024m
    memory: 1024Mi
  requests:
    cpu: 1024m
    memory: 1024Mi
persistence:
  enabled: true
  storageClass: do-block-storage
  accessMode: ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  size: 1Gi
openvpn:
  # Network allocated for openvpn clients (default: 10.240.0.0).
  OVPN_NETWORK: ${vpn_network} 
  # Network subnet allocated for openvpn client (default: 255.255.0.0).
  OVPN_SUBNET: 255.255.240.0
  # Protocol used by openvpn tcp or udp (default: udp).
  OVPN_PROTO: tcp
  dhcpOptionDomain: true
  # Redirect all client traffic through VPN
  redirectGateway: false 
  # Arbitrary lines appended to the end of the server configuration file
  conf: |
    script-security 2
    client-to-client
    push "route 10.244.0.0 255.255.0.0"
    up "/bin/bash -c '/bin/touch /etc/openvpn/certs/portforward.sh && /bin/chmod +x /etc/openvpn/certs/portforward.sh && /etc/openvpn/certs/portforward.sh'"
    max-clients 10000
EOF

echo "Installing OpenVPN in the cluster ... "
while true ; do
	helm install stable/openvpn -f /tmp/helm_openvpn_values.yaml
	if [ $? -eq 0 ] ; then
		break
	fi

	echo "Helm didn't succeed. Trying again."
	sleep 10
	check_ready
done

check_ready

echo "Configuring CB to recognize the openvpn server ..."
POD_NAME=$(kubectl get pods --namespace "default" -l app=openvpn -o jsonpath='{ .items[0].metadata.name }')
INTERNAL_VPN_IP=$(kubectl describe pod ${POD_NAME} | grep IP | sed "s/.* //g")
VPN_STATUS_PORT=$(python -c "$PREFIX print api.cldshow('${cldid}', 'vpn')['management_port'].lower()")

python -c "$PREFIX api.cldalter('${cldid}', 'vpn', 'server_bootstrap', '${INTERNAL_VPN_IP}')"
python -c "$PREFIX api.cldalter('${cldid}', 'vpn', 'use_vpn_ip', 'True')"

while true ; do
	RELEASE=$(helm list -q)
	code=$?
	if [ $code -eq 0 ] && [ x"$RELEASE" != x ] ; then
		break
	fi
	echo "Helm return code $code and release $RELEASE ..."
	sleep 10
	check_ready
done

echo "Generating client key for $RELEASE..."
check_ready
POD_NAME=$(kubectl get pods --namespace "default" -l "app=openvpn,release=${RELEASE}" -o jsonpath='{ .items[0].metadata.name }')
check_error $? "get pods"
check_ready
SERVICE_NAME=$(kubectl get svc --namespace "default" -l "app=openvpn,release=${RELEASE}" -o jsonpath='{ .items[0].metadata.name }')
echo "Service name: ${SERVICE_NAME}"
check_error $? "get service name"
check_ready

while true ; do
	SERVICE_IP=$(kubectl get svc --namespace "default" "$SERVICE_NAME" -o go-template='{{ range $k, $v := (index .status.loadBalancer.ingress 0)}}{{ $v }}{{end}}')
	code=$?
	if [ $code -eq 0 ] && [ x"$SERVICE_IP" != x ] ; then
		break
	fi
	echo "Service IP not yet ready ..."
	sleep 10
	check_ready
done

echo "Service IP: ${SERVICE_IP}"

KEY_NAME=kubeVPN-${cldid}-${vmcname}
kubectl --namespace "default" exec -it "$POD_NAME" /etc/openvpn/setup/newClientCert.sh "$KEY_NAME" "$SERVICE_IP"
check_error $? "create client certificate"
kubectl --namespace "default" exec -it "$POD_NAME" cat "/etc/openvpn/certs/pki/$KEY_NAME.ovpn" > "/tmp/${KEY_NAME}.ovpn"
check_error $? "extract client certificate"

echo "management 127.0.0.1 ${VPN_STATUS_PORT}" >> /tmp/${KEY_NAME}.ovpn
echo "management-log-cache 10000" >> /tmp/${KEY_NAME}.ovpn

sudo pkill -9 -f ${KEY_NAME}

echo "Starting VPN ..."
sudo openvpn --config /tmp/${KEY_NAME}.ovpn --daemon

sleep 20

echo "Getting local VPN IP... "

bootstrap=""

while true ; do
	bootstrap=$(echo -e "log all\nexit" | nc localhost ${VPN_STATUS_PORT} | grep "ip addr" | sed "s/.*local //g" | sed "s/ .*//g")
	if [ x"$bootstrap" != x ] ; then
		echo "Bootstrap VPN IP: $bootstrap"
		break
	fi

	echo "Boostrap VPN IP not ready yet..."
	sleep 10
done

# The VPN is working, but now we need the services internal to k8s
# to be able to reach CloudBench.

echo "Uploading iptables rules ... "

logproto=$(python -c "$PREFIX print api.cldshow('${cldid}', 'logstore')['protocol'].lower()")
logport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'logstore')['port'].lower()")
metricport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'metricstore')['port'].lower()")
fileport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'filestore')['port'].lower()")
apiport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'api_defaults')['port'].lower()")
redisport=6379 # command isn't working yet

cat << EOF > ${dir}/portforward.sh
#!/usr/bin/env bash

iptables -A PREROUTING -t nat -i eth0 -p tcp --dport 22 -j DNAT --to ${bootstrap}:22
iptables -A FORWARD -p tcp -d ${bootstrap} --dport 22 -j ACCEPT

iptables -A PREROUTING -t nat -i eth0 -p tcp --dport ${metricport} -j DNAT --to ${bootstrap}:${metricport}
iptables -A FORWARD -p tcp -d ${bootstrap} --dport ${metricport} -j ACCEPT

iptables -A PREROUTING -t nat -i eth0 -p ${logproto} --dport ${logport} -j DNAT --to ${bootstrap}:${logport}
iptables -A FORWARD -p tcp -d ${bootstrap} --dport ${logport} -j ACCEPT

iptables -A PREROUTING -t nat -i eth0 -p tcp --dport ${apiport} -j DNAT --to ${bootstrap}:${apiport}
iptables -A FORWARD -p tcp -d ${bootstrap} --dport ${apiport} -j ACCEPT

iptables -A PREROUTING -t nat -i eth0 -p tcp --dport ${redisport} -j DNAT --to ${bootstrap}:${redisport}
iptables -A FORWARD -p tcp -d ${bootstrap} --dport ${redisport} -j ACCEPT

iptables -A PREROUTING -t nat -i eth0 -p tcp --dport ${fileport} -j DNAT --to ${bootstrap}:${fileport}
iptables -A FORWARD -p tcp -d ${bootstrap} --dport ${fileport} -j ACCEPT
EOF

chmod +x ${dir}/portforward.sh

kubectl cp $dir/portforward.sh default/${POD_NAME}:/etc/openvpn/certs/portsforward.sh
kubectl exec -it ${POD_NAME} /bin/chmod +x /etc/openvpn/certs/portsforward.sh
kubectl exec -it ${POD_NAME} /etc/openvpn/certs/portsforward.sh

rm ${dir}/portforward.sh 

# This part isn't working yet, but the code is here.

echo "Installing the docker registry"

REGISTRYPORT=5000
PRIVATE_REGISTRY="ibmcb" # ${INTERNAL_VPN_IP}:${REGISTRYPORT}
accesskey="$1"
secretkey="$2"

# An S3-compatible-backed docker registry, running
# directly inside of the k8s cluster

cat << EOF >> /tmp/cbhelmregistry.yaml
replicaCount: 1
updateStrategy:
podAnnotations: {}

image:
  repository: registry
  tag: 2.6.2
  pullPolicy: IfNotPresent
service:
  name: registry
  type: ClusterIP
  port: ${REGISTRYPORT} 
  annotations: {}
ingress:
  enabled: false
  path: /
  hosts:
    - chart-example.local
  annotations:
  labels: {}
  tls:
resources: {}
  # We usually recommend not to specify default resources and to leave this as a conscious
  # choice for the user. This also increases chances charts run on environments with little
  # resources, such as Minikube. If you do want to specify resources, uncomment the following
  # lines, adjust them as necessary, and remove the curly braces after 'resources:'.
  # limits:
  #  cpu: 100m
  #  memory: 128Mi
  # requests:
  #  cpu: 100m
  #  memory: 128Mi
persistence:
  accessMode: 'ReadWriteOnce'
  enabled: false
  size: 10Gi
  # storageClass: '-'

storage: s3 
secrets:
   s3:
     accessKey: "${accesskey}"
     secretKey: "${secretkey}"
s3:
  region: nyc3
  regionEndpoint: nyc3.digitaloceanspaces.com
  bucket: mariner-docker
  encrypt: false
  secure: true
configData:
  version: 0.1
  log:
    fields:
      service: registry
  storage:
    cache:
      blobdescriptor: inmemory
  http:
    addr: :${REGISTRYPORT}
    headers:
      X-Content-Type-Options: [nosniff]
  health:
    storagedriver:
      enabled: true
      interval: 10s
      threshold: 3
securityContext:
  enabled: true
  runAsUser: 1000
  fsGroup: 1000
priorityClassName: ""
nodeSelector: {}
tolerations: []
EOF

# There doesn't seem to be a way to do this without access to
# the host k8s droplets to modify the docker daemon to allow
# insecure docker registries to be accessible.

#helm install stable/docker-registry -f /tmp/cbhelmregistry.yaml

rm /tmp/cbhelmregistry.yaml

#check_error $? "helm install registry"
#check_ready

#SERVICE=$(helm list | grep registry | cut -d " " -f 1)
#check_error $? "find helm registry service"
#PODNAME=$(kubectl get pods --namespace default -l "app=docker-registry,release=${SERVICE}" -o jsonpath="{.items[0].metadata.name}")
#check_error $? "get registry pod name"
#REGISTRYIP=$(kubectl describe pod ${PODNAME} | grep IP | sed "s/.* //g")
#check_error $? "get registry IP address"

python -c "$PREFIX api.cldalter('${cldid}', 'vm_defaults', 'image_prefix', '${PRIVATE_REGISTRY}/ubuntu')"

kubectl get pods

echo "Done."
