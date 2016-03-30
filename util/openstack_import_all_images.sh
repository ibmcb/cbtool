#!/bin/bash

#IMAGES_URL=http://sderepo.watson.ibm.com/repo/vmimages/
IMAGES_URL=http://9.2.212.67/repo/vmimages/
IMAGES_ARCH=x86_64
IMAGES_LIST=coremark:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},nullworkload:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},nullworkload:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},ddgen:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},filebench:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},hadoop:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},hadoop:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},linpack:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},hpcc:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},ycsb:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},ycsb:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},iperf:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},iperf:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},netperf:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},netperf:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},specjbb:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},giraph:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},nuttcp:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},nuttcp:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},fio:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},fio:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},xping:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},xping:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},speccloud_cassandra_2111:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},speccloud_cassandra_2111:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},speccloud_hadoop_271:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},speccloud_hadoop_271:docker:raw:x86_64:docker
IMAGES_LIST=${IMAGES_LIST},daytrader:bare:qcow2:x86_64:qemu
IMAGES_LIST=$(echo ${IMAGES_LIST} | sed 's/,/ /g')

sudo wget -N --directory-prefix=/tmp/sdebuilder ${IMAGES_URL}/cloudbench/${IMAGES_ARCH}/md5sum.txt

if [[ -f ~/adminrc ]]
then
	RCFILE_LIST=~/adminrc
elif [[ -f ~/openrc ]]
then
	RCFILE_LIST=~/openrc
elif [[ -f ~/cbrc ]]
then
	RCFILE_LIST=~/cbrc
else
	RCFILE_LIST=$(ls ~/cbrc-*)
fi
	
