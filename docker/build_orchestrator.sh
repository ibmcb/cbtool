#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_DOCKER_BASE_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

source $CB_DOCKER_BASE_DIR/build_common.sh

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -r|--repo)
        CB_REPO="$2"
        shift
        ;;
        -r=*|--repo=*)
        CB_REPO=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -u|--ubuntubase)
        CB_UBUNTU_BASE="$2"
        shift
        ;;
        -u=*|--ubuntubase=*)
        CB_UBUNTU_BASE=$(echo $key | cut -d '=' -f 2)
        shift
        ;;        
        -p|--phusionbase)
        CB_PHUSION_BASE="$2"
        shift
        ;;
        -c|--centosbase)
        CB_CENTOS_BASE="$2"
        shift
        ;;
        -c=*|--centosbase=*)
        CB_CENTOS_BASE=$(echo $key | cut -d '=' -f 2)
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
        -a|--arch)
        CB_ARCH="$2"
        shift
        ;;
        -a=*|--arch=*)
        CB_ARCH=$(echo $key | cut -d '=' -f 2)
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
        --rsync)
        CB_RSYNC="$2"
        shift
        ;;
        --rsync=*)
        CB_RSYNC=$(echo $key | cut -d '=' -f 2)
        shift
        ;;                     
        -v|--verbose)
        CB_VERB='--ve'
        ;;
        -m|--multiarch)
        CB_MULTIARCH=1
        ;;        
        --push)
        CB_PUSH="push"
        ;;
        --psall)
        CB_PUSH="push"
        CB_PALL=1
        ;;
        -f|--force)
        CB_FORCE_REBUILD=1
        ;;        
        -h|--help)
        echo $CB_USAGE
        exit 0        
        shift
        ;;
        *)
                # unknown option
        ;;
        esac
        shift
done

cb_refresh_vanilla_images $CB_UBUNTU_BASE $CB_CENTOS_BASE
cb_build_base_images $CB_REPO $CB_VERB $CB_USERNAME $CB_ARCH $CB_RSYNC $CB_MULTIARCH
#cb_remove_images $CB_REPO orchestrator $CB_BRANCH
cb_build_orchestrator $CB_REPO $CB_VERB $CB_USERNAME $CB_ARCH $CB_RSYNC $CB_BRANCH $CB_MULTIARCH
#cb_remove_images $CB_REPO installtest $CB_BRANCH
cb_build_installtest $CB_REPO $CB_VERB $CB_USERNAME $CB_ARCH $CB_RSYNC $CB_BRANCH $CB_MULTIARCH

if [[ $CB_PUSH == "push" ]]
then
    cb_push_images $CB_REPO $CB_VERB $CB_PALL orchestrator $CB_BRANCH
fi
