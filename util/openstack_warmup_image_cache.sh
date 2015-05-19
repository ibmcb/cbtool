#!/bin/bash

. ~/adminrc
. ~/openrc

NVMS_SIZE=${NVMS_SIZE:-"m1.tiny"}
NVMS_COPIES=${NVMS_COPIES:-1}
NVMS_DISK_FORMAT=${NVMS_DISK_FORMAT:-"qcow2"}
QNETWORKS_NETNAME=${QNETWORKS_NETNAME:-"private1"}

if [[ -z ${1} ]]
then
	NVMS_CB_STR="cb_"
else
	NVMS_CB_STR=${1}
fi
	
for COPY in ${NVMS_COPIES}
do
    for IMAGEID in $(glance image-list | grep -v "| ID" | grep -v "+" | grep ${NVMS_CB_STR} | grep ${NVMS_DISK_FORMAT} | awk '{ print $2 }')
    do
        IMAGEDISKFORMAT=$(glance image-show ${IMAGEID} | grep disk_format | awk '{ print $4 }' | sed 's/qcow2/qemu/g')
        IMAGENAME=$(glance image-show ${IMAGEID} | grep name | awk '{ print $4 }')
        
		for HYPERVISOR_ID in $(nova hypervisor-list | grep -v '+-' | grep -v "Hypervisor hostname" | awk '{ print $2 }')
		do
		    HYPERVISOR_TYPE=$(nova hypervisor-show ${HYPERVISOR_ID} | grep hypervisor_type | awk '{ print $4 }' | tr '[:upper:]' '[:lower:]')
		    HYPERVISOR_NAME=$(nova hypervisor-show ${HYPERVISOR_ID} | grep service_host | awk '{ print $4 }' | tr '[:upper:]' '[:lower:]')
    		HYPERVISOR_AZ=$(nova host-list | grep -v '+-' | grep -v "host_name" | grep -v internal | grep ${HYPERVISOR_NAME}[[:space:]] | awk '{ print $6 }')

	        if [[ ${HYPERVISOR_TYPE} == $IMAGEDISKFORMAT ]]
	        then

	            NETID=$(neutron net-list | grep ${QNETWORKS_NETNAME} | awk '{ print $2 }')
	            NETID_SIZE=${#NETID}            
	            if [[ $NETID_SIZE -ne 0 ]]
	            then
	                SCRIPT_NAME=/tmp/boot_test_$(echo ${imagename} | sed 's#/#___#g')_at_${HYPERVISOR_NAME}_${COPY}_privnet.sh
	                echo "Booting ${IMAGENAME} on hypervisor ${HYPERVISOR_NAME} (on the ${QNETWORKS_NETNAME} network)..."    
	                sleep $(( $RANDOM % 10 ))
	                echo -e "#!/bin/bash\n. ~/adminrc\nnova boot --flavor $NVMS_SIZE \
 --image $IMAGEID \
 --nic net-id=$NETID \
 --key-name cbtool_rsa \
 --availability-zone ${HYPERVISOR_AZ}:${HYPERVISOR_NAME} \
${IMAGENAME}_at_${HYPERVISOR_NAME}_${COPY}_privnet" > $SCRIPT_NAME
	                chmod 755 $SCRIPT_NAME
	                $SCRIPT_NAME        
            	fi
        	fi
    	done
	done
done