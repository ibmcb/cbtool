FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN useradd -ms /bin/bash cbuser

ENV OBJECTSTORE_PORT=10000
ENV METRICSTORE_PORT=20000
ENV LOGSTORE_PORT=30000
ENV FILESTORE_PORT=40000
ENV GUI_PORT=50000
ENV API_PORT=60000
ENV VPN_PORT=65000

EXPOSE $OBJECTSTORE_PORT
EXPOSE $METRICSTORE_PORT
EXPOSE $LOGSTORE_PORT
EXPOSE $FILESTORE_PORT
EXPOSE $GUI_PORT
EXPOSE $API_PORT
EXPOSE $VPN_PORT

RUN ln -s /sbin/ifconfig /usr/local/bin/ifconfig
RUN ln -s /sbin/ip /usr/local/bin/ip

RUN apt-get install -y \
psmisc \
ntp \
ntpdate \
git \
wget \
python-pip \
gcc \
make \
emacs \
sshpass \
curl \
vim \
screen \
rsync \
ncftp \
lftp \
libffi-dev \
libssl-dev \
python-webob \
python-beaker \
python-libvirt \
netcat-openbsd \
net-tools
RUN cp /bin/nc /usr/local/bin/netcat

RUN apt-get install -y \
nmap \
openvpn 
RUN ln -s /usr/sbin/openvpn /usr/local/bin/openvpn

RUN apt-get install -y \
ganglia-monitor
RUN ln -s /usr/sbin/gmond /usr/local/bin/gmond

RUN apt-get install -y \
rsyslog
RUN ln -s /usr/sbin/rsyslogd /usr/local/bin/rsyslogd

RUN mkdir -p /var/log/cloudbench
RUN sed -i -e "s/#\$ModLoad imudp/\$ModLoad imudp/g" /etc/rsyslog.conf
RUN sed -i -e "s/#\$UDPServerRun.*/\$UDPServerRun $METRIC_STORE_PORT/g" /etc/rsyslog.conf

RUN apt-get install -y \
apache2 \
redis-server
RUN sed -i "s/.*bind 127.0.0.1/bind 0.0.0.0/" /etc/redis/redis.conf
RUN sed -i "s/.*port.*/port $OBJECTSTORE_PORT/" /etc/redis/redis.conf

RUN apt-get install -y \
mongodb
RUN sed -i "s/.*bind_ip.*/bind_ip=0.0.0.0/" /etc/mongodb.conf
RUN sed -i "s/.*port.*/port = $METRICSTORE_PORT/" /etc/redis/redis.conf

RUN apt-get install -y \
sudo
RUN echo "cbuser  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN apt-get install -y \
python-dev \
python-setuptools \
python-prettytable

RUN pip install --upgrade \
prettytable \
python-daemon \
twisted \
redis \
pymongo \
pypureomapi \
pbr \
netifaces \
python-novaclient \
python-neutronclient \
softlayer \
apache-libcloud \
boto \
gcloud \
google-api-python-client

RUN apt-get install -y \
r-base-core \
pssh

RUN pip install --upgrade \
docutils \
setuptools \
markup \
pyyaml \
ruamel.yaml

USER cbuser
ENV CLOUDSDK_CORE_DISABLE_PROMPTS=1
RUN curl https://sdk.cloud.google.com | bash
WORKDIR /home/cbuser/
RUN git clone https://github.com/ibmcb/cbtool.git
RUN mkdir /home/cbuser/cbtool/3rd_party
WORKDIR /home/cbuser/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/monitor-core.git
RUN git clone https://github.com/ibmcb/bootstrap.git
RUN git clone https://github.com/ibmcb/Bootstrap-Wizard.git
RUN git clone https://github.com/ibmcb/StreamProx.git
RUN git clone https://github.com/ibmcb/d3.git
RUN git clone https://github.com/ibmcb/HTML.py.git
WORKDIR /home/cbuser/cbtool/3rd_party/HTML.py
RUN sudo python setup.py install
WORKDIR /home/cbuser/cbtool/configs
RUN cp cloud_definitions.txt cbuser_cloud_definitions.txt

RUN echo "\n[OBJECTSTORE]\nPORT = $OBJECTSTORE_PORT\nUSAGE = private" >> cbuser_cloud_definitions.txt
RUN echo "\n[METRICSTORE]\nPORT = $METRICSTORE_PORT\nUSAGE = private" >> cbuser_cloud_definitions.txt
RUN echo "\n[LOGSTORE]\nPORT = $LOGSTORE_PORT\nUSAGE = private" >> cbuser_cloud_definitions.txt
RUN echo "\n[FILESTORE]\nPORT = $FILESTORE_PORT\nUSAGE = private" >> cbuser_cloud_definitions.txt
RUN echo "\n[API_DEFAULTS]\nPORT = $API_PORT\n" >> cbuser_cloud_definitions.txt
RUN echo "\n[GUI_DEFAULTS]\nPORT = $GUI_PORT\n" >> cbuser_cloud_definitions.txt
RUN echo "\n[VPN]\nSERVER_PORT = $VPN_PORT\n" >> cbuser_cloud_definitions.txt
