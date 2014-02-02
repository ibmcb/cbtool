#!/usr/bin/env bash

if [ x"$1" == x ] ; then
	echo "specify keyword for daemon to restart in foreground..."
	exit 1
fi

key=$1
shift
pids=$(pgrep -f "$key")

if [ x"$pids" == x ] ; then
	echo "no daemons available with key '$key'"
	exit 1
fi


cmd=""

for pid in $pids ; do
	if [ $pid != $$ ] && [ $pid != $PPID ] ; then
		cmd="$(cat /proc/$pid/cmdline  | sed -e 's/--/ --/g' | sed 's/^python//g' | sed -e 's/ --daemon//g' | sed -e 's/ --debug.*//g')"
		if [ x"$(echo "$cmd" | grep -Eo '(cbact|tac.py)')" != x ] ; then 
			echo "killing pid $pid"
			echo "kill $pid; cmd: $cmd"
			kill -9 $pid
			break
		fi
	fi
done

if [ x"$cmd" == x ] ; then
	echo "no valid pid found to restart for '$key'"
	exit 1
fi

$cmd $@

if [ $? -gt 0 ] ; then
	echo "command failed, re-daemonizing"
	$cmd --daemon
fi
