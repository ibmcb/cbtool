#! /usr/bin/python  

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
