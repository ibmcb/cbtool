#!/usr/bin/env python

from fcntl import ioctl
import socket
import struct
import IN

SIOCGIFMTU = 0x8921
SIOCSIFMTU = 0x8922


def path_mtu_discover() :
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    hostName = "9.186.105.50" 
    Port = 9999
    s.connect((hostName, Port))
    s.setsockopt(socket.IPPROTO_IP, IN.IP_MTU_DISCOVER, IN.IP_PMTUDISC_DO)
    option = getattr(IN, 'IP_MTU', 14)
    return s.getsockopt(socket.IPPROTO_IP, option)

def get_mtu(ifname):
    '''Use socket ioctl call to get MTU size'''
    s = socket.socket(type=socket.SOCK_DGRAM)
    
    ifr = ifname + '\x00'*(32-len(ifname))
    try:
        ifs = ioctl(s, SIOCGIFMTU, ifr)
        mtu = struct.unpack('<H',ifs[16:18])[0]
    except Exception, s:
        print 'socket ioctl call failed: {0}'.format(s)
        raise
 
    return mtu

print str(get_mtu("eth0"))
print str(path_mtu_discover())
