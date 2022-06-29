# define directory structure
URDFDIR=urdf
MJCFDIR=mujoco
SETSCRIPT=make_object_sets.sh

all: urdf mjcf

.PHONY: urdf
urdf:
	$(MAKE) -C $(URDFDIR)

.PHONY: mjcf
mjcf:
	$(MAKE) -C $(MJCFDIR)

.PHONY: sets
sets:
	$(MJCFDIR)/$(SETSCRIPT)

clean:
	$(MAKE) -C $(URDFDIR) clean
	$(MAKE) -C $(MJCFDIR) clean