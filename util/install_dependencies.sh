#!/usr/bin/env bash

#/*****************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*****************************************************************************

DISTRO=`lsb_release -a 2>& 1| grep Description | cut -d ':' -f 2 | sed -e 's/^[ \t]*//'`

IS_UBUNTU=`echo ${DISTRO} | grep -c Ubuntu`
IS_RHEL=`echo ${DISTOR} | grep -c "Red Hat Enterprise Linux"`

if [ ${IS_UBUNTU} -eq 1 ]; then
	echo "##################### Installing Ubuntu dependencies..."
	sudo apt-get update
	sudo apt-get -y install git make gcc python-setuptools python-dev python-daemon python-twisted-web python-webob python-beaker netcat-openbsd screen ganglia-monitor r-base-core python-libvirt libsnmp-python ntp
	echo "##################### Done"
fi

if [ ${IS_RHEL} -eq 1 ]; then
	echo "##################### Adding EPEL as an extra repository for RHEL..."
	sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm
	echo "##################### Installing RHEL dependencies..."
	sudo yum -y install  git make gcc python-setuptools python-devel python-daemon python-twisted-web python-webob python-beaker nc screen ganglia-gmond R ganglia-gmond-python libvirt-python net-snmp-python ntp
	echo "##################### Done"
fi

echo "##################### Installing additional python dependencies using easy_install..."
sudo easy_install setuptools-git
sudo easy_install redis pymongo boto python-novaclient
echo "##################### Done"
	
THIRD_PARTY_DIR=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/../3rd_party
echo "##################### Installing distribution-agnostic packages..."
mkdir -p ${THIRD_PARTY_DIR}
cd ${THIRD_PARTY_DIR}; git clone https://github.com/ibmcb/bootstrap.git; 
#cd ${THIRD_PARTY_DIR}; git clone https://github.com/boto/boto.git;cd boto; sudo python setup.py install; 
cd ${THIRD_PARTY_DIR}; git clone https://github.com/ibmcb/d3.git;  
cd ${THIRD_PARTY_DIR}; git clone https://github.com/apache/libcloud.git;cd libcloud; sudo python setup.py install;
cd ${THIRD_PARTY_DIR}; wget http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-2.2.2.tgz; tar -zxf mongodb-linux-*.tgz; cd mongodb-linux-*; sudo cp bin/* /usr/local/bin; 
cd ${THIRD_PARTY_DIR}; git clone https://github.com/antirez/redis.git; cd redis; git checkout 2.6; sudo make install
cd ${THIRD_PARTY_DIR}; git clone https://github.com/ibmcb/monitor-core.git
#cd ${THIRD_PARTY_DIR}; git clone https://github.com/openstack/python-novaclient.git;cd python-novaclient; sudo python setup.py install;
#cd ${THIRD_PARTY_DIR}; git clone https://github.com/mongodb/mongo-python-driver.git;cd mongo-python-driver; sudo python setup.py install; 
cd ${THIRD_PARTY_DIR}; wget http://pypureomapi.googlecode.com/files/pypureomapi-0.3.tar.gz; tar -xzvf pypureomapi-0.3.tar.gz; cd pypureomapi-0.3; sudo python setup.py install;
#cd ${THIRD_PARTY_DIR}; git clone https://github.com/andymccurdy/redis-py.git; cd redis-py; sudo python setup.py install; 
cd ${THIRD_PARTY_DIR}; git clone https://github.com/ibmcb/Bootstrap-Wizard.git
echo "##################### Done"