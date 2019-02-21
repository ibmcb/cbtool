FROM REPLACE_PREREQS_UBUNTU

WORKDIR /home/REPLACE_USERNAME/
RUN git clone https://github.com/ibmcb/cbtool.git; cd /home/REPLACE_USERNAME/cbtool; git checkout REPLACE_BRANCH
RUN cd /home/REPLACE_USERNAME/cbtooltmp/; mv 3rd_party ../cbtool/; mkdir -p /home/REPLACE_USERNAME/cbtool/3rd_party/workload
RUN rsync -az /home/REPLACE_USERNAME/cbtooltmp/configs/ /home/REPLACE_USERNAME/cbtool/configs/
RUN rsync -az /home/REPLACE_USERNAME/cbtooltmp/lib/ /home/REPLACE_USERNAME/cbtool/lib/
RUN cp -f /home/REPLACE_USERNAME/cbtool/util/manually_download_files.txt /home/REPLACE_USERNAME/cbtool/3rd_party/workload
RUN cd /home/REPLACE_USERNAME/cbtool; mv configs private_configs; mkdir data; mv data private_data

WORKDIR /home/REPLACE_USERNAME/cbtool
