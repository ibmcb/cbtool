#! /usr/bin/python  
import sys  

#
# Number of Tokens/Nodes to generate tokens for
#
num = 0
if (len(sys.argv) > 1):  
  num=int(sys.argv[1])  

if num == 0 : 
  print "Not a valid input."
  sys.exit(1)

#
# Token Gen
#
for i in range(1,num):  
  print 'Token %d : %d' % (i, (i*(2**127)/num))  
