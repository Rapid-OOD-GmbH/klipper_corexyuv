# klipper_corexyuv
This project modifies clipper. A second printhead shall be integrated. Both print heads run according to the corexy principle.  

### Goal: 
both print heads should be able to print simultaneously or offset. With the command G1 for movement it should be possible to control the x- and y-axis of printhead 1 and the u- and v-axis of printhead 2. The z-axis is shared by both printing heads.  

### Demarcation: 
The swerving of the two heads from each other is not the subject of this project.  

### Procedure:
(1) Adapt the kinematics to two print heads.  
(2) Adjust the print process files to the new kinematics  
(3) Modify the commands of the printer control  
(4) Tests with gcode files  

### Status:
(1) in progress  
(2) not started  
(3) not started  
(4) a test printer is set up and ready for use  

### Exact procedure:
In the kinematics (corexy.py), the settings are taken from the previous x and y axis and adjusted to the new position. Printhead 1 has its home position at the back left, printhead 2 has its home position at the back right.  
Next, all files that use this kinematics are adjusted (toolhelp.py, klippy.py, gcode.py (??)).   
Finally, the type of commands is adapted. In this case, the G-code command for the motor movement gets the new format "G1 x0 y0 z0 u0 v0" mentioned above. It should then be remembered that all the essential processes for a print head outside of printing itself (homing, preheating the extruder, drawing in print material) must then also be taken into account and transferred from the first print head.  
