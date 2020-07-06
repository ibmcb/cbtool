#!/usr/bin/env python3

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

'''
    Created on Dec 15, 2010

    General purpose connection to remote machines with through ssh

    @author: Marcio A. Silva, Michael R. Galaxy
'''

from time import sleep
from subprocess import PIPE,Popen
import base64
import hashlib
import binascii
from os.path import isdir
import re

from ..auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from ..auxiliary.data_ops import wait_on_process
from ..remote.process_management import ProcessManagement

class SSHMgdConn :
    '''
    TBD
    '''
    
    def __init__(self, procid, obj_types, obj_tags, obj_ips, obj_logins, \
                 passwords, priv_keys, command_list, file_list) :
        '''
        TBD
        '''
        self.pid = procid
        self.obj_types = obj_types
        self.obj_tags = obj_tags
        self.ips = obj_ips
        self.logins = obj_logins
        self.priv_keys = priv_keys
        self.file_list = file_list
        self.command_list = command_list
        
    def finish_up (self, procs, output_list, results) :
        '''
        TBD
        '''
        success = True 
        for proc in procs :
            if success :
                if not wait_on_process(self.pid, proc, output_list) :
                    success = False 
                else :
                    if results is not None :
                        results.append(output_list[-1])
            else :
                proc.kill()
        return success
    
    def execute(self) :
        '''
        TBD
        '''
        
        output_list = []
        procs = []
        
        for index in range (0, len(self.ips)) :
            if self.command_list[index].strip() == "" :
                _msg = "nothing to execute."
                cbwarn(_msg)
                output_list.append(_msg)
                continue
                
            _cmd = "ssh -i " + self.priv_keys[index]
            _cmd += " -o StrictHostKeyChecking=no "
            _cmd += "-o UserKnownHostsFile=/dev/null "
            _cmd += "-l " + self.logins[index] + " "
            _cmd += self.ips[index] + " \"" + self.command_list[index] + "\""
            _msg = "SSH: " + _cmd
            cbdebug(_msg)
            proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
            if not proc_h :
                _msg = "Failed to create subprocess with " + _cmd
                cberr(_msg)
                return False
            procs.append(proc_h)
        
        return self.finish_up(procs, output_list, None), output_list
    
    def transfer(self) :
        '''
        TBD
        '''
        output_list = []
        procs = []
        file_list = ""
        hash_file_list = ""
        remote_file_list = []
        for file in self.file_list :
            file_list += " " + file + " "
            if not isdir(file) :
                hash_file_list += " " + file.split("/")[-1]
                remote_file_list.append(file)
            
        hash_cmd = "for file in " + hash_file_list + "; do sha256sum \$file | " + \
            "sed -e 's/ \+/,/g'; done"
        
        for index in range (0, len(self.ips)) :
            _cmd = "scp -i " + self.priv_keys[index] + " -o StrictHostKeyChecking=no "
            _cmd += file_list + " " + self.logins[index] + '@' + self.ips[index] + ":"
            _msg = "SCP: " + _cmd
            cbdebug(_msg)
            proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
            if not proc_h :
                _msg = "Failed to create subprocess with " + _cmd
                cberr(_msg)
                return False
            procs.append(proc_h)
            
        status = self.finish_up(procs, output_list, None)
                
        if not status :
            return status, output_list
        
        _msg = " - Going to verify SCP file integrity..."
        cbdebug(_msg)
        output_list = []
        procs = []
        
        for index in range (0, len(self.ips)) :
            _cmd = "ssh -i " + self.priv_keys[index] + " -o StrictHostKeyChecking=no "
            _cmd += " -l " + self.logins[index] + " "
            _cmd += self.ips[index] + " \"" + hash_cmd + "\""
            _msg = "SSH: " + _cmd
            cbdebug(_msg)
            proc_h = Popen(_cmd, bufsize=-1, shell=True, stdout=PIPE, stderr=PIPE) 
            if not proc_h :
                _msg = "Failed to create subprocess with " + _cmd
                cberr(_msg)
                return False
            procs.append(proc_h)

        remote_hash_lines = []
        status = self.finish_up(procs, output_list, remote_hash_lines)
        
        if not status :
            return status, output_list
        
        for index in range (0, len(self.ips)) :
            remote_hashes = []
            for line in re.split("[\n\r]+", remote_hash_lines[index]) : 
                if line != "" :
                    record = line.split(',')
                    if len(record) != 2 :
                        _msg = "integrity check failed: not enough hashes: "
                        _msg += str(remote_hash_lines[index])
                        cberr(_msg)
                        return False, output_list
                    remote_hashes.append(record[0])
                    
            for file_index in range (0, len(remote_file_list)) :
                local_file = remote_file_list[file_index]
                if isdir(local_file) :
                    continue
                remote_hex = remote_hashes[file_index]
                local_hex = ""
                
                try :
                    local_hash = hashlib.sha256()
                    local_hash.update(open(local_file, 'r').read())
                    local_hex = local_hash.hexdigest()
                except Exception as msg :
                    _msg = "Failed to verify SCP integrity: " + str(msg)
                    cberr(_msg)
                    return False, output_list
                
                if local_hex != remote_hex :
                    _msg = "Integrity failed for " + local_file + ": "
                    _msg += local_hex + " != " + remote_hex
                    cberr(_msg)
                    return False, output_list
            
            _msg = self.ips[index] + ": Good file integrity."
            cbdebug(_msg)
            
        return status, output_list
    
