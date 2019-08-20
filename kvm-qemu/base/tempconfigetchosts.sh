#!/bin/bash
sudo rsync --ignore-existing -az /etc/hosts /etc/hosts.original
sudo hostname cbinst
sudo bash -c "echo \"$(ip -o addr list | grep eth0 | grep inet[[:space:]] | awk '{ print $4 }' | cut -d '/' -f 1) cbinst\" >> /etc/hosts"
sudo bash -c "cat /root/cache_resolve_dns >> /etc/hosts"
exit 0
