#!/usr/bin/env python3

import yaml
import os
from lxml import etree
import numpy as np
import argparse

# define arguments and parse them
parser = argparse.ArgumentParser()
parser.add_argument("--gen-objects", default=True, type=int)
args = parser.parse_args()

if not bool(args.gen_objects):
  # no need to run this script
  exit()

# objects yaml file
objects_yaml_file = "define_objects.yaml"

# get relevant path information
filepath = os.path.dirname(os.path.abspath(__file__))
description_path = os.path.dirname(filepath)

# import the dictionary of object information
with open(filepath + "/" + objects_yaml_file) as file:
  object_details = yaml.safe_load(file)

# do we have a fixed random seed (so test set fixed)
rand_seed = object_details["settings"]["fixed_random_seed"]
if rand_seed == 0: rand_seed = np.random.randint(0, 2147483647)
np.random.seed(rand_seed)

# how big do we want the ground
ground_xy_size = 1

# define key xml snippets in the form of a function, returning formatted snippet
def get_object_xml(name, quat, mass, diaginertia, friction="1 0.005 0.0001"):
  # this snippet creates the main object in mujoco
  object_xml = """
  <body name="{0}" pos="0 0 0">
    <inertial pos="0 0 0" quat="{1}" mass="{2}" diaginertia="{3}"/>
    <freejoint name="{0}"/>
    <geom name="{0}_geom" type="mesh" mesh="{0}" friction="{4}"/>
  </body>\n
  """.format(name, quat, mass, diaginertia, friction)
  return object_xml

def get_asset_xml(name, filepath, xscale, yscale, zscale, refquat):
  # this snippet defines the object mesh
  mesh_xml = """
  <mesh name="{0}" file="{1}"
        scale="{2} {3} {4}"
        refquat="{5}"
  />\n
  """.format(name, filepath, xscale, yscale, zscale, refquat)
  return mesh_xml

def get_details_xml(name, x, y, z, z_rest):
  # this snippet is for me to save any extrsa relevant information
  details_xml = """
  <object_details name="{0}" x="{1}" y="{2}" z="{3}" z_rest="{4}"/>\n
  """.format(name, x, y, z, z_rest)
  return details_xml

# function to add xml to a tree
def add_chunk(tree, parent_tag, xml_string_to_add):
  """
  This function adds a chunk of xml text under the bracket of the given
  parent tag into the given tree
  """

  # print(xml_string_to_add)

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

def print_categories(count_dict):
  """
  Print a summary of numbers of objects in each category
  """
  total = 0
  for key in count_dict:
    total += count_dict[key]

  table_header = f"{'category':<12} | {'num':<5} | {'%':<5}"
  row_template = "{0:<12} | {1:<5} | {2:<5.1f}"

  print("Printing categories of", total, "objects:")
  print(table_header)
  for key in count_dict:
    print(row_template.format(key, count_dict[key], count_dict[key]*(100.0/total)))
  print()

  return total

