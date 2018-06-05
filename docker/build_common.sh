#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_DOCKER_BASE_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

CB_REPO=cloudbench-docker-local.artifactory.swg-devops.com
CB_WKS="ALL"
CB_RSYNC_ADDR=$(sudo ifconfig docker0 | grep "inet " | awk '{ print $2 }' | sed 's/addr://g')
for pi in $(sudo netstat -puntel | grep rsync | grep tcp[[:space:]] | awk '{ print $9 }' | sed 's^/rsync^^g')
do
    if [[ $(echo $(sudo ps aux | grep $pi | grep -c $(whoami)_rsync.conf)) -ne 0 ]]
    then
        CB_RSYNC_PORT=$(sudo netstat -puntel | grep $pi | awk '{ print $4 }' | cut -d ':' -f 2)
    break
    fi
done
CB_RSYNC=$CB_RSYNC_ADDR:${CB_RSYNC_PORT}/$(whoami)_cb
CB_UBUNTU_BASE=ubuntu:16.04
CB_PHUSION_BASE=phusion/baseimage:latest
CB_CENTOS_BASE=centos:latest
CB_VERB="-q"
CB_PUSH="nopush"
CB_ARCH=$(uname -a | awk '{ print $12 }')
CB_PALL=0
CB_USERNAME="cbuser"
CB_MYUSERNAME=$(whoami)
CB_MYUID=$(id -u $(whoami))
CB_MYGID=$(id -g $(whoami))
CB_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CB_USAGE="Usage: $0 [-r <repository>] [-u Ubuntu base image] [-p Phusion base image] [-c Centos base image] [-w Workload] [-l CB Username/login] [-b branch] [--verbose] [--push] [--psall]"

function cb_docker_build {
    _CB_REPOSITORY=$1
    _CB_VERBQUIET=$2    
    _CB_DOCKERFN=$3
    _CB_BRANCH=$4     
    _CB_USERNAME=$5 
    _CB_ARCH=$6
    _CB_RSYNC=$7
    _CB_FATAL=$8
    _CB_SQUASH=$9

    if [[ ${_CB_ARCH} == "x86_64" ]]
    then
        CB_ARCH1=x86_64
        CB_ARCH2=x86-64
        CB_ARCH3=amd64
    elif [[ ${_CB_ARCH} == "ppc64le" ]]
    then
        CB_ARCH1=ppc64le
        CB_ARCH2=ppc64
        CB_ARCH3=ppc64
    else
        CB_ARCH1=$CB_ARCH
        CB_ARCH2=$CB_ARCH
        CB_ARCH3=$CB_ARCH
    fi                     

    CB_ACTUAL_SQUASH=''
    if [[ ! -z ${_CB_SQUASH} ]]
    then
        if [[ ${_CB_SQUASH} == "true" ]]
        then
#            CB_ACTUAL_SQUASH="--squash"
            CB_ACTUAL_SQUASH=""
        fi
    fi                                                                                                                                                                                                                        
    sudo rm -rf Dockerfile && sudo cp -f ${_CB_DOCKERFN} Dockerfile

    sudo sed -i "s^REPLACE_USERNAME^${_CB_USERNAME}^g" Dockerfile    
            
    CB_DNAME=$(echo ${_CB_DOCKERFN} | sed 's/Dockerfile-//g')

    sudo sed -i "s^REPLACE_BRANCH^${_CB_BRANCH}^g" Dockerfile

    sudo sed -i "s^REPLACE_ARCH1^$CB_ARCH1^g" Dockerfile
    sudo sed -i "s^REPLACE_ARCH2^$CB_ARCH2^g" Dockerfile
        
    sudo sed -i "s^REPLACE_BASE_VANILLA_UBUNTU^$CB_UBUNTU_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_VANILLA_PHUSION^$CB_PHUSION_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_VANILLA_CENTOS^$CB_CENTOS_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_RSYNC^rsync -a rsync://${_CB_RSYNC}/3rd_party/workload/^g" Dockerfile
                
    if [[ ! -z $CB_DNAME_BASE_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_BASE_UBUNTU^${_CB_REPOSITORY}/$CB_DNAME_BASE_UBUNTU^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_BASE_PHUSION ]]
    then    
        sudo sed -i "s^REPLACE_BASE_PHUSION^${_CB_REPOSITORY}/$CB_DNAME_BASE_PHUSION^g" Dockerfile
    fi
    
    if [[ ! -z $CB_DNAME_BASE_CENTOS ]]
    then        
        sudo sed -i "s^REPLACE_BASE_CENTOS^${_CB_REPOSITORY}/$CB_DNAME_BASE_CENTOS^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_NULLWORKLOAD_UBUNTU^${_CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_UBUNTU:${_CB_BRANCH}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_PHUSION ]]
    then      
        sudo sed -i "s^REPLACE_NULLWORKLOAD_PHUSION^${_CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_PHUSION:${_CB_BRANCH}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_CENTOS ]]
    then          
        sudo sed -i "s^REPLACE_NULLWORKLOAD_CENTOS^${_CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_CENTOS:${_CB_BRANCH}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_PREREQS_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_PREREQS_UBUNTU^${_CB_REPOSITORY}/$CB_DNAME_PREREQS_UBUNTU^g" Dockerfile
    fi
    
    if [[ ! -z $CB_DNAME_PREREQS_CENTOS ]]
    then        
        sudo sed -i "s^REPLACE_PREREQS_CENTOS^${_CB_REPOSITORY}/$CB_DNAME_PREREQS_CENTOS^g" Dockerfile
    fi

    sudo cp -f Dockerfile ${_CB_DOCKERFN}._processed_    
            
    CB_ACTUAL_VERBQUIET=$(echo ${_CB_VERBQUIET} | sed 's/--ve//g')
    CB_DOCKER_CMD="sudo docker build -t ${_CB_REPOSITORY}/$CB_DNAME:${_CB_BRANCH} $CB_ACTUAL_VERBQUIET $CB_ACTUAL_SQUASH ."
    echo "########## Building image ${_CB_REPOSITORY}/$CB_DNAME by executing the command \"$CB_DOCKER_CMD\" ..."
    $CB_DOCKER_CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "############## ERROR: Image \"${_CB_REPOSITORY}/$CB_DNAME\" failed while executing command \"$CB_DOCKER_CMD\""
        sudo rm -rf Dockerfile
        if [[ ${_CB_FATAL} == "true" ]]
        then
            exit 1
        else
            echo "############## WARNING: Image \"${_CB_REPOSITORY}/$CB_DNAME\" will not be available for deployment!!!"
            sleep 5
        fi
    else
        echo "############## INFO: Image \"${_CB_REPOSITORY}/$CB_DNAME\" built successfully!!!" 
    fi
    sudo rm -rf Dockerfile
}
export -f cb_docker_build

