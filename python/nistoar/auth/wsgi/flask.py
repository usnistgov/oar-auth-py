"""
This is a Flask implementation of an OAR Authentication Broker Service.  The purpose of the
service is to broker the authentication process with the Identity Provider (IDP) and to provide
authentication tokens for authenticated users that need to connect to other OAR services.

This implementation interacts with a SAML-based IDP to log the user in, leveraging the 
python3-saml package.  The WSGI application is created via the :py:func:`create_app` factory
which should be passed a configuration dictionary.  That dictionary recognizes the follow 
properties: 

``flask``
    (dict) _required_.  A dictionary that contains parameters used to configure the Flask
    machinery; see the `Flask documentation <https://flask.palletsprojects.com/>`_ for details.  
    The only sub-property that is required is ``SECRET_KEY``.
``saml``
    (dict) _required_.  A dictionary that contains the python3-saml (``onelogin.saml2``) 
    settings.  This combines the data from the ``settings.json`` and ``advanced_settings.json``
    described in the `python3-saml documentation 
    <https://github.com/SAML-Toolkits/python3-saml/blob/master/README.md>`_.  Sub-properties 
    that describe your IDP and SP deployments need to be provided; others will have default
    values set via the file ``etc/authservicee/default_config.json`` (see below).  
``jwt``
    (dict) _required_.  A dictionary that configures the generation of JWT authentication tokens
    (see below for supported sub-properties).
``allowed_service_endpoints``
    (list of str) _required_.  A list given base URLs for the OAR front-end applications that 
    need to make use of this service.  Applications not registered here will not be able to use 
    the service. 
``data_dir``
    The location of the directory that contains the files needed to drive this Flask-based 
    service.  This includes the Flask ``templates`` and ``static`` folders, as well as the 
    ``default_config.json``.  
``logfile``
    (str) _recommended_.  The name or path (relative or absolute) for the file to write log 
    messages to.  
``logdir``
    (str) _optional_.  The directory to write the log file into (if ``logfile`` is given as 
    a relative path).  
``debug``
    (bool) _optional_.  If true, debugging will be turned on in both the Flask machinery and the 
    SAML library (over-riding the ``debug`` properties supported in the ``flask`` and ``saml``
    dictionaries).

The following sub-properties of the ``jwt`` configuration dictionary are supported:

``secret``
    (str) _required_.  The HS256 secret to use to create the encrypted JWT token.  This must be 
    shared with the backend services that will accept tokens from this service.
``lifetime``
    The lifespan of tokens generated by this service, given in seconds.  That is, the tokens
    will expire this many seconds after they are created. 

As alluded to above, this Flask requires access to various files, including the one containing 
the default configuration values.  By default, this will be _<install_root>_``/etc/authservice``,
but it can be overridden by the via the ``data_dir`` configuration parameter.  By default,
the name of the default configuration file is ``default_config.json``; however, a different 
default file can be given to the :py:func:`create_app` function.  

@Deoyani Nandrekar-Heinis
@Raymond Plante
"""
import os, logging, pdb
from pathlib import Path
from typing import List
from collections.abc import Mapping
from datetime import datetime

from flask import (Flask, request, current_app, redirect, session,
                   make_response, jsonify)

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils, OneLogin_Saml2_Error
from lxml.etree import XMLSyntaxError

from .config import expand_config, ConfigurationException, configure_log, find_auth_data_dir
from ..creds import Credentials, create_default_token_generator
from ..idp import make_credentials

