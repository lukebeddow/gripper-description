#!/usr/bin/env python3

import yaml
import os
from lxml import etree
from math import floor, ceil
from copy import deepcopy
import numpy as np
import argparse

# ----- if we are given command line arguments ---- #

# define arguments and parse them
parser = argparse.ArgumentParser()
parser.add_argument("--build-folder",         default="build")
parser.add_argument("--objects-folder",       default="objects")
parser.add_argument("--task-folder",          default="task")
parser.add_argument("--gen-objects",          default=True, type=int) 

args = parser.parse_args()

# # parse arguments but allow unknown arguments
# args, unknown = parser.parse_known_args()

generate_objects = bool(args.gen_objects)

# ----- initial setup, no need to change ----- #

# are we in debug mode
debug = False

# define directory structure
build_folder = args.build_folder
objects_folder = args.objects_folder
task_file_folder = args.task_folder
gripper_config_file = "/config/gripper.yaml"
define_objects_file = "/" + objects_folder + "/define_objects.yaml"

# get relevant path information
filepath = os.path.dirname(os.path.abspath(__file__))
description_path = os.path.dirname(filepath)
directory_path = filepath + "/" + build_folder + "/"

with open(description_path + gripper_config_file) as file:
  gripper_details = yaml.safe_load(file)

with open(directory_path + define_objects_file) as file:
  object_details = yaml.safe_load(file)

# do we have a fixed random seed (so test set fixed)
rand_seed = object_details["settings"]["fixed_random_seed"]
if rand_seed == 0: rand_seed = np.random.randint(0, 2147483647)
np.random.seed(rand_seed)

if debug:
  print("Running xml_script.py, debug mode is ON")
  print("The random seed is:", rand_seed, "yaml value = ", object_details['settings']['fixed_random_seed'])
  print("The gripper description directory path is:", description_path)
  print("The mjcf directory path is:", directory_path)
  print("The task folder name is:", task_file_folder)
  print("Generate objects flag is:", generate_objects)

# ----- essential user defined parameters ----- #

# exctract the details of the gripper configuration from yaml file
is_segmented = gripper_details["gripper_config"]["is_segmented"]
num_segments = gripper_details["gripper_config"]["num_segments"]
fixed_first_segment = gripper_details["gripper_config"]["fixed_first_segment"]
fixed_hook_segment = gripper_details["gripper_config"]["fixed_hook_segment"]
fixed_motor_joints = gripper_details["gripper_config"]["fixed_motor_joints"]

if debug:
  print("is segmented is", is_segmented)
  print("num segments is", num_segments)
  print("fixed first segment is", fixed_first_segment)
  print("fixed hook joint is", fixed_hook_segment)
  print("fixed motor joints is", fixed_motor_joints)

# starting configuration of the robot joints
joint_start = {
  "panda_joint1": 0.0,
  "panda_joint2": 0.0,
  "panda_joint3": 0.0,
  "panda_joint4": 0.0,
  "panda_joint5": 0.0,
  "panda_joint6": 1.0,
  "panda_joint7": 0.0,
  "gripper_prismatic": gripper_details["gripper_params"]["xy_home"],
  "gripper_revolute": 0.0,
  "gripper_palm": gripper_details["gripper_params"]["z_home"],
  "base_z": 0.0
}

# panda parameters
panda_control = "motor"

# gripper parameters
gripper_control = "motor"
force_limit_prismatic = 10.0 # these are currently not used
force_limit_revolute = 10.0  # these are currently not used
force_limit_palm = 10.0      # these are currently not used

# finger dummy parameters
finger_control = "motor"
finger_joint_stiffness = 5 # 10 appears more realistic

# base parameters
base_control = "motor"

# task parameters
base_joint_dof = 1
max_objects_per_task = 20

# finger friction parameters
default_mujoco_friction = [1, 0.005, 0.0001]
finger_segment_friction = [0.5 * x for x in default_mujoco_friction]
finger_segment_friction = "".join(str(finger_segment_friction)[1:-1].split(",")) # convert [1,2,3] to "1 2 3"

# define all the joint names
gripper_joints = [
  "finger_1_prismatic_joint", "finger_1_revolute_joint",
  "finger_2_prismatic_joint", "finger_2_revolute_joint",
  "finger_3_prismatic_joint", "finger_3_revolute_joint",
  "palm_prismatic_joint"]
base_joints = ["world_to_base"]

# ----- generate qpos and joint names ---- #

ffs = 1 if fixed_first_segment else 0
hk_jnt = 0 if fixed_hook_segment else 1

# auto generate joint names
panda_joints = ["panda_joint{0}".format(i) for i in range(1,8)]
finger_joints = ["finger_{0}_segment_joint_{1}".format(i, j) for i in range(1,4) 
                  for j in range(ffs, num_segments)]

# define keyframe qpos for segmented finger, 0 for all
if is_segmented:
  finger_joint_qpos = "0 " * (num_segments - ffs + hk_jnt)
else:
  finger_joint_qpos = ""

# define keyframe qpos for main model joints
if fixed_motor_joints:
  gripper_qpos = "{0} {0} {0} {1}".format(
    finger_joint_qpos, joint_start["gripper_palm"]
  )
else:
  gripper_qpos = "{0} {1} {2} {0} {1} {2} {0} {1} {2} {3}".format(
    joint_start["gripper_prismatic"], joint_start["gripper_revolute"], 
    finger_joint_qpos, joint_start["gripper_palm"]
  )
panda_qpos = "{0} {1} {2} {3} {4} {5} {6}".format(
  joint_start["panda_joint1"], joint_start["panda_joint2"], 
  joint_start["panda_joint3"], joint_start["panda_joint4"],
  joint_start["panda_joint5"], joint_start["panda_joint6"], 
  joint_start["panda_joint7"]
)
base_joint_qpos = "{0}".format(
  joint_start["base_z"]
)

# ----- create keyframe xml -----#

# format xml code with keyframe information
gripper_keyframe = """ 
  <keyframe>
    <key name="initial pose"
         time="0"
         qpos="{0}"
    />
  </keyframe>
""".format(gripper_qpos)

panda_keyframe = """
  <keyframe>
    <key name="initial pose"
         time="0"
         qpos="{0}"
    />
  </keyframe>
""".format(panda_qpos)

panda_and_gripper_keyframe = """
  <keyframe>
    <key name="initial pose"
         time="0"
         qpos="{0} {1}" 
    />
  </keyframe>
""".format(panda_qpos, gripper_qpos)

task_keyframe = """
  <keyframe>
    <key name="initial pose"
         time="0"
         qpos="{0} {1} {2}"
    />
  </keyframe>
"""

# ----- create actuator xml ----- #

# define the actuator information
gripper_actuator_subelement = """
  <{0} name="{1}_actuator" joint="{1}"/>
"""

panda_actuator_subelement = """
  <{0} name="{1}_actuator" joint="{1}"/>
"""

finger_actuator_subelement = """
  <{0} name="{1}_actuator" joint="{1}"/>
"""

base_actuator_subelement = """
  <{0} name="{1}_actuator" joint="{1}"/>
"""

# create actuator xml for each joint
gripper_actuator_string = """"""
for joint in gripper_joints:
  if fixed_motor_joints: 
    if joint.endswith("revolute_joint"): continue
    if joint.endswith("prismatic_joint"): continue
  gripper_actuator_string += gripper_actuator_subelement.format(
    gripper_control, joint
  )
panda_actuator_string = """"""
for joint in panda_joints:
  panda_actuator_string += panda_actuator_subelement.format(
    panda_control, joint
  )
finger_actuator_string = """"""
for joint in finger_joints:
  finger_actuator_string += finger_actuator_subelement.format(
    finger_control, joint
  )
base_actuator_string = """"""
for joint in base_joints:
  base_actuator_string += base_actuator_subelement.format(
    base_control, joint
  )

# format the final xml chunks for the actuation
gripper_actuator = """
  <actuator>
    {0}
    {1}
  </actuator>
""".format(gripper_actuator_string, finger_actuator_string)

panda_actuator = """
  <actuator>
    {0}
  </actuator>
""".format(panda_actuator_string)

panda_and_gripper_actuator = """
  <actuator>
    {0}
    {1}
    {2}
  </actuator>
""".format(panda_actuator_string, gripper_actuator_string, finger_actuator_string)

task_actuator = """
  <actuator>
    {0}
    {1}
    {2}
  </actuator>
""".format(base_actuator_string, gripper_actuator_string, finger_actuator_string)

# ----- create force sensor xml ----- #

force_sensor_site = """
  <site name="force sensor site"
        type="sphere"
        rgba="0 0 0 0"
        size="0.005 0.005 0.005"
        pos="0 0 0"
        quat="0 0 0 1"
  />
"""

force_sensor = """
  <sensor>
    <force name="force sensor" noise="0" site="force sensor site"/>
  </sensor>
"""

# ----- create equality constraints for gripper motors ----- #
if not fixed_motor_joints:
  equality_constraints = """
    <equality>
      <weld name="pris1_weld"
            active="false"
            body1="gripper_base_link"
            body2="finger_1_intermediate"
      />
      <weld name="pris2_weld"
            active="false"
            body1="gripper_base_link"
            body2="finger_2_intermediate"
      />
      <weld name="pris3_weld"
            active="false"
            body1="gripper_base_link"
            body2="finger_3_intermediate"
      />
      <weld name="rev1_weld"
            active="false"
            body1="finger_1"
            body2="finger_1_intermediate"
      />
      <weld name="rev2_weld"
            active="false"
            body1="finger_2"
            body2="finger_2_intermediate"
      />
      <weld name="rev3_weld"
            active="false"
            body1="finger_3"
            body2="finger_3_intermediate"
      />
      <weld name="palm_weld"
            active="false"
            body1="gripper_base_link"
            body2="palm"
      />
    </equality>
  """
else:
  equality_constraints = """
    <equality>
      <weld name="palm_weld"
            active="false"
            body1="gripper_base_link"
            body2="palm"
      />
    </equality>
  """

# ----- helper functions ----- #

def modify_tag_text(tree, tagname, target_text):
  """
  This function loads an xml file, finds a specific tag, then overrides that
  tag with the given target text. These changes are saved back under the
  given filename, with the original file being now lost
  NB lxml preserves comments and ordering
  """

  # now get the root of the tree
  root = tree.getroot()

  # search recursively for all instances of the tag
  tags = root.findall(".//" + tagname)

  # now overwrite the text in each tag
  for t in tags:
    t.text = target_text

def modify_tag_attribute(tree, tagname, attribute_name, new_value):
  """
  Modify the attribute text on the tree
  """

  # now get the root of the tree
  root = tree.getroot()

  # search recursively for all instances of the tag
  tags = root.findall(".//" + tagname)

  # add the attribute only if the tag_label matches
  for t in tags:
    t.set(attribute_name, new_value)

def add_tag_attribute(tree, tagname, tag_label, attribute_name, attribute_value):
  """
  Add a new attribute for a tag, eg <tag/> goes to <tag attribute="true"/>
  """

  # now get the root of the tree
  root = tree.getroot()

  # search recursively for all instances of the tag
  tags = root.findall(".//" + tagname)

  # add the attribute only if the tag_label matches
  for t in tags:
    if t.attrib["name"] == tag_label:
      t.set(attribute_name, attribute_value)

def add_chunk(tree, parent_tag, xml_string_to_add):
  """
  This function adds a chunk of xml text under the bracket of the given
  parent tag into the given tree
  """

  # extract the xml text from
  new_tree = etree.fromstring(xml_string_to_add)

  # get the root of the parent tree
  root = tree.getroot()

  # special case where we are adding at the root
  if parent_tag == "@root":
    root.append(new_tree)
    return

  # search recursively for all instances of the parent tag
  tags = root.findall(".//" + parent_tag)

  if len(tags) > 1:
    raise RuntimeError("more than one parent tag found")
  elif len(tags) == 0:
    raise RuntimeError("parent tag not found")

  for t in tags:
    t.append(new_tree)
  
  return

def add_chunk_with_specific_attribute(tree, parent_tag, attribute_name,
  attribute_value, xml_string_to_add):
  """
  Add a chunk of xml text to a parent tag, but only if the parent tag
  has a specific attribute with a specific value
  """

  # extract the xml text from
  new_tree = etree.fromstring(xml_string_to_add)

  # get the root of the parent tree
  root = tree.getroot()

  # special case where we are adding at the root
  if parent_tag == "@root":
    root.append(new_tree)
    return

  # search recursively for all instances of the parent tag
  tags = root.findall(".//" + parent_tag)

  for t in tags:
    if t.attrib[attribute_name] == attribute_value:
      t.append(new_tree)
  
  return

def add_geom_name_and_friction(tree, parent_body, friction):
  """
  Adds a name to finger segment collision geoms, as well as friction which should
  be given in the form "1 0.001 0.0005"
  """

  # now get the root of the tree
  root = tree.getroot()

  # search recursively for all instances of the tag
  tags = root.findall(".//" + "body")

  # special case if we want to name every single geom
  if parent_body == "@all":
    num = 0
    for t in tags:
      geoms = t.findall("geom")
      for g in geoms:
        g.set("name", "geom_" + str(num))
        num += 1
    return

  # first geom always visual, then collision, if 4 geoms then must be hook link
  labels = ["visual", "collision", "hook_visual", "hook_collision"]

  # add the geom label only to bodies that match the parent body name
  for t in tags:
    if t.attrib["name"] == parent_body:
      geoms = t.findall("geom")
      for i, g in enumerate(geoms):

        # set the name to a given template
        g.set("name", parent_body + "_geom_" + labels[i])

        # also set the friction
        g.set("friction", friction)

def random_object_split(asset_tree, object_tree, detail_tree, obj_per_task):
  """
  Randomly split the total number of objects into num new seperate files
  """

  # create blank trees
  blankroot = """<mujoco></mujoco>"""
  blanktree = etree.fromstring(blankroot)

  # get the roots of the input trees
  asset_root = asset_tree.getroot()
  object_root = object_tree.getroot()
  detail_root = detail_tree.getroot()

  # how many total objects are there
  num_obj = len(asset_root.getchildren())

  # determine how many splits we need
  num_splits = int(np.ceil(num_obj / float(obj_per_task)))

  # print essential information to the terminal
  print("There are", num_obj, "objects, with", 
    obj_per_task, "per task, giving", num_splits, "splits")

  # create copies of the trees
  trees = []
  for i in range(num_splits):
    trees.append(
      [deepcopy(blanktree), deepcopy(blanktree), ""]
    )

  # for testing: compare asset/object numbers (object should be +1 for ground)
  if debug:
    other_num = len(object_root.getchildren())
    print("number of assets is", num_obj)
    print("number of objects is", other_num)

  if num_obj < 1:
    raise RuntimeError("number of objects is zero! Ensure objects have 'include: true'"
      " and beware repeated names of objects override each other")

  # create shuffled random list of every object
  rand_lists = np.arange(num_obj)
  np.random.shuffle(rand_lists) # comment this line for unshuffled objects

  # get the qpos info, split into individual numbers
  qpos_str = " {0} {1} {2} {3} {4} {5} {6}"

  # setup the free objects to the side in a grid formation
  grid_xrange = [-1, 1]
  grid_ystart = 2
  spacing = 0.5

  per_x = int(floor((grid_xrange[1] - grid_xrange[0]) / float(spacing)))
  num_y = int(ceil(obj_per_task / float(per_x)))
  object_X = [(grid_xrange[0] + (spacing / 2.) + spacing * i) for i in range(per_x)] * num_y
  object_Y = [(grid_ystart + spacing * j) for j in range(num_y) for i in range(per_x)]

  # loop through the num of objects per split and assemble trees and qpos
  for i in range(num_splits):
    for j in range(obj_per_task):

      # if we run out of objects
      if i * obj_per_task + j >= len(rand_lists):
        print("The last file has", j, "objects instead of", obj_per_task)
        break

      r = rand_lists[i * obj_per_task + j]
      trees[i][0].append(deepcopy(asset_root[r]))
      trees[i][1].append(deepcopy(object_root[r]))
      
      # get the z_rest from the detail tree
      z_rest = detail_root[r].attrib["z_rest"]

      # add a very small padding
      z_rest_padding = 1e-4
      z_rest = str(float(z_rest) + z_rest_padding)

      # create the qpos for this object
      trees[i][2] += qpos_str.format(
        object_X[j],
        object_Y[j],
        z_rest,
        0,
        0,
        0,
        1
      ) 

    # now add the ground plane (we assume its the last entry)
    trees[i][1].append(deepcopy(object_root[-1]))

  return trees

# ----- execute scripting to insert xml snippets into files ----- #

if __name__ == "__main__":
 
  """
  This script opens a given xml file, saves the tree, and then makes some
  changes to it. The new tree then overwrites the old tree and the file is
  saved. The lxml module is used, which preserves comments and ordering, so
  the new file should look identical to the old file except the changes.

  The idea is to take mujoco xml files (mjcf files), open their xml tree,
  and then insert some extra bits and pieces.

  There are 4 target files (names given below in code):
    - gripper contains the gripper only
    - panda contains the panda only
    - both contains both the gripper and the panda
    - task contains the gripper fixed above the ground, ready for grasping
  """

  # define the names of the base xml files we will be editing
  gripper_filename = directory_path + "gripper_mujoco.xml"
  panda_filename = directory_path + "panda_mujoco.xml"
  both_filename = directory_path + "panda_and_gripper_mujoco.xml"
  task_filename = directory_path + "gripper_task.xml"

  # define the names of object files we will open
  asset_filename = directory_path + objects_folder + "/" + "assets.xml"
  object_filename = directory_path + objects_folder + "/" + "objects.xml"
  detail_filename = directory_path + objects_folder + "/" + "details.xml"

  # define the names of files we will make when we split tasks and objects
  asset_split_filename = "assets/assets_{}.xml"
  object_split_filename = "objects/objects_{}.xml"
  keyframe_split_filename = "keyframes/keyframe_{}.xml"
  task_split_filename = task_file_folder + "/gripper_task_{}.xml"
  taskN_filename = directory_path + "/" + task_split_filename
  assetN_filename = directory_path + objects_folder + "/" + asset_split_filename
  objectN_filename = directory_path + objects_folder + "/" + object_split_filename
  keyframeN_filename = directory_path + task_file_folder + "/" + keyframe_split_filename

  # parse and extract the xml tree for each file we want to use
  parser = etree.XMLParser(remove_comments=True)
  gripper_tree = etree.parse(gripper_filename, parser=parser)
  panda_tree = etree.parse(panda_filename, parser=parser)
  both_tree = etree.parse(both_filename, parser=parser)
  task_tree = etree.parse(task_filename, parser=parser)
  asset_tree = etree.parse(asset_filename, parser=parser)
  object_tree = etree.parse(object_filename, parser=parser)
  detail_tree = etree.parse(detail_filename, parser=parser)

  # add the keyframe information to each
  add_chunk(gripper_tree, "@root", gripper_keyframe)
  add_chunk(panda_tree, "@root", panda_keyframe)
  add_chunk(both_tree, "@root", panda_and_gripper_keyframe)

  # add the actuator information to each
  add_chunk(gripper_tree, "@root", gripper_actuator)
  add_chunk(panda_tree, "@root", panda_actuator)
  add_chunk(both_tree, "@root", panda_and_gripper_actuator)
  add_chunk(task_tree, "@root", task_actuator)

  # add force sensor to the gripper body
  add_chunk_with_specific_attribute(task_tree, "body", "name",
                                    "gripper_base_link", force_sensor_site)
  add_chunk(task_tree, "@root", force_sensor)

  # add equality constraints to gripper task for non-backdriveable joints
  add_chunk(task_tree, "@root", equality_constraints)

  # now add in finger joint stiffnesses
  tag_string = "finger_{0}_segment_joint_{1}"
  body_string = "finger_{0}_segment_link_{1}"

  ffs = 1 if fixed_first_segment else 0

  for i in range(3):

    # # experiment: add joint friction
    # next_rev = "finger_{0}_revolute_joint".format(i)
    # next_pris = "finger_{0}_prismatic_joint".format(i)
    # add_tag_attribute(task_tree, "joint", next_rev, "frictionloss", str(1))
    # add_tag_attribute(task_tree, "joint", next_pris, "frictionloss", str(1))
    # raise RuntimeError("joint friction not tested out yet!!!")

    # loop through each finger segment and add xml tags/attributes
    for j in range(num_segments):

      # names of the finger segment joint and body
      next_joint = tag_string.format(i + 1, j + ffs)
      next_body = body_string.format(i + 1, j + ffs + 1)

      # add finger stiffness attributes
      add_tag_attribute(gripper_tree, "joint", next_joint,
                        "stiffness", str(finger_joint_stiffness))
      add_tag_attribute(both_tree, "joint", next_joint,
                        "stiffness", str(finger_joint_stiffness))
      add_tag_attribute(task_tree, "joint", next_joint,
                        "stiffness", str(finger_joint_stiffness))
                    
      # add geom names
      add_geom_name_and_friction(task_tree, next_body, finger_segment_friction)

  # add palm geom names
  add_geom_name_and_friction(task_tree, "palm", finger_segment_friction)

  # finally, overwrite the files with the new xml
  gripper_tree.write(gripper_filename, xml_declaration=True, encoding='utf-8')
  panda_tree.write(panda_filename, xml_declaration=True, encoding='utf-8')
  both_tree.write(both_filename, xml_declaration=True, encoding='utf-8')

  # ----- now we split the task tree into multiple files (each with fewer objects) ----- #

  # split the files into equal parts with a given number of objects per task
  taskN_trees = random_object_split(asset_tree, object_tree, detail_tree, max_objects_per_task)

  # for each split, perform the formatting as above and save as a new file
  for i in range(len(taskN_trees)):

    # create a copy which we will edit
    taskN_tree = deepcopy(task_tree)

    # edit the meshdir because the tasks are in the /task directory
    modify_tag_attribute(taskN_tree, "compiler", "meshdir", "../meshes_mujoco")

    # create xml text for specefic includes and add them to the tree
    objectN_includes = """<include file="../{0}/{1}"/>""".format(objects_folder, object_split_filename.format(i))
    assetN_include = """<include file="../{0}/{1}"/>""".format(objects_folder, asset_split_filename.format(i))
    keyframeN_include = """<include file="../{0}/{1}"/>""".format(task_file_folder, keyframe_split_filename.format(i))
    add_chunk(taskN_tree, "worldbody", objectN_includes)
    add_chunk(taskN_tree, "asset", assetN_include)
    add_chunk(taskN_tree, "@root", keyframeN_include)

    # write the split task files into the task folder
    taskN_tree.write(taskN_filename.format(i))

    # make a keyframe snippet to be saved in a seperate file
    keyframe_tree = etree.ElementTree(etree.Element("mujoco"))
    add_chunk(keyframe_tree, "@root", 
        task_keyframe.format(base_joint_qpos, gripper_qpos, taskN_trees[i][2]))

    # write the keyframe inside the task folder
    keyframe_tree.write(keyframeN_filename.format(i))

    # if generating object set, write to the assets.xml files etc
    if generate_objects:

      # create element trees from the split
      new_asset_tree = etree.ElementTree(taskN_trees[i][0])
      new_object_tree = etree.ElementTree(taskN_trees[i][1])

      new_asset_tree.write(assetN_filename.format(i))
      new_object_tree.write(objectN_filename.format(i))
      
