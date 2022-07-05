# define directory structure
URDFDIR=urdf
MJCFDIR=mujoco
SETSCRIPT=make_object_sets.sh

all: urdf mjcf

.PHONY: everything
everything: urdf sets

.PHONY: urdf
urdf:
	$(MAKE) -C $(URDFDIR)

.PHONY: mjcf
mjcf:
	$(MAKE) -C $(MJCFDIR)

# make object sets, clean first
.PHONY: sets
sets: clean
	cd $(MJCFDIR) && ./$(SETSCRIPT)

clean:
	$(MAKE) -C $(URDFDIR) clean
	$(MAKE) -C $(MJCFDIR) clean