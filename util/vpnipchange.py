#!/usr/bin/env python3

import telnetlib

tn = telnetlib.Telnet("localhost", 1195, 1)

tn.write(b"log all\r\n")
tn.write(b"exit\n")
lines = []
while True :
    try :
        lines.append(tn.read_until(b"\n", 1).decode("utf-8"))
    except EOFError as e :
        break

tn.close

for line in lines :
    if line.count("route 10.9.0.0") :
        print(line.split(" ")[10])