for RCFILE in $(echo "$RCFILE_LIST")
do
    source $RCFILE
    echo "source $RCFILE"
    for IMAGE in ${IMAGES_LIST}
    do
        
        IMAGE_NAME=cb_$(echo ${IMAGE} | cut -d ':' -f 1)
        CONTAINER_FORMAT=$(echo ${IMAGE} | cut -d ':' -f 2)
        DISK_FORMAT=$(echo ${IMAGE} | cut -d ':' -f 3)
        ARCH=$(echo ${IMAGE} | cut -d ':' -f 4)
        HYPERVISOR=$(echo ${IMAGE} | cut -d ':' -f 5)
    
        if [[ ${CONTAINER_FORMAT} == "docker" ]]
        then
            IMAGE_FILE_EXTENSION="tar"
        else
            IMAGE_FILE_EXTENSION="qcow2"
        fi    
                
        IS_IMAGE_IMPORTED=$(glance --os-image-api-version 1 image-list 2>&1 | grep ${DISK_FORMAT} | grep ${CONTAINER_FORMAT} | grep -c ${IMAGE_NAME} )
            
        if [[ IS_IMAGE_IMPORTED -eq 0 ]]
        then 
            echo "Importing Cloudbench image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}) from ${IMAGES_URL}/cloudbench/${ARCH}/${IMAGE_NAME} into Glance..."
            GICMD="glance --os-image-api-version 1 image-create --name ${IMAGE_NAME} --is-public true --container-format ${CONTAINER_FORMAT} --disk-format ${DISK_FORMAT} --copy-from ${IMAGES_URL}/cloudbench/${ARCH}/${IMAGE_NAME}.${IMAGE_FILE_EXTENSION}"
            echo "Command line is \"$GICMD\""
            $GICMD
            sleep 2
            
        else
            UUID=$(glance --os-image-api-version 1 image-list | grep ${DISK_FORMAT} | grep ${CONTAINER_FORMAT} | grep [[:space:]]${IMAGE_NAME}[[:space:]] | awk '{ print $2 }')
            STATE=$(glance --os-image-api-version 1 image-list | grep ${DISK_FORMAT} | grep ${CONTAINER_FORMAT} | grep [[:space:]]${IMAGE_NAME}[[:space:]] | awk '{ print $12 }')

            echo "The Cloudbench image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}) is present in glance with the UUID ${UUID} (state \"$STATE\")"
            if [[ $STATE == "active" ]]
            then
                CURRENT_CHECKSUM=$(glance --os-image-api-version 1 image-show $UUID | grep checksum | awk '{ print $4}')
                NEW_CHECKSUM=$(sudo cat /tmp/sdebuilder/md5sum.txt | grep $IMAGE_FILE_EXTENSION | grep [[:space:]]${IMAGE_NAME}\. | awk '{ print $1 }')
                
                if [[ ${CURRENT_CHECKSUM} == ${NEW_CHECKSUM} ]]
                then
                    echo "Image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}) is already present in glance with the appropriate checksum ${NEW_CHECKSUM}."
                else
                    echo "The Cloudbench image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}) present in glance has a checksum (${CURRENT_CHECKSUM}) that does not match the most current ${NEW_CHECKSUM}. Deleting image..."
                    glance --os-image-api-version 1 image-delete $UUID
                    sleep 2                
                                    
                    echo "Re-importing Cloudbench image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}), with correct checksum, from ${REPO_VMIMAGES}/cloudbench/${ARCH}/${IMAGE_NAME} into glance..."
                    GICMD="glance --os-image-api-version 1 image-create --name ${IMAGE_NAME} --is-public true --container-format ${CONTAINER_FORMAT} --disk-format ${DISK_FORMAT} --copy-from ${IMAGES_URL}/cloudbench/${ARCH}/${IMAGE_NAME}.${IMAGE_FILE_EXTENSION}"
                    echo "Command line is \"$GICMD\""
                    $GICMD
                    sleep 2
                fi
             else
                 echo "Image ${IMAGE_NAME} (${DISK_FORMAT}/${CONTAINER_FORMAT}) is in state \"$STATE\". Will ignore it for now"
             fi                          
        fi
        
        UUID=$(glance --os-image-api-version 1 image-list | grep ${DISK_FORMAT} | grep ${CONTAINER_FORMAT} | grep [[:space:]]${IMAGE_NAME}[[:space:]] | awk '{ print $2 }')
        IMGINFO=$(glance --os-image-api-version 1 image-show $UUID)
        if [[ $(echo "$IMGINFO" | grep architecture | grep -c $ARCH) -eq 0 ]]
        then
            echo "Adding property \"architecture=${ARCH}\" to image \"${IMAGE_NAME}\" (${UUID})..."
            glance --os-image-api-version 1 image-update ${UUID} --property architecture=${ARCH} > /dev/null 2>&1 || ( echo "failed while updating image properties"; exit 1 )
        fi

        if [[ $(echo "$IMGINFO" | grep hypervisor_type | grep -c $HYPERVISOR) -eq 0 ]]
        then
            echo "Adding property \"hypervisor_type=${HYPERVISOR}\" to image \"${IMAGE_NAME}\" (${UUID})..."
            glance --os-image-api-version 1 image-update ${UUID} --property hypervisor_type=${HYPERVISOR} > /dev/null 2>&1 || ( echo "failed while updating image properties"; exit 1 )
        fi
 
    done
      
    COUNTER=1
    ATTEMPTS=400
    ERROR=0
    SAVING_IMAGES=1
    while [[ "$COUNTER" -le "$ATTEMPTS" && $ERROR -eq 0 && $SAVING_IMAGES -eq 1 ]]
    do
        SAVING_IMAGES=0
        for IMAGE_FILE in ${IMAGES_LIST}
        do
            
            IMAGE_NAME=cb_$(echo ${IMAGE_FILE} | cut -d ':' -f 1)
            CONTAINER_FORMAT=$(echo ${IMAGE_FILE} | cut -d ':' -f 2)
            DISK_FORMAT=$(echo ${IMAGE_FILE} | cut -d ':' -f 3)
            ARCH=$(echo ${IMAGE_FILE} | cut -d ':' -f 4)
            HYPERVISOR=$(echo ${IMAGE_FILE} | cut -d ':' -f 5)
    
            if [[ $(glance --os-image-api-version 1 image-list | grep ${DISK_FORMAT} | grep ${CONTAINER_FORMAT} | grep -c ${IMAGE_NAME}) -eq 0 ]]
            then
                ERROR=1
                echo "Image ${IMAGE_NAME} ($HYPERVISOR) not present on Glance!"
                break
            else
                if [[ $(glance --os-image-api-version 1 image-list | grep [[:space:]]${IMAGE_NAME}[[:space:]] | grep -c active) -eq 0 ]]
                then
                    echo "Image ${IMAGE_NAME} ($HYPERVISOR) still not in \"active\" state"
                    SAVING_IMAGES=1
                else 
                    echo "Image ${IMAGE_NAME} ($HYPERVISOR) is ready to be used"
                fi
            fi
    
            sleep 2
                
        done
        
        COUNTER="$(( $COUNTER + 1 ))"
    done
    echo "Done"
done
exit 0
