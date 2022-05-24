# this script makes multiple object sets and copies them into the object_sets folder
# with no inputs, it makes every possible set, otherwise give the names of the sets
# to make as inputs, without the trailing .yaml extension

# variables
SETDIR=object_sets
SETMATCH=set*.yaml
YAMLDESTDIR=mjcf/mjcf_include/
YAMLDESTNAME=define_objects.yaml
CREATEDESTNAME=create_objects.xacro

# find all sets we can build based on SETMATCH
cd $SETDIR
sets_to_build=($SETMATCH)
cd ..
printf "The following sets are possible:"
printf "\t%s\n" "${arr[*]}"  ${sets_to_build[*]}
printf "\n"

# fcn to check if an array contains an element
containsElement () {
  local e match="$1"
  shift
  for e; do [[ "$e" == "$match" ]] && return 0; done
  return 1
}

# check if we have received arguments
if [ $# -ne 0 ]; then

  # put the inputs into an array
  inputs_to_build=("$@")

  printf "The inputs given are the following:"
  printf "\t%s\n" "${arr[*]}"  ${inputs_to_build[*]}
  printf "\n"

  # add .yaml to each array element
  inputs_to_build=("${inputs_to_build[@]/%/.yaml}")

  actually_build=()

  # check that these sets are possible
  for input_set in "${inputs_to_build[@]}"; do
    if containsElement "${input_set}" "${sets_to_build[@]}"; then
      actually_build+="${input_set} "
    fi

  done

  # overwrite with what we will actually build
  sets_to_build=()
  sets_to_build="${actually_build[@]}"

else

  printf "No inputs given, default to all sets\n\n"

fi

# print to the screen the sets which will be created
printf "The following sets will be created:"
printf "\t%s\n" "${arr[*]}"  ${sets_to_build[*]}
printf "\n"

# copy create_objects.xacro into the build area
cp $SETDIR/$CREATEDESTNAME $YAMLDESTDIR/$CREATEDESTNAME

# loop over the set yamls and create them
for set_yaml in "${sets_to_build[@]}"; do

  echo Now making: "${set_yaml%.*}"

  # copy the set yaml into the mjcf builder directory
  cp $SETDIR/$set_yaml $YAMLDESTDIR/$YAMLDESTNAME

  # run the makefile and create the object set
  make

  # now copy the entire made folder as an object set
  cp -TR mjcf $SETDIR/${set_yaml%.*}

done