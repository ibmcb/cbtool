FROM REPLACE_NULLWORKLOAD_UBUNTU

# linpack-install-man
RUN apt-get update
RUN mkdir -p /home/REPLACE_USERNAME/linpack/benchmarks/linpack
RUN REPLACE_RSYNC/l_lpk_p_11.3.0.004.tgz /home/REPLACE_USERNAME/
RUN cd /home/REPLACE_USERNAME/; tar -xzf l_lpk_p_11.3.0.004.tgz; rm l_lpk_p_11.3.0.004.tgz
# linpack-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME