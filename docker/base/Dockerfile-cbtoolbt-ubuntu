FROM REPLACE_BASE_VANILLA_UBUNTU

ENV DEBIAN_FRONTEND=noninteractive
ENV CB_SSH_PUB_KEY=NA
ENV CB_LOGIN=NA

RUN apt-get update
RUN apt-get install -y sudo rsync python2.7
RUN apt-get update
RUN apt-get install -y openssh-server
RUN ln -s /usr/bin/python2.7 /usr/bin/python; mkdir /var/run/sshd
RUN echo 'root:temp4now' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

RUN useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash ubuntu; useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash fedora; useradd -m -p "$1$1rCJhvTo$nIoKRh4zdGdnk0Dntsdnq/" -s /bin/bash REPLACE_USERNAME

RUN echo "ubuntu  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN echo "fedora  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN echo "REPLACE_USERNAME  ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

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