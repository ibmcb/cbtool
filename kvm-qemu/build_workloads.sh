#!/usr/bin/env bash

CB_KVMQEMU_BIMG_DIR=NONE
CB_KVMQEMU_UBUNTU_BASE=https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img
CB_KVMQEMU_CENTOS_BASE=https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
CB_DISTROS="ubuntu"
CB_USERNAME="cbuser"
CB_BRANCH="experimental"
CB_WKS="all"
CB_VERB=''
CB_BASE_IMAGE_SKIP=0

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_KVMQEMU_S_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

CB_USAGE="Usage: $0 -r built image location [-w Workload] [-l CB Username/login] [-b branch] [-o distros] [--skip] [--verbose]"

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -r|--repo)
        CB_KVMQEMU_BIMG_DIR="$2"
        shift
        ;;
        -r=*|--repo=*)
        CB_KVMQEMU_BIMG_DIR=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -w|--workload)
        CB_WKS="$2"
        shift
        ;;        
        -w=*|--workload=*)
        CB_WKS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -l|--login)
        CB_USERNAME="$2"
        shift
        ;;
        -l=*|--login=*)
        CB_USERNAME=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -b|--branch)
        CB_BRANCH="$2"
        shift
        ;;
        -b=*|--branch=*)
        CB_BRANCH=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -o|--osdistros)
        CB_DISTROS="$2"
        shift
        ;;
        -o=*|--osdistros=*)
        CB_DISTROS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        --rsync)
        CB_RSYNC="$2"
        shift
        ;;
        --rsync=*)
        CB_RSYNC=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        --skip)
        CB_BASE_IMAGE_SKIP=1
        ;;                                                 
        -v|--verbose)
        CB_VERB='-v'
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

if [[ $CB_KVMQEMU_BIMG_DIR == "NONE" ]]
then
    echo $CB_USAGE
    exit 1
fi

if [[ $CB_DISTROS == "ubuntu" ]]
then
    CB_KVMQEMU_DISTROS_IMG_LIST=$CB_KVMQEMU_UBUNTU_BASE
elif [[ $CB_DISTROS == "centos" ]]
then
    CB_KVMQEMU_DISTROS_IMG_LIST=$CB_KVMQEMU_CENTOS_BASE
elif [[ $CB_DISTROS == "all" ]]
then
    CB_KVMQEMU_DISTROS_IMG_LIST=$CB_KVMQEMU_UBUNTU_BASE' '$CB_KVMQEMU_CENTOS_BASE
fi

function download_base_images {
    echo "##### Downloading latest version of the vanilla cloud images"
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1
    for CB_KVMQEMU_IMG in $CB_KVMQEMU_DISTROS_IMG_LIST
    do
        wget -N $CB_KVMQEMU_IMG        
    done
    echo "##### Done downloading the latest version of the vanilla cloud images"
    echo
    popd > /dev/null 2>&1    
}

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
        cp -f $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
        cp -f $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        sudo sed -i "s^REPLACE_USERNAME^${CB_USERNAME}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        sudo sed -i "s^REPLACE_BRANCH^${CB_BRANCH}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
        virt-customize -a cb_base_${CB_KVMQEMU_BIMG} $CB_VERB --commands-from-file $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
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
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep ${_CB_DISTRO} | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        else
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep $CB_WKS_LIST | grep ${_CB_DISTRO} | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        fi
        
        for _CB_WKS in $CB_WKS_LIST
        do    
            CB_KVMQEMU_BIMG_FN=cb_base_${_CB_DISTRO}
            cp -f $CB_KVMQEMU_BIMG_FN cb_${_CB_WKS}
            echo "####### Creating workload image \"${_CB_WKS}\" by executing the command \"cd /home/$CB_USERNAME/cbtool; ./install -r workload --wks ${_CB_WKS}\""
            virt-customize -a cb_${_CB_WKS} $CB_VERB --run-command "cd /home/$CB_USERNAME/cbtool; ./install -r workload --wks ${_CB_WKS}"
            COUT=$?
            if [[ $COUT -ne 0 ]]
            then
                echo "############## ERROR: workload image \"${_CB_WKS}\" failed while executing command \"cd /home/$CB_USERNAME/cbtool; ./install -r workload --wks ${_CB_WKS}\""
            else
                echo "############## INFO: workload image \"${_CB_WKS}\" built successfully!!!" 
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
    
if [[ $CB_BASE_IMAGE_SKIP -eq 0 ]]
then
    download_base_images
    create_base_images
fi

create_workload_images $CB_WKS $CB_DISTROS