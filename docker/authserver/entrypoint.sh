#! /bin/bash
#
port=9095
script=/dev/oar-auth-py/scripts/authservice-uwsgi.py
[ -f "$script" ] || script=/app/dist/oarauth/bin/authservice-uwsgi.py

[ -n "$OAR_WORKING_DIR" ] || OAR_WORKING_DIR=`mktemp --tmpdir -d _authserver.XXXXX`
[ -d "$OAR_WORKING_DIR" ] || {
    echo authserver: ${OAR_WORKING_DIR}: working directory does not exist
    exit 10
}
[ -n "$OAR_LOG_DIR" ] || export OAR_LOG_DIR=$OAR_WORKING_DIR
[ -n "$OAR_AUTHSERVER_CONFIG" ] || OAR_AUTHSERVER_CONFIG=/app/authservice-config.yml

echo
echo Working Dir: $OAR_WORKING_DIR
echo Access the OAR Authentication broker service at http://localhost:$port/
echo

crts=/app/dist/oarauth/etc/authservice/certs

echo '++' uwsgi --plugin python3 --https-socket :$port,$crts/spsite.pem,$crts/spsite.key \
                --wsgi-file $script --static-map /docs=/docs \
                --set-ph oar_config_file=$OAR_AUTHSERVER_CONFIG \
                --set-ph oar_working_dir=$OAR_WORKING_DIR $opts
uwsgi --plugin python3 --https-socket :$port,$crts/spsite.pem,$crts/spsite.key \
      --wsgi-file $script --static-map /docs=/docs \
      --set-ph oar_config_file=$OAR_AUTHSERVER_CONFIG \
      --set-ph oar_working_dir=$OAR_WORKING_DIR $opts
