#!/bin/bash
mkdir -p ~/.gucn
sudo ls ~/.gucn/unique_cloud_name > /dev/null 2>&1
if [[ $? -eq 0 ]]
then
    sudo cat ~/.gucn/unique_cloud_name
else
    sudo bash -c "echo $(pwgen 8 1) | tr '[:lower:]' '[:upper:]' > ~/.gucn/unique_cloud_name"
    mkdir -p ~/.gucn
    sudo cat ~/.gucn/unique_cloud_name
fi