#! /bin/bash
#
# dockbuild.sh:  build all docker images in this directory
#
# Usage: dockbuild.sh [-h|--help] [-l LOGFILE] [-q] [image_dir ...]
#
# where an image_dir can be one of,
#    pymongo jq ejsonschema pdrpytest
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
codedir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`
set -e

## These are set by default via _dockbuild.sh; if necessary, uncomment and
## customize:
#
PACKAGE_NAME=oar-auth-py

# 
## list the names of the image directories (each containing a Dockerfile) for
## containers to be built.  List them in dependency order (where a latter one
## depends the former ones).  
#
DEP_DOCKER_IMAGE_DIRS="pymongo jqfromsrc ejsonschema pyenv"
EXEC_DOCKER_IMAGE_DIRS="build-test authserver"

[ -d "$codedir/metadata/docker" ] || {
    echo ${prog}: Missing metadata submodule
    echo Clone the oar-metadata repo in this directory\; name it "'metadata'"
    exit 3
}
. $codedir/oar-build/_dockbuild.sh

# Override, if need be, the UID of the user to run as in the container; the 
# default is the user running this script.
#
# OAR_DOCKER_UID=

# set BUILD_OPTS and BUILD_IMAGES
# 
setup_build

log_intro   # record start of build into log

$codedir/metadata/docker/dockbuild.sh $BUILD_IMAGES

if { echo " $BUILD_IMAGES " | grep -qs " pyenv "; }; then
    echo '+' docker build $BUILD_OPTS -t $PACKAGE_NAME/pyenv pyenv | logit
    docker build $BUILD_OPTS -t $PACKAGE_NAME/pyenv pyenv 2>&1 | logit
fi
if { echo " $BUILD_IMAGES " | grep -qs " build-test "; }; then
    echo '+' docker build $BUILD_OPTS -t $PACKAGE_NAME/build-test build-test | logit
    docker build $BUILD_OPTS -t $PACKAGE_NAME/build-test build-test 2>&1 | logit
fi
if { echo " $BUILD_IMAGES " | grep -qs " authserver "; }; then
    echo '+' docker build $BUILD_OPTS -t $PACKAGE_NAME/authserver authserver | logit
    docker build $BUILD_OPTS -t $PACKAGE_NAME/authserver authserver 2>&1 | logit
fi