def repeated_ssh(processid, types, tags, ips, logins, passwds, keys, commands, \
                 files, obj_attr_list, operation) :
    '''
    TBD
    '''
    ssh_cnt = SSHMgdConn(processid, types, tags, ips, logins, passwds, keys, \
                         commands, files)

    attempts = int(obj_attr_list["update_attempts"])
                
    while attempts :
        # Finally we try to start the application on each VM.
        if operation == "transfer" :
            _success, _stack_results = ssh_cnt.transfer()
        else :
            _success, _stack_results = ssh_cnt.execute()

        _all_stack_results = ''
        if _success :
            for _output in _stack_results :
                if not _output or _output.count("NOK") :
                    _msg = "Command failed: " + str(_output) + ' '
                    _msg += str(attempts) + " left..."
                    cberr(_msg)
                    return False
                _all_stack_results += "-------------------------\n"       
                _all_stack_results += ''.join(_output)
            _msg = " - Remote commands for object name " + obj_attr_list["name"]
            _msg += " success. "
            cbdebug(_msg)
            break
        else :
            _msg = " - Remote commmands for object name " + obj_attr_list["name"]
            _msg += " failed to execute.\n"
                
            for _output in _stack_results :
                _all_stack_results += "-------------------------\n"
                _all_stack_results += ''.join(_output)
            _msg += "Error info:\n"
            _msg += _all_stack_results
            cberr(_msg)
            return False
            
        sleep(30)
            
        if not attempts :
            _msg = "giving up. Too many attempts."
            cberr(_msg)
            return False
        
    return True


def get_ssh_key(pub_key_fn, fptype = "common", read_from_file = True) :
    '''
    TBD
    '''

    if read_from_file :
        _fh = open(pub_key_fn, 'r')
        _pub_key = _fh.read()
        _fh.close()
    else :
        _pub_key = pub_key_fn

    _key_type = False
    _key_contents = False

    for _element in _pub_key.split() :
        if not _key_type :
            _key_type = _element
        else :
            if not _key_contents :
                _key_contents = _element
        
    if not _key_contents :
        _fmsg = "ERROR: unknown format for pubkey file. The pubkey has to be in"
        _fmsg += " the format \"<KEY-TYPE> <KEY-CONTENTS> [<KEY-USERNAME>]"
        return _fmsg, False, False

    if fptype == "Amazon Elastic Compute Cloud" or fptype == "EC2" or fptype == "ec2" :
        _key_fingerprint = key2ec2fp(pub_key_fn)    
    elif fptype == "IBM Cloud" or fptype == "IBM" or fptype == "ibm" :
        _key_fingerprint = keyibmfp(_key_contents.encode('utf-8'))
    elif fptype == "SoftLayer Cloud" or fptype == "SLR" or fptype == "slr" :
        _key_fingerprint = keyibmfp(_key_contents.encode('utf-8'))
    else :
        _key_fingerprint = key2fp(_key_contents)
                
    return _key_type, _key_contents, _key_fingerprint

def key2fp(pubkey_contents):
    '''
    TBD
    '''
    key = base64.b64decode(pubkey_contents.encode('ascii'))
    fp_plain = hashlib.md5(key).hexdigest()
    return ':'.join(a+b for a,b in zip(fp_plain[::2], fp_plain[1::2]))

def keyibmfp(pubkey_contents):
    '''
    TBD
    ''' 
    key = bytes(pubkey_contents)
    fp_plain = base64.b64encode(hashlib.sha256(binascii.a2b_base64(key)).digest()).rstrip(b'=')
    return "SHA256:" + fp_plain.decode('utf-8')

def key2ec2fp(pub_key_fn) :
    '''
    TBD
    '''
    pub_key_fn = pub_key_fn.replace(".pub",'')
    _proc_man = ProcessManagement()
    _cmdline = "openssl pkey -in " + pub_key_fn + " -pubout -outform DER | openssl md5 -c"
    _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmdline)
    return _result_stdout.strip().replace("(stdin)= ",'')
    
def get_public_rsa_fingerprint(pubkey_contents):
    """
    Returns the fingerprint of the public portion of an RSA key as a
    47-character string (32 characters separated every 2 characters by a ':').
    The fingerprint is computed using the MD5 (hex) digest of the DER-encoded
    RSA public key.
    """
    md5digest = hashlib.md5(pubkey_contents).hexdigest()
    fingerprint = insert_char_every_n_chars(md5digest, ':', 2)
    return fingerprint 

def insert_char_every_n_chars(string, char='\n', every=64):
    return char.join(string[i:i + every] for i in range(0, len(string), every)) 
