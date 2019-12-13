#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_DOCKER_BASE_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

source $CB_DOCKER_BASE_DIR/build_common.sh
CB_ORCH=0
CB_WKS=0
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
        -w|--workload)
        CB_WKS="$2"
        shift
        ;;        
        -w=*|--workload=*)
        CB_WKS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -o|--orchestrator)
        CB_ORCH=1
        ;;
        -h|--help)
        echo $0 [-w] [-o]
        exit 0        
        shift
        ;;
        *)
                # unknown option
        ;;
        esac
        shift
done

CB_MULTI_ARCH_LIST="amd64 ppc64le arm64"

CB_MY_DOCKER_ARCH=$(dpkg --print-architecture | sed s'/ppc64el/ppc64le/g')
if [[ $CB_ORCH -eq 1 ]]
then
#    curr_docker_img_list=$(docker images | grep $CB_REPO | grep -v installtest | grep latest | grep orchestrator | grep -v "<none>" | grep $CB_MY_DOCKER_ARCH | awk '{ print $1 }')
	curr_docker_img_list=$(ls $CB_DOCKER_BASE_DIR/orchestrator/* | grep -v processed | grep Dockerfile | sed "s^$CB_DOCKER_BASE_DIR/orchestrator/^^g" | sed "s^Dockerfile-^$CB_REPO^g" | sed ":a;N;\$!ba;s/\n/-$CB_MY_DOCKER_ARCH\n/g")"-"$CB_MY_DOCKER_ARCH
else 
    if [[ $CB_WKS == "ALL" || $CB_WKS == "all" ]]
    then
#        curr_docker_img_list=$(docker images | grep $CB_REPO | grep -v installtest | grep latest | grep -v orchestrator | grep -v "<none>" | grep $CB_MY_DOCKER_ARCH | awk '{ print $1 }')
		curr_docker_img_list=$(ls $CB_DOCKER_BASE_DIR/workload/* | grep -v processed | sed "s^$CB_DOCKER_BASE_DIR/workload/^^g" | sed "s^Dockerfile-^$CB_REPO^g" | sed ":a;N;\$!ba;s/\n/-$CB_MY_DOCKER_ARCH\n/g")"-"$CB_MY_DOCKER_ARCH
    else
#        curr_docker_img_list=$(docker images | grep $CB_REPO | grep -v installtest | grep latest | grep $CB_WKS | grep -v orchestrator | grep -v "<none>" | grep $CB_MY_DOCKER_ARCH | awk '{ print $1 }')
		curr_docker_img_list=$(ls $CB_DOCKER_BASE_DIR/workload/* | grep $CB_WKS | grep -v processed | sed "s^$CB_DOCKER_BASE_DIR/workload/^^g" | sed "s^Dockerfile-^$CB_REPO^g")"-"$CB_MY_DOCKER_ARCH
    fi
fi

echo "####### pulling images from from \"$CB_REPO\"..."
for curr_img in $(echo "$curr_docker_img_list")
do
    curr_arch=$(echo "$curr_img" | rev | cut -d '-' -f 1 | rev)
    curr_img_name=$(echo "$curr_img" | sed "s/-$curr_arch//g")
    sudo ls ~/.docker/manifests/ | grep $(echo $curr_img_name | sed 's^/^_^g') >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        echo "####### deleting already existing manifest for multi-arch image \"$curr_img_name\"..."
        docker manifest push --purge ${curr_img_name}
    fi
    CB_DOCKER_MANIFEST_CREATE_CMD="sudo docker manifest create $curr_img_name --amend"
    CB_DOCKER_MANIFEST_ANNOTATE_CMD=""
    for arch in $(echo $CB_MULTI_ARCH_LIST)
    do
        echo "########## pulling image \"$curr_img_name\" for \"$arch\"  from from \"$CB_REPO\"..."
        docker pull ${curr_img_name}-${arch} >/dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            CB_DOCKER_MANIFEST_CREATE_CMD="$CB_DOCKER_MANIFEST_CREATE_CMD ${curr_img_name}-${arch}"
            CB_DOCKER_MANIFEST_ANNOTATE_CMD="$CB_DOCKER_MANIFEST_ANNOTATE_CMD docker manifest annotate $curr_img_name ${curr_img_name}-${arch} --arch ${arch}; " 
        fi
    done
    
    echo "####### building manifest for multi-arch image \"$curr_img_name\" with command \"$CB_DOCKER_MANIFEST_CREATE_CMD\"..."
    bash -c "$CB_DOCKER_MANIFEST_CREATE_CMD"
    if [[ $? -ne 0 ]]
    then
        exit 1
    fi    

    echo "####### annotating manifest for multi-arch image \"$curr_img_name\" with command \"$CB_DOCKER_MANIFEST_ANNOTATE_CMD\"..."
    bash -c "$CB_DOCKER_MANIFEST_ANNOTATE_CMD"

    echo "####### pushing manifest for multi-arch image \"$curr_img_name\"..."    
    docker manifest push $curr_img_name
done
