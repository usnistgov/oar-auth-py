#! /bin/bash
#
# setversion.sh:  sets the current version of this software by writing
#    a VERSION file and injecting it into the code.
#
# Usage: setversion.sh [version]
#
# If version is provided as an argument, this string will be set as the
# current version.
#
# This script can be edited to customize it for its package.
#
# set -x
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
PACKAGE_DIR=`(cd $execdir/.. > /dev/null 2>&1; pwd)`
set -e

## This is set by default via _setversion.sh; if necessary, uncomment 
#  and customize
# 
PACKAGE_NAME=oar-auth-py

. $PACKAGE_DIR/oar-build/_setversion.sh
version=$1

[ -n "$version" ] || version=$(determine_version)

# write the package name and version to file called VERSION
# don't overwrite VERSION if this is not a cloned repo
if [ -n "$GIT_COMMIT" -o ! -e VERSION ]; then
    write_VERSION $PACKAGE_NAME $version
else
    [ -n "$PACKAGE_NAME" ] || PACKAGE_NAME=`cat VERSION | awk '{print $1}'`
    version=`cat VERSION | awk '{print $2}'`
fi

# inject the version string into the source code
#
# At the moment, a special script is not needed; setup.py has been updated
# to read the current contents of VERSION.  Thus, inject_version.sh does not
# exist.
#
[ ! -e "$PACKAGE_DIR/scripts/inject_version.sh" ] || {
    bash "$PACKAGE_DIR/scripts/inject_version.sh" $version $PACKAGE_NAME
}

# echo $PACKAGE_NAME $version
