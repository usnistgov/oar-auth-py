"""
a module providing support for interacting with an identity provider (IDP).  
Support for different IDPs appear in different submodules.  The primary 
function of the different implementations is to populate a Credentials 
instance from the data returned by the IDP.
"""
from .nist_okta import make_credentials
