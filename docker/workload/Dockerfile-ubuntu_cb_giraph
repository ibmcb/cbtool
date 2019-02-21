FROM REPLACE_NULLWORKLOAD_UBUNTU

# java-install-pm
RUN apt-get update; mkdir /home/REPLACE_USERNAME/openjdk7/ ; wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN cd /home/REPLACE_USERNAME/openjdk7/; dpkg -i *.deb; sudo apt --fix-broken -y install
# java-install-pm

# hadoop-install-man
RUN sudo wget -N -q -P /home/REPLACE_USERNAME https://archive.apache.org/dist/hadoop/common/hadoop-1.2.1/hadoop-1.2.1.tar.gz
#RUN wget -N -q -P /home/REPLACE_USERNAME https://archive.apache.org/dist/hadoop/common/hadoop-2.3.0/hadoop-2.3.0.tar.gz
RUN /bin/true; cd /home/REPLACE_USERNAME; sudo tar -xzf /home/REPLACE_USERNAME/hadoop*.gz
# hadoop-install-man

# maven-install-pm
RUN apt-get install -y maven ant
# maven-install-pm

# giraph-install-git
RUN sudo chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/apache/giraph.git
RUN /bin/true; export JAVA_HOME=/usr/lib/jvm/$(ls -t /usr/lib/jvm | grep java | sed '/^$/d' | sort -r | head -n 1)/jre; cd /home/REPLACE_USERNAME/giraph/; git checkout release-1.0.0; mvn package -Dhttps.protocols=TLSv1,TLSv1.1,TLSv1.2,SSLv3 -Phadoop_1.0 -DskipTests; /bin/true
#RUN /bin/true; cd /home/REPLACE_USERNAME/giraph/; git checkout release-1.1; mvn package -Phadoop_yarn -Dhadoop.version=2.3.0 -DskipTests
# giraph-install-git

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
