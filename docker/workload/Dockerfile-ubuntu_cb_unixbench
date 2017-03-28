FROM REPLACE_NULLWORKLOAD_UBUNTU

# gcc-install-pm
RUN apt-get update
RUN apt-get install -y gcc
# gcc-install-pm

# git-install-pm
RUN apt-get install -y git-all
# git-install-pm

# perl-install-pm
RUN apt-get install -y perl
# perl-install-pm

# unixbench-install-git
RUN mkdir -p /home/REPLACE_USERNAME/byte-unixbench; chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME/
RUN wget -N -q -P /home/REPLACE_USERNAME/byte-unixbench https://s3.amazonaws.com/cloudbench/software/UnixBench5.1.3.tgz
RUN cd /home/REPLACE_USERNAME/byte-unixbench; tar -zxf UnixBench5.1.3.tgz; rm UnixBench5.1.3.tgz
RUN cd /home/REPLACE_USERNAME/byte-unixbench/UnixBench; make all
# unixbench-install-git

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME