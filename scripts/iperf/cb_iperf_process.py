#!/usr/bin/env python3

import os
from sys import path, argv

_fn = argv[1]

if os.access(_fn, os.F_OK) :
    _fh = open(_fn, "r")
    _fc = _fh.readlines()
    _fh.close()

_bw = False
_jitter = 0
_loss = 0
_flows = 0
_datagrams = 0

for _line in _fc :
    _line = _line.replace("/ ",'/')

    if _line.count(" local ") :
        _flows += 1

    if _line.count("SUM") and not _line.count("datagrams"):
        _bw = _line.split()[5]
    else :
        if _line.count("ms") :
            if _line.count("/sec") :
                _xline = _line.split()

                if not _bw :
                    _idx = _xline.index("Mbits/sec") - 1
                    _bw = _xline[_idx]

                _idx = _xline.index("ms") - 1
                _jitter += float(_xline[_idx])

                _idx = _idx + 2
                _loss += int(_xline[_idx].split('/')[0])
                _datagrams += int(_xline[_idx].split('/')[1])
        else :
            if _line.count("/sec") :
                if not _bw :
                    _bw = _line.split()[6]

if _jitter :
    _jitter = _jitter / _flows

if _datagrams :
    _loss = 100*float(_loss)/float(_datagrams)

_m_d = {}
_m_d["/tmp/iperf_bw"] = _bw
_m_d["/tmp/iperf_jitter"] = _jitter
_m_d["/tmp/iperf_loss"] = _loss

for _fn in [ "/tmp/iperf_bw", "/tmp/iperf_jitter", "/tmp/iperf_loss" ] :
    _fh = open(_fn, "w")
    _fh.write(str(_m_d[_fn]))
    _fh.close()
