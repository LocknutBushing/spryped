# Copyright 2020 Benjamin Bokser

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import numpy as np
import math
import csv

values = []
with open('spryped_urdf_rev05/urdf/spryped_urdf_rev05.csv', 'r') as csvfile:
    data = csv.reader(csvfile, delimiter=',') 
    next(data) # skip headers
    values = list(zip(*(row for row in data))) # transpose rows to columns
    values = np.array(values) # convert list of nested lists to array

comx = values[1].astype(np.float)
comy = values[2].astype(np.float)
comz = values[3].astype(np.float)

mass = values[7].astype(np.float)
ixx = values[8].astype(np.float)
ixy = values[9].astype(np.float)
ixz = values[10].astype(np.float)
iyy = values[11].astype(np.float)
iyz = values[12].astype(np.float)
izz = values[13].astype(np.float)

ox = values[38].astype(np.float)
oy = values[39].astype(np.float)
oz = values[40].astype(np.float)

coml = []
for j in range(9):
     # joint origin to COM length ignoring y axis
    comlen = math.sqrt((comx[j]**2)+(comz[j]**2))
    #comlen = math.sqrt((comx[j]**2)+(comy[j]**2)+(comz[j]**2)) # joint origin to COM length
    coml.append(comlen)
#print(coml[1])

# estimating init link angles
#p = 4
#dist = math.sqrt((ox[p]**2)+(oz[p]**2))
#angle = np.degrees(math.atan(oz[p]/dist))
#print("dist = ", dist)
#print("angle p = ", angle)
               
# link masses
if mass[1]!=mass[5]:
    print("WARNING: femur L/R masses unequal, check CAD")
if mass[2]!=mass[6]:
    print("WARNING: tibiotarsus L/R masses unequal, check CAD")
if mass[3]!=mass[7]:
    print("WARNING: tarsometatarsus L/R masses unequal, check CAD")
if mass[4]!=mass[8]:
    print("WARNING: toe L/R masses unequal, check CAD")

class Robot:

    def __init__(self, q=np.zeros(8), dq=np.zeros(8), init_q=[np.pi/4, -np.pi*40.3/180, np.pi*84.629/180,
                               -np.pi*44.329/180, np.pi/4, -np.pi*40.3/180,
                               np.pi*84.629/180, -np.pi*44.329/180.],
                               init_dq=[0., 0., 0., 0., 0., 0.], **kwargs):
        # link lengths must be manually updated
        l1 = 0.05 # femur left
        l2 = 0.199 # tibiotarsus left
        l3 = 0.5 # tarsometatarsus left
        l4 = 0.05 # toe left
        l5 = 0.05 # femur right
        l6 = 0.199 # tibiotarsus right
        l7 = 0.5 # tarsometatarsus right
        l8 = 0.05 # toe right
        self.L = np.array([l1, l2, l3, l4, l5, l6, l7, l8])

        # mass matrices
        self.MM = []
        for i in range(9):
            M = np.zeros((6, 6))
            M[0:3, 0:3] = np.eye(3)*float(mass[i])
            M[3, 3] = ixx[i]
            M[3, 4] = ixy[i]
            M[3, 5] = ixz[i]
            M[4, 3] = -ixy[i]
            M[4, 4] = iyy[i]
            M[4, 5] = iyz[i]
            M[5, 3] = -ixz[i]
            M[5, 4] = -iyz[i]
            M[5, 5] = izz[i]
            #self.MM.insert(i,M)
            self.MM.append(M)
        self.JCOM1 = np.zeros((6, 3))
        self.JCOM1[1, 0] = -2*coml[1]*np.sin(2*q[0])
        self.JCOM1[2, 0] = 2*coml[1]*np.cos(2*q[0])
        self.JCOM1[3, 0] = 1
robert = Robot()
#print(robert.MM[7])
print(robert.JCOM1)