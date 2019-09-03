#!/usr/bin/env bash

CB_RESET=0
CB_SLEEP=15
CB_WORKLOADS="none"
CB_USAGE="Usage: $0 [-w/--workloads] [-s/--sleep] [-r/--reset]"
CB_MODEL="auto"

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
        -w|--workloads)
        CB_WORKLOADS="$2"
        shift
        ;;
        -w=*|--workloads=*)
        CB_WORKLOADS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -c|--cloud_model)
        CB_MODEL="$2"
        shift
        ;;
        -c=*|--cloud_model=*)
        CB_MODEL=$(echo $key | cut -d '=' -f 2)
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
else 
    cat ~/$CB_ACTUAL_DIR/util/workloads_alias_mapping.txt | awk '{ print $1 }' | grep $CB_WORKLOADS > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        CB_WORKLOADS=$(cat ~/$CB_ACTUAL_DIR/util/workloads_alias_mapping.txt | grep $CB_WORKLOADS[[:space:]] | cut -d ' ' -f 2 | sed 's/,/ /g')
    fi
fi

pushd $CB_CURR_DIR/.. >/dev/null 2>&1 
if [[ $CB_WORKLOADS != "none" ]]
then
    wlist=''
    wcount=0
    ./cb --soft_reset exit
    time ./regression/real_application_regression_test.py --cloud_model $CB_MODEL --headeronly
    popd
    for workload in $CB_WORKLOADS
    do  
        sudo tmux kill-session -t cb${workload} > /dev/null 2>&1
        sudo rm /tmp/*${workload}_real_application_regression_test.txt > /dev/null 2>&1
        sudo tmux new -d -s cb${workload}
        sudo tmux send-keys -t cb${workload} "su - ${USER}" Enter
        sudo tmux send-keys -t cb${workload} "cd ~/$CB_ACTUAL_DIR" Enter
        sudo tmux send-keys -t cb${workload} "time ./regression/real_application_regression_test.py --cloud_model $CB_MODEL --types ${workload} --noheader" Enter
    
        actual_workloads=$(echo $workload | sed 's/fake/nullworkload/g')
        for alias in $(sudo cat ~/$CB_ACTUAL_DIR/util/workloads_alias_mapping.txt | grep "synthetic \|application-stress \|scientific \|transactional \|data-centric " | awk '{ print $1}')
        do
            cb_alias=$(echo $alias | cut -d ' ' -f 1)
            cb_list=$(sudo cat ~/$CB_ACTUAL_DIR/util/workloads_alias_mapping.txt | grep "$alias " | cut -d ' ' -f 2 | sed 's/,/ /g')
            actual_workloads=$(echo $actual_workloads | sed "s/$cb_alias/$cb_list/g")    
        done
    	wlist=$actual_workloads' '$wlist
    done            
fi
    
function snapshot_results {
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
}

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
    snapshot_results
    sleep $CB_SLEEP
done

date2=`date +%s`
ddiff=$((date2-date1))
echo " "
echo "$wcount tests completed after $ddiff seconds"


snapshot_results