#! /bin/bash
#
# run.sh -- launch the server in a docker container
#
# For command line help, type "run.sh -h"
#

prog=authserver
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
dockerdir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`
repodir=`(cd $dockerdir/.. > /dev/null 2>&1; pwd)`
scriptsdir=$repodir/scripts
os=`uname`
SED_RE_OPT=r
[ "$os" != "Darwin" ] || SED_RE_OPT=E

PACKAGE_NAME=oar-auth-py
DEFAULT_CONFIGFILE=$dockerdir/authserver/authservice-config.yml

set -e

function usage {
    cat <<EOF
$prog - launch a docker container running the authentication broker server

SYNOPSIS
  $prog [-h|--help] [-b|--build] [-D|--docker-build] [-c|--config-file FILE] 
        [-d|--data-dir DIR] [start|stop]

ARGUMENTS
  start                         Start the service; this is the default if the 
                                start|stop argument is not provided.  
  stop                          Stop the running service.  
  -b, --build                   Rebuild the python library and install into dist;
                                This is done automatically if the dist directory 
                                does not exist.
  -D, --docker-build            Rebuild the authserver docker image; this is 
                                done automatically if the authserver image 
                                does not exist.
  -c FILE, --config-file FILE   Use a custom service configuration given in FILE.
                                This file must be in YAML or JSON format.
                                Defaut: docker/authserver/authserver-config.yml
  -d DIR, --data-dir            Use DIR as the location of the static data files 
                                needed by the service.  Default: etc/authservice
  -h, --help                    Print this text to the terminal and then exit

EOF
}

function docker_images_built {
    for image in "$@"; do
        (docker images | grep -qs $image) || {
            return 1
        }
    done
    return 0
}

function build_server_image {
    echo '+' $dockerdir/dockbuild.sh -d authserver
    $dockerdir/dockbuild.sh -d authserver # > log
}

DOPYBUILD=
DODOCKBUILD=
CONFIGFILE=
DATADIR=
while [ "$1" != "" ]; do
    case "$1" in
        -b|--build)
            DOPYBUILD="-b"
            ;;
        -D|--docker-build)
            DODOCKBUILD="-D"
            ;;
        -c)
            shift
            CONFIGFILE=$1
            ;;
        --config-file=*)
            CONFIGFILE=`echo $1 | sed -e 's/[^=]*=//'`
            ;;
        -d)
            shift
            DATADIR=$1
            ;;
        --data-file=*)
            DATADIR=`echo $1 | sed -e 's/[^=]*=//'`
            ;;
        -h|--help)
            usage
            exit
            ;;
        -*)
            echo "${prog}: unsupported option:" $1
            false
            ;;
        start|stop)
            [ -z "$ACTION" ] || {
                echo "${prog}: Action $ACTION already set; provide only one"
                false
            }
            ACTION=`echo $1 | tr A-Z a-z`
            ;;
        *)
            echo "${prog}: ignoring extra argument," $1
            ;;
    esac
    shift
done
[ -n "$ACTION" ] || ACTION=start

([ -z "$DOPYBUILD" ] && [ -e "$repodir/python/dist/oarauth" ]) || {
    echo '+' scripts/install.sh --prefix=$repodir/python/dist/oarauth
    $repodir/scripts/install.sh --prefix=$repodir/python/dist/oarauth
}
[ -d "$repodir/python/dist/oarauth/lib/python/nistoar" ] || {
    echo ${prog}: Python library not found in dist directory: $repodir/python/dist
    false
}
VOLOPTS="-v $repodir/python/dist:/app/dist"

# build the docker images if necessary
(docker_images_built authserver && [ -z "$DODOCKBUILD" ]) || build_server_image

[ -n "$CONFIGFILE" ] || CONFIGFILE=$DEFAULT_CONFIGFILE
[ -f "$CONFIGFILE" ] || {
    echo "${prog}: Config file ${CONFIGFILE}: does not exist as a file"
    false
}
echo Running server with config file, $CONFIGFILE
configext=`echo $CONFIGFILE | sed -e 's/^.*\.//' | tr A-Z a-z`
[ "$configext" = "json" -o "$configext" = "yml" ] || {
    echo "${prog}:" Config file type not recognized by extension: $configext
    false
}
configparent=`dirname $CONFIGFILE`
configfile=`(cd $configparent; pwd)`/`basename $CONFIGFILE`
VOLOPTS="$VOLOPTS -v ${configfile}:/app/authservice-config.${configext}:ro"
ENVOPTS="-e OAR_AUTHSERVER_CONFIG=/app/authservice-config.${configext}"

if [ -n "$DATADIR" ]; then
    [ -d "$DATADIR" ] || {
        echo "${prog}: Data directory ${DATADIR}: does not exist as a directory"
        false
    }
    VOLOPTS="$VOLOPTS -v ${DATADIR}:/app/dist/etc"
fi

if [ -d "$repodir/docs" ]; then
    VOLOPTS="$VOLOPTS -v $repodir/docs:/docs"
fi

CONTAINER_NAME="authserver"
function stop_server {
    echo '+' docker kill $CONTAINER_NAME
    docker kill $CONTAINER_NAME
}

if [ "$ACTION" = "stop" ]; then
    echo Shutting down the midas server...
    stop_server || true
else
    echo '+' docker run $ENVOPTS $VOLOPTS -p 127.0.0.1:9095:9095/tcp --rm --name=$CONTAINER_NAME $PACKAGE_NAME/authserver
    docker run $ENVOPTS $VOLOPTS -p 127.0.0.1:9095:9095/tcp --rm --name=$CONTAINER_NAME $PACKAGE_NAME/authserver
fi

