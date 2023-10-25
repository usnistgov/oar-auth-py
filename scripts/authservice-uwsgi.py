"""
The uWSGI script for launching the ID resolver service.

This script launches an ID resolver as a web service using uwsgi.  For example, one can 
launch the service with the following command:

  uwsgi --plugin python3 --http-socket :9090 --wsgi-file resolver-uwsgi.py \
        --set-ph oar_config_file=authservice-config.yml

[config parameters]

This script also pays attention to the following environment variables:

   OAR_HOME            The directory where the OAR PDR system is installed; this 
                          is used to find the OAR PDR python package, nistoar.
   OAR_PYTHONPATH      The directory containing the PDR python module, nistoar.
                          This overrides what is implied by OAR_HOME.
   OAR_CONFIG_SERVICE  The base URL for the configuration service; this is 
                          overridden by the oar_config_service uwsgi variable. 
   OAR_CONFIG_ENV      The application/component name for the configuration; 
                          this is only used if OAR_CONFIG_SERVICE is used.
   OAR_CONFIG_TIMEOUT  The max number of seconds to wait for the configuration 
                          service to come up (default: 10);
                          this is only used if OAR_CONFIG_SERVICE is used.
   OAR_CONFIG_APP      The name of the component/application to retrieve 
                          configuration data for (default: pdr-resolve);
                          this is only used if OAR_CONFIG_SERVICE is used.
"""

import os, sys, logging, copy
from copy import deepcopy

try:
    import nistoar
except ImportError:
    oarpath = os.environ.get('OAR_PYTHONPATH')
    if not oarpath and 'OAR_HOME' in os.environ:
        oarpath = os.path.join(os.environ['OAR_HOME'], "lib", "python")
    if oarpath:
        sys.path.insert(0, oarpath)
    import nistoar

from nistoar.base import config
from nistoar.auth import wsgi

try:
    import uwsgi
except ImportError:
    # simulate uwsgi for testing purpose
    from nistoar.testing import uwsgi
    uwsgi = uwsgi.load()

# determine where the configuration is coming from
confsrc = uwsgi.opt.get("oar_config_file")
if isinstance(confsrc, (bytes, bytearray)):
    confsrc = confsrc.decode()
if confsrc:
    # it's from a file
    cfg = config.resolve_configuration(confsrc)

elif 'oar_config_service' in uwsgi.opt:
    # it's from a config service set by the uwsgi command-line
    srvc = config.ConfigService(uwsgi.opt.get('oar_config_service'),
                                uwsgi.opt.get('oar_config_env'))
    srvc.wait_until_up(int(uwsgi.opt.get('oar_config_timeout', 10)),
                       True, sys.stderr)
    cfg = srvc.get(uwsgi.opt.get('oar_config_appname', 'auth-broker'))

elif config.service:
    # it's from a config service set by environment variables
    config.service.wait_until_up(int(os.environ.get('OAR_CONFIG_TIMEOUT', 10)),
                                 True, sys.stderr)
    cfg = config.service.get(os.environ.get('OAR_CONFIG_APP', 'auth-broker'))

else:
    raise config.ConfigurationException("authservice: nist-oar configuration not provided")

# create the WSGI application; note: this also configures the log.
application = wsgi.create_app(cfg, uwsgi.opt.get("oar_auth_data_dir"))
logging.info("Auth service is ready")


