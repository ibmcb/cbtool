#!/usr/bin/env bash

source ~/.bashrc

SIM_TENANT_NAME=cb-tenant
SIM_USER_NAME=cb-user
SIM_NETWORK_NAME=cb-tenantnet
SIM_SUBNETWORK_NAME=cb-subtenantnet
SIM_ROUTER_NAME=cb-router
SIM_LBPOOL_NAME=cb-lbpool
SIM_LBVIP_NAME=cb-lbvip
SIM_LBMEMBER_NAME=cb-lbmember
SIM_LB_PROTOCOL=TCP
SIM_LB_PROTOCOL_PORT=22

TNSRC_ERROR=0

function all_clear () {
	/bin/true
}

MY_PATH="`dirname \"$0\"`"
MY_PATH="`( cd \"$MY_PATH\" && pwd )`"
RC_PATH=${MY_PATH}/../../configs/generated/
RC_PATH="`( cd \"$RC_PATH\" && pwd )`"
source $RC_PATH/$(whoami)_cb_lastcloudrc
all_clear