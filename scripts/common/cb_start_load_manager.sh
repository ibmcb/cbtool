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

# Used for remote-debugging. Eclipse passes "--debug_host". If there are such
# options, then do not daemonize the process so that we may connect the debugger

source $(echo $0 | sed -e "s/\(.*\/\)*.*/\1.\//g")/cb_common.sh

operation="ai-execute"
daemonize=" --daemon"
options="$@"

if [[ x"$options" != x ]]
then
    daemonize=""
    for pid in $(pgrep -f $operation)
    do 
        if [[ $pid == $$ ]]
        then 
            echo skipping $pid
            continue
        fi
        
        if [[ $PPID == $pid ]]
        then 
            echo skipping parent ssh process $pid
            continue
        fi
        
        kill -9 $pid
        
    done
fi

load_manager_vm=`get_my_ai_attribute load_manager_vm`
run_application_scripts=`get_my_ai_attribute run_application_scripts`
run_application_scripts=`echo $run_application_scripts | tr '[:upper:]' '[:lower:]'`

debug_remote_commands=`get_my_ai_attribute debug_remote_commands`
debug_remote_commands=`echo $debug_remote_commands | tr '[:upper:]' '[:lower:]'`

echo $options | grep debug
if [[ $? -eq 0 ]]
then
    options=$(echo $options | sed 's/debug//g')
    sudo pkill -9 -f cbloadmanwatch
    sudo screen -wipe
    sudo pkill -9 -f "\\-\\-procid=${osprocid} \\-\\-uuid=${my_ai_uuid} \\-\\-syslogp=${NC_PORT_SYSLOG} \\-\\-syslogf=19 \\-\\-syslogr=${NC_PROTO_SYSLOG} \\-\\-syslogh=${NC_HOST_SYSLOG} \\-\\-operation=$operation"
    run_application_scripts="false"
    debug_remote_commands="true"        
fi

if [[ $run_application_scripts == "false" && $debug_remote_commands == "true" ]]
then
    daemonize="--logdest console -v 5"
fi

cat > /tmp/cbloadman <<EOF
#!/usr/bin/env bash

CBLOADMANEXEC="~/${my_remote_dir}/cbact"
eval CBLOADMANEXEC=\${CBLOADMANEXEC}
CBLOADMANBASECMD="\$CBLOADMANEXEC --procid=${osprocid} --uuid=${my_ai_uuid} --syslogp=${NC_PORT_SYSLOG} --syslogf=19 --syslogr=${NC_PROTO_SYSLOG} --syslogh=${NC_HOST_SYSLOG} --operation=$operation"
if [[ -z \$1 ]]
then
    if [[ \$(sudo ps aux | grep -v grep | grep cbact | grep -c ai-execute) -eq 0 ]]
    then
	CBLOADMANCMD="\$CBLOADMANBASECMD -v 5 $daemonize $options"    
        echo "Starting Load Manager with command \"\$CBLOADMANCMD\""
        \$CBLOADMANCMD
    else
        echo "A Load Manager is already running"
    fi
else 
    if [[ \$(echo \${1} | tr '[:upper:]' '[:lower:]') == "debug" ]]
    then
        echo "CBTOOL Load Manager will be started in DEBUG mode. All output will be sent to the console"
        echo "Killing the \"Load Manager Watcher\" process (a screen session)..."
        sudo screen -X -S cbloadmanwatch  quit
        sudo pkill -9 -f cbloadmanwatch
        echo "Done"
        CBLOADMANCMD="\$CBLOADMANBASECMD --logdest console -v 5 $options"
        echo "Starting Load Manager with command \"\$CBLOADMANCMD\""
        \$CBLOADMANCMD
    fi
fi
exit 0
EOF

sudo mv /tmp/cbloadman /usr/local/bin/cbloadman
sudo chmod 755 /usr/local/bin/cbloadman

if [[ x"${load_manager_vm}" == x"${my_vm_uuid}" ]]
then
    if [[ $run_application_scripts == "false" && $debug_remote_commands == "true" ]]
    then
        syslog_netcat "The command \"appdev\" was run on the orchestrator. Please start the Load Manager in debug mode by running /usr/local/bin/cbloadman"    
    else        
        running_load_managers=`pgrep -f $operation`
    
        if [[ x"${running_load_managers}" == x ]]
        then
            syslog_netcat "Starting Load Manager"
            /usr/local/bin/cbloadman

            sudo pkill -9 -f cbloadmanwatch
            sudo screen -d -m -S cbloadmanwatch bash -c "su - ${my_login_username}"
            sudo screen -p 0 -S cbloadmanwatch -X stuff "while true ; do sleep 30; /usr/local/bin/cbloadman; done$(printf \\r)"                        
    
            exit 0
        else
            syslog_netcat "A Load Manager is already running"
            exit 2
        fi
    fi
else
    syslog_netcat "This VM is not designated as Load Manager"
fi
exit 0
exit 0
