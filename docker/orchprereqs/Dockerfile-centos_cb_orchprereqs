FROM REPLACE_BASE_VANILLA_CENTOS
RUN yum -y update
RUN yum -y install openssh-server 
RUN yum -y install passwd 
RUN yum -y install sudo 
RUN yum -y install rsync

RUN useradd -ms /bin/bash REPLACE_USERNAME
RUN echo "REPLACE_USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

#ENV OBJECTSTORE_PORT=10000
#ENV METRICSTORE_PORT=20000
#ENV LOGSTORE_PORT=30000
#ENV FILESTORE_PORT=40000
#ENV GUI_PORT=50000
#ENV API_PORT=60000
#ENV VPN_PORT=65000

#EXPOSE $OBJECTSTORE_PORT
#EXPOSE $METRICSTORE_PORT
#EXPOSE $LOGSTORE_PORT
#EXPOSE $FILESTORE_PORT
#EXPOSE $GUI_PORT
#EXPOSE $API_PORT
#EXPOSE $VPN_PORT

# sudo-install-man
RUN yum install -y sudo
# echo "USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers; sed -i s/"Defaults requiretty"/"#Defaults requiretty"/g /etc/sudoers
# sudo-install-man

# ifconfig-install-sl
RUN yum -y update; yum clean all
RUN yum install -y net-tools
RUN ln -s /sbin/ifconfig /usr/local/bin/ifconfig
# ifconfig-install-sl

# ip-install-sl
RUN ln -s /sbin/ip /usr/local/bin/ip
# ip-install-sl

# pkill-install-pm
RUN yum install -y psmisc coreutils
# pkill-install-pm

# which-install-pm
RUN /bin/true
# which-install-pm

# ntp-install-pm
RUN yum install -y ntp ntpdate 
# ntp-install-pm

# git-install-pm
RUN yum install -y git
# git-install-pm

# wget-install-pm
RUN yum install -y wget
# wget-install-pm

# pip-install-pm
RUN yum install -y epel-release
RUN yum install -y python-pip
# pip-install-pm

# gcc-install-pm
RUN yum install -y gcc gcc-c++ 
# gcc-install-pm

# make-install-pm
RUN yum install -y make
# make-install-pm

# bc-install-pm
RUN yum install -y bc
# bc-install-pm

# sshpass-install-pm
RUN yum install -y sshpass
# sshpass-install-pm

# curl-install-pm
RUN yum install -y curl
# curl-install-pm

# screen-install-pm
RUN yum install -y screen
# screen-install-pm

# rsync-install-pm
RUN yum install -y rsync
# rsync-install-pm

# ncftp-install-pm
RUN yum install -y ncftp
# ncftp-install-pm

# lftp-install-pm
RUN yum install -y lftp iputils-ping
# lftp-install-pm

# haproxy-install-pm
RUN yum install -y haproxy
# service_stop_disable haproxy
# haproxy-install-pm

RUN yum install -y vim

# netcat-install-man
RUN yum install -y nmap-ncat netcat-openbsd
RUN cp /bin/nc /usr/local/bin/netcat
# netcat-install-man

# nmap-install-pm
RUN yum install -y nmap
# nmap-install-pm

# openvpn-install-pm
RUN yum install -y openvpn 
RUN ln -s /usr/sbin/openvpn /usr/local/bin/openvpn
# openvpn-install-pm

# gmond-install-pm
RUN yum install -y ganglia ganglia-gmond.REPLACE_ARCH1
RUN ln -s /usr/sbin/gmond /usr/local/bin/gmond
# service_stop_disable gmond
# gmond-install-pm

# rsyslog-install-pm
RUN yum install -y rsyslog
RUN ln -s /sbin/rsyslogd /usr/local/bin/rsyslogd
# rsyslog-install-pm

# apache-install-pm
RUN yum -y install httpd; /bin/true
# apache-install-pm

# redis-install-pm
RUN yum install -y redis
RUN sed -i "s/.*bind 127.0.0.1/bind 0.0.0.0/" /etc/redis.conf
# redis-install-pm
RUN sed -i "s/.*port.*/port $OBJECTSTORE_PORT/" /etc/redis.conf

# mongodb-install-pm
RUN yum install -y mongodb mongodb-server
RUN sed -i "s/.*bind_ip.*/bind_ip=0.0.0.0/" /etc/mongod.conf
# mongodb-install-pm
RUN sed -i "s/.*port.*/port = $METRICSTORE_PORT/" /etc/mongod.conf

# pylibvirt-install-pm
RUN yum install -y libvirt-python
# pylibvirt-install-pm

# pypureomapi-install-pip
RUN pip install --upgrade pypureomapi
# pypureomapi-install-pip

# python-devel-install-pm
RUN yum install -y python-devel libffi-devel openssl-devel libxml2-devel
# python-devel-install-pm 

# python-prettytable-install-pip
RUN pip install --upgrade docutils prettytable
# python-prettytable-install-pip

# python-daemon-install-pip
RUN pip install --upgrade python-daemon
# python-daemon-install-pip

# python-twisted-install-pip
RUN pip install --upgrade twisted service_identity
# python-twisted-install-pip

# python-beaker-install-pip
RUN pip install --upgrade beaker
# python-beaker-install-pip

