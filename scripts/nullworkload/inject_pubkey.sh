#!/bin/sh
if [ "${CB_SSH_PUB_KEY}" != "NA" ]
then
    echo "# Key Injected by CB" >> /home/cbuser/.ssh/authorized_keys
    echo "ssh-rsa "${CB_SSH_PUB_KEY} >> /home/cbuser/.ssh/authorized_keys

    echo "# Key Injected by CB" >> /root/.ssh/authorized_keys
    echo "ssh-rsa "${CB_SSH_PUB_KEY} >> /root/.ssh/authorized_keys
else
    echo "Bypassing SSH pubkey injection for \"root\" and \"cbuser\""
fi
exit 0
