# define directory structure
URDFDIR=urdf
MJCFDIR=mujoco
SETSCRIPT=make_object_sets.sh

MAKEFLAGS += -j8 # jN => use N parallel cores

all: urdf mjcf

.PHONY: everything
everything: urdf sets

.PHONY: urdf
urdf:
	$(MAKE) -C $(URDFDIR)

.PHONY: mjcf
mjcf:
	$(MAKE) -C $(MJCFDIR)

# make object sets, clean first, use '$ make sets SET=set_test' to make only set_test
.PHONY: sets
sets: clean
	cd $(MJCFDIR) && ./$(SETSCRIPT) $(SET)

clean:
	$(MAKE) -C $(URDFDIR) clean
	$(MAKE) -C $(MJCFDIR) clean