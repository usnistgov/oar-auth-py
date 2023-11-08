#! /bin/bash
#
port=8088
script=/dev/oar-auth-py/scripts/authservice-uwsgi.py
[ -f "$script" ] || script=/app/dist/oarauth/bin/authservice-uwsgi.py

[ -n "$OAR_WORKING_DIR" ] || OAR_WORKING_DIR=`mktemp --tmpdir -d _authserver.XXXXX`
[ -d "$OAR_WORKING_DIR" ] || {
    echo authserver: ${OAR_WORKING_DIR}: working directory does not exist
    exit 10
}
[ -n "$OAR_LOG_DIR" ] || export OAR_LOG_DIR=$OAR_WORKING_DIR
[ -n "$OAR_IDPSERVER_CONFIG" ] || OAR_IDPSERVER_CONFIG=/app/idp/idp_conf.py

echo
echo Working Dir: $OAR_WORKING_DIR
echo Access the OAR Authentication broker service at https://localhost:$port/
echo

cd /app/idp

echo '++' python idp.py $OAR_IDPSERVER_CONFIG
python idp.py $OAR_IDPSERVER_CONFIG




