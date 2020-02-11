# Copyright 2020 Benjamin Bokser

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import numpy as np
import xml.etree.ElementTree as ET

xmltree = ET.parse('spryped rev03/urdf/spryped rev03.urdf')

#matrix = np.zeros(shape=(3,3))

ixx, ixy, ixz, iyy, iyz, izz, mass = ([] for i in range(7))

for v in xmltree.iter('mass'):
    mass.append((v.attrib['value']))
    
for v in xmltree.iter('inertia'):
    ixx.append((v.attrib['ixx']))
    ixy.append((v.attrib['ixy']))
    ixz.append((v.attrib['ixz']))
    iyy.append((v.attrib['iyy']))
    iyz.append((v.attrib['iyz']))
    izz.append((v.attrib['izz']))

# print(ixx[0])