def create_app(config: Mapping=None, data_dir=None):
    """
    create the fully configured Flask (WSGI) application.

    :param Mapping config:  the application configuration.  
                            See the :py:mod:`module doc<nistoar.auth.wsgi.flask>` for 
                            an enumeration of the supported properties.
    """
    if data_dir or not config.get('data_dir'):
        # data_dir will override what's in config
        config = dict(config)
        if not data_dir:
            data_dir = find_auth_data_dir(config)
        data_dir = Path(data_dir).resolve()
        config['data_dir'] = str(data_dir)
    else:
        data_dir = Path(config.get('data_dir')).resolve()

    config = expand_config(config)
    missing = []
    for param in "flask saml".split():
        if param not in config:
            missing.append(param)
    if not config.get('flask', {}).get('secret_key') and \
       not config.get('flask', {}).get('SECRET_KEY'):
        missing.append("flask.secret_key")
    if missing:
        raise ConfigurationException("Missing required config parameters: " +
                                     ", ".join(missing))
    if not isinstance(config.get('allowed_service_endpoints', []), list):
        raise ConfigurationException("Config param, allowed_service_endpoints, not a str: " +
                                     str(type(config.get('allowed_service_endpoints'))))

    configure_log(config=config)
    create_default_token_generator(config.get('jwt'))

    if config.get('debug'):
        # setting debug at the top level sets for both Flask and onelogin.saml2 
        config['flask']['DEBUG'] = True
        config['saml']['debug'] = True

    config.update(config['flask'])
    del config['flask']
    
    app = Flask(__name__,
                static_folder=data_dir/"static",
                template_folder=data_dir/"templates")
    app.name = config.get('name', 'authservice')
    app.logger = logging.getLogger(app.name)

    if not config.get('allowed_service_endpoints'):
        app.logger.warning("No allowed service endpoints set in configuration")
    else:
        app.logger.debug("Set to handle redirects to:\n  %s",
                         "\n  ".join(config.get('allowed_service_endpoints')))

    if config.get("disable_saml_login", {}).get("engaged") is True:
        app.logger.warning("SAML-based logins have been disabled!")

    app.config.update(config)  # sets SECRET_KEY

    @app.route('/sso/saml/login', methods=['GET'])
    def login():
        """
        send the client through the IDP's authentication process.  This may include presenting
        a login page to the user.  

        This endpoint is used by browser-based front-end applications to the authenticate 
        the user.  The process is initiated by redirecting the browser to this endpoint.  The 
        redirection must include one query parameter: ``redirectTo``, a URL for returning to 
        the front-end application after successful authentication.
        """
        cfg = current_app.config
        log = current_app.logger
        auth = create_saml_sp(request, cfg['saml'], cfg.get('data_dir'),
                              cfg.get('lowercase_urlencoding'))

        if 'redirectTo' not in request.args:
            return _handle_badinput("missing redirectTo query parameter")

        if not checkAllowedUrls(request.args['redirectTo'], cfg.get('allowed_service_endpoints', [])):
            log.warning("Unapproved redirect requested: %s", request.args['redirectTo']) 
            return _handle_badinput("redirectTo URL is not recognized or not approved",
                                    "Disallowed redirectTo")

        idp_url = auth.login(request.args['redirectTo'])
        session['AuthNRequestId'] = auth.get_last_request_id() # initializes req id
        return redirect(idp_url)

    @app.route('/sso/saml/acs', methods=['POST'])
    def acs():
        """
        receive and validate the results of the authentication process.  

        Upon successful authentication, the IDP server will redirect the browser to POST the 
        results of the authentication, which includes the user's identity and associated 
        attributes, to this endpoint.  This endpoint's job is to validate that the information
        is genuine and to cache the information into the session memory for access by other 
        endpoints.
        """
        request_id = None
        if 'AuthNRequestID' in session:
            request_id = session['AuthNRequestID']

        log = current_app.logger
        cfg = current_app.config
        auth = create_saml_sp(request, cfg['saml'], cfg.get('data_dir'),
                              cfg.get('lowercase_urlencoding'))

        try: 
            auth.process_response(request_id=request_id)
        except (OneLogin_Saml2_Error, XMLSyntaxError) as ex:
            return _handle_badinput(str(ex))
        errs = auth.get_errors()

        if len(errs) > 0:
            # IDP message has some validity errors
            last = str(auth.get_last_error_reason())
            if last:
                errs.append(last)
            log.error("Failures encountered while processing IDP response:\n  "+
                      "\n  ".join(errs))
            return _handle_error("Invalid response from IDP: "+last, 400, errors=errs)
                                 

        if not auth.is_authenticated():
            return _handle_unauthenticated("User did not successfully login")

        current_app.logger.info("user %s successfully authenticated", auth.get_nameid())

        if 'AuthNRequestID' in session:
            del session['AuthNRequestID']
        session['samlUserAttrs'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlNameIdFormat'] = auth.get_nameid_format()
        session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
        session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
        session['samlSessionIndex'] = auth.get_session_index()
        session['samlSessionExpiration'] = auth.get_session_expiration()
        session['samlAuthenticated'] = True
        req = convert_flask_request_for_saml(request,
                                             current_app.config.get('lowercase_urlencoding'))
        self_url = OneLogin_Saml2_Utils.get_self_url(req)

        if 'RelayState' in request.form and self_url != request.form['RelayState']:
            if not checkAllowedUrls(request.form['RelayState'], cfg['allowed_service_endpoints']):
                return _handle_badinput("redirectTo URL is not recognized or not approved",
                                        "Disallowed redirectTo")
            return redirect(auth.redirect_to(request.form['RelayState']))

        return redirect(auth.redirect_to())

    @app.route('/sso/saml/logout', methods=['GET'])
    def logout():
        """
        send the client through the logout process.  

        This endpoint is used by browser-based front-end applications to end an authenticated
        session for the user.  The process is initiated by redirecting the browser to this 
        endpoint.  The redirection may include one query parameter: ``redirectTo``, a URL for 
        returning to the front-end application after successful logout.  If not provided,
        the browser will be directed to a default location (configurable via the 
        ``default_logout_return_url``.        
        """
        log = current_app.logger
        cfg = current_app.config
        auth = create_saml_sp(request, cfg['saml'], cfg.get('data_dir'),
                              cfg.get('lowercase_urlencoding'))

        name_id = session_index = name_id_format = name_id_nq = name_id_spnq = None
        if 'samlNameId' in session:
            name_id = session['samlNameId']
        if 'samlSessionIndex' in session:
            session_index = session['samlSessionIndex']
        if 'samlNameIdFormat' in session:
            name_id_format = session['samlNameIdFormat']
        if 'samlNameIdNameQualifier' in session:
            name_id_nq = session['samlNameIdNameQualifier']
        if 'samlNameIdSPNameQualifier' in session:
            name_id_spnq = session['samlNameIdSPNameQualifier']

        return_to = request.args.get('redirectTo')
        if return_to and not checkAllowedUrls(return_to, cfg.get('allowed_service_urls', [])):
            log.warning("Logout requested unapproved return url: "+return_to)
            return_to = None
        if not return_to:
            return_to = cfg.get('default_logout_return_url')
        if not return_to:
            log.warning("No logout return URL configured; returning local default")
            req = convert_flask_request_for_saml(request,
                                                 current_app.config.get('lowercase_urlencoding'))
            return_to = OneLogin_Saml2_Utils.get_self_host(req)       + \
                        cfg.get('server', {}).get('context-path', "") + \
                        "sso/_logininfo"

        return redirect(auth.logout(return_to, name_id, session_index, name_id_nq,
                                    name_id_format, name_id_spnq))

    @app.route('/sso/saml/sls', methods=['GET'])
    def sls():
        """
        receive and process a logout request response from the IDP
        """
        request_id = None
        if 'LogoutRequestID' in session:
            request_id = session['LogoutRequestID']
            
        log = current_app.logger
        cfg = current_app.config
        auth = create_saml_sp(request, cfg['saml'], cfg.get('data_dir'),
                              cfg.get('lowercase_urlencoding'))

        dscb = lambda: session.clear()
        try:
            return_to = auth.process_slo(request_id=request_id, delete_session_cb=dscb)
        except OneLogin_Saml2_Error as ex:
            return _handle_badinput(str(ex))
            
        errs = auth.get_errors()
        
        if len(errs) > 0:
            # IDP message has some validity errors
            log.error("Failures encountered while processing IDP response:\n  "+
                      "\n  ".join(errs))
            return _handle_error("Invalid response from IDP: "+str(auth.get_last_error_reason()),
                                 502, errors=errs)

        if return_to and not checkAllowedUrls(return_to, cfg.get('allowed_service_urls', [])):
            log.error("Logout requested unapproved return url: "+return_to)
            return _handle_badinput("post-logout return URL is not recognized or not approved",
                                    "Disallowed redirectTo")
            
        if not return_to:
            cfg.get('default_logout_return_url')
        if not return_to:
            log.warning("No logout return URL configured; returning local default")
            return_to = OneLogin_Saml2_Utils.get_self_host(req)       + \
                        cfg.get('server', {}).get('context-path', "") + \
                        "sso/_logininfo"
            
        return redirect(return_to)

    @app.route('/sso/auth/_logininfo')
    def get_user_info():
        """
        return to the client information about the currently logged-in user.
        """
        creds = get_credentials()

        if not creds.is_authenticated() or creds.expired():
            return _handle_unauthenticated("Client is not authenticated", "Unauthenticated")

        resp = make_response(creds.to_json(), 200)
        resp.content_type = "application/json"
        return resp

    def get_credentials() -> Credentials:
        """
        generate a credentials object for the currently logged in user.  
        :rtype:  Credentials
        """
        disabled = current_app.config.get("disabled_saml_login")
        if disabled and disabled.get("engaged") is True:
            try:
                return make_testuser_credentials(disabled.get('testuser',{}))
            except ConfigurationException as ex:
                current_app.logger.failure("Failed to create testuser "
                                           "credentials: %s", str(ex))
                raise

        if session_authenticated(session):
            return make_credentials(session.get('samlUserAttrs', {}), get_expiration(session))

        # return an anonymous user
        return Credentials()  

    def session_authenticated(sess):
        """
        return True if the given dictionary describes an unexpired, authentication session. 
        
        :param dict sess:  the session data that set by the login process
        """
        try:
            return sess.get('samlAuthenticated') and not session_expired(sess)
        except Exception as ex:
            if current_app:
                current_app.logger.error("Failure to interpret samlExpiration: "+str(ex))
                current_app.logger.warning("Treating session for user %s as unauthenticated",
                                           sess.get('samlNameId', "(unknown)"))
            return False

    def get_expiration(sess):
        expiration = sess.get('samlSessionExpiration')

        if isinstance(expiration, str):
            try:
                expiration = datetime.fromisoformat(sess['samlSessionExpiration'])
            except ValueError as ex:
                if current_app:
                    current_app.logger.error("session property, samlSessionExpiration, contains "
                                             "unparseable value: %s", sess['samlSessionExpiration'])
                raise

        return expiration

    def session_expired(sess):
        """
        return True if the authenticated session has expired.  If the 
        ``samlSessionExpiration`` property is not set, the session will be considered expired.
        """
        expires = get_expiration(sess)
        if expires is None:
            return False
        if expires < datetime.now():
            return True
        return False

    @app.route('/sso/auth/_tokeninfo')
    def get_token():
        """
        generate a credentials object for the currently logged in user that includes
        an authentication token
        :rtype:  Credentials
        """
        creds = get_credentials()

        if not creds.is_authenticated() or creds.expired():
            return _handle_unauthenticated("Client is not authenticated", "Unauthenticated")

        creds.set_token()
        resp = make_response(creds.to_json(), 200)
        resp.content_type = "application/json"
        return resp

    @app.route('/sso/metadata/')
    def metadata():
        log = current_app.logger
        cfg = current_app.config
        auth = create_saml_sp(request, cfg['saml'], cfg.get('data_dir'),
                              cfg.get('lowercase_urlencoding'))

        settings = auth.get_settings()
        metadata = settings.get_sp_metadata()
        errs = settings.validate_metadata(metadata)
    
        if len(errs) > 0:
            # IDP message has some validity errors
            log.error("Generated invalid SP metadata:\n  "+
                      "\n  ".join(errs))
            return _handle_error("Failed to assemble valid metadata", 500, errors=errs)

        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
        return resp


    return app


def convert_flask_request_for_saml(flaskreq, lowercase_urlencoding=False):
    """
    Convert an incoming flask request to authenticate the user into a onelogin.saml2 
    request

    :param flaskreq:  the flask request instance
    :param bool lowercase_urlencoding:  if True, support lowercase url encoding as is done
                                        by the Microsoft ADFS IDP.  (default: False)
    """
    out = {
        'https': 'on' if flaskreq.scheme == 'https' else 'off',
        'http_host': flaskreq.host,
        'script_name': flaskreq.root_path,
        'path_info': flaskreq.path,
        'query_string': flaskreq.query_string,
        'get_data': flaskreq.args.copy(),
        'post_data': flaskreq.form.copy()
    }

    if lowercase_urlencoding:
        out['lowercase_urlencoding'] = True

    if flaskreq.environ.get('HTTP_X_FORWARDED_PROTO'):
        out['https'] = 'on' if flaskreq.environ.get('HTTP_X_FORWARDED_PROTO') == 'https' else 'off'
    if flaskreq.environ.get('HTTP_X_FORWARDED_HOST'):
        out['http_host'] = flaskreq.environ.get('HTTP_X_FORWARDED_HOST')

    return out

def create_saml_sp(flaskreq, samlconfig: Mapping, datadir: str=None,
                   lowercase_urlencoding: bool=False):
    """
    create the SAML SP instance
    :param        flaskreq:  the current Flask Request instance 
    :param dict samlconfig:  the configuration to pass to the SAML SP's constructor
    :param str    data_dir:  the directory containing saml2 data (like certs)
    :rtype: OneLogin_Saml2_Auth
    """
    samlreq = convert_flask_request_for_saml(flaskreq, lowercase_urlencoding)
    return OneLogin_Saml2_Auth(samlreq, samlconfig, datadir)

def checkAllowedUrls(url: str, allowed: List[str]):
    """ 
    Check whether a given URL matches one of the allowed endpoints.  To match, the given URL
    (i.e. the client service's return URL) must begin with one of the allowed base URLs.
    :param str           url:  the URL to test
    :param list[str] allowed:  a list of allowed base URLs
    :return:  True if the given URL is allowed, False, if a match cannot be made
              :rtype: bool
    """
    for listedurl in allowed:
        if url.startswith(listedurl):
            return True
    return False

def make_testuser_credentials(usercfg):
    attrs = {
        "userName":     usercfg.get("given_name", "Test"),
        "userLastName": usercfg.get("family_name", "User"),
        "userEmail":    usercfg.get("email", "test.user@example.com"),
        "userOU":       usercfg.get("ou", "unknown"),
        "displayName":  usercfg.get("display_name", "TestUser"),
        "role":         usercfg.get("role", "not-set"),
        "winId":        usercfg.get("id", usercfg.get("id", "testuser")),
    }
    return Credentials(usercfg.get("id", "testuser"), attrs)

def _handle_error(reason: str, code: int=400, status: str=None, **kwargs):
    """
    send the client an error reponse

    Note: use only within the app context

    :param str reason:  a message explaining what the problem is
    :param int code:    the status code to return (default: 400)
    """
    content = dict(kwargs)
    content.update({"Error": reason, "ErrorCode": code})
    if status:
        content['status'] = status
    resp = make_response(content, code)
    if status:
        resp.status = f"{code} {status}"
    return resp

def _handle_unauthenticated(reason: str=None, status: str=None):
    """
    send the client an error response indicating the user could not be authenticated

    Note: use only within the app context

    :param str reason:  a message explaining what the problem is
    """
    if not reason:
        reason = "Authentication Failed"
    return _handle_error(reason, 401, status)

def _handle_badinput(reason: str, status: str=None):
    """
    send the client an error response indicating the request was ill-formed or missing 
    a required piece.

    Note: use only within the app context

    :param str reason:  a message explaining what the problem is
    """
    return _handle_error(reason, 400, status)




if __name__ == "__main__":
    app.run(port=8000, debug=True)
    
    
