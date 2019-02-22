#!/bin/bash

f=/etc/security/limits.conf
cat > $f <<EOF
* soft memlock unlimited
* hard memlock unlimited
* soft nofile 2097152
* hard nofile 2097152
* soft nproc unlimited
* hard nproc unlimited
* hard stack unlimited
* soft stack unlimited
root soft memlock unlimited
root hard memlock unlimited
root hard nofile 2097152
root soft nofile 2097152
root hard nproc unlimited
root soft nproc unlimited
root hard stack unlimited
root soft stack unlimited
user hard nofile unlimited
user soft nofile unlimited
EOF

if ! grep pam_limits /etc/pam.d/common-session > /dev/null 2>&1 
then
	echo "session required pam_limits.so" >> /etc/pam.d/common-session
fi
  
if ! grep pam_limits /etc/pam.d/common-session-noninteractive > /dev/null 2>&1 
then
	echo "session required pam_limits.so" >> /etc/pam.d/common-session-noninteractive
fi  

if ! grep fs.file-max /etc/sysctl.conf > /dev/null 2>&1
then
    echo "fs.file-max = 209715" >> /etc/sysctl.conf
fi

sed -i "s/.*DefaultLimitNOFILE=/DefaultLimitNOFILE=2097152/g" /etc/systemd/system.conf
sed -i "s/.*DefaultLimitNOFILE=/DefaultLimitNOFILE=2097152/g" /etc/systemd/user.conf