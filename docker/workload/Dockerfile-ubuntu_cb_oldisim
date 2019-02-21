FROM REPLACE_NULLWORKLOAD_UBUNTU

# scons-install-pm
RUN apt-get update
RUN apt-get install -y build-essential gengetopt libgoogle-perftools-dev libunwind-dev libevent-dev scons libboost-all-dev tmux
# scons-install-pm

# oldisim-install-man
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/GoogleCloudPlatform/oldisim.git; cd /home/REPLACE_USERNAME/oldisim/; git submodule update --init
RUN /bin/true; cd /home/REPLACE_USERNAME/oldisim/; ; sed -n -i 'p;23a #include <functional>' include/oldisim/FanoutManager.h; scons
# oldisim-install-man
RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
