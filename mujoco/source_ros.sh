#!/bin/bash

# this script is no longer used, but the code may be helpful to keep

# roscore in the background
source ~/gripper_repo_ws/devel/setup.bash
roscore &

# set the flag to know ros is sourced
export LUKE_FLAG=1

# if first arg is set, recall make
if [ -n "$1" ]; then
  echo ros has now been sourced
  $1 $2
fi