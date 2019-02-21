FROM REPLACE_NULLWORKLOAD_UBUNTU

# hpcc-install-pm
RUN apt-get update
RUN apt-get install -y hpcc gfortran libopenmpi-dev
RUN wget -N -q -P /home/REPLACE_USERNAME https://www.nas.nasa.gov/assets/npb/NPB3.3.1.tar.gz
RUN cd /home/REPLACE_USERNAME && tar zxvf NPB3.3.1.tar.gz
RUN echo "" > /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/suite.def
RUN bash -c 'for bm in ft mg sp lu bt is ep cg dt ; do echo "${bm} S 1" >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/suite.def ; done'
RUN bash -c 'for bm in ft mg sp lu bt is ep cg dt ; do for np in 4 16 64 256 ; do for class in C D ; do echo "${bm} ${class} ${np}" >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/suite.def ; done ; done ; done'
RUN bash -c 'echo "MPIF77 = mpif77"         >  /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "FLINK   = mpif77"        >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "FMPI_LIB ="              >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "FMPI_INC ="              >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "FFLAGS  = -O3"           >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "FLINKFLAGS = -O3"        >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "MPICC = mpicc"           >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CLINK   = mpicc"         >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CMPI_LIB  ="             >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CMPI_INC ="              >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CFLAGS  = -O3"           >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CLINKFLAGS = -O3"        >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "CC      = cc -O3"        >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "BINDIR  = ../bin"        >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'echo "RAND   = randi8"         >> /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI/config/make.def'
RUN bash -c 'cd /home/REPLACE_USERNAME/NPB3.3.1/NPB3.3-MPI && make suite'
# hpcc-install-pm

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
