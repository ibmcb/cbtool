#!/usr/bin/env bash

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************


# Standalone application initialization script:
#
# Run this inside each VM to transform into the appropriate tier
# Run with no options to determine correct parameters

dir=$(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")
tier=$1
shift

options="client_daytrader, client_tradelite, client_specweb, client_lost, was, db2, loadbalancer, specwebfront, specwebback, lostfront, lostback"

if [ x"$tier" == x ] ; then
	echo "Need tier type of this VM (options: $options)"
	exit 1
fi

# client and db2 require to run as klabuser, perhaps others
function require_klabuser {
	if [ $(whoami) != klabuser ] ; then
		echo "This tier type must be run as the 'klabuser' account.  Please 'su klabuser' and try again."
		exit 1
	fi
}

case "$tier" in 
	client_daytrader )
		require_klabuser
		$dir/../daytrader/cb_daytrader.sh reserved reserved reserved offline $@
		;;
	client_tradelite )
		require_klabuser
		$dir/../tradelite/cb_tradelite.sh reserved reserved reserved offline $@
		;;
	was )
		app=$1
		shift
		if [ x"$app" != x"daytrader" ] && [ x"$app" != x"tradelite" ] ; then
			echo "Which websphere application? options: [daytrader | tradelite]"
			exit 1
		fi

		$dir/../$app/cb_restart_was.sh offline $@
		;;
	db2 )
		require_klabuser
		$dir/../daytrader/cb_restart_db2.sh offline 
		;;
	loadbalancer )
		$dir/cb_restart_loadbalancer.sh offline $@
		;;
	client_specweb )
		require_klabuser
		$dir/../specweb/cb_specrun.sh reserved reserved reserved offline $@
		;;
	specwebfront )
		$dir/../specweb/cb_restart_webserver.sh offline $@
		;;
	specwebback )
		$dir/../specweb/cb_restart_webserver.sh offline $@
		;;
	client_lost )
		sudo su -c "hostname client"
		$dir/../lost/cb_setup_mysql.sh offline $@
		$dir/../lost/cb_restart_autobench.sh offline $@
		$dir/../lost/cb_lostrun.sh reserved reserved reserved offline $@
		;;
	lostfront )
		sudo su -c "hostname web"
		$dir/../lost/cb_setup_lostfront.sh offline $@
		$dir/../lost/cb_restart_autobench.sh offline $@
		;;
	lostback )
		sudo su -c "hostname be"
		$dir/../lost/cb_setup_mysql.sh offline $@
		$dir/../lost/cb_restart_autobench.sh offline $@
		;;
	* )
		echo "unknown tier type. (options: $options)"
		;;
esac
