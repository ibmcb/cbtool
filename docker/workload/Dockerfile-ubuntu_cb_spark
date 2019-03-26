FROM REPLACE_NULLWORKLOAD_UBUNTU

# ibm-java-install-man
RUN REPLACE_RSYNC/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin /home/REPLACE_USERNAME/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin
RUN chmod 0755 /home/REPLACE_USERNAME/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin
RUN echo "INSTALLER_UI=silent" > /home/REPLACE_USERNAME/installer.properties; echo "LICENSE_ACCEPTED=TRUE" >> /home/REPLACE_USERNAME/installer.properties
RUN /home/REPLACE_USERNAME/ibm-java-REPLACE_ARCH1-sdk-8.0-5.27.bin -i silent -f /home/REPLACE_USERNAME/installer.properties
# ibm-java-install-man

# java-install-pm
#RUN apt-get update; apt-get install -y software-properties-common;
#RUN add-apt-repository -y ppa:openjdk-r/ppa
#RUN apt-get update; apt-get install -y openjdk-8-jdk
# java-install-pm

# scala-install-pm
RUN apt-get update; apt-get install -y scala
# scala-install-pm

# hadoop-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://archive.apache.org/dist/hadoop/common/hadoop-2.7.5/hadoop-2.7.5.tar.gz
RUN /bin/true; cd /home/REPLACE_USERNAME; tar -xzf /home/REPLACE_USERNAME/hadoop*.gz
# hadoop-install-man

# spark-install-man
#RUN wget -N -q -P /home/REPLACE_USERNAME http://apache.cs.utah.edu/spark/spark-2.1.3/spark-2.1.3-bin-hadoop2.7.tgz
#RUN wget -N -q -P /home/REPLACE_USERNAME http://apache.cs.utah.edu/spark/spark-2.2.2/spark-2.2.2-bin-hadoop2.7.tgz
RUN wget -N -q -P /home/REPLACE_USERNAME http://apache.cs.utah.edu/spark/spark-2.2.3/spark-2.2.3-bin-hadoop2.7.tgz
RUN /bin/true; cd /home/REPLACE_USERNAME; tar -xzf /home/REPLACE_USERNAME/spark*.tgz
RUN wget -N -q -P /home/REPLACE_USERNAME http://9.2.130.17/repo/dropbox/cloudbench/spark/spark-2.2.0-bin-ibm-dcs-spark.tgz; cd /home/REPLACE_USERNAME; tar -xzf /home/REPLACE_USERNAME/spark-2.2.0-bin-ibm-dcs-spark.tgz
# spark-install-man

# gradle-install-pm
RUN apt-get install -y gradle unzip
# gradle-install-pm

# numpy-install-pm
RUN apt-get install -y python-numpy
# numpy-install-pm

#git-lfs-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://github.com/git-lfs/git-lfs/releases/download/v2.3.4/git-lfs-linux-amd64-2.3.4.tar.gz
RUN /bin/true; cd /home/REPLACE_USERNAME; tar -xzvf /home/REPLACE_USERNAME/git-lfs*.tar.gz; cd git-lfs-2.3.4; sudo ./install.sh
# git-lfs-install-man

# gatk4-install-man
#RUN cd /home/REPLACE_USERNAME; git clone https://github.com/broadinstitute/gatk.git
#RUN export JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF8; cd /home/REPLACE_USERNAME/gatk; ./gradlew bundle; /bin/true
#RUN wget -N -q -P /home/REPLACE_USERNAME https://github.com/broadinstitute/gatk/releases/download/4.0.10.0/gatk-4.0.10.0.zip
RUN /bin/true; wget -N -q -P /home/REPLACE_USERNAME https://github.com/broadinstitute/gatk/releases/download/4.0.1.1/gatk-4.0.1.1.zip; cd /home/REPLACE_USERNAME; sudo unzip /home/REPLACE_USERNAME/gatk-4.0.1.1.zip
RUN /bin/true; wget -N -q -P /home/REPLACE_USERNAME https://github.com/broadinstitute/gatk/releases/download/4.0.12.0/gatk-4.0.12.0.zip; cd /home/REPLACE_USERNAME; sudo unzip /home/REPLACE_USERNAME/gatk-4.0.12.0.zip
# gatk4-install-man

# spark-perf-install-man
RUN cd /home/REPLACE_USERNAME; pip install nose; git clone https://github.com/databricks/spark-perf.git
# spark-perf-install-man

# sparkbench-install-man
RUN wget -N -q -P /home/REPLACE_USERNAME https://github.com/SparkTC/spark-bench/releases/download/v91/spark-bench_2.1.1_0.3.0-RELEASE_91.tgz; cd /home/REPLACE_USERNAME; tar -xzf /home/REPLACE_USERNAME/spark-bench_*.tgz;
# sparkbench-install-man

# gatk4-input-install-man
RUN mkdir /home/REPLACE_USERNAME/GATK4-small-input
RUN mkdir /home/REPLACE_USERNAME/GATK4-full-input
RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME 
RUN REPLACE_RSYNC/CEUTrio.HiSeq.WGS.b37.NA12878.20.21* /home/REPLACE_USERNAME/GATK4-small-input/
RUN REPLACE_RSYNC/human_g1k_v37.20.21* /home/REPLACE_USERNAME/GATK4-small-input/
RUN REPLACE_RSYNC/dbsnp_138.b37.20.21* /home/REPLACE_USERNAME/GATK4-small-input/
# gatk4-input-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
