"""
This is a flask application to provide SAML based authentication Service Provider API
This API is used by clients to connect to SSO and get user authenticated,
It also generates authtnetication token for the service. In this case all OAR systems use this to connect
NIST SSO service using SAML protocol.

@Deoyani Nandrekar-Heinis
"""
import os, logging
from pathlib import Path
from typing import List
from collections.abc import Mapping

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
    if data_dir:
        # this will override any value in the config
        config = dict(config)
        config['data_dir'] = str(data_dir)
    else:
        data_dir = find_auth_data_dir(config)
    if data_dir:
        data_dir = Path(data_dir).resolve()

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
        auth = create_saml_sp(request, cfg['saml'], cfg.get('lowercase_urlencoding'))

        if 'redirectTo' not in request.args:
            return _handle_badinput("missing redirectTo query parameter")

        if not checkAllowedUrls(request.args['redirectTo'], cfg.get('allowed_service_endpoints', [])):
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
        auth = create_saml_sp(request, cfg['saml'], cfg.get('lowercase_urlencoding'))

        try: 
            auth.process_response(request_id=request_id)
        except (OneLogin_Saml2_Error, XMLSyntaxError) as ex:
            return _handle_badinput(str(ex))
        errs = auth.get_errors()

        if len(errs) > 0:
            # IDP message has some validity errors
            log.error("Failures encountered while processing IDP response:\n  "+
                      "\n  ".join(errs))
            return _handle_error("Invalid response from IDP", 400, errors=errs)

        if not auth.is_authenticated():
            return _handle_unauthenticated("User did not successfully login")

        current_app.logger.info("user %s successfully authenticated", auth.get_nameid())

        if 'AuthNRequestID' in session:
            del session['AuthNRequestID']
        session['samlUserdata'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlNameIdFormat'] = auth.get_nameid_format()
        session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
        session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
        session['samlSessionIndex'] = auth.get_session_index()
        session['samlSessionExpiration'] = auth.get_session_expiration()
        session['samlAuthenticated'] = True
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
        auth = create_saml_sp(request, cfg['saml'], cfg.get('lowercase_urlencoding'))

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
        auth = create_saml_sp(request, cfg['saml'], cfg.get('lowercase_urlencoding'))

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
            return _handle_error("Invalid response from IDP", 502, errors=errs)

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

    @app.route('/sso/_logininfo')
    def get_user_info():
        """
        return to the client information about the currently logged-in user.
        """
        creds = get_credentials()

        if not creds.is_authenticated() or creds.expired():
            return _handle_unauthenticated("Client is not authenticated", "Unauthenticated")

        return creds.to_json(), 200

    def get_credentials() -> Credentials:
        """
        generate a credentials object for the currently logged in user.  
        :rtype:  Credentials
        """
        if session_authenticated(session):
            expiration = session.get('samlSessionExpiration')
            if expiration is not None:
                try:
                    expiration = datetime.fromisoformat(expiration).timestamp()
                except ValueError as ex:
                    if current_app:
                        current_app.logger.warning("SAML process returned unparseable expiration "
                                                   "time: %s", str(expiration))
                    expiration = None

            return make_credentials(session.get('samlUserData'), expiration)

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

    def session_expired(sess):
        """
        return True if the authenticated session has expired.  If the 
        ``samlSessionExpiration`` property is not set, the session will be considered expired.
        """
        if sess.get('samlSessionExpiration'):
            return True

        try:
            expires = datetime.fromisoformat(sess['samlSessionExpiration'])
            if expires < datetime.now():
                return True
        except ValueError as ex:
            if current_app:
                current_app.logger.error("session property, samlSessionExpiration, contains "
                                         "unparseable value: %s", sess['samlSessionExpiration'])
            raise

        return False

    @app.route('/sso/_tokeninfo')
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
        return creds.to_json(), 200

    @app.route('/sso/metadata/')
    def metadata():
        log = current_app.logger
        cfg = current_app.config
        auth = create_saml_sp(request, cfg['saml'], cfg.get('lowercase_urlencoding'))

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

def create_saml_sp(flaskreq, samlconfig, lowercase_urlencoding=False):
    """
    create the SAML SP instance
    :param flaskreq:    the current Flask Request instance 
    :param samlconfig:  the configuration to pass to the SAML SP's constructor
    :rtype: OneLogin_Saml2_Auth
    """
    samlreq = convert_flask_request_for_saml(flaskreq, lowercase_urlencoding)
    return OneLogin_Saml2_Auth(samlreq, samlconfig)

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
    
    
