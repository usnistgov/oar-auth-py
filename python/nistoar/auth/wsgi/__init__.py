"""
a module providing the implementations for the OAR authentication web service.  
The purpose of the service is to broker the authentication process with the IDP 
and to provide authentication tokens for authenticated users that need to 
connect to other OAR services.  

Currently, the default implementation is a Flask application; see the 
:py:mod:`nistoar.auth.wsgi.flask` documentation for more details.
"""

# the default implementation is a flask app
from .flask import create_app
