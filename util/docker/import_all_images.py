#!/usr/bin/env python

from os import access, F_OK
from sys import argv
import docker
import wget

def main() :
    
    _usage = argv[0] + " docker_host_ip1[,docker_host_ip2,..,docker_host_ipn]"    

    if len(argv) != 2 :
        print _usage
        exit(1)    

    _endpoint_port = 2375    
    _images_base_dir = "/tmp"
    _images_base_url = "http://9.2.212.67/repo/vmimages/"
    _images_arch = "x86_64"
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

    _images_cksum = _images_base_url + "/cloudbench/" + _images_arch + "/md5sum.txt"
    
    for _image in _images_names :
        if not access(_images_base_dir + "/cb_" + _image + ".tar", F_OK) :
            _image_url = _images_base_url + "/cloudbench/" + _images_arch + "/cb_" + _image + ".tar"
            _msg = "Downloading from URL \"" + _image_url + "\"..."
            print _msg
            wget.download(_image_url, out = _images_base_dir + "/cb_" + _image + ".tar")    
            print " "

    print " " 
    for _endpoint in argv[1].split(',') :
        _cli = docker.Client(base_url="tcp://" + _endpoint + ':' + str(_endpoint_port), timeout = 600)
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