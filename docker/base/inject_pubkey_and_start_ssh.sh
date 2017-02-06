#!/bin/sh
if [ "${CB_SSH_PUB_KEY}" != "NA" ]
then

    CB_USER_LIST=$(ls /home)
    if [ "${CB_LOGIN}" != "NA" ]
    then
        ls /home | grep $CB_LOGIN
        if [[ $? -eq 0 ]]
        then
            CB_USER_LIST=${CB_LOGIN}
        fi
    fi

    for USRNAM in ${CB_USER_LIST}
    do
        mkdir -p /home/$USRNAM/.ssh
        chmod 700 /home/$USRNAM/.ssh
        chown ${USRNAM}:${USRNAM} /home/$USRNAM/.ssh
        echo "# Key Injected by CB" >> /home/$USRNAM/.ssh/authorized_keys
        echo "${CB_SSH_PUB_KEY}" >> /home/$USRNAM/.ssh/authorized_keys
        chmod 0600 /home/$USRNAM/.ssh/authorized_keys
        chown $USRNAM:$USRNAM /home/$USRNAM/.ssh/authorized_keys
    done

    echo "# Key Injected by CB" >> /root/.ssh/authorized_keys
    echo "${CB_SSH_PUB_KEY}" >> /root/.ssh/authorized_keys
else
    echo "Bypassing SSH pubkey injection for \"root\" and regular users"
fi

/usr/sbin/sshd -D

exit 0
