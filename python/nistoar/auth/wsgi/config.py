"""
configuration support for the authentication service.  

This module allows much of its extensive configuration to be set by default values stored in a 
system file set at build/install-time.  The default name for this file is value of 
:py:data:`DEFAULT_CONFIG_FILE` (``default_config.json``), stored under the ``etc/authserver`` 
directory below the root of the OAR installation.  The exact location is determine by 
:py:function:`find_auth_data_dir()`.  This function is run at module load-time, and the result is 
saved to :py:data:`def_auth_data_dir` (but it can be updated later).  

The default configuration data can be mreged with the configuration data loaded at run-time using
the :py:function:`expand_config`.
"""
import os
from pathlib import Path
from collections.abc import Mapping

from nistoar.base import config as oarconfig

DEFAULT_CONFIG_FILE = "default_config.json"

def find_auth_data_dir(config: Mapping=None):
    """
    return the path to the directory containing operational data that 
    drives the authentication broker service.  The given configuration 
    can specify the directly explicitly; otherwise, the default location
    in production mode is the ``etc/authservice`` directory where the OAR 
    code is installed.  (In development mode, the default location is under
    the ``etc`` directory within the ``oar-auth-py`` repository.  

    If the directory is not set in the input configuration (see below), this 
    function will check the environment variable ``OAR_HOME`` which should hold 
    the absolute path to the installation directory of the OAR software.  If it 
    is set, this function will look for the ``etc/authservice`` directory below it.
    If not set, a list of default locations will be checked assuming different 
    production and development scenarios.

    :param dict config:  a configuration dictionary that may include a ``data_dir`` parameter
                         indicating the path to the directory containing the operation data.
                         If not provided, alternate locations will be checked (including 
                         checking the value of OAR_HOME).
    """
    def assert_exists(dir, ctxt=""):
        if not Path(dir).exists():
            msg = "{0}directory does not exist: {1}".format(ctxt, dir)
            raise oarconfig.ConfigurationException(msg)

    # check the configuration
    if config and 'data_dir' in config:
        assert_exists(config['data_dir'], "Auth Broker service data ")
        return config['data_dir']

    # look relative to a base directory
    if 'OAR_HOME' in os.environ:
        # this might be the install base directory or the source base directory;
        # either way, look for a subdirectory "etc/authservice"
        assert_exists(os.environ['OAR_HOME'], "env var OAR_HOME ")
        basedir = Path(os.environ['OAR_HOME'])
        candidates = [basedir / 'etc' / 'authservice']

    else:
        # guess some locations based on the location of the executing code
        # The code might be coming from an installation, build, or source
        candidates = []

        # assume library has been installed; library is rooted at {root}/lib/python
        basedir = Path(__file__).parents[5]

        # and the etc dir is {root}/etc
        candidates.append(basedir / 'etc' / 'authservice')

        # assume library has been build within the soure code directory at {root}/python/build/lib
        basedir = Path(__file__).parents[6]

        # then etc would be {root}/etc
        candidates.append(basedir / 'etc' / 'authservice')

        # assume library being used from its source code location
        basedir = Path(__file__).parents[4]

        # and etc is {root}/etc
        candidates.append(basedir / 'etc' / 'authservice')

    for dir in candidates:
        if dir.exists():
            return str(dir)
        
    return None

def_auth_data_dir = find_auth_data_dir()

def expand_config(config=None, def_config=None):
    """
    expand the authentication service configuration with default values for parameters that 
    do not appear in the input.  

    The defaults are read in from the data directory and merged with the given data (using 
    :py:func:`nistoar.base.config.merge_config`).  The data in given config data over-rides 
    any set in the defaults.

    :param Mapping config:  the primary configuraiton data (usually read from the config 
                            service).  If not provide, only the default values are returned.
    :param str|Mapping def_config:    the default configuration data.  If value is a string,
                            it will be interpreted as the path to the file containing the 
                            default configuration; otherwise, it should be a dictionary 
                            containing the actual default configuration data.
    @return dict  a new dictionary containing the expanded configuration.  
    """
    if config:
        if not isinstance(config, Mapping):
            raise TypeError("expand_config(): config parameter is not a dictionary: " +
                            str(type(config)))

    if not def_config:
        def_config = Path(def_auth_data_dir) / DEFAULT_CONFIG_FILE
    if isinstance(def_config, Path):
        def_config = str(def_config)
    if isinstance(def_config, str):
        def_config = oarconfig.load_from_file(def_config)
    elif not isinstance(def_config, Mapping):
        raise TypeError("expand_config(): def_config parameter is neither str nor dict: " +
                        str(type(def_config)))
        
    if not config:
        return def_config
    return oarconfig.merge_config(config, def_config)

