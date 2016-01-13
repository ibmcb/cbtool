#!/usr/bin/env python

import time, subprocess, signal, datetime, os, sys

_timeout = int(sys.argv[-1])
_commands = ' '.join(sys.argv[1:-1]).split(',')
_attempts = 3

for _command in _commands :
    _current_attempts = 1
    _complete = False
    while _current_attempts <= _attempts and not _complete :
        _complete = True
        start = datetime.datetime.utcnow()
        process = subprocess.Popen(_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() is None :
            time.sleep(0.1)
            now = datetime.datetime.utcnow()
            if (now - start).seconds > _timeout:
                os.kill(process.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
                print "Command \"" + _command + "\" did not respond within " + str(_timeout) + " seconds (attempt " + str(_current_attempts) + " of " + str(_attempts) + ")."
                _current_attempts += 1
                _complete = False
                break

if _current_attempts > _attempts :
    print "Command \"" + _command + "\" failed to complete within " + str(_timeout) + " seconds after " + str(_attempts) + " attempts."
    exit(1)
else :
    print process.stdout.read()
    exit(process.returncode)
