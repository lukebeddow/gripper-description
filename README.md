# luke-gripper-description

This repository defines the gripper in xml form. This means:
* urdf - standard robot format
* sdf - gazebo simulator format
* mjcf - mujoco simulator format
* semantic urdf - additional MoveIt configuration information

xml files for the gripper and panda are defined using xml scripting with xacro in python3 - install this with ```python3 -m install xacro```.

## Defining the gripper and panda

The key base definitions of the panda and gripper are in the ```xacro``` folder:
* Gripper
** ```gripper.xacro``` declares a macro called ```add_gripper``` which generates all the gripper xml code
** ```gripper.main.xacro``` defines the gripper main body layout and joint motions
** ```gripper.segmented_fingers.xacro``` defines optional multi-segment flexible fingers for the gripper
* Panda
** ```panda.xacro``` declares a macro called ```add_panda``` which generates all the panda xmal code
** ```panda.main.xacro``` defines the panda main body layout and joint motions
** ```panda.gazebo.xacro``` adds gazebo specific information
** ```panda.control.xacro``` adds ROS controller details to the panda

## Making urdf and sdf files in the ```urdf``` folder

The ```urdf``` folder contains the target ```urdf```, ```sdf```, and ```semantic urdf``` files. These are based on xacro definitions in files ending with ```urdf.xacro```. Run ```make``` in this directory to generate the resulant files from these xacro definitions. These definition files are very short, and simply use the previously mentioned macros (eg ```add_gripper```) as well as some short code to define a link from the origin to the robot.

## Making mjcf files in the ```mujoco``` folder

The ```mujoco``` folder contains the target ```mjcf``` files, which are more complex than the other types and require more work to convert from ```urdf``` to ```mjcf``` format. Run ```make``` in this directory to generate the resultant ```xml``` files in the ```mjcf``` folder, as well as generate files in two more important folders:
* ```mjcf_include``` -  this folder defines objects which can then be included into other ```xml``` files. Currently, these are only included in ```gripper_task.xml```. This folder contains two files which define the objects:
** ```create_objects.xacro``` uses xacro to generate different objects based on input options
** ```define_objects.yaml``` sets these input options, controlling how many objects are generated and what types
* ```task``` - this folder contains files almost identical to ```grippper_task.xml``` however, that file includes all possible objects, whereas each file in this folder will include a random subset of the objects, currently set to be 20

The converstion from ```urdf``` to ```mjcf``` is first accomplished using mujoco's compiler, however then the script ```xml_script.py``` is run to make additional changes. This is where it is set that the ```task``` files should have 20 objects each, and these should be randomly chosen from the total object set defined in ```mjcf_include```. Edit this file to adjust the resultant ```mjcf``` files.

Running ```make``` in the ```mujoco``` folder generates the gripper, panda, and object xml code in ```mjcf``` format. However, it may be that multiple different object sets are wanted along with all required files. A facility for this is provided in the ```object_sets``` folder. Recall that the object set relies on two files, ```create_objects.xacro``` and ```define_objects.yaml```. In this folder, there is a master version of each. Then, to make your own object set, copy and rename ```define_objects.yaml``` to ```yourobjectsetname.yaml``` and inside that file set the desired changes to the options. You can edit ```create_objects.xacro``` to add additional options or objects. Then, run ```make_object_sets.sh [ARGS]``` where the arguments are the names of the yaml files (without the .yaml extension) you want to generate complete object sets for. For example, ```./make_object_sets.sh yourobjectsetname set1_fullset_795```. Now, these object sets will be generated and copied into the ```object_sets``` folder.




