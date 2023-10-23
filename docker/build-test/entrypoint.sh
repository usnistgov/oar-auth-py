#! /bin/bash
#
[ "$1" = "" ] && exec /bin/bash

function install {
    scripts/install.sh --prefix=/app/oarauth || return 1
    export OAR_HOME=/app/oarauth
    export PYTHONPATH=$OAR_HOME/lib/python
    export OAR_LOG_DIR=$OAR_HOME/var/logs
}

function exitopwith { 
    echo $2 > $1.exit
    exit $2
}

cmd=$1
case "$1" in
    makedist)
        shift
        scripts/makedist "$@"
        ;;
    testall)
        install || {
            echo "testall: Failed to install oar-auth-py"
            exitopwith testall 2
        }
        shift
        scripts/testall "$@"; stat=$?

        [ "$stat" != "0" ] && {
            echo "testall: One or more tests failed (last=$stat)"
            exitopwith testall 3
        }

        echo All python tests passed
        ;;
    install)
        install
        python -c 'import nistoar.auth'
        ;;
    testshell)
        # libdir=`ls /dev/oar-oarauth-py/python/build | grep lib.`
        export OAR_PYTHONPATH=/dev/oar-auth-py/python/build/lib
        export OAR_JQ_LIB=/dev/oar-auth-py/metadata/jq
        export OAR_MERGE_ETC=/dev/oar-auth-py/metadata/etc/merge
        export OAR_SCHEMA_DIR=/dev/oar-auth-py/metadata/model
        export PYTHONPATH=$OAR_PYTHONPATH
        exec /bin/bash
        ;;
    shell)
        exec /bin/bash
        ;;
    installshell)
        install
        exec /bin/bash
        ;;
    *)
        echo Unknown command: $1
        echo Available commands:  makedist testall testshell install shell installshell testmdservshell testpreserveshell
        ;;
esac

[ $? -ne 0 ] && exitopwith $cmd 1
true

    
    
