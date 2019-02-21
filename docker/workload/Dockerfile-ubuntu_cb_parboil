FROM REPLACE_NULLWORKLOAD_UBUNTU

# cuda-install-man
RUN REPLACE_RSYNC/cuda-repo-ubuntu1804-10-0-local-10.0.130-410.48_1.0-1_REPLACE_ARCH3.deb /home/REPLACE_USERNAME/
RUN dpkg -i /home/REPLACE_USERNAME/cuda-repo-ubuntu1804-10-0-local-10.0.130-410.48_1.0-1_REPLACE_ARCH3.deb
RUN apt-key add /var/cuda-repo-*/7fa2af80.pub
RUN REPLACE_RSYNC/cudnn-10.0-linux-REPLACE_ARCH4-v7.4.2.24.tar /home/REPLACE_USERNAME/
RUN apt-get update
RUN apt-get install -y cuda
# cuda-install-man

# parboil-install-man
RUN REPLACE_RSYNC/pb2.5driver.tar /home/REPLACE_USERNAME/
RUN REPLACE_RSYNC/pb2.5datasets_standard-2.tgz /home/REPLACE_USERNAME/
RUN REPLACE_RSYNC/pb2.5benchmarks-2.tgz /home/REPLACE_USERNAME/
RUN cd /home/REPLACE_USERNAME; tar -xf pb2.5driver.tar
RUN cd /home/REPLACE_USERNAME; tar -xf pb2.5benchmarks-2.tgz; mv benchmarks /home/REPLACE_USERNAME/parboil
RUN cd /home/REPLACE_USERNAME; tar -xf pb2.5datasets_standard-2.tgz; mv datasets /home/REPLACE_USERNAME/parboil
RUN cd /home/REPLACE_USERNAME/parboil; chmod u+x ./parboil; chmod u+x benchmarks/*/tools/compare-output
# parboil-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME