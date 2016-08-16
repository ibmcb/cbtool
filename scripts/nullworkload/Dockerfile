FROM phusion/baseimage:latest 

ENV DEBIAN_FRONTEND=noninteractive
ENV CB_SSH_PUB_KEY NA

RUN rm -f /etc/service/sshd/down

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

RUN apt-get update
RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash cbuser

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
sshpass \
curl \
screen \
rsync \
ncftp \
lftp

RUN apt-get install -y \
netcat-openbsd
RUN cp /bin/nc /usr/local/bin/netcat

RUN apt-get install -y \
nmap \
openvpn 
RUN ln -s /usr/sbin/openvpn /usr/local/bin/openvpn

RUN apt-get install -y \
ganglia-monitor
RUN ln -s /usr/sbin/gmond /usr/local/bin/gmond

RUN apt-get install -y \
apache2 \
redis-server
RUN sed -i "s/.*bind 127.0.0.1/bind 0.0.0.0/" /etc/redis/redis.conf

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
pymongo

RUN apt-get install -y \
pssh

RUN pip install --upgrade \
docutils \
setuptools \
markup \
pyyaml

RUN mkdir -p /etc/my_init.d
ADD inject_pubkey.sh /etc/my_init.d/inject_pubkey.sh

RUN ssh-keygen -q -t rsa -N '' -f /root/.ssh/id_rsa
RUN touch /root/.ssh/authorized_keys
RUN chmod 644 /root/.ssh/authorized_keys

RUN rsync -az /root/.ssh/ /home/cbuser/.ssh/
RUN chown -R cbuser:cbuser /home/cbuser/
RUN chmod 755 /home/cbuser/.ssh

USER cbuser
WORKDIR /home/cbuser/
RUN git clone https://github.com/ibmcb/cbtool.git
RUN mkdir /home/cbuser/cbtool/3rd_party
WORKDIR /home/cbuser/cbtool/3rd_party
RUN git clone https://github.com/ibmcb/monitor-core.git
RUN git clone https://github.com/ibmcb/HTML.py.git
WORKDIR /home/cbuser/cbtool/3rd_party/HTML.py
RUN sudo python setup.py install
WORKDIR /home/cbuser
RUN mv cbtool cloudbench
USER root