function cb_build_orchprereqs {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
                            
    echo "##### Building Docker orchestrator images"
    pushd orchprereqs > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        
        CB_DNAME=$(echo $CB_DFILE | sed 's/Dockerfile-//g')
        
        echo $CB_DNAME | grep ubuntu > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_PREREQS_UBUNTU=$CB_DNAME
        fi

        echo $CB_DNAME | grep centos > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_PREREQS_CENTOS=$CB_DNAME
        fi        
        
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE latest $CB_USERNAME $CB_ARCH $CB_RSYNC true
    done
    echo "##### Done building Docker orchestrator images"
    echo
    popd > /dev/null 2>&1    
}
export -f cb_build_orchprereqs

function cb_build_orchestrator {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
    CB_BRANCH=$6

    echo "##### Building Docker orchestrator images"
    pushd orchestrator > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true
    done
    echo "##### Done building Docker orchestrator images"
    echo
    popd > /dev/null 2>&1    
}
export -f cb_build_orchestrator

function cb_build_installtest {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
    CB_BRANCH=$6
                            
    echo "##### Building Docker orchestrator images"
    pushd installtest > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true
    done
    echo "##### Done building Docker orchestrator images"
    echo
    popd > /dev/null 2>&1    
}
export -f cb_build_installtest

function cb_refresh_vanilla_images {
    CB_BUIM=$1
    CB_BPIM=$2
    CB_BCIM=$3

    sudo docker pull $CB_BUIM
    sudo docker pull $CB_BPIM
    sudo docker pull $CB_BCIM            
}
export -f cb_refresh_vanilla_images

function cb_build_base_images {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
                      
    echo "##### Building Docker base images"
    pushd base > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        CB_DNAME=$(echo $CB_DFILE | sed 's/Dockerfile-//g')
        
        echo $CB_DNAME | grep ubuntu > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_BASE_UBUNTU=$CB_DNAME
        fi

        echo $CB_DNAME | grep phusion > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_BASE_PHUSION=$CB_DNAME
        fi

        echo $CB_DNAME | grep centos > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_BASE_CENTOS=$CB_DNAME
        fi

        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE latest $CB_USERNAME $CB_ARCH $CB_RSYNC true false
    done
    echo "##### Done building Docker base images"
    echo
    popd > /dev/null 2>&1
}
export -f cb_build_base_images

