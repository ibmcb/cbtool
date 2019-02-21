FROM REPLACE_NULLWORKLOAD_UBUNTU

# java-install-pm
RUN apt-get update; mkdir /home/REPLACE_USERNAME/openjdk7/ ; wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN cd /home/REPLACE_USERNAME/openjdk7/; dpkg -i *.deb; sudo apt --fix-broken -y install
# java-install-pm

# hadoop-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://archive.apache.org/dist/hadoop/common/hadoop-2.6.1/hadoop-2.6.1.tar.gz
RUN /bin/true; cd /home/REPLACE_USERNAME; sudo tar -xzf /home/REPLACE_USERNAME/hadoop*.gz
# hadoop-install-man

# hibench-install-git
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/ibmcb/HiBench.git; cd /home/REPLACE_USERNAME/HiBench; git checkout dev
# hibench-install-git

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
