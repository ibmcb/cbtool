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
#   After the VPN is setup, we perform even more craziness with helm. We install an
#   object-storage-based docker registry directly into the cluster. This script defaults
#   to using object storage, but it could also be flexible enough to use volumes
#   whatever is supported by the helm chart.
#
#   Finally, because docker is wierd, docker won't use unsigned or self-signed docker
#   registries by default. As a result we have to do more trickery. The only way to
#   make docker use the registry is to create a /etc/docker/daemon.json file that
#   whitelists it *and* login to the k8s host and restart the docker daemon. The only
#   way to make this happen is to install a privileged pod on every k8s worker node
#   that mounts the host filesystem, installs an ssh key and makes the appropriate
#   modifications to the /etc/shadow file (referred to as 'backdoor' below). Once that
#   is done, we can SSH into each k8s worker node finally and restart the daemon,
#   allowing CB to create AIs that are able to use our registry.
#
#   What a PITA.
#
#   Usage:
#   $ ./cb -f exit
#   $ util/setuphelm.sh [objectstorage accesskey] [objectstorage secretkey]
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
			echo "Pods still not ready:"
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

KEY_NAME=kubeVPN-${cldid}-${vmcname}
sudo pkill -9 -f ${KEY_NAME}

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

cat << EOF > /tmp/cbhelm_openvpn_values.yaml 
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
	helm install stable/openvpn -f /tmp/cbhelm_openvpn_values.yaml
	if [ $? -eq 0 ] ; then
		break
	fi

	echo "Helm didn't succeed. Trying again."
	sleep 10
	check_ready
done

echo "Installing the docker registry"

REGISTRYPORT=5000
accesskey="$1"
secretkey="$2"

# An S3-compatible-backed docker registry, running
# directly inside of the k8s cluster

#  repository: registry
#  tag: 2.6.2

cat << EOF > /tmp/cbhelmregistry.yaml
replicaCount: 1
updateStrategy:
podAnnotations: {}

image:
  repository: registry@sha256 
  tag: 5a156ff125e5a12ac7fdec2b90b7e2ae5120fa249cf62248337b6d04abc574c8 
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

echo "Installing docker registry backed by Object storage"

helm install stable/docker-registry -f /tmp/cbhelmregistry.yaml

check_error $? "helm install registry"

check_ready

echo "Configuring CB to recognize the openvpn server ..."
POD_NAME=$(kubectl get pods --namespace "default" -l app=openvpn -o jsonpath='{ .items[0].metadata.name }')

VPN_STATUS_PORT=$(python -c "$PREFIX print api.cldshow('${cldid}', 'vpn')['management_port'].lower()")

echo "VPN status port: ${VPN_STATUS_PORT}"

python -c "$PREFIX api.cldalter('${cldid}', 'vpn', 'use_vpn_ip', 'True')"

while true ; do
	RELEASE=$(helm list | grep openvpn | sed "s/\t/ /g" | cut -d " " -f 1)
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
	INTERNAL_SERVICE_IP=$(kubectl get svc --namespace "default" "$SERVICE_NAME" -o json | jq -r .spec.clusterIP)
	code=$?
	if [ $code -eq 0 ] && [ x"$SERVICE_IP" != x ] ; then
		break
	fi
	echo "Service IP not yet ready ..."
	sleep 10
	check_ready
done

echo "Service IP: ${SERVICE_IP}"

python -c "$PREFIX api.cldalter('${cldid}', 'vpn', 'server_bootstrap', '${INTERNAL_SERVICE_IP}')"
kubectl --namespace "default" exec -it "$POD_NAME" /etc/openvpn/setup/newClientCert.sh "$KEY_NAME" "$SERVICE_IP"
check_error $? "create client certificate"
kubectl --namespace "default" exec -it "$POD_NAME" cat "/etc/openvpn/certs/pki/$KEY_NAME.ovpn" > "/tmp/${KEY_NAME}.ovpn"
check_error $? "extract client certificate"

echo "management 127.0.0.1 ${VPN_STATUS_PORT}" >> /tmp/${KEY_NAME}.ovpn
echo "management-log-cache 10000" >> /tmp/${KEY_NAME}.ovpn
# The helm chart unconditionally creates this route, which is wrong. Get rid of it.
echo 'pull-filter ignore "route 10.0.0.0"' >> /tmp/${KEY_NAME}.ovpn
echo 'pull-filter ignore redirect-gateway' >> /tmp/${KEY_NAME}.ovpn

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
logprotoupper=$(python -c "$PREFIX print api.cldshow('${cldid}', 'logstore')['protocol'].upper()")
logport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'logstore')['port'].lower()")
metricport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'metricstore')['port'].lower()")
fileport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'filestore')['port'].lower()")
apiport=$(python -c "$PREFIX print api.cldshow('${cldid}', 'api_defaults')['port'].lower()")
redisport=6379 # command isn't working yet

cat << EOF > /tmp/cbportforward.sh
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

chmod +x /tmp/cbportforward.sh

kubectl cp /tmp/cbportforward.sh default/${POD_NAME}:/etc/openvpn/certs/portforward.sh
kubectl exec -it ${POD_NAME} /bin/chmod +x /etc/openvpn/certs/portforward.sh

check_error $? "setup IPtables script executable"

kubectl exec -it ${POD_NAME} /etc/openvpn/certs/portforward.sh

check_error $? "setup IPtables rules"
check_ready

cat << EOF > /tmp/cbvpnservice.yaml
apiVersion: v1
kind: Service
metadata:
  name: openvpn-proxy 
spec:
#  type: NodePort
  ports:
  - port: ${redisport} 
    protocol: TCP
    name: redis
    targetPort: ${redisport} 
  - port: 22 
    protocol: TCP
    name: ssh 
    targetPort: 22 
  - port: ${metricport} 
    protocol: TCP
    name: mongodb 
    targetPort: ${metricport} 
  - port: ${logport} 
    protocol: ${logprotoupper} 
    name: rsyslog 
    targetPort: ${logport} 
  - port: ${apiport} 
    protocol: TCP
    name: api 
    targetPort: ${apiport} 
  - port: ${fileport} 
    protocol: TCP
    name: rsync 
    targetPort: ${fileport} 
  selector:
    app: openvpn 
EOF

kubectl create -f /tmp/cbvpnservice.yaml

check_error $? "setup openvpn proxy"
check_ready

while true ; do
	INTERNAL_SERVICE_IP=$(kubectl get svc --namespace "default" "openvpn-proxy" -o json | jq -r .spec.clusterIP)
	code=$?
	if [ $code -eq 0 ] && [ x"${INTERNAL_SERVICE_IP}" != x ] ; then
		break
	fi
	echo "Openvpn Proxy IP not yet ready ..."
	sleep 10
	check_ready
done

echo "Openvpn Proxy IP: ${INTERNAL_SERVICE_IP}"

python -c "$PREFIX api.cldalter('${cldid}', 'vpn', 'server_bootstrap', '${INTERNAL_SERVICE_IP}')"

while true ; do
	RELEASE=$(helm list | grep registry | sed "s/\t/ /g" | cut -d " " -f 1)
	if [ $? -eq 0 ] && [ x"$RELEASE" != x ]; then
		break
	fi
	echo "Registry not ready yet..."
	check_ready
done

while true ; do
	PODNAME=$(kubectl get pods --namespace default -l "app=docker-registry,release=${RELEASE}" -o jsonpath="{.items[0].metadata.name}")
	if [ $? -eq 0 ] && [ x"$PODNAME" != x ]; then
		break
	fi
	echo "Pod name not yet ready... "
	check_ready
done
	
SERVICE_NAME=$(kubectl get svc --namespace "default" -l "app=docker-registry,release=${RELEASE}" -o jsonpath='{ .items[0].metadata.name }')
echo "Registry Service name: ${SERVICE_NAME}"
check_error $? "get registry service name"
check_ready

