#! /bin/bash
#
# run.sh -- launch the server in a docker container
#
# For command line help, type "run.sh -h"
#

prog=idpserver
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
dockerdir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`
repodir=`(cd $dockerdir/.. > /dev/null 2>&1; pwd)`
scriptsdir=$repodir/scripts
os=`uname`
SED_RE_OPT=r
[ "$os" != "Darwin" ] || SED_RE_OPT=E

PACKAGE_NAME=oar-auth-py
DEFAULT_CONFIGFILE=idp_conf.py  # found, by default, in the idp directory

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
  -D, --docker-build            Rebuild the idpserver docker image; this is 
                                done automatically if the idpserver image 
                                does not exist.
  -c FILE, --config-file FILE   Use a custom the IDP configuration given in FILE.
                                Note that this file must contain executable python 
                                code.  Defaut: idp/idp_conf.
  -d DIR, --data-dir            Use DIR as the location of the static data files 
                                needed by the service.  Default: idp
  -B, --bg                      Run the server in the background (returning the 
                                command prompt after successful launch)
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
    echo '+' $dockerdir/dockbuild.sh -d idpserver
    $dockerdir/dockbuild.sh -d idpserver # > log
}

DOPYBUILD=
DODOCKBUILD=
CONFIGFILE=
DATADIR=$repodir/idp
PORT=8088
while [ "$1" != "" ]; do
    case "$1" in
        -b|--build)
            DOPYBUILD="-b"
            ;;
        -D|--docker-build)
            DODOCKBUILD="-D"
            ;;
        -B|--bg|--detach)
            DETACH="--detach"
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
        --data-dir=*)
            DATADIR=`echo $1 | sed -e 's/[^=]*=//'`
            ;;
        -p)
            shift
            PORT=$1
            ;;
        --port=*)
            PORT=`echo $1 | sed -e 's/[^=]*=//'`
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

# build the docker images if necessary
(docker_images_built idpserver && [ -z "$DODOCKBUILD" ]) || build_server_image

[ -d "$DATADIR" ] || {
    echo "${prog}: Data directory ${DATADIR}: does not exist as a directory"
    false
}
dataparent=`dirname $DATADIR`
datadir=`(cd $dataparent; pwd)`/`basename $DATADIR`
VOLOPTS="-v ${datadir}:/app/idp"

[ -n "$CONFIGFILE" ] || CONFIGFILE=$DATADIR/$DEFAULT_CONFIGFILE
[ -f "$CONFIGFILE" ] || {
    echo "${prog}: Config file ${CONFIGFILE}: does not exist as a file"
    false
}
echo Running server with config file, $CONFIGFILE
configext=`echo $CONFIGFILE | sed -e 's/^.*\.//' | tr A-Z a-z`
[ "$configext" = "py" ] || {
    echo "${prog}:" Config file type not recognized by extension: $configext
    false
}
configparent=`dirname $CONFIGFILE`
configfile=`(cd $configparent; pwd)`/`basename $CONFIGFILE`
VOLOPTS="$VOLOPTS -v ${configfile}:/app/idp_conf.py:ro"
ENVOPTS="-e OAR_IDPSERVER_CONFIG=/app/idp_conf.py"

if [ -d "$repodir/docs" ]; then
    VOLOPTS="$VOLOPTS -v $repodir/docs:/docs"
fi

CONTAINER_NAME="idpserver"
function stop_server {
    echo '+' docker kill $CONTAINER_NAME
    docker kill $CONTAINER_NAME
}

if [ "$ACTION" = "stop" ]; then
    echo Shutting down the IDP login server...
    stop_server || true
else
    echo '+' docker run $ENVOPTS $VOLOPTS -p $PORT:8088 --rm \
                        --name=$CONTAINER_NAME $DETACH $PACKAGE_NAME/idpserver
    docker run $ENVOPTS $VOLOPTS -p $PORT:8088 --rm \
           --name=$CONTAINER_NAME $DETACH $PACKAGE_NAME/idpserver

    [ -z "$DETACH" ] || {
        echo
        echo Started IDP Login service in background \(see logs with \"docker logs idpserver\"\)
        echo
    }
fi
