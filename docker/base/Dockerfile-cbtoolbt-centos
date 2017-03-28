FROM REPLACE_BASE_VANILLA_CENTOS

ENV DEBIAN_FRONTEND=noninteractive
ENV CB_SSH_PUB_KEY=NA
ENV CB_LOGIN=NA

RUN yum -y update; yum clean all
RUN yum -y install openssh-server 
RUN yum -y install passwd sudo rsync; yum clean all

RUN echo 'root:temp4now' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config; mkdir /var/run/sshd

RUN ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N '' 

# SSH login fix. Otherwise user is kicked off after login
#RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash ubuntu
RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash fedora
RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash REPLACE_USERNAME

RUN echo "ubuntu  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers; echo "fedora  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers; echo "REPLACE_USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN echo 'ubuntu:temp4now' | chpasswd
RUN echo 'fedora:temp4now' | chpasswd
RUN echo 'REPLACE_USERNAME:temp4now' | chpasswd

RUN ssh-keygen -q -t rsa -N '' -f /root/.ssh/id_rsa; touch /root/.ssh/authorized_keys; chmod 644 /root/.ssh/authorized_keys

RUN mkdir -p /home/ubuntu/.ssh/
RUN ssh-keygen -q -t rsa -N '' -f /home/ubuntu/.ssh/id_rsa
RUN touch /home/ubuntu/.ssh/authorized_keys; chmod 644 /home/ubuntu/.ssh/authorized_keys; chown -R ubuntu:ubuntu /home/ubuntu/

RUN mkdir -p /home/fedora/.ssh/
RUN ssh-keygen -q -t rsa -N '' -f /home/fedora/.ssh/id_rsa
RUN touch /home/fedora/.ssh/authorized_keys; chmod 644 /home/fedora/.ssh/authorized_keys; chown -R fedora:fedora /home/fedora/

RUN mkdir -p /home/REPLACE_USERNAME/.ssh/
RUN ssh-keygen -q -t rsa -N '' -f /home/REPLACE_USERNAME/.ssh/id_rsa
RUN touch /home/REPLACE_USERNAME/.ssh/authorized_keys; chmod 644 /home/REPLACE_USERNAME/.ssh/authorized_keys; chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME/

RUN mkdir -p /etc/my_init.d
ADD inject_pubkey_and_start_ssh.sh /etc/my_init.d/inject_pubkey_and_start_ssh.sh

CMD ["/etc/my_init.d/inject_pubkey_and_start_ssh.sh"]