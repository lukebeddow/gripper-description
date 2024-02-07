# this makefile is used for building gripper xml style files, eg urdf, sdf, mjcf

# define directory structure
URDFDIR=urdf
MJCFDIR=mujoco
SETSCRIPT=build_multi_segment_set.py

# ----- start options that can be overriden on command line ----- #

# override @ command line eg 'make SEGMENTS=default'
# options (defined in mujoco/build_multi_segment_set.py):
#		config         -> builds with number of segments specified in config/gripper.yaml
#		"X Y Z..."     -> builds sets with X, Y, Z, ... segments eg SEGMENTS="5 10 15"
#   basic          -> builds a basic set of "5 10 15 20 25 30"
#   fast           -> builds "5 6 7 8 9 10"
#   most           -> builds "5 6 7 8 9 10 12 14 ... (even numbers) ... 28 30"
#		all            -> builds "5 6 7 8 9 10 11 12 ... (all numbers) ... 29 30"
SEGMENTS=config

# override @ command line eg 'make WIDTHS="24 28"'
#		config				 -> builds with current width in config/gripper.yaml
#		"X Y Z..."		 -> builds with widths X, Y, Z, ...
WIDTHS=config

# what is the path to mujoco, 'default' uses hardcoded path
MUJOCO_PATH=default

# are we copying to an additional folder
EXTRA_COPY_TO=no
EXTRA_COPY_YES_TO_ALL=no
EXTRA_COPY_TO_OVERRIDE_EXISTING=no
EXTRA_COPY_TO_MERGE_SETS=no

# are we hashing the task file names
USE_HASHES=no

# are we using system python or given python path
PYTHON=python3

# ----- end options that can be overriden on command line ----- #

MAKEFLAGS += -j8 # jN => use N parallel cores

all: urdf mjcf

.PHONY: everything
everything: urdf sets

# create the urdf files for the gripper
.PHONY: urdf
urdf:
	$(MAKE) -C $(URDFDIR)

ARGS_FOR_PARSE = --segments "$(SEGMENTS)" \
	--widths "$(WIDTHS)" \
	--mujoco-path "$(MUJOCO_PATH)" \
	--copy-to "$(EXTRA_COPY_TO)" \
	--copy-to-yes "$(EXTRA_COPY_YES_TO_ALL)" \
	--copy-to-override "$(EXTRA_COPY_TO_OVERRIDE_EXISTING)" \
	--copy-to-merge-sets "$(EXTRA_COPY_TO_MERGE_SETS)" \
	--use-hashes "$(USE_HASHES)" \
	--python "$(PYTHON)"

# build mujoco files for the gripper (in mujoco/build)
.PHONY: mjcf
mjcf:
	cd $(MJCFDIR) && ./$(SETSCRIPT) --build-only $(ARGS_FOR_PARSE)

# build all mujoco object sets, cleans first to ensure maximally up to date*
# note: override $(SET) @ command line to build only one set, eg 'make sets SET=set_test'
.PHONY: sets
sets: clean
	cd $(MJCFDIR) && ./$(SETSCRIPT) $(SET) $(ARGS_FOR_PARSE)

clean:
	$(MAKE) -C $(URDFDIR) clean
	cd $(MJCFDIR) && ./$(SETSCRIPT) --clean
#	$(MAKE) -C $(MJCFDIR) clean