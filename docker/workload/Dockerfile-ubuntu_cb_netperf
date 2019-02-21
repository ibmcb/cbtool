FROM REPLACE_NULLWORKLOAD_UBUNTU

# netperf-install-pm
RUN echo "deb http://us.archive.ubuntu.com/ubuntu bionic main multiverse" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y netperf
# netperf-install-pm

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
