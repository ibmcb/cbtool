FROM REPLACE_NULLWORKLOAD_UBUNTU

# java-install-pm
RUN apt-get update; mkdir /home/REPLACE_USERNAME/openjdk7/ ; wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN cd /home/REPLACE_USERNAME/openjdk7/; dpkg -i *.deb; sudo apt --fix-broken -y install
# java-install-pm

# cassandra-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME http://launchpadlibrarian.net/109052632/python-support_1.0.15_all.deb; dpkg -i /home/REPLACE_USERNAME/python-support*.deb; sudo apt --fix-broken -y install
RUN wget -N -q -P /home/REPLACE_USERNAME http://dl.bintray.com/apache/cassandra/pool/main/c/cassandra/cassandra_2.1.1_all.deb
RUN dpkg -i /home/REPLACE_USERNAME/cassandra*.deb; sudo apt --fix-broken -y install
# cassandra-install-man

# cassandra-tools-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME http://dl.bintray.com/apache/cassandra/pool/main/c/cassandra/cassandra-tools_2.1.1_all.deb
RUN dpkg -i /home/REPLACE_USERNAME/cassandra-tools*.deb; sudo apt --fix-broken -y install
# service_stop_disable cassandra
# cassandra-tools-install-man

# mongo-install-pm
RUN apt-get install -y mongodb
RUN sed -i "s/.*bind_ip.*/bind_ip=0.0.0.0/" /etc/mongodb.conf
# service_stop_disable mongodb
# mongo-install-pm

# redis-install-pm
RUN apt-get install -y redis-server
RUN sed -i "s/.*bind.*/bind 0.0.0.0/" /etc/redis/redis.conf
# service_stop_disable redis-server
# redis-install-pm

# ycsb-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://github.com/brianfrankcooper/YCSB/releases/download/0.5.0/ycsb-0.5.0.tar.gz; cd /home/REPLACE_USERNAME; tar -xvzf ycsb-*.tar.gz; sudo rm ycsb*.gz; sudo mv ycsb-* YCSB
# ycsb-install-man
RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
