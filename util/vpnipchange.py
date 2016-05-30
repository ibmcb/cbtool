#!/usr/bin/env python

import telnetlib

tn = telnetlib.Telnet("localhost", 1195, 1)

tn.write("log all\r\n")
tn.write("exit\n")
lines = []
while True :
    try :
        lines.append(tn.read_until("\n", 1))
    except EOFError, e :
        break

tn.close

for line in lines :
    if line.count("route 10.9.0.0") :
        print line.split(" ")[10]
