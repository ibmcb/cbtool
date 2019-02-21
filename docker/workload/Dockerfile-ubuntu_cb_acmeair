FROM REPLACE_NULLWORKLOAD_UBUNTU

# ibm-java-install-man
RUN REPLACE_RSYNC/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin /tmp/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin
RUN sudo mv /tmp/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin /home/REPLACE_USERNAME/; sudo chmod 0755 /home/REPLACE_USERNAME/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin
RUN echo "INSTALLER_UI=silent" > /home/REPLACE_USERNAME/installer.properties; echo "LICENSE_ACCEPTED=TRUE" >> /home/REPLACE_USERNAME/installer.properties
RUN /home/REPLACE_USERNAME/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin -i silent -f /home/REPLACE_USERNAME/installer.properties
# ibm-java-install-man

# maven-install-pm
RUN apt-get update; apt-get install -y maven ant
# maven-install-pm

# gradle-install-pm
RUN apt-get install -y gradle unzip
# gradle-install-pm

# acmeair-install-man
RUN cd /home/REPLACE_USERNAME; git clone https://github.com/blueperf/acmeair-monolithic-java.git;
RUN echo "loader.timeout=180" > /home/REPLACE_USERNAME/acmeair-monolithic-java/src/main/resources/loader.properties; echo "loader.numCustomers=200" >> /home/REPLACE_USERNAME/acmeair-monolithic-java/src/main/resources/loader.properties 
RUN export JAVA_HOME=/opt/ibm/java-REPLACE_ARCH1-80/jre; cd /home/REPLACE_USERNAME/acmeair-monolithic-java; mvn clean package
RUN sudo mkdir -p /root/.m2/; sudo rsync -az /root/.m2/ /home/REPLACE_USERNAME/
#RUN mv /root/.gradle/ /home/REPLACE_USERNAME/
# acmeair-install-man

# websphere-liberty-install-man
RUN REPLACE_RSYNC/wlp-webProfile7-17.0.0.3.zip /tmp/wlp-webProfile7-17.0.0.3.zip
RUN mkdir -p /opt/ibm; sudo mv /tmp/wlp-webProfile7-17.0.0.3.zip /opt/ibm/wlp-webProfile7-17.0.0.3.zip
RUN cd /opt/ibm/; sudo unzip -q wlp-webProfile7-17.0.0.3.zip
RUN rm /opt/ibm/wlp-webProfile7-17.0.0.3.zip
# websphere-liberty-install-man

# jmeter-install-pm
RUN apt-get install -y jmeter
# jmeter-install-pm

# acmeairdriver-install-man
RUN cd /home/REPLACE_USERNAME; git clone https://github.com/acmeair/acmeair-driver.git; export JAVA_HOME=/opt/ibm/java-REPLACE_ARCH1-80/jre; cd acmeair-driver; sed -i 's/gradle-.*/gradle-4.10.2-bin.zip/g' gradle/wrapper/gradle-wrapper.properties; ./gradlew build
RUN cp /home/REPLACE_USERNAME/acmeair-driver/acmeair-jmeter/build/libs/acmeair-jmeter-1.1.0-SNAPSHOT.jar /usr/share/jmeter/lib/ext/
RUN cd /usr/share/jmeter/lib/ext/; sudo wget -N -q https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/json-simple/json-simple-1.1.1.jar
# acmeairdriver-install-man

# mongo-install-pm
RUN apt-get install -y mongodb
RUN sed -i "s/.*bind_ip.*/bind_ip=0.0.0.0/" /etc/mongodb.conf
# service_stop_disable mongodb
# mongo-install-pm

# mongo-driver-java-install-man
#RUN mkdir -p /opt/ibm/wlp/usr/shared/resources/mongodb; cd /opt/ibm/wlp/usr/shared/resources/mongodb; wget -N -q http://central.maven.org/maven2/org/mongodb/mongo-java-driver/2.12.2/mongo-java-driver-2.12.2.jar
RUN mkdir -p /opt/ibm/wlp/usr/shared/resources/mongodb; sudo cp -f $(find /home/REPLACE_USERNAME/acmeair-monolithic-java | grep mongo-java-driver-.*.jar) /opt/ibm/wlp/usr/shared/resources/mongodb/
# mongo-driver-java-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
