#!/usr/bin/env bash

source ./build_common.sh

CB_REPO=NONE
CB_RSYNC=$(sudo ifconfig docker0 | grep "inet addr" | cut -d ':' -f 2 | cut -d ' ' -f 1):10000/$(whoami)_cb
CB_WKS="ALL"
CB_UBUNTU_BASE=ubuntu:16.04
CB_PHUSION_BASE=phusion/baseimage:latest
CB_CENTOS_BASE=centos:latest
CB_VERB="-q"
CB_PUSH="nopush"
CB_ARCH=$(uname -a | awk '{ print $12 }')
CB_PALL=0
CB_USAGE="Usage: build_all.sh -r <repository> [-u Ubuntu base image] [-p Phusion base image] [-c Centos base image] [-w Workload] [--verbose] [--push] [--psall]"

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -r|--repo)
        CB_REPO="$2"
        shift
        ;;
        -r=*|--repo=*)
        CB_REPO=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -u|--ubuntubase)
        CB_UBUNTU_BASE="$2"
        shift
        ;;
        -u=*|--ubuntubase=*)
        CB_UBUNTU_BASE=$(echo $key | cut -d '=' -f 2)
        shift
        ;;        
        -p|--phusionbase)
        CB_PHUSION_BASE="$2"
        shift
        ;;
        -p=*|--phusionbase=*)
        CB_PHUSION_BASE=$(echo $key | cut -d '=' -f 2)
        shift
        ;;        
        -c|--centosbase)
        CB_CENTOS_BASE="$2"
        shift
        ;;
        -c=*|--centosbase=*)
        CB_CENTOS_BASE=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -w|--workload)
        CB_WKS="$2"
        shift
        ;;
        -w=*|--workload=*)
        CB_WKS=$(echo $key | cut -d '=' -f 2)
        shift
        ;;        
        -a|--arch)
        CB_ARCH="$2"
        shift
        ;;
        -a=*|--arch=*)
        CB_ARCH=$(echo $key | cut -d '=' -f 2)
        shift
        ;;
        -r|--rsync)
        CB_RSYNC="$2"
        shift
        ;;
        -r=*|--rsync=*)
        CB_RSYNC=$(echo $key | cut -d '=' -f 2)
        shift
        ;;                     
        -v|--verbose)
        CB_VERB='--ve'
        shift
        ;;
        --push)
        CB_PUSH="push"
        ;;
        --psall)
        CB_PUSH="push"
        CB_PALL=1
        ;;        
        -h|--help)
        echo $CB_USAGE
        shift
        ;;
        *)
                # unknown option
        ;;
        esac
        shift
done

if [[ $CB_REPO == NONE ]]
then
	echo $USAGE
    exit 1
fi

cb_build_orchestrator $CB_REPO $CB_VERB $CB_ARCH $CB_RSYNC

if [[ $CB_PUSH == "push" ]]
then
    cb_push_images $CB_REPO $CB_PALL
fi