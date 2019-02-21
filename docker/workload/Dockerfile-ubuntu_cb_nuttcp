FROM REPLACE_NULLWORKLOAD_UBUNTU

# nuttcp-install-man
RUN apt-get install -y gcc
RUN apt-get update
RUN wget -N -q -P /home/REPLACE_USERNAME http://nuttcp.net/nuttcp/nuttcp-7.3.3/nuttcp-7.3.3.c
RUN cd /home/REPLACE_USERNAME; gcc nuttcp-7.3.3.c -o nuttcpbin; sudo mv /home/REPLACE_USERNAME/nuttcpbin /usr/local/bin/nuttcp
RUN chmod 755 /usr/local/bin/nuttcp
# nuttcp-install-man
RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
