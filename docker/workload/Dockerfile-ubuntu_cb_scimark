FROM REPLACE_NULLWORKLOAD_UBUNTU

# java-install-pm
RUN apt-get update; mkdir /home/REPLACE_USERNAME/openjdk7/ ; wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN cd /home/REPLACE_USERNAME/openjdk7/; dpkg -i *.deb; sudo apt --fix-broken -y install
# java-install-pm

# scimark-install-man
RUN wget -N -v -P /home/REPLACE_USERNAME http://math.nist.gov/scimark2/scimark2lib.zip
RUN apt-get install -y unzip; cd /home/REPLACE_USERNAME; unzip -qu /home/REPLACE_USERNAME/scimark2lib.zip
# scimark-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
