FROM REPLACE_NULLWORKLOAD_UBUNTU

# autoreconf-install-pm
RUN apt-get update
RUN apt-get install -y build-essential autoconf automake libpcre3-dev zlib1g-dev libtool pkg-config
# autoreconf-install-pm

# redis-install-pm
RUN apt-get install -y redis-server
RUN sed -i "s/.*bind.*/bind 0.0.0.0/" /etc/redis/redis.conf
# service_stop_disable redis-server
# redis-install-pm

# memtier_benchmark-install-man
RUN apt-get update; apt-get install -y libevent-dev
RUN /bin/true; cd /home/REPLACE_USERNAME; git clone https://github.com/RedisLabs/memtier_benchmark.git
RUN /bin/true; cd /home/REPLACE_USERNAME/memtier_benchmark/; export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}; autoreconf -ivf; ./configure; make
RUN /bin/true; cd /home/REPLACE_USERNAME/memtier_benchmark/; sudo make install
# memtier_benchmark-install-man
RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME
