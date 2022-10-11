# luke-gripper-description

This repository defines the gripper in xml form. This means:
* urdf - standard robot format
* semantic urdf - additional MoveIt/ROS configuration information
* sdf - gazebo simulator format
* mjcf - mujoco simulator format

xml files for the gripper and panda are defined using xml scripting with xacro in python3 - install this with ```python3 -m pip install xacro```.

## Using this repository

This repo is set up for use as a ROS package as well as for standalone generation of files without ROS.

Before using this repo, you will need to build it using make:
* ```make``` gerenates urdf, sdf, and mjcf files
* ```make urdf``` generates urdf and sdf files
* ```make everything``` builds urdf, sdf, and mjcf files (including multiple object sets)

Delete generated files with ```make clean```.

To use this repo with mujoco, you can also build object sets:
* ```make sets``` creates all object sets for mujoco, find them in ```mujoco/object_sets```
* ```make sets SET=<setname> SEGMENTS=<option>``` creates only one set called \<setname\>. Segment options define whether the set should include multiple versions of the gripper xml code with different numbers of finger segments. The main options are:
    * ```SEGMENTS=config```, build with the number of segments in ```config/gripper.yaml```, this is the default.
    * ```SEGMENTS="x y z ... "```, specify a list of specific integers within quotes.
    * ```SEGMENTS=all```, build every number from 5 to 30.

## Defining the gripper and panda

The key base definitions of the panda and gripper are in the ```xacro``` folder:
* Gripper
     * ```gripper.xacro``` declares a macro called ```add_gripper``` which generates all the gripper xml code
     * ```gripper.main.xacro``` defines the gripper main body layout and joint motions
     * ```gripper.segmented_fingers.xacro``` defines optional multi-segment flexible fingers for the gripper
* Panda
     * ```panda.xacro``` declares a macro called ```add_panda``` which generates all the panda xmal code
     * ```panda.main.xacro``` defines the panda main body layout and joint motions
     * ```panda.gazebo.xacro``` adds gazebo specific information
     * ```panda.control.xacro``` adds ROS controller details to the panda

## Making urdf and sdf files in the ```urdf``` folder

The ```urdf``` folder contains the target ```urdf```, ```sdf```, and ```semantic urdf``` files. These are based on xacro definitions in files ending with ```urdf.xacro```. Run ```make urdf``` in the root to generate the resulant files from these xacro definitions. These definition files are very short, and simply use the previously mentioned macros (eg ```add_gripper```) as well as some short code to define a link from the origin to the robot.

## Making mjcf files in the ```mujoco``` folder

Run ```make``` or ```make mjcf``` at the root of the repo and this will build one object set, which will be contained within the ```mujoco/build``` folder. The build will occur according to two key files:
* ```build/objects/build_object_set.py```, this script creates xml snippets which define the objects, for example it sets their mass, their size, which .stl 3D model file they rely on, and more.
* ```build/objects/define_objects.yaml```, this yaml file sets options for the python script (above), here is how you tell it which objects you want, and how you add new objects.

Once the set is built, many files are generated:
* Gripper files are in folders named ```gripper_N{X}``` where X indicates the number of finger segments. There can be many of these folders if you want the object set to include variations of the gripper fingers.
* Object files are in two folders, ```build/objects/objects``` and ```build/objects/assets```, here are xml code snippets for creating the objects and linking them with 3D model files, which should be in the ```build/meshes_mujoco``` folder.

## Making mujoco object sets

For convienience, it is better to make object sets directly and never edit inside the ```build``` folder. This can be done inside the ```mujoco/object_sets``` folder. To make a set called ```mynewset```:
* Navigate into the ```mujoco/object_sets``` directory, eg ```$ cd /path/to/repo/mujoco/object_sets```
* Copy and rename the ```define_objects.yaml``` file, eg ```$ cp define_objects.yaml set_mynewset.yaml```
* Edit the options and add new entries in ```set_mynewset.yaml``` to define the objects used in the set.
* (Optional) Edit the ```build_object_set.py``` file to get extra options/functionality in your object set. BEWARE! Changes here can break backwards compatibility for other object sets.
* Decide what numbers of gripper finger segments you want in the set, for example 5, 10, 20, 30.
* Navigate to the root of the repo, eg ```$ cd /path/to/repo/```
* Build with ```make sets SET=set_mynewset SEGMENTS="5 10 20 30"``` (the files you added/changed are copied into the ```build``` folder during the build).
* Navigate into the ```mujoco/object_sets``` directory, eg ```$ cd /path/to/repo/mujoco/object_sets```
* You should see a new folder called ```set_mynewset```, here is the new object set.

## Advanced usage

Some further customisation is possible inside the ```mujoco``` folder:
* To add new objects, add any 3D model files into ```build/meshes_mujoco``` and then edit ```object_sets/build_object_set.py``` to generate xml snippets which point to these new files. You can also add extra options, and make use of these in ```object_sets/define_objects.yaml```.
* To adjust how object set files are configured (eg number of objects in each 'task' file), see the user configuration settings at the top of ```xml_script.py```.
* To add or edit code into the output ```mjcf``` files which will not also be in the ```urdf``` files, edit ```xml_script.py```. This script puts the final touches on object set xml, including mixing up the objects randomly and adding some custom mujoco xml tags.
* To adjust how object sets build or configure their options, edit ```build_multi_segment_set.py```. This script builds object sets and then copies them into the ```object_sets``` folder.




