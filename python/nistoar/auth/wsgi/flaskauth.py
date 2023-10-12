"""
This is a flask application to provide SAML based authentication Service Provider API
This API is used by clients to connect to SSO and get user authenticated,
It also generates authtnetication token for the service. In this case all OAR systems use this to connect
NIST SSO service using SAML protocol.

@Deoyani Nandrekar-Heinis
"""
import os
import jwt
from flask import (Flask, request, render_template, redirect, session,
                   make_response , jsonify)

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from configs import odiconfig 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'onelogindemopytoolkit'
app.config['SAML_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saml')

"""
Initialize python3-saml onelogin library
"""
def init_saml_auth(req):
    
    auth = OneLogin_Saml2_Auth(req, custom_base_path=app.config['SAML_PATH'])
    return auth

"""
Setting up flask requests here including host and scheme.
"""
def prepare_flask_request(request):
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'script_name': request.path,
        'get_data': request.args.copy(),
        # Uncomment if using ADFS as IdP, https://github.com/onelogin/python-saml/pull/144
        # 'lowercase_urlencoding': True,
        'post_data': request.form.copy()
    }

"""
This is handling unauthencated user errors.  
"""
def handle_errors(error_reason):
    jsonmessage ={ "Error":error_reason, "ErrorCode": "401"}
    response = jsonify(jsonmessage)
    return response, 401

"""
Loading configurations from the configserver
"""
authconfig = odiconfig.get_auth_config()

"""
This  function checks whether the URL provided in redirectTo parameter is a valid URL,
If it is valid once authenticated user is redirected to that URL if not appropriate error message is sent. 
"""
def checkAllowedUrls(url):
    listurls = authconfig.redirect_url.split(',')
    for listedurl in listurls:
        if url.startswith(listedurl):
            return True
    return False 

"""
Enter to SAML login system endpoint.
This is main api endpoint for this authentication provider, In this once the authentication is requested by client, 
the request is redirected to NIST SSO endpoint. If user is authenticated it successfully redirected back to the
requesting application.

we kept the path this way to support existing
URLs used in all the applications which use this auth service
"""
@app.route('/sso/saml/login', methods=['GET', 'POST'])
def nistsso():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []
    error_reason = None

    redirectTo = None
    #check if this argument is provided to capture redirect URL and validate it. 
    if 'redirectTo' in request.args:
        if checkAllowedUrls(request.args.get("redirectTo")): 
            redirectTo = request.args.get("redirectTo")
        else: 
            return handle_errors("Redirect to the application URL is not allowed.")

    if 'sso' in request.args:
        return redirect(auth.login())
    elif 'sso2' in request.args:
        return_to = '%sattrs/' % request.host_url
        return redirect(auth.login(return_to))
 
    errors = auth.get_errors()
    error_reason = auth.get_last_error_reason()
    if(len(errors) != 0):
        return handle_errors("User is not Authenticated."+ error_reason)
    # If user is authenticated the session hosts all the userdata
    if 'samlUserdata' in session:
        if len(session['samlUserdata']) > 0:
            #collect all the userinformation related data
            attributes = session['samlUserdata'].items()
            # if the redirect URL is valid, redirect to requsted URL
            if redirectTo :
                return redirect(redirectTo)
            else: 
                return redirect("/sso/_tokeninfo")
     #This needs to be updated in future   
    return redirect('/sso/saml/login?sso')

"""
Get token information endpoint.
Once User is authenticated, extract relevant information from the samlUserData stored in session.
This API endpoint provides that information in JSON format along with JWT generated using various 
paramters.
"""
@app.route('/sso/_tokeninfo/')
def token():
    if 'samlUserdata' in session:
        paint_logout = True
        if len(session['samlUserdata']) > 0:
            attributes = session['samlUserdata'] #.items()
    else:
        if 'samlUserdata' not in session:
            return handle_errors("User is not Authenticated!")
    
    attributes_out = {}        
    for attribute in attributes.keys():
        if attribute == 'http://schemas.microsoft.com/identity/claims/displayname':
            attributes_out['displayName'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress':
            attributes_out['emailId'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname':
            attributes_out['name'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nistDivisionNumber':
            attributes_out['division'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nistOU':
            attributes_out['OU'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname':
            attributes_out['lastname'] = attributes[attribute]
        elif attribute == 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/windowsaccountname':
            attributes_out['shortname'] = attributes[attribute]
        
    
    token = jwt.encode(attributes_out,odiconfig.jwtsecret,algorithm="HS256")
    attributes_out["token"] = token
    return jsonify(attributes_out)

"""
SP metadata endpoint.
This endpoint provides metadata of the service provider aka this 
authentication API, this helps communication between SSO and SP possible.
"""
@app.route('/sso/metadata/')
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp

"""
Assertion consumer service endpoint.
When user logs in first time into system, it gets redirected to SSO and once valid response recieved
those values are stored in session, this endpoint provides this functionality.
"""
@app.route('/sso/asc', methods=['GET', 'POST'])
def acshandling():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []
    error_reason = None
    not_auth_warn = False


    request_id = None
    if 'AuthNRequestID' in session:
        request_id = session['AuthNRequestID']
    auth.process_response(request_id=request_id)
    errors = auth.get_errors()
    not_auth_warn = not auth.is_authenticated()
    if len(errors) == 0:
        if 'AuthNRequestID' in session:
            del session['AuthNRequestID']
        session['samlUserdata'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlNameIdFormat'] = auth.get_nameid_format()
        session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
        session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
        session['samlSessionIndex'] = auth.get_session_index()
        self_url = OneLogin_Saml2_Utils.get_self_url(req)
        print("user id",auth.get_nameid())
        print ("My id", request.form['RelayState'])
        if 'RelayState' in request.form and self_url != request.form['RelayState']:
            # To avoid 'Open Redirect' attacks, before execute the redirection confirm
            # the value of the request.form['RelayState'] is a trusted URL.
            return redirect(auth.redirect_to(request.form['RelayState']))
    elif auth.get_settings().is_debug_active():
        error_reason = auth.get_last_error_reason()
        print(error_reason)
            
            
# This is used to run locally in development mode
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=odiconfig.authport, debug=True, ssl_context='adhoc')

if __name__ == "__main__":
    app.run( port=odiconfig.authport, debug=True)
    
    