#!/usr/bin/env python
import sys
from sys import path
p = path[0] + "/util/pydevd/pysrc"
print "appending " + p
sys.path.append(p)
