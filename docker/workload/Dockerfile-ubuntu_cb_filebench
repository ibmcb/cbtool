FROM REPLACE_NULLWORKLOAD_UBUNTU

# filebench-install-man
RUN apt-get update
RUN apt-get install -y libaio1 bison flex gawk build-essential libtool automake
RUN cd /home/REPLACE_USERNAME; git clone https://github.com/filebench/filebench.git
RUN cd /home/REPLACE_USERNAME/filebench; libtoolize; aclocal; autoheader; automake --add-missing; autoconf; ./configure; make; sudo make install
# filebench-install-man

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
