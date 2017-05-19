FROM REPLACE_NULLWORKLOAD_UBUNTU

# mysql-install-pm
RUN echo "mysql-server-5.7 mysql-server/root_password password temp4now" | sudo debconf-set-selections; echo "mysql-server-5.7 mysql-server/root_password_again password temp4now" | sudo debconf-set-selections
RUN apt-get update
RUN apt-get install -y mysql-server python-mysqldb python-pip python-dev libmysqlclient-dev
# mysql-install-pm

# sysbench-install-pm
RUN apt-get update
RUN apt-get install -y sysbench
# sysbench-install-pm

RUN chown -R REPLACE_USERNAME:REPLACE_USERNAME /home/REPLACE_USERNAME