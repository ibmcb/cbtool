#!/usr/bin/env bash

IMAGE_STORAGE_DIR=$1

if [ -z "$FILE_BASE_STORAGE" ]
then
    IMAGE_STORAGE_DIR=/kvm_repo
fi

if [ -d ${IMAGE_STORAGE_DIR} ]
then
    echo "Image directory ${IMAGE_STORAGE_DIR} does not exist."
    exit 2
fi

PLMFBASEDIR=${IMAGE_STORAGE_DIR}/plmfbase

PLMBASEVG=$2
if [ -z "$IMAGE_STORAGE_VOLUME_GROUP" ]
then
    PLMBASEVG=vgplm
fi

echo "Checking for the \"${PLMFBASEDIR}\" Directory....."
mkdir -p ${PLMFBASEDIR}
echo "Directory exists"

echo "Checking for \"${PLMBASEVG}\" Volume Group....."
VOLUME_GROUP_LIST=`vgdisplay`
IS_VOLUME_GROUP_CREATED=`echo $VOLUME_GROUP_LIST | grep -c ${PLMBASEVG}`
if [ ${IS_VOLUME_GROUP_CREATED} -eq 0 ]
then
    echo "Volume Group ${PLMBASEVG} not created. Bypassing LVM-based VMs."
    exit 0
fi
VGPESIZE=`vgdisplay -c | grep ${PLMBASEVG} | cut -d ':' -f 13`
VGPESIZE=`echo "${VGPESIZE} * 1024" | bc`

echo "Volume Group exists (Physical Extent size is ${VGPESIZE} bytes"
VOLUME_LIST=`lvdisplay -c`

for IMAGE_FILE in `ls ${IMAGE_STORAGE_DIR} | grep qcow2`
do
    IMAGE_NAME=`echo ${IMAGE_FILE} | cut -d '.' -f 1`
    RAW_IMAGE_FILE=${PLMFBASEDIR}/${IMAGE_NAME}.raw
    echo "Checking for image file \"${IMAGE_NAME}\" in \"${PLMFBASEDIR}\" ...." 
    if [ -e ${RAW_IMAGE_FILE} ] 
    then
        echo -n "RAW image file \"${RAW_IMAGE_FILE}\" found: "
    else
        echo "Converting QCOW2 image file \"${IMAGE_STORAGE_DIR}/$IMAGE_FILE\" to RAW \"${RAW_IMAGE_FILE}\" ...." 
        qemu-img convert ${IMAGE_STORAGE_DIR}/$IMAGE_FILE -p -O raw ${RAW_IMAGE_FILE}
    fi
    QEMU_IMG_INFO_OUTPUT=`qemu-img info ${RAW_IMAGE_FILE} 2>&1`
    IMAGE_FORMAT=`echo ${QEMU_IMG_INFO_OUTPUT} | cut -d ' ' -f 5`
    VIRTUAL_IMAGE_SIZE_BYTES=`echo ${QEMU_IMG_INFO_OUTPUT} | cut -d ' ' -f 9 | sed 's/(//g'`
    VIRTUAL_IMAGE_SIZE=`echo ${QEMU_IMG_INFO_OUTPUT} | cut -d ' ' -f 8`
    ACTUAL_IMAGE_SIZE=`echo ${QEMU_IMG_INFO_OUTPUT} | cut -d ' ' -f 13`
    echo "format is \"${IMAGE_FORMAT}\", with a virtual size of ${VIRTUAL_IMAGE_SIZE} (${VIRTUAL_IMAGE_SIZE_BYTES} bytes), and an actual size of ${ACTUAL_IMAGE_SIZE}"
    
    echo "Checking for volume \"${IMAGE_NAME}\" in \"${PLMBASEVG}\" ..."
    IS_VOLUME_CREATED=`echo ${VOLUME_LIST} | grep -c ${IMAGE_NAME}`

    if [ ${IS_VOLUME_CREATED} -eq 0 ]
    then
        VOLUME_SIZE_IN_PES=`echo "${VIRTUAL_IMAGE_SIZE_BYTES} / ${VGPESIZE}" | bc`
        echo "Creating volume \"${IMAGE_NAME}\" in Volume Group \"${PLMBASEVG}\" with ${VOLUME_SIZE_IN_PES} PEs...."
        lvcreate -l ${VOLUME_SIZE_IN_PES} -n ${IMAGE_NAME} ${PLMBASEVG}
        echo "Copying image file contents to volume ...."
        dd if=${RAW_IMAGE_FILE} of=/dev/${PLMBASEVG}/${IMAGE_NAME} bs=${VGPESIZE}
    else
        VOLUME_SIZE_IN_PES=`echo ${VOLUME_LIST} | grep ${IMAGE_NAME} | cut -d ':' -f 8`
        echo "Volume found: size is ${VOLUME_SIZE_IN_PES} PEs"
    fi
        
done
