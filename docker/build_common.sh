#!/usr/bin/env bash

function cb_docker_build {
    CB_REPOSITORY=$1
    CB_VERBQUIET=$2    
    CB_DOCKERFN=$3
    CB_BRANCH=$4     
    CB_USERNAME=$5 
    CB_ARCH=$6
    CB_RSYNC=$7
    CB_FATAL=$8
    CB_SQUASH=$9

    if [[ $CB_ARCH == "x86_64" ]]
    then
        CB_ARCH1=x86_64
        CB_ARCH2=x86-64
        CB_ARCH3=amd64
    fi

    if [[ $CB_ARCH == "ppc64le" ]]
    then
        CB_ARCH1=ppc64le
        CB_ARCH2=ppc64
        CB_ARCH3=ppc64
    fi                        

    CB_ACTUAL_SQUASH=''
    if [[ ! -z $CB_SQUASH ]]
    then
        if [[ $CB_SQUASH == "true" ]]
        then
#	        CB_ACTUAL_SQUASH="--squash"
	        CB_ACTUAL_SQUASH=""
        fi
    fi                                                                                                                                                                                                                        
    sudo rm -rf Dockerfile && sudo cp -f $CB_DOCKERFN Dockerfile

    sudo sed -i "s^REPLACE_USERNAME^$CB_USERNAME^g" Dockerfile    
            
    CB_DNAME=$(echo $CB_DOCKERFN | sed 's/Dockerfile-//g')

    sudo sed -i "s^REPLACE_BRANCH^$CB_BRANCH^g" Dockerfile

    sudo sed -i "s^REPLACE_ARCH1^$CB_ARCH1^g" Dockerfile
    sudo sed -i "s^REPLACE_ARCH2^$CB_ARCH2^g" Dockerfile
        
    sudo sed -i "s^REPLACE_BASE_VANILLA_UBUNTU^$CB_UBUNTU_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_VANILLA_PHUSION^$CB_PHUSION_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_VANILLA_CENTOS^$CB_CENTOS_BASE^g" Dockerfile
    sudo sed -i "s^REPLACE_RSYNC^rsync -a rsync://$CB_RSYNC/3rd_party/workload/^g" Dockerfile
                
    if [[ ! -z $CB_DNAME_BASE_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_BASE_UBUNTU^${CB_REPOSITORY}/$CB_DNAME_BASE_UBUNTU^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_BASE_PHUSION ]]
    then    
        sudo sed -i "s^REPLACE_BASE_PHUSION^${CB_REPOSITORY}/$CB_DNAME_BASE_PHUSION^g" Dockerfile
    fi
    
    if [[ ! -z $CB_DNAME_BASE_CENTOS ]]
    then        
        sudo sed -i "s^REPLACE_BASE_CENTOS^${CB_REPOSITORY}/$CB_DNAME_BASE_CENTOS^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_UBUNTU ]]
    then
        sudo sed -i "s^REPLACE_NULLWORKLOAD_UBUNTU^${CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_UBUNTU^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_PHUSION ]]
    then      
        sudo sed -i "s^REPLACE_NULLWORKLOAD_PHUSION^${CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_PHUSION^g" Dockerfile
    fi

    if [[ ! -z $CB_DNAME_NULLWORKLOAD_CENTOS ]]
    then          
        sudo sed -i "s^REPLACE_NULLWORKLOAD_CENTOS^${CB_REPOSITORY}/$CB_DNAME_NULLWORKLOAD_CENTOS^g" Dockerfile
    fi

    sudo cp -f Dockerfile ${CB_DOCKERFN}._processed_    
            
    CB_ACTUAL_VERBQUIET=$(echo $CB_VERBQUIET | sed 's/--ve//g')
    CB_DOCKER_CMD="sudo docker build -t ${CB_REPOSITORY}/$CB_DNAME:$CB_BRANCH $CB_ACTUAL_VERBQUIET $CB_ACTUAL_SQUASH ."
    echo "########## Building image ${CB_REPOSITORY}/$CB_DNAME by executing the command \"$CB_DOCKER_CMD\" ..."
    $CB_DOCKER_CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "############## ERROR: Image \"${CB_REPOSITORY}/$CB_DNAME\" failed while executing command \"$CB_DOCKER_CMD\""
        sudo rm -rf Dockerfile
        if [[ $CB_FATAL == "true" ]]
        then
            exit 1
        else
            echo "############## WARNING: Image \"${CB_REPOSITORY}/$CB_DNAME\" will not be available for deployment!!!"
            sleep 5
        fi
    else
        echo "############## INFO: Image \"${CB_REPOSITORY}/$CB_DNAME\" built successfully!!!" 
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
    CB_BRANCH=$6
                      
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

        cb_docker_build $CB_REPOSITORY $CB_VERBQUIET $CB_DFILE $CB_BRANCH $CB_USERNAME $CB_ARCH $CB_RSYNC true false
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
    
    echo "##### Pushing all images to Docker repository"
    for IMG in $(docker images | grep ${CB_REPOSITORY} | awk '{ print $1 }')
    do
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
        if [[ $NOT_COREMARK -eq 1 && $NOT_LINPACK -eq 1 && $NOT_PARBOIL -eq 1 && $NOT_SPEC -eq 1 && $NOT_CAFFE -eq 1 && $NOT_RUBIS -eq 1 && $NOT_RUBBOS -eq 1 || $CB_PUSHALL -eq 1 ]]
        then
            CMD="docker push $IMG"
            echo "########## Pushing image ${IMG} by executing the command \"$CMD\" ..."             
            $CMD
        fi
    done
    echo "##### Images to Docker repository"    
}