#!/bin/bash

if [[ ! -z $1 ]]
then
    CB_USERNAME=$1
else
    CB_USERNAME=$USER
fi

if [[ -z $2 ]]
then
    if [ $0 != "-bash" ] ; then
        pushd `dirname "$0"` 2>&1 > /dev/null
    fi
    
    CB_BASE_DIR=$(pwd)
    
    if [ $0 != "-bash" ] ; then
        popd 2>&1 > /dev/null
    fi
    CB_BASE_DIR=$(echo $CB_BASE_DIR | sed 's^/configs^^g' | sed 's^/private_configs^^g')
else
    CB_BASE_DIR=$2
fi

CB_PRIVATE_CONFIG=${CB_PRIVATE_CONFIG:-0}
CB_PRIVATE_DATA=${CB_PRIVATE_DATA:-0}

if [[ $CB_PRIVATE_CONFIG -eq 1 && ! -d $CB_BASE_DIR/configs ]]
then
    mv $CB_BASE_DIR/private_configs $CB_BASE_DIR/configs
fi

if [[ -z $3 ]]
then
    CB_DEFAULT_OBJECTSTORE_PORT=6379
    CB_DEFAULT_OBJECTSTORE_USAGE=shared
    CB_DEFAULT_LOGSTORE_PORT=5114
    CB_DEFAULT_METRICSTORE_PORT=27017
    CB_DEFAULT_METRICSTORE_USAGE=shared
    CB_DEFAULT_FILESTORE_PORT=873
    CB_DEFAULT_API_DEFAULTS_PORT=7070
    CB_DEFAULT_GUI_DEFAULTS_PORT=8080
    CB_DEFAULT_VPN_SERVER_PORT=1194
else
    CB_DEFAULT_OBJECTSTORE_PORT=30000
    CB_DEFAULT_OBJECTSTORE_USAGE=private
    CB_DEFAULT_LOGSTORE_PORT=30001
    CB_DEFAULT_METRICSTORE_PORT=30002
    CB_DEFAULT_METRICSTORE_USAGE=private
    CB_DEFAULT_FILESTORE_PORT=30003
    CB_DEFAULT_API_DEFAULTS_PORT=30004
    CB_DEFAULT_GUI_DEFAULTS_PORT=30005
    CB_DEFAULT_VPN_SERVER_PORT=30006
fi

if [[ $CB_PRIVATE_CONFIG -eq 0 && -d $CB_BASE_DIR ]]
then
    sudo ls $CB_BASE_DIR/private_configs/ > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        sudo rsync -az $CB_BASE_DIR/private_configs/ $CB_BASE_DIR/configs/
    fi
fi

if [[ $CB_PRIVATE_DATA -eq 1 || ! -d $CB_BASE_DIR/data ]]
then
    sudo mkdir $CB_BASE_DIR/data
fi

if [[ $CB_PRIVATE_DATA -eq 0 && -d $CB_BASE_DIR/data ]]
then
    sudo ls $CB_BASE_DIR/private_data/ > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then    
        sudo rsync -az $CB_BASE_DIR/private_data/ $CB_BASE_DIR/data/
    fi
fi

if [[ -z $CB_USERNAME ]]
then
    CB_USERNAME=$(whoami)
fi

CB_CONFIG_FILE=$CB_BASE_DIR/configs/${CB_USERNAME}_cloud_definitions.txt

sudo chown -R $CB_USERNAME:$CB_USERNAME $CB_BASE_DIR

echo "START: Building private cloud configuration file \"$CB_CONFIG_FILE\" combining both \"$CB_BASE_DIR/configs/cloud_definitions.txt\" and environment variables (all variables start with \"CB_\")"  
    
cat $CB_BASE_DIR/configs/cloud_definitions.txt | sed '/# END: Specify the individual parameters for each cloud/,$d' > $CB_CONFIG_FILE

CB_MANAGER_IP=${CB_MANAGER_IP:-\$IP_AUTO}
echo "    Setting the parameter \"MANAGER_IP\", on the \"[USER-DEFINED]\" section to \"$CB_MANAGER_IP\""
sed -i "s/MANAGER_IP.*/MANAGER_IP = ${CB_MANAGER_IP}/g" $CB_CONFIG_FILE

CB_STARTUP_CLOUD=${CB_STARTUP_CLOUD:-MYSIM}
if [[ $CB_STARTUP_CLOUD != "NONE" ]]
then
    echo "    Setting the parameter \"STARTUP_CLOUD\", on the \"[USER-DEFINED]\" section to \"$CB_STARTUP_CLOUD\""
    sed -i "s/STARTUP_CLOUD.*/STARTUP_CLOUD = ${CB_STARTUP_CLOUD}/g" $CB_CONFIG_FILE
fi

CB_OBJECTSTORE_HOST=${CB_OBJECTSTORE_HOST:-\$MANAGER_IP}
CB_OBJECTSTORE_PORT=${CB_OBJECTSTORE_PORT:-$CB_DEFAULT_OBJECTSTORE_PORT}
CB_OBJECTSTORE_DBID=${CB_OBJECTSTORE_DBID:-15}
CB_OBJECTSTORE_USAGE=${CB_OBJECTSTORE_USAGE:-$CB_DEFAULT_OBJECTSTORE_USAGE}

