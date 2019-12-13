#!/usr/bin/env bash

source ./build_common.sh

CB_USAGE="Usage: $0 -r built image location [-w Workload] [-l CB Username/login] [-b branch] [-o distros] [--noskip] [--verbose] [--allinone] [--preserve] [--ubuntubi <filename or url>] [--centosbi <filename or url>]"

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
        --noskip)
        CB_BASE_IMAGE_SKIP=0
        CB_NULLWORKLOAD_IMAGE_SKIP=0
        ;;                                                 
        -v|--verbose)
        CB_VERB='-v'
        ;;
        --allinone)
        CB_ALLINONE=1
        ;;
        --preserve)
        CB_PRESERVE_ON_ERROR=1
        ;;
        --ubuntubi)
        CB_KVMQEMU_UBUNTU_BASE="$2"
        shift
        ;;
        --ubuntubi=*)
        CB_KVMQEMU_CENTOS_BASE=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        --centosbi)
        CB_KVMQEMU_CENTOS_BASE="$2"
        shift
        ;;
        --centosbi=*)
        CB_KVMQEMU_UBUNTU_BASE=$(echo $key | cut -d '=' -f 2)
        shift        
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

cat $CB_KVMQEMU_S_DIR/../util/workloads_alias_mapping.txt | awk '{ print $1 }' | grep ^${CB_WKS}$ > /dev/null 2>&1
if [[ $? -eq 0 ]]
then
    CB_WKS=$(cat $CB_KVMQEMU_S_DIR/../util/workloads_alias_mapping.txt | grep $CB_WKS[[:space:]] | cut -d ' ' -f 2)
fi

download_base_images
create_base_images
create_workload_images nullworkload $CB_DISTROS

if [[ $(echo $CB_WKS | grep -c none) -eq 0 ]]
then 
    create_workload_images $CB_WKS $CB_DISTROS
fi