# python-webob-install-pip
RUN pip install --upgrade webob
# python-webob-install-pip

# pyredis-install-pip
RUN pip install redis==2.10.6
# pyredis-install-pip

# pymongo-install-pip
RUN pip install --upgrade mongo
# pymongo-install-pip

# pssh-install-pm
RUN yum install -y pssh
# pssh-install-pm

# docutils-install-pip
RUN pip install --upgrade docutils
# docutils-install-pip

# python-setuptools-install-pip
RUN pip install --upgrade setuptools
# python-setuptools-install-pip 

# markup-install-pip
RUN pip install --upgrade markup
# markup-install-pip 

# pyyaml-install-pip
RUN pip install --upgrade pyyaml
# pyyaml-install-pip 

# ruamelyaml-install-pip
RUN pip install --upgrade ruamel.yaml
# ruamelyaml-install-pip

# urllib3-install-pip
RUN pip install --upgrade  urllib3[secure]
# urllib3-install-pip

# jq-install-pm
RUN yum install -y jq
# jq-install-pm

# httplib2shim-install-pip
RUN pip install --upgrade httplib2shim
# httplib2shim-install-pip

# iptables-install-pm
RUN yum install -y iptables
# service_stop_disable iptables
# iptables-install-pm

# sshd-install-pm
RUN yum -y install openssh-server
RUN sudo bash -c "echo 'UseDNS no' >> /etc/ssh/sshd_config"
RUN sed -i 's/.*UseDNS.*/UseDNS no/g' /etc/ssh/sshd_config
RUN sed -i 's/.*GSSAPIAuthentication.*/GSSAPIAuthentication no/g' /etc/ssh/sshd_config
# sshd-install-pm

# novaclient-install-pip
RUN pip install --upgrade pbr
RUN pip install --upgrade netifaces
RUN pip install --upgrade python-novaclient==9.1.1
# novaclient-install-pip

# neutronclient-install-pip
RUN pip install --upgrade python-neutronclient==6.5.0
# neutronclient-install-pip

# cinderclient-install-pip
RUN pip install --upgrade python-cinderclient==3.2.0
# cinderclient-install-pip

# glanceclient-install-pip
RUN pip install --upgrade python-glanceclient==2.8.0
# glanceclient-install-pip

# softlayer-install-pip
RUN pip install --upgrade softlayer
# softlayer-install-pip

# boto-install-pip
RUN pip install --upgrade boto
# boto-install-pip

# libcloud-install-pip
RUN pip install --upgrade apache-libcloud
# libcloud-install-pip

# pygce-install-pip
RUN pip install --upgrade gcloud google-api-python-client
# pygce-install-pip

# pydocker-install-pip
RUN pip install --upgrade docker-py==1.8.1 wget
# pydocker-install-pip

# pylxd-install-pip
RUN pip install --upgrade pylxd
# pylxd-install-pip

# pykube-install-pip
RUN pip install --upgrade pykube
# pykube-install-pip

# R-install-pm
RUN yum install -y R
# R-install-pm

# rrdtool-install-pm
RUN yum install -y rrdtool
# rrdtool-install-pm

# python-rrdtool-install-pm
RUN yum install -y rrdtool-python
# python-rrdtool-install-pm

# python-dateutil-install-pip
RUN pip install --upgrade python-dateutil
# python-dateutil-install-pip

# python-pillow-install-pip
RUN pip install --upgrade Pillow
# python-pillow-install-pip

# python-jsonschema-install-pip
RUN pip install --upgrade jsonschema
# python-jsonschema-install-pip

USER REPLACE_USERNAME
# gcloud-install-man
ENV CLOUDSDK_CORE_DISABLE_PROMPTS=1
RUN curl https://sdk.cloud.google.com | bash
RUN sudo ln -s /home/REPLACE_USERNAME/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud
# gcloud-install-man

WORKDIR /home/REPLACE_USERNAME/

# gmetad-python-install-git
RUN mkdir -p /home/REPLACE_USERNAME/cbtool/3rd_party/workload
RUN cp____-f____/home/REPLACE_USERNAME/cbtool/util/manually_download_files.txt____/home/REPLACE_USERNAME/cbtool/3rd_party/workload; /bin/true
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/monitor-core.git
# gmetad-python-install-git

# pyhtml-install-git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/HTML.py.git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party/HTML.py
RUN sudo python setup.py install
# pyhtml-install-git

# bootstrap-install-git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/bootstrap.git
# bootstrap-install-git

# bootstrap-wizard-install-git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/Bootstrap-Wizard.git
# bootstrap-wizard-install-git

# streamprox-install-git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/StreamProx.git
# streamprox-install-git

# d3-install-git
WORKDIR /home/REPLACE_USERNAME/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/d3.git
# d3-install-git

WORKDIR /home/REPLACE_USERNAME
RUN mkdir -p /home/REPLACE_USERNAME/cbtool/lib/clouds/
RUN mkdir -p /home/REPLACE_USERNAME/cbtool/configs/templates/
COPY cloud_definitions.txt /home/REPLACE_USERNAME/cbtool/configs/
RUN sudo chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
RUN mv /home/REPLACE_USERNAME/cbtool /home/REPLACE_USERNAME/cbtooltmp