CB_LOGSTORE_HOST=${CB_LOGSTORE_HOST-\$MANAGER_IP}
CB_LOGSTORE_PORT=${CB_LOGSTORE_PORT:-$CB_DEFAULT_LOGSTORE_PORT}
CB_LOGSTORE_VERBOSITY=${CB_LOGSTORE_VERBOSITY:-5}
CB_LOGSTORE_USAGE=${CB_LOGSTORE_USAGE:-private}

CB_METRICSTORE_HOST=${CB_METRICSTORE_HOST-\$MANAGER_IP}
CB_METRICSTORE_PORT=${CB_METRICSTORE_PORT:-$CB_DEFAULT_METRICSTORE_PORT}
CB_METRICSTORE_DATABASE=${CB_METRICSTORE_DATABASE:-metrics}
CB_METRICSTORE_USAGE=${CB_METRICSTORE_USAGE:-$CB_DEFAULT_METRICSTORE_USAGE}

CB_FILESTORE_HOST=${CB_FILESTORE_HOST-\$MANAGER_IP}
CB_FILESTORE_PORT=${CB_FILESTORE_PORT:-$CB_DEFAULT_FILESTORE_PORT}
CB_FILESTORE_USAGE=${CB_FILESTORE_USAGE:-private}

CB_API_DEFAULTS_HOST=${CB_API_DEFAULTS_HOST-\$MANAGER_IP}
CB_API_DEFAULTS_PORT=${CB_API_DEFAULTS_PORT:-$CB_DEFAULT_API_DEFAULTS_PORT}

CB_GUI_DEFAULTS_HOST=${CB_GUI_DEFAULTS_HOST-\$MANAGER_IP}
CB_GUI_DEFAULTS_PORT=${CB_GUI_DEFAULTS_PORT:-$CB_DEFAULT_GUI_DEFAULTS_PORT}

CB_VPN_START_SERVER=${CB_VPN_START_SERVER:-\$False}
CB_VPN_SERVER_IP=${CB_VPN_SERVER_IP:-\$MANAGER_IP}
CB_VPN_SERVER_PORT=${CB_VPN_SERVER_PORT:-$CB_DEFAULT_VPN_SERVER_PORT}
CB_VPN_NETWORK=${CB_VPN_NETWORK:-192.168.0.0}
CB_VPN_NETMASK=${CB_VPN_NETMASK:-255.255.0.0}

CB_ATTACH_STARTUP_CLOUD=${CB_ATTACH_STARTUP_CLOUD:-1}

echo "" >> $CB_CONFIG_FILE
echo "[OBJECTSTORE]" >> $CB_CONFIG_FILE
echo "HOST=${CB_OBJECTSTORE_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_OBJECTSTORE_PORT}" >> $CB_CONFIG_FILE
echo "DBID=${CB_OBJECTSTORE_DBID}" >> $CB_CONFIG_FILE
echo "USAGE=${CB_OBJECTSTORE_USAGE}" >> $CB_CONFIG_FILE
echo "" >> $CB_CONFIG_FILE
echo "[LOGSTORE]" >> $CB_CONFIG_FILE
echo "HOST=${CB_LOGSTORE_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_LOGSTORE_PORT}" >> $CB_CONFIG_FILE
echo "VERBOSITY=${CB_LOGSTORE_VERBOSITY}" >> $CB_CONFIG_FILE
echo "USAGE=${CB_LOGSTORE_USAGE}" >> $CB_CONFIG_FILE
echo "" >> $CB_CONFIG_FILE
echo "[METRICSTORE]" >> $CB_CONFIG_FILE
echo "HOST=${CB_METRICSTORE_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_METRICSTORE_PORT}" >> $CB_CONFIG_FILE
echo "DATABASE=${CB_METRICSTORE_DATABASE}" >> $CB_CONFIG_FILE
echo "USAGE=${CB_METRICSTORE_USAGE}" >> $CB_CONFIG_FILE
if [[ ! -z $CB_METRICSTORE_PASSWORD ]]
then
    echo "PASSWORD = $CB_METRICSTORE_PASSWORD" >> $CB_CONFIG_FILE
fi
echo "" >> $CB_CONFIG_FILE
echo "[FILESTORE]" >> $CB_CONFIG_FILE
echo "HOST=${CB_FILESTORE_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_FILESTORE_PORT}" >> $CB_CONFIG_FILE
echo "USAGE=${CB_FILESTORE_USAGE}" >> $CB_CONFIG_FILE
echo "" >> $CB_CONFIG_FILE
echo "[API_DEFAULTS]" >> $CB_CONFIG_FILE
echo "HOST=${CB_API_DEFAULTS_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_API_DEFAULTS_PORT}" >> $CB_CONFIG_FILE
echo "" >> $CB_CONFIG_FILE
echo "[GUI_DEFAULTS]" >> $CB_CONFIG_FILE
echo "HOST=${CB_GUI_DEFAULTS_HOST}" >> $CB_CONFIG_FILE
echo "PORT=${CB_GUI_DEFAULTS_PORT}" >> $CB_CONFIG_FILE
echo "" >> $CB_CONFIG_FILE
echo "[VPN]" >> $CB_CONFIG_FILE
echo "START_SERVER=${CB_VPN_START_SERVER}" >> $CB_CONFIG_FILE
echo "SERVER_IP=${CB_VPN_SERVER_IP}" >> $CB_CONFIG_FILE
echo "SERVER_PORT=${CB_VPN_SERVER_PORT}" >> $CB_CONFIG_FILE
echo "NETWORK=${CB_VPN_NETWORK}" >> $CB_CONFIG_FILE
echo "NETMASK=${CB_VPN_NETMASK}" >> $CB_CONFIG_FILE

for cmodel in SIM PLM PDM PCM KUB NOP OSK OS CSK VCD EC2 SLR GCE DO AS
do
    for param in ACCESS CREDENTIALS SECURITY_GROUPS INITIAL_VMCS SSH_KEY_NAME NETNAME POOLNAME NETNAME LOGIN
    do
        cb_env_var_name=CB_${cmodel}_${param}
        cb_env_var_value=$(echo ${!cb_env_var_name})
        if [[ ! -z ${!cb_env_var_name} ]]
        then
            echo "    Setting the parameter \"$param\", on the \"[USER-DEFINED : CLOUDOPTION_MY${cmodel}]\" section to \"${!cb_env_var_name}\""
            sed -i "s^${cmodel}_${param}.*^${cmodel}_${param} = ${!cb_env_var_name}^g" $CB_CONFIG_FILE
        fi
    done
done
    
for obj in MON_DEFAULTS VMC_DEFAULTS VM_DEFAULTS AI_DEFAULTS AIDRS_DEFAULTS
do
    for cmodel in EMPTY SIM PLM PDM PCM KUB NOP OSK OS CSK VCD EC2 SLR GCE DO AS
    do
        section_exists=0
        for param in EMPTY REMOTE_DIR_NAME RUN_NETNAME PROV_NETNAME EXECUTE_SCRIPT_NAME CHECK_BOOT_STARTED CHECK_BOOT_COMPLETE TRANSFER_FILES CHECK_SSH RUN_GENERIC_SCRIPTS RUN_APPLICATION_SCRIPTS UPDATE_FREQUENCY DONT_START_LOAD_MANAGER LEAVE_INSTANCE_ON_FAILURE PORTS_BASE USE_VPN_IP USE_FLOATING_IP FLOATING_POOL EXPLICIT_VOLUME_CREATION USE_JUMPHOST JUMPHOST_IP JUMPHOST_LOGIN COLLECT_FROM_GUEST PORT VPC_NAME IMAGE_PREFIX IMAGE_SUFFIX ARCH EMULATOR
        do
            cb_env_var_name=CB_${obj}_${cmodel}_${param}
            cb_env_var_name=$(echo $cb_env_var_name | sed 's/_EMPTY//g')
            cb_section_name="[${obj} : ${cmodel}_CLOUDCONFIG]"
            cb_section_name=$(echo $cb_section_name | sed 's/ : EMPTY_CLOUDCONFIG//g')
            if [[ ! -z ${!cb_env_var_name} ]]
            then
                echo "    Setting the parameter \"$param\", on the section \"$cb_section_name\" to \"${!cb_env_var_name}\""
                if [[ $section_exists -eq 0 ]]
                then
                    echo "" >> $CB_CONFIG_FILE
                    echo "$cb_section_name" >> $CB_CONFIG_FILE
                    section_exists=1
                fi
                echo "${param} = ${!cb_env_var_name}" >> $CB_CONFIG_FILE
            fi
        done
    done
done

if [[ ! -z $CB_CLOUD_RENAME ]]
then
    if [[ $CB_CLOUD_RENAME == "AUTO" ]]
    then
        which gucn 2>&1 > /dev/null
        if [[ $? -eq 0 ]]
        then
            CB_CLOUD_RENAME=MYCLOUD$(gucn)
        else
            CB_CLOUD_RENAME=CB$(cat /dev/urandom | tr -dc 'a-zA-Z' | fold -w 8 | head -n 1 | tr '[:lower:]' '[:upper:]')
        fi
    fi
    
    echo "    Renaming STARTUP_CLOUD \"$CB_STARTUP_CLOUD\" to \"$CB_CLOUD_RENAME\""
    sed -i "s/$CB_STARTUP_CLOUD/$CB_CLOUD_RENAME/g" $CB_CONFIG_FILE
fi

if [[ $CB_ATTACH_STARTUP_CLOUD -eq 0 ]]
then
    sed -i "s/.*STARTUP_CLOUD/#STARTUP_CLOUD/g" $CB_CONFIG_FILE    
fi

echo "END: Built private cloud configuration file \"$CB_CONFIG_FILE\" combining both \"$CB_BASE_DIR/configs/cloud_definitions.txt\" and environment variables (all variables start with \"CB_\")"