if __name__ == "__main__":

  object_root = etree.Element("mujoco")
  assets_root = etree.Element("mujoco")
  detail_root = etree.Element("mujoco")

  object_tree = etree.ElementTree(object_root)
  assets_tree = etree.ElementTree(assets_root)
  detail_tree = etree.ElementTree(detail_root)

  biggest_mass = [0, "object"]

  # default mujoco friction parameters for geoms
  # mujoco friction: sliding / torsional / rolling
  # default: 1.0, 0.005, 0.0001
  # increase rolling friction to 0.005 to prevent objects rolling on their own
  default_friction = [1.0, 0.005, 0.005]
  scale_all = False # only scale sliding friction

  # get density and friction values from the yaml file
  density_values = object_details["settings"]["object_densities"]
  friction_factors = object_details["settings"]["friction_scalings"]
  try:
    max_mass = object_details["settings"]["maximum_mass_grams"] * 1e-3
  except KeyError as e:
    print("settings does not contain 'maximum_mass_grams':", e)
    max_mass = 1e6
  avg_mass = 0

  # scale default friction by factors and convert [[a,b,c], [d,e,f]] into ["a b c", "d e f"]
  friction_values = []
  for f in friction_factors:
    if scale_all:
      friction_values.append("".join(str([f * x for x in default_friction])[1:-1].split(",")))
    else: # scale only the first friction, sliding friction
      friction_values.append("".join(str([f * x if i == 0 else x for i, x in enumerate(default_friction)])[1:-1].split(",")))

  random_density = object_details["settings"]["random_density"]
  random_friction = object_details["settings"]["random_friction"]

  if random_density:
    density_loop = 1
  else:
    density_loop = len(density_values)

  if random_friction:
    friction_loop = 1
  else:
    friction_loop = len(friction_values)

  category_count = {
    "cubes" : 0,
    "cuboids" : 0,
    "cylinders" : 0,
    "spheres" : 0,
    "ellipsoids" : 0
  }
  counter_ref = ""

  mass_capped_counter = 0

  # loop through top level entries in the yaml file
  for object in object_details:

    # should we skip this yaml file entry
    if object == "settings": continue
    elif object_details[object]["include"] is False: continue

    # loop through the given densities
    for d in range(density_loop):

      # extract key information
      name_root = object_details[object]["name_root"]
      name_suffix = object_details[object]["suffix"]
      name_path = object_details[object]["path"]

      spawn_axis = object_details[object]["spawn"]["axis"]
      spawn_height = object_details[object]["spawn"]["rest"]

      scale_num = object_details[object]["scale"]["num"]
      x_max = object_details[object]["scale"]["max"]["x"]
      x_min = object_details[object]["scale"]["min"]["x"]
      y_max = object_details[object]["scale"]["max"]["y"]
      y_min = object_details[object]["scale"]["min"]["y"]
      z_max = object_details[object]["scale"]["max"]["z"]
      z_min = object_details[object]["scale"]["min"]["z"]

      inertial_type = object_details[object]["inertial"]["type"]
      frame_align = object_details[object]["inertial"]["align"]

      fillet_used = object_details[object]["fillet"]["used"]
      if fillet_used:
        fillet_step = object_details[object]["fillet"]["step"]
        fillet_max = object_details[object]["fillet"]["max"]
        fillet_min = object_details[object]["fillet"]["min"]
        # work out how many fillet steps
        fillet_num = int((fillet_max - fillet_min) / fillet_step) + 1

      qx = object_details[object]["quat"]["x"]
      qy = object_details[object]["quat"]["y"]
      qz = object_details[object]["quat"]["z"]
      qw = object_details[object]["quat"]["w"]

      # work out scale increments
      if scale_num > 1:
        x_increment = (x_max - x_min) / (scale_num - 1)
        y_increment = (y_max - y_min) / (scale_num - 1)
        z_increment = (z_max - z_min) / (scale_num - 1)

      # loop through scaling number
      for i in range(scale_num):

        if random_density: density = np.random.choice(density_values)
        else: density = density_values[d]
        # print("density is", density)

        # work out this scale factor
        if scale_num == 1:
          xscale = 1.0
          yscale = 1.0
          zscale = 1.0
        else:
          xscale = x_min + i * x_increment
          yscale = y_min + i * y_increment
          zscale = z_min + i * z_increment

        # swap scaling for inertia based on frame alignment
        scales = [xscale, yscale, zscale]
        align = [
          0 if frame_align[0] == 'x' else (1 if frame_align[0] == 'y' else 2),
          0 if frame_align[1] == 'x' else (1 if frame_align[1] == 'y' else 2),
          0 if frame_align[2] == 'x' else (1 if frame_align[2] == 'y' else 2)
        ]
        xscale_in = scales[align[0]]
        yscale_in = scales[align[1]]
        zscale_in = scales[align[2]]

        if inertial_type == "cuboid":

          # extract dimensions
          x = xscale_in * object_details[object]["inertial"]["x"]
          y = yscale_in * object_details[object]["inertial"]["y"]
          z = zscale_in * object_details[object]["inertial"]["z"]

          # calculate the mass
          mass = x * y * z * density

          # calculate the diaginertia
          ixx = (1.0/12.0) * mass * (y**2 + z**2)
          iyy = (1.0/12.0) * mass * (x**2 + z**2)
          izz = (1.0/12.0) * mass * (x**2 + y**2)

          detail_x = x
          detail_y = y
          detail_z = z

          if x == y and x == z and y == z:
            counter_ref = "cubes"
          else:
            counter_ref = "cuboids"

        elif inertial_type == "sphere":
          
          # extract dimensions
          rx = xscale_in * object_details[object]["inertial"]["r"]
          ry = yscale_in * object_details[object]["inertial"]["r"]
          rz = zscale_in * object_details[object]["inertial"]["r"]

          # calculate the mass
          mass = (4.0/3.0) * np.pi * rx * ry * rz * density

          # calculate the diaginertia
          ixx = (1.0/5.0) * mass * (ry**2 + rz**2)
          iyy = (1.0/5.0) * mass * (rx**2 + rz**2)
          izz = (1.0/5.0) * mass * (rx**2 + ry**2)

          detail_x = rx * 2
          detail_y = ry * 2
          detail_z = rz * 2

          counter_ref = "spheres"

        elif inertial_type == "cylinder":

          # extract dimensions
          rx = xscale_in * object_details[object]["inertial"]["r"]
          ry = yscale_in * object_details[object]["inertial"]["r"]
          h = zscale_in * object_details[object]["inertial"]["h"]
          
          # calculate the mass
          mass = np.pi * rx * ry * h * density

          # calculate the diaginertia
          ixx = (1.0/12.0) * mass * (3 * rx * ry + h**2)
          iyy = (1.0/12.0) * mass * (3 * rx * ry + h**2)
          izz = (1.0/2.0) * mass * rx * ry

          detail_x = rx * 2
          detail_y = ry * 2
          detail_z = h

          counter_ref = "cylinders"

        elif inertial_type == "ellipsoid":

          # extract dimensions
          a = xscale_in * object_details[object]["inertial"]["a"]
          b = yscale_in * object_details[object]["inertial"]["b"]
          c = zscale_in * object_details[object]["inertial"]["c"]

          # calculate the mass
          mass = (4.0/3.0) * np.pi * a * b * c * density

          # calculate the diaginertia
          ixx = (1.0/5.0) * mass * (b**2 + c**2)
          iyy = (1.0/5.0) * mass * (a**2 + c**2)
          izz = (1.0/5.0) * mass * (a**2 + b**2)

          detail_x = a * 2
          detail_y = b * 2
          detail_z = c * 2

          counter_ref = "ellipsoids"

        else:
          raise RuntimeError("inertial type not one of 'cuboid', 'sphere', 'cylinder'")

        # now generate the final xml name
        if fillet_used:
          obj_filenames = [
            "{0}_{1}".format(name_root, fillet_min + j * fillet_step)
            for j in range(fillet_num)
          ]
          names = [
            "{0}_{1}_{2}_{3}".format(
              name_root,
              fillet_min + j * fillet_step,
              name_suffix,
              i
            ) for j in range(fillet_num)
          ]
        else:
          obj_filenames = ["{0}".format(name_root, name_suffix)]
          names = ["{0}_{1}_{2}".format(name_root, name_suffix, i)]
        
        # format key data ready to insert into xml snippets
        quat = f"{qw} {qx} {qy} {qz}"
        quat_conj = f"{qw} {-qx} {-qy} {-qz}" # note quaternion conjugate used, see mujoco docs
        diaginertia = "{0:.6f} {1:.6f} {2:.6f}".format(ixx, iyy, izz)

        dims = [detail_x, detail_y, detail_z]
        
        # check which axis the z rest is
        if spawn_axis == "x": 
          x_size = dims[align[2]]
          y_size = dims[align[0]]
          z_size = dims[align[1]]
          z_rest = spawn_height * xscale
        elif spawn_axis == "y":
          x_size = dims[align[1]]
          y_size = dims[align[2]]
          z_size = dims[align[0]]
          z_rest = spawn_height * yscale
        elif spawn_axis == "z":
          x_size = dims[align[0]]
          y_size = dims[align[1]]
          z_size = dims[align[2]]
          z_rest = spawn_height * zscale
        else: raise RuntimeError("spawn axis not one of 'x', 'y', 'z'")

        if mass > biggest_mass[0]:
          biggest_mass[0] = mass
          biggest_mass[1] = names[0] + f", density {density}"

        # cap mass above a certain amount
        if mass > max_mass:
          mass = max_mass
          mass_capped_counter += 1

        # loop through every fillet option and create the xml snippets
        for k, name in enumerate(names):

          # loop through every friction option (if random then friction_loop=1)
          for f in range(friction_loop):

            if random_friction: friction = np.random.choice(friction_values)
            else: friction = friction_values[f]

            path = "models/{0}/{1}.STL".format(name_path, obj_filenames[k])

            # add an extension to uniquely name each object (friction is vec [f1, f2, f3], use only f1)
            fric_float = float(friction.split(" ")[0])
            name_ext = f"_den{density}_fric{fric_float:.1f}"
            name += name_ext

            object_xml = get_object_xml(name, quat, mass, diaginertia, friction)
            asset_xml = get_asset_xml(name, path, xscale, yscale, zscale, quat_conj)
            detail_xml = get_details_xml(name, x_size, y_size, z_size, z_rest)

            add_chunk(object_tree, "@root", object_xml)
            add_chunk(assets_tree, "@root", asset_xml)
            add_chunk(detail_tree, "@root", detail_xml)

            # count the category of this object
            category_count[counter_ref] += 1
            avg_mass += mass

  # add the ground as the final element in the object tree
  ground_xml = f"""
  <body name="ground" pos="0 0 0">
    <geom name="ground_geom" type="plane" size="{ground_xy_size} {ground_xy_size} {ground_xy_size}"
      friction="{default_friction[0]} {default_friction[1]} {default_friction[2]}"/>
  </body>
  """
  add_chunk(object_tree, "@root", ground_xml)

  # finally, save the trees
  object_tree.write(filepath + "/objects.xml")
  assets_tree.write(filepath + "/assets.xml")
  detail_tree.write(filepath + "/details.xml")

  if max_mass < biggest_mass[0]: extra = f", but mass capped at {max_mass * 1e3:.0f}g. {mass_capped_counter} objects had mass capped"
  else: extra = ""
  total = print_categories(category_count)
  print(f"The biggest mass was {biggest_mass[0] * 1e3:.0f}g for the object: {biggest_mass[1]}" + extra + f". The average mass was {avg_mass/total * 1e3:.1f}g")




    


