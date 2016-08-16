#!/usr/bin/env python

from os import access, F_OK
from sys import argv
import docker
import wget

def main() :
    
    _usage = argv[0] + " docker_host_ip1:port[,docker_host_ip2:port,..,docker_host_ipn] [images names]"    

    for _argv in argv :
        if argv.count("--help") or argv.count("-h") :
            print _usage
            exit(0)

    if len(argv) < 2 :
        print _usage
        exit(1) 

    if len(argv) > 2 :
        _image_list = argv[2]
    else :
        _image_list = "all"

    _images_base_dir = "/tmp"
    _images_base_url = "http://9.2.212.67/repo/vmimages/"
    _images_arch = "x86_64"

    if _image_list == "all" :
        _images_names = [ "nullworkload", \
                          "hadoop", \
                          "ycsb", \
                          "iperf", \
                          "netperf", \
                          "nuttcp", \
                          "fio", \
                          "xping", \
                          "speccloud_cassandra_2111", \
                          "speccloud_hadoop_271" ]
    else :
        _images_names = argv[2].split(',')

    _images_cksum = _images_base_url + "/cloudbench/" + _images_arch + "/md5sum.txt"
    
    for _image in _images_names :
        if not access(_images_base_dir + "/cb_" + _image + ".tar", F_OK) :
            _image_url = _images_base_url + "/cloudbench/" + _images_arch + "/cb_" + _image + ".tar"
            _msg = "Downloading from URL \"" + _image_url + "\"..."
            print _msg
            wget.download(_image_url, out = _images_base_dir + "/cb_" + _image + ".tar")    
            print " "

    print " " 
    
    _endpoint_list = ''
    for _endpoint in argv[1].split(',') :
        _cli = docker.Client(base_url="tcp://" + _endpoint, timeout = 600)        
        _info = _cli.info()
        if _info["SystemStatus"] :
            for _item in _info["SystemStatus"] :
                if _item[1].count(':') == 1 :
                    _endpoint_list += _item[1] + ','

    if len(_endpoint_list) :
        _endpoint_list = _endpoint_list[0:-1]    
    else :
        _endpoint_list = argv[1]
    
    _endpoint_port = 17282
    
    for _endpoint in _endpoint_list.split(',') :
        _cli = docker.Client(base_url="tcp://" + _endpoint, timeout = 600)
        for _image in _images_names :
            _image = "cb_" + _image
            if not len(_cli.images(name = _image)) :
                _image_filename = _images_base_dir + '/' + _image + ".tar" 
                
                _msg = "Loading file \"" + _image_filename + "\" into Docker image store on host \"" + _endpoint + "\"..."
                print _msg
                
                with open(_image_filename, "rb") as f:
                    _cli.load_image(f)
            else :
                _msg = "Image \"" + _image + " already present on Docker image store on host \"" + _endpoint + "\"..."
                print _msg

main()
exit(0)