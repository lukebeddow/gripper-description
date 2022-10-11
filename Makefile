# this makefile is used for building gripper xml style files, eg urdf, sdf, mjcf

# define directory structure
URDFDIR=urdf
MJCFDIR=mujoco
SETSCRIPT=build_multi_segment_set.py

# override @ command line eg 'make SEGMENTS=default'
# options (defined in mujoco/build_multi_segment_set.py):
#		config         -> builds with number of segments specified in config/gripper.yaml
#		"X Y Z..."     -> builds sets with X, Y, Z, ... segments eg SEGMENTS="5 10 15"
#   basic          -> builds a basic set of "5 10 15 20 25 30"
#   most           -> builds "5 6 7 8 9 10 12 14 ... (even numbers) ... 28 30"
#		all            -> builds "5 6 7 8 9 10 11 12 ... (all numbers) ... 29 30"
SEGMENTS=config

MAKEFLAGS += -j8 # jN => use N parallel cores

all: urdf mjcf

.PHONY: everything
everything: urdf sets

# create the urdf files for the gripper
.PHONY: urdf
urdf:
	$(MAKE) -C $(URDFDIR)

# build mujoco files for the gripper (in mujoco/build)
.PHONY: mjcf
mjcf:
	cd $(MJCFDIR) && ./$(SETSCRIPT) --build-only --segments "$(SEGMENTS)"

# build all mujoco object sets, cleans first to ensure maximally up to date*
# note: override $(SET) @ command line to build only one set, eg 'make sets SET=set_test'
.PHONY: sets
sets: 
	cd $(MJCFDIR) && ./$(SETSCRIPT) $(SET) --segments "$(SEGMENTS)"

clean:
	$(MAKE) -C $(URDFDIR) clean
	cd $(MJCFDIR) && ./$(SETSCRIPT) --clean
#	$(MAKE) -C $(MJCFDIR) clean