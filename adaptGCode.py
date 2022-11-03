# Johann Fischer, Rapid-OOD, 2022-09-19, postprocessing: set markers for multiple extruders
# ---


# imports
from pickle import FALSE, TRUE
import sys

# open file in read-mode

gcode = open("current.gcode", mode="r")

# read the gcode and extract it to a list
changes = gcode.readlines()

count = 0
T0 = []
T1 = []
for lines in changes:
    count = count+1
    if "T0" in lines:
        T0.append(count)
    if "T1" in lines:
        T1.append(count)

line_count = 0
edit = FALSE
for lines in changes:
    if(line_count in T1):
        edit = TRUE
    if(line_count in T0):
        edit = FALSE
    if edit==TRUE:
        changes[line_count] = str(changes[line_count][:changes[line_count].find(";")]).replace("X", "U").replace("Y", "V") + str(changes[line_count][changes[line_count].find(";"):])
    line_count = line_count + 1

z=0
while z<len(T0):
    items = T0[z]
    changes.insert(items-1, "G1 U60 F10000\n")
    changes.insert(items, "G1 V325 F15000\n")
    changes.insert(items+1, "G1 U10 F10000\n")
    changes.insert(items+2, "G1 X40 F10000\n")
    a = 0
    while a<len(T0):
        if T0[a] > items:
            T0[a] = T0[a]+4
        a = a+1
    a=0
    while a<len(T1):
        if T1[a] > items:
            T1[a] = T1[a]+4
        a = a+1
    z = z+1

z=0
while z<len(T1):
    items = T1[z]
    changes.insert(items-1, "G1 X60 F10000\n")
    changes.insert(items, "G1 Y0 F15000\n")
    changes.insert(items+1, "G1 X10 F10000\n")
    changes.insert(items+2, "G1 U60 F10000\n")
    a = 0
    while a<len(T0):
        if T0[a] > items:
            T0[a] = T0[a]+4
        a = a+1
    a=0
    while a<len(T1):
        if T1[a] > items:
            T1[a] = T1[a]+4
        a = a+1
    z=z+1

gcode.close()

gcode = gcode = open("current.gcode", mode="w")
for item in changes:
    gcode.write(item)
gcode.close()
print("xyuv ready")
