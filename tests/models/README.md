# models
This directory is used to hold models (at this point, just GridLAB-D),
supplemental model files (e.g. voltage.player), and model outputs.

## Files

### ieee_13.glm
Created in test_gridappsd_platform.py. GridLAB-D model for the IEEE 13
bus model as provided by the platform.

### ieee_123.glm
123 node model from the platform.

### ieee_123_mod.glm
123 node model given to Brandon by Yuan Liu on 2019-09-12 so that
Brandon can update glm.py to support classes and "object configuration"
syntax.

### ieee_8500.glm
Created by pulling the 8500 node model from the GridAPPS-D platform and
writing to file. There's a commented out test in
test_gridappsd_platform.py that could create this, but it's commented 
out for a reason.

### README.md
This file.

### test.glm
Used by test_glm.py. Originally taken from 
https://github.com/gridlab-d/gridlab-d/blob/release/RC4.1/mysql/autotest/test_mysql_group_recorder_1.glm
and annotated. 

### test2.glm
Silly simple and runnable model. Just has powerflow, a clock, and a 
substation.

### test3.glm
Just a substation object, used to test making a model runnable.

### test4.glm
Non-runnable model for testing object recursion.

### test4_expected.glm
Flattened version of test4.glm, used to ensure glm.py's recursion 
properly flattens nested objects.

### test_inverter_output.glm
Simple model with a triplex swing node, a triplex line, triplex load,
and an inverter (without an explicit DC source). This file was created
to ensure that GridLAB-D will output the specified P and Q of the 
inverter even while the system changes.

### test_substation_meter.glm
Test file to ensure we get the expected results when parenting a
meter to a substation, and then subsequently parenting a recorder to
the meter. So that tests can run this with both the tape and mysql
modules, the recorder itself and tape/mysql modules are not included.

### test_three_phase_inverter_output.glm
Test file used in proving/confirming that a three phase inverter's 
P_Out and Q_Out properties are three phase.

### test_zip.glm
Model with a variety of ZIP loads. Used to ensure zip.py behaves in the
same way as GridLAB-D for several cases. 

### test_zip_1.csv
One of the output files from running test_zip.glm. 

### voltage.player
Player file used by test_zip.glm to ensure node voltages are easily
discernible and reproducible.
