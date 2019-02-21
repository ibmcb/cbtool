FROM REPLACE_BASE_VANILLA_UBUNTU

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN useradd -ms /bin/bash REPLACE_USERNAME

# sudo-install-man
RUN apt-get install -y sudo
# echo "USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers; sed -i s/"Defaults requiretty"/"#Defaults requiretty"/g /etc/sudoers
# sudo-install-man

# ifconfig-install-sl
RUN apt-get update
RUN apt-get install -y net-tools
RUN ln -s /sbin/ifconfig /usr/local/bin/ifconfig
# ifconfig-install-sl

# ip-install-sl
RUN ln -s /sbin/ip /usr/local/bin/ip
# ip-install-sl

# pkill-install-pm
RUN apt-get install -y psmisc coreutils
# pkill-install-pm

# which-install-pm
RUN /bin/true
# which-install-pm

# ntp-install-pm
RUN apt-get install -y ntp ntpdate 
# ntp-install-pm

# git-install-pm
RUN apt-get install -y git bc
# git-install-pm

# wget-install-pm
RUN apt-get install -y wget
# wget-install-pm

# pip-install-pm
RUN apt-get update
RUN apt-get install -y python-pip
# pip-install-pm

# gcc-install-pm
RUN apt-get install -y gcc
# gcc-install-pm

# make-install-pm
RUN apt-get install -y make
# make-install-pm

# bc-install-pm
RUN apt-get install -y bc
# bc-install-pm

# sshpass-install-pm
RUN apt-get install -y sshpass
# sshpass-install-pm

# curl-install-pm
RUN apt-get install -y curl
# curl-install-pm

# screen-install-pm
RUN apt-get install -y screen
# screen-install-pm

# rsync-install-pm
RUN apt-get install -y rsync
# rsync-install-pm

# ncftp-install-pm
RUN apt-get install -y ncftp
# ncftp-install-pm

# lftp-install-pm
RUN apt-get install -y lftp iputils-ping
# lftp-install-pm

# haproxy-install-pm
RUN apt-get install -y haproxy
# service_stop_disable haproxy
# haproxy-install-pm

RUN apt-get install -y vim

# netcat-install-man
RUN apt-get install -y netcat-openbsd
RUN cp /bin/nc /usr/local/bin/netcat
# netcat-install-man

# nmap-install-pm
RUN apt-get install -y nmap
# nmap-install-pm

# openvpn-install-pm
RUN apt-get install -y openvpn 
RUN ln -s /usr/sbin/openvpn /usr/local/bin/openvpn
# openvpn-install-pm

# gmond-install-pm
RUN apt-get install -y ganglia-monitor
RUN ln -s /usr/sbin/gmond /usr/local/bin/gmond
# service_stop_disable ganglia-monitor
# gmond-install-pm

# rsyslog-install-pm
RUN apt-get install -y rsyslog
RUN ln -s /usr/sbin/rsyslogd /usr/local/bin/rsyslogd
RUN mkdir -p /var/log/cloudbench
# rsyslog-install-pm

# rsyslog-filter-pm
RUN mkdir -p /var/log/cloudbench
RUN sed -i -e "s/#\$ModLoad imudp/\$ModLoad imudp/g" /etc/rsyslog.conf; sed -i -e 's^#module(load="imudp")^module(load="imudp")^g' /etc/rsyslog.conf
RUN sed -i  "s/#\$UDPServerRun.*/\$UDPServerRun $METRIC_STORE_PORT/g" /etc/rsyslog.conf
RUN bash -c "echo -e \"local5.*  \t\t\t\t /var/log/cloudbench/remote.log\" >> /etc/rsyslog.conf"
RUN bash -c "echo -e \"local6.* \t\t\t\t /var/log/cloudbench/local.log\" >> /etc/rsyslog.conf"
#service_restart_enable rsyslog
# rsyslog-filter-pm

# apache-install-pm
RUN apt-get install -y apache2
# apache-install-pm

# redis-install-pm
RUN apt-get install -y redis-server
RUN sed -i "s/.*bind 127.0.0.1/bind 0.0.0.0/" /etc/redis/redis.conf
# redis-install-pm
RUN sed -i "s/.*port.*/port $OBJECTSTORE_PORT/" /etc/redis/redis.conf

# mongodb-install-pm
RUN apt-get install -y mongodb
RUN sed -i "s/.*bind_ip.*/bind_ip=0.0.0.0/" /etc/mongodb.conf
# mongodb-install-pm
RUN sed -i "s/.*port.*/port = $METRICSTORE_PORT/" /etc/mongodb.conf

RUN apt-get install -y sudo
RUN echo "REPLACE_USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

# pylibvirt-install-pm
RUN apt-get install -y python-libvirt
# pylibvirt-install-pm

# pypureomapi-install-pip
RUN pip install --upgrade pypureomapi
# pypureomapi-install-pip

# python-devel-install-pm
RUN apt-get install -y python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev
# python-devel-install-pm 

# python-prettytable-install-pip
RUN pip install --upgrade prettytable docutils
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
RUN apt-get install -y pssh
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
RUN apt-get install -y jq
# jq-install-pm

# httplib2shim-install-pip
RUN pip install --upgrade httplib2shim
# httplib2shim-install-pip

# iptables-install-pm
RUN apt-get install -y iptables
# service_stop_disable iptables
# iptables-install-pm

# sshd-install-pm
RUN apt-get install -y openssh-server
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
RUN apt-get install -y r-base-core
# R-install-pm

# rrdtool-install-pm
RUN apt-get install -y rrdtool
# rrdtool-install-pm

# python-rrdtool-install-pm
RUN apt-get install -y python-rrdtool
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

ADD get_my_ips.sh /usr/local/bin/getmyips
ADD gucn.sh /usr/local/bin/gucn
RUN chmod +x /usr/local/bin/getmyips; chmod +x /usr/local/bin/gucn

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
