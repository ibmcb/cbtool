#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_DOCKER_BASE_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

CB_REPO=${CB_REPO:-"ibmcb/"}
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

if [[ -z $CB_RSYNC_PORT ]]
then
    CB_RSYNC_PORT=25001
    echo "No rsync server detected, creating one on port $CB_RSYNC_PORT"
    CB_RSYNC_CONF=~/private_rsync
    eval CB_RSYNC_CONF=${CB_RSYNC_CONF}
    sudo mkdir -p $CB_RSYNC_CONF
    sudo chown -R $(whoami):$(whoami) $CB_RSYNC_CONF
    cat <<EOF > $CB_RSYNC_CONF/$(whoami)_rsync.conf
port=$CB_RSYNC_PORT
lock file=$CB_RSYNC_CONF/$(whoami)_rsync.lock
log file=/var/log/$(whoami)_rsyncd.log
pid file=$CB_RSYNC_CONF/$(whoami)_rsyncd.pid
[$(whoami)_cb]
    path=$CB_DOCKER_BASE_DIR/..
    uid=$(whoami)
    gid=$(whoami)
    read only=no
    list=yes
EOF
    sudo rsync --daemon --config ${CB_RSYNC_CONF}/$(whoami)_rsync.conf
fi

#CB_CACHE_OLD_JDK_DIR=$CB_DOCKER_BASE_DIR/../3rd_party/workload/openjdk7/
#mkdir $CB_CACHE_OLD_JDK_DIR
#wget -N -q -P $CB_CACHE_OLD_JDK_DIR http://ftp.us.debian.org/debian/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_1.5.2-2+b1_$(uname -m | sed 's/x86_64/amd64/g').deb
#wget -N -q -P $CB_CACHE_OLD_JDK_DIR http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre-headless_7u161-2.6.12-1_$(uname -m | sed 's/x86_64/amd64/g').deb
#wget -N -q -P $CB_CACHE_OLD_JDK_DIR http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jre_7u161-2.6.12-1_$(uname -m | sed 's/x86_64/amd64/g').deb
#wget -N -q -P $CB_CACHE_OLD_JDK_DIR http://ftp.us.debian.org/debian/pool/main/o/openjdk-7/openjdk-7-jdk_7u161-2.6.12-1_$(uname -m | sed 's/x86_64/amd64/g').deb

CB_RSYNC=$CB_RSYNC_ADDR:${CB_RSYNC_PORT}/$(whoami)_cb
echo "##### Testing rsync server on $CB_RSYNC..." 
rsync -a rsync://${CB_RSYNC}/util/cbssh.sh > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    echo "Error while testing rsync server"
    exit 1
else
    echo "##### rsync server was found on ${CB_RSYNC}"  
fi

CB_UBUNTU_BASE=ubuntu:18.04
CB_CENTOS_BASE=centos:7
CB_VERB="-q"
CB_PUSH="nopush"
CB_ARCH=$(uname -a | awk '{ print $12 }')
CB_PALL=0
CB_MULTIARCH=0
CB_USERNAME="cbuser"
CB_MYUSERNAME=$(whoami)
CB_MYUID=$(id -u $(whoami))
CB_MYGID=$(id -g $(whoami))
if [[ -z $CB_BRANCH ]]
then
    CB_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>&1)
    if [[ $? -ne 0 ]]
    then
        CB_BRANCH="experimental"
    fi
fi
CB_FORCE_REBUILD=0
CB_USAGE="Usage: $0 [-r <repository>] [-u Ubuntu base image] [-c Centos base image] [-w Workload] [-l CB Username/login] [-b branch] [--verbose] [--multiarch] [--push] [--psall] [-f]"

