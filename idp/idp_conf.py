#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
import saml2.xmldsig as ds

from saml2 import BINDING_HTTP_ARTIFACT
from saml2 import BINDING_HTTP_POST
from saml2 import BINDING_HTTP_REDIRECT
from saml2 import BINDING_SOAP
from saml2 import BINDING_URI
from saml2.saml import NAME_FORMAT_UNSPECIFIED
from saml2.saml import NAMEID_FORMAT_PERSISTENT
from saml2.saml import NAMEID_FORMAT_TRANSIENT
from saml2.saml import NAMEID_FORMAT_UNSPECIFIED


try:
    from saml2.sigver import get_xmlsec_binary
except ImportError:
    get_xmlsec_binary = None

if get_xmlsec_binary:
    xmlsec_path = get_xmlsec_binary(["/opt/local/bin"])
else:
    xmlsec_path = '/usr/bin/xmlsec1'

import builtins
BASEDIR = os.path.abspath(os.path.dirname(__file__))
if hasattr(builtins, 'IDP_BASE_DIR') and getattr(builtins, 'IDP_BASE_DIR'):
    BASEDIR = getattr(builtins, 'IDP_BASE_DIR') 

def full_path(local_file):
    return os.path.join(BASEDIR, local_file)

HOST = 'localhost'
PORT = 8088

HTTPS = True

if HTTPS:
    BASE = "https://%s:%s" % (HOST, PORT)
else:
    BASE = "http://%s:%s" % (HOST, PORT)

# HTTPS cert information
SERVER_CERT = full_path("pki/mycert.pem")
SERVER_KEY = full_path("pki/mykey.pem")
CERT_CHAIN = ""
#SIGN_ALG = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
DIGEST_ALG = None
SIGN_ALG = ds.SIG_RSA_SHA512
DIGEST_ALG = ds.DIGEST_SHA512


CONFIG = {
    "entityid": "%s/idp.xml" % BASE,
    "description": "My IDP",
    #"valid_for": 168,
    "service": {
        "aa": {
            "endpoints": {
                "attribute_service": [
                    ("%s/attr" % BASE, BINDING_SOAP)
                ]
            },
            "name_id_format": [NAMEID_FORMAT_TRANSIENT,
                               NAMEID_FORMAT_PERSISTENT]
        },
        "aq": {
            "endpoints": {
                "authn_query_service": [
                    ("%s/aqs" % BASE, BINDING_SOAP)
                ]
            },
        },
        "idp": {
            "name": "Rolands IdP",
            "sign_response": True,
            "signing_algorithm": SIGN_ALG,
            "endpoints": {
                "single_sign_on_service": [
                    ("%s/sso/redirect" % BASE, BINDING_HTTP_REDIRECT),
                    ("%s/sso/post" % BASE, BINDING_HTTP_POST),
                    ("%s/sso/art" % BASE, BINDING_HTTP_ARTIFACT),
                    ("%s/sso/ecp" % BASE, BINDING_SOAP)
                ],
                "single_logout_service": [
                    ("%s/slo/soap" % BASE, BINDING_SOAP),
                    ("%s/slo/post" % BASE, BINDING_HTTP_POST),
                    ("%s/slo/redirect" % BASE, BINDING_HTTP_REDIRECT)
                ],
                "artifact_resolve_service": [
                    ("%s/ars" % BASE, BINDING_SOAP)
                ],
                "assertion_id_request_service": [
                    ("%s/airs" % BASE, BINDING_URI)
                ],
                "manage_name_id_service": [
                    ("%s/mni/soap" % BASE, BINDING_SOAP),
                    ("%s/mni/post" % BASE, BINDING_HTTP_POST),
                    ("%s/mni/redirect" % BASE, BINDING_HTTP_REDIRECT),
                    ("%s/mni/art" % BASE, BINDING_HTTP_ARTIFACT)
                ],
                "name_id_mapping_service": [
                    ("%s/nim" % BASE, BINDING_SOAP),
                ],
            },
            "policy": {
                "default": {
                    "lifetime": {"minutes": 15},
                    "attribute_restrictions": None, # means all I have
                    "name_form": NAMEID_FORMAT_UNSPECIFIED,
                    #"entity_categories": ["swamid", "edugain"]
                },
            },
            "subject_data": "./idp.subject",
            "name_id_format": [NAMEID_FORMAT_TRANSIENT,
                               NAMEID_FORMAT_PERSISTENT]
        },
    },
    "debug": 1,
    "key_file": full_path("pki/mykey.pem"),
    "cert_file": full_path("pki/mycert.pem"),
    "metadata": {
        "local": [full_path("authbroker.xml")]
    },
    "organization": {
        "display_name": "OAR MIDAS",
        "name": "Developers",
        "url": "http://localhost",
    },
    "contact_person": [
        {
            "contact_type": "technical",
            "given_name": "Roland",
            "sur_name": "Hedberg",
            "email_address": "technical@example.com"
        }, {
            "contact_type": "support",
            "given_name": "Support",
            "email_address": "support@example.com"
        },
    ],
    # This database holds the map between a subject's local identifier and
    # the identifier returned to a SP
    "xmlsec_binary": xmlsec_path,
    "attribute_map_dir": full_path("attributemaps"),
    "logging": {
        "version": 1,
        "formatters": {
            "simple": {
                "format": "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s] %(message)s",
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "level": "DEBUG",
                "formatter": "simple",
            },
        },
        "loggers": {
            "saml2": {
                "level": "DEBUG"
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": [
                "stderr",
            ],
        },
    },
}

# Authentication contexts

    #(r'verify?(.*)$', do_verify),

CAS_SERVER = "https://cas.umu.se"
CAS_VERIFY = "%s/verify_cas" % BASE
PWD_VERIFY = "%s/verify_pwd" % BASE

AUTHORIZATION = {
    "CAS" : {"ACR": "CAS", "WEIGHT": 1, "URL": CAS_VERIFY},
    "UserPassword" : {"ACR": "PASSWORD", "WEIGHT": 2, "URL": PWD_VERIFY}
}
