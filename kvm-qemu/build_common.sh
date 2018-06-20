#!/usr/bin/env bash

CB_KVMQEMU_BIMG_DIR=NONE
CB_KVMQEMU_UBUNTU_BASE=https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img
CB_KVMQEMU_CENTOS_BASE=https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
CB_DISTROS="ubuntu"
CB_USERNAME="cbuser"
CB_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CB_WKS="all"
CB_VERB=''
CB_BASE_IMAGE_SKIP=0
CB_NULLWORKLOAD_IMAGE_SKIP=0
CB_RSYNC_ADDR=$(sudo ifconfig docker0 | grep "inet " | awk '{ print $2 }' | sed 's/addr://g')
for pi in $(sudo netstat -puntel | grep rsync | grep tcp[[:space:]] | awk '{ print $9 }' | sed 's^/rsync^^g')
do
    if [[ $(echo $(sudo ps aux | grep $pi | grep -c $(whoami)_rsync.conf)) -ne 0 ]]
    then
        CB_RSYNC_PORT=$(sudo netstat -puntel | grep $pi | awk '{ print $4 }' | cut -d ':' -f 2)
	break
    fi
done
CB_RSYNC=$CB_RSYNC_ADDR-${CB_RSYNC_PORT}-$(whoami)
    
if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_KVMQEMU_S_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

CB_USAGE="Usage: $0 -r built image location [-w Workload] [-l CB Username/login] [-b branch] [-o distros] [--skip] [--verbose]"

function download_base_images {
    echo "##### Downloading latest version of the vanilla cloud images"
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1
    for CB_KVMQEMU_IMG in $CB_KVMQEMU_DISTROS_IMG_LIST
    do
        sudo wget -N $CB_KVMQEMU_IMG
    done
    echo "##### Done downloading the latest version of the vanilla cloud images"
    echo
    popd > /dev/null 2>&1    
}
export -f download_base_images

function create_base_images {
    echo "##### Creating base images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1
    for CB_KVMQEMU_IMG in $CB_KVMQEMU_DISTROS_IMG_LIST
    do
        CB_KVMQEMU_CIMG_FN=$(echo $CB_KVMQEMU_IMG | rev | cut -d '/' -f 1 | rev)
        if [[ $(echo $CB_KVMQEMU_CIMG_FN | grep -ci centos) -eq 1 ]]
        then
            CB_KVMQEMU_BIMG="centos"
        else
            CB_KVMQEMU_BIMG="ubuntu"
        fi
        sudo rm -rf cb_base_${CB_KVMQEMU_BIMG}
        sudo qemu-img create -f qcow2 cb_base_${CB_KVMQEMU_BIMG} 15G
        sudo virt-resize --expand /dev/sda1 $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
        #cp -f $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
        #sudo qemu-img resize cb_base_${CB_KVMQEMU_BIMG} +18G    
        cp -f $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        sudo sed -i "s^REPLACE_USERNAME^${CB_USERNAME}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        sudo sed -i "s^REPLACE_BRANCH^${CB_BRANCH}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        sudo sed -i "s^REPLACE_PATH^${CB_KVMQEMU_S_DIR}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_

        sudo virt-customize -a cb_base_${CB_KVMQEMU_BIMG} $CB_VERB --commands-from-file $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        COUT=$?
        let ERROR+=$COUT
    done
    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating base images"
        exit $ERROR
    else
        echo "##### Done creating base images"
    fi
    echo
    popd > /dev/null 2>&1    
}
export -f create_base_images

function create_workload_images {
    CB_WKS_LIST=$1
    CB_DISTROS_LIST=$2
    
    if [[ $CB_DISTROS_LIST == "all" ]]
    then
        CB_DISTROS_LIST=ubuntu' 'centos
    fi

    echo "##### Creating workload images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1

    for _CB_DISTRO in $CB_DISTROS_LIST
    do
        if [[ $CB_WKS_LIST == "all" ]]
        then
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep ${_CB_DISTRO} | grep -v caffe | grep -v rubbos | grep -v rubis | grep -v spark | grep -v speccpu | grep -v specsfs | grep -v specweb | grep -v nullworkload | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        else
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep $CB_WKS_LIST | grep ${_CB_DISTRO} | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        fi
        
        for _CB_WKS in $CB_WKS_LIST
        do  
            if [[ ${_CB_WKS} == "nullworkload" ]]
            then
                CB_KVMQEMU_BIMG_FN=cb_base_${_CB_DISTRO}
            else
                CB_KVMQEMU_BIMG_FN=cb_nullworkload_${_CB_DISTRO}
            fi
            cp -f $CB_KVMQEMU_BIMG_FN cb_${_CB_WKS}_${_CB_DISTRO}
            CMD="sudo -u $CB_USERNAME /home/$CB_USERNAME/cloudbench/install -r workload --wks ${_CB_WKS} --filestore $CB_RSYNC"
            echo "####### Creating workload image \"cb_${_CB_WKS}_${_CB_DISTRO}\" by executing the command \"$CMD\""
            sudo virt-customize -m 4096 -a cb_${_CB_WKS}_${_CB_DISTRO} $CB_VERB --run-command "$CMD"
            COUT=$?
            if [[ $COUT -ne 0 ]]
            then
                echo "############## ERROR: workload image \"cb_${_CB_WKS}_${_CB_DISTRO}\" failed while executing command \"$CMD\""
            else
                echo "############## INFO: workload image \"cb_${_CB_WKS}_${_CB_DISTRO}\" built successfully!!!" 
            fi 
            let ERROR+=$COUT
        done
    done

    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating workload images"
        exit $ERROR
    else
        echo "##### Done creating workload images"
    fi
    echo
    popd > /dev/null 2>&1    
}
export -f create_workload_images

function create_orchestrator_images {
    CB_DISTROS_LIST=$1

    if [[ $CB_DISTROS_LIST == "all" ]]
    then
        CB_DISTROS_LIST=ubuntu' 'centos
    fi

    echo "##### Creating orchestrator images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1

    for _CB_DISTRO in $CB_DISTROS_LIST
    do

        cp -f cb_base_${_CB_DISTRO} cb_orchestrator_${_CB_DISTRO}
        CMD="sudo -u $CB_USERNAME /home/$CB_USERNAME/cloudbench/install -r orchestrator"
        echo "####### Creating orchestrator image \"cb_orchestrator_${_CB_DISTRO}\" by executing the command \"$CMD\""
        sudo virt-customize -a cb_orchestrator_${_CB_DISTRO} $CB_VERB --run-command "$CMD"
        COUT=$?
        if [[ $COUT -ne 0 ]]
        then
            echo "############## ERROR: orchestrator image \"cb_orchestrator_${_CB_DISTRO}\" failed while executing command \"$CMD\""
        else
            echo "############## INFO: orchestrator image \"cb_orchestrator_${_CB_DISTRO}\" built successfully!!!"
        fi
        let ERROR+=$COUT
    done

    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating orchestrator images"
        exit $ERROR
    else
        echo "##### Done creating orchestrator images"
    fi
    echo
    popd > /dev/null 2>&1
}
export -f create_orchestrator_images