function cb_build_nullworkloads {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
    CB_BRANCH=$6
                
    echo "##### Building Docker nullworkload images"
    pushd workload > /dev/null 2>&1
    sudo rm -rf Dockerfile        
    for CB_DFILE in $(ls Dockerfile*nullworkload | grep -v _processed_)
    do

        CB_DNAME=$(echo $CB_DFILE | sed 's/Dockerfile-//g')

        echo $CB_DNAME | grep ubuntu > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_NULLWORKLOAD_UBUNTU=$CB_DNAME
        fi

        echo $CB_DNAME | grep phusion > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_NULLWORKLOAD_PHUSION=$CB_DNAME
        fi

        echo $CB_DNAME | grep centos > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_NULLWORKLOAD_CENTOS=$CB_DNAME
        fi                
                                                
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true true
    done
    echo "##### Done building Docker nullworkload images"
    echo
    popd > /dev/null 2>&1
}
export -f cb_build_nullworkloads

function cb_build_workloads {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_WORKLOAD=$5
    CB_RSYNC=$6
    CB_BRANCH=$7
    
    if [[ $CB_WORKLOAD == "ALL" ]]
    then
        CB_WORKLOAD=''
    fi

    pushd workload > /dev/null 2>&1
    sudo rm -rf Dockerfile
    echo "##### Building the rest of the Docker workload images"
    for CB_DFILE in $(ls Dockerfile*${CB_WORKLOAD} | grep -v nullworkload | grep -v _processed_ | grep -v ignore)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC false false
    done
    echo "##### Done building the rest of the Docker workload images"
    popd > /dev/null 2>&1
}
export -f cb_build_workloads
    
function cb_push_images {
    CB_REPOSITORY=$1
    CB_PUSHALL=$2
    CB_IMGTYPE=$3
    CB_BRANCH=$4
    
    if [[ -z $3 ]]
    then
        CB_IMGTYPE=$2
    fi

    if [[ -z $4 ]]
    then
        CB_BRANCH=""
    else
        CB_BRANCH=":"$CB_BRANCH 
    fi
            
    if [[ $CB_IMGTYPE == "orchestrator" ]]
    then
        CB_IMG_GREP_CMD="grep $CB_IMGTYPE"
    fi
    
    if [[ $CB_IMGTYPE == "workload" ]]
    then
        CB_IMG_GREP_CMD="grep -v orchestrator"
    fi    

    echo "##### Pushing all images to Docker repository"
    for IMG in $(docker images | grep ${CB_REPOSITORY} | $CB_IMG_GREP_CMD | awk '{ print $1 }')
    do
        if [[ $CB_BRANCH != ""  ]]
        then
            CMD="docker tag ${IMG}${CB_BRANCH} ${IMG}:latest"
            echo "########## Tagging image ${IMG}${CB_BRANCH} by executing the command \"$CMD\" ..."             
            $CMD            
        fi
        echo $IMG | grep coremark
        NOT_COREMARK=$?
        echo $IMG | grep linpack
        NOT_LINPACK=$?
        echo $IMG | grep parboil
        NOT_PARBOIL=$?
        echo $IMG | grep spec
        NOT_SPEC=$?
        echo $IMG | grep caffe
        NOT_CAFFE=$?
        echo $IMG | grep rubis
        NOT_RUBIS=$?
        echo $IMG | grep rubbos
        NOT_RUBBOS=$?
        echo $IMG | grep acmeair
        NOT_ACMEAIR=$?
        echo $IMG | grep spark
        NOT_SPARK=$?  
        if [[ $NOT_COREMARK -eq 1 && $NOT_LINPACK -eq 1 && $NOT_PARBOIL -eq 1 && $NOT_SPEC -eq 1 && $NOT_CAFFE -eq 1 && $NOT_RUBIS -eq 1 && $NOT_RUBBOS -eq 1 && $NOT_ACMEAIR -eq 1 && $NOT_SPARK -eq 1 || $CB_PUSHALL -eq 1 ]]
        then
            CMD="docker push ${IMG}${CB_BRANCH}"
            echo "########## Pushing image ${IMG}${CB_BRANCH} by executing the command \"$CMD\" ..."             
            $CMD
            if [[ $CB_BRANCH != ""  ]]
            then
                CMD="docker push ${IMG}:latest"
                echo "########## Pushing image ${IMG}:latest by executing the command \"$CMD\" ..."             
                $CMD            
            fi            
        fi
    done
    echo "##### Images to Docker repository"    
}

function cb_remove_images {
    CB_REPOSITORY=$1
    CB_IMG_CLASS=$2
    CB_BRANCH=$3
    
    for img in $(sudo docker images | grep $CB_REPO | grep $CB_IMG_CLASS | grep $CB_BRANCH | awk '{ print $3 }')
    do
        sudo docker rmi -f $img
    done
}
