#!/usr/bin/env bash

CB_TEST_LEVEL="lowest"
CB_ADAPTERS="fast"
CB_RESET=0
CB_SLEEP=15
CB_USAGE="Usage: $0 [-l/--level test level] [-a/--adapters adapters] [-s/--sleep] [-r/--reset]"

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -l|--level)
        CB_TEST_LEVEL="$2"
        shift
        ;;
        -l=*|--level=*)
        CB_TEST_LEVEL=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -a|--adapters)
        CB_ADAPTERS="$2"
        shift
        ;;
        -a=*|--adapters=*)
        CB_ADAPTERS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -s|--sleep)
        CB_SLEEP="$2"
        shift
        ;;
        -s=*|--sleep=*)
        CB_SLEEP=$(echo $key | cut -d '=' -f 2)
        shift
        ;;        
        -r|--reset)
        CB_RESET=1
        ;;
        -h|--help)
        echo $CB_USAGE
        shift
        ;;
        *)
        # unknown option
        ;;
        esac
        shift
done

date1=`date +%s`

if [[ $CB_RESET -eq 1 ]]
then
    #    sudo pkill -9 -f cloudbench
    #    sudo pkill -9 -f cbtool 
    #    sudo pkill -9 -f stores
    sudo rm /tmp/*real_multicloud* > /dev/null 2>&1
    sudo rm /tmp/*_real_cloud_regression_*.txt > /dev/null 2>&1
    for i in $(sudo tmux ls | grep cb | awk '{ print $1 }' | sed 's/://g')
    do 
        sudo tmux kill-session -t $i > /dev/null 2>&1
    done
fi

if [[ $CB_ADAPTERS == "all" ]]
then
    CB_ADAPTERS="sim pdm pcm kub osk,oskfile,oskfip nop gen osl,oslfip ec2 gce do as slr"
elif [[ $CB_ADAPTERS == "private" ]]
then
    CB_ADAPTERS="sim plm pdm pcm kub osk,oskfile,oskfip nop gen osl,oslfip"
elif [[ $CB_ADAPTERS == "public" ]]
then
    CB_ADAPTERS="ec2 gce do as slr"
elif [[ $CB_ADAPTERS == "libcloud" ]]
then
    CB_ADAPTERS="osl,oslfip do as"
elif [[ $CB_ADAPTERS == "fast" ]]
then
    CB_ADAPTERS="sim nop"
fi

CB_ADAPTERS=$(echo $CB_ADAPTERS | sed 's/do[[:space:]]/dozz /g' | sed 's/as[[:space:]]/aszz /g')

alist=''
acount=0
time ./regression/real_multicloud_regression.py configs/softlayer_ris a0 lowest private headeronly
for adapter in $CB_ADAPTERS
do
    adapter=$(echo $adapter | sed 's/zz//g')
    actual_user=$(echo $adapter | cut -d ',' -f 1)
    adapter=$(echo $adapter | sed 's/osl/os/g')
    actual_adapter=$(echo $adapter | cut -d ',' -f 1)
    
	sudo tmux kill-session -t cb${actual_user} > /dev/null 2>&1
	sudo rm /tmp/${actual_adapter}_real_multicloud_regression_test.txt > /dev/null 2>&1
	sudo rm /tmp/${actual_adapter}_real_cloud_regression_ecode.txt    > /dev/null 2>&1
	sudo tmux new -d -s cb${actual_user}
	sudo tmux send-keys -t cb${actual_user} "su - cb${actual_user}" Enter
	sudo tmux send-keys -t cb${actual_user} "cd ~/repos/cloudbench/" Enter
	sudo tmux send-keys -t cb${actual_user} "~/cbsync.sh" Enter
	sudo tmux send-keys -t cb${actual_user} "time ./regression/real_multicloud_regression.py configs/softlayer_ris ${adapter} ${CB_TEST_LEVEL} private noheader" Enter
	
    alist=$adapter' '$alist
done

alist=$(echo $alist | sed 's/,/ /g' | sed -e $'s/ /\\\n/g' | sort | sed ':a;N;$!ba;s/\n/ /g')
acount=$(echo $alist | wc -w)
ecodes=$(sudo ls /tmp/*_real_multicloud_regression_ecode.txt 2>&1 | grep -v 'cannot access' | wc -l)

echo "Will wait until $acount tests ($alist) are completed"
while [[ "$ecodes" -lt "$acount" ]]
do
    aclist=$(sudo ls -la /tmp/*_real_multicloud_regression_ecode.txt 2>&1 | grep -v 'cannot access' | awk '{ print $9 }' | sed 's^/tmp/^^g' | sed 's^_real_multicloud_regression_ecode.txt^^g' | sort | sed ':a;N;$!ba;s/\n/ /g')
    ecodes=$(sudo ls /tmp/*_real_multicloud_regression_ecode.txt 2>&1 | grep -v 'cannot access' | wc -l)
    diff=$(python -c "a=\"$alist\"; b=\"$aclist\"; a=set(a.split()); b=set(b.split()); print ' '.join(sorted(a-b))") 
    echo "$ecodes ($aclist) out of $acount tests completed so far (missing: $diff)"
    sudo ls /tmp/*_real_multicloud_regression_test.txt > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
	sudo cat /tmp/a0_real_multicloud_regression_test.txt        
    for fn in $(ls /tmp/*_real_multicloud_regression_test.txt | grep -v a0_)
        do 
            cat $fn | tail -1
        done
    fi
    sleep $CB_SLEEP
done

date2=`date +%s`
ddiff=$((date2-date1))
echo "$acount tests completed after $ddiff seconds"