function cb_docker_build {
    _CB_REPOSITORY=$1
    _CB_VERBQUIET=$2
    _CB_DOCKERFN=$3
    _CB_BRANCH=$(echo $4 | sed 's/://g')
    _CB_USERNAME=$5
    _CB_ARCH=$6
    _CB_RSYNC=$7
    _CB_FATAL=$8
    _CB_SQUASH=$9
    _CB_MULTIARCH=${10}
    _CB_DROPBOX=${11}
    
    if [[ ${_CB_ARCH} == "x86_64" ]]
    then
        CB_ARCH1=x86_64
        CB_ARCH2=x86-64
        CB_ARCH3=amd64
        CB_ARCH4=x64
        CB_ARCH5=amd64
    elif [[ ${_CB_ARCH} == "ppc64le" ]]
    then
        CB_ARCH1=ppc64le
        CB_ARCH2=ppc64
        CB_ARCH3=ppc64el
        CB_ARCH4=ppc64le
        CB_ARCH5=ppc64le      
    else
        CB_ARCH1=$CB_ARCH
        CB_ARCH2=$CB_ARCH
        CB_ARCH3=$CB_ARCH
        CB_ARCH4=$CB_ARCH
        CB_ARCH5=$CB_ARCH        
    fi

    CB_ACTUAL_SQUASH=''
    if [[ ${_CB_SQUASH} == "true" ]]
    then
#       CB_ACTUAL_SQUASH="--squash"
        CB_ACTUAL_SQUASH=""
    fi

    sudo rm -rf Dockerfile && sudo cp -f ${_CB_DOCKERFN} Dockerfile

    sudo sed -i "s^REPLACE_USERNAME^${_CB_USERNAME}^g" Dockerfile

    if [[ ! -z ${_CB_DROPBOX} ]]
    then
        sudo sed -i "s^REPLACE_DROPBOX^${_CB_DROPBOX}^g" Dockerfile
    fi

    CB_DNAME=$(echo ${_CB_DOCKERFN} | sed 's/Dockerfile-//g')

    sudo sed -i "s^REPLACE_ARCH1^${CB_ARCH1}^g" Dockerfile
    sudo sed -i "s^REPLACE_ARCH2^${CB_ARCH2}^g" Dockerfile        
    sudo sed -i "s^REPLACE_ARCH3^${CB_ARCH3}^g" Dockerfile
    sudo sed -i "s^REPLACE_ARCH4^${CB_ARCH4}^g" Dockerfile

    sudo sed -i "s/-ARCH${CB_ARCH1}//g" Dockerfile
    sudo sed -i "s/-ARCH${CB_ARCH2}//g" Dockerfile    
    sudo sed -i "s/-ARCH${CB_ARCH3}//g" Dockerfile
    sudo sed -i "s/-ARCH${CB_ARCH4}//g" Dockerfile
                
    sudo sed -i "/-ARCH/,/-ARCH/d" Dockerfile

    sudo sed -i "s^____^ ^g" Dockerfile
    sudo sed -i "s^REPLACE_BRANCH^${_CB_BRANCH}^g" Dockerfile

    sudo sed -i "s^REPLACE_BASE_VANILLA_UBUNTU^${CB_UBUNTU_BASE}^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_VANILLA_CENTOS^${CB_CENTOS_BASE}^g" Dockerfile
    sudo sed -i "s^REPLACE_RSYNC_DOWNLOAD^rsync -a rsync://${_CB_RSYNC}/ --exclude 3rd_party/workload/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/^g" Dockerfile        
    sudo sed -i "s^REPLACE_RSYNC^rsync -a rsync://${_CB_RSYNC}/3rd_party/workload/^g" Dockerfile

    sudo sed -i "s^apt-get update^apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update^g" Dockerfile

    if [[ ${_CB_MULTIARCH} -eq 1 ]]
    then
        CB_ARCH_TAG_SUFFIX="-${CB_ARCH5}"
    else
        CB_ARCH_TAG_SUFFIX=""
    fi
    
    if [[ ! -z $CB_DNAME_BASE_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_BASE_UBUNTU^${_CB_REPOSITORY}${CB_DNAME_BASE_UBUNTU}${CB_ARCH_TAG_SUFFIX}^g" Dockerfile
    fi
    
    if [[ ! -z $CB_DNAME_BASE_CENTOS ]]
    then        
        sudo sed -i "s^REPLACE_BASE_CENTOS^${_CB_REPOSITORY}${CB_DNAME_BASE_CENTOS}${CB_ARCH_TAG_SUFFIX}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_NULLWORKLOAD_UBUNTU^${_CB_REPOSITORY}${CB_DNAME_NULLWORKLOAD_UBUNTU}${CB_ARCH_TAG_SUFFIX}:${_CB_BRANCH}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_CENTOS ]]
    then          
        sudo sed -i "s^REPLACE_NULLWORKLOAD_CENTOS^${_CB_REPOSITORY}${CB_DNAME_NULLWORKLOAD_CENTOS}${CB_ARCH_TAG_SUFFIX}:${_CB_BRANCH}^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_PREREQS_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_PREREQS_UBUNTU^${_CB_REPOSITORY}$CB_DNAME_PREREQS_UBUNTU^g" Dockerfile
    fi
    
    if [[ ! -z $CB_DNAME_PREREQS_CENTOS ]]
    then        
        sudo sed -i "s^REPLACE_PREREQS_CENTOS^${_CB_REPOSITORY}$CB_DNAME_PREREQS_CENTOS^g" Dockerfile
    fi

    sudo cp -f Dockerfile ${_CB_DOCKERFN}._processed_    
            
    CB_ACTUAL_VERBQUIET=$(echo ${_CB_VERBQUIET} | sed 's/--ve//g')
    if [[ $CB_FORCE_REBUILD -eq 1 ]]
    then
        sudo docker rmi -f ${_CB_REPOSITORY}$CB_DNAME:${_CB_BRANCH}
    fi
    
    CB_DOCKER_CMD="sudo docker build --build-arg CLOUDBENCH_VERSION=$(date +%Y%m%d-%H%M%S) -t ${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}:${_CB_BRANCH} $CB_ACTUAL_VERBQUIET $CB_ACTUAL_SQUASH ."
    echo "########## Building image ${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX} by executing the command \"$CB_DOCKER_CMD\" ..."
    $CB_DOCKER_CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "############## ERROR: Image \"${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}\" failed while executing command \"$CB_DOCKER_CMD\""
        sudo rm -rf Dockerfile
        if [[ ${_CB_FATAL} == "true" ]]
        then
            exit 1
        else
            echo "############## WARNING: Image \"${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}\" will not be available for deployment!!!"
            sudo cat /tmp/cb_docker_failed | grep "${_CB_REPOSITORY}$CB_DNAME:${_CB_BRANCH}" > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then
                echo "${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}:${_CB_BRANCH}" >> /tmp/cb_docker_failed
            fi
            sleep 5
        fi
    else
        echo "############## INFO: Image \"${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}\" built successfully!!!"
        sudo sed -i "s^${_CB_REPOSITORY}${CB_DNAME}${CB_ARCH_TAG_SUFFIX}:${_CB_BRANCH}^^g" /tmp/cb_docker_failed > /dev/null 2>&1  
    fi
    sudo rm -rf Dockerfile
}
export -f cb_docker_build

function cb_build_orchestrator {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
    CB_BRANCH=$6
    CB_MULTIARCH=$7

    echo "##### Building Docker orchestrator images"
    pushd orchestrator > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true false $CB_MULTIARCH $CB_DROPBOX
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
    CB_MULTIARCH=$7
                                
    echo "##### Building Docker orchestrator images"
    pushd installtest > /dev/null 2>&1
    sudo rm -rf Dockerfile
    for CB_DFILE in $(ls Dockerfile* | grep -v _processed_)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true false $CB_MULTIARCH $CB_DROPBOX
    done
    echo "##### Done building Docker orchestrator images"
    echo
    popd > /dev/null 2>&1    
}
export -f cb_build_installtest

function cb_refresh_vanilla_images {
    CB_BUIM=$1
    CB_BCIM=$2

    sudo docker pull $CB_BUIM
    sudo docker pull $CB_BCIM
}
export -f cb_refresh_vanilla_images

function cb_build_base_images {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2
    CB_USERNAME=$3
    CB_ARCH=$4
    CB_RSYNC=$5
    CB_MULTIARCH=$6

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

        echo $CB_DNAME | grep centos > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_BASE_CENTOS=$CB_DNAME
        fi

        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE latest $CB_USERNAME $CB_ARCH $CB_RSYNC true false $CB_MULTIARCH $CB_DROPBOX
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
    CB_MULTIARCH=$7

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

        echo $CB_DNAME | grep centos > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            export CB_DNAME_NULLWORKLOAD_CENTOS=$CB_DNAME
        fi                
                                                
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true true $CB_MULTIARCH $CB_DROPBOX
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
    CB_MULTIARCH=$8

    if [[ $CB_WORKLOAD == "ALL" ]]
    then
        CB_WORKLOAD=''
    fi

    pushd workload > /dev/null 2>&1
    sudo rm -rf Dockerfile
    echo "##### Building the rest of the Docker workload images"
    for CB_DFILE in $(ls Dockerfile*${CB_WORKLOAD} | grep -v nullworkload | grep -v _processed_ | grep -v ignore)
    do
        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC false false $CB_MULTIARCH $CB_DROPBOX
    done
    echo "##### Done building the rest of the Docker workload images"
    popd > /dev/null 2>&1
}
export -f cb_build_workloads
    
function cb_push_images {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2    
    CB_PUSHALL=$3
    CB_IMGTYPE=$4
    CB_BRANCH=$5
    
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
    
    CB_BRANCH=$(echo $CB_BRANCH | sed 's/::/:/g')
    
    if [[ $CB_IMGTYPE == "ALL" ]]
    then
        CB_IMG_GREP_CMD="grep -v orchestrator"
    else
        CB_IMG_GREP_CMD="grep $CB_IMGTYPE"
    fi

    if [[ $CB_IMGTYPE == "orchestrator" ]]
    then
        CB_IMG_GREP_CMD="grep $CB_IMGTYPE"
    fi

    echo "##### Pushing all images to Docker repository"
    for IMG in $(docker images | grep ${CB_REPOSITORY} | $CB_IMG_GREP_CMD | awk '{ print $1 }')
    do
        if [[ $CB_BRANCH != ""  ]]
        then
            CMD="docker tag ${IMG}${CB_BRANCH} ${IMG}:latest"
            echo "########## Tagging image ${IMG}${CB_BRANCH} by executing the command \"$CMD\" ..."             
	        if [[ $? -eq 0 ]]
	        then
                echo "############ Image ${IMG}${CB_BRANCH} tagged successfully!!!"
        	else
                echo "############ Image ${IMG}${CB_BRANCH} tagging FAILED!"	        		
			fi   
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
	        $CMD > /dev/null 2>&1
	        if [[ $? -eq 0 ]]
	        then
                echo "############ Image ${IMG}${CB_BRANCH} pushed successfully!!!"
        	else
                echo "############ Image ${IMG}${CB_BRANCH} push FAILED!"	        		
			fi                	
            if [[ $CB_BRANCH != "latest"  ]]
            then
                CMD="docker push ${IMG}:latest"
                echo "########## Pushing image ${IMG}:latest by executing the command \"$CMD\" ..."
                $CMD > /dev/null 2>&1
                if [[ $? -eq 0 ]]
                then
	                echo "############ Image ${IMG}:latest pushed successfully!!!"
	        	else
	                echo "############ Image ${IMG}:latest push FAILED!"	        		
				fi                	
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
