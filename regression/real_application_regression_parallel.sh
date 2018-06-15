#!/usr/bin/env bash

CB_TEST_LEVEL="lowest"
CB_ADAPTERS="fast"
CB_RESET=0
CB_SLEEP=15
CB_USAGE="Usage: $0 [-l/--level test level] [-w/--workloads] [-s/--sleep] [-r/--reset]"

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_CURR_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

CB_ACTUAL_DIR=$(echo $CB_CURR_DIR | sed "s^$HOME^^g" | sed "s^/regression^^g")

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
        -w|--workloads)
        CB_WORKLOADS="$2"
        shift
        ;;
        -w=*|--workloads=*)
        CB_WORKLOADS=$(echo $key | cut -d '=' -f 2)
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
    sudo rm /tmp/*real_application_regression_test.txt* > /dev/null 2>&1
#    sudo rm /tmp/*_real_cloud_regression_*.txt > /dev/null 2>&1
    for i in $(sudo tmux ls | grep cb | awk '{ print $1 }' | sed 's/://g')
    do 
        sudo tmux kill-session -t $i > /dev/null 2>&1
    done
fi

CB_WORKLOADS=$(echo $CB_WORKLOADS | sed 's/,/ /g')

if [[ $CB_WORKLOADS == "all" ]]
then
    CB_WORKLOADS="fake synthetic application-stress scientific transactional data-centric"
fi

if [[ $CB_WORKLOADS == "spec" ]]
then
	CB_WORKLOADS="nullworkload cassandra_ycsb hadoop"
fi

wlist=''
wcount=0
./cb --soft_reset exit
time ./regression/real_application_regression_test.py --headeronly
for workload in $CB_WORKLOADS
do  
    sudo tmux kill-session -t cb${workload} > /dev/null 2>&1
    sudo rm /tmp/*${workload}_real_application_regression_test.txt > /dev/null 2>&1
    sudo tmux new -d -s cb${workload}
    sudo tmux send-keys -t cb${workload} "su - ${USER}" Enter
    sudo tmux send-keys -t cb${workload} "cd ~/$CB_ACTUAL_DIR" Enter
    sudo tmux send-keys -t cb${workload} "time ./regression/real_application_regression_test.py --types ${workload} --noheader" Enter

    actual_workloads=$(echo $workload | sed 's/fake/nullworkload/g')
    actual_workloads=$(echo $actual_workloads | sed 's/synthetic/bonnie,btest,ddgen,fio,filebench,postmark,iperf,netperf,nuttcp,xping,unixbench,coremark/g')
    actual_workloads=$(echo $actual_workloads | sed 's/application-stress/memtier,oldisim,wrk,wrk_lb/g')
    actual_workloads=$(echo $actual_workloads | sed 's/scientific/hpcc,linpack,multichase,parboil,scimark/g')
    actual_workloads=$(echo $actual_workloads | sed 's/transactional/cassandra_ycsb,mongo_ycsb,redis_ycsb,open_daytrader,open_daytrader_lb,specjbb,sysbench,mongo_acmeair/g')
    actual_workloads=$(echo $actual_workloads | sed 's/data-centric/hadoop,giraph/g')

    wlist=$actual_workloads' '$wlist
done

wlist=$(echo $wlist | sed 's/,/ /g' | sed -e $'s/ /\\\n/g' | sort | sed ':a;N;$!ba;s/\n/ /g')
wcount=$(echo $wlist | wc -w)
ecodes=0
    
echo "Will wait until $wcount tests ($wlist) are completed"
while [[ "$ecodes" -lt "$wcount" ]]
do
    wclist=''
    for fn in $(ls /tmp/*_real_application_regression_test.txt | grep -v a0_)
    do
        wclist=$wclist" "$(cat $fn | grep "build:" | awk '{ print $2 }' | cut -d ':' -f 3)
    done
    wclist=$(echo $wclist | sed 's/ /\n/g' | sort | sed ':a;N;$!ba;s/\n/ /g')
    ecodes=$(echo $wclist | wc -w)
    diff=$(python -c "a=\"$wlist\"; b=\"$wclist\"; a=set(a.split()); b=set(b.split()); print ' '.join(sorted(a-b))") 
    echo "$ecodes ($wclist) out of $wcount tests completed so far (missing: $diff)"
    sudo ls /tmp/*_real_application_regression_test.txt > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        sudo cat /tmp/*a0_real_application_regression_test.txt
        for fn in $(ls /tmp/*_real_application_regression_test.txt | grep -v a0_)
        do
            nlf=$(cat $fn | wc -l)
            nlf=$((nlf-1))
            cat $fn | tail -$nlf
        done
    fi
    sleep $CB_SLEEP
done

date2=`date +%s`
ddiff=$((date2-date1))
echo "$wcount tests completed after $ddiff seconds"