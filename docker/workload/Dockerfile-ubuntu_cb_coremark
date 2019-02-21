FROM REPLACE_NULLWORKLOAD_UBUNTU

# coremark-install-man
RUN apt-get update
RUN apt-get install -y build-essential
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/eembc/coremark.git
RUN cd /home/REPLACE_USERNAME/coremark/; make
# coremark-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME