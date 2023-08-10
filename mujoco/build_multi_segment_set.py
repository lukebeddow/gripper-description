#!/usr/bin/env python3

"""
This file scripts the making of an object set where a single set of object files
is created, but multiple gripper xml files are created with different numbers
of segments.
"""

import yaml
import subprocess
import os
import shutil
import argparse
from datetime import datetime

debug = False

# ----- user defined options ----- #

# ESSENTIAL name requirements for object sets
set_starts_with = "set"
set_ends_with = ".yaml"

# define files and folders, these must ALL correspond to EXISTING files/folders
gripper_config_file_name = "gripper.yaml"
gripper_config_file = f"/config/{gripper_config_file_name}"
set_directory = "object_sets"
object_yaml = "define_objects.yaml"
object_py = "build_object_set.py"

# these do not have to exist (note that we need the 'meshes_mujoco' folder for real applications)
objects_folder = "objects"
build_folder = "build"

# default task folder name (see Makefile), only to delete it for tidyness
default_task_folder_name = "task"

# name of folders containing gripper model files (+ str(N) on the end)
task_folder_name = "gripper"

# ----- command line options ----- #

# define arguments and parse them
parser = argparse.ArgumentParser()
parser.add_argument("sets", metavar="set", nargs="*", default=None)
parser.add_argument("-N", "--segments", default=None)
parser.add_argument("-W", "--widths", default=None)
parser.add_argument("-B", "--build-only", action="store_true", default=False) # builds a set, but leaves it in build_folder
parser.add_argument("-C", "--clean", action="store_true", default=False) # clean build folder only, this overrides other settings
parser.add_argument("--mujoco-path", type=str, default="default") # where is mujoco? Used for bin/compile to get mjcf files
parser.add_argument("--copy-to", default="no") # copy the output files to an additional folder specified by a relative path
parser.add_argument("--copy-to-yes", default="no") # force yes to copy-to, ensures copy takes place
parser.add_argument("--copy-to-override", default="no") # if the copy-to location exists, do we delete it first
parser.add_argument("--copy-to-merge-sets", default="no") # do we copy task files into an already existing set in the 'copy-to' directory
parser.add_argument("--use-hashes", default="no") # do we make hash versions of task files
args = parser.parse_args()

# ----- begin scripting ---- #

def get_yaml_hash(filepath):
  """
  Get a simple hash of the text of the yaml file, stripping all whitespace
  """

  # simple string hash function which returns same hash each run (unlike Python hash())
  def myHash(text:str):
    hash=0
    for ch in text:
      hash = ( hash*281  ^ ord(ch)*997) & 0xFFFFFFFF
    # return hash
    return hex(hash)[2:].upper().zfill(8)

  # read the yaml file as a string for hashing
  with open(filepath, "r") as yamlfile:
    yaml_string = yamlfile.read()
    yaml_string = "".join(yaml_string.split())

  # hash the yaml string for the task folder name
  return myHash(yaml_string)

filepath = os.path.dirname(os.path.abspath(__file__))
description_path = os.path.dirname(filepath)

ext_length = len(set_ends_with)

# ensure the relevant subdirecotires exist
dirs = [
  build_folder,
  build_folder + "/" + objects_folder,
]
for dir in dirs:
  if not os.path.exists(filepath +  "/" + dir):
    os.makedirs(filepath +  "/" + dir)

# path to where the set will be built
activepath = filepath + "/" + build_folder

# get the names of possible object sets
setpath = filepath + "/" + set_directory + "/"
available_sets = [x for x in os.listdir(setpath) if x.startswith(set_starts_with) and x.endswith(set_ends_with)]

if debug:
  print("The available sets are:", available_sets)

# now see if we have been given specific sets to build
if args.build_only or args.clean:
  build_sets = ["empty"] # we aren't making a set, only building or cleaning files
elif len(args.sets) == 0:
  build_sets = available_sets
  if debug: print("No set input given, building all sets")
else:
  build_sets = []
  for set in available_sets:
    for inset in args.sets:
      if set[:-ext_length] == inset:
        build_sets.append(set)
  if debug: 
    print("Set input is:", args.sets)
    print("Building sets:", build_sets)

# check if we have been given a specific mujoco path
if args.mujoco_path in ["default", "luke", "luke-laptop"]: 
  args.mujoco_path = "/home/luke/repo/mujoco/mujoco-2.2.0"
elif args.mujoco_path in ["luke-PC", "lab"]:
  args.mujoco_path = "/home/luke/mymujoco/libs/mujoco/mujoco-2.1.5"
elif args.mujoco_path in ["operator-PC, lab-op"]:
  args.mujoco_path = "/home/luke/luke-gripper-mujoco/libs/mujoco/mujoco-2.1.5"

with open(description_path + gripper_config_file) as file:
  gripper_details = yaml.safe_load(file)

# what segment number is in the config file? Save this value
original_N = gripper_details["gripper_config"]["num_segments"]

# have we been given a segment list?
if args.segments is None:
  segments = [original_N]
elif args.segments in ["config"]:
  segments = [original_N]
elif args.segments in ["basic"]:
  segments = [5, 10, 15, 20, 25, 30]
elif args.segments in ["fast"]:
  segments = [5, 6, 7, 8, 9, 10]
elif args.segments in ["most"]:
  segments = [5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
elif args.segments in ["all"]:
  segments = list(range(5, 31))
elif args.segments in ["all2"]:
  segments = list(range(2, 31))
else:
  list_segments = args.segments.split(" ")
  segments = []
  for string in list_segments:
    segments.append(int(string))

# have we been given a list of widths?
original_W = gripper_details["gripper_params"]["finger_width"]

if args.widths is None or args.widths in ["config", "default"]:
  # widths in config file must be in metres, convert to mm
  widths = [original_W * 1e3]
else:
  list_widths = args.widths.split(" ")
  widths = []
  for string in list_widths:
    widths.append(int(string))

if len(segments) == 0:
  raise RuntimeError("no segments specified in build_multi_segment_set.py")

# copy object generation python file into the build area
if not args.build_only:
  shutil.copyfile(setpath + "/" + object_py, activepath + "/" + objects_folder + "/" + object_py)

# ----- create object sets ----- #

copy_choice = None
err_str = ""
allow_copy_to = True

for set_to_build in build_sets:

  if not args.build_only and not args.clean:
    set_to_build = set_to_build[:-ext_length]

    # remove the object set from the object folder, before we rebuild it
    if (os.path.isdir(setpath + "/" + set_to_build)):
      print("Removing", set_to_build)
      shutil.rmtree(setpath + set_to_build)

    # copy the set yaml into the mjcf builder directory
    set_yaml = f"{set_to_build}.yaml"
    shutil.copyfile(setpath + "/" + set_yaml, activepath + "/" + objects_folder + "/" + object_yaml)

  # delete all folders with the same style as the task folder name (ie out of date)
  folders = [x for x in os.listdir(activepath) if os.path.isdir(activepath + "/" + x)]
  for f in folders:
    if f.startswith(task_folder_name):
      shutil.rmtree(activepath + "/" + f)
    elif f.startswith(default_task_folder_name):
      # check for the default task name, if there we can delete for tidyness
      shutil.rmtree(activepath + "/" + f)

  # if cleaning, run 'make clean' and exit now folders have been deleted
  if args.clean:
    make = "make clean"
    subprocess.run([make], shell=True, cwd=filepath)
    print("build_multi_segment_set.py has finished cleaning")
    exit()

  for i, N in enumerate(segments):
    for width_mm in widths:

      # overwrite yaml dictionary with settings for this iteration
      gripper_details["gripper_config"]["num_segments"] = N
      gripper_details["gripper_params"]["finger_width"] = width_mm * 1e-3

      # write the overwritten dictionary to the file
      with open(description_path + gripper_config_file, "w") as outfile:
        yaml.dump(gripper_details, outfile, default_flow_style=False)

      # create the task folder name
      if args.use_hashes == "yes":
        yaml_hash = get_yaml_hash(description_path + gripper_config_file)
        this_folder_name = f"{task_folder_name}_N{N}_H{yaml_hash}"
      else:
        this_folder_name = f"{task_folder_name}_N{N}_{width_mm:.0f}"

      # call make to create the files
      make = "make TASK={0} INCDIR={1} DIRNAME={2} MJCOMPILE={3}/bin/compile".format(
        this_folder_name, objects_folder, build_folder, args.mujoco_path)
    
      # disable object generation until the final loop (assets/objects wiped at the start of each 'make')
      if i != len(segments) - 1: make += " GEN_OBJECTS=0"

      subprocess.run([make], shell=True, cwd=filepath)

      # copy the gripper.yaml config file into the new folder
      shutil.copyfile(description_path + gripper_config_file, 
                      activepath + "/" + this_folder_name + "/" + gripper_config_file_name)

      # are we merging new tasks into an existing object set (in 'copy_to' directory)
      if args.copy_to != "no" and args.copy_to_merge_sets == "yes":
        copy_to_path = filepath + "/" + args.copy_to
        if os.path.exists(copy_to_path + f"/{set_to_build}"):
          # now copy our task files directly into that set
          allow_copy_to = False
          if not os.path.exists(f"{copy_to_path}/{set_to_build}/{this_folder_name}"):
            shutil.copytree(f"{activepath}/{this_folder_name}", 
                            f"{copy_to_path}/{set_to_build}/{this_folder_name}")
            err_str += f"TASK ADDED: {set_to_build}/{this_folder_name}\n"
          else: err_str += f"TASK FOUND ALREADY FOR {set_to_build}/{this_folder_name}\n"

  # finally, copy the built set into the specified object sets folder
  if not args.build_only:
    shutil.copytree(activepath, setpath + "/" + set_to_build)

    # are we copying to an additional directory
    if args.copy_to != "no" and allow_copy_to:
      copy_to_path = filepath + "/" + args.copy_to
      print(f"build_multi_segment_set.py is about to copy the object set to: {copy_to_path}")
      if copy_choice is None:
        if args.copy_to_yes == "yes": copy_choice = "yes"
        else:
          copy_choice = input("Type yes to continue (this choice will apply to all sets being built)\n> ")
      if copy_choice.lower() in ["y", "yes"]:
        try:
          shutil.copytree(activepath, copy_to_path + "/" + set_to_build)
          print("Copy operation complete\n")
          err_str += f"Generated {set_to_build} and moved it to: {copy_to_path}/{set_to_build}"
        except FileExistsError as e:
          if args.copy_to_override == "yes":
            delete_folder = "deleted"
            timestamp = datetime.now().strftime("%d-%m-%y-%H:%M:%S")
            if not os.path.exists(copy_to_path + f"/{delete_folder}"):
              os.makedirs(copy_to_path + f"/{delete_folder}")
            err_str += f"Existing object set '{set_to_build}' found, moved to '{copy_to_path}/{delete_folder}' with timestamp: {timestamp}\n"
            shutil.move(copy_to_path + "/" + set_to_build, copy_to_path + f"/{delete_folder}/" + set_to_build + f"_{timestamp}")
            shutil.copytree(activepath, copy_to_path + "/" + set_to_build)
            err_str += f"Generated {set_to_build} and moved it to: {copy_to_path}/{set_to_build}"
          else:
            print(f"Copy operation failed because object set '{set_to_build}' already exists: {e}")
            err_str += f"COPY FAILED, OBJECT SET ALREADY EXISTS: '{set_to_build}'\n"
      else:
        print("Copy operation aborted")

if err_str != "": print(f"\n{err_str}\n")

# now we have finished making the sets, restore the config file to its original state
gripper_details["gripper_config"]["num_segments"] = original_N
gripper_details["gripper_params"]["finger_width"] = original_W

# write the overwritten dictionary to the file
with open(description_path + gripper_config_file, "w") as outfile:
  yaml.dump(gripper_details, outfile, default_flow_style=False)