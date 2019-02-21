FROM REPLACE_NULLWORKLOAD_UBUNTU

# java-install-pm
RUN apt-get update; mkdir /home/REPLACE_USERNAME/openjdk7/ ; wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN wget -N -q -P /home/REPLACE_USERNAME/openjdk7/ http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_REPLACE_ARCH3.deb
RUN cd /home/REPLACE_USERNAME/openjdk7/; dpkg -i *.deb; sudo apt --fix-broken -y install
# java-install-pm

# subversion-install-pm
RUN apt-get install -y xinetd subversion unzip
# subversion-install-pm

# maven-install-pm
RUN apt-get install -y maven ant
# maven-install-pm

# apache-install-pm
RUN apt-get install -y apache2
# service_stop_disable apache2
# apache-install-pm

# mysql-install-pm
RUN apt-get update; echo "mysql-server-5.7 mysql-server/root_password password temp4now" | sudo debconf-set-selections; echo "mysql-server-5.7 mysql-server/root_password_again password temp4now" | sudo debconf-set-selections
RUN apt-get install -y ant unzip mysql-server python-mysqldb python-pip python-dev libmysqlclient-dev
# mysql-install-pm

# daytrader-install-man
RUN /bin/true; cd /home/REPLACE_USERNAME; svn co http://svn.apache.org/repos/asf/geronimo/daytrader/tags/daytrader-parent-3.0.0/; export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-REPLACE_ARCH3/; cd /home/REPLACE_USERNAME/daytrader-parent-3.0.0/; mvn clean install
# daytrader-install-man

# geronimo-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://fossies.org/linux/www/geronimo-tomcat7-javaee6-3.0.1-bin.zip; cd /home/REPLACE_USERNAME; unzip geronimo-tomcat7-javaee6-3.0.1-bin.zip
# geronimo-install-man

# geronimo-jdbc-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-java-5.1.40.zip; cd /home/REPLACE_USERNAME/; unzip -qu mysql-connector-java-5.1.40.zip
RUN mkdir -p /home/REPLACE_USERNAME/geronimo-tomcat7-javaee6-3.0.1/repository/mysql/mysql-connector-java/5.1.40/
RUN mkdir -p /home/REPLACE_USERNAME/geronimo-tomcat7-javaee6-3.0.1/repository/mysql/com.mysql.jdbc/5.1.40/; chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME/
RUN cp -f /home/REPLACE_USERNAME/mysql-connector-java-5.1.40/mysql-connector-java-5.1.40-bin.jar /home/REPLACE_USERNAME/geronimo-tomcat7-javaee6-3.0.1/repository/mysql/mysql-connector-java/5.1.40/mysql-connector-java-5.1.40.jar; cp -f /home/REPLACE_USERNAME/mysql-connector-java-5.1.40/mysql-connector-java-5.1.40-bin.jar /home/REPLACE_USERNAME/geronimo-tomcat7-javaee6-3.0.1/repository/mysql/com.mysql.jdbc/5.1.40/com.mysql.jdbc-5.1.40.jar
RUN cp -f /home/REPLACE_USERNAME/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml /home/REPLACE_USERNAME/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml.orig; sed -i "s^<version>5.*^<version>5.1.40</version>^g" /home/REPLACE_USERNAME/daytrader-parent-3.0.0/javaee6/plans/target/classes/daytrader-mysql-xa-plan.xml
# geronimo-jdbc-install-man

# rain-wkt-install-man
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/ibmcb/rain-workload-toolkit.git; cd /home/REPLACE_USERNAME/rain-workload-toolkit; ant package; ant package-daytrader
# rain-wkt-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME/
