#!/bin/bash

. ~/adminrc
. ~/openrc

IMAGES_URL=http://sderepo.watson.ibm.com/repo/vmimages/
IMAGES_ARCH=x86_64
IMAGES_LIST=coremark:bare:qcow2:x86_64:qemu,daytrader:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},ddgen:bare:qcow2:x86_64:qemu,filebench:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},hadoop:bare:qcow2:x86_64:qemu,linpack:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},hpcc:bare:qcow2:x86_64:qemu,ycsb:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},iperf:bare:qcow2:x86_64:qemu,netperf:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},nullworkload:bare:qcow2:x86_64:qemu,specjbb:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},giraph:bare:qcow2:x86_64:qemu,nuttcp:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},fio:bare:qcow2:x86_64:qemu,xping:bare:qcow2:x86_64:qemu
IMAGES_LIST=${IMAGES_LIST},speccloud_cassandra:bare:qcow2:x86_64:qemu,speccloud_kmeans:bare:qcow2:x86_64:qemu

IMAGES_LIST=$(echo ${IMAGES_LIST} | sed 's/,/ /g')

sudo wget -N --directory-prefix=/tmp/sdebuilder ${IMAGES_URL}/cloudbench/${IMAGES_ARCH}/md5sum.txt

for IMAGE in ${IMAGES_LIST}
do
    
    IMAGE_NAME=cb_$(echo ${IMAGE} | cut -d ':' -f 1)
    CONTAINER_FORMAT=$(echo ${IMAGE} | cut -d ':' -f 2)
    DISK_FORMAT=$(echo ${IMAGE} | cut -d ':' -f 3)
    ARCH=$(echo ${IMAGE} | cut -d ':' -f 4)
    HYPERVISOR=$(echo ${IMAGE} | cut -d ':' -f 5)
    
    IS_IMAGE_IMPORTED=$(glance image-list 2>&1 | grep -c ${IMAGE_NAME})
        
    if [[ IS_IMAGE_IMPORTED -eq 0 ]]
    then 
        echo "Importing Cloudbench image ${IMAGE_NAME} from ${IMAGES_URL}/cloudbench/${ARCH}/${IMAGE_NAME} into glance..."
        glance image-create --name ${IMAGE_NAME} --is-public true --container-format ${CONTAINER_FORMAT} --disk-format ${DISK_FORMAT} --copy-from ${IMAGES_URL}/cloudbench/${ARCH}/${IMAGE_NAME}.qcow2
    
        sleep 2
#       UUID=$(glance image-list | grep [[:space:]]${IMAGE_NAME}[[:space:]] | awk '{ print $2 }')
#       echo "Adding property \"architecture=${ARCH}\" to image \"${IMAGE_NAME}\" (${UUID})..."
#       glance image-update ${UUID} --property architecture=${ARCH}
#       echo "Adding property \"hypervisor_type=${HYPERVISOR}\" to image \"${IMAGE_NAME}\" (${UUID})..."
#       glance image-update ${UUID} --property hypervisor_type=${ARCH}
    else
        UUID=$(glance image-list | grep [[:space:]]${IMAGE_NAME}[[:space:]] | awk '{ print $2 }')
        CURRENT_CHECKSUM=$(glance image-show $UUID | grep checksum | awk '{ print $4}')
        NEW_CHECKSUM=$(sudo cat /tmp/sdebuilder/md5sum.txt | grep [[:space:]]${IMAGE_NAME}\. | awk '{ print $1 }')
            
        if [[ ${CURRENT_CHECKSUM} == ${NEW_CHECKSUM} ]]
        then
            echo "Image ${IMAGE_NAME} is already present in glance with the appropriate checksum ${NEW_CHECKSUM}."
        else
            echo "The Cloudbench image ${IMAGE_NAME} present in glance has a checksum (${CURRENT_CHECKSUM}) that does not match the most current ${NEW_CHECKSUM}. Deleting image..."
            glance image-delete $UUID
            sleep 2                
                                
            echo "Re-importing Cloudbench image ${IMAGE_NAME} (with correct checksum) from ${REPO_VMIMAGES}/cloudbench/${ARCH}/${IMAGE_NAME} into glance..."
            glance image-create --name ${IMAGE_NAME} --is-public true --container-format ${CONTAINER_FORMAT} --disk-format ${DISK_FORMAT} --copy-from ${REPO_VMIMAGES}/cloudbench/${ARCH}/${IMAGE_NAME}.qcow2
            sleep 2                
        fi 
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

        if [[ $(glance image-list | grep -c ${IMAGE_NAME}) -eq 0 ]]
        then
            ERROR=1
            echo "Image ${IMAGE_NAME} not present on Glance!"
            break
        else
            if [[ $(glance image-list | grep [[:space:]]${IMAGE_NAME}[[:space:]] | grep -c active) -eq 0 ]]
            then
                echo "Image ${IMAGE_NAME} still not in \"active\" state after ${COUNTER} attempts"
                SAVING_IMAGES=1
            fi
        fi

        sleep 2
            
    done
    
    COUNTER="$(( $COUNTER + 1 ))"
done
echo "Done"
exit 0