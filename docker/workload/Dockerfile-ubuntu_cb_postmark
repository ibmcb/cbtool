FROM REPLACE_NULLWORKLOAD_UBUNTU

# postmark-install-man
RUN apt-get update
RUN apt-get install -y libaio1
RUN cd /home/REPLACE_USERNAME; git clone https://github.com/wolfwood/postmark.git; cd /home/REPLACE_USERNAME/postmark/; make all
# postmark-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME