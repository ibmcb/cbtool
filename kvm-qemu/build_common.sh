#!/usr/bin/env bash
if [[ $(whoami) != "root" ]]
then
    echo "Please run the kvm-qemu image builder as root"
    exit 1
fi

echo "Making sure all dependencies are in place..."
for _dep in ps bc git ifconfig netstat wget rsync dpkg qemu-img virt-customize virsh libvirtd
do
    which ${_dep}
    if [[ $? -ne 0 ]]
    then
        echo "Dependency ${_dep} not installed. Please install it, and the proceed"
        echo "Usually, just running \"sudo apt -y install git bc libguestfs-tools libvirt-clients rsync wget qemu-utils libvirt-dev numactl libvirt-bin virtinst virt-manager virt-viewer python-libvirt qemu-kvm qemu-system qemu-system-arm qemu-efi\" should be enough."
        exit 1
    fi
done

CB_KVMQEMU_BIMG_DIR=NONE
CB_KVMQEMU_UBUNTU_BASE=https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-$(uname -m | sed 's/ppc64le/ppc64el/g' | sed 's/x86_64/amd64/g').img
CB_KVMQEMU_CENTOS_BASE=https://cloud.centos.org/centos/7/images/CentOS-7-$(uname -m)-GenericCloud-1808.qcow2
CB_ALLINONE=0
CB_PRESERVE_ON_ERROR=0
CB_DISTROS="ubuntu"
CB_USERNAME="cbuser"
git rev-parse --abbrev-ref HEAD > /dev/null 2>&1
if [[ $? -eq 0 ]]
then
    CB_BRANCH=$(git rev-parse --abbrev-ref HEAD)
else
    CB_BRANCH="master"
fi
CB_WKS="all"
CB_VERB=''
CB_BASE_IMAGE_SKIP=1
CB_NULLWORKLOAD_IMAGE_SKIP=1
CB_KVMQEMU_BIMG_SIZE=50G 
CB_KVMQEMU_URIS_LIST=archive.canonical.com,archive.ubuntu.com,security.ubuntu.com,download.docker.com,pypi.org,files.pythonhosted.org,github.ibm.com,pypi.python.org,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,dl.google.com,packages.cloud.google.com,apt.kubernetes.io,storage.googleapis.com,github.com,storage.cloud.google.com,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,storage.googleapis.com,pkg.cfssl.org,ports.ubuntu.com,github-production-release-asset-2e65be.s3.amazonaws.com,ppa.launchpad.net,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,launchpadlibrarian.net,piccolo.link,nuttcp.net,fossies.org,dev.mysql.com,download.forge.ow2.org,dl.bintray.com,sourceforge.net,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,downloads.sourceforge.net,ayera.dl.sourceforge.net,cytranet.dl.sourceforge.net,superb-sea2.dl.sourceforge.net,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,cfhcable.dl.sourceforge.net,versaweb.dl.sourceforge.net,astuteinternet.dl.sourceforge.net,ibm.biz,archive.apache.org,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,managedway.dl.sourceforge.net,akamai.bintray.com,cdn.kernel.org,dualstack.k.shared.global.fastly.net,ftp.us.debian.org,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,repo.maven.apache.org,www.nas.nasa.gov,math.nist.gov,svn.apache.org,cdn.mysql.com,download.schedmd.com,ftp.ports.debian.org,
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,master.dl.sourceforge.net,cran.us.r-project.org,s3.amazonaws.com,newcontinuum.dl.sourceforge.net,keyserver.ubuntu.com
CB_KVMQEMU_URIS_LIST=$CB_KVMQEMU_URIS_LIST,mirrors.adn.networklayer.com

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
CB_KVMQEMU_S_DIR=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

export CB_BASE_DIR=$(echo $CB_KVMQEMU_S_DIR | sed 's/kvm-qemu//g' | rev | cut -d '/' -f 2 | rev)
export CB_KVMQEMU_HOME=$HOME

#
#
#
#
#
#

#
#
#
#
#
#

CB_RSYNC_IFACE=$(sudo netstat -rn | grep UG | grep ^0.0.0.0 | awk '{ print $8 }')
CB_RSYNC_ADDR=$(sudo ifconfig $CB_RSYNC_IFACE | grep "inet " | awk '{ print $2 }' | sed 's/addr://g')
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
    path=$CB_KVMQEMU_S_DIR/..
    uid=$(whoami)
    gid=$(whoami)
    read only=no
    list=yes
EOF
    sudo rsync --daemon --config ${CB_RSYNC_CONF}/$(whoami)_rsync.conf
fi

CB_RSYNC=$CB_RSYNC_ADDR-${CB_RSYNC_PORT}-$(whoami)
CB_RSYNC_DIRECT=${CB_RSYNC_ADDR}:${CB_RSYNC_PORT}/$(whoami)_cb    
echo "##### Testing rsync server on ${CB_RSYNC_DIRECT}..." 
rsync -a rsync://${CB_RSYNC_DIRECT}/util/cbssh.sh > /dev/null 2>&1
if [[ $? -ne 0 ]]
then
    echo "Error while testing rsync server"
    exit 1
else
    echo "##### rsync server was found on ${CB_RSYNC_DIRECT}"
fi

function cache_resolve_dns {
    fcdns=/tmp/cache_resolve_dns
    touch $fcdns
    for turi in $(echo $CB_KVMQEMU_URIS_LIST | sed 's/,,/,/g' | sed 's/,/ /g')
    do
        sudo grep [[:space:]]${turi}$ $fcdns > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            _do=$(dig +short $turi)
            if [[ $? -ne 0 ]]
            then
                announce "ERROR: unable to resolve \"$turi\""
                exit 1
            else
                echo "$(echo \"${_do}\" | grep -E -o '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)' | head -n 1) $turi" >> $fcdns
            fi
        else
            /bin/true
            #announce "$turi already present in $fcdns"
        fi
    done
}
export -f cache_resolve_dns

function get_actual_architecture {
    which dpkg > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        CB_KVMQEMU_ACTUAL_ARCH=$(dpkg --print-architecture)
    else
        CB_KVMQEMU_ACTUAL_ARCH=$(uname -m)
    fi        
}
export -f get_actual_architecture

cache_resolve_dns
get_actual_architecture

CB_USAGE="Usage: $0 -r built image location [-w Workload] [-l CB Username/login] [-b branch] [-o distros] [--skip] [--verbose]"

function download_base_images {
    echo "##### Downloading latest version of the vanilla cloud images"
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1
    for CB_KVMQEMU_IMG in $CB_KVMQEMU_DISTROS_IMG_LIST
    do
        echo $CB_KVMQEMU_IMG | grep http > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            echo "####### Downloading from url $CB_KVMQEMU_IMG" 
            sudo wget -N $CB_KVMQEMU_IMG
        else
            echo "####### Assuming image file $CB_KVMQEMU_IMG already in place"
        fi
    done
    echo "##### Done downloading the latest version of the vanilla cloud images"
    echo
    popd > /dev/null 2>&1    
}
export -f download_base_images

function create_base_images {
    echo "##### Creating base images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1
    for CB_KVMQEMU_IMG in $CB_KVMQEMU_DISTROS_IMG_LIST
    do
        CB_KVMQEMU_CIMG_FN=$(echo $CB_KVMQEMU_IMG | rev | cut -d '/' -f 1 | rev)
        if [[ $(echo $CB_KVMQEMU_CIMG_FN | grep -ci centos) -eq 1 ]]
        then
            CB_KVMQEMU_BIMG="centos"
        else
            CB_KVMQEMU_BIMG="ubuntu"
        fi
    
        if [[ $CB_ALLINONE -eq 1 ]]
        then    
            CB_KVMQEMU_BIMG_SIZE=250G
        fi
        
        sudo ls cb_base_${CB_KVMQEMU_BIMG} > /dev/null 2>&1
        if [[ $? -ne 0 ]]
        then
            CB_BASE_IMAGE_SKIP=0
        fi
        
        if [[ $CB_BASE_IMAGE_SKIP -eq 0 ]]
        then        
        
            sudo rm -rf cb_base_${CB_KVMQEMU_BIMG} > /dev/null 2>&1
#        sudo qemu-img create -f qcow2 -o preallocation=metadata cb_base_${CB_KVMQEMU_BIMG} 50G
    
            CB_KVMQEMU_BIMG_PARTS=$(virt-filesystems --long --parts --blkdevs -h -a $CB_KVMQEMU_CIMG_FN  | grep partition)
            
            sudo cp -f $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
            CB_KVMQEMU_BIMG_CURRENT_SIZE=$(echo "$CB_KVMQEMU_BIMG_PARTS" | grep -v M | tail -1 | awk '{ print $4 }' | sed 's/G//g')
            CB_KVMQEMU_BIMG_SIZE=$(echo $CB_KVMQEMU_BIMG_SIZE | sed 's/G//g')
            CB_KVMQEMU_BIMG_ACTUAL_SIZE=$(echo "(${CB_KVMQEMU_BIMG_SIZE}-${CB_KVMQEMU_BIMG_CURRENT_SIZE})/1" | bc)
            echo $CB_KVMQEMU_BIMG_ACTUAL_SIZE | grep "^-" > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then  
                sudo qemu-img resize cb_base_${CB_KVMQEMU_BIMG} +${CB_KVMQEMU_BIMG_ACTUAL_SIZE}G
                sudo virt-customize -a cb_base_${CB_KVMQEMU_BIMG} --run-command "growpart /dev/sda 1; resize2fs /dev/sda1"
            fi
#           sudo qemu-img create -f qcow2 cb_base_${CB_KVMQEMU_BIMG} 15G
#           sudo virt-resize --expand /dev/sda1 $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
    
#           cp -f $CB_KVMQEMU_CIMG_FN cb_base_${CB_KVMQEMU_BIMG}
#           sudo qemu-img resize cb_base_${CB_KVMQEMU_BIMG} +18G
    
            cp -f $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
            sudo sed -i "s^REPLACE_USERNAME^${CB_USERNAME}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
            sudo sed -i "s^REPLACE_BRANCH^${CB_BRANCH}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
            sudo sed -i "s^REPLACE_PATH^${CB_KVMQEMU_S_DIR}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
            sudo sed -i "s^REPLACE_HOME^${CB_KVMQEMU_HOME}^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
                    
            if [[ $CB_ALLINONE -ne 0 ]]
            then
                sudo sed -i "s^#all-in-one ^^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
                sudo sed -i "s^REPLACE_RSYNC_DOWNLOAD^rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude old_data/ --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_                    
            else 
                sudo sed -i "s^REPLACE_RSYNC_DOWNLOAD^rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude 3rd_party/workload/ --exclude old_data/ --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/^g" $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_
            fi
    
            sudo virt-customize -a cb_base_${CB_KVMQEMU_BIMG} $CB_VERB --hostname cbinst --commands-from-file $CB_KVMQEMU_S_DIR/base/${CB_KVMQEMU_BIMG}_commands._processed_

            COUT=$?
            let ERROR+=$COUT
        else
            echo "####### Skipping the creation of base images \"cb_base_${CB_KVMQEMU_BIMG}\""
        fi
    done
    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating base images"
        exit $ERROR
    else
        echo "##### Done creating base images"
    fi
    echo
    popd > /dev/null 2>&1    
}
export -f create_base_images

function create_workload_images {
    CB_WKS_LIST=$1
    CB_DISTROS_LIST=$2

    CB_WKS_LIST=$(echo $CB_WKS_LIST | sed 's/,/\\|/g')
    
    if [[ $CB_DISTROS_LIST == "all" ]]
    then
        CB_DISTROS_LIST=ubuntu' 'centos
    fi

    if [[ $CB_WKS_LIST == "none" ]]
    then
        return 0
    fi
    
    echo "##### Creating workload images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1

    for _CB_DISTRO in $CB_DISTROS_LIST
    do
        if [[ $CB_WKS_LIST == "all" ]]
        then
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep ${_CB_DISTRO} | grep -v caffe | grep -v rubbos | grep -v rubis | grep -v spark | grep -v speccpu | grep -v specsfs | grep -v specweb | grep -v nullworkload | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        else
            CB_WKS_LIST=$(ls $CB_KVMQEMU_S_DIR/../docker/workload/ | grep "$CB_WKS_LIST" | grep ${_CB_DISTRO} | grep -v ._processed_ | sed "s/Dockerfile-${_CB_DISTRO}_cb_//g")
        fi
        
        for _CB_WKS in $CB_WKS_LIST
        do  
            if [[ ${_CB_WKS} == "nullworkload" ]]
            then
                CB_KVMQEMU_BIMG_FN=cb_base_${_CB_DISTRO}
                sudo ls cb_nullworkload_${_CB_DISTRO} > /dev/null 2>&1
                if [[ $? -ne 0 ]]
                then                    
                    CB_NULLWORKLOAD_IMAGE_SKIP=0
                fi
            else
                CB_KVMQEMU_BIMG_FN=cb_nullworkload_${_CB_DISTRO}
            fi

            if [[ ${_CB_WKS} == "nullworkload" && $CB_NULLWORKLOAD_IMAGE_SKIP -eq 1 ]]
            then
                echo "####### Skipping the creation of the \"nullworkload\" image \"${CB_KVMQEMU_BIMG_FN}\""
            else
                                    
                if [[ $CB_ALLINONE -eq 0 ]]
                then
                    CB_KVMQEMU_WIMG_FN=cb_${_CB_WKS}_${_CB_DISTRO}
                    echo "######### Preparing workload image \"cb_${_CB_WKS}_${_CB_DISTRO}\" by creating a copy from \"$CB_KVMQEMU_BIMG_FN\"..."
                    cp -f $CB_KVMQEMU_BIMG_FN cb_${_CB_WKS}_${_CB_DISTRO}
                else
                    CB_KVMQEMU_WIMG_FN=cb_all_in_one_${_CB_DISTRO}
                    sudo ls ${CB_KVMQEMU_WIMG_FN} > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "######### Preparing workload image \"${CB_KVMQEMU_WIMG_FN}\" by creating a copy from \"$CB_KVMQEMU_BIMG_FN\"..."
                        cp -f $CB_KVMQEMU_BIMG_FN ${CB_KVMQEMU_WIMG_FN}
                     fi
                fi
                
                rsync -a rsync://$CB_RSYNC_DIRECT/util/cbrsync.sh > /dev/null 2>&1
                if [[ $? -eq 0 ]]
                then
                    if [[ $CB_ALLINONE -ne 0 ]]
                    then
                        CMD="cd /home/${CB_USERNAME}; rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/ /home/${CB_USERNAME}/$CB_BASE_DIR/;"
                    else
                        CMD="cd /home/${CB_USERNAME}; rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude 3rd_party/workload/ --exclude 3rd_party/workload/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/ /home/${CB_USERNAME}/$CB_BASE_DIR/;"                        
                    fi
                else
                    CMD=""
                fi
                
                CMD=$CMD"chown -R ${CB_USERNAME}:${CB_USERNAME} /home/${CB_USERNAME};"
                CMD=$CMD"sudo -u $CB_USERNAME bash -c \"cd /home/$CB_USERNAME/$CB_BASE_DIR/; git pull\"; "
                CMD=$CMD"sudo -u $CB_USERNAME /home/$CB_USERNAME/$CB_BASE_DIR/install -r workload --wks ${_CB_WKS} --cleanupimageid --filestore $CB_RSYNC"
                echo "######### Creating workload image \"${CB_KVMQEMU_WIMG_FN}\" by executing the command \"$CMD\""
                sudo virt-customize -m 4096 -a ${CB_KVMQEMU_WIMG_FN} $CB_VERB --hostname cbinst \
                --run-command "echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections" \
                --upload /tmp/cache_resolve_dns:/root/cache_resolve_dns \
                --run-command "sudo -u $CB_USERNAME /usr/local/bin/tempconfigetchosts" \
                --run-command "$CMD" \
                --run-command "sudo -u $CB_USERNAME /home/$CB_USERNAME/$CB_BASE_DIR/configure -r workload --wks ${_CB_WKS}" \
                --run-command "sudo -u $CB_USERNAME /usr/local/bin/preinjectkeys /home/${CB_USERNAME}/$CB_BASE_DIR $CB_USERNAME" \
                --run-command "sudo cp -f /etc/hosts.original /etc/hosts"
                COUT=$?
                if [[ $COUT -ne 0 ]]
                then
                    echo "############## ERROR: workload image \"${CB_KVMQEMU_WIMG_FN}\" failed while executing command \"$CMD\""
                    if [[ $CB_PRESERVE_ON_ERROR -ne 1 ]]
                    then
                        sudo rm -rf ${CB_KVMQEMU_WIMG_FN}
                    fi
                    sudo cat /tmp/cb_kvm_failed | grep "${CB_KVMQEMU_WIMG_FN}" > /dev/null 2>&1
                    if [[ $? -ne 0 ]]
                    then
                        echo "${CB_KVMQEMU_WIMG_FN}" >> /tmp/cb_kvm_failed
                    fi
                else
                    echo "############## INFO: workload image \"${CB_KVMQEMU_WIMG_FN}\" built successfully!!!" 
                    sudo sed -i "s^${CB_KVMQEMU_WIMG_FN}^^g" /tmp/cb_kvm_failed
                fi 
                let ERROR+=$COUT
            fi
        done
    done

    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating workload images"
        exit $ERROR
    else
        echo "##### Done creating workload images"
    fi
    echo
    popd > /dev/null 2>&1    
}
export -f create_workload_images

function create_orchestrator_images {
    CB_DISTROS_LIST=$1

    if [[ $CB_DISTROS_LIST == "all" ]]
    then
        CB_DISTROS_LIST=ubuntu' 'centos
    fi

    echo "##### Creating orchestrator images.."
    ERROR=0
    pushd $CB_KVMQEMU_BIMG_DIR > /dev/null 2>&1

    for _CB_DISTRO in $CB_DISTROS_LIST
    do

        if [[ $CB_ALLINONE -eq 0 ]]
        then
            CB_KVMQEMU_OIMG_FN=cb_orchestrator_${_CB_DISTRO}
            cp -f cb_base_${_CB_DISTRO} ${CB_KVMQEMU_OIMG_FN}            
        else
            CB_KVMQEMU_OIMG_FN=cb_all_in_one_${_CB_DISTRO}
            sudo ls ${CB_KVMQEMU_OIMG_FN} > /dev/null 2>&1
            if [[ $? -ne 0 ]]
            then
                 cp -f cb_base_${_CB_DISTRO} ${CB_KVMQEMU_OIMG_FN}
             fi            
        fi                            

        rsync -a rsync://$CB_RSYNC_DIRECT/util/cbrsync.sh > /dev/null 2>&1
        if [[ $? -eq 0 ]]
        then
            if [[ $CB_ALLINONE -ne 0 ]]
            then
                CMD="cd /home/${CB_USERNAME}; rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/ /home/${CB_USERNAME}/$CB_BASE_DIR/;"
            else
                CMD="cd /home/${CB_USERNAME}; rsync -a rsync://$CB_RSYNC_DIRECT/ --exclude 3rd_party/workload/ --exclude 3rd_party/workload/ --exclude old_data/ --include=configs/cloud_definitions.txt --include configs/build*.sh --include configs/generated/ --include=configs/templates/ --exclude=configs/* --exclude tsam/ --exclude data/ --exclude jar/ --exclude windows/ /home/${CB_USERNAME}/$CB_BASE_DIR/;"                        
            fi
        else
            CMD=""
        fi

        CMD=$CMD"chown -R ${CB_USERNAME}:${CB_USERNAME} /home/${CB_USERNAME};"
        CMD=$CMD"sudo -u $CB_USERNAME /home/$CB_USERNAME/$CB_BASE_DIR/install -r orchestrator"
        echo "####### Creating orchestrator image \"${CB_KVMQEMU_OIMG_FN}\" by executing the command \"$CMD\""        
        sudo virt-customize -a ${CB_KVMQEMU_OIMG_FN} $CB_VERB --hostname cbinst \
        --run-command "echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections" \
        --upload /tmp/cache_resolve_dns:/root/cache_resolve_dns \
        --upload $CB_KVMQEMU_S_DIR/base/installrlibs.R:/usr/local/bin/installrlibs \
        --run-command "sudo -u $CB_USERNAME /usr/local/bin/tempconfigetchosts" \
        --run-command "$CMD" \
        --install r-base-core,expect,xfce4,xfce4-goodies,tightvncserver \
        --run-command "sudo -u $CB_USERNAME /usr/local/bin/preinjectkeys /home/${CB_USERNAME}/$CB_BASE_DIR $CB_USERNAME" \
        --run-command "sudo chmod +x /usr/local/bin/installrlibs" \
        --run-command "/usr/local/bin/installrlibs" \
        --run-command "sudo cp -f /etc/hosts.original /etc/hosts"
        COUT=$?
        if [[ $COUT -ne 0 ]]
        then
            echo "############## ERROR: orchestrator image \"${CB_KVMQEMU_OIMG_FN}\" failed while executing command \"$CMD\""
        else
            echo "############## INFO: orchestrator image \"${CB_KVMQEMU_OIMG_FN}\" built successfully!!!"
        fi
        let ERROR+=$COUT
    done

    if [[ $ERROR -ne 0 ]]
    then
        echo "##### Failure while creating orchestrator images"
        exit $ERROR
    else
        echo "##### Done creating orchestrator images"
    fi
    echo
    popd > /dev/null 2>&1
}
export -f create_orchestrator_images