while true ; do
	REGISTRYIP=$(kubectl get svc --namespace "default" "$SERVICE_NAME" -o json | jq -r .spec.clusterIP)
	code=$?
	if [ $code -eq 0 ] && [ x"$REGISTRYIP" != x ] ; then
		break
	fi
	echo "Docker Service IP not yet ready ..."
	sleep 10
	check_ready
done


PRIVATE_REGISTRY="${REGISTRYIP}:${REGISTRYPORT}"
python -c "$PREFIX api.cldalter('${cldid}', 'vm_defaults', 'image_prefix', '${PRIVATE_REGISTRY}/ubuntu_')"

echo "Registry located at: ${PRIVATE_REGISTRY}"

NODES=$(kubectl get nodes | grep Ready | wc -l)
SSHKEY="$(cat ~/.ssh/id_rsa.pub)"
PRIVKEY="$(cat ~/.ssh/id_rsa | sed ':a;N;$!ba;s/\n/\\\\n/g')"

echo "Performing backdoor reconfiguration on ${NODES} nodes... "

cat << EOF > /tmp/cbbackdoor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backdoor
  labels:
    app: foo
spec:
  replicas: ${NODES} 
  selector:
    matchLabels:
      app: foo
  template:
    metadata:
      labels:
       app: foo
    spec:
      volumes:
      - name: data
        hostPath:
          path: /
      affinity:
              podAntiAffinity:
                requiredDuringSchedulingIgnoredDuringExecution:
                  - labelSelector:
                      matchExpressions:
                        - key: "app"
                          operator: In
                          values:
                          - foo 
                    topologyKey: "kubernetes.io/hostname"
      containers:
      - name: entrypoint
        image: ubuntu:18.04
        command: ["/bin/bash"]
        args: ["-c", "/bin/echo -e \"\$PRIVKEY\" > id_rsa; /bin/chmod go-rx id_rsa; /usr/bin/apt update; /usr/bin/apt install -y iproute2 ssh; dest=\$(ip route | grep default | cut -d ' ' -f 3); /bin/echo \$SSHKEY >> /tmp/slash/root/.ssh/authorized_keys; /bin/echo '{ \"insecure-registries\" : [\"${PRIVATE_REGISTRY}\"] }' > /tmp/slash/etc/docker/daemon.json; sed -ie 's/\\\\:0\\\\:0/\\\\:99999\\\\:0/g' /tmp/slash/etc/shadow; /usr/bin/ssh -i id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@\$dest \"service docker restart\"; /bin/sleep infinity"]
        env:
        - name: SSHKEY
          value: "${SSHKEY}"
        - name: PRIVKEY
          value: "${PRIVKEY}"
        volumeMounts:
        - name: data
          mountPath: /tmp/slash
          readOnly: false
        securityContext:
          privileged: true
EOF


cat /tmp/cbbackdoor.yaml | kubectl create -f -
check_error $? "install backdoor"

check_ready

kubectl get pods

#echo "Restarting docker on all nodes..."
#
#for node in $(kubectl get nodes | grep Ready | cut -d " " -f 1) ; do
#	nodeip=$(kubectl describe node ${node} | grep ExternalIP | sed "s/.* //g")
#	echo "Restarting on ${nodeip}"
#	ssh -o ConnectTimeout=120 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@${nodeip} "service docker restart"
#	check_error $? "docker restart failed"
#done

echo "Backdoor installed, waiting for completion..."

while true ; do
	completed=$(kubectl get pods | grep backdoor | sed "s/ \+/ /g" | cut -d " " -f 4 | grep -v 0 | wc -l)
	echo "Completed: $completed ..."
	if [ $completed == ${NODES} ] ; then
		echo "Backdoor complete."
		break
	fi
done

kubectl delete --wait deployment backdoor

rm /tmp/cbbackdoor.yaml
rm /tmp/cbportforward.sh 
rm /tmp/cbhelmregistry.yaml
rm /tmp/cbvpnservice.yaml
rm /tmp/cbhelm_openvpn_values.yaml 

echo "Done."
