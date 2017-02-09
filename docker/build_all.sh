#!/usr/bin/env bash


if [[ -z $1 ]]
then
    echo "Usage: build_all.sh <repository> [quiet|verbose] [nopush|push]"
    exit 1
fi
REPOSITORY=${1}

VERBQUIET="-q"
if [[ ! -z $2 ]]
then
    VERBQUIET=`echo $2 | tr '[:upper:]' '[:lower:]'`
    if [[ $VERBQUIET == "verbose" ]]
    then
        VERBQUIET=''
    fi
fi

PUSH_IMAGES="nopush"
if [[ ! -z $3 ]]
then
    PUSH_IMAGES=`echo $3 | tr '[:upper:]' '[:lower:]'`
fi
    
echo "##### Building Docker orchestrator images"
pushd orchestrator > /dev/null 2>&1
sudo rm -rf Dockerfile
for DFILE in $(ls Dockerfile* | grep -v centos)
do
    sudo rm -rf Dockerfile && sudo cp -f $DFILE Dockerfile
    DNAME=$(echo $DFILE | sed 's/Dockerfile-//g')
                                                 
    CMD="sudo docker build -t ${REPOSITORY}/$DNAME $VERBQUIET ."
    echo "########## Building image ${REPOSITORY}/$DNAME by executing the command \"$CMD\" ..."
    $CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "Failed while executing command \"$CMD\""
        sudo rm -rf Dockerfile
        exit 1
    fi
    sudo rm -rf Dockerfile
    echo "########## Image ${1}/$(echo $DFILE | sed 's/Dockerfile-//g') built successfully"
done
echo "##### Done building Docker orchestrator images"
echo

popd > /dev/null 2>&1    
    
echo "##### Building Docker base images"
pushd base > /dev/null 2>&1
sudo rm -rf Dockerfile
for DFILE in $(ls Dockerfile*)
do
    sudo rm -rf Dockerfile && sudo cp -f $DFILE Dockerfile
    DNAME=$(echo $DFILE | sed 's/Dockerfile-//g')
    
    echo $DNAME | grep ubuntu > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_BASE_UBUNTU=$DNAME
    fi

    echo $DNAME | grep phusion > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_BASE_PHUSION=$DNAME
    fi

    echo $DNAME | grep centos > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_CENTOS_PHUSION=$DNAME
    fi
                                                 
    CMD="sudo docker build -t ${REPOSITORY}/$DNAME $VERBQUIET ."
    echo "########## Building image ${REPOSITORY}/$DNAME by executing the command \"$CMD\" ..."
    $CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "Failed while executing command \"$CMD\""
        sudo rm -rf Dockerfile
        exit 1
    fi
    sudo rm -rf Dockerfile
    echo "########## Image ${1}/$(echo $DFILE | sed 's/Dockerfile-//g') built successfully"
done
echo "##### Done building Docker base images"
echo

popd > /dev/null 2>&1
pushd workload > /dev/null 2>&1
echo "##### Building Docker nullworkload images"
for DFILE in $(ls Dockerfile*nullworkload)
do
    sudo rm -rf Dockerfile && sudo cp -f $DFILE Dockerfile
    DNAME=$(echo $DFILE | sed 's/Dockerfile-//g')
    sudo sed -i "s^REPLACE_BASE_UBUNTU^${REPOSITORY}/$DNAME_BASE_UBUNTU^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_PHUSION^${REPOSITORY}/$DNAME_BASE_PHUSION^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_CENTOS^${REPOSITORY}/$DNAME_BASE_CENTOS^g" Dockerfile

    echo $DNAME | grep ubuntu > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_NULLWORKLOAD_UBUNTU=$DNAME
    fi

    echo $DNAME | grep phusion > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_NULLWORKLOAD_PHUSION=$DNAME
    fi

    echo $DNAME | grep centos > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        DNAME_NULLWORKLOAD_PHUSION=$DNAME
    fi                
                                                
    CMD="sudo docker build -t ${REPOSITORY}/$DNAME $VERBQUIET ."
    echo "########## Building image ${REPOSITORY}/$DNAME by executing the command \"$CMD\" ..."
    $CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "Failed while executing command \"$CMD\""
        sudo rm -rf Dockerfile        
        exit 1
    fi
    sudo rm -rf Dockerfile    
    echo "########## Image ${REPOSITORY}/$DNAME built successfully"    
done
echo "##### Done building Docker nullworkload images"
echo

echo "##### Building the rest of the Docker workload images"
for DFILE in $(ls Dockerfile* | grep -v nullworkload | grep -v ignore)
do
    sudo rm -rf Dockerfile && sudo cp -f $DFILE Dockerfile
    DNAME=$(echo $DFILE | sed 's/Dockerfile-//g')
    sudo sed -i "s^REPLACE_BASE_UBUNTU^${REPOSITORY}/$DNAME_BASE_UBUNTU^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_PHUSION^${REPOSITORY}/$DNAME_BASE_PHUSION^g" Dockerfile
    sudo sed -i "s^REPLACE_BASE_CENTOS^${REPOSITORY}/$DNAME_BASE_CENTOS^g" Dockerfile
    sudo sed -i "s^REPLACE_NULLWORKLOAD_UBUNTU^${REPOSITORY}/$DNAME_NULLWORKLOAD_UBUNTU^g" Dockerfile
    sudo sed -i "s^REPLACE_NULLWORKLOAD_PHUSION^${REPOSITORY}/$DNAME_NULLWORKLOAD_PHUSION^g" Dockerfile
    sudo sed -i "s^REPLACE_NULLWORKLOAD_CENTOS^${REPOSITORY}/$DNAME_NULLWORKLOAD_CENTOS^g" Dockerfile
                                                
    CMD="sudo docker build -t ${REPOSITORY}/$DNAME $VERBQUIET ."
    echo "########## Building image ${REPOSITORY}/$DNAME by executing the command \"$CMD\" ..."
    $CMD
    ERROR=$?
    if [[ $ERROR -ne 0 ]]
    then
        echo "Failed while executing command \"$CMD\""
        sudo rm -rf Dockerfile        
        exit 1
    fi
    sudo rm -rf Dockerfile    
    echo "########## Image ${REPOSITORY}/$DNAME built successfully"    
done
echo "##### Done building the rest of the Docker workload images"
popd > /dev/null 2>&1

if [[ $PUSH_IMAGES == "push" ]]
then
    echo "##### Pushing all images to Docker repository"
    for IMG in $(docker images | grep ${REPOSITORY} | awk '{ print $1 }')
    do
        echo $IMG | grep coremark
        NOT_COREMARK=$?
        echo $IMG | grep linpack
        NOT_LINPACK=$?
        echo $IMG | grep parboil
        NOT_LINPACK=$?        
        if [[ $NOT_COREMARK && $NOT_LINPACK && $NOT_PARBOIL ]]
        then
            CMD="docker push $IMG"
            echo "########## Pushing image ${IMG} by executing the command \"$CMD\" ..."             
            $CMD
        fi
    done
    echo "##### Images to Docker repository"    
fi