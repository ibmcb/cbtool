FROM phusion/baseimage:latest 

ENV DEBIAN_FRONTEND=noninteractive
ENV CB_SSH_PUB_KEY NA
ENV CB_LOGIN NA

RUN rm -f /etc/service/sshd/down

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

RUN apt-get update
RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash ubuntu

RUN ln -s /sbin/ifconfig /usr/local/bin/ifconfig
RUN ln -s /sbin/ip /usr/local/bin/ip

RUN mkdir -p /etc/my_init.d
ADD inject_pubkey.sh /etc/my_init.d/inject_pubkey.sh

RUN ssh-keygen -q -t rsa -N '' -f /root/.ssh/id_rsa
RUN touch /root/.ssh/authorized_keys
RUN chmod 644 /root/.ssh/authorized_keys
