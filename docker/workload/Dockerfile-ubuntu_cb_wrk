FROM REPLACE_NULLWORKLOAD_UBUNTU

# apache-install-pm
RUN apt-get update
RUN apt-get install -y apache2
# service_stop_disable apache2
# apache-install-pm

# wrk-install-man
RUN /bin/true; cd /home/REPLACE_USERNAME/; git clone https://github.com/wg/wrk.git; cd /home/REPLACE_USERNAME/wrk; make all
# wrk-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
