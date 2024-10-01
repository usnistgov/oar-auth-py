"""
Support for the NIST Identity Provider service.  This module mainly handles 
populating a Credentials object based on the SAML user attributes provide by 
the NIST IDP. 
"""
from collections import namedtuple
from collections.abc import Mapping
from typing import Union

from ..creds import Credentials

_MS_BASE_URI = "http://schemas.microsoft.com/"
_SOAP_BASE_URI = "http://schemas.xmlsoap.org/"

AttributeNames = namedtuple("AttributeNames",
                            "ID EMAIL QNAME DNAME GIVEN FAMILY OU DIVNO ROLE GROUP WINID".split())
ATTR_NAME = AttributeNames(
    ID     = _SOAP_BASE_URI + "ws/2005/05/identity/claims/nameidentifier",
    EMAIL  = _SOAP_BASE_URI + "ws/2005/05/identity/claims/emailaddress",
    QNAME  = _SOAP_BASE_URI + "ws/2005/05/identity/claims/name",
    DNAME  = _MS_BASE_URI   + "identity/claims/displayname",
    GIVEN  = _SOAP_BASE_URI + "ws/2005/05/identity/claims/givenname",
    FAMILY = _SOAP_BASE_URI + "ws/2005/05/identity/claims/surname",
    OU     = _SOAP_BASE_URI + "ws/2005/05/identity/claims/nistOU",
    DIVNO  = _SOAP_BASE_URI + "ws/2005/05/identity/claims/nistDivisionNumber",
    ROLE   = _MS_BASE_URI   + "ws/2008/06/identity/claims/role",
    GROUP  = _SOAP_BASE_URI + "claim/Group",
    WINID  = _MS_BASE_URI + "ws/2008/06/identity/claims/windowsaccountname"
)

def make_credentials(samlattrs: Mapping, expiration: Union[str,int,float]=None):
    """
    create a Credentials object based on the results of SAML authentication 
    that can be returned to our service clients.
    """
    want = [ ATTR_NAME.ID, ATTR_NAME.EMAIL, ATTR_NAME.GIVEN, ATTR_NAME.FAMILY, ATTR_NAME.WINID ]
    id = samlattrs.get(ATTR_NAME.WINID, ["unknown"])[0]
    attrs = {
        "userName":     samlattrs.get(ATTR_NAME.GIVEN,  ["unknown"])[0],
        "userLastName": samlattrs.get(ATTR_NAME.FAMILY, ["unknown"])[0],
        "userEmail":    samlattrs.get(ATTR_NAME.EMAIL,  ["not-set"])[0],
        "winId":        samlattrs.get(ATTR_NAME.WINID,  ["unknown"])[0],
    }

    for name in samlattrs:
        if name not in want:
            attrs[name] = samlattrs.get(name)[0]

    if expiration is not None and isinstance(expiration, str):
        # assume in ISO format
        try:
            expiration = datetime.fromisoformat(expiration).timestamp()
        except ValueError as ex:
            raise ValueError("make_credentials(): expiration param not an ISO date: "+expiration)

    return Credentials(id, attrs, expiration)

